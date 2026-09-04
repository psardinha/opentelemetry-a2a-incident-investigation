from ollama import chat


def get_trace(trace_id: str) -> str:
    return f"TRACE RESULT FOR {trace_id}"


messages = [
    {
        "role": "system",
        "content": (
            "You are a tool-calling test agent. "
            "You MUST call get_trace. "
            "Do not explain what you are doing. "
            "Do not write JSON. "
            "Actually call the tool."
        ),
    },
    {
        "role": "user",
        "content": "Call get_trace for trace abc123.",
    },
]


response = chat(
    model="gemma4",
    messages=messages,
    tools=[get_trace],
    think=False,
)

print("CONTENT:")
print(repr(response.message.content))

print("\nTOOL CALLS:")
print(response.message.tool_calls)

print("\nFULL MESSAGE:")
print(response.message)