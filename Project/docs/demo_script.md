# Demo script (about 8 minutes)

Open two browser windows on http://localhost:8080. Keep the API docs (http://localhost:8081/docs) in a third tab.

1. **The problem (1 min).** One sentence: hundreds of pay queries a week, the real ones are stuck in the line, and one month can need several rates.
2. **Query queue, as `daniel` (Payroll Analyst) (1 min).** Point at the counts along the top and that the list is sorted by money at stake. Filter to *Overpaid* to show overpayments are corrected too.
3. **Query detail, `PQR-SYD-0041927` (2 min).** *Pay owed* tab: three pieces, the traineeship ending on 09 Jan, a rate rise on 18 Jan, rounded once. Show the schedules it read and PC1 broken. Then the *Notes and models* tab.
4. **Assess (1 min).** Type a request and start it. While it runs: five agents, one call each, and none of them calculates.
5. **Decision queue, as `daniel` (20 s).** The analyst can't see the page. Optional: call the decision endpoint in `/docs` to show the 403.
6. **Decision, as `olivia` (Remediation Controller) in the second window (1 min).** Choose *Correct and compensate*. Show the settled amount (difference plus PC1), the letter and the statement.
7. **Audit trail (1 min).** Calls made 7 against 7 expected, latency per agent, who decided and why.
8. **Chat, as `hannah` (HR Service Desk Agent) (1 min).** Ask a rate question, which is answered with its source. Ask "where is PQR-SYD-0041927?": she hears the status, never a figure. Ask about the weather: refused.
9. **Close (30 s).** Models give facts, code does the maths, AI writes the words, a person decides.

Backup: if Gemini is down, restart the service with `FAIRPAY_OFFLINE_LLM=1` and say so.
