# Kafka Production Debugging (Scenario-Based)

> **Critical context**: Start read-only (describe, list, offsets), capture metrics before changes, and coordinate with producers/consumers on version/serialization. Avoid deleting topics/consumer groups in production without business approval.

---

## Scenario: Consumer Lag Spiking

**Symptoms**: Lag climbing, end-to-end latency growing, no recent deploy.  
**Likely causes**: Slow processing, partition imbalance, consumer session timeouts, broker throttling (quota).

```bash
# Lag per group/topic/partition
kafka-consumer-groups.sh --bootstrap-server <broker:9092> --describe --group <group>

# Check client-side metrics (Prometheus/JMX preferred)
curl -s localhost:7071/metrics | grep kafka_consumer_lag

# Rebalance to fix partition skew (Kafka >=2.4)
kafka-reassign-partitions.sh --bootstrap-server <broker:9092> \
  --execute --reassignment-json-file reassign.json

# Validate max.poll.interval.ms vs processing time (Java client)
grep max.poll.interval.ms client.properties
```

Remediations:
- Increase consumer parallelism (more instances) or partitions; ensure balanced assignment strategy (`range` vs `cooperative-sticky`).  
- Tune `max.poll.interval.ms`, `max.partition.fetch.bytes`, `fetch.max.bytes` to match payload size/latency.  
- Verify quotas: `kafka-configs.sh --bootstrap-server <broker:9092> --describe --entity-type clients`.  

---

## Scenario: Producer Errors / Timeouts

**Symptoms**: `TimeoutException`, `RecordTooLargeException`, increased retries.  
**Likely causes**: Broker throttle, batch.size too small/large, lingering DNS or TLS errors.

```bash
# Broker-side request/response latency (JMX/metrics recommended)
curl -s localhost:7071/metrics | grep kafka_network_RequestMetrics

# Check max message size (broker + topic)
kafka-configs.sh --bootstrap-server <broker:9092> --describe --entity-type topics --entity-name <topic> \
  | grep max.message.bytes
kafka-configs.sh --bootstrap-server <broker:9092> --describe --entity-type brokers \
  | grep message.max.bytes

# Client config sanity (Java)
grep -E "compression.type|max.in.flight.requests.per.connection|linger.ms|batch.size|acks" producer.properties
```

Remediations:
- Align `message.max.bytes` (broker) and `max.request.size` (producer).  
- For high throughput: use `acks=all`, `linger.ms` 5–50ms, `batch.size` 64–256KB, `compression.type=zstd`.  
- Limit in-flight: `max.in.flight.requests.per.connection=1` for ordering; higher for throughput with idempotence.  

---

## Scenario: Unclean Leader Elections / ISR Shrink

**Symptoms**: Frequent leadership changes, ISR < replication factor, data loss risk.  
**Likely causes**: Broker flaps, slow disks/network, under-replicated partitions.

```bash
# Under-replicated partitions
kafka-topics.sh --bootstrap-server <broker:9092> --describe | grep "UnderReplicatedPartitions"

# Controller log for elections
kubectl -n kafka logs kafka-0 | grep -i "Leader election"

# Check disk and network on brokers
iostat -xz 1 5
ss -Htn state established '( sport = :9092 )'
```

Remediations:
- Ensure `unclean.leader.election.enable=false` for critical topics.  
- Add brokers or move hot partitions: `kafka-reassign-partitions.sh ... --generate`.  
- Verify broker GC (JVM) and heap sizing; upgrade storage performance if needed.  

---

## Scenario: Schema Registry / Serialization Failures

**Symptoms**: `UnknownMagicByte`, schema evolution errors, consumer deserialization failures.  
**Likely causes**: Incompatible schema changes, subject compatibility mis-set, client not configured for registry.

```bash
# Subject compatibility
curl -s http://schema-registry:8081/config/<subject>

# Latest schema
curl -s http://schema-registry:8081/subjects/<subject>/versions/latest | jq .

# Consumer errors (Avro/JSON schema)
kubectl logs deploy/consumer -c app | grep -i "deserial"
```

Remediations:
- Enforce `BACKWARD` or `FULL` compatibility; avoid `NONE` in prod.  
- Ensure clients set `value.serializer`/`key.serializer` aligned with registry; pin schema IDs if needed for rollbacks.  

---

## Scenario: Topic Explosion / Quota Pressure

**Symptoms**: Controller overload, slow metadata responses, storage pressure.  
**Likely causes**: Many tiny topics/partitions, runaway tenants, unbounded retention.

```bash
# Topic and partition counts
kafka-topics.sh --bootstrap-server <broker:9092> --list | wc -l
kafka-topics.sh --bootstrap-server <broker:9092> --describe | wc -l

# Per-topic retention
kafka-configs.sh --bootstrap-server <broker:9092> --describe --entity-type topics | grep retention

# Disk usage per broker
du -sh /var/lib/kafka/data/* | head
```

Remediations:
- Cap partitions per broker (rule of thumb: <= 4000 per broker, adjust by hardware).  
- Apply defaults: `retention.ms`, `retention.bytes`, and compaction where applicable.  
- Use templates for topic creation; gate via platform API.  

---

## Incident Checklist (Keep Handy)
- Capture broker/controller logs before restart.  
- Snapshot metrics: under-replicated partitions, request latency, GC, disk I/O.  
- Validate client versions and configs (acks, retries, idempotence, compression).  
- Confirm network path (MTU, DNS, TLS cert validity).  
- Ensure `auto.create.topics.enable=false` in production clusters.  

---

## Quick Client Sanity Snippet (Python, confluent-kafka)

```python
from confluent_kafka import Producer, Consumer

conf = {
    "bootstrap.servers": "kafka-1:9092,kafka-2:9092",
    "enable.idempotence": True,
    "retries": 5,
    "linger.ms": 20,
    "batch.num.messages": 1000,
}

producer = Producer(conf)
producer.produce("health", key="ping", value="pong")
producer.flush(5)

consumer = Consumer({
    **conf,
    "group.id": "debug",
    "auto.offset.reset": "latest",
})
consumer.subscribe(["health"])
msg = consumer.poll(2)
print(msg.value())
consumer.close()
```
