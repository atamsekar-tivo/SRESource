# Kubernetes Production Debugging Commands

> **Critical Context**: Always diagnose issues in non-production environments first. Use read-only commands initially.

---

## Scenario: Diagnosing `Pending` Pod

**Prerequisites**: Pod exists but hasn't been scheduled to any node  
**Common Causes**: Insufficient resources, node selector mismatch, PVC unavailable, admission controller rejection

```bash
# STEP 1: Get detailed pod information
kubectl describe pod <podname> -n <namespace>
# Shows: Events section reveals exact reason (Insufficient memory, No nodes match selector, etc.)
# WARNING: Timestamps may be misleading; check node resources independently

# STEP 2: Check full pod specification
kubectl get pod <podname> -n <namespace> -o yaml
# Look for: nodeSelector, affinity, tolerations, resource requests/limits

# STEP 3: View recent cluster events
kubectl get events -n <namespace> --sort-by='.lastTimestamp' | tail -20
# CAVEAT: Events are cluster-wide and may be in different namespaces; check time correlation

# STEP 4: Verify node resource availability
kubectl top nodes  # Real-time resource usage
kubectl get nodes -o json | jq '.items[] | {name: .metadata.name, allocatable: .status.allocatable}'

# STEP 5: Check for node selector constraints
kubectl get nodes --show-labels | grep -E '<label-key>'
# PREREQUISITE: Know which labels pod is looking for

# STEP 6: Verify PVC status (if applicable)
kubectl get pvc -n <namespace> -o wide
kubectl describe pvc <pvc-name> -n <namespace>
# POST-REQ: If PVC is pending, diagnose storage separately

# STEP 7: Check if pod has node affinity constraints
kubectl get pod <podname> -n <namespace> -o jsonpath='{.spec.affinity}' | jq .

# STEP 8: Examine resource quotas and limits
kubectl describe resourcequota -n <namespace>
kubectl describe limits -n <namespace>

# ADVANCED: Check scheduler logs
kubectl logs -n kube-system -l component=kube-scheduler --tail=100
# WARNING: High verbosity; may need to filter with grep
```

**Commands to NEVER use in production**:
```bash
# ❌ NEVER: kubectl delete pod <podname> --force --grace-period=0
#    Causes ungraceful termination; data loss and connection issues
# ❌ NEVER: kubectl patch pod to manually change phase
#    Corrupts cluster state permanently
```

---

## Scenario: Diagnosing `CrashLoopBackOff` Pod

**Prerequisites**: Pod restarts repeatedly with non-zero exit code  
**Common Causes**: Application crash, missing dependencies, configuration error, resource limits too low

```bash
# STEP 1: Get container restart information
kubectl describe pod <podname> -n <namespace>
# Look for: Last State, Restart Count, Reason (CrashLoopBackOff), Exit Code

# STEP 2: Examine application logs from current run
kubectl logs <podname> -n <namespace> --tail=100
# Shows: Most recent logs before crash

# STEP 3: Examine logs from previous crash (critical!)
kubectl logs <podname> -n <namespace> --previous --tail=100
# CAVEAT: Only available if container has restarted; check Restart Count > 0
# WARNING: Multiple containers? Specify with -c <container-name>

# STEP 4: Get full pod YAML to check resource limits
kubectl get pod <podname> -n <namespace> -o yaml | jq '.spec.containers[] | {name, resources}'

# STEP 5: Check for OOM kills specifically
kubectl get pod <podname> -n <namespace> -o json | jq '.status.containerStatuses[].state.waiting.reason'
# POST-REQ: If "CrashLoopBackOff" with OOMKilled, increase memory limits

# STEP 6: Stream logs in real-time
kubectl logs -f <podname> -n <namespace>
# PREREQUISITE: Pod must be running; may need to pause backoff temporarily
# CAVEAT: Only shows current run's logs

# STEP 7: Get detailed container status
kubectl get pod <podname> -n <namespace> -o json | jq '.status.containerStatuses'

# STEP 8: Check for liveness/readiness probe failures
kubectl get pod <podname> -n <namespace> -o jsonpath='{.spec.containers[*].livenessProbe}'
kubectl get pod <podname> -n <namespace> -o jsonpath='{.spec.containers[*].readinessProbe}'
```

