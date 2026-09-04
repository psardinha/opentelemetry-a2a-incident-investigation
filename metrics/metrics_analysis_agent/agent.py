import json


class MetricsAnalysisAgent:
  SYSTEM_PROMPT = """
You are a Prometheus incident-investigation agent.

Analyze the initial metrics and identify one important unresolved question.

Available HTTP request metrics:
- http_server_requests_milliseconds_bucket
- http_server_requests_milliseconds_sum
- http_server_requests_milliseconds_count

Available labels:
- method
- outcome
- status
- exception
- uri

Then CALL at least one Prometheus tool to investigate the unresolved question.

The tool call is mandatory. Do not answer the question before calling the
tool. Do not describe or simulate a tool call.

The initial analysis covers a specific start and end time in nanoseconds.
For temporal investigation, use those exact start and end timestamps in the
Prometheus tool invocation.

After receiving the tool result, reassess the evidence and provide the conclusion.

Do not invent observations, metric semantics, baselines, or causes.
Do not infer causation from correlation alone.
If a Prometheus tool returns an error, the query produced no evidence.
Do not infer or describe the value the failed query was intended to calculate.

Final answer format:
## CONCLUSION

Return only:

### Findings
- Observed behavior
- Affected metric / URI / status
- Time window
- Strongest evidence

### Likely Cause
A cause must be directly supported by the telemetry.

Do not state a possible, potential, or suggested cause.
Do not infer a cause from the presence of 4xx/5xx errors, latency,
traffic patterns, or correlations between metrics.

If no telemetry directly identifies the mechanism causing the abnormal
behavior, return exactly:
"Cause cannot be established from the available telemetry."

### Confidence
High / Medium / Low

Do not produce:
- analysis plans
- hypothetical causes
- step-by-step narratives
- repeated raw telemetry
"""


  def __init__(self, analyzer, llm, prometheus_tools=None):
    self.analyzer = analyzer
    self.llm = llm
    self.prometheus_tools = prometheus_tools


  def summarize_range_result(self, raw):
    if isinstance(raw, dict) and "error" in raw:
        return raw
    summary = []
    for series in raw:
        metric = series.get("metric", {})
        values = series.get("values", [])
        numbers = []
        for _, value in values:
            try:
                numbers.append(float(value))
            except (TypeError, ValueError):
                pass
        if not numbers:
            continue
        summary.append({
            "metric": metric,
            "samples": len(numbers),
            "min": min(numbers),
            "max": max(numbers),
            "mean": sum(numbers) / len(numbers),
            "first": numbers[0],
            "last": numbers[-1],
        })
    return {"series_count": len(summary), "series": summary}


  def investigate(self, service_name, start, end, on_event=None):

    def emit(message):
      if on_event:
        on_event(message)

    # 1. Deterministic metric discovery
    emit("Running deterministic metric discovery.")
    analysis = self.analyzer.analyze(service_name=service_name, start=start, end=end)
    emit("Initial metric discovery completed.")

    for metric in analysis.get("metrics", {}).values():
      for result in metric.get("result", []):
        numbers = []
        for _, value in result.get("values", []):
          try:
            numbers.append(float(value))
          except (TypeError, ValueError):
            pass
        if not numbers:
          continue
        
        result["samples"] = len(numbers)
        result["min"] = min(numbers)
        result["max"] = max(numbers)
        result["mean"] = sum(numbers) / len(numbers)
        result["first"] = numbers[0]
        result["last"] = numbers[-1]
        if result["values"]:
          del result["values"]

    print("\n=== STEP 1: METRICS DISCOVERY ===")
    print(json.dumps(analysis, indent=2, default=str))

    # 2. Give initial evidence to the LLM
    evidence = {"service": service_name,
                "start_ns": start,
                "end_ns": end,
                "initial_metrics": analysis}

    messages = [{"role": "system",
                 "content": self.SYSTEM_PROMPT},
                {"role": "user",
                 "content": self._build_prompt(evidence)}]

    # 3. LLM-driven investigation
    tools = self._get_tools()

    print(f"\n=== STEP 2: LLM INVESTIGATION ===")
    emit("Waiting for LLM analysis to first metrics discovery...")
    response = self.llm.chat(messages=messages, tools=tools)

    max_rounds = 8
    rounds = 0
    executed_calls = set()

    while getattr(response.message, "tool_calls", None):
      if rounds >= max_rounds:
        break

      rounds += 1
      messages.append(response.message)
      print(f"\nTools round # {rounds}")

      for tool_call in response.message.tool_calls:
        name = tool_call.function.name
        arguments = tool_call.function.arguments

        if isinstance(arguments, str):
          try:
            arguments = json.loads(arguments)
          except json.JSONDecodeError:
            arguments = {}

        # Don't repeat queries
        call_key = (name, json.dumps(arguments, sort_keys=True))
        if call_key in executed_calls:
          print(f"[AGENT TOOL CALL] Skipping duplicate: {name}({arguments})")
          continue
        executed_calls.add(call_key)

        print(f"\n[AGENT TOOL CALL] {name}({arguments})")
        emit(f"Tool call>> {name}(" +
             ", ".join(f'{k}="{v}"' if isinstance(v, str) else f"{k}={v}" for k, v in arguments.items()) + 
             ")")
        result = self._execute_tool(name, arguments)

        print("\n[AGENT TOOL RESULT]")
        print(json.dumps(self.summarize_range_result(result), indent=2, default=str))
        tool_message = {"role": "tool", "content": json.dumps(self.summarize_range_result(result), default=str)}

        if getattr(tool_call, "id", None):
          tool_message["tool_call_id"] = tool_call.id
        messages.append(tool_message)

      emit("Waiting for tool reply analysis...")
      response = self.llm.chat(messages=messages, tools=tools)

    answer = response.message.content
    print("\n=== FINAL INVESTIGATION ===")
    print(answer)
    return {"analysis": analysis, "answer": answer}
    

  def _build_prompt(self, evidence):
    return f"""
            Initial deterministic metric analysis:

            {json.dumps(evidence, indent=2, default=str)}

            Identify one important unresolved question from the initial evidence.

            CALL AT LEAST ONE available Prometheus tool now to answer that question.
            Do not answer it in prose before the tool call.

            For temporal investigation, use the provided start and end timestamps in the tool invocation.
            """  


  def _get_tools(self):
    if self.prometheus_tools:
      return self.prometheus_tools.definitions()
    return []


  def _execute_tool(self, name, arguments):
    if not self.prometheus_tools:
      return {"error": "Prometheus tools are not available"}

    if name == "query_prometheus":
      query = arguments.get("query")
      if not query:
        return {"error": "query is required"}
      try:
        return self.prometheus_tools.query(query=query)
      except Exception as exc:
        return {"error": "PromQL query failed",
                "query": arguments["query"],
                "details": str(exc)}

    if name == "query_prometheus_range":
      required = ["query", "start", "end"]
      for field in required:
        if arguments.get(field) is None:
          return {"error": f"{field} is required"}

      try:
        return self.prometheus_tools.query_range(query=arguments["query"],
                                                 start=arguments["start"],
                                                 end=arguments["end"],
                                                 step=arguments.get("step", "30s"))
      except Exception as exc:
        return {"error": "PromQL query failed",
                "query": arguments["query"],
                "details": str(exc)}

    return {"error": f"Unknown tool: {name}"}