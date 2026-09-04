import json

from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill
from .config import BASE_URL


def create_agent_card() -> AgentCard:
  skill = AgentSkill(id="incident-coordination",
                     name="Multi-Signal Incident Investigation",
                  #    description=("Coordinates service incident investigations across specialized "
                  #                 "observability agents. Delegates metric analysis to a Prometheus "
                  #                 "agent and log and distributed-trace analysis to a Loki and Tempo "
                  #                 "agent, correlates their findings and returns a coherent, "
                  #                 "evidence-based incident analysis and conclusion. "
                  #                 "The investigation request contains a service name and an ISO-8601 "
                  #                 "time range defining the temporal interval of analysis."),
description=( "Coordinates service incident investigations across specialized " "observability agents. Delegates metric analysis to a Prometheus " "agent and log and distributed-trace analysis to a Loki and Tempo " "agent, correlates their findings and returns a coherent, " "evidence-based incident analysis and conclusion. " "The coordinator accepts a natural-language investigation request " "identifying a service and an ISO-8601 time range defining the " "temporal interval of analysis." ),                                  
                    tags=["incident-investigation",
                          "observability",
                          "coordination",
                          "prometheus",
                          "loki",
                          "tempo",
                          "metrics",
                          "logs",
                          "traces",
                          "root-cause-analysis"],
                    examples=["Investigate the incident affecting string-utils-service.",
                              ("Investigate string-utils-service and determine the root "
                               "cause using metrics, logs and traces."),
                              ("Correlate Prometheus metrics with Loki logs and Tempo "
                               "traces to determine why the service experienced errors."),
                              ("Determine whether the incident was caused by the service "
                               "itself or by a downstream dependency."),
                              ("Example of input parameters: " +
                               json.dumps({"service_name": "string-utils-service",
                                           "time_range": {"start": "2026-08-31T20:45:00Z",
                                                          "end": "2026-08-31T21:00:00Z"}}))])

  return AgentCard(name="Observability Incident Coordinator",
                   description=("Coordinates multi-signal service incident investigations by "
                                "delegating work to specialized Prometheus and Loki/Tempo agents. "
                                "Correlates metrics, logs and distributed traces to identify "
                                "incident impact, contributing factors and likely root cause, "
                                "and returns a coherent evidence-based conclusion."),
                   version="1.0.0",
                   supported_interfaces=[AgentInterface(url=f"{BASE_URL}/",
                                                        protocol_binding="JSONRPC",
                                                        protocol_version="1.0")],
                   capabilities=AgentCapabilities(streaming=True, push_notifications=False),
                   default_input_modes=["application/json"],
                   default_output_modes=["application/json"],
                   skills=[skill])