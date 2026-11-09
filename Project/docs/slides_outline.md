# Slide outline (10 slides)

1. **FairPay AI**: title, team, one-line pitch
2. **The problem**: hundreds of queries a week; real ones stuck in line; one month, several rates
3. **What we built**: rank, rebuild the pay, recommend, stop for a person
4. **Architecture**: `docs/flowchart.png`
5. **Data**: five dirty extracts, with the counts from `data_quality_report.json`
6. **Models**: three models against their baselines (`output/experiments/baseline_comparison.md`)
7. **The pay engine**: worked example split into 3 pieces, rounded once, underpaid AUD 515.07
8. **Agents and the gate**: 5 calls, interrupt, a different controller, 0 to 2 more calls
9. **Trust and ops**: role guard, figure line, audit trail, monitoring, CI, Docker
10. **Live demo, then questions**

Take every number from your own `model_metrics.json` and quality report, not from these notes.
