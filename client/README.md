# String Utils Client

A Spring Boot 4.1.1 / Java 25 load generator for the String Utils Service.

The client continuously sends HTTP requests to the server using a configurable number of parallel worker threads. Its purpose is to create realistic application traffic so that the server and observability stack generate telemetry data for monitoring and incident investigation.

## Run

From client module directory, run:

```bash
mvn spring-boot:run -Dspring-boot.run.arguments="--threads=4 --server-url=http://localhost:8080"
```

Both options are optional:

* `--threads` — number of parallel workers; defaults to `1`.
* `--server-url` — String Utils Service URL; defaults to the `string-utils-client.server-url` property, or `http://localhost:8080` if not configured.

For example:

```properties
string-utils-client.server-url=http://localhost:8080
```

Command-line options override the configured defaults.

## Behavior

Each worker continuously and randomly invokes one of the String Utils Service endpoints:

```text
/api/strings/length
/api/strings/reverse
/api/strings/upper
```

Each request uses a randomly selected test value.

Workers continue running after HTTP errors or request failures, allowing the client to maintain continuous traffic while the server is experiencing simulated failures or latency.

The workers are shut down cleanly when the application terminates.

## Purpose in the Demo

The client acts as the **traffic generator** for the observability showcase:

```text
        String Utils Client
                │
                │ continuous HTTP traffic
                ▼
        String Utils Service
                │
                ├── logs
                ├── metrics
                └── traces
                        │
                        ▼
               Observability Stack
                        │
                        ▼
             Prometheus / Loki / Tempo
                        │
                        ▼
             A2A Investigation Agents
```

The client itself is not responsible for generating the server's observability telemetry. Its job is to generate enough application traffic for the String Utils Service and observability stack to produce useful telemetry for the investigation workflow.

## Configuration

The default server URL can be configured in `application.properties`:

```properties
string-utils-client.server-url=http://localhost:8080
```

The same value can be overridden at runtime:

```bash
--server-url=http://localhost:8080
```

The number of concurrent workers can be controlled with:

```bash
--threads=4
```
