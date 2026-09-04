from log_analysis_agent.tempo.client import TempoClient

def main():
  tempo = TempoClient("http://localhost:3200")
  trace_id = "f96352b68e9fb39cb3a7027da0cb6b78"
  spans = tempo.get_trace(trace_id)

  print("=== TRACE ===")
  for span in spans:
    print(f"{span['name']} "
          f"[{span['kind']}] "
          f"service={span['service']} "
          f"status={span['status']} "
          f"duration={span['duration_ns']}ns")
    if span["parent_span_id"]:
      print(f"  parent: {span['parent_span_id']}")
    if span["attributes"]:
      print(f"  attributes: {span['attributes']}")


if __name__ == "__main__":
  main()