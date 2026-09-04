import json

from .models import InvestigationRequest, InvestigationResult
from .orchestrator import IncidentOrchestrator
from .input_parser import InvestigationRequestParser

class CoordinatorAgent:
  def __init__(self):
    self.orchestrator = IncidentOrchestrator()
    self.parser = InvestigationRequestParser()

  async def investigate(self, request: InvestigationRequest) -> InvestigationResult:
    return await self.orchestrator.investigate(request)

  async def investigate_text(self, user_input: str) -> InvestigationResult:
    request = self.parser.parse(user_input)
    return await self.investigate(request)