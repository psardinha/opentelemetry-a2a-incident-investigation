import json
import uuid
import requests


url = "http://127.0.0.1:8001/"

context_id = str(uuid.uuid4())

payload = {
    "jsonrpc": "2.0",
    "id": str(uuid.uuid4()),
    "method": "SendStreamingMessage",
    "params": {
        "message": {
            "messageId": str(uuid.uuid4()),
            "contextId": context_id,
            "role": "ROLE_USER",
            "parts": [
                {
                    "text": json.dumps({
                        "service_name": "string-utils-service",
                        "start": 1788209100000000000,
                        "end": 1788210000000000000
                    })
                }
            ]
        }
    }
}


with requests.post(url,
                   json=payload,
                   headers={"Content-Type": "application/json",
                            "A2A-Version": "1.0",
                            "Accept": "text/event-stream"},
                   stream=True) as response:
  print("HTTP:", response.status_code)
  response.raise_for_status()

  for line in response.iter_lines(decode_unicode=True):
    if not line:
      continue
    if line.startswith("data:"):
      data = line[len("data:"):].strip()
      event = json.loads(data)

      print("\n=== A2A EVENT ===")
      print(json.dumps(event, indent=2))
