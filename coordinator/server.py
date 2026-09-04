from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from coordinator.models import InvestigationRequest, InvestigationResult

from .agent import CoordinatorAgent
from .agent_card import create_agent_card


app = FastAPI(title="Observability Incident Coordinator")
agent = CoordinatorAgent()

class MessageRequest(BaseModel):
  message: str


@app.get("/.well-known/agent-card.json")
async def agent_card():
  return create_agent_card()


@app.post("/investigate", response_model=InvestigationResult)
async def investigate(request: InvestigationRequest):
  return await agent.investigate(request)


class TextInvestigationRequest(BaseModel):
    message: str


@app.post("/investigate/text", response_model=InvestigationResult)
async def investigate_text(request: TextInvestigationRequest):
  try:
    return await agent.investigate_text(request.message)
  except ValueError as exc:
    raise HTTPException(status_code=400, detail=str(exc)) from exc
