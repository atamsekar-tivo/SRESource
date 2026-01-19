# Linux Internals for Containers, Performance, and Security

> **How to use this page**: This is the kernel-and-host companion to `production-debugging-unix-linux.html`. It focuses on container primitives (namespaces/cgroups), tracing syscalls, kernel networking, and host hardening. Use read-only commands first; run perf/strace only when impact is acceptable.

---

## Container Isolation: Namespaces

```bash
# List namespaces per PID (verify container isolation)
lsns -p <PID>

# Enter a pod's namespaces from the node (root required)
nsenter -t <PID> --mount --uts --ipc --net --pid bash

# Launch an isolated test shell (no network)
unshare -n -m -p --fork --mount-proc bash

# Inspect PID namespace + hostname details
cat /proc/<PID>/status | grep -E "NSpid|Pid|PPid"
hostnamectl
```

---

## Resource Control: cgroups v2

```bash
# Locate a process cgroup and effective limits
cat /proc/<PID>/cgroup
systemd-cgls /sys/fs/cgroup
cat /sys/fs/cgroup/<slice>/cpu.max      # quota/period (e.g., "200000 100000")
cat /sys/fs/cgroup/<slice>/memory.max   # bytes (max for unlimited)

# Live usage by cgroup (great for kubelet-managed pods)
systemd-cgtop

# Pressure stall information (detect contention)
cat /proc/pressure/cpu
cat /proc/pressure/memory
cat /proc/pressure/io
```

---

## Syscalls, Scheduling, and Tracing

```bash
# Low-impact syscall mix and latency
strace -f -tt -p <PID> -c -s 80   # Run briefly; adds overhead

# CPU/scheduler counters for a PID
perf stat -p <PID> sleep 10       # Cycles, instructions, context switches

# Call stacks for hot paths (perf record/report)
perf record -g -p <PID> -- sleep 15
perf report

# eBPF-powered oneliners (if bcc/tools available)
execsnoop     # Show new exec() calls
opensnoop    # Show open() calls
tcplife      # TCP life events (connections)

# Kernel ftrace quick tap
trace-cmd record -p function_graph -l '<module>*' sleep 5
trace-cmd report | head -100
```

---

## Networking Internals (Services, Load-Balancing)

```bash
# kube-proxy rules (iptables mode)
iptables -t nat -L KUBE-SERVICES -n -v --line-numbers | head
iptables -t nat -L KUBE-POSTROUTING -n -v | head

# nftables mode (some distros)
nft list ruleset | head -80

# Conntrack table health
conntrack -L | head
sysctl net.netfilter.nf_conntrack_count
sysctl net.netfilter.nf_conntrack_max

# Socket-level view
ss -Htnp state established | head
ss -Htn 'sport = :6443' | head   # API server traffic

# Traffic control queues (detect drops)
tc -s qdisc show dev eth0
```

---

## Filesystems, I/O, and Storage

```bash
# Mount + namespace view for a PID
lsns -t mnt -p <PID>
findmnt -R /var/lib/kubelet/pods | head

# Disk and inode pressure
df -hT
df -i

# Per-PID I/O load
pidstat -d 1 5
iotop -P -b -n 3 | head

# File descriptor and open files
ls -l /proc/<PID>/fd | head
lsof -p <PID> | head
```

---

## Systemd + Kubelet on the Host

```bash
systemctl status kubelet
journalctl -u kubelet -b -n 200
systemd-analyze blame | head        # Slow boot units
systemd-cgls                         # Inspect unit/pod cgroups tree
```

---

## Security Primitives: seccomp, AppArmor, SELinux

```bash
# Current seccomp mode per process
ps -eo pid,comm,seccomp | head

# AppArmor profile status (Debian/Ubuntu)
aa-status
apparmor_status

# SELinux enforcement and denials (RHEL/CentOS/Fedora)
getenforce
ausearch -m avc -ts recent | head
semanage boolean -l | head

# Auditd syscall watch (example: chmod)
auditctl -l
auditctl -w /bin/chmod -p x -k chmod-watch
ausearch -k chmod-watch | tail
```

---

## Performance Quick Wins (host-level)

```bash
# One-liners for hotspots
vmstat 1 5                     # Run-queue, swap, system time
pidstat -u -r -d 1 5           # CPU/mem/I/O per PID
perf top --no-children --sort comm,dso  # CPU hotspots live

# NUMA awareness (latency issues)
numactl --hardware
numastat -p <PID>

# Page cache and dirty pages
cat /proc/meminfo | egrep 'Dirty|Writeback'
```

---

## When to Escalate

- If pressure stall info (PSI) stays high for CPU/memory/I/O, capture perf/strace and involve kernel/SRE.  
- If conntrack hits `nf_conntrack_max`, increase the table only with business approval and in maintenance.  
- If seccomp/AppArmor/SELinux denials block pods, adjust profiles via Kubernetes policy rather than disabling globally.  
- Always capture before/after metrics and reference the broader runbook: `production-debugging-unix-linux.html`.
