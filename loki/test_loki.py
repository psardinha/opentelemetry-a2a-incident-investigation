from common.ollama_llm import OllamaLLM
from loki.log_analysis_agent.loki.client import LokiClient
from loki.log_analysis_agent.tempo.client import TempoClient
from loki.log_analysis_agent.analysis.analyzer import LogAnalyzer
from loki.log_analysis_agent.analysis.agent import LogAnalysisAgent
from loki.log_analysis_agent.tools.loki_tools import LokiTools
from loki.log_analysis_agent.tools.tempo_tools import TempoTools

LOKI_URL = "http://localhost:3100"
TEMPO_URL = "http://localhost:3200"

def main():
  loki = LokiClient(LOKI_URL)
  tempo = TempoClient(TEMPO_URL)
  analyzer = LogAnalyzer(loki, tempo)

  # Logs are around 2026-08-26 23:07:40 UTC
  end_ns = 1788210000000000000
  start_ns = 1788209100000000000

  loki_tools = LokiTools(loki)
  tempo_tools = TempoTools(tempo)
  llm = OllamaLLM(model="gemma4")
  agent = LogAnalysisAgent(analyzer=analyzer, llm=llm, loki_tools=loki_tools, tempo_tools=tempo_tools)
  result = agent.investigate(service_name="string-utils-service", start_ns=start_ns, end_ns=end_ns)
  print("\n=== FINAL ANSWER ===")
  print(result["answer"]) 
  print("\n=== END OF FINAL ANSWER ===")

if __name__ == "__main__":
  main()
