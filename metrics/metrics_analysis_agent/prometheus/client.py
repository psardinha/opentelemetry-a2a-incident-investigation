import requests


class PrometheusClient:
  def __init__(self, base_url, timeout=10):
    self.base_url = base_url.rstrip("/")
    self.timeout = timeout

  def query(self, query):
    response = requests.get(f"{self.base_url}/api/v1/query", params={"query": query}, timeout=self.timeout)
    response.raise_for_status()
    payload = response.json()
    if payload.get("status") != "success":
      raise RuntimeError(payload)

    
    import json
    print(f"Qry {query}::")
    print(json.dumps(payload["data"]["result"], indent=2))

    return payload["data"]["result"]

  def query_range(self, query, start, end, step="30s"):
    response = requests.get(f"{self.base_url}/api/v1/query_range",
                            params={"query": query,
                                    "start": start/1000000000,
                                    "end": end/1000000000,
                                    "step": step},
                            timeout=self.timeout)
    response.raise_for_status()
    payload = response.json()
    if payload.get("status") != "success":
      raise RuntimeError(payload)
    return payload["data"]["result"]