**Diagnostic checklist**:
```bash
# Verify container image exists and is accessible
kubectl describe pod <podname> -n <namespace> | grep -A 5 "Image:"

# Check init containers (may fail silently)
kubectl get pod <podname> -n <namespace> -o jsonpath='{.spec.initContainers}' | jq .

# Verify environment variables are set
kubectl get pod <podname> -n <namespace> -o jsonpath='{.spec.containers[].env}' | jq .
```

**Commands to NEVER use in production**:
```bash
# ❌ NEVER: kubectl exec <podname> -- rm -rf / (or similar destructive commands)
# ❌ NEVER: kubectl set image without testing in staging first
```

---

## Scenario: Diagnosing `ImagePullBackOff`

**Prerequisites**: Pod unable to pull container image  
**Common Causes**: Image doesn't exist, incorrect image tag, registry credentials missing, network isolation

```bash
# STEP 1: Verify image name and tag
kubectl describe pod <podname> -n <namespace> | grep -A 3 "Image:"
# Check for typos, incorrect registry URL, or non-existent tags

# STEP 2: Check image pull secret
kubectl get pod <podname> -n <namespace> -o jsonpath='{.spec.imagePullSecrets}' | jq .
kubectl get secret -n <namespace> | grep -i docker

# STEP 3: Verify secret is correctly formatted
kubectl get secret <secret-name> -n <namespace> -o yaml | jq '.data.".dockerconfigjson"' | base64 -d | jq .

# STEP 4: Test registry connectivity from a utility pod
kubectl run debug-image-pull --image=curlimages/curl -n <namespace> -- sleep 3600
kubectl exec -it debug-image-pull -n <namespace> -- curl -v https://<registry-url>/v2/_catalog
# POST-REQ: Delete debug pod after testing

# STEP 5: Check node's container runtime logs
# On node: docker logs | grep <podname>  (Docker)
# On node: crictl logs <container-id>   (containerd)
# WARNING: Requires SSH access to node

# STEP 6: Verify service account has permission to pull image
kubectl get sa default -n <namespace> -o yaml | jq '.imagePullSecrets'

# STEP 7: Check if image exists in registry
# Manually test: docker pull <image-name>:<tag>
# CAVEAT: May work locally but fail in cluster due to network policies

# STEP 8: Examine events for detailed error
kubectl get events -n <namespace> --field-selector involvedObject.name=<podname> -o wide
```

**Network diagnostic commands**:
```bash
# Test DNS resolution for registry
kubectl run debug-dns --image=busybox -n <namespace> --rm -it -- nslookup <registry-domain>

# Test network connectivity to registry
kubectl run debug-network --image=nicolaka/netshoot -n <namespace> --rm -it -- nc -zv <registry-url> 443
```

**Commands to NEVER use in production**:
```bash
# ❌ NEVER: kubectl patch secret with base64-encoded credentials in command line
#    Leaves credentials in shell history
```

---

## Scenario: Diagnosing `OOMKilled` Pod

**Prerequisites**: Pod terminated due to memory exhaustion  
**Common Causes**: Memory leak, insufficient limits, memory spikes under load

