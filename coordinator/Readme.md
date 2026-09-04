# Observability Incident Coordinator

An **A2A-based incident investigation coordinator** that turns an incident request into an evidence-based RCA by delegating investigation to specialized observability agents.

The coordinator provides a flexible northbound interface: callers can submit either a structured JSON investigation request or describe the incident in natural language.

The coordinator combines:

* **Prometheus** — metrics, request rates, error rates and endpoint behavior
* **Loki + Tempo** — application logs, distributed traces, exceptions and failing spans
* **Ollama / Gemma** — natural-language request interpretation and final RCA (Root Cause Analysis) synthesis

The goal is not simply to collect telemetry, but to **correlate independent evidence and distinguish what is observed from what is inferred**.

---

## Architecture

```text
                    User / Client 
                           | 
                           | 
            +--------------+--------------+
            |                             | 
            v                             v 
    Structured JSON               Natural language 
       /investigate               investigate/text 
            |                             |
            |                      Ollama / Gemma 
            |                             |
            +--------------+--------------+ 
                           |
                           v 
                  InvestigationRequest 
                           |
                           v
                +-------------------------+
                | Incident Coordinator    |
                |                         |
                | Parse                   |
                | Delegate                |
                | Correlate               |
                | Synthesize              |
                +------------+------------+
                             |
                   Parallel A2A delegation
                     +-------+-------+
                     |               |
                     v               v
             +-------------+   +----------------+
             | Prometheus  |   | Loki + Tempo   |
             | A2A Agent   |   | A2A Agent      |
             +------+------+   +--------+-------+
                    |                   |
                    v                   v
               Prometheus          Loki / Tempo
                  metrics          logs / traces
                     \               /
                      \             /
                       +-----+-----+
                             |
                             v
                    Evidence correlation
                             |
                             v
                    Ollama / Gemma
                             |
                             v
                       Structured RCA
```

---

## What the Coordinator Does

A typical request looks like:

```text
Investigate string-utils-service between 2026-08-31T20:45:00Z and 2026-08-31T21:00:00Z.
```

The coordinator:

1. **Parses** the natural-language request into a typed investigation request.
2. **Delegates** the same investigation window to the Prometheus and Loki/Tempo specialists.
3. **Runs specialist investigations in parallel** to reduce unnecessary latency.
4. **Correlates** their independent findings.
5. **Synthesizes** a single RCA using Ollama/Gemma.
6. **Reports confidence and unknowns** instead of inventing unsupported causes.

---

## Evidence-Based RCA

The coordinator deliberately separates telemetry from interpretation.

For example:

```text
        PROMETHEUS — OBSERVED
        5xx traffic observed for /api/strings/reverse
                |
                v
        TEMPO — OBSERVED
        A trace for /api/strings/reverse returned HTTP 500
                |
                v
        TEMPO — OBSERVED
        The "external service call" span failed
                |
                v
        TEMPO — OBSERVED
        AnyOtherProblem:
        EXTERNAL_SERVICE_FAILURE_001
                |
                v
        LOKI — OBSERVED
        An ERROR log records the same failure message
                |
                v
        COORDINATOR — INFERRED
        The external-service failure propagated to the HTTP request
```

The coordinator does **not** claim that the underlying trigger is known when the telemetry does not establish it.

Example:

```json
{
  "failure_mechanism": "An external service failure propagated to the HTTP request.",
  "confidence": {
    "failure_mechanism": "HIGH",
    "underlying_trigger": "UNKNOWN"
  }
}
```

This distinction is intentional: **high confidence in a failure mechanism does not imply high confidence in its underlying trigger.**

---

## Output

The coordinator returns a structured investigation result:

```json
{
  "incident": "...",
  "evidence_chain": [
    {
      "source": "PROMETHEUS",
      "classification": "OBSERVED",
      "evidence": "..."
    },
    {
      "source": "TEMPO",
      "classification": "OBSERVED",
      "evidence": "..."
    },
    {
      "source": "LOKI",
      "classification": "OBSERVED",
      "evidence": "..."
    },
    {
      "source": "COORDINATOR",
      "classification": "INFERRED",
      "evidence": "..."
    }
  ],
  "correlated_evidence": [],
  "failure_mechanism": "...",
  "unknowns": [],
  "confidence": {
    "failure_mechanism": "HIGH",
    "underlying_trigger": "UNKNOWN"
  }
}
```

The `evidence_chain` makes the reasoning auditable: each step identifies its source and whether it is directly observed or inferred.

---

## A2A Responsibilities

The coordinator uses A2A to keep responsibilities separated:

| Component        | Responsibility                             |
| ---------------- | ------------------------------------------ |
| Coordinator      | Orchestration, correlation, RCA synthesis  |
| Prometheus Agent | Metrics investigation using PromQL         |
| Loki/Tempo Agent | Logs and distributed-trace investigation   |
| Ollama / Gemma   | Natural-language parsing and RCA synthesis |

The coordinator does not directly query every telemetry system. It delegates to agents specialized in those domains.

---

## Investigation Contracts

The coordinator deliberately uses **different contracts northbound and southbound**.

### Northbound

Clients can provide either:

- structured JSON
- natural-language text

Both are normalized into:

```json
{
  "service_name": "string-utils-service", 
  "time_range": { 
    "start": "2026-08-31T20:45:00Z", 
    "end": "2026-08-31T21:00:00Z" 
  }
}
```

### Southbound

Specialist agents receive a strict JSON contract:

```json
{
  "service_name": "string-utils-service",
  "start": 1788209100000000000,
  "end": 1788210000000000000
}
```

This separation is intentional:

```text
      Flexible northbound
              ↓
      Typed normalization
              ↓
      Strict southbound A2A contracts
```

Natural language is useful at the boundary where humans interact with the system. Deterministic contracts are preferable between cooperating agents.

---

## API

### Structured investigation

```http
POST /investigate
Content-Type: application/json
```

```json
{
  "service_name": "string-utils-service",
  "time_range": {
    "start": "2026-08-31T20:45:00Z",
    "end": "2026-08-31T21:00:00Z"
  }
}
```

### Natural-language investigation

```http
POST /investigate/text
Content-Type: application/json
```

```json
{
  "message": "Investigate string-utils-service between 2026-08-31T20:45:00Z and 2026-08-31T21:00:00Z."
}
```


### Example Investigation Result

The coordinator delegates the investigation to both specialist agents in parallel and uses the local LLM to correlate their findings into a structured, evidence-based RCA.

A representative response is shown below. The JSON formatting has been simplified and adjusted for readability; the example preserves the structure and relevant content of the actual response.

