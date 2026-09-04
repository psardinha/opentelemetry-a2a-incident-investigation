class TempoTools:
  def __init__(self, tempo_client):
    self.tempo = tempo_client

  def get_trace(self, trace_id):
    return self.tempo.get_trace(trace_id)

  @staticmethod
  def definitions():
    return [{"type": "function",
             "function": {"name": "get_trace",
                          "description": "Retrieve the complete Tempo trace for a trace ID.",
                          "parameters": {"type": "object",
                                         "properties": {"trace_id": {"type": "string"}},
                                         "required": ["trace_id"]}
                         }}]  