```bash
# STEP 1: Identify OOMKilled status
kubectl describe pod <podname> -n <namespace> | grep -A 5 "State:"
# Look for: Reason: OOMKilled, Exit Code: 137

# STEP 2: Check current memory limits and requests
kubectl get pod <podname> -n <namespace> -o json | jq '.spec.containers[] | {name, resources}'

# STEP 3: Monitor actual memory usage before crash
kubectl top pod <podname> -n <namespace>
# NOTE: Requires Metrics Server to be installed
# POST-REQ: Compare current usage with pod limits

# STEP 4: Check memory trends over time
kubectl logs <podname> -n <namespace> --previous | grep -i "memory\|RSS\|heap"
# CAVEAT: Depends on application logging memory metrics

# STEP 5: Increase memory limit and redeploy
kubectl set resources deployment <deployment-name> -n <namespace> \
  --containers=<container-name> \
  --limits=memory=2Gi --requests=memory=1Gi
# WARNING: Document reason for increase; avoid unlimited memory

# STEP 6: Check for memory leaks
kubectl exec -it <podname> -n <namespace> -- ps aux | grep <process>
# Look for: Continuously increasing VSZ or RSS columns over time
# PREREQUISITE: Container must have shell/ps utilities

# STEP 7: Verify resource quota isn't causing immediate OOM
kubectl describe resourcequota -n <namespace>

# STEP 8: Check Kubernetes memory eviction policies
kubectl describe node <node-name> | grep -A 10 "Allocatable\|Reserved"
```

**Advanced memory profiling** (application-dependent):
```bash
# For Java applications
kubectl exec -it <podname> -n <namespace> -- jcmd PID GC.heap_dump /tmp/heap.dump

# For Go applications (with pprof)
kubectl exec -it <podname> -n <namespace> -- curl localhost:6060/debug/pprof/heap > heap.profile

# For Python applications
kubectl exec -it <podname> -n <namespace> -- python -m tracemalloc
```

**Commands to NEVER use in production**:
```bash
# ❌ NEVER: Set memory limits to unlimited (no limits specified)
#    Can cause node crashes when all containers consume max memory
```

---

## Scenario: Diagnosing `Node NotReady`

**Prerequisites**: Node shows NotReady status; pods cannot be scheduled  
**Common Causes**: Container runtime crash, kubelet service failure, network issues, disk space exhaustion

```bash
# STEP 1: Check node status
kubectl get nodes -o wide
kubectl describe node <node-name>
# Look for: Conditions section, especially Ready status

# STEP 2: Check kubelet status on the node
# On node: sudo systemctl status kubelet
# POST-REQ: Check kubelet logs if service is running but node NotReady

# STEP 3: Check kubelet logs
# On node: sudo journalctl -u kubelet -n 100 --no-pager
# Or: kubectl logs -n kube-system -l component=kubelet -n kube-system
# CAVEAT: DaemonSet logs show all nodes; filter by hostname

# STEP 4: Verify container runtime
# On node: docker ps (Docker) or crictl ps (containerd)
# WARNING: If hung/unresponsive, may need restart

# STEP 5: Check disk space (critical)
kubectl describe node <node-name> | grep -A 5 "Allocated resources"
# On node: df -h  (filesystem usage)
# On node: du -sh /var/lib/docker  (Docker storage)
# POST-REQ: If < 10% free, trigger cleanup/eviction

# STEP 6: Check network connectivity
kubectl get nodes -o wide | grep <node-name>
# INTERNAL-IP should be reachable; test: ping <internal-ip> from another node

# STEP 7: Check for disk pressure/memory pressure conditions
kubectl get node <node-name> -o json | jq '.status.conditions'

# STEP 8: Check if node is cordoned
kubectl describe node <node-name> | grep -i "unschedulable"
# If true: kubectl uncordon <node-name>

# STEP 9: Check SSL/TLS certificate expiration on kubelet
# On node: sudo openssl x509 -in /var/lib/kubelet/pki/kubelet.crt -text -noout | grep -i "not after"
# WARNING: If expired, kubelet cannot communicate with API server
```

**Recovery procedures**:
```bash
# If container runtime is hung
# On node: sudo systemctl restart docker (or: systemctl restart containerd)

# If kubelet is stuck
# On node: sudo systemctl restart kubelet

# If disk full, drain node and clear
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data
# On node: sudo rm -rf /var/lib/docker/overlay2/*  (only if Docker restarted)
# Then: kubectl uncordon <node-name>
```

**Commands to NEVER use in production**:
```bash
# ❌ NEVER: kubectl delete node without proper draining
#    Pods may not have time to gracefully terminate
# ❌ NEVER: Manually edit /var/lib/kubelet on node
#    Corrupts node state permanently
```