```json
{
  "request": {
    "service_name": "string-utils-service",
    "time_range": {
      "start": "2026-08-31T20:45:00Z",
      "end": "2026-08-31T21:00:00Z"
    }
  },
  "prometheus": {
    "agent": "Prometheus Metrics Analysis Agent",
    "finding": "## CONCLUSION
    
                ### Findings
                - Observed behavior
                  The rate of 4xx and 5xx errors for all three URIs (`/api/strings/length`, `/api/strings/reverse`,
                  `/api/strings/upper`) 
                  was observed in the time window 1788209100000000000 to 1788210000000000000.
                (...)"
  },
  "loki_tempo": {
    "agent": "Loki and Tempo Analysis Agent",
    "finding": "### Incident Summary
		            The `string-utils-service` experienced multiple failures when processing requests to `/api/strings/reverse`,  
                consistently resulting in HTTP 500 errors due to a simulated external service failure. (...)

                ### Observed Facts
                *   The primary service endpoint handling the request was an HTTP GET request to 
                    `/api/strings/reverse`, associated with a status of 500.
                *   (...)

                ### Error Pattern
                (...)

                ### Trace Evidence
                (...)

                ### Root Cause (mechanism + evidence + unknowns)

                Mechanism observed: An exception of type `pt.example.stringutils.exception.AnyOtherProblem`
                was recorded.
                Evidence: The exception details show the message `EXTERNAL_SERVICE_FAILURE_001: simulated external service failure` 
                originating from `DownstreamSimulator.java` at line 29.
                Triggering condition: UNKNOWN.

                (...)"
  },
  "conclusion": {
    "incident": "HTTP 500 errors occurred for requests to /api/strings/reverse on the string-utils-service due to a simulated external service failure.",
    "evidence_chain": [
      {
        "source": "PROMETHEUS",
        "classification": "OBSERVED",
        "evidence": "The rate of errors for /api/strings/reverse was highest for the 500 status code, with a mean rate of 
        approximately 0.1123 requests/second in the window 1788209100000000000 to 1788210000000000000."
      },
      {
        "source": "TEMPO",
        "classification": "OBSERVED",
        "evidence": "The span a59b7779f032d7cc (name: \"http get /api/strings/reverse\") reported status: \"500\" and outcome: \"SERVER_ERROR\"."
      },
      (...)
      {
        "source": "LOKI",
        "classification": "OBSERVED",
        "evidence": "Logs recorded an ERROR level entry with the message: \"EXTERNAL_SERVICE_FAILURE_001: simulated external service failure\"."
      },
      {
        "source": "COORDINATOR",
        "classification": "INFERRED",
        "evidence": "The Prometheus observation of increased 500 errors for /api/strings/reverse correlates (...)"
      }
    ],
    "correlated_evidence": [
      "The Prometheus finding observed 500 errors for /api/strings/reverse. This corresponds to the Tempo evidence showing (...)"
    ],
    "failure_mechanism": "The failure mechanism is the propagation of an exception of type 
                          pt.example.stringutils.exception.AnyOtherProblem, 
                          containing the message \"EXTERNAL_SERVICE_FAILURE_001: (...))",
    "unknowns": [
      "What triggered the 'simulated external service failure' (the underlying trigger).",
      (...)
    ],
    "confidence": {
      "failure_mechanism": "HIGH",
      "underlying_trigger": "UNKNOWN"
    }
  }
}
```

The response illustrates the distinction between observed telemetry and inferred conclusions. Aggregate Prometheus evidence is kept separate from request-level Loki/Tempo evidence, while the coordinator explicitly represents uncertainty where the available telemetry cannot establish the underlying trigger.


### Agent Card

```http
GET /.well-known/agent-card.json
```

The coordinator exposes its A2A agent card for discovery.

---

## Running

The coordinator runs on:

```text
http://localhost:8003
```

The expected agent topology is:

```text
Loki/Tempo Agent     http://localhost:8001
Prometheus Agent     http://localhost:8002
Coordinator          http://localhost:8003
Ollama               local
```

Start the specialist agents first, then the coordinator.

Make sure the configured Ollama model is available locally:

```text
gemma4
```

---

## Design Principles

### Specialized agents

Each agent owns a specific observability domain rather than trying to reason over every datasource.

### Evidence over narrative

Specialist conclusions are treated as evidence, but the coordinator prefers concrete telemetry over unsupported narrative claims.

### Explicit uncertainty

Unknown causes remain unknown. The coordinator is instructed not to manufacture missing telemetry or causal explanations.

### Correlation without overclaiming

Matching service names, endpoints, status codes and time windows can support correlation, but they do not prove that two observations belong to the same request. Explicit trace/request identifiers are required for request-level correlation.

### Structured results

The RCA is returned as validated structured data rather than an unstructured block of text, making the result suitable for APIs, dashboards, or downstream automation.

---

## Why This Architecture

Traditional observability workflows require an engineer to manually move between metrics, logs and traces.

This coordinator demonstrates a different workflow:

```text
        Natural-language incident
                ↓
        Specialized investigations
                ↓
        Independent telemetry evidence
                ↓
        Cross-domain correlation
                ↓
        Evidence-based RCA
```

The value is not that an LLM can query Prometheus or Loki.

The value is that **specialized agents can investigate different telemetry domains and a coordinator can combine their evidence while explicitly preserving uncertainty.**
