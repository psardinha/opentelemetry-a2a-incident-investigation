import base64
import binascii
import requests
import re


class TempoClient:
  def __init__(self, base_url: str):
    self.base_url = base_url.rstrip("/")

  def get_trace(self, trace_id: str) -> list[dict]:
    response = requests.get(f"{self.base_url}/api/traces/{trace_id}", timeout=10)
    response.raise_for_status()
    data = response.json()
    return self.parse_trace(data, trace_id)

  def extract_exception_details(self, span_attributes, span_event):
    if not isinstance(span_event, dict):
      return None
    if span_event.get("name") != "exception":
      return None
    event_attr = self.attributes_to_dict(span_event.get("attributes", []))
    stacktrace = event_attr.get("exception.stacktrace")
    exception_type = event_attr.get("exception.type")
    exception_message = event_attr.get("exception.message")
    if not (stacktrace or exception_type or exception_message):
      return None
    source = {"method": None, "class": None, "file": None, "line": None}
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

    if "method" in span_attributes:
      source["method"] = span_attributes.get("method")
    if "class" in span_attributes:
      source["class"] = span_attributes.get("class")        
    return {"type": exception_type,
            "message": exception_message,
            "location": source}
    
  def parse_trace(self, data: dict, expected_trace_id: str) -> list[dict]:
    spans = []
    for batch in data.get("batches", []):
      resource_attributes = self.attributes_to_dict(batch.get("resource", {}).get("attributes", []))
      service_name = resource_attributes.get("service.name")
      for scope_spans in batch.get("scopeSpans", []):
        scope = scope_spans.get("scope", {})
        for span in scope_spans.get("spans", []):
          trace_id = self.decode_trace_id(span.get("traceId"))
          if trace_id != expected_trace_id:
            raise ValueError(f"Tempo returned unexpected trace ID: {trace_id} != {expected_trace_id}")

          span_attributes = self.attributes_to_dict(span.get("attributes", []))

          status = span.get("status", {})
          exceptions = []
          for span_event in span.get("events", []):
            ev = self.extract_exception_details(span_attributes, span_event)
            if ev is not None:
              exceptions.append(ev)

          start_ns = int(span["startTimeUnixNano"])
          end_ns = int(span["endTimeUnixNano"])
          spans.append({"trace_id": trace_id,
                        "span_id": self.decode_id(span.get("spanId")),
                        "parent_span_id": self.decode_id(span.get("parentSpanId")),
                        "name": span.get("name"),
                        "kind": span.get("kind"),
                        "start_time_ns": str(start_ns),
                        "end_time_ns": str(end_ns),
                        "duration_ns": end_ns - start_ns,
                        "status": status.get("code"),
                        "status_message": status.get("message"),
                        "attributes": span_attributes,
                        "exceptions": exceptions,
                        "service": service_name,
                        "scope": {"name": scope.get("name"),
                                "version": scope.get("version")}})

    if not spans:
      return []
    by_parent = {}
    for span in spans:
      parent_id = span.get("parent_span_id")
      by_parent.setdefault(parent_id, []).append(span)

    def build_node(span):
      children = by_parent.get(span.get("span_id"), [])
      if children:
        span["children"] = [build_node(child) for child in children]
        if span["exceptions"]:
          leaf_span = self.get_leaf_spanid_with_exception(span)
          if leaf_span:
            span["exception_refs"] = [{"span_id": leaf_span}]
          del span["exceptions"]
      if span["parent_span_id"]:
        del span["trace_id"]
        del span["service"]
        del span["scope"]
      return span

    roots = by_parent.get(None, [])
    roots = [build_node(root) for root in roots]
    for root in roots:
      root["exception_origin_span_id"] = self.get_leaf_spanid_with_exception(root)
    return roots


  def get_leaf_spanid_with_exception (self, span):
    if span == None:
      return None
    children = span.get("children", [])
    for child in children:
      result = self.get_leaf_spanid_with_exception(child)
      if result is not None:
        return result
    if span.get("exceptions"):
      return span["span_id"]
    return None


  @staticmethod
  def attributes_to_dict(attributes: list) -> dict:
    result = {}
    for attribute in attributes:
      key = attribute.get("key")
      value = attribute.get("value", {})
      if "stringValue" in value:
        result[key] = value["stringValue"]
      elif "intValue" in value:
        if key != "exception" or result[key] != "none":
          result[key] = value["intValue"]
      elif "boolValue" in value:
        result[key] = value["boolValue"]
      elif "doubleValue" in value:
        result[key] = value["doubleValue"]
    return result


  @staticmethod
  def decode_id(value: str | None) -> str | None:
    if not value:
      return None
    try:
      return base64.b64decode(value, validate=True).hex()
    except (binascii.Error, ValueError):
      return value


  @classmethod
  def decode_trace_id(cls, value: str | None) -> str | None:
    return cls.decode_id(value)


if __name__ == "__main__":
  tempo = TempoClient("http://localhost:3200")
  trace_id = "0a905ed42e902de17fa0e3cef9fb0c7c"
  spans = tempo.get_trace(trace_id)

  print("=== TRACE ===")
  import json
  print(json.dumps(spans, indent=2))