---

## Scenario: Diagnosing Network Connectivity Issues

**Prerequisites**: Pod cannot reach services, external APIs, or other pods  
**Common Causes**: Network policy blocking, DNS failure, service misconfiguration, firewall rules

```bash
# STEP 1: Verify DNS resolution
kubectl run debug-dns --image=busybox -n <namespace> --rm -it -- nslookup <service-name>
# Should resolve to service IP (ClusterIP)
# CAVEAT: Different namespaces have different DNS domains

# STEP 2: Test internal service connectivity
kubectl run debug-curl --image=curlimages/curl -n <namespace> --rm -it -- \
  curl -v http://<service-name>.<namespace>.svc.cluster.local:8080
# PREREQUISITE: Know service port number

# STEP 3: Check service endpoints
kubectl get svc <service-name> -n <namespace> -o wide
kubectl get endpoints <service-name> -n <namespace>
# WARNING: If no endpoints, pods aren't being selected by service

# STEP 4: Verify service selector matches pod labels
kubectl get pods -n <namespace> --show-labels
kubectl get svc <service-name> -n <namespace> -o jsonpath='{.spec.selector}' | jq .
# POST-REQ: Update service selector or pod labels if mismatch

# STEP 5: Check NetworkPolicy restrictions
kubectl get networkpolicy -n <namespace>
kubectl describe networkpolicy <policy-name> -n <namespace>
# CAVEAT: Multiple policies may apply; check all

# STEP 6: Test connectivity from source pod to destination
kubectl exec -it <source-pod> -n <namespace> -- nc -zv <dest-ip> <port>
# Or: kubectl exec -it <source-pod> -n <namespace> -- telnet <dest-ip> <port>
# PREREQUISITE: nc or telnet must be installed in container

# STEP 7: Check iptables rules on node (if using kube-proxy)
# On node: sudo iptables-save | grep <service-name>
# WARNING: Complex output; may need grep for specific ports

# STEP 8: Verify pod network interface
kubectl exec -it <podname> -n <namespace> -- ip addr show
kubectl exec -it <podname> -n <namespace> -- ip route show
# POST-REQ: Ensure pod has valid IP and default route

# STEP 9: Check ingress rules (if external access)
kubectl get ingress -n <namespace>
kubectl describe ingress <ingress-name> -n <namespace>
```

**Advanced network debugging**:
```bash
# Capture network packets
kubectl exec -it <podname> -n <namespace> -- tcpdump -i eth0 -n
# WARNING: High verbosity; use filters like: tcp port 8080

# Check DNS cache (if applicable)
kubectl exec -it <podname> -n <namespace> -- cat /etc/resolv.conf

# Test external connectivity
kubectl run debug-external --image=curlimages/curl -n <namespace> --rm -it -- \
  curl -v https://api.example.com
```

**Commands to NEVER use in production**:
```bash
# ❌ NEVER: kubectl exec to modify container network config
#    Changes are lost on pod restart; fix source issue instead
```

---

## Scenario: Diagnosing Storage/PVC Issues

**Prerequisites**: Pod cannot mount persistent volume or I/O errors  
**Common Causes**: PVC not bound, storage class not found, insufficient capacity, permission issues

