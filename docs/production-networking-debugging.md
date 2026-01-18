# Production Networking Debugging Commands

> **Critical Context**: Network debugging requires systematic layer-by-layer analysis (OSI Model). Always start with physical layer (L1), then L2 (data link), L3 (routing), L4 (TCP/UDP), L7 (application). Network changes affect downstream systems; document and test thoroughly.

---

## Scenario: Diagnosing Pod-to-Pod Communication Failures

**Prerequisites**: Two pods in same or different namespaces cannot communicate  
**Common Causes**: NetworkPolicy blocking, CNI misconfiguration, overlay network issues, service DNS failure, iptables rules

```bash
# STEP 1: Verify both pods are running and have IPs
kubectl get pods -n <namespace> -o wide
# Shows: Pod IP addresses; ensure both pods are Running

# STEP 2: Get pod network namespace
kubectl exec -it <pod1> -n <namespace> -- hostname -I
kubectl exec -it <pod2> -n <namespace> -- hostname -I
# Note: Pod IPs for later verification

# STEP 3: Test direct connectivity between pods
kubectl exec -it <pod1> -n <namespace> -- ping -c 4 <pod2-ip>
# Should succeed if network is healthy

# STEP 4: Check for NetworkPolicy blocking traffic
kubectl get networkpolicies -n <namespace>
kubectl describe networkpolicy <policy-name> -n <namespace>
# Look for: ingress/egress rules that match pods

# STEP 5: Test with all network policies removed (diagnostic only)
kubectl delete networkpolicy --all -n <namespace>
# Then test again with: kubectl exec ... ping
# CAVEAT: Temporary removal for diagnosis; restore immediately

# STEP 6: Check CNI plugin status
kubectl get daemonset -n kube-system -o wide
# Look for: weave, flannel, calico, cilium pods; should be Running

# STEP 7: View pod network interface from host
kubectl debug pod/<pod1> -it --image=busybox -- ip addr show
# Or access via: kubectl exec -it <pod1> -- ip addr

# STEP 8: Check pod's default route
kubectl exec -it <pod1> -- ip route show
# Should show: default route to container gateway

# STEP 9: Verify iptables rules aren't blocking (on node)
# On node with pod1:
iptables -L -n | grep <pod1-ip>
# May show ACCEPT/DROP rules

# STEP 10: Check container veth interface on node
ip link show | grep veth
# Shows: Virtual ethernet pairs for pods

# STEP 11: Trace network path with traceroute
kubectl exec -it <pod1> -- traceroute <pod2-ip>
# Shows: Hops between pods; should be 1-2 hops max within cluster

# STEP 12: Monitor network traffic on node
# On node: tcpdump -i <veth-interface> -n "icmp"
# Capture ping packets to verify traffic reaching interface
```

**Advanced pod connectivity diagnostics**:
```bash
# Test DNS resolution
kubectl exec -it <pod1> -- nslookup <pod2-service>
# Should resolve to pod2 service IP

# Test TCP connectivity with specific port
kubectl exec -it <pod1> -- nc -zv <pod2-ip> <port>
# Or: timeout 5 kubectl exec <pod1> -- curl http://<pod2-ip>:<port>

# Check MTU for fragmentation issues
kubectl exec -it <pod1> -- ip link show | grep mtu
# If < 1500, may cause issues with large packets

# Monitor network latency
kubectl exec -it <pod1> -- ping -c 10 <pod2-ip> | grep "min/avg/max"
# Normal: < 1ms within node, < 5ms cross-node
```

**NetworkPolicy debugging**:
```bash
# Create temporary allow-all policy for testing
cat << EOF | kubectl apply -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-all-debug
  namespace: <namespace>
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - {}
  egress:
  - {}
EOF

# Test connectivity, then remove
kubectl delete networkpolicy allow-all-debug -n <namespace>

# Restore original policies
kubectl apply -f <original-policies.yaml>
```

**Commands to NEVER use in production**:
```bash
# ❌ NEVER: kubectl delete networkpolicy --all without backup
#    Leaves cluster exposed to internal attacks
# ❌ NEVER: Permanently remove CNI plugin to "fix" networking
#    All pods lose connectivity
# ❌ NEVER: Modify veth interfaces on host while pod running
#    Breaks container network connection
```

---

## Scenario: Diagnosing Service Discovery and DNS Issues

**Prerequisites**: Applications cannot reach services by name, DNS resolution failing  
**Common Causes**: CoreDNS pod down, service not created properly, DNS cache issues, network policy blocking DNS traffic

```bash
# STEP 1: Verify CoreDNS is running
kubectl get pods -n kube-system -l k8s-app=kube-dns -o wide
# Should show: 2+ Running pods in different nodes

# STEP 2: Check CoreDNS logs for errors
kubectl logs -n kube-system -l k8s-app=kube-dns --tail=50 --all-containers

# STEP 3: Verify service exists and has endpoints
kubectl get svc <service-name> -n <namespace>
kubectl get endpoints <service-name> -n <namespace>
# Service IP should be assigned; endpoints should list pod IPs

# STEP 4: Test DNS resolution from test pod
kubectl run debug-dns --image=busybox -n <namespace> --rm -it -- \
  nslookup <service-name>
# Should return service ClusterIP

# STEP 5: Test DNS with FQDN
kubectl run debug-dns --image=busybox -n <namespace> --rm -it -- \
  nslookup <service-name>.<namespace>.svc.cluster.local
# Full domain name should also resolve

# STEP 6: Check pod's DNS configuration
kubectl exec -it <pod> -n <namespace> -- cat /etc/resolv.conf
# Should list kube-dns service IP as nameserver

# STEP 7: Test DNS server directly
kubectl run debug-dns --image=busybox -n <namespace> --rm -it -- \
  nslookup <service-name> <coredns-service-ip>:53
# Verify DNS service itself responds

# STEP 8: Check for DNS query timeouts
kubectl run debug-dns --image=busybox -n <namespace> --rm -it -- \
  timeout 5 dig <service-name>
# Shows: Query time and response

# STEP 9: Verify NetworkPolicy allows DNS traffic
kubectl get networkpolicy -n kube-system
# Look for: Policies blocking port 53 (DNS)

# STEP 10: Check CoreDNS ConfigMap
kubectl get configmap coredns -n kube-system -o yaml | grep -A 20 "data:"
# Shows: DNS configuration and plugins

# STEP 11: Monitor DNS query rate
kubectl exec -it <coredns-pod> -n kube-system -- \
  tcpdump -i eth0 -n "udp port 53" -c 20
# Shows: DNS traffic pattern

# STEP 12: Check for DNS resolution loops
dig @<coredns-ip> <service-name> +trace
# Should show DNS resolution path without loops
```

