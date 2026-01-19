# Root Cause Analysis (RCA) Playbook — SRE-Grade

> **Use this template during incidents.** Capture facts quickly, prioritize safety, and document decisions for fast resolution and learning. Treat every entry as a working draft until the incident is closed.

---

## RCA Template (fill during the incident)

```text
Summary:
  One-line impact + duration + blast radius.

Timeline (UTC):
  - T0: Detection (who/what)
  - T+X: User impact confirmed
  - T+Y: Mitigation started
  - T+Z: Mitigation complete
  - T+…: Verification and monitoring checks

Impact:
  - Users affected (%/regions/tenants)
  - Services/components affected
  - SLO/SLA breach? (y/n)

Signals:
  - Alerts fired (names, thresholds)
  - Key metrics (latency, errors, saturation)
  - Logs/snippets (links)

Hypotheses (ranked):
  1) ...
  2) ...
  3) ...

Tests/Experiments:
  - What to run, expected vs observed, results

Mitigations:
  - Immediate: traffic shift, feature flag, rollback, scale up/down
  - Permanent (planned): config fix, code change, infra change

Decisions & Owners:
  - Decision, who approved, timestamp

Root Cause:
  - Direct cause
  - Contributing factors
  - Control gaps (missing alert, missing guardrail)

Lessons / Follow-ups:
  - Action items (owner, due date, priority)
  - Playbook updates needed?
```

---

## Prioritization Rules (SRE/Google-Style)
- **Safety first**: Stop the bleeding before root cause. Prefer rollback/traffic shift over risky fixes.
- **Stabilize service**: Protect user experience and data integrity; avoid data-destructive actions.
- **Blast radius awareness**: Prefer surgical mitigations (per-tenant, per-az) before global changes.
- **Time-bounded experiments**: Set a timer; if no improvement, roll back and reassess.
- **Single change at a time**: Avoid multiple concurrent fixes that mask the true cause.
- **Evidence over intuition**: Promote hypotheses only with data (metrics/logs/traces).
- **Repro or correlate**: Correlate with recent deploys, config changes, infra events, traffic patterns.
- **Guardrails**: Require peer ack for prod-impacting actions (db schema, firewall, auth).

---

## How to Choose Priorities (fast triage)
1) **User harm & data risk**: data loss/corruption > auth failures > availability > latency > degradation.  
2) **Breadth of impact**: multi-region > single AZ > single tenant.  
3) **Time sensitivity**: regulatory/finance windows, partner SLAs, batch deadlines.  
4) **Reversibility**: reversible mitigations first (rollback, disable feature flag, traffic split).  
5) **Detectability**: actions with clear, rapid feedback take precedence.  

---

## Scenarios & Example RCAs

### 1) API Latency Regression Post-Deploy

**Context**: p95 latency +80% in 10 minutes after release.  
**Hypotheses**: bad feature flag path, thread pool starvation, downstream 429s.  
**Tests**:
- Compare metrics pre/post deploy (latency, saturation, error rate).  
- Toggle flag off for 10% traffic; observe metrics.  
- Increase pool size temporarily; check thread rejection.  
**Mitigation**: Roll back to previous image; disable new flag.  
**Root cause**: Feature flag enabled sync call to downstream without timeout; thread pool exhausted.  
**Follow-ups**: Add timeout + circuit breaker; load test flag path; alert on queue depth.

### 2) Kafka Consumer Lag Spike

**Context**: Lag jumps to 200k after schema deployment.  
**Hypotheses**: deserialization failures causing retries; partition skew; throttling.  
**Tests**:
- `kafka-consumer-groups.sh --describe --group <g>`  
- Check consumer error logs for `UnknownMagicByte` or schema ID mismatch.  
- Verify partition assignment strategy and max.poll.interval.  
**Mitigation**: Roll back consumer build; pin schema ID; rebalance partitions.  
**Root cause**: Producer deployed with new schema without backward compatibility; consumers on older schema failed deserialization.  
**Follow-ups**: Enforce registry compatibility = BACKWARD; add pre-deploy contract tests.

### 3) Database Connection Storm

**Context**: Error rate spikes, DB CPU at 95%, connection count maxed.  
**Hypotheses**: connection pool leak, sudden traffic shift, liveness probe retry storm.  
**Tests**:
- App pool metrics vs DB connections; check liveness/readiness probe frequency.  
- DB slowlog/pg_stat_activity for autovacuum locks/long transactions.  
- Traffic routing changes (ingress/feature flag).  
**Mitigation**: Reduce pod count or pool size; apply connection limit per pod; temporarily scale DB read replicas.  
**Root cause**: New pod autoscaler rule doubled pods without reducing pool size; DB hit max connections.  
**Follow-ups**: Pool per-core sizing; admission checks for pool size; SLO alert on connection utilization.

### 4) Regional Outage / Dependency Failure

**Context**: Upstream DNS or cloud service failure in a region.  
**Hypotheses**: bad resolver, provider incident, route table change.  
**Tests**:
- `dig @resolver service.` across regions; traceroute to upstream.  
- Check status page and own synthetic probes.  
- Validate failover policies (GSLB/ingress weights).  
**Mitigation**: Shift traffic to healthy regions; disable failing upstream in routing; extend client timeouts.  
**Root cause**: External provider DNS outage; failover policy not triggered due to missing health check.  
**Follow-ups**: Add active health checks to GSLB; drill failover; set TTL caps.

---

## Quick Commands & Links to Capture Evidence

```bash
# Kubernetes rollout + events
kubectl get deploy -A --show-labels
kubectl describe pod <pod> -n <ns> | sed -n '/Events/,$p'

# Compare configs between revisions (git)
git diff HEAD~1..HEAD -- path/to/configs

# Logs with correlation IDs
kubectl logs deploy/<svc> -n <ns> | grep <request-id> | tail -50

# System health snapshot
uptime; free -m; df -h; vmstat 1 5
```

---

## Postmortem Essentials (after mitigation)
- **Timeline accuracy**: Convert all times to UTC; verify from logs/metrics.  
- **Single root cause with contributing factors**: avoid laundry lists.  
- **Action items**: owner + due date + severity; include tests/automation to prevent recurrence.  
- **Share back**: update runbooks; add checks to CI/CD (lint configs, contracts, chaos drills).  
