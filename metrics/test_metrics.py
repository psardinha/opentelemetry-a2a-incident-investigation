from common.ollama_llm import OllamaLLM
from metrics.metrics_analysis_agent import MetricsAnalysisAgent, MetricsAnalyzer
from metrics.metrics_analysis_agent.prometheus.client import PrometheusClient
from metrics.metrics_analysis_agent.tools.prometheus_tools import PrometheusTools

PROMETHEUS_URL = "http://localhost:9090"
SERVICE_NAME = "string-utils-service"
START = 1788209100000000000
END = 1788210000000000000

llm = OllamaLLM(model="gemma4")
prometheus_client = PrometheusClient(base_url=PROMETHEUS_URL)
prometheus_tools = PrometheusTools(prometheus_client)
analyzer = MetricsAnalyzer(prometheus_client)
agent = MetricsAnalysisAgent(analyzer=analyzer, llm=llm, prometheus_tools=prometheus_tools)

result = agent.investigate(service_name=SERVICE_NAME, start=START, end=END)

print("\n=== RESULT ===")
print(result["answer"])