**DNS troubleshooting**:
```bash
# Test external DNS resolution
kubectl run debug-dns --image=busybox -n <namespace> --rm -it -- \
  nslookup google.com
# Should resolve external domains

# Check DNS query response time
kubectl run debug-dns --image=busybox -n <namespace> --rm -it -- \
  time nslookup <service-name>
# Should be < 100ms

# Test DNS with dig for more details
kubectl run debug-dns --image=busybox -n <namespace> --rm -it -- \
  dig <service-name> +short +stats
# Shows: Query statistics and DNSSEC info

# Check for DNS cache issues
kubectl exec -it <pod> -n <namespace> -- \
  systemd-resolve --statistics  # If systemd-resolved used
```

**CoreDNS recovery**:
```bash
# Restart CoreDNS pods to clear cache
kubectl rollout restart deployment coredns -n kube-system

# Scale CoreDNS replicas if needed
kubectl scale deployment coredns -n kube-system --replicas=3

# Check CoreDNS resource limits
kubectl describe deployment coredns -n kube-system | grep -A 5 "Limits\|Requests"

# Enable CoreDNS debug logging temporarily
kubectl edit configmap coredns -n kube-system
# Add: log
# Then restart pods
```

**Commands to NEVER use in production**:
```bash
# ❌ NEVER: kubectl scale deployment coredns --replicas=0
#    Entire cluster loses DNS; services become unreachable
# ❌ NEVER: Delete CoreDNS pods without considering traffic
#    Brief outage during pod restart
# ❌ NEVER: Modify CoreDNS ConfigMap without testing
#    Syntax errors break DNS for entire cluster
```

---

## Scenario: Diagnosing Ingress and Load Balancer Issues

**Prerequisites**: External traffic cannot reach services, ingress controller unhealthy, load balancer not distributing traffic  
**Common Causes**: Ingress controller down, service selector mismatch, node ports blocked, load balancer misconfigured

```bash
# STEP 1: Verify Ingress controller is running
kubectl get deployment -n ingress-nginx  # NGINX ingress
kubectl get daemonset -n ingress-nginx  # NGINX as DaemonSet
kubectl get pods -n ingress-nginx -o wide

# STEP 2: Check ingress resource exists and has IPs
kubectl get ingress -n <namespace>
kubectl describe ingress <ingress-name> -n <namespace>
# Look for: Address field (should have IP or hostname)

# STEP 3: Verify backend service endpoints
kubectl get endpoints -n <namespace> | grep <service-name>
# Should show pod IPs for that service

# STEP 4: Test ingress controller health
kubectl exec -it <ingress-pod> -n ingress-nginx -- \
  curl -s localhost:10254/metrics | head -20
# PREREQUISITE: Metrics port exposed

# STEP 5: Check ingress controller logs
kubectl logs -n ingress-nginx -l app.kubernetes.io/name=ingress-nginx --tail=50

# STEP 6: Verify ingress configuration was loaded
kubectl exec -it <ingress-pod> -n ingress-nginx -- \
  cat /etc/nginx/nginx.conf | grep <ingress-hostname>
# Should show nginx configuration for ingress hostname

# STEP 7: Test directly to ingress pod
kubectl exec -it <ingress-pod> -n ingress-nginx -- \
  curl -v -H "Host: <ingress-hostname>" localhost
# Should return backend response

# STEP 8: Check if ingress controller NodePort is accessible
kubectl get svc -n ingress-nginx ingress-nginx
# Note: NodePort (e.g., 30123), then test: curl http://<node-ip>:30123

# STEP 9: Verify DNS points to correct ingress IP
nslookup <ingress-hostname>
# Should resolve to load balancer IP or ingress controller node IP

# STEP 10: Check for firewall rules blocking ingress ports
# On node: iptables -L -n | grep 80
# Look for: Rules on port 80/443

# STEP 11: Monitor ingress pod connections
kubectl exec -it <ingress-pod> -n ingress-nginx -- \
  netstat -tlnp | grep -E ":80|:443"
# Should show listening on HTTP/HTTPS ports

# STEP 12: Test TLS certificate if HTTPS ingress
kubectl get secret -n <namespace> <cert-secret-name> -o yaml
# Verify certificate fields and validity dates
```

**Ingress troubleshooting**:
```bash
# Test ingress with curl
curl -v http://<ingress-ip> -H "Host: <ingress-hostname>"
# Shows: Request/response headers and body

# Check if path-based routing works
curl http://<ingress-ip>/path1 -H "Host: example.com"

# Test TLS/HTTPS
curl -v https://<ingress-ip> -H "Host: <ingress-hostname>" \
  --insecure  # For self-signed certs

# Check ingress controller metrics
kubectl exec -it <ingress-pod> -n ingress-nginx -- \
  curl -s localhost:10254/metrics | grep nginx_http_requests_total
```

**Load balancer recovery**:
```bash
# Scale ingress replicas if needed
kubectl scale deployment ingress-nginx -n ingress-nginx --replicas=3

# Force reload of ingress configuration
kubectl rollout restart deployment ingress-nginx -n ingress-nginx

# Check ingress controller resource limits
kubectl describe deployment ingress-nginx -n ingress-nginx | grep -A 5 "Resources"

# Verify ingress class annotation
kubectl get ingress <ingress-name> -n <namespace> -o jsonpath='{.spec.ingressClassName}'

# For multiple ingress controllers, ensure correct class
kubectl get ingressclass
```

**Commands to NEVER use in production**:
```bash
# ❌ NEVER: kubectl delete all ingress --all-namespaces
#    Breaks all external traffic routing
# ❌ NEVER: Edit ingress-nginx ConfigMap without reload
#    Changes may not take effect until restart
# ❌ NEVER: Disable TLS to "fix" HTTPS issues
#    Security risk; debug certificate issues instead
```

---

## Scenario: Diagnosing Cross-Namespace and Multi-Cluster Network Issues

**Prerequisites**: Services in different namespaces cannot communicate, multi-cluster mesh failing  
**Common Causes**: Network policy isolation, RBAC preventing service discovery, cross-cluster routing misconfigured

