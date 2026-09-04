class MetricsAnalyzer:
  def __init__(self, prometheus_client):
    self.prometheus = prometheus_client

  def analyze(self, service_name, start, end):
    queries = {#"average_response_time_ms": (f'sum by (uri)(rate(http_server_requests_milliseconds_sum{{service_name="{service_name}"}}[5m])) / '
               #                             f'sum by (uri)(rate(http_server_requests_milliseconds_count{{service_name="{service_name}"}}[5m]))'),
               #"error_rate_percent": (f'100 * sum by (uri)(rate(http_server_requests_milliseconds_count{{service_name="{service_name}",status=~"4..|5.."}}[5m])) / '
               #                       f'sum by (uri)(rate(http_server_requests_milliseconds_count{{service_name="{service_name}"}}[5m]))'),
               #"request_rate_per_second": f'sum by (uri)(rate(http_server_requests_milliseconds_count{{service_name="{service_name}"}}[5m]))',
               "errors_by_status_per_second" : f'sum by (uri, status) (rate(http_server_requests_milliseconds_count{{service_name="{service_name}",status=~"4..|5.."}}[5m]))',
               "p95_response_time_ms": f'histogram_quantile(0.95, sum by (uri, le) (rate(http_server_requests_milliseconds_bucket{{service_name="{service_name}"}}[5m])))'}
    results = {}

    for name, query in queries.items():
      try:
        results[name] = {"query": query,
                         "result": self.prometheus.query_range(query=query, start=start, end=end, step="1m")}
      except Exception as exc:
        results[name] = {"query": query, "error": str(exc)}

    return {"service": service_name,
            "time_range": {"start": start, "end": end},
            "metrics": results}
