# SRE Cheat Sheets (Rapid Revision)

Use this before interviews for quick recall.

## Linux Quick Triage

```bash
uptime
top
vmstat 1 5
iostat -xz 1 5
ss -s
df -h
free -m
dmesg | tail -n 40
```

## Kubernetes Quick Triage

```bash
kubectl get pods -A
kubectl describe pod <pod>
kubectl logs <pod> --previous
kubectl get events --sort-by=.lastTimestamp | tail -n 30
kubectl top pod -A
```

## Networking Quick Triage

```bash
dig <host>
nslookup <host>
traceroute <host>
curl -v <url>
ss -ltnp
```

## Reliability Formulas

```text
Availability % = (Total time - Downtime) / Total time * 100

Error budget = (1 - SLO) * Total requests/time window

Burn rate = observed error rate / allowed error rate
```

## Capacity Thinking

```text
Required capacity = peak QPS * avg cost per request * safety factor
Safety factor commonly starts at 1.3x to 2x depending on variance.
```

## Golden Signals

1. Latency
2. Traffic
3. Errors
4. Saturation

If you cannot explain all four for a service, observability is incomplete.

## Interview Answer Structure

Use this structure for technical questions:

1. Clarify assumptions
2. Explain current state
3. Propose stepwise approach
4. Discuss trade-offs
5. Add measurable validation plan

## Must-Know Trade-offs

- Consistency vs availability
- Throughput vs latency
- Reliability vs cost
- Fast release vs change risk
- Centralized control vs team autonomy
