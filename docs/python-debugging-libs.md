# Python Libraries for SRE/DevOps Automation (FAANG-Level)

> **Use case**: Rapidly debug, automate, and observe infrastructure with production-safe patterns (timeouts, retries, auth, structured logs, metrics).

---

## Fast Reference

| Library | Primary Uses | Example |
| --- | --- | --- |
| `httpx` | HTTP APIs with timeouts/retries/HTTP2 | [snippet](#httpx-prod-safe-http-client) |
| `boto3` | AWS automation (EC2, S3, IAM, STS) | [snippet](#boto3-aws-automation) |
| `kubernetes` | Cluster CRUD, logs, exec, events | [snippet](#kubernetes-api-client) |
| `paramiko` + `fabric` | SSH automation with sudo, file push/pull | [snippet](#paramiko--fabric-ssh-automation) |
| `aiohttp` + `asyncio` | Concurrent I/O for fleet checks | [snippet](#aiohttp--asyncio-concurrent-health-checks) |
| `tenacity` | Resilient retries with backoff/jitter | [snippet](#tenacity-retries) |
| `psutil` | Host/process metrics (CPU, mem, I/O, fds) | [snippet](#psutil-host--process-telemetry) |
| `pexpect` | Automate interactive CLIs (kubectl, mysql) | [snippet](#pexpect-automate-interactive-clis) |
| `dnspython` | DNS diag (A/AAAA/SRV/CAA, tracing) | [snippet](#dnspython-dns-debug) |
| `prometheus_client` | Expose metrics for scripts/agents | [snippet](#prometheus_client-exporter) |
| `typer` | Typed CLIs (arg parsing + help) | [snippet](#typer-production-cli) |
| `pydantic` | Config validation from env/JSON | [snippet](#pydantic-validated-config) |
| `rich` | Structured logs/tables for operators | [snippet](#rich-operator-output) |

---

## httpx (Prod-Safe HTTP Client)

```python
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

@retry(
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=0.2, max=2),
    retry=retry_if_exception_type(httpx.HTTPError),
)
def get_json(url: str) -> dict:
    with httpx.Client(timeout=httpx.Timeout(2.0, read=3.0), http2=True) as client:
        r = client.get(url, follow_redirects=True)
        r.raise_for_status()
        return r.json()

resp = get_json("https://status.example.com/health")
print(resp)
```

---

## boto3 (AWS Automation)

```python
import boto3
from botocore.config import Config

cfg = Config(retries={"max_attempts": 5, "mode": "adaptive"}, region_name="us-west-2")
ec2 = boto3.client("ec2", config=cfg)

resp = ec2.describe_instances(
    Filters=[{"Name": "tag:Role", "Values": ["frontend"]}, {"Name": "instance-state-name", "Values": ["running"]}]
)
instances = [i["InstanceId"] for r in resp["Reservations"] for i in r["Instances"]]
print("Running:", instances)
```

---

## kubernetes API client

```python
from kubernetes import client, config

config.load_kube_config()
core = client.CoreV1Api()

pods = core.list_namespaced_pod("default", label_selector="app=sresource").items
for pod in pods:
    print(pod.metadata.name, pod.status.phase)

log = core.read_namespaced_pod_log(pod.metadata.name, "default", tail_lines=50)
print("--- tail ---")
print(log)
```

---

## paramiko + fabric (SSH Automation)

```python
from fabric import Connection

hosts = ["web1", "web2"]
for host in hosts:
    with Connection(host=host, user="ops", connect_timeout=5) as c:
        c.run("sudo systemctl status nginx --no-pager", hide=False)
        c.put("site.conf", "/tmp/site.conf")
        c.sudo("mv /tmp/site.conf /etc/nginx/conf.d/site.conf && systemctl reload nginx")
```

---

## aiohttp + asyncio (Concurrent Health Checks)

```python
import asyncio
import aiohttp

services = ["https://svc-a/healthz", "https://svc-b/healthz"]

async def check(url):
    timeout = aiohttp.ClientTimeout(total=3)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url, ssl=False) as resp:
            body = await resp.text()
            return url, resp.status, body[:120]

async def main():
    results = await asyncio.gather(*(check(u) for u in services), return_exceptions=True)
    for r in results:
        print(r)

asyncio.run(main())
```

---

## tenacity (Retries)

```python
from tenacity import retry, wait_exponential, stop_after_attempt

@retry(wait=wait_exponential(multiplier=0.1, max=1.5), stop=stop_after_attempt(5))
def flaky():
    ...
```

---

## psutil (Host & Process Telemetry)

```python
import psutil

print("CPU%", psutil.cpu_percent(interval=1))
print("Mem", psutil.virtual_memory())

for p in psutil.process_iter(["pid", "name", "cpu_percent", "num_fds"]):
    if p.info["cpu_percent"] > 50:
        print(p.info)
```

---

## pexpect (Automate Interactive CLIs)

```python
import pexpect

child = pexpect.spawn("ssh ops@db1")
child.expect("password:")
child.sendline("REDACTED")
child.expect(r"\$ ")
child.sendline("mysql -e 'SHOW PROCESSLIST;'")
child.expect(r"\$ ")
print(child.before.decode())
child.sendline("exit")
```

---

## dnspython (DNS Debug)

```python
import dns.resolver

resolver = dns.resolver.Resolver()
resolver.timeout = 1
resolver.lifetime = 2

for qtype in ["A", "AAAA", "CAA", "SRV", "TXT"]:
    try:
        answers = resolver.resolve("api.example.com", qtype)
        print(qtype, [r.to_text() for r in answers])
    except Exception as e:
        print(qtype, "error", e)
```

---

## prometheus_client (Exporter)

```python
from prometheus_client import start_http_server, Gauge
import time

queue_depth = Gauge("job_queue_depth", "Jobs waiting", ["queue"])

if __name__ == "__main__":
    start_http_server(9100)
    while True:
        queue_depth.labels("ingest").set(42)
        time.sleep(5)
```

---

## typer (Production CLI)

```python
import typer
from rich.console import Console

app = typer.Typer()
log = Console().log

@app.command()
def logs(namespace: str = "default"):
    log(f"Fetching logs from {namespace}")
    # call kubernetes client here

if __name__ == "__main__":
    app()
```

---

## pydantic (Validated Config)

```python
from pydantic import BaseModel, AnyUrl, Field
import os, json

class Settings(BaseModel):
    api_url: AnyUrl
    timeout: float = Field(ge=0.1, le=30)
    kubeconfig: str

data = json.loads(os.environ["APP_CONFIG"])
cfg = Settings(**data)
print(cfg)
```

---

## rich (Operator Output)

```python
from rich.table import Table
from rich.console import Console

table = Table(title="Service Health")
table.add_column("Service")
table.add_column("Status")
table.add_column("Latency (ms)", justify="right")

table.add_row("auth", "OK", "42")
table.add_row("payments", "WARN", "210")

Console().print(table)
```

---

### FAANG-Level Practices (apply across libraries)
- **Timeouts + retries**: never call a network API without both (httpx/boto3/k8s client config).  
- **Structured logging + redaction**: use `rich` or `json` logs; never print secrets.  
- **Auth profiles**: support AWS/GCP workload identity, kube in-cluster config, and env overrides.  
- **Backpressure and limits**: cap concurrency (`asyncio.Semaphore`), rate-limit AWS/k8s calls.  
- **Idempotency**: design operations to be safe on retry; use request IDs.  
- **Observability**: emit Prometheus metrics and traces (e.g., `opentelemetry` if needed).  
- **Validation**: validate configs with `pydantic`; fail fast on bad inputs.  
- **Security**: prefer least-privilege IAM/service accounts; ssh via bastions; avoid long-lived keys.  
