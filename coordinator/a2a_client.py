import json
import uuid
import httpx


class A2AClient:
  def __init__(self, agent_url: str):
    self.agent_url = agent_url.rstrip("/") + "/"

  async def send_message(self, message: str) -> str:
    context_id = str(uuid.uuid4())

    payload = {"jsonrpc": "2.0",
               "id": str(uuid.uuid4()),
               "method": "SendStreamingMessage",
               "params": {"message": {"messageId": str(uuid.uuid4()),
                          "contextId": context_id,
                          "role": "ROLE_USER",
                          "parts": [{"text": message}]}}}
    headers = {"Content-Type": "application/json",
               "A2A-Version": "1.0",
               "Accept": "text/event-stream"}
    events = []

    async with httpx.AsyncClient(timeout=300.0) as client:
      async with client.stream("POST", self.agent_url, json=payload, headers=headers) as response:
        response.raise_for_status()
        async for line in response.aiter_lines():
            if not line:
              continue
            if not line.startswith("data:"):
              continue
            data = line[len("data:"):].strip()
            if not data:
              continue
            event = json.loads(data)
            if "error" in event:
              raise RuntimeError(f"A2A agent returned an error: {event['error']}")
            events.append(event)
    return self._extract_text(events)


  @staticmethod
  def _extract_text(events: list[dict]) -> str:
    for event in reversed(events):
      result = event.get("result")
      if not isinstance(result, dict):
        continue
      status_update = result.get("statusUpdate")
      if not isinstance(status_update, dict):
        continue
      status = status_update.get("status")
      if not isinstance(status, dict):
        continue
      if status.get("state") != "TASK_STATE_COMPLETED":
        continue
      message = status.get("message")
      if not isinstance(message, dict):
        continue
      parts = message.get("parts", [])
      texts = []
      for part in parts:
        if isinstance(part, dict) and part.get("text"):
          texts.append(part["text"])
      if texts:
        return "\n".join(texts)

    return "No completed agent response found."

  @staticmethod
  def _extract_message_parts(message: dict) -> list[str]:
    texts = []
    for part in message.get("parts", []):
      if not isinstance(part, dict):
        continue
      text = part.get("text")
      if text:
        texts.append(text)

    return texts
