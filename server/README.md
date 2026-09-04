
# String Utils Service

A small Spring Boot 4.1.1 service built with Java 25 that exposes string operations and generates **OpenTelemetry traces, metrics and structured logs** for an LGTM observability stack.

The service can also **simulate processing latency and application failures with configurable probabilities**, making it suitable for observability and incident-investigation scenarios.

## Stack

```text
String Utils Service
        │
        ├── traces ──────────► Tempo
        ├── metrics ─────────► Prometheus
        └── JSON logs ─► Alloy ─► Loki
                           │
                           ▼
                        Grafana
```

## Build & Run

Package the application:

```bash
./mvnw package
```

Build the Docker image:

```bash
docker build -t string-utils-service .
```

Start the complete environment:

```bash
docker compose up --build
```

This launches the String Utils Service together with Grafana LGTM and Grafana Alloy.

Stop the environment with:

```bash
docker compose down
```

## HTTP API

```text
GET http://localhost:8080/api/strings/length?value=observability
GET http://localhost:8080/api/strings/reverse?value=observability
GET http://localhost:8080/api/strings/upper?value=observability
```

Example:

```json
{
  "value": "observability",
  "length": 13
}
```

Actuator endpoints:

```text
http://localhost:8080/actuator/health
http://localhost:8080/actuator/metrics
```

## Simulated Failures & Latency

The service can simulate:

* processing latency
* database failures
* external-service failures
* input-validation failures
* business-rule failures

The exception probability and average processing delay are configurable through:

```text
prob.generating.exceptions
delay.average.to.reply.in.ms
```

This enables controlled generation of telemetry patterns for observability and incident RCA.

## Observability

The service produces **traces, metrics and structured JSON logs**.

### Metrics

HTTP request duration is exposed as a histogram:

* `http_server_requests_milliseconds_bucket` — request-duration buckets
* `http_server_requests_milliseconds_sum` — total request duration
* `http_server_requests_milliseconds_count` — request count

The application also provides:

* `string_requests_total` — custom counter for successfully completed string operations

The `@Observed` instrumentation provides additional timing telemetry for string operations and simulated downstream calls.

### Traces & Logs

Traces and metrics are exported through OTLP. JSON application logs are collected by Alloy and sent to Loki.

When running with Docker Compose, the OTLP endpoint is:

```text
http://lgtm:4318
```

Telemetry is exported through:

```text
/v1/traces
/v1/metrics
```

## Services

| Service              |    Port | Purpose              |
| -------------------- | ------: | -------------------- |
| String Utils Service |  `8080` | HTTP API             |
| Grafana              |  `3000` | Observability UI     |
| Loki                 |  `3100` | Logs                 |
| Tempo                |  `3200` | Traces               |
| OTLP gRPC            |  `4317` | Telemetry ingestion  |
| OTLP HTTP            |  `4318` | Telemetry ingestion  |
| Prometheus           |  `9090` | Metrics              |
| Alloy                | `12345` | Telemetry collection |

Grafana:

```text
http://localhost:3000
```

## Telemetry Persistence

**Telemetry persistence is not configured.**

Logs, traces and metrics are ephemeral. Resetting or recreating the application/LGTM environment can **lose all previously collected telemetry**.

This setup is intended for local development, demonstrations and observability experiments rather than production-grade telemetry retention.