```bash
# STEP 1: Verify service is accessible across namespaces
kubectl run debug -n <namespace1> --image=busybox --rm -it -- \
  nslookup <service-name>.<namespace2>.svc.cluster.local
# Should resolve if DNS allows cross-namespace queries

# STEP 2: Check NetworkPolicy in both namespaces
kubectl get networkpolicy -n <namespace1>
kubectl get networkpolicy -n <namespace2>
# Look for: Policies that may block inter-namespace traffic

# STEP 3: Create test policy allowing cross-namespace
kubectl apply -f - << EOF
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-cross-ns
  namespace: <namespace2>
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: <namespace1>
EOF

# STEP 4: Test cross-namespace connectivity
kubectl exec -it <pod1> -n <namespace1> -- \
  nc -zv <service-name>.<namespace2>.svc.cluster.local <port>

# STEP 5: For multi-cluster, check inter-cluster network
# On cluster1: ping <cluster2-gateway-ip>
ping <cluster2-pod-subnet-gateway>
# Should have route to cluster2 subnet

# STEP 6: Verify service mesh is running (if using istio/linkerd)
kubectl get deployment -n istio-system  # Istio
kubectl get deployment -n linkerd  # Linkerd
# Shows: Control plane components status

# STEP 7: Check service mesh injector is enabled
kubectl get ns -L istio-injection
# Look for: Namespaces with istio-injection=enabled

# STEP 8: Verify sidecar proxy is injected
kubectl get pods <pod> -n <namespace> -o jsonpath='{.spec.containers[*].name}'
# Should show: istio-proxy or linkerd-proxy container

# STEP 9: Check service mesh traffic policy
kubectl get destinationrule -n <namespace>
kubectl get virtualservice -n <namespace>
# Shows: Service mesh routing rules

# STEP 10: Monitor inter-cluster traffic (if available)
kubectl exec -it <istio-proxy-pod> -- netstat -tlnp | grep -i proxy
# Shows: Sidecar proxy connections

# STEP 11: Check for certificate issues in mesh
kubectl get secret -n istio-system istio.io/ca-key -o yaml
# Verify mesh CA certificate validity

# STEP 12: Test multi-cluster service discovery
kubectl get services --all-namespaces | grep <service-name>
# Should show service in multiple clusters
```

**Cross-namespace networking setup**:
```bash
# Label namespace for service mesh injection
kubectl label namespace <namespace> istio-injection=enabled

# Create NetworkPolicy allowing specific cross-namespace traffic
kubectl apply -f - << EOF
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-from-app
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: app-namespace
      podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 8080
EOF

# Test connectivity before/after policy
```

**Multi-cluster debugging**:
```bash
# Check inter-cluster connectivity
kubectl exec -it <pod> -- ping -c 4 <remote-cluster-pod-ip>

# Monitor cross-cluster service discovery
kubectl describe endpoints <service-name> -n <namespace> | grep -i "not-ready\|ready"

# Check service mesh control plane communication
kubectl logs -n istio-system -l app=istiod | grep -i "error\|connection"
```

**Commands to NEVER use in production**:
```bash
# ❌ NEVER: kubectl delete namespace without draining pods
#    May cause resource orphaning
# ❌ NEVER: Disable service mesh on live traffic
#    Causes immediate service disruption
# ❌ NEVER: Modify cross-cluster routing without testing
#    Can cause routing loops or connectivity loss
```

---

## Scenario: Diagnosing Node Network Interface and Driver Issues

**Prerequisites**: Node has poor network performance, interface errors, driver issues  
**Common Causes**: NIC driver outdated, interface misconfiguration, hardware failure, MTU size incorrect

```bash
# STEP 1: List all network interfaces
ip link show
ifconfig -a  # Legacy tool

# STEP 2: Check interface status
ethtool <interface>
# Shows: Speed, duplex, link status, driver info

# STEP 3: Monitor interface statistics
ethtool -S <interface> | grep -E "error|dropped|collision"
# Shows: Hardware error counters

# STEP 4: Check MTU size
ip link show <interface> | grep mtu
# Should be 1500 (standard) or 9000 (jumbo frames)

# STEP 5: Check for interface errors
ip -s link show <interface>
# Shows: RX/TX errors, dropped packets

# STEP 6: Verify driver is loaded
lspci | grep -i ethernet
ethtool -i <interface>
# Shows: Driver name and version

# STEP 7: Check for driver update availability
modinfo <driver-name>
# Shows: Driver version and author

# STEP 8: Monitor packet loss on interface
timeout 10 tcpdump -i <interface> -q
# Capture packets to identify loss pattern

# STEP 9: Check interface interrupt handling
cat /proc/interrupts | grep <interface-name>
# Shows: Interrupt count; rapid growth = high traffic

# STEP 10: Monitor interface queue
ethtool -g <interface>
# Shows: RX/TX ring buffer sizes

# STEP 11: Check for promiscuous mode
ip link show <interface> | grep -i promisc
# Should NOT be set normally

# STEP 12: Verify interface has correct IP
ip addr show <interface>
# Should have IP address configured
```

**Network interface diagnostics**:
```bash
# Check interface speed negotiation
ethtool <interface> | grep Speed

# Monitor real-time interface stats
watch -n 1 'ip -s link show <interface>'

# Check RX packet distribution across CPUs
cat /proc/interrupt | grep -E "TxRx|Rx"

# For SR-IOV interfaces, check VF status
lspci -vv | grep -E "Single Root|Virtual Function"
```

**Interface recovery and optimization**:
```bash
# Restart interface
ip link set <interface> down
ip link set <interface> up

# Adjust MTU for jumbo frames (if network supports)
ip link set <interface> mtu 9000

# Increase ring buffer for high-traffic interface
ethtool -G <interface> rx 4096 tx 4096
# May improve throughput

# Enable offloading features
ethtool -K <interface> tso on  # TCP Segmentation Offload
ethtool -K <interface> gso on  # Generic Segmentation Offload
ethtool -K <interface> gro on  # Generic Receive Offload

# Update network driver
# For Linux: usually requires kernel update or driver RPM/DEB

# Configure interrupt coalescing (reduce CPU overhead)
ethtool -C <interface> rx-usecs 100
```

**Commands to NEVER use in production**:
```bash
# ❌ NEVER: ip link set <interface> down on active traffic
#    Service disruption for all pods on that node
# ❌ NEVER: Change MTU without coordinating with network team
#    May cause packet fragmentation or black hole routing
# ❌ NEVER: Unload driver module without stopping services
#    Immediate network outage on that node
```

---

## Scenario: Diagnosing VPN/Tunnel and Hybrid Cloud Connectivity Issues

