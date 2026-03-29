# Top 50 Most-Asked SRE Interview Questions (with Model Answers)

This page gives concise, high-signal answers. Practice expanding each into a 2-4 minute spoken response.

## Reliability Fundamentals

1. **What is SRE?**  
   SRE applies software engineering to operations to improve reliability, scalability, and velocity with measurable outcomes.

2. **Difference between SLI, SLO, SLA?**  
   SLI is a metric, SLO is the target on that metric, SLA is the contractual promise with consequences.

3. **What is an error budget?**  
   The acceptable failure allowance implied by an SLO; it helps balance reliability and feature velocity.

4. **Why are SLOs important?**  
   They align teams on user-impacting reliability goals and reduce subjective prioritization debates.

5. **What are the four golden signals?**  
   Latency, traffic, errors, and saturation.

6. **What is toil?**  
   Manual, repetitive, automatable operational work with little enduring value.

7. **How do you reduce alert fatigue?**  
   Remove noisy alerts, alert on symptoms not causes, tune thresholds, and enforce ownership.

8. **What makes a good postmortem?**  
   Blameless analysis, precise timeline, root causes, and tracked remediation with owners/dates.

9. **MTTR vs MTTD?**  
   MTTD is detection time; MTTR is total recovery time. Both are key incident KPIs.

10. **When to stop a release?**  
   When error budget burn or user-impact metrics exceed defined release guardrails.

## Linux + Networking

11. **How do you debug high CPU?**  
   Identify hot processes/threads, confirm user/system split, inspect workload change, then optimize bottleneck path.

12. **How do you debug memory pressure?**  
   Validate RSS/heap trends, OOM events, allocation patterns, and leaks under steady load.

13. **Difference between load average and CPU usage?**  
   Load average includes runnable and uninterruptible tasks; CPU usage is processor utilization.

14. **How to check open network connections quickly?**  
   Use `ss -s` and `ss -ltnp` to inspect summary and listening sockets.

15. **TCP vs UDP for production services?**  
   TCP for reliable ordered delivery; UDP for low-latency or loss-tolerant communication.

16. **What is DNS TTL impact?**  
   TTL controls cache lifetime and affects failover speed vs query volume.

17. **What causes packet loss in cloud networks?**  
   Congestion, faulty network paths, MTU mismatch, or host-level saturation/firewall drops.

18. **What is backpressure?**  
   A flow-control mechanism preventing producer rates from overwhelming downstream systems.

19. **What is connection pooling?**  
   Reusing connections to reduce setup overhead and improve throughput/latency consistency.

20. **How do you validate latency spikes?**  
   Compare percentiles (p95/p99), correlate with traffic, saturation, and dependency timings.

## Kubernetes + Cloud

21. **Readiness vs liveness probes?**  
   Readiness controls traffic eligibility; liveness controls container restart behavior.

22. **Why do pods go CrashLoopBackOff?**  
   Startup failures, bad config/secrets, dependency outages, or resource constraints.

23. **What causes OOMKilled in Kubernetes?**  
   Container exceeds memory limit; fix via right-sizing, leak fixes, and memory-aware tuning.

24. **How does HPA scale?**  
   It adjusts replica count based on metrics (CPU/memory/custom/external) and configured targets.

25. **What is a PodDisruptionBudget for?**  
   It protects minimum availability during voluntary disruptions.

26. **Why use requests and limits?**  
   Requests drive scheduling fairness; limits prevent noisy-neighbor resource starvation.

27. **How do you secure K8s workloads?**  
   Least privilege, network policies, image provenance, secret hygiene, and policy-as-code.

28. **Ingress vs service?**  
   Service exposes internal app endpoints; ingress manages external HTTP routing and TLS.

29. **How do you debug DNS in a cluster?**  
   Check CoreDNS health, service discovery records, and namespace-qualified lookup behavior.

30. **How to design multi-region failover?**  
   Define RTO/RPO, automate health-based traffic switching, and test failover regularly.

## System Design + Architecture

31. **How do you design for high availability?**  
   Remove single points of failure, replicate across failure domains, automate failover, and monitor health.

32. **Caching trade-offs?**  
   Better latency/cost but introduces staleness, invalidation complexity, and consistency concerns.

33. **Strong vs eventual consistency?**  
   Strong ensures immediate correctness; eventual improves availability/latency in distributed systems.

34. **How to prevent retry storms?**  
   Exponential backoff with jitter, retry budgets, and circuit breakers.

35. **What is idempotency?**  
   Multiple identical requests produce the same outcome, critical for safe retries.

36. **How to design rate limiting?**  
   Token bucket/leaky bucket with per-tenant keys and clear user feedback headers.

37. **Queue vs synchronous API?**  
   Queues decouple producers/consumers and absorb bursts; sync APIs simplify direct request/response flows.

38. **How do you choose a database?**  
   Based on access patterns, consistency requirements, scale profile, and operational complexity.

39. **What is a canary release?**  
   Progressive rollout to a small subset with guardrails before full exposure.

40. **What makes observability effective?**  
   Correlated metrics, traces, logs, and actionable alerts aligned to user-impact SLOs.

## Behavioral + Leadership

41. **Tell me about a major incident you handled.**  
   Use STAR format; focus on ownership, technical actions, communication, and measurable outcomes.

42. **How do you prioritize reliability work?**  
   Prioritize by user impact, risk probability, error-budget burn, and implementation leverage.

43. **How do you handle disagreements during incidents?**  
   Align on objective signals, assign clear roles, time-box hypotheses, and keep communication calm.

44. **How do you influence teams without authority?**  
   Build trust with data, provide paved-road solutions, and make adoption cheaper than avoidance.

45. **How do you mentor junior engineers?**  
   Pair on incidents, teach mental models, review postmortems, and gradually transfer ownership.

46. **How do you measure your effectiveness as SRE?**  
   Reliability outcomes, incident KPIs, toil reduction, and developer productivity improvements.

47. **What is your 90-day plan in a new team?**  
   Learn system topology, baseline reliability metrics, fix top risks, and establish improvement roadmap.

48. **How do you communicate risk to leadership?**  
   Use business impact language, quantified probabilities, and clear mitigation options.

49. **How do you prevent burnout in on-call teams?**  
   Reduce noise, rotate fairly, improve runbooks/automation, and maintain recovery time policies.

50. **Why should we hire you for this role?**  
   Tie your reliability wins, systems thinking, incident leadership, and collaboration skills to their needs.

---

## Company-Style Preparation Guide

### Google-style interviews

- Deep systems fundamentals
- SRE philosophy and reliability trade-offs
- Analytical incident/problem decomposition

Focus: first-principles reasoning and clarity under ambiguity.

### Amazon-style interviews

- Operational excellence + ownership
- Large-scale architecture trade-offs
- Leadership principles in incident examples

Focus: measurable impact and decisive execution.

### Meta-style interviews

- Speed with scale
- Practical debugging and production pragmatism
- Cross-functional communication and delivery velocity

Focus: strong execution plus concise communication.

### Startup-style interviews

- Breadth across infra/dev/product ops
- High ownership, fast iteration, lean tooling
- Cost-aware reliability decisions

Focus: end-to-end execution with limited resources.

---

## How to Practice This Page

1. Pick 10 questions daily.
2. Answer each in under 2 minutes.
3. Record and score with rubric from mock bank.
4. Improve weak areas next day.
