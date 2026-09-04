# Prometheus Metrics Investigation Agent

An evidence-first A2A agent for investigating service incidents with Prometheus. It analyzes HTTP request metrics, asks one focused follow-up question through a PromQL tool and returns a concise conclusion that separates observed behavior from unsupported causes.

## What it does

For a service and time window, the agent:

1. Runs deterministic PromQL discovery queries over the requested time window.
2. Reduces time series to compact statistical evidence, e.g., sample count, minimum, maximum, mean, first value and last value, before passing it to the LLM, keeping the investigation context small while preserving key characteristics of the observed behavior.
3. Gives the evidence to an LLM with the investigation constraints.
4. Uses the Prometheus investigation tool to execute a targeted query selected by the agent.
5. Reassesses the tool result and reports findings, a cause only when directly supported and a confidence level.

The agent currently uses these Micrometer HTTP metrics:

- `http_server_requests_milliseconds_bucket`
- `http_server_requests_milliseconds_sum`
- `http_server_requests_milliseconds_count`

Relevant labels include `method`, `outcome`, `status`, `exception` and `uri`.


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
            │       └── Prometheus
            │
            └── Ollama LLM
                    │
                    └── Prometheus investigation tool
```


## A2A interface

The service exposes a streaming A2A endpoint and an agent card:

- Agent Card: `/.well-known/agent-card.json`
- JSON-RPC endpoint: `/`
- Streaming method: `SendStreamingMessage`
- Default address: `http://127.0.0.1:8002/`
- JSON input containing `service_name`, `start` and `end`, where `start` and `end` are Unix timestamps in nanoseconds.

Example input:

```json
{
  "service_name": "string-utils-service",
  "start": 1788209100000000000,
  "end": 1788210000000000000
}
```

`start` and `end` are Unix timestamps in nanoseconds. The A2A executor streams progress while discovery, LLM analysis and Prometheus tool calls run.

## Project structure

```text
Project root directory/
    ├── common/
    │   └── ollama_llm.py             # Shared Ollama adapter
    └── metrics/
        ├── README.md
        ├── test_metrics.py                 # Direct agent invocation
        └── metrics_analysis_agent/
            ├── a2a_server.py               # A2A server and agent card
            ├── agent.py                    # Investigation orchestration
            ├── analyzer.py                 # Deterministic PromQL discovery
            ├── prometheus/
            │   └── client.py               # Prometheus HTTP API client
            ├── tools/
            │   └── prometheus_tools.py     # LLM tool definitions and dispatch
            └── test_a2a.py                 # Streaming A2A client example
```

The Ollama adapter is shared by both observability agents at `common/ollama_llm.py` in the repository root.

## Run it

Run commands from project root directory so `common` and `metrics` are importable.

Prerequisites:

- Python 3.10+
- Prometheus at `http://localhost:9090`
- Ollama with the configured `gemma4` model
- A service exposing the metrics listed above
- A Python environment with the project dependencies installed

Start the A2A server:

```bash
python -m metrics.metrics_analysis_agent.a2a_server
```

In another terminal, send the sample streaming request:

```bash
python -m metrics.metrics_analysis_agent.test_a2a
```

For the direct flow:

```bash
python -m metrics.test_metrics
```

Set `A2A_HOST` and `A2A_PORT` to change the server binding. Prometheus URL, model, service name and time window are configured in the server and example scripts.

## Evidence boundary

The agent treats metric names, labels, values, timestamps and PromQL results
as telemetry. Correlation between error rate, traffic and latency does not
establish causation. An HTTP status, endpoint name, or latency pattern alone
is not proof of an implementation defect.

When the available metrics do not identify a causal mechanism, the agent
reports:

```text
Cause cannot be established from the available telemetry.
```

This keeps the A2A response useful for incident triage while making its conclusions traceable to Prometheus evidence.