**Prerequisites**: On-prem to cloud connectivity broken, VPN tunnel down, hybrid cloud apps cannot communicate  
**Common Causes**: IPsec/wireguard misconfiguration, BGP route propagation failure, asymmetric routing, encryption mismatch

```bash
# STEP 1: Check VPN tunnel status
# For IPsec:
sudo ipsec status
ipsec verify  # Verify IPsec configuration

# For WireGuard:
sudo wg show  # Shows WireGuard interface status
ip link show wg0  # Check interface state

# STEP 2: Verify VPN endpoints are reachable
ping -c 4 <vpn-endpoint-ip>
# Should have sub-10ms latency

# STEP 3: Check tunnel interface status
ip link show | grep -E "tun|wg|ipsec|vpn"
# Should show UP status

# STEP 4: Verify tunnel has IP address
ip addr show <tunnel-interface>
# Should have IP for tunnel subnet

# STEP 5: Monitor tunnel traffic
tcpdump -i <tunnel-interface> -n
# Should see packets flowing across tunnel

# STEP 6: Check routing through tunnel
ip route show | grep -E "tunnel-subnet|vpn-route"
# Should have route pointing to tunnel interface

# STEP 7: For BGP, check route propagation
# If using BGP for hybrid routing:
show ip route  # On router/device
# Should show routes from remote site

# STEP 8: Monitor tunnel encapsulation
tcpdump -i <physical-interface> -n "dst <vpn-endpoint>"
# Capture encapsulated traffic to verify encryption

# STEP 9: Check IPsec security associations
sudo ipsec trafficstatus
# Shows: Active SAs and traffic volume

# STEP 10: Monitor tunnel packet loss
ping -c 100 <remote-ip-via-tunnel> | grep "%"
# Should have 0% loss; > 5% indicates issues

# STEP 11: Verify encryption parameters match
sudo ipsec statusall | grep -E "cipher|hash"
# Ensure both sides match: DES/AES, MD5/SHA256

# STEP 12: Check NAT traversal if behind NAT
# For IPsec: ipsec trafficstatus | grep NAT
# Shows: If NAT-T is active
```

**VPN connectivity diagnostics**:
```bash
# Test end-to-end latency through tunnel
ping -c 10 <on-prem-app> | awk -F'/' '{print $(NF-1)}'
# Extract RTT; typical < 50ms for cloud

# Trace route through tunnel
traceroute <on-prem-ip>
# Should show tunnel device in path

# Check MTU through tunnel (may be reduced)
ping -M do -s 1472 <remote-ip>  # Test with MTU 1500
# If fails, may need to reduce local MTU

# Monitor tunnel interface counters
ip -s link show <tunnel-interface>
# Check: RX/TX errors, dropped packets

# For hybrid cloud, verify BGP convergence
show bgp summary  # Router
# All neighbors should be in "Established" state
```

**VPN tunnel recovery**:
```bash
# Restart VPN service
# IPsec:
sudo systemctl restart strongswan

# WireGuard:
sudo ip link del wg0  # Remove interface
sudo ip link add wg0 type wireguard  # Recreate
sudo wg set wg0 listen-port 51820 private-key /path/to/key  # Reconfigure

# Reconnect BGP sessions if stuck
# On router: clear bgp <neighbor-ip>
# Causes BGP to re-establish; routes may be re-propagated

# Force tunnel re-negotiation
# IPsec: ipsec down all && ipsec up all
# WireGuard: sudo wg set wg0 peer <pubkey> endpoint <ip>:<port>
```

**Hybrid cloud routing verification**:
```bash
# From cloud, verify route to on-prem exists
ip route show | grep <on-prem-subnet>

# Check if on-prem DNS is accessible
nslookup <on-prem-hostname> <on-prem-dns-ip>

# Monitor cross-site application traffic
tcpdump -i <tunnel-interface> -n "host <on-prem-app>" -c 20
# Verify traffic is actually flowing
```

**Commands to NEVER use in production**:
```bash
# ❌ NEVER: Kill VPN process without graceful shutdown
#    Use: systemctl stop vpn-service
# ❌ NEVER: Change IPsec keys without coordination
#    Breaks all VPN connections
# ❌ NEVER: Disable tunnel without alternate route
#    Isolates sites from each other
```

---

## Scenario: Diagnosing Docker/Container Networking Issues

**Prerequisites**: Container cannot reach network, port mapping fails, container-to-host communication broken  
**Common Causes**: Docker daemon issue, network driver misconfigured, port conflict, bridge network down

```bash
# STEP 1: Check Docker daemon status
systemctl status docker
docker ps -a  # Should work if daemon healthy

# STEP 2: Verify Docker networks exist
docker network ls
# Should show: bridge, host, none, + custom networks

# STEP 3: Inspect container network
docker inspect <container-id> | jq '.NetworkSettings'
# Shows: IP address, network name, port mappings

# STEP 4: Test container can reach gateway
docker exec <container> ping -c 4 $(docker inspect <container> | jq -r '.[0].NetworkSettings.Gateway')
# Should show gateway reachable

# STEP 5: Check published ports
docker ps | grep <container>
# Look for: Port mappings (e.g., 0.0.0.0:8080->80/tcp)

# STEP 6: Test port from host
netstat -tlnp | grep <port>
# Should show: docker-proxy or docker listening

# STEP 7: Test connectivity to published port
curl -v localhost:<port>
# Should connect; if fails, check firewall

# STEP 8: Verify container network driver
docker inspect <container> | jq '.HostConfig.NetworkMode'
# Shows: bridge, host, container:xxx, or none

# STEP 9: Check bridge network configuration
docker network inspect <network-name> | jq '.IPAM'
# Shows: Subnet and gateway for network

# STEP 10: Monitor container network interface
docker exec <container> ip link show
docker exec <container> ip addr show
# Shows: eth0 (usually) with IP address

# STEP 11: Check for port conflicts
docker ps -a | grep -E "0.0.0.0:<port>"
# May show another container using same port

# STEP 12: Verify DNS inside container
docker exec <container> cat /etc/resolv.conf
# Should list docker's embedded DNS (127.0.0.11)
```

**Container networking diagnostics**:
```bash
# Test connectivity between containers
docker exec <container1> ping -c 4 <container2-ip>

# Check container's default route
docker exec <container> ip route show

# Verify container can reach Docker host
docker exec <container> ping -c 4 $(docker inspect <container> | jq -r '.[0].NetworkSettings.Gateway')

# Monitor port forwarding on host
watch -n 1 'netstat -tlnp | grep docker-proxy'
# Shows active port forwards and packet count

# Check iptables rules for container
iptables -L -n | grep <container-ip>
# May show DNAT rules for port mapping
```