```bash
# STEP 1: Check PVC status
kubectl get pvc -n <namespace> -o wide
# Look for: Phase (Bound, Pending, Failed), Capacity, Access Mode

# STEP 2: Describe PVC for error details
kubectl describe pvc <pvc-name> -n <namespace>
# Shows: Events with exact error (StorageClass not found, insufficient capacity, etc.)

# STEP 3: Verify storage class exists
kubectl get storageclass
kubectl describe storageclass <storage-class-name>
# CAVEAT: Different provisioners have different capabilities

# STEP 4: Check if storage provisioner is running
kubectl get pods -n kube-system | grep -i storage
# POST-REQ: Restart provisioner pod if failing

# STEP 5: Verify pod mount status
kubectl get pod <podname> -n <namespace> -o yaml | jq '.spec.volumes'
kubectl describe pod <podname> -n <namespace> | grep -A 10 "Mounts:"

# STEP 6: Check mount inside pod
kubectl exec -it <podname> -n <namespace> -- df -h
kubectl exec -it <podname> -n <namespace> -- mount | grep /mnt
# PREREQUISITE: Pod must be in Running state

# STEP 7: Test read/write permissions
kubectl exec -it <podname> -n <namespace> -- touch /mnt/test-file
kubectl exec -it <podname> -n <namespace> -- rm /mnt/test-file
# WARNING: May fail if volume is read-only or permission denied

# STEP 8: Check underlying storage backend
# For AWS EBS: AWS console > EBS Volumes (check status, attachments)
# For NFS: Check NFS server connectivity and exports
# For local: Verify disk space on node

# STEP 9: Verify PVC can be claimed by pod (selector/label match)
kubectl get pvc <pvc-name> -n <namespace> -o json | jq '.metadata.labels'
```

**Advanced storage debugging**:
```bash
# Check PV (Persistent Volume) details
kubectl get pv
kubectl describe pv <pv-name>

# For StatefulSets, verify ordering
kubectl get statefulset <name> -n <namespace> -o yaml | jq '.spec.volumeClaimTemplates'

# Test storage provisioner logs
kubectl logs -n kube-system -l app=storage-provisioner --tail=50
```

**Commands to NEVER use in production**:
```bash
# ❌ NEVER: kubectl delete pvc <pvc-name> without backup
#    Permanently deletes volume data (retention policy dependent)
# ❌ NEVER: kubectl delete pv <pv-name> while in use
#    Causes data corruption and pod crashes
```

---

## Scenario: Diagnosing High CPU/Memory Resource Issues

**Prerequisites**: Nodes or pods consuming excessive resources  
**Common Causes**: Memory leak, inefficient algorithm, runaway process, resource limit misconfiguration

```bash
# STEP 1: Check node resource usage
kubectl top nodes
# PREREQUISITE: Metrics Server must be running
# Shows: CPU and memory usage per node

# STEP 2: Check pod resource usage
kubectl top pod -n <namespace>
kubectl top pod -n <namespace> --containers  # Per-container breakdown

# STEP 3: Identify resource hogs
kubectl top pod -n <namespace> --sort-by=memory
kubectl top pod -n <namespace> --sort-by=cpu

# STEP 4: Get current resource limits
kubectl get pod <podname> -n <namespace> -o json | jq '.spec.containers[] | {name, resources}'

# STEP 5: Compare usage vs limits
# Calculate: (current usage / limit) * 100 = percentage of limit
# CAVEAT: Spike may be temporary; monitor over time

# STEP 6: Check historical trends (if Prometheus available)
# Query: rate(container_cpu_usage_seconds_total{pod_name="<podname>"}[5m])

# STEP 7: Monitor in real-time
kubectl top pod -n <namespace> --watch
# Press Ctrl+C to exit

# STEP 8: Identify specific container consuming most resources
kubectl exec -it <podname> -n <namespace> -- top -b -n 1
# Shows: Processes sorted by CPU/memory within container

# STEP 9: Check if horizontal pod autoscaler is active
kubectl get hpa -n <namespace>
kubectl describe hpa <hpa-name> -n <namespace>
```

**Advanced profiling** (application-dependent):
```bash
# For Java: Enable JFR (Java Flight Recorder)
kubectl exec -it <podname> -n <namespace> -- jcmd PID JFR.start

# For Go: Dump goroutines
kubectl exec -it <podname> -n <namespace> -- curl localhost:6060/debug/pprof/goroutine

# For Python: Memory snapshot
kubectl exec -it <podname> -n <namespace> -- python -m memory_profiler
```

**Optimization commands**:
```bash
# Update resource limits
kubectl set resources deployment <deployment-name> -n <namespace> \
  --containers=<container-name> \
  --limits=cpu=2,memory=2Gi --requests=cpu=500m,memory=512Mi
# WARNING: Document the change and monitor for regressions

# Update HPA metrics
kubectl autoscale deployment <deployment-name> -n <namespace> \
  --min=2 --max=10 --cpu-percent=80
```

