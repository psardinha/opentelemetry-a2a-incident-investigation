# Loki + Tempo Incident Investigation Agent

An evidence-first incident investigation agent that correlates Loki logs with Tempo traces. It discovers representative failures, reconstructs span relationships, preserves recorded exception details and returns a concise conclusion without inventing a root cause.

## What it does

For a service and nanosecond time window, the agent:

1. Finds relevant error patterns in Loki.
2. Selects a representative trace in Tempo.
3. Reconstructs the trace tree using `parent_span_id`.
4. Correlates logs, request outcomes and exception events.
5. Extracts exception type, message, exception references and source location when available.
6. Uses Ollama with Loki and Tempo investigation tools to investigate evidence-supported questions.

The result separates observed facts from interpretation. A span hierarchy shows telemetry relationships; it does not, by itself, prove causation. When telemetry does not establish the trigger, the agent reports that explicitly.


## Architecture

```text
        A2A Client
            │
            ▼
        A2A Server
            │
            ▼
        Investigation Agent
            │
            ├── Deterministic Analyzer
            │       ├── Loki
            │       └── Tempo
            │
            └── Ollama LLM
                    │
                    └── Loki / Tempo investigation tools
```


## A2A interface

The agent is exposed as a streaming A2A server with:

- Agent Card: `/.well-known/agent-card.json`
- JSON-RPC endpoint: `/`
- Streaming method: `SendStreamingMessage`
- Default address: `http://127.0.0.1:8001/`
- JSON input containing `service_name`, `start` and `end`, where `start` and `end` are Unix timestamps in nanoseconds.

Example input:

```json
{
  "service_name": "string-utils-service",
  "start": 1788209100000000000,
  "end": 1788210000000000000
}
```

The server emits progress events while discovery, LLM analysis and Loki or Tempo tool calls are running.

## Project structure

```text
Project root directory/
    ├── common/
    │   └── ollama_llm.py             # Shared Ollama adapter
    └── loki/
        ├── README.md
        ├── log_analysis_agent/
        │   ├── a2a_server.py          # A2A server and agent card
        │   ├── agent.py               # Investigation orchestration
        │   ├── analysis/
        │   │   ├── agent.py           # Evidence-constrained LLM flow
        │   │   └── analyzer.py        # Deterministic Loki/Tempo analysis
        │   ├── loki/client.py          # Loki HTTP client
        │   ├── tempo/client.py         # Tempo HTTP client
        │   ├── tools/                  # Loki and Tempo tool definitions
        │   └── test_a2a.py             # Streaming A2A client example
        ├── test_loki.py                # Direct investigation example
        ├── test_ollama_tools.py        # Ollama/tool smoke test
        └── test_tempo.py               # Tempo client example
```

The `common` directory is one level above `loki` because the Ollama adapter is shared by the Loki and metrics agents.

## Run it

Run commands from project root directory so both `common` and `loki` are importable.

Prerequisites:

- Python 3.10+
- Loki at [http://localhost:3100](http://localhost:3100)
- Tempo at [http://localhost:3200](http://localhost:3200)
- Ollama running locally with the configured `gemma4` model
- A telemetry-producing service such as `string-utils-service`

Start the A2A server:

```bash
python -m loki.log_analysis_agent.a2a_server
```

In another terminal, send the sample streaming request:

```bash
python -m loki.log_analysis_agent.test_a2a
```

For the direct investigation flow:

```bash
python -m loki.test_loki
```

Set `A2A_HOST` and `A2A_PORT` to change the server binding. Loki and Tempo URLs, the model, service name and time window are configured in the server and example scripts.

## Output discipline

The analyzer produces a compact evidence bundle containing log patterns,
trace IDs, span relationships, request outcomes and exception metadata.
The LLM reasons only within this evidence boundary.

This separation between deterministic evidence collection and model-based
investigation keeps conclusions auditable and evidence-bounded. Recorded
exception locations identify where an exception was captured, not necessarily
why it occurred. When telemetry does not establish a triggering condition,
the agent reports it explicitly as unknown.