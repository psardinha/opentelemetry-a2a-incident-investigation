import json
import re
from collections import Counter


class LogAnalyzer:
  def __init__(self, loki_client, tempo_client):
    self.loki = loki_client
    self.tempo = tempo_client

  def analyze(self, service_name: str, start_ns: int, end_ns: int):
    raw = self.loki.query_range(service_name=service_name, start_ns=start_ns, end_ns=end_ns)
    logs = self.parse_logs(raw)
    traces = self.build_trace_summaries(logs)
    traces = self.correlate_traces(traces)
    return {"service": service_name,
            "total_logs": len(logs),
            "info_count": sum(1 for log in logs if log.get("level") == "INFO"),
            "warn_count": sum(1 for log in logs if log.get("level") == "WARN"),
            "error_count": sum(1 for log in logs if log.get("level") == "ERROR"),
            "exception_count": self.count_exceptions(logs),
            "exception_messages": self.summarize_exceptions(logs),
            "traces": traces,
            "patterns": self.build_error_patterns(traces)}

  # ------------------------------------------------------------------
  # Loki
  # ------------------------------------------------------------------

  def parse_logs(self, raw):
    logs = []

    for stream in raw:
      for timestamp_ns, log_line in stream.get("values", []):
        try:
          entry = json.loads(log_line)
        except json.JSONDecodeError:
          continue
        logs.append({"timestamp": entry.get("@timestamp"),
                     "timestamp_ns": timestamp_ns,
                     "level": entry.get("level"),
                     "service": entry.get("service.name"),
                     "message": entry.get("message"),
                     "exception_type": entry.get("exceptionType"),
                     "trace_id": entry.get("traceId"),
                     "span_id": entry.get("spanId")})
    return logs

  def count_exceptions(self, logs):
    return dict(Counter(log["exception_type"] for log in logs if log.get("exception_type")))

  def summarize_exceptions(self, logs):
    exceptions = {}

    for log in logs:
      exception_type = log.get("exception_type")
      if not exception_type:
        continue
      
      if exception_type not in exceptions:
        exceptions[exception_type] = {"count": 0, "messages": Counter()}
      exceptions[exception_type]["count"] += 1
      message = log.get("message")
      if message:
        exceptions[exception_type]["messages"][message] += 1

    for data in exceptions.values():
      data["messages"] = dict(data["messages"])

    return exceptions

  # ------------------------------------------------------------------
  # Trace grouping
  # ------------------------------------------------------------------

  def build_trace_summaries(self, logs):
    grouped = {}
    for log in logs:
      trace_id = log.get("trace_id")
      if trace_id:
        grouped.setdefault(trace_id, []).append(log)

    return [self.build_trace_summary(trace_id, trace_logs) for trace_id, trace_logs in grouped.items()]


  def build_trace_summary(self, trace_id, logs):
    error_logs = [log for log in logs if log.get("level") == "ERROR"]
    warn_logs = [log for log in logs if log.get("level") == "WARN"]
    info_logs = [log for log in logs if log.get("level") == "INFO"]

    if error_logs:
      status = "ERROR"
      primary_log = error_logs[0]
    elif warn_logs:
      status = "WARN"
      primary_log = warn_logs[0]
    else:
      status = "INFO"
      primary_log = info_logs[0] if info_logs else logs[0]

    return {"trace_id": trace_id,
            "status": status,
            "log_count": len(logs),
            "error_count": len(error_logs),
            "warn_count": len(warn_logs),
            "info_count": len(info_logs),
            "summary": {"message": primary_log.get("message"),
                        "exception_type": primary_log.get("exception_type"),
                        "span_id": primary_log.get("span_id"),
                        "timestamp": primary_log.get("timestamp")}}

  # ------------------------------------------------------------------
  # Loki -> Tempo correlation
  # ------------------------------------------------------------------

  def correlate_traces(self, traces):
    for trace in traces:
      if trace["status"] != "ERROR":
        continue
      spans = self.tempo.get_trace(trace["trace_id"])
      trace["tempo"] = self.summarize_tempo_trace(spans, trace["summary"]["span_id"])
      trace["diagnosis"] = self.build_trace_diagnosis(trace)
    return traces

  # ------------------------------------------------------------------
  # Tempo
  # ------------------------------------------------------------------

  def summarize_tempo_trace(self, spans, log_span_id):
    if not spans:
      return {"span_count": 0,
              "request": None,
              "error_associated_span": None,
              "failed_operations": [],
              "span_tree": []}

    request_span = None
    error_associated_span = None
    failed_operations = []

    for span in spans:
      if span.get("kind") == "SPAN_KIND_SERVER":
        request_span = span
      if span.get("span_id") == log_span_id:
        error_associated_span = span
      if span.get("status") == "STATUS_CODE_ERROR":
        failed_operations.append(self.summarize_span(span))

    return {"span_count": len(spans),
            "request": self.summarize_span(request_span),
            "error_associated_span": self.summarize_span(error_associated_span),
            "failed_operations": failed_operations,
            "span_tree": self.build_span_tree(spans)}


  @staticmethod
  def _read_attribute_value(attribute):
    if not isinstance(attribute, dict):
      return None
    value = attribute.get("value")
    if not isinstance(value, dict):
      return None
    for key in ("stringValue", "intValue", "boolValue", "doubleValue"):
      if key in value:
        return value.get(key)
    return value


  @classmethod
  def extract_exception_details(cls, span):
    if not isinstance(span, dict):
      return None

    events = span.get("events") or []
    for event in events:
      if event.get("name") != "exception":
        continue

      attributes = event.get("attributes") or []
      attr_map = {}
      for attribute in attributes:
        key = attribute.get("key")
        if key:
          attr_map[key] = cls._read_attribute_value(attribute)

      stacktrace = attr_map.get("exception.stacktrace")
      exception_type = attr_map.get("exception.type")
      exception_message = attr_map.get("exception.message")

      if not (stacktrace or exception_type or exception_message):
        continue

      source = {"method": None,
                "class": None,
                "file": None,
                "line": None}

      if stacktrace:
        for stack_line in stacktrace.splitlines():
          match = re.search(r"at\s+([^\s(]+)\(([^:()]+):(\d+)\)", stack_line)
          if match:
            source["method"] = match.group(1)
            source["file"] = match.group(2)
            source["line"] = int(match.group(3))
            if source["class"] is None and "." in match.group(1):
              source["class"] = match.group(1).rsplit(".", 1)[0]
            break

      method_attr = None
      class_attr = None
      for attribute in span.get("attributes") or []:
        key = attribute.get("key")
        if key == "method":
          method_attr = cls._read_attribute_value(attribute)
        elif key == "class":
          class_attr = cls._read_attribute_value(attribute)

      if not source["method"] and method_attr:
        source["method"] = method_attr
      if not source["class"] and class_attr:
        source["class"] = class_attr

      details = {"type": exception_type,
                 "message": exception_message,
                 "stacktrace": stacktrace,
                 "source": source}
      return details

    return None


  def summarize_span(self, span):
    if not span:
      return None

    result = {"span_id": span.get("span_id"),
              "parent_span_id": span.get("parent_span_id"),
              "name": span.get("name"),
              "kind": span.get("kind"),
              "status": span.get("status")}
    duration_ns = span.get("duration_ns")
    if duration_ns is not None:
      result["duration_ms"] = round(duration_ns / 1_000_000, 2)
    exception_details = self.extract_exception_details(span)
    if exception_details:
      result["exception"] = exception_details
    if span.get("attributes"):
      result["attributes"] = span["attributes"]
    return result


  def build_span_tree(self, spans):
    if not spans:
      return []
    by_parent = {}

    for span in spans:
      parent_id = span.get("parent_span_id")
      by_parent.setdefault(parent_id, []).append(span)

    def build_node(span):
      node = self.summarize_span(span)
      children = by_parent.get(span.get("span_id"), [])
      if children:
        node["children"] = [build_node(child) for child in children]
      return node

    roots = by_parent.get(None, [])
    return [build_node(root) for root in roots]

  # ------------------------------------------------------------------
  # Trace evidence
  # ------------------------------------------------------------------

  def build_trace_diagnosis(self, trace):
    summary = trace.get("summary", {})
    tempo = trace.get("tempo", {})

    request = tempo.get("request")
    operation = tempo.get("error_associated_span")

    failed_child_operation = None
    if operation:
      operation_span_id = operation.get("span_id")
      failed_child_operation = next((span for span in tempo.get("failed_operations", []) if span.get("parent_span_id") == operation_span_id),
                                    None)
    diagnosis = {"trace_id": trace["trace_id"],
                 "severity": trace["status"],
                 "exception": None,
                 "request": None,
                 "operation": None,
                 "failed_child_operation": None}

    # --------------------------------------------------------------
    # Loki exception evidence
    # --------------------------------------------------------------

    if summary.get("exception_type"):
      diagnosis["exception"] = {"type": summary.get("exception_type"), "message": summary.get("message")}

    # --------------------------------------------------------------
    # HTTP request evidence
    # --------------------------------------------------------------

    if request:
      attributes = request.get("attributes", {})
      diagnosis["request"] = {"method": attributes.get("method"),
                              "uri": attributes.get("uri", request.get("name")),
                              "status": attributes.get("status"),
                              "outcome": attributes.get("outcome"),
                              "duration_ms": request.get("duration_ms"),
                              "span_id": request.get("span_id")}

    # --------------------------------------------------------------
    # Span associated with the Loki error
    # --------------------------------------------------------------

    if operation:
      diagnosis["operation"] = {"name": operation.get("name"),
                                "span_id": operation.get("span_id"),
                                "duration_ms": operation.get("duration_ms"),
                                "status": operation.get("status"),
                                "exception": operation.get("exception")}

    # --------------------------------------------------------------
    # Failed child operation
    # --------------------------------------------------------------

    if failed_child_operation:
      diagnosis["failed_child_operation"] = {"name": failed_child_operation.get("name"),
                                             "span_id": failed_child_operation.get("span_id"),
                                             "duration_ms": failed_child_operation.get("duration_ms"),
                                             "status": failed_child_operation.get("status"),
                                             "parent_span_id": failed_child_operation.get("parent_span_id"),
                                             "exception": failed_child_operation.get("exception")}

    return diagnosis

  # ------------------------------------------------------------------
  # Error patterns
  # ------------------------------------------------------------------

  def build_error_patterns(self, traces):
    patterns = {}

    for trace in traces:
      diagnosis = trace.get("diagnosis")
      if not diagnosis:
        continue

      exception = diagnosis.get("exception") or {}
      request = diagnosis.get("request") or {}
      operation = diagnosis.get("operation") or {}
      failed_child = diagnosis.get("failed_child_operation") or {}

      # Only primitive/hashable values belong in the key.
      key = (exception.get("type"),
             request.get("method"),
             request.get("uri"),
             request.get("status"),
             operation.get("name"),
             failed_child.get("name"))
      if key not in patterns:
          patterns[key] = {"exception_type": exception.get("type"),
                           "message": exception.get("message"),
                           "method": request.get("method"),
                           "uri": request.get("uri"),
                           "http_status": request.get("status"),
                           "operation": operation.get("name"),
                           "failed_child_operation": failed_child.get("name"),
                           "count": 0,
                           "example_trace_ids": [],
                           "durations": []}

      pattern = patterns[key]
      pattern["count"] += 1
      if len(pattern["example_trace_ids"]) < 3:
        pattern["example_trace_ids"].append(trace["trace_id"])
      duration = request.get("duration_ms")
      if duration is not None:
        pattern["durations"].append(duration)

    result = []
    for pattern in patterns.values():
      durations = pattern.pop("durations")
      pattern["duration_stats_ms"] = self.duration_stats(durations)
      result.append(pattern)

    result.sort(key=lambda pattern: pattern["count"], reverse=True)
    for pattern in result:
      pattern["diagnosis"] = self.build_pattern_diagnosis(pattern)
    return result


  def duration_stats(self, durations):
    if not durations:
      return {"min": None,
              "max": None,
              "avg": None,
              "p50": None,
              "p95": None}

    durations = sorted(durations)
    return {"min": round(min(durations), 2),
        "max": round(max(durations), 2),
        "avg": round(sum(durations) / len(durations),  2),
        "p50": round(self.percentile(durations, 50), 2),
        "p95": round(self.percentile(durations, 95), 2)}

  def percentile(self, values, percentile):
    if not values:
      return None

    index = (len(values) - 1) * percentile / 100
    lower = int(index)
    upper = min(lower + 1, len(values) - 1)

    if lower == upper:
      return values[lower]

    weight = index - lower

    return values[lower] + weight * (values[upper] - values[lower])

  # ------------------------------------------------------------------
  # Pattern evidence
  # ------------------------------------------------------------------

  def build_pattern_diagnosis(self, pattern):
    exception_type = pattern.get("exception_type")
    message = pattern.get("message")
    method = pattern.get("method")
    uri = pattern.get("uri")
    http_status = pattern.get("http_status")
    operation = pattern.get("operation")
    failed_child = pattern.get("failed_child_operation")
    count = pattern.get("count")

    evidence = []
    if exception_type:
      evidence.append(f"{exception_type} occurred {count} times")
    if operation:
      evidence.append(f"failures occur in '{operation}'")
    if failed_child:
      evidence.append(f"failed child operation is '{failed_child}'")
    if http_status:
      evidence.append(f"requests return HTTP {http_status}")
    if http_status is not None:
      http_status = int(http_status)
    if http_status and 400 <= http_status < 500:
      category = "CLIENT_ERROR"
    elif http_status and http_status >= 500:
      category = "SERVER_ERROR"
    else:
      category = "UNKNOWN"

    return {"category": category,
            "exception": exception_type,
            "message": message,
            "operation": operation,
            "failed_child_operation": failed_child,
            "request": {"method": method,
                        "uri": uri,
                        "status": http_status},
            "occurrences": count,
            "duration_stats": pattern.get("duration_stats", {}),
            "evidence": evidence}
