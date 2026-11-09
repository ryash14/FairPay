"""Print the monitoring snapshot and exit non-zero when a high-severity alert is open.

    python -m ops.monitor            # human-readable
    python -m ops.monitor --json     # for scripts and CI
"""
import argparse
import json
import sys

from ops.monitoring import collect_monitoring_snapshot


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    arguments = parser.parse_args()
    snapshot = collect_monitoring_snapshot()
    if arguments.json:
        print(json.dumps(snapshot, indent=2))
    else:
        print(f"FairPay AI monitoring · {snapshot['generated_at']}")
        print(f"  runs by status        {snapshot['runs_by_status']}")
        print(f"  assessments by status {snapshot['assessments_by_status']}")
        print(f"  decisions             {snapshot['decisions_by_outcome']}")
        print(f"  language model calls  {snapshot['llm_calls']} (p50 {snapshot['latency_ms']['p50']} ms, "
              f"p95 {snapshot['latency_ms']['p95']} ms)")
        chat = snapshot["chat"]
        print(f"  chat                  {chat['questions']} questions, {chat['refused']} refused "
              f"({chat['refusal_rate']:.0%})")
        if snapshot["alerts"]:
            print("  ALERTS")
            for alert in snapshot["alerts"]:
                print(f"    [{alert['severity']}] {alert['run_id']}: {alert['alert']}")
        else:
            print("  no alerts")
    return 1 if any(alert["severity"] == "high" for alert in snapshot["alerts"]) else 0


if __name__ == "__main__":
    sys.exit(main())