**Commands to NEVER use in production**:
```bash
# ❌ NEVER: Set resources to unlimited
# ❌ NEVER: Delete metrics-server to "fix" resource issues
#    Root cause investigation required first
```

---

## Scenario: Diagnosing Pod Stuck in `Terminating` State

**Prerequisites**: Pod deletion in progress but never completes  
**Common Causes**: Finalizer loop, graceful shutdown timeout, sidecar preventing termination

```bash
# STEP 1: Identify stuck pod
kubectl get pod -n <namespace> | grep Terminating

# STEP 2: Check pod details
kubectl describe pod <podname> -n <namespace>
# Look for: deletionGracePeriodSeconds, deletion timestamp

# STEP 3: Check for finalizers (blocking deletion)
kubectl get pod <podname> -n <namespace> -o jsonpath='{.metadata.finalizers}' | jq .

# STEP 4: Check pod logs during termination
kubectl logs <podname> -n <namespace> --previous --tail=50

# STEP 5: Examine preStop hooks
kubectl get pod <podname> -n <namespace> -o jsonpath='{.spec.containers[*].lifecycle}' | jq .

# STEP 6: Check if graceful period already exceeded
# Calculate: now - deletionTimestamp > gracefulTerminationPeriod
kubectl get pod <podname> -n <namespace> -o json | jq '.metadata.deletionTimestamp'

# STEP 7: Check kubelet logs on pod's node
# On node: sudo journalctl -u kubelet -n 100 | grep <podname>

# STEP 8: Verify no process is stuck in uninterruptible sleep
kubectl exec -it <podname> -n <namespace> -- ps aux | grep '<D'
# CAVEAT: If in '<D' state, process cannot receive signals

# EMERGENCY: Force delete if graceful period exceeded
kubectl delete pod <podname> -n <namespace> --grace-period=0 --force
# WARNING: Use only after confirming graceful deletion stuck for extended period
# POST-REQ: Investigate why graceful termination failed
```

**Investigation checklist**:
```bash
# Check if finalizers are preventing deletion
kubectl patch pod <podname> -n <namespace> -p '{"metadata":{"finalizers":null}}'
# WARNING: Only if you understand what finalizer does

# Check node disk space (may prevent cleanup)
kubectl describe node <node-name> | grep -A 5 "DiskPressure"
```

**Commands to NEVER use in production**:
```bash
# ❌ NEVER: kubectl delete pod --force --grace-period=0 prematurely
#    Data loss, connection resets, inconsistent state
# ❌ NEVER: Forcefully kill container runtime processes
#    Only use kubectl delete with grace period
```

---

## Scenario: Diagnosing RBAC Permission Issues

**Prerequisites**: Access denied errors or "forbidden" responses  
**Common Causes**: Role/RoleBinding misconfiguration, service account permissions, cluster admin needed

```bash
# STEP 1: Check current user/service account
kubectl auth whoami
# Shows: Current user and groups

# STEP 2: Check if user can perform action
kubectl auth can-i <verb> <resource> --as=<user>
# Example: kubectl auth can-i get pods --as=system:serviceaccount:default:mysa

# STEP 3: Check service account permissions
kubectl get sa <service-account-name> -n <namespace>
kubectl get rolebindings -n <namespace> -o wide

# STEP 4: Check role details
kubectl get role <role-name> -n <namespace> -o yaml
# Look for: rules section with verbs, resources, apiGroups

# STEP 5: Check cluster role bindings
kubectl get clusterrolebindings -o wide | grep <service-account-name>

# STEP 6: Verify token is valid
kubectl get secret -n <namespace> | grep <service-account-name>
kubectl get secret <token-secret-name> -n <namespace> -o yaml | jq '.data.token' | base64 -d

# STEP 7: Test API call with specific user
kubectl get pods --as=system:serviceaccount:default:mysa
# Should show permission denied or success

# STEP 8: Check for wildcards in role
kubectl get role <role-name> -n <namespace> -o jsonpath='{.rules}' | jq '.[] | select(.verbs[] == "*")'

# STEP 9: Audit log analysis (if enabled)
kubectl logs -n kube-system -l component=kube-apiserver | grep "forbidden"
# CAVEAT: Audit logging must be enabled in cluster
```

