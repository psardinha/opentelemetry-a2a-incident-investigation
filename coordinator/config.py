import os

# Coordinator itself
BASE_URL = os.getenv("COORDINATOR_BASE_URL", "http://127.0.0.1:8003")

# Specialist A2A agents
PROMETHEUS_AGENT_URL = os.getenv("PROMETHEUS_AGENT_URL", "http://127.0.0.1:8002")

LOKI_TEMPO_AGENT_URL = os.getenv("LOKI_TEMPO_AGENT_URL", "http://127.0.0.1:8001")