**Docker networking recovery**:
```bash
# Restart Docker daemon
systemctl restart docker

# Recreate bridge network
docker network rm bridge-name  # Remove old network
docker network create --driver bridge bridge-name  # Create new

# Reconnect container to network
docker network disconnect <network-name> <container>
docker network connect <network-name> <container>

# Fix port mapping (requires container restart)
docker stop <container>
docker rm <container>
docker run -p <host-port>:<container-port> <image>

# Clean up dangling networks
docker network prune
```

**Commands to NEVER use in production**:
```bash
# ❌ NEVER: docker network rm to the default bridge
#    Requires complete Docker restart to recover
# ❌ NEVER: Modify iptables rules for Docker containers
#    Docker may overwrite on restart
# ❌ NEVER: docker stop with -t 0 on stateful containers
#    No graceful shutdown; data loss possible
```

---

## Scenario: Diagnosing Firewall and Security Policy Issues

**Prerequisites**: Traffic is blocked, services unreachable despite being up, policies too restrictive  
**Common Causes**: Firewall rule misconfigured, security group blocking, SELinux/AppArmor denying, ACL mismatch

```bash
# STEP 1: Check firewall status
systemctl status ufw  # Ubuntu
systemctl status firewalld  # CentOS/RHEL
iptables -L -n | head -20  # Direct iptables

# STEP 2: List firewall rules for specific port
ufw show added  # UFW
firewall-cmd --list-all  # firewalld
iptables -L -n | grep <port>  # iptables

# STEP 3: Check if port is open
ss -tlnp | grep <port>  # Service listening
nmap -p <port> localhost  # Port scan from host

# STEP 4: Test firewall from remote
nmap -p <port> <host-ip>
# From remote machine: shows if port accessible

# STEP 5: Check security group (cloud environments)
# AWS: describe-security-groups --group-ids <sg-id>
# Shows: Ingress/egress rules

# STEP 6: Monitor firewall logs
tail -f /var/log/ufw.log  # UFW
journalctl -u firewalld -f  # firewalld
grep -i "dropped\|denied" /var/log/messages  # iptables

# STEP 7: Check SELinux context blocking (if enabled)
getenforce  # Check status
getsebool -a | grep http  # Get booleans
semanage fcontext -l | grep -i <port>  # File contexts

# STEP 8: Test with firewall disabled (diagnostic only)
systemctl stop ufw  # or firewalld
# Test connectivity, then restart

# STEP 9: Check for egress rules blocking outbound
# UFW: ufw show added | grep "OUT"
# firewalld: firewall-cmd --list-rich-rules | grep "egress\|reject"

# STEP 10: Verify traffic reaching interface
tcpdump -i <interface> -n "tcp port <port>" -c 10
# If packets arrive, firewall is blocking; if not, network issue

# STEP 11: Check cloud provider security policies
# AWS: describe-network-acls
# Azure: az network nsg show
# GCP: gcloud compute firewall-rules list

# STEP 12: Monitor failed connection attempts
tail -f /var/log/auth.log | grep -i "refused\|denied"
# May show connection attempts being rejected
```

**Firewall rule diagnostics**:
```bash
# Get detailed firewall rules
iptables -L -n -v  # Verbose output
firewall-cmd --list-rich-rules  # Rich rules (more readable)

# Test specific rule
# Create temporary rule, test, then delete

# Check if traffic matches rule
iptables -L -n | grep -E "<src-ip>|<dst-ip>|<port>"

# Monitor firewall state
watch -n 1 'iptables -L -n | grep policy'
# Shows: Default policies (DROP, ACCEPT)
```

**Firewall rule management**:
```bash
# Add allow rule for port/service
ufw allow 8080  # UFW
firewall-cmd --permanent --add-port=8080/tcp  # firewalld
# Then reload: firewall-cmd --reload

# Delete rule
ufw delete allow 8080
firewall-cmd --permanent --remove-port=8080/tcp

# Allow from specific IP/subnet
ufw allow from 10.0.0.0/8 to any port 8080
firewall-cmd --permanent --add-rich-rule 'rule family="ipv4" source address="10.0.0.0/8" port protocol="tcp" port="8080" accept'

# Test rule before applying
iptables-save > /tmp/rules.backup  # Backup current
# Test new rules, if good, make permanent
iptables-restore < /tmp/rules.backup  # Restore if needed
```

**Commands to NEVER use in production**:
```bash
# ❌ NEVER: iptables -F without saving current rules
#    All firewall rules deleted; service exposed
# ❌ NEVER: firewall-cmd --set-default-zone=trusted
#    Disables all security; complete exposure
# ❌ NEVER: Disable firewall entirely to "fix" connectivity
#    Use proper rules instead
```

---

## Scenario: Diagnosing Load Balancer and High Availability Issues

**Prerequisites**: Traffic not distributed, some backends always unavailable, failover not working  
**Common Causes**: Health check failing, unequal backend capacity, sticky sessions misconfigured, backend unreachable

```bash
# STEP 1: Check load balancer service status
kubectl get svc <lb-service> -n <namespace>
# Shows: EXTERNAL-IP, should be assigned (not <pending>)

# STEP 2: Verify backend endpoints
kubectl get endpoints <lb-service> -n <namespace>
# Should list all healthy backend pod IPs

# STEP 3: Monitor load balancer metrics (if available)
kubectl top pod <lb-pod> -n <namespace>
# Shows: CPU and memory usage

# STEP 4: Check load balancer logs
kubectl logs <lb-pod> -n <namespace> --tail=50
# Look for: Error messages, connection failures

# STEP 5: Test connection to load balancer
nc -zv <lb-external-ip> <port>
# Should connect successfully

# STEP 6: Check backend health
kubectl exec -it <lb-pod> -n <namespace> -- \
  curl -s http://<backend-ip>:<port>/health
# Should show healthy status

# STEP 7: Verify load balancing algorithm
kubectl get svc <lb-service> -n <namespace> -o yaml | grep -i "sessionAffinity"
# ClientIP = sticky sessions, None = round-robin

# STEP 8: Monitor connection distribution
for i in {1..10}; do
  kubectl exec -it <lb-pod> -- curl -s http://backend/hostname
done
# Should see different backend hostnames (if round-robin)

# STEP 9: Check for asymmetric routing
# From client: traceroute <lb-ip>
# From backend: traceroute <client-ip>
# Paths should be similar (not completely opposite)

# STEP 10: Monitor active connections
kubectl exec -it <lb-pod> -- netstat -tlnp | grep -E "ESTABLISHED|LISTEN"
# Shows: Connection count and state

# STEP 11: Check for connection resets
kubectl exec -it <lb-pod> -- netstat -s | grep -i "reset"
# High reset count = backend or network issue

# STEP 12: Verify no single backend is overloaded
for backend in <backend-list>; do
  kubectl exec -it <lb-pod> -- curl -s http://$backend/metrics | grep requests_total | tail -1
done
# Should see similar request counts across backends
```