**Creating proper RBAC**:
```bash
# Example: Create role for reading pods only
kubectl create role pod-reader --verb=get,list --resource=pods -n <namespace>

# Example: Bind role to service account
kubectl create rolebinding pod-reader --role=pod-reader --serviceaccount=default:mysa -n <namespace>

# Verify permission
kubectl auth can-i get pods --as=system:serviceaccount:default:mysa -n <namespace>
```

**Commands to NEVER use in production**:
```bash
# ❌ NEVER: kubectl create clusterrolebinding with cluster-admin for troubleshooting
#    Creates permanent security hole; use --as flag instead
# ❌ NEVER: kubectl delete clusterrolebinding cluster-admin-* without understanding impact
#    Can break cluster access permanently
```

---

## Scenario: Diagnosing Cluster Resource Exhaustion

**Prerequisites**: Pod scheduling failure, nodes full, cluster cannot accept new workloads  
**Common Causes**: Resource quota exceeded, node capacity full, forgotten resources not cleaned up

```bash
# STEP 1: Check cluster node capacity
kubectl get nodes -o wide
kubectl top nodes  # Current usage

# STEP 2: Check resource requests vs allocatable
kubectl describe nodes | grep -A 5 "Allocatable\|Allocated resources"

# STEP 3: Check namespace resource quota
kubectl describe resourcequota -n <namespace>
# Shows: Requests and limits usage vs quota

# STEP 4: List all resources using capacity
kubectl get pods -A --sort-by='.spec.containers[0].resources.requests.memory'

# STEP 5: Find pods without resource limits (dangerous)
kubectl get pods -n <namespace> -o json | \
  jq '.items[] | select(.spec.containers[].resources == null) | .metadata.name'

# STEP 6: Check persistent volumes usage
kubectl get pv -o wide | grep -v "100%"
# Look for: Nearly full volumes

# STEP 7: Identify orphaned resources
kubectl get pvc -n <namespace> --no-headers | \
  awk '{print $1}' | xargs -I {} kubectl get pvc {} -o json | jq 'select(.status.phase != "Bound")'

# STEP 8: Check DNS pod capacity
kubectl get pods -n kube-system -l k8s-app=kube-dns
# Verify replicas match node count (usually 1 per 2 cores)

# STEP 9: Monitor eviction events
kubectl get events -A --sort-by='.lastTimestamp' | grep -i evict
# CAVEAT: Evictions are aggressive and cause pod failures
```

**Cleanup procedures**:
```bash
# Remove completed jobs (occupy resources if not cleaned)
kubectl delete job -n <namespace> --field-selector status.successful=1

# Delete pod disruption budgets blocking scale-down
kubectl get pdb -n <namespace>
kubectl describe pdb <pdb-name> -n <namespace>

# Scale down unnecessary deployments
kubectl scale deployment <name> -n <namespace> --replicas=0

# Adjust resource quotas
kubectl edit resourcequota <quota-name> -n <namespace>
```

**Commands to NEVER use in production**:
```bash
# ❌ NEVER: kubectl set resources ... --limits=memory=999Gi for single pod
#    Causes cluster-wide resource exhaustion
# ❌ NEVER: Delete nodes to free resources
#    Use drain and properly schedule workloads instead
```

---

## Scenario: Diagnosing DNS/Service Discovery Issues

**Prerequisites**: Pod cannot resolve service names or external domains  
**Common Causes**: CoreDNS down, misconfigured service, network policy blocking DNS, nameserver issues

