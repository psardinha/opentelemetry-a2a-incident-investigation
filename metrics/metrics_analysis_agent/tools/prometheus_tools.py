class PrometheusTools:
  def __init__(self, prometheus_client):
    self.prometheus = prometheus_client

  def query(self, query):
    return self.prometheus.query(query)

  def query_range(self, query, start, end, step="30s"):
    return self.prometheus.query_range(query=query, start=start, end=end, step=step)

  @staticmethod
  def definitions():
    return [{"type": "function",
             "function": {"name": "query_prometheus",
                          "description": ("Execute an instant PromQL query against Prometheus. "
                                          "Use for current metric values or state. "
                                          "Use query_prometheus_range when temporal behavior matters. "
                                          "Use valid PromQL aggregation syntax, e.g. "
                                          "sum by (uri, status) (expression)."),
                          "parameters": {"type": "object",
                                         "properties": {"query": {"type": "string",
                                                                  "description": "Valid PromQL to execute. Aggregation syntax: "
                                                                                 "sum by (label1, label2) (expression)."}},
                                         "required": ["query"]}
                         }},
            {"type": "function",
             "function": {"name": "query_prometheus_range",
             "description": ("Execute a PromQL range query over a historical or current time interval. "
                             "Use when temporal behavior or trends matter. "
                             "For counter metrics such as "
                             "http_server_requests_milliseconds_count and "
                             "http_server_requests_milliseconds_sum, use rate() or increase() "
                             "before aggregation; never aggregate metric{...}[5m] directly. "
                             "Range selectors must immediately follow the metric selector. "
                             "For aggregation, use an explicit aggregation operator such as "
                             "sum by (uri, status) (expression). "
                             "Do not write by (...) after an arithmetic expression.\n\n"
                             "Examples:\n"
                             "Valid: sum by (uri, status) (rate(metric{service_name=\"x\"}[5m]))\n"
                             "Valid: sum by (uri, status) (increase(metric{service_name=\"x\"}[5m]))\n"
                             "Invalid: sum by (uri, status) (metric{service_name=\"x\"}[5m])\n"
                             "Invalid: (expression1 - expression2) / expression1 by (uri)"),                        
                          # "description": ("Execute a PromQL range query over a historical or current time interval. "
                          #                 "Use when temporal behavior or trends matter. "
                          #                 "Use valid PromQL. "
                          #                 "For counter metrics, use rate(metric[5m]) for per-second rates "
                          #                 "or increase(metric[5m]) for totals. "
                          #                 "Range selectors must immediately follow the metric selector. "
                          #                 "For aggregation, use an explicit aggregation operator such as "
                          #                 "sum by (uri, status) (expression). "
                          #                 "Do not write by (...) after an arithmetic expression.\n\n"
                          #                 "Examples:\n"
                          #                 "Valid: sum by (uri, status) (rate(metric{service_name=\"x\"}[5m]))\n"
                          #                 "Valid: sum by (uri, status) (increase(metric{service_name=\"x\"}[5m]))\n"
                          #                 "Invalid: sum by (uri, status) (metric{service_name=\"x\"} [5m])\n"
                          #                 "Invalid: (expression1 - expression2) / expression1 by (uri)"),
                          "parameters": {"type": "object",
                                         "properties": {"query": {"type": "string",
                                                                  "description": "Valid PromQL. For counters use "
                                                                                 "rate(metric[window]) or increase(metric[window]). "
                                                                                 "Range selectors must directly follow the metric."},
                                                        "start": {"type": "number",
                                                                  "description": "Time interval start timestamp in nanoseconds."},
                                                        "end": {"type": "number",
                                                                "description": "Time interval end timestamp in nanoseconds."},
                                                        "step": {"type": "string",
                                                                 "description": ("Prometheus query resolution, "
                                                                                 "for example '30s' or '1m'.")}},
                                         "required": ["query", "start", "end"]}
                         }}]
