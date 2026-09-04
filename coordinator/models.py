from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime

class TimeRange(BaseModel):
  start: datetime
  end: datetime

class InvestigationRequest(BaseModel):
  service_name: str
  time_range: TimeRange

class AgentFinding(BaseModel):
  agent: str
  finding: str

class RCAConfidence(BaseModel):
  failure_mechanism: Literal["HIGH", "MEDIUM", "LOW"]
  underlying_trigger: Literal["HIGH", "MEDIUM", "LOW", "UNKNOWN"]

class EvidenceStep(BaseModel):
  source: Literal["PROMETHEUS", "LOKI", "TEMPO", "COORDINATOR"]
  classification: Literal["OBSERVED", "INFERRED"]
  evidence: str

class RCAResult(BaseModel):
  incident: str
  evidence_chain: list[EvidenceStep]
  correlated_evidence: list[str]
  failure_mechanism: str
  unknowns: list[str]
  confidence: RCAConfidence

class InvestigationResult(BaseModel):
  request: InvestigationRequest
  prometheus: Optional[AgentFinding] = None
  loki_tempo: Optional[AgentFinding] = None
  conclusion: Optional[RCAResult] = None