```bash
# STEP 1: Verify CoreDNS is running
kubectl get pods -n kube-system -l k8s-app=kube-dns
# Should show 2+ Running pods (HA setup)

# STEP 2: Check CoreDNS logs
kubectl logs -n kube-system -l k8s-app=kube-dns --tail=50

# STEP 3: Test DNS from pod
kubectl run debug-dns --image=busybox -n <namespace> --rm -it -- \
  nslookup <service-name>
# PREREQUISITE: Pod must have network access to kube-system namespace

# STEP 4: Test full DNS name
kubectl run debug-dns --image=busybox -n <namespace> --rm -it -- \
  nslookup <service-name>.<namespace>.svc.cluster.local

# STEP 5: Test external DNS
kubectl run debug-dns --image=busybox -n <namespace> --rm -it -- \
  nslookup google.com

# STEP 6: Check pod's DNS configuration
kubectl exec -it <podname> -n <namespace> -- cat /etc/resolv.conf
# Look for: nameserver (should be service IP of kube-dns)

# STEP 7: Check CoreDNS ConfigMap
kubectl get configmap coredns -n kube-system -o yaml
# Look for: Corefile plugin configuration

# STEP 8: Verify service records in CoreDNS
kubectl exec -it <dns-pod> -n kube-system -- dig <service-name>.default.svc.cluster.local

# STEP 9: Check for network policies blocking DNS traffic
kubectl get networkpolicy -n <namespace> -o yaml | grep -A 5 "port: 53"
```

**NetworkPolicy for DNS**:
```bash
# Allow DNS traffic if blocked
kubectl create networkpolicy allow-dns -n <namespace> --pod-selector='{}' \
  --direction-ingress --action-allow \
  --protocol UDP --port 53 --selector 'k8s-app=kube-dns'
```

**Commands to NEVER use in production**:
```bash
# ❌ NEVER: Modify CoreDNS ConfigMap without testing
#    Can break DNS for entire cluster
# ❌ NEVER: Restart kube-dns pods simultaneously
#    Results in cluster-wide DNS outage
```

---

## Critical Production Debugging Principles

### General Best Practices
1. **Always gather context first**: Never make changes without understanding root cause
2. **Use read-only commands initially**: `describe`, `get`, `logs` before `edit`, `patch`
3. **Change one variable at a time**: Makes root cause analysis possible
4. **Document every change**: Include timestamp, reason, expected outcome
5. **Test in non-production first**: Stage/dev environment for all experiments
6. **Check timestamps**: Logs and events must be chronologically consistent
7. **Monitor impact**: After each change, verify desired outcome achieved
8. **Have rollback plan**: Know how to revert changes immediately

### Dangerous Commands Checklist
```bash
# NEVER IN PRODUCTION:
kubectl delete pod --force --grace-period=0          # Ungraceful termination
kubectl delete node <node>                           # Without drain first
kubectl delete pvc <pvc>                             # Without backup
kubectl patch secret                                 # In command line (shell history!)
kubectl set image ... without staging                # Untested changes
kubectl scale deployment --replicas=0                # Without understanding impact
kubectl delete namespace                             # Destroys all resources
kubectl drain node without --ignore-daemonsets       # Hangs indefinitely
```

### Essential Metadata to Always Collect
- **Timestamps**: Pod creation, last transition, crash time
- **Resource limits vs actual usage**: Critical for OOM/CPU issues
- **Event messages**: Always in describe output
- **Previous container logs**: Essential for CrashLoopBackOff
- **Node conditions**: Ready, DiskPressure, MemoryPressure, PIDPressure
- **Service endpoints**: Verify pods are actually selected

### Tools Required in Production Cluster
```bash
# Minimal required tools for debugging
- kubectl >= 1.20
- jq (JSON parser)
- curl/wget
- netcat or netshoot container
- Metrics Server (for kubectl top)
- Prometheus (for historical metrics, optional but recommended)

# Install netshoot for debugging
kubectl run netshoot --image=nicolaka/netshoot -n default --rm -it -- /bin/bash
```

---

**Last Updated**: January 2026  
**Kubernetes Version**: 1.24+  
**Severity Level**: Production Critical  
**Review Frequency**: Quarterly