**Load balancer troubleshooting**:
```bash
# Test individual backend directly (bypass LB)
curl -v http://<backend-direct-ip>:<port>
# If works, issue is with LB; if fails, backend is the problem

# Check health check configuration
kubectl describe svc <lb-service> | grep -i "health\|check"

# Monitor load balancer session table
kubectl exec -it <lb-pod> -- ss -an | grep ESTABLISHED | wc -l
# Count of active connections

# Trace requests through load balancer
kubectl exec -it <lb-pod> -- tcpdump -i eth0 -n "tcp" | head -20
```

**Load balancer recovery**:
```bash
# Restart load balancer service
kubectl rollout restart deployment <lb-deployment> -n <namespace>

# Force health check on backends
kubectl exec -it <lb-pod> -- kill -HUP <pid>  # Reload config

# Adjust load balancer timeout settings
kubectl patch svc <lb-service> -n <namespace> -p \
  '{"spec":{"sessionAffinityConfig":{"clientIP":{"timeoutSeconds":10800}}}}'

# Scale load balancer replicas
kubectl scale deployment <lb-deployment> -n <namespace> --replicas=3
```

**Commands to NEVER use in production**:
```bash
# ❌ NEVER: Delete load balancer service without redirect
#    All external traffic to service is lost
# ❌ NEVER: Reduce health check timeout too low
#    Causes flapping backends (up/down/up)
# ❌ NEVER: Change load balancing algorithm during traffic
#    Can cause connection resets
```

---

## Scenario: Diagnosing Bandwidth Bottlenecks and Performance Issues

**Prerequisites**: Network throughput low, latency high, slow file transfers  
**Common Causes**: Network congestion, QoS policy throttling, packet loss, suboptimal routing, bandwidth limit configured

```bash
# STEP 1: Check interface throughput
iftop -i <interface> -n
# Shows: Real-time bandwidth usage by connection

# STEP 2: Monitor aggregate bandwidth
nethogs -t  # By process
bwm-ng  # Bandwidth monitoring (if installed)
# Shows: Total bandwidth in/out

# STEP 3: Check for packet loss
ping -c 100 <remote> | grep "%"
# > 1% loss indicates network issues

# STEP 4: Measure latency
ping -c 10 <remote> | awk -F'/' '{print "RTT:", $(NF-1)}'
# Should be < 50ms for cloud, < 1ms for same datacenter

# STEP 5: Check TCP window size
ss -i | grep <connection> | awk '{print "Window:", $5}'
# Larger window = better throughput

# STEP 6: Test actual throughput (iperf)
# Terminal 1: iperf3 -s  # Server mode
# Terminal 2: iperf3 -c <server-ip>
# Shows: Actual TCP throughput achievable

# STEP 7: Check for TCP retransmissions
netstat -s | grep -E "retrans|lost"
# High count = packet loss or congestion

# STEP 8: Monitor QoS queue status
# For Linux TC: tc qdisc show
# Shows: Configured traffic shaping

# STEP 9: Check for bandwidth limiting
tc filter show dev <interface>
# May show rate-limiting rules

# STEP 10: Monitor CPU during transfers
top -p <transfer-process>
# High CPU = CPU-bound (not network-bound)

# STEP 11: Check interface driver offloading
ethtool -k <interface> | grep offload
# Should have TSO, GSO, GRO enabled for performance

# STEP 12: Monitor packet processing
cat /proc/interrupts | grep <interface>
# High interrupt count = heavy traffic load
```

**Performance diagnostics**:
```bash
# Detailed throughput test
iperf3 -c <server> -t 60 -P 4  # 4 parallel streams, 60 seconds

# UDP throughput test
iperf3 -c <server> -u -b 1G  # 1Gbps UDP

# Jitter measurement
ping -c 100 <remote> | awk 'NR>1{printf "%d\n", $(NF-1)}' | \
  awk 'NR==1{prev=$1; next} {print ($1-prev); prev=$1}' | \
  awk '{sum+=($1*$1)} END {print sqrt(sum/NR)}'  # Standard deviation

# Route efficiency (check for suboptimal paths)
traceroute <remote>
# Compare hop count with expected value
```

**Network optimization**:
```bash
# Increase TCP buffer sizes
sysctl -w net.ipv4.tcp_rmem="4096 87380 134217728"
sysctl -w net.ipv4.tcp_wmem="4096 65536 134217728"

# Enable TCP window scaling
sysctl -w net.ipv4.tcp_window_scaling=1

# Tune congestion control algorithm
# View options: cat /proc/sys/net/ipv4/tcp_available_congestion_control
sysctl -w net.ipv4.tcp_congestion_control=bbr  # BBR for high-speed networks

# Remove bandwidth limit if configured
tc qdisc del dev <interface> root  # Remove traffic shaping
```

**Commands to NEVER use in production**:
```bash
# ❌ NEVER: tc qdisc del without understanding current config
#    May remove intentional traffic shaping
# ❌ NEVER: Enable CPU offloading without driver support
#    Can cause packet drops or corruption
# ❌ NEVER: Run bandwidth tests during peak hours
#    Can congest network for other users
```

---

## Scenario: Diagnosing Container Registry Network Issues (On-Prem to Cloud)

**Prerequisites**: Image pulls slow, timeout during push, registry unreachable from cluster  
**Common Causes**: Registry across WAN slow, bandwidth-limited, VPN tunnel congested, DNS slow

