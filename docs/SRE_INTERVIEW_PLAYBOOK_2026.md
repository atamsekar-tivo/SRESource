# SRE Interview Playbook (2026)

This playbook is designed for advanced SRE, Platform, and Production Engineering interviews.
If you can explain and execute most sections here, you should perform strongly in senior rounds.

## What Companies Evaluate

1. Incident handling under ambiguity
2. Trade-off thinking (latency, reliability, cost, security)
3. Systems reasoning from first principles
4. Practical automation and observability depth
5. Ability to influence architecture and operations culture

## Core Reliability Math You Must Know

### SLI, SLO, SLA

- **SLI**: measurable signal (availability, latency, error rate)
- **SLO**: objective on SLI over a window
- **SLA**: contractual commitment, usually external

### Error Budget

For 99.9% availability in 30 days:

```text
Total minutes in 30 days = 43,200
Allowed downtime = 0.1% of 43,200 = 43.2 minutes
```

You should explain how error budget controls release velocity.

### Percentiles

Know why P50 is not enough, and why P95/P99 matter in tail-heavy systems.

## High-Value Interview Scenarios

### 1) API Latency Spike During Peak Traffic

Expected approach:

1. Confirm impact with golden signals
2. Narrow to service/region/AZ
3. Compare request volume vs saturation
4. Check recent deploy/feature flags
5. Roll back or throttle safely
6. Create follow-up action items and ownership

Useful Linux triage commands:

```bash
top
vmstat 1 5
iostat -xz 1 5
ss -s
ss -ltnp
```

### 2) Kubernetes Pods CrashLoopBackOff

Rapid diagnostic sequence:

```bash
kubectl get pods -A
kubectl describe pod <pod>
kubectl logs <pod> --previous
kubectl get events --sort-by=.lastTimestamp | tail -n 30
```

Common root causes:

- readiness/liveness misconfiguration
- missing secret/configmap
- memory OOMKill
- startup dependency unavailable

### 3) Queue Backlog Growth (Kafka/SQS/PubSub)

What interviewers expect:

- quantify arrival rate vs processing rate
- identify bottleneck (consumer CPU, downstream DB, partition skew)
- propose immediate mitigation and long-term design fix

## System Design for SRE Rounds

### Design Prompt Template

When asked to design a reliable service:

1. Define workload and SLO
2. Estimate throughput, storage, QPS, p99 targets
3. Draw critical path and failure domains
4. Add resiliency patterns:
   - retries with jitter
   - circuit breaker
   - bulkhead isolation
   - idempotency keys
5. Add observability:
   - traces
   - metrics
   - structured logs
6. Add operations:
   - runbooks
   - alerts with low noise
   - rollback strategy

### Interview-Grade Trade-off Example

**Question:** "Would you prefer active-active or active-passive?"

Strong answer:

- active-active improves failover and latency, but adds consistency and operational complexity
- active-passive is simpler and safer for some regulated systems
- choose based on RTO/RPO, data model, budget, and team maturity

## Modern Topics (2026)

### eBPF in Production

- low-overhead profiling
- syscall and network visibility
- safer than ad-hoc host debugging in many cases

### OpenTelemetry Standardization

- converged instrumentation across traces/metrics/logs
- exemplars linking metrics to traces
- tail-based sampling for cost control

### Progressive Delivery

- canary + automated rollback
- feature flags with safety guards
- release gates driven by SLO/error budget burn

### Platform Engineering

- golden paths for service onboarding
- paved-road templates for CI/CD and runtime policies
- developer experience as reliability multiplier

## Incident Communication Framework

During incident rounds, communicate with structure:

1. **What we know**
2. **What users feel**
3. **Current hypothesis**
4. **Actions running now**
5. **Next update time**

Interviewers score clarity as much as technical depth.

## 30-60-90 Day Senior SRE Plan (Sample)

### 30 days

- map services and dependencies
- baseline SLOs and alert quality
- identify top 3 operational risks

### 60 days

- reduce alert noise by 30%+
- ship reliability improvements for highest-risk service
- standardize postmortem format

### 90 days

- establish reliability roadmap with measurable outcomes
- define guardrails for deployments
- present leadership review using error-budget trends

## Final Interview Checklist

- Can explain SLOs and error budget with numbers
- Can debug Linux/K8s quickly from first principles
- Can design resilient distributed systems with trade-offs
- Can communicate crisply under incident pressure
- Can connect reliability to business impact

If you can do all five consistently, you are interview-ready for advanced SRE roles.
