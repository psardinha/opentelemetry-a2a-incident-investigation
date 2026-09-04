import asyncio
import datetime
import json

from .a2a_client import A2AClient
from .config import LOKI_TEMPO_AGENT_URL, PROMETHEUS_AGENT_URL
from .models import AgentFinding, InvestigationRequest, InvestigationResult, RCAResult
from common.ollama_llm import OllamaLLM


class IncidentOrchestrator:
  def __init__(self):
    self.prometheus = A2AClient(PROMETHEUS_AGENT_URL)
    self.loki_tempo = A2AClient(LOKI_TEMPO_AGENT_URL)
    self.llm = OllamaLLM(model="gemma4")

  async def investigate(self, request: InvestigationRequest) -> InvestigationResult:
    result = InvestigationResult(request=request)

    # 1. Build independent investigation requests
    prometheus_prompt = self._build_prometheus_prompt(request)
    loki_tempo_prompt = self._build_loki_tempo_prompt(request)

    # 2. Run specialist agents in parallel
    prometheus_response, loki_tempo_response = await asyncio.gather(self.prometheus.send_message(prometheus_prompt),
                                                                    self.loki_tempo.send_message(loki_tempo_prompt))
    result.prometheus = AgentFinding(agent="Prometheus Metrics Analysis Agent",
                                     finding=prometheus_response)
    result.loki_tempo = AgentFinding(agent="Loki and Tempo Analysis Agent",
                                     finding=loki_tempo_response)

    # 3. Synthesize findings
    result.conclusion =  await self._build_conclusion(request=request,
                                                      prometheus=prometheus_response,
                                                      loki_tempo=loki_tempo_response)
    return result


  def _build_prometheus_prompt(self, request: InvestigationRequest) -> str:
    return json.dumps({"service_name": request.service_name,
                       "start": self.to_unix_ns(request.time_range.start),
                       "end": self.to_unix_ns(request.time_range.end)})

  
  def _build_loki_tempo_prompt(self, request: InvestigationRequest) -> str:
    return json.dumps({"service_name": request.service_name,
                       "start": self.to_unix_ns(request.time_range.start),
                       "end": self.to_unix_ns(request.time_range.end)})


  async def _build_conclusion(self, request: InvestigationRequest, prometheus: str, loki_tempo: str) -> RCAResult:
    prompt = f"""
You are the incident RCA coordinator.

You have received two independent specialist investigations for the
same incident:

1. Prometheus metrics analysis
2. Loki/Tempo logs and traces analysis

Your job is to correlate their evidence and produce ONE concise,
evidence-based incident root-cause analysis.

Do not invent facts.

Distinguish clearly between:
- Observed facts
- Supported failure mechanism
- Unknowns
- Confidence
- Evidence chain

A root cause should only be considered confirmed when the available
evidence supports the causal relationship.

The metrics specialist may establish:
- when the degradation occurred
- affected endpoints
- HTTP status codes
- request/error rates
- metric trends

The Loki/Tempo specialist may establish:
- application errors
- exceptions
- trace failures
- failing spans
- downstream dependencies
- exception locations

Correlate matching:
- service
- endpoint
- time window
- HTTP status
- trace/span failures
- exceptions
- dependencies

IMPORTANT CORRELATION RULES:

- Do not assume that two observations are the same request merely
  because they share a service, endpoint, status code, or time window.
  Treat them as the same request only when a trace ID, request ID, or
  equivalent explicit correlation evidence exists.

- Do not generalize from a single trace to all failures. If Loki/Tempo
  provides evidence for one specific request, state that the evidence
  explains that observed request unless broader evidence supports a
  wider conclusion.

- Do not claim that something is the root cause merely because it is
  mentioned in one specialist's output.

- Do not use words such as "always", "consistently", or "repeatedly"
  unless the specialist evidence explicitly supports that claim.

- Do not use words such as "elevated", "increased", "spiking", or
  "degraded" unless the evidence explicitly establishes a change
  relative to a baseline.

- Prefer concrete telemetry evidence over narrative claims in a
  specialist's conclusion. If a specialist's narrative makes a stronger
  claim than its underlying evidence supports, use the weaker,
  evidence-supported interpretation.

- If the specialists report different time windows, do not treat the
  absence of evidence in one window as evidence that the event did not
  occur in another window. Explicitly note the window mismatch.

- Distinguish between the failure mechanism and the underlying trigger.
  It is valid to have HIGH confidence in a failure mechanism while the
  underlying trigger remains UNKNOWN.

- Do not invent missing logs, traces, metric values, dependencies,
  timestamps, trace IDs, request IDs, span IDs, or causal explanations.

If the evidence only proves a failure mechanism but not the underlying
trigger, explicitly say so.

IMPORTANT EVIDENCE CHAIN RULES:

The "evidence_chain" must show how the available telemetry supports
the final RCA.

Each evidence_chain item must contain:
- source
- classification
- evidence

Allowed source values:
- PROMETHEUS
- LOKI
- TEMPO
- COORDINATOR

Allowed classification values:
- OBSERVED
- INFERRED

Use "OBSERVED" only when the evidence is directly reported by the
specialist's telemetry findings.

Use "INFERRED" only when the statement is a conclusion derived from
one or more observed facts.

Do not present an inference as an observed fact.

Prometheus evidence is generally aggregate metric evidence. Do not
represent a Prometheus observation as evidence about one specific
request unless an explicit request-level correlation identifier exists.

Loki/Tempo evidence may be request-level or trace-level evidence.

If Loki/Tempo provides a specific trace ID, preserve it in the
evidence_chain when relevant.

If Loki/Tempo provides a specific span ID, preserve it in the
evidence_chain when relevant.

Do not claim that a Prometheus observation and a specific Loki/Tempo
trace represent the same request unless an explicit correlation
identifier establishes that relationship.

The evidence_chain should show progression from:
1. observed telemetry
2. observed application failure evidence
3. supported failure mechanism
4. coordinator inference, when applicable

The evidence_chain must not contain invented steps.

The evidence_chain does not need timestamps. Do not invent timestamps
when they are not provided by the specialist findings.

Return ONLY valid JSON matching this exact structure:

{{
  "incident": "Brief description of the incident.",
  "evidence_chain": [
    {{
      "source": "PROMETHEUS",
      "classification": "OBSERVED",
      "evidence": "Concrete evidence from the specialist finding."
    }},
    {{
      "source": "TEMPO",
      "classification": "OBSERVED",
      "evidence": "Concrete evidence from the specialist finding."
    }},
    {{
      "source": "LOKI",
      "classification": "OBSERVED",
      "evidence": "Concrete evidence from the specialist finding."
    }},
    {{
      "source": "COORDINATOR",
      "classification": "INFERRED",
      "evidence": "A conclusion supported by the observed evidence."
    }}
  ],
  "correlated_evidence": ["Evidence connecting the Prometheus and Loki/Tempo findings."],
  "failure_mechanism": "The strongest conclusion supported by the evidence.",
  "unknowns": ["What the telemetry does not establish."],
  "confidence": {{
    "failure_mechanism": "HIGH",
    "underlying_trigger": "UNKNOWN"
  }}
}}

Rules for the JSON response:

- "evidence_chain" must be an array of objects.
- Every evidence_chain object must contain:
  - "source"
  - "classification"
  - "evidence"

- "source" must be exactly one of:
  PROMETHEUS, LOKI, TEMPO, COORDINATOR.

- "classification" must be exactly one of:
  OBSERVED, INFERRED.

- "correlated_evidence" must be an array of strings.
- "unknowns" must be an array of strings.

- "confidence.failure_mechanism" must be exactly HIGH, MEDIUM, or LOW.

- "confidence.underlying_trigger" must be exactly HIGH, MEDIUM, LOW, or UNKNOWN.

- Do not include markdown.
- Do not include ```json.
- Do not include any text before or after the JSON.

- Be precise about the scope of the conclusion.

- If the evidence explains one specific request or endpoint but not the
  entire incident, explicitly say so.

- If the underlying trigger cannot be established, say UNKNOWN rather
  than guessing.

- The evidence_chain must not imply stronger correlation than the
  evidence supports.

PROMETHEUS FINDING
------------------
{prometheus}

LOKI / TEMPO FINDING
--------------------
{loki_tempo}

Incident metadata:
Service: {request.service_name}
Start: {request.time_range.start.isoformat()}
End: {request.time_range.end.isoformat()}
"""

    response = self.llm.chat(messages=[ {"role": "system",
                                         "content": ("You are a senior site reliability engineer "
                                                     "specializing in evidence-based incident RCA.")},
                                        { "role": "user",
                                          "content": prompt}])

    
    content = self.extract_llm_text(response)
    return RCAResult.model_validate_json(content)


  @staticmethod
  def extract_llm_text(response) -> str:
    if hasattr(response, "message"):
      message = response.message
      if hasattr(message, "content"):
        return message.content
      if isinstance(message, dict):
        return message.get("content", "")

    if isinstance(response, dict):
      message = response.get("message")
      if isinstance(message, dict):
        return message.get("content", "")
      return response.get("response", "")

    return str(response)

  @staticmethod
  def to_unix_ns(value: datetime) -> int:
    return int(value.timestamp() * 1_000_000_000)