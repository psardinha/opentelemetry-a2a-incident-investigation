from ollama import chat


class OllamaLLM:
  def __init__(self, model="gemma4"):
    self.model = model

  def chat(self, messages, tools=None):
    return chat(model=self.model, messages=messages, tools=tools, think=False)
