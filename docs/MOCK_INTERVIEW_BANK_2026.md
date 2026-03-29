# Mock Interview Question Bank (SRE/Platform/Systems)

Use this bank for mock interviews. Questions are grouped by difficulty.

## Debugging and Incident Response

### L1-L2

1. A service returns 5xx after deployment. Walk through first 10 minutes.
2. CPU is normal but latency doubled. What do you check next?
3. A pod is restarting every 2 minutes. How do you isolate cause quickly?

### L3-L4

1. Multi-region outage affects only write traffic. How do you stabilize and recover?
2. Alert storm starts at midnight after scaling event. How do you reduce noise without losing safety?
3. Design an incident command process for a globally distributed team.

## Reliability and SRE Design

### L1-L2

1. Explain SLI, SLO, and SLA with examples.
2. How do you calculate error budget for 99.95% over 30 days?
3. How would you set first SLOs for a new internal API?

### L3-L4

1. What should happen when a service burns budget too fast?
2. How do you design alerting strategy to reduce false positives?
3. How would you align product and engineering using reliability goals?

## Kubernetes and Cloud

### L1-L2

1. Explain readiness vs liveness probe with practical failure case.
2. Why can autoscaling fail even when CPU is high?
3. How do you debug DNS issues inside Kubernetes?

### L3-L4

1. Design a safe multi-tenant cluster strategy for 100+ teams.
2. How do you enforce deployment guardrails without slowing development?
3. Design DR strategy with clear RTO/RPO for stateful workloads.

## System Design

### L2-L3

1. Design a URL shortener with high availability.
2. Design centralized log ingestion platform.
3. Design rate-limiting service for public APIs.

### L4

1. Design global feature flag system with low-latency reads and strong auditability.
2. Design platform for progressive delivery with auto rollback.
3. Design reliability scorecard system for all services in an organization.

## Behavioral + Leadership

1. Tell me about a severe incident you handled end-to-end.
2. When did you disagree with a release decision and what happened?
3. How did you reduce operational toil for multiple teams?
4. How do you mentor engineers during critical incidents?

## Rubric for Scoring Answers

Score each response from 1-5 across:

1. Problem framing clarity
2. Technical correctness
3. Trade-off quality
4. Operational realism
5. Communication and structure

## Mock Session Format (Recommended)

1. **5 min** prompt setup
2. **20 min** deep technical discussion
3. **10 min** follow-up edge cases
4. **10 min** feedback and improvement notes

Repeat this format consistently to improve rapidly.
