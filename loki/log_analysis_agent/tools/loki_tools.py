class LokiTools:
  def __init__(self, loki_client):
    self.loki = loki_client

  def query_logs(self, service_name, start_ns, end_ns, exception_type=None, trace_id=None, span_id=None):
    return self.loki.query_range(service_name=service_name, start_ns=start_ns, end_ns=end_ns, 
                                 trace_id=trace_id, span_id=span_id, exception_type=exception_type)

  @staticmethod
  def definitions():
    return [{"type": "function",
             "function": {"name": "query_logs",
                          "description": ("Query Loki logs for a service within a time range. "
                                          "When a trace_id is available, prefer trace-level correlation "
                                          "to retrieve logs for the incident. Use span_id only when a "
                                          "specific span-level correlation is still needed. Do not query "
                                          "parent/child span IDs individually when they belong to the same "
                                          "trace unless there is a specific reason to do so. "
                                          "Use exception_type only when useful for the investigation. "
                                          "Return actual log messages and correlation metadata, not only "
                                          "aggregate counts."),
                          "parameters": {"type": "object",
                                         "properties": {"service_name": {"type": "string"},
                                                        "start_ns": {"type": "integer"},
                                                        "end_ns": {"type": "integer"},
                                                        "exception_type": {"type": "string",
                                                                           "description": "Optional exception type to filter on"},

                                                        "trace_id": {"type": "string", 
                                                                     "description": ("Tempo trace ID. Prefer this for correlating Loki logs "
                                                                                     "with the complete incident trace.")},
                                                        "span_id": {"type": "string", 
                                                                    "description": ("Tempo span ID. Use only when trace-level correlation "
                                                                                    "does not answer a specific span-level question.")}},
                                         "required": ["service_name", "start_ns", "end_ns"]}
                         }}]