```bash
# STEP 1: Measure latency to registry
ping -c 4 <registry-ip>
# Should be < 100ms; > 500ms indicates issue

# STEP 2: Check DNS resolution of registry
nslookup <registry-hostname>
# Should resolve quickly

# STEP 3: Test basic connectivity to registry
curl -I https://<registry>/v2/
# Should return 200 or 401, not timeout

# STEP 4: Measure download speed from registry
time curl -o /dev/null https://<registry>/v2/<image>/manifests/<digest>
# Note time to download; typical: 1-5 seconds per MB

# STEP 5: Check network path to registry
traceroute <registry-ip>
# Should take < 20 hops; > 30 hops may have routing issues

# STEP 6: Monitor throughput to registry
iftop -i <interface> -n | grep <registry-ip>
# Shows: Current bandwidth to registry

# STEP 7: Test image pull performance
time docker pull <registry>/<image>:tag
# Measure total pull time

# STEP 8: Check for packet loss on path
mtr -r -c 100 <registry-ip> | tail -3
# mtr (like traceroute with packet loss)

# STEP 9: Verify VPN/tunnel is active (if on-prem)
ipsec status  # For IPsec tunnel
ip link show wg0 | grep UP  # For WireGuard
# Should show tunnel is active

# STEP 10: Check bandwidth allocation to registry traffic
# For QoS: tc filter show dev <interface>
# May show rate limits on registry destination

# STEP 11: Monitor concurrent pulls
# During pull: watch -n 1 'netstat -an | grep <registry-ip> | wc -l'
# Shows: Number of connections

# STEP 12: Check layer caching (may speed up pulls)
docker inspect <image> | jq '.RootFS.Layers | length'
# Shows: Number of layers; cached layers are faster
```

**Registry performance diagnostics**:
```bash
# Detailed curl with timing
curl -w '\nTime: %{time_total}s\n' https://<registry>/v2/<image>/manifests/latest

# Test with compression disabled
curl -H "Accept-Encoding: identity" https://<registry>/v2/<image>/blobs/<digest>

# Monitor concurrent connections
watch -n 1 'netstat -an | grep <registry-ip> | grep ESTABLISHED | wc -l'

# Check registry backend connectivity (if applicable)
time docker pull <registry>/<image>:tag 2>&1 | grep -E "Pull|Download"
```

**Registry connectivity optimization**:
```bash
# Configure image pull policy to prefer local cache
# Pod spec: imagePullPolicy: IfNotPresent

# Pre-load images on nodes
# DaemonSet that pulls images on all nodes at off-peak time

# Enable registry mirroring/caching
# Configure Docker daemon: registry-mirrors in /etc/docker/daemon.json

# For on-prem to cloud, optimize tunnel
# Increase VPN throughput: increase MTU, tune TCP windows

# Local registry proxy
# Deploy Nexus or Harbor in cluster to cache images locally

# Parallel image pulls
# Configure kubelet: max-concurrent-downloads=10
```

**Commands to NEVER use in production**:
```bash
# ❌ NEVER: Disable SSL verification to "speed up" pulls
#    Security risk; attack surface exposed
# ❌ NEVER: Reduce image pull timeout to zero
#    Prevents pull completion
# ❌ NEVER: Kill image pull process without cleanup
#    Partial layers left, next pull takes longer
```

---

## Scenario: Diagnosing CI/CD Network Connectivity Issues

**Prerequisites**: CI/CD runners cannot reach artifact servers, webhook delivery failing, build dependencies timeout  
**Common Causes**: Network isolation, firewall blocking, proxy misconfigured, DNS not resolving

```bash
# STEP 1: Verify build runner can reach git server
git clone https://<git-server>/<repo>  # From runner
# Should succeed without timeout

# STEP 2: Check artifact server connectivity from runner
curl -I https://<artifact-server>/artifactory
# Should return 200 or auth error, not connection refused

# STEP 3: Test artifact download speed
time curl -o artifact.tar.gz https://<artifact-server>/artifacts/<file>
# Should be < expected download time

# STEP 4: Verify webhook destination is accessible
curl -I https://<webhook-receiver>:8080/webhook
# Should be reachable from CI/CD platform

# STEP 5: Check DNS from build runner
nslookup <artifact-server>
# Should resolve quickly

# STEP 6: Test proxy connectivity (if behind corporate proxy)
curl -v -x http://<proxy>:8080 https://<artifact-server>
# Should work if proxy configured correctly

# STEP 7: Monitor build runner network usage
iftop -i <interface> -n
# Shows: Network activity during build

# STEP 8: Check for firewall rules on runner
iptables -L -n | grep <artifact-server-ip>
# May show blocked connections

# STEP 9: Test artifact push performance (for registry)
time docker push <registry>/<image>:tag
# Measure push speed; should be reasonable

# STEP 10: Verify build dependencies are reachable
# From runner, test critical dependency URLs:
curl -I https://repo.maven.apache.org/maven2/
curl -I https://hub.docker.com/v2/
curl -I https://registry.npmjs.org/

# STEP 11: Check bandwidth allocation to CI/CD
# Monitor: watch -n 1 'iftop -i eth0 -n'
# May show if CI/CD traffic is limited

# STEP 12: Test webhook delivery logs
# Check CI platform logs for webhook failures
# May show: timeout, DNS error, connection refused
```

**CI/CD network diagnostics**:
```bash
# Build with verbose networking output
# Docker: docker build --progress=plain
# Maven: mvn -X (includes HTTP requests)
# npm: npm install --verbose

# Monitor build dependencies download
# Maven: watch -n 1 'lsof -i | grep java'
# Shows: Connections to dependency servers

# Check proxy latency
time curl -x http://<proxy>:8080 https://<external-url>

# Trace webhook delivery
# Enable debug logging on webhook receiver
# Monitor: tcpdump to capture webhook packets
```

**CI/CD network optimization**:
```bash
# Cache dependencies locally
# Maven: ~/.m2 repository mirroring
# Docker: image caching and pulling from local registry
# npm: npm cache (local node_modules)

# Use faster mirrors for dependencies
# Maven: configure mirror in settings.xml
# npm: configure registry in .npmrc

# Pre-download critical artifacts
# DaemonSet in cluster to cache images
# Build step to cache Maven/npm repositories

# Configure parallel downloads
# Maven: -T 1C (1 thread per core)
# Docker: max-concurrent-downloads in daemon.json
```

**Commands to NEVER use in production**:
```bash
# ❌ NEVER: Run CI/CD tests over unencrypted HTTP
#    Credentials may be exposed
# ❌ NEVER: Disable SSL verification for speed
#    Security risk; MITM attacks possible
# ❌ NEVER: Store artifact server credentials in build logs
#    Use environment variables or secrets instead
```

---

## Scenario: Diagnosing BGP and Complex Routing Issues

**Prerequisites**: Routes not propagating, multi-path routing not balanced, convergence slow after changes  
**Common Causes**: BGP session down, AS path misconfigured, next-hop unreachable, route priority incorrect

