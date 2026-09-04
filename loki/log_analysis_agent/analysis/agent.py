import json


class LogAnalysisAgent:
  SYSTEM_PROMPT = """
You are an incident investigation agent using Loki logs and Tempo traces.

Investigate using available telemetry. Initial evidence is only a starting
point; never assume it is the root cause.

Identify the most specific failure mechanism directly supported by telemetry.
Describe what was observed, not why it happened.

RULES

* Report exceptions, messages, error codes, span names, HTTP status, logs,
  attributes and source locations literally.
* Names, messages, status codes and span names do not prove their meaning.
* HTTP 400 does not prove client fault or invalid input.
* A span name such as "validate input" does not prove a validation failure.
* Do not infer request data, application behavior, implementation behavior,
  or root cause.
* Correlate Loki and Tempo using trace_id and span_id; use parent_span_id
  to reconstruct hierarchy.
* exception_origin_span_id identifies where an exception was recorded, not
  its cause.
* `exceptions` means an exception was recorded; do not say "threw" unless
  explicitly established.
* `exception_refs` identify descendant spans containing recorded exceptions.
* Parent/child relationships show telemetry hierarchy, not causation.
* Do not claim causation unless independently established by telemetry.
* Never turn a plausible explanation into a hypothesis without evidence.
* If the trigger is not established, write exactly:
  "Triggering condition: UNKNOWN."
* If no causal hypothesis is supported, write exactly:
  "No supported hypothesis can be established."

INVESTIGATION

* Start with Tempo.
* Use Loki only for relevant correlation or additional evidence.
* Do not query Loki merely to rediscover information already present in Tempo.
* Stop when the available telemetry is sufficient.

OUTPUT
Produce ONLY these sections:

### Incident Summary

### Observed Facts

### Error Pattern

### Trace Evidence

### Root Cause (mechanism + evidence + unknowns)

### Confidence

### Hypotheses

### Recommended Next Steps

Keep it concise:

* Observed Facts: maximum 5 bullets.
* Trace Evidence: maximum 4 bullets.
* Root Cause: exactly 3 bullets: Mechanism observed, Evidence,
  Triggering condition.
* Confidence: exactly 3 bullets: Failure mechanism, Exception origin,
  Triggering condition.
* Recommended Next Steps: maximum 3 bullets.

IMPORTANT

* Mechanism observed = concrete telemetry event, not its cause.
* Exception origin = span where the exception was recorded, not necessarily
  the runtime cause.
* A source-code location attached to an exception identifies its recorded
  location only; it is not automatically the root cause.
* Hypotheses must explain an unknown causal condition, not restate telemetry.
* If unsupported, the Hypotheses section must contain only:
  "No supported hypothesis can be established."

* Describe telemetry relationships neutrally.
  Prefer "X was recorded on span Y", "span Y reported X", or
  "X is correlated with Y".
* Do not use causal wording such as "caused", "resulted in", "led to",
  "triggered", "propagated", or "produced" unless the telemetry explicitly
  establishes causation.
* A sequence in the trace is not a causal explanation.
* Do not describe an HTTP response as being caused by a descendant span
  merely because that span is part of the same trace.

Complete every section. Never stop mid-sentence. Never omit a section.
Do not repeat the investigation or add a separate final answer.
"""

  def __init__(self, analyzer, llm, loki_tools=None, tempo_tools=None):
    self.analyzer = analyzer
    self.llm = llm
    self.loki_tools = loki_tools
    self.tempo_tools = tempo_tools

  def investigate(self, service_name, start_ns, end_ns, on_event=None):
    def emit(message):
      if on_event:
        on_event(message)

    # 1. Deterministic Loki discovery
    emit("Running deterministic Loki discovery.")
    analysis = self.analyzer.analyze(service_name=service_name, start_ns=start_ns, end_ns=end_ns)
    selected = self.select_representative_pattern(analysis)
    emit("Initial Loki discovery completed.")

    if selected is None:
      emit("No representative failure with a trace ID was found.")
      return {"analysis": analysis,
              "answer": "No representative failure with a trace ID was found."}

    pattern, trace_id = selected
    print("\n=== STEP 1: LOKI DISCOVERY ===")
    print(f"[AGENT] pattern={pattern.get('exception_type')} "
          f"uri={pattern.get('uri')} "
          f"status={pattern.get('http_status')} "
          f"count={pattern.get('count')}")
    print(f"[AGENT] trace_id={trace_id}")

    # 2. Give only initial evidence to the LLM.
    evidence = {"service": service_name,
                "time_range": {"start_ns": start_ns,
                              "end_ns": end_ns},
                "loki_pattern": pattern,
                "selected_trace_id": trace_id}

    messages = [{"role": "system",
                 "content": self.SYSTEM_PROMPT},
                {"role": "user",
                 "content": self._build_prompt(evidence)}]

    # 3. LLM-driven investigation.
    tools = self._get_tools()

    print("\n=== STEP 2: LLM INVESTIGATION ===")
    emit("Waiting for LLM analysis to first metrics discovery...")
    response = self.llm.chat( messages=messages, tools=tools)

    max_rounds = 8
    rounds = 0
    while getattr(response.message, "tool_calls", None):
      if rounds >= max_rounds:
        break

      rounds += 1
      messages.append(response.message)
      print(f"Tools round # {rounds}")
      for tool_call in response.message.tool_calls:
        name = tool_call.function.name
        arguments = tool_call.function.arguments
        if isinstance(arguments, str):
          try:
            arguments = json.loads(arguments)
          except json.JSONDecodeError:
            arguments = {}
        print(f"\n[AGENT TOOL CALL] {name}({arguments})")
        emit(f"Tool call>> {name}(" +
                     ", ".join(f'{k}="{v}"' if isinstance(v, str) else f"{k}={v}" for k, v in arguments.items()) + 
                     ")")
        result = self._execute_tool(name, arguments)

        print("\n[AGENT TOOL RESULT]")
        print(json.dumps(result, indent=2, default=str))
        tool_message = {"role": "tool",
                        "content": json.dumps(result, default=str)}
        
        if getattr(tool_call, "id", None):
          tool_message["tool_call_id"] = tool_call.id
        messages.append(tool_message)

      emit("Waiting for tool reply analysis...")
      response = self.llm.chat(messages=messages, tools=tools)

    answer = response.message.content
    print("\n=== FINAL INVESTIGATION ===")
    print(answer)
    return {"analysis": analysis,
            "selected_pattern": pattern,
            "trace_id": trace_id,
            "answer": answer}


  def _build_prompt(self, evidence):
    return f"""
Investigate this incident using the available Loki and Tempo tools.

Initial deterministic discovery:

{json.dumps(evidence, indent=2, ensure_ascii=False, default=str)}

This is only initial evidence, not the complete investigation.

Start by retrieving the Tempo trace for:

trace_id = `{evidence["selected_trace_id"]}`

Then correlate the relevant trace/span IDs with Loki logs.

Determine from telemetry:

1. What failed.
2. Where the failure was recorded.
3. The exception-origin span, if one exists.
4. How the failure is reflected through parent spans.
5. The observed HTTP/server outcome.
6. Whether the triggering condition is actually established.

Use tools before producing the final answer.
Do not assume that the initial Loki finding is the root cause.
"""

  def _get_tools(self):
    tools = []
    if self.loki_tools:
      tools += self.loki_tools.definitions()
    if self.tempo_tools:
      tools += self.tempo_tools.definitions()
    return tools

  def _execute_tool(self, name, arguments):
    if name == "get_trace":
      if not self.tempo_tools:
        return {"error": "Tempo tools are not available"}
      trace_id = arguments.get("trace_id")
      if not trace_id:
        return {"error": "trace_id is required"}
      try:
        return self.tempo_tools.get_trace(trace_id)
      except Exception as exc:
        return {"error": "Tempo query failed",
                "query": arguments["query"],
                "details": str(exc)}      

    if name == "query_logs":
      if not self.loki_tools:
        return {"error": "Loki tools are not available"}
      required = ["service_name", "start_ns", "end_ns"]
      for field in required:
        if arguments.get(field) is None:
          return {"error": f"{field} is required"}
      try:
        return self.loki_tools.query_logs(service_name=arguments["service_name"],
                                          start_ns=arguments["start_ns"],
                                          end_ns=arguments["end_ns"],
                                          trace_id=arguments.get("trace_id"),
                                          span_id=arguments.get("span_id"),
                                          exception_type=arguments.get("exception_type"))
      except Exception as e:
        return {"error": str(e)}

    return {"error": f"Unknown tool: {name}"}


  @staticmethod
  def select_representative_pattern(analysis):
    candidates = []
    for pattern in analysis.get("patterns", []):
      trace_ids = pattern.get("example_trace_ids", [])
      if not trace_ids:
        continue
      try:
        count = int(pattern.get("count", 0))
      except (TypeError, ValueError):
        count = 0
      try:
        status = int(pattern.get("http_status", 0))
      except (TypeError, ValueError):
        status = 0
      candidates.append({"pattern": pattern,
                         "trace_id": trace_ids[0],
                         "count": count,
                         "status": status})

    if not candidates:
      return None
    candidates.sort(key=lambda x: (x["count"], 1 if x["status"] == 500 else 0),
                    reverse=True)
    winner = candidates[0]
    return winner["pattern"], winner["trace_id"]
