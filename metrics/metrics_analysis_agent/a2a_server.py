import asyncio
import json
import os

import uvicorn
from starlette.applications import Starlette

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
from a2a.types import AgentInterface, AgentCapabilities, AgentCard, AgentSkill, Message, Part,  Task, TaskStatus, TaskState

from common.ollama_llm import OllamaLLM
from metrics.metrics_analysis_agent import MetricsAnalysisAgent, MetricsAnalyzer
from metrics.metrics_analysis_agent.prometheus.client import PrometheusClient
from metrics.metrics_analysis_agent.tools.prometheus_tools import PrometheusTools

HOST = os.getenv("A2A_HOST", "127.0.0.1")
PORT = int(os.getenv("A2A_PORT", "8002"))
BASE_URL = f"http://{HOST}:{PORT}"
PROMETHEUS_URL = "http://localhost:9090"
SERVICE_NAME = "string-utils-service"
START = 1788209100000000000
END = 1788210000000000000

class MetricsAgentExecutor(AgentExecutor):
  def __init__(self, agent: MetricsAnalysisAgent):
    self.agent = agent

  async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
    # A2A input is a text message containing JSON:
    #
    # {
    #   "service_name": "...",
    #   "start": 1788209100000000000,
    #   "end": 1788210000000000000
    # }
    user_input = context.get_user_input()

    try:
      request = json.loads(user_input)
      service_name = request["service_name"]
      start = int(request["start"])
      end = int(request["end"])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
      raise ValueError("Expected JSON with service_name, start and end") from exc

    task = context.current_task

    if not task:
      task = Task(id=context.task_id,
                  context_id=context.context_id,
                  status=TaskStatus(state=TaskState.TASK_STATE_SUBMITTED),
                  history=[context.message])
      await event_queue.enqueue_event(task)

    updater = TaskUpdater(event_queue, task.id,  task.context_id)

    # Capture the A2A event loop before entering the worker thread.
    loop = asyncio.get_running_loop()

    def emit(message):
      asyncio.run_coroutine_threadsafe(updater.update_status(TaskState.TASK_STATE_WORKING, message=agent_message(message)), loop)

    await updater.update_status(TaskState.TASK_STATE_WORKING,
                                message=agent_message("Investigating Prometheus metrics..."))

    try:
      result = await asyncio.to_thread(self.agent.investigate, service_name, start, end, emit)
      answer = result["answer"]
      await updater.complete(message=agent_message(answer))
    except asyncio.CancelledError:
      await updater.cancel()
      raise
    except Exception as exc:
      await updater.update_status(TaskState.TASK_STATE_FAILED,
                                  message=agent_message(f"Metrics investigation failed: {exc}"),
                                  final=True)

  async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
    updater = TaskUpdater(event_queue, context.task_id or "",  context.context_id or "")
    await updater.cancel()


def create_agent_card() -> AgentCard:
  skill = AgentSkill(id="prometheus-investigation",
                     name="Prometheus Incident Investigation",
                     description=("Investigates service incidents using Prometheus metrics, "
                                  "performs additional PromQL queries and returns "
                                  "evidence-based findings and conclusions. "
                                  "Input must be JSON with the following fields: "
                                  "service_name (string), start (integer Unix timestamp in nanoseconds), "
                                  "and end (integer Unix timestamp in nanoseconds)."),
                     tags=["prometheus",
                           "metrics",
                           "incident-investigation",
                           "observability"],
                     examples=["Investigate the metrics for string-utils-service.",
                               "Determine whether the HTTP error rates changed during the incident.",
                               "Example of input parameters: ",
                               json.dumps({"service_name":
                                           "string-utils-service", 
                                           "start": 1788209100000000000, 
                                           "end": 1788210000000000000})])

  return AgentCard(name="Prometheus Metrics Analysis Agent",
                   description=("Investigates service incidents using Prometheus telemetry "
                                "and returns evidence-based findings and conclusions."),
                   version="1.0.0",
                   supported_interfaces=[AgentInterface(url=f"{BASE_URL}/", protocol_binding="JSONRPC", protocol_version="1.0")],
                   capabilities=AgentCapabilities(streaming=True, push_notifications=False),
                   default_input_modes=["text/plain"],
                   default_output_modes=["text/plain"],
                   skills=[skill])


def agent_message(text: str) -> Message:
  return Message(role=2,  # ROLE_AGENT
                 parts=[Part(text=text)])


def build_app(agent: MetricsAnalysisAgent) -> Starlette:
  agent_card = create_agent_card()
  handler = DefaultRequestHandler(agent_executor=MetricsAgentExecutor(agent),
                                  task_store=InMemoryTaskStore(),
                                  agent_card=agent_card)
  routes = [*create_agent_card_routes(agent_card), *create_jsonrpc_routes(handler, "/")]
  return Starlette(routes=routes)


# ----------------------------------------------------------------------
# Wire your existing dependencies here.
# ----------------------------------------------------------------------

def build_agent() -> MetricsAnalysisAgent:
  llm = OllamaLLM(model="gemma4")
  prometheus_client = PrometheusClient(base_url=PROMETHEUS_URL)
  prometheus_tools = PrometheusTools(prometheus_client)
  analyzer = MetricsAnalyzer(prometheus_client)
  return MetricsAnalysisAgent(analyzer=analyzer, llm=llm, prometheus_tools=prometheus_tools)


if __name__ == "__main__":
  agent = build_agent()
  app = build_app(agent)
  print(f"Prometheus Metrics A2A agent listening on {BASE_URL}")
  print(f"Agent Card: {BASE_URL}/.well-known/agent-card.json")
  uvicorn.run(app, host=HOST, port=PORT)