```bash
# STEP 1: Check BGP session status (requires BGP router access)
show bgp summary
# Shows: BGP neighbor state (Established/Down)

# STEP 2: Verify BGP routes are being advertised
show bgp ipv4 unicast summary
# Shows: Prefixes received/sent per neighbor

# STEP 3: Check specific route in BGP table
show bgp ipv4 unicast <prefix>
# Shows: Available paths and path attributes

# STEP 4: Verify best path selection
show bgp ipv4 unicast <prefix> detail
# Shows: Why specific path is selected

# STEP 5: Monitor BGP convergence time after change
# Before: note time
# After change: measure until route stable
show bgp ipv4 unicast | include flap  # CISCO format

# STEP 6: Check AS path for loops or issues
show bgp ipv4 unicast <prefix> | grep "AS path"
# Look for: Unnecessary AS hops or missing ASes

# STEP 7: Verify communities are set correctly
show route <prefix> detail | grep "community"
# Shows: BGP community values

# STEP 8: Check route dampening status (if configured)
show bgp ipv4 unicast dampening flap-statistics
# Shows: Flappy routes being suppressed

# STEP 9: Verify MPLS labels (for traffic engineering)
show mpls forwarding-table
# Shows: Label-to-prefix mapping

# STEP 10: Monitor BGP packet exchange
# Enable debugging: debug bgp packets
# Shows: BGP OPEN, UPDATE, KEEPALIVE messages

# STEP 11: Check for route summarization issues
show route summary
# Shows: Route count and memory usage

# STEP 12: Verify next-hop reachability
show ip route <next-hop-ip>
# Must be reachable locally
```

**BGP troubleshooting procedures**:
```bash
# Clear BGP session to force re-establishment
clear bgp <neighbor-ip>
# Causes BGP to re-negotiate and re-send routes

# Verify BGP configuration
show run | include bgp
# Shows: All BGP configuration statements

# Debug BGP route selection
debug bgp keepalives  # Minimal output
debug bgp updates     # Detailed updates
# Then clear output: undebug all

# Check for route redistribution issues
show ip bgp summary
# Compare advertised/received counts

# Verify network statement configuration
show run | include network
# Each advertised prefix needs network statement
```

**Routing convergence optimization**:
```bash
# Reduce BGP keepalive timers for faster convergence
# neighbor <ip> timers 3 9  # 3 second keepalive, 9 second holddown

# Enable BFD for faster failure detection
# neighbor <ip> fall-over bfd single-hop
# Or configure BFD parameters separately

# Set BGP MED for load balancing
# route-map set metric <value>

# Increase BGP router ID stability
# bgp router-id <stable-ip>
```

**Commands to NEVER use in production**:
```bash
# ❌ NEVER: clear bgp * (clear all BGP sessions)
#    Causes network-wide routing convergence delay
# ❌ NEVER: Delete default route to "fix" routing
#    Breaks reachability to all networks
# ❌ NEVER: Modify BGP AS number during active sessions
#    Requires session restart; traffic loss
```

---

## Critical Network Debugging Principles

### OSI Layer Breakdown
```
Layer 1 (Physical):    Cables, interfaces, signals
Layer 2 (Data Link):   MAC, switches, VLANs, ARP
Layer 3 (Network):     IP, routing, BGP, traceroute
Layer 4 (Transport):   TCP/UDP, ports, connections
Layer 5-7 (Session/Presentation/Application): DNS, HTTP, services
```

### Debugging Methodology
```
1. Verify physical connectivity (ping, cables)
   ↓
2. Check Layer 2 (ARP, VLAN, MAC tables)
   ↓
3. Verify routing (route table, BGP)
   ↓
4. Check port-level connectivity (nc, telnet)
   ↓
5. Test application protocol (HTTP, DNS, etc.)
   ↓
6. Analyze performance (latency, throughput, packet loss)
   ↓
7. Document root cause and solution
```

### Network Monitoring Hierarchy
1. **High-level**: Ping, curl, service availability
2. **Medium-level**: netstat, ss, route table
3. **Deep-level**: tcpdump, strace, packet analysis
4. **Infrastructure**: BGP, QoS, load balancer state

### Common Bottlenecks
- **Bandwidth**: Congestion, QoS limits, ISP throttling
- **Latency**: Long distances, routing issues, buffer delays
- **Loss**: Congestion, hardware failure, duplex mismatch
- **DNS**: CoreDNS down, cache issues, resolver misconfigured
- **Security**: Firewall rules, NAT issues, SSL cert validation

### Hybrid Cloud Connectivity Checklist
```
✓ VPN tunnel up and active
✓ Routes propagated via BGP
✓ DNS resolves from both sides
✓ Health checks passing
✓ MTU compatible (no fragmentation)
✓ No asymmetric routing
✓ Firewall allows necessary ports
✓ Security groups/NACLs configured
✓ Time synchronized (certificates)
✓ Bandwidth sufficient for workload
```

### Tools Required for Production
```
Basic:
- ping, traceroute, dig, nslookup
- netstat, ss, ip command
- iptables, ufw, firewall-cmd
- curl, wget, nc (netcat)

Advanced:
- tcpdump, wireshark
- iperf, mtr, nethogs
- strace, ltrace
- ethtool, lspci
- bgp tools (show commands on routers)
```

### Dangerous Network Commands
```bash
# CRITICAL - NEVER in production:
iptables -F without save                    # Clear all rules
ip route del default                        # Remove default gateway
systemctl stop networking while SSH'd       # Lose connectivity
tc qdisc del root (without understanding)   # Remove traffic shaping
ipsec down all                              # Tear down all VPNs
ip link set <interface> down                # Disable interface
firewall-cmd --set-default-zone=trusted     # Disable firewall
```

### Network Incident Response Checklist
1. [ ] Document baseline (normal state)
2. [ ] Identify affected services
3. [ ] Check physical layer (cables, interfaces)
4. [ ] Check routing (tables, BGP convergence)
5. [ ] Check firewalls (rules, logs)
6. [ ] Test with/without specific network devices
7. [ ] Verify DNS resolution
8. [ ] Check application logs (correlation)
9. [ ] Measure latency, loss, throughput
10. [ ] Implement fix with rollback plan
11. [ ] Validate resolution
12. [ ] Document root cause
13. [ ] Update runbooks

---

**Last Updated**: January 2026  
**Network Stack**: TCP/IP, Kubernetes networking  
**OSI Layers**: Comprehensive L1-L7  
**Severity Level**: Production Critical  
**Review Frequency**: Quarterly