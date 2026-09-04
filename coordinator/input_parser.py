import json

from .models import InvestigationRequest
from common.ollama_llm import OllamaLLM


class InvestigationRequestParser:
  def __init__(self):
    self.llm = OllamaLLM(model="gemma4")

  def parse(self, user_input: str) -> InvestigationRequest:
    prompt = f"""
Extract the investigation request from the user's message.

Return ONLY valid JSON matching this schema:

{{
  "service_name": "string",
  "time_range": {{
    "start": "ISO-8601 datetime",
    "end": "ISO-8601 datetime"
  }}
}}

Rules:
- Extract the service name.
- Extract the investigation start and end timestamps.
- Preserve the timestamps as ISO-8601 values.
- Do not invent missing values.
- Return JSON only.

User message:
{user_input}
"""

    response = self.llm.chat([{"role": "user",
                               "content": prompt}])
    content = self._extract_text(response)
    # If JSON comes wrapped in markdown code block, remove the wrapping.
    if content.startswith("```"):
      content = content.removeprefix("```json").removeprefix("```").strip()
      content = content.removesuffix("```").strip()

    try:
      data = json.loads(content)
    except json.JSONDecodeError as exc:
      raise ValueError("The request parser did not return valid JSON.") from exc
    return InvestigationRequest.model_validate(data)

  @staticmethod
  def _extract_text(response) -> str:
    return response.message.content