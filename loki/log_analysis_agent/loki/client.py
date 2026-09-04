import requests

class LokiClient:
  def __init__(self, base_url: str):
    self.base_url = base_url.rstrip("/")

  def query_range(self, 
                  service_name: str, 
                  start_ns: int, end_ns: int, 
                  trace_id: str | None = None, 
                  span_id: str | None = None,
                  limit: int = 1000,
                  exception_type=None):
    query = f'{{service_name="{service_name}"}}'
    if trace_id or exception_type:
      query += " | json"
    if trace_id:
      query += f' | traceId="{trace_id}"'
    if span_id:
      query += f' | spanId="{span_id}"'      
    if exception_type:
      query += f' | exceptionType="{exception_type}"'      
    print("[LOKI QUERY]", query)
    response = requests.get(f"{self.base_url}/loki/api/v1/query_range",
                            params={"query": query,
                                    "start": start_ns,
                                    "end": end_ns,
                                    "limit": limit,
                                    "direction": "forward"},
                            timeout=10)
    response.raise_for_status()
    data = response.json()
    if data.get("status") != "success":
      raise RuntimeError(f"Loki query failed: {data}")
    return data["data"]["result"]