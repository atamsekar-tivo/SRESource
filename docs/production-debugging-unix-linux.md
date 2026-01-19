# Production Debugging Commands for Unix/Linux

> **Critical Context**: Always perform diagnosis on non-production systems first when possible. Use read-only commands initially. Document all changes with timestamp and reason.

---

## Linux Internals Quick Start (see `linux-internals.html` for deep dive)

```bash
# Identify namespace/cgroup context for a PID
lsns -p <PID>         # Namespaces (pid, net, mnt, uts, user)
cat /proc/<PID>/cgroup
nsenter -t <PID> --mount --uts --ipc --net --pid bash  # Enter all namespaces (root only)

# Check cgroup v2 limits on a node
cat /sys/fs/cgroup/cpu.max      # CPU quota/period
cat /sys/fs/cgroup/memory.max   # Memory limit (max for unlimited)
systemd-cgtop                   # Live cgroup CPU/mem I/O usage

# Fast syscall + scheduler sanity
pidstat -u -r -d 1 5            # CPU/mem/I/O per PID
strace -f -tt -p <PID> -c -s 80 # Syscalls + time (use briefly)
perf stat -p <PID> sleep 10     # High-level CPU counters

# Kernel networking dataplane (Service/Pod routing)
iptables -t nat -L KUBE-SERVICES -n -v --line-numbers | head
nft list ruleset | head -50           # If nftables is enabled
conntrack -L | head                  # Conntrack state table

# Security posture quick view
ps -eo pid,comm,seccomp | head       # Seccomp status
aa-status 2>/dev/null || true        # AppArmor profiles (Debian/Ubuntu)
getenforce 2>/dev/null || echo "SELinux not enabled"  # SELinux mode
```

## Scenario: Diagnosing High CPU Utilization

**Prerequisites**: CPU usage consistently > 80%, application performance degraded  
**Common Causes**: Runaway process, busy-wait loop, insufficient scaling, memory pressure causing swapping

```bash
# STEP 1: Get overall CPU usage
top -b -n 1 | head -20
# Shows: Load average, per-CPU usage, top processes

# STEP 2: Identify top CPU consumers
ps aux --sort=-%cpu | head -10
# Shows: User, PID, CPU%, memory%, command
# CAVEAT: Snapshot only; use repeatedly to identify sustained high usage

# STEP 3: Monitor CPU in real-time
top -p <PID>
# Shows: Real-time CPU, memory, threads for specific process
# Press: 1 (show per-CPU), q (quit)

# STEP 4: Check per-CPU breakdown
mpstat -P ALL 1 5
# PREREQUISITE: sysstat package installed
# Shows: 5 iterations of 1-second intervals for all CPUs

# STEP 5: Identify CPU contention
sar -P ALL -u 1 5
# Shows: CPU utilization history including I/O wait (%iowait)
# CAVEAT: %iowait > 50% indicates I/O bottleneck, not CPU

# STEP 6: Check process threads
ps -eLf | grep <process-name> | wc -l
# Shows: Number of threads in process
# POST-REQ: Compare with expected thread count

# STEP 7: Examine process CPU affinity
taskset -p <PID>
# Shows: Which CPU cores process is pinned to
# CAVEAT: May see hex mask; convert with: printf "%d\n" 0x<hex>

# STEP 8: Check for context switching overhead
vmstat 1 5 | tail -3
# Look for: cs (context switches) - if > 100000/sec, high contention
# Also look for: sy (system time) - excessive kernel time

# STEP 9: Profile with strace (WARNING: high overhead)
strace -c -p <PID> sleep 10
# Shows: System calls and time spent in each
# PREREQUISITE: Process must be running
# WARNING: Slows down process significantly; use in non-critical only

# STEP 10: Check scheduler information
cat /proc/<PID>/status | grep -E "VmPeak|Threads|voluntary_ctxt_switches|nonvoluntary_ctxt_switches"
```

**Advanced CPU profiling** (application-dependent):
```bash
# For compiled binaries with perf (Linux)
perf record -p <PID> -F 99 sleep 10
perf report
# Shows: Flamegraph of CPU usage by function

# For Python
python -m cProfile -s cumtime <script.py>

# For Java
jcmd <PID> Compiler.codelist | head -20
jcmd <PID> JFR.start duration=60s filename=/tmp/recording.jfr
```

**CPU optimization commands**:
```bash
# Adjust process nice level (priority)
nice -n 10 <command>  # Lower priority (0 to 19, higher = lower priority)
renice -n 5 -p <PID>  # Change priority of running process

# Pin process to specific CPUs
taskset -cp 0,1,2 <PID>

# Enable CPU frequency scaling if available
cpupower frequency-set -g powersave
```

**Commands to NEVER use in production**:
```bash
# ❌ NEVER: kill -9 <PID> without investigation
#    May corrupt application state; use SIGTERM first
# ❌ NEVER: Disable CPU frequency scaling without understanding impact
#    May waste power and increase thermal issues
# ❌ NEVER: Set nice to negative without privileges
#    Creates security risk; verify sudo access required
```

---

## Scenario: Diagnosing High Memory Usage/OOM

**Prerequisites**: Memory usage > 85%, swapping occurring, OOM killer may trigger  
**Common Causes**: Memory leak, insufficient heap size, cache unbounded growth, data structure bloat

```bash
# STEP 1: Get overall memory usage
free -h
# Shows: Total, used, free, buffers, cached memory
# CAVEAT: "available" is better metric than "free" for application allocation

# STEP 2: Get memory breakdown
vmstat -s
# Shows: Detailed memory statistics including swap usage

# STEP 3: Identify top memory consumers
ps aux --sort=-%mem | head -10
# Shows: User, PID, memory %, VSZ (virtual size), RSS (resident size)
# POST-REQ: Compare VSZ vs RSS to identify memory mapping issues

# STEP 4: Monitor memory in real-time
top -o %MEM
# Press: M (sort by memory), q (quit)

# STEP 5: Check for memory leaks (Linux only)
cat /proc/<PID>/status | grep -E "VmPeak|VmHWM|VmRSS"
# Shows: Peak virtual memory, peak RSS, current RSS
# CAVEAT: VmPeak > VmRSS may indicate memory release failure

# STEP 6: Analyze heap (if application supports)
jmap -heap <PID>  # Java
gdb -ex "info proc mappings" -ex quit <PID>  # General (requires debug symbols)

# STEP 7: Check page fault rate
vmstat 1 5 | tail -3
# Look for: minflt (minor), majflt (major) - if majflt increasing, memory pressure

# STEP 8: Monitor swap usage
cat /proc/vmstat | grep pswp
# Shows: Pages swapped in/out; if increasing, memory pressure

# STEP 9: Trace memory allocations (strace)
strace -e brk,mmap,mremap -p <PID> 2>&1 | head -100
# PREREQUISITE: Process must be running
# WARNING: High overhead; use briefly only

# STEP 10: Check for OOM killer activity
dmesg | tail -50 | grep -i "oom\|killed"
# Shows: Which process was killed by OOM killer

# STEP 11: Monitor page cache
cat /proc/meminfo | grep -E "Cached|Buffers"
# Shows: Kernel page cache size; can be reclaimed if needed

# STEP 12: Check memory cgroup limits (if running in container)
cat /sys/fs/cgroup/memory/memory.limit_in_bytes
cat /sys/fs/cgroup/memory/memory.max_usage_in_bytes
```

**Memory profiling for languages**:
```bash
# Python: memory_profiler
python -m memory_profiler <script.py>

# Go: pprof
go tool pprof http://localhost:6060/debug/pprof/heap

# Node.js: clinic.js
clinic doctor -- node <script.js>

# Java: JVM heap dump
jmap -dump:live,format=b,file=/tmp/heap.dump <PID>
# Then analyze with: jhat /tmp/heap.dump
```

**Memory optimization commands**:
```bash
# Force sync and drop caches (caution!)
sync
echo 3 > /proc/sys/vm/drop_caches
# POST-REQ: Monitor application performance; may cause temporary slowdown

# Increase swap space (if available disk)
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Configure memory pressure threshold
sysctl vm.memory_pressure_level  # View current
sysctl -w vm.memory_pressure_level=50  # Adjust threshold
```

**Commands to NEVER use in production**:
```bash
# ❌ NEVER: echo 3 > /proc/sys/vm/drop_caches on live system
#    Causes page cache flush; severe performance impact
# ❌ NEVER: kill -9 to memory pressure issues
#    Application may have pending writes
# ❌ NEVER: Disable swap without increasing memory
#    Can cause cascading OOM kills
```

---

## Scenario: Diagnosing Disk Space Exhaustion

**Prerequisites**: Disk usage > 90%, application write failures, inode exhaustion  
**Common Causes**: Log file bloat, temporary files not cleaned, disk leak, core dumps, cache accumulation

```bash
# STEP 1: Check overall disk usage
df -h
# Shows: Filesystem, size, used, available, use%
# CAVEAT: "available" may differ from "free" due to reserved space

# STEP 2: Check inode usage
df -i
# Shows: Inode usage; if close to limit, many small files consuming space

# STEP 3: Find largest directories
du -sh /* 2>/dev/null | sort -rh
# Shows: Top-level directory sizes
# PREREQUISITE: Sufficient read permissions

# STEP 4: Drill down to find space hogs
du -sh /var/* 2>/dev/null | sort -rh
# Common culprits: /var/log, /var/cache, /var/tmp

# STEP 5: Find largest files
find / -type f -exec du -h {} + 2>/dev/null | sort -rh | head -20
# Shows: 20 largest files on system
# WARNING: May take time on large filesystems; specify starting directory

# STEP 6: Find large files in specific directory
find /var/log -type f -size +100M -exec ls -lh {} \;
# Shows: Log files > 100MB

# STEP 7: Check for deleted files still held open
lsof | grep deleted | head -20
# Shows: Processes holding deleted files
# POST-REQ: May need to restart service to free space

# STEP 8: Monitor disk I/O during cleanup
iotop -o
# Shows: Processes reading/writing to disk
# PREREQUISITE: iotop package installed

# STEP 9: Check disk usage trends
sar -d 1 5
# Shows: Disk I/O statistics over time
# PREREQUISITE: sysstat package installed

# STEP 10: Identify inode usage by directory
find / -xdev -printf '%h\n' 2>/dev/null | sort | uniq -c | sort -rn | head -20
# Shows: Directories with most files
```

**Cleanup procedures** (use with caution):
```bash
# Clean old log files (keep recent only)
find /var/log -type f -name "*.log*" -mtime +30 -delete
# CAVEAT: Specify exact -mtime value; may delete important logs

# Compress old logs instead of deleting
find /var/log -type f -name "*.log" -mtime +7 -exec gzip {} \;

# Clean temporary files
rm -rf /tmp/* /var/tmp/*
# WARNING: Verify no running process depends on /tmp files

# Clean package manager cache
apt clean && apt autoclean  # Debian/Ubuntu
yum clean all  # CentOS/RHEL
# POST-REQ: Safe to run regularly

# Find and clear large core dumps
find / -name "core.*" -type f -delete
# CAVEAT: Delete core dumps only after debugging

# Clean orphaned docker images/volumes (if Docker installed)
docker system prune --volumes
```

**Commands to NEVER use in production**:
```bash
# ❌ NEVER: rm -rf /* or similar recursive deletion
#    System destruction; no recovery possible
# ❌ NEVER: echo 3 > /proc/sys/vm/drop_caches then delete files
#    File metadata corruption risk
# ❌ NEVER: Delete /var/log without rotating first
#    Active logs may be corrupted
```

---

## Scenario: Diagnosing High Load Average

**Prerequisites**: Load average > 2x CPU count, system appears sluggish, processes queued  
**Common Causes**: CPU contention, I/O wait, blocked processes, excessive context switching

```bash
# STEP 1: Get load average
uptime
# Shows: 1, 5, 15 minute load averages
# INTERPRETATION: Load = 1.0 per CPU = 100% CPU time available

# STEP 2: Get CPU count for reference
nproc
# Compare with load average; if load > nproc*2, significant contention

# STEP 3: Detailed load analysis
cat /proc/loadavg
# Also shows: Running/Total processes, last PID

# STEP 4: Check which processes are causing load
ps aux | awk '$8 ~ /R/'  # Running processes (R state)
ps aux | awk '$8 ~ /D/'  # Uninterruptible sleep (D state - I/O wait)
# CAVEAT: Processes in D state are harder to interrupt

# STEP 5: Monitor load in real-time
watch -n 1 'uptime; echo; ps aux | grep -E "PID|R|D"'

# STEP 6: Check runqueue depth
cat /proc/sched_debug | grep "runnable"
# Shows: Number of processes waiting to run
# PREREQUISITE: Must have sched_debug enabled

# STEP 7: Analyze I/O wait component
iostat -xm 1 5
# Look for: %iowait column; if > 50%, I/O is bottleneck not CPU
# PREREQUISITE: sysstat package installed

# STEP 8: Check process states distribution
ps aux | awk '{print $8}' | sort | uniq -c
# Shows: Count of each process state (R=running, S=sleeping, D=I/O, Z=zombie)

# STEP 9: Find process with longest run time (stuck process)
ps aux --sort=etime | tail -10
# Shows: Processes running longest; may indicate hung process

# STEP 10: Check blocked I/O operations
lsof | grep -E "REG|DIR" | wc -l
# Shows: Number of open files; high count may indicate I/O load
```

**Advanced load diagnosis**:
```bash
# Trace system calls of slow process
strace -c -p <PID> sleep 5
# Shows: Which syscalls consuming time

# Monitor context switches
vmstat 1 10 | awk '{print $11}' | tail -5
# Look for: cs column (context switches); > 100000 = high contention

# Check thread count on key process
ps -eLf | grep <process> | wc -l
```

**Load reduction commands**:
```bash
# Reduce process priority to lower load
nice -n 19 <command>  # Lowest priority
renice -n 19 -p <PID>

# Pause non-critical processes
kill -STOP <PID>
# Resume with: kill -CONT <PID>

# Limit CPU usage of process
cpulimit -l 25 -p <PID>  # Limit to 25% CPU
```

**Commands to NEVER use in production**:
```bash
# ❌ NEVER: kill -9 random processes to reduce load
#    May kill critical services
# ❌ NEVER: Disable swap to "fix" high load
#    Makes situation worse
# ❌ NEVER: Overcommit CPU by running unlimited threads
#    Increases load without improving throughput
```

---

## Scenario: Diagnosing Network Connectivity Issues

**Prerequisites**: Host cannot reach services, external connectivity failed, latency high  
**Common Causes**: Network interface down, routing issue, firewall blocking, DNS failure, network congestion

```bash
# STEP 1: Check network interface status
ip link show
# Shows: All interfaces and their status (UP/DOWN)
# Alternative: ifconfig -a

# STEP 2: Check IP addresses
ip addr show
# Shows: IP addresses assigned to interfaces
# CAVEAT: IPv4 and IPv6 may be configured separately

# STEP 3: Test interface connectivity
ping -c 4 <destination>
# PREREQUISITE: ICMP must be allowed
# CAVEAT: Some hosts block ping; ping failure doesn't mean no connectivity

# STEP 4: Check routing table
ip route show
# Shows: Routes and default gateway
# Look for: default route pointing to gateway

# STEP 5: Trace route to destination
traceroute <destination>
# Shows: Path packets take to destination
# PREREQUISITE: traceroute package installed
# CAVEAT: May be blocked by firewalls; hops without response show *

# STEP 6: Check DNS resolution
nslookup <hostname>
dig <hostname>
# Shows: DNS lookup results and query info
# CAVEAT: Different DNS servers may give different results

# STEP 7: Check DNS configuration
cat /etc/resolv.conf
# Shows: DNS servers used for resolution
# CAVEAT: May be overridden by DHCP or systemd-resolved

# STEP 8: Check network statistics
netstat -an | head -20
# Shows: Network connections, listening ports, established connections
# Alternative: ss -an (faster, more detailed)

# STEP 9: Monitor network traffic
tcpdump -i <interface> -n "tcp port <port>" -c 10
# Shows: Live packet capture for specific port
# PREREQUISITE: Root/sudo access required
# WARNING: High verbosity; use filters to limit output

# STEP 10: Check for network errors
ethtool -S <interface> | grep -i "error\|drop\|collision"
# Shows: Network driver statistics including errors
# PREREQUISITE: ethtool package installed

# STEP 11: Check firewall rules
iptables -L -n
# Shows: Current firewall rules
# CAVEAT: Complex rules may need grep to find specific port

# STEP 12: Check connection limits
netstat -an | wc -l
# Shows: Total number of connections
# Compare with: cat /proc/sys/net/ipv4/tcp_max_syn_backlog

# STEP 13: Monitor network bandwidth
iftop -i <interface>
# Shows: Real-time bandwidth usage by connection
# PREREQUISITE: iftop package installed
```

**TCP connection debugging**:
```bash
# Check for TIME_WAIT connections (may exhaust ports)
netstat -an | grep TIME_WAIT | wc -l

# Check for listening ports
netstat -tlnp | grep LISTEN

# Monitor connection state transitions
watch -n 1 'netstat -an | grep -c ESTABLISHED'

# Check TCP socket buffer tuning
cat /proc/sys/net/ipv4/tcp_rmem
cat /proc/sys/net/ipv4/tcp_wmem
```

**Network recovery commands**:
```bash
# Restart network interface
ip link set <interface> down
ip link set <interface> up

# Flush and rebuild routing table
ip route flush table main
# Then reconfigure routes or restart networking service

# Clear ARP cache (if needed)
arp -a  # View current ARP table
ip neigh flush all  # Clear all ARP entries

# Adjust TCP/IP tuning for performance
sysctl -w net.ipv4.tcp_tw_reuse=1  # Reuse TIME_WAIT connections
sysctl -w net.ipv4.tcp_max_syn_backlog=2048
```

**Commands to NEVER use in production**:
```bash
# ❌ NEVER: iptables -F without saving first
#    Clears all firewall rules; service becomes exposed
# ❌ NEVER: ip route del default
#    Destroys all external connectivity
# ❌ NEVER: systemctl restart networking while SSH'd
#    Disconnects session; may not be able to reconnect
# ❌ NEVER: tcpdump on high-traffic interface without filter
#    Causes significant performance impact
```

---

## Scenario: Diagnosing Process Hangs and Zombie Processes

**Prerequisites**: Process not responding, appears hung, command doesn't complete  
**Common Causes**: Deadlock, blocking system call, waiting for resource, parent process not reaped

```bash
# STEP 1: Identify zombie processes
ps aux | grep '<defunct>'
# Shows: Processes in zombie (Z) state

# STEP 2: Get more details on zombie
ps -o ppid= -p <zombie-pid>
# Shows: Parent process ID; parent should reap zombie

# STEP 3: Find all processes in specific state
ps aux | awk '$8 ~ /Z/'  # Zombies
ps aux | awk '$8 ~ /D/'  # Uninterruptible sleep (real issue)

# STEP 4: Get process state details
cat /proc/<PID>/status | grep State
# Shows: Current process state

# STEP 5: Check what process is waiting for
cat /proc/<PID>/wchan
# Shows: Which kernel function process is blocked in

# STEP 6: Check file descriptors
ls -la /proc/<PID>/fd
# Shows: Which files process has open; may reveal blocking resource

# STEP 7: Get full stack trace (requires gdb)
gdb -p <PID> -ex "bt" -ex quit
# Shows: Function call stack
# PREREQUISITE: gdb installed, debug symbols present

# STEP 8: Trace system calls with strace
strace -p <PID> 2>&1 | head -50
# Shows: Current system call and parameters
# WARNING: Attaching may hang if process is stuck

# STEP 9: Check if process is waiting for I/O
lsof -p <PID> | grep REG
# Shows: All files process has open

# STEP 10: Monitor process memory (may reveal hang reason)
cat /proc/<PID>/status | grep -E "VmRSS|VmSize|Threads"
# Rapidly growing memory may indicate infinite loop

# STEP 11: Check if parent still exists
ps -o ppid= -p <PID> | xargs ps -p
# Shows: Parent process; if ppid=1, parent died (zombie can't be reaped)

# STEP 12: Send signals to process
kill -0 <PID>  # Test if process exists (no signal sent)
kill -TERM <PID>  # Graceful termination request
# POST-REQ: Wait 10 seconds, then force kill if needed
```

**Zombie process cleanup**:
```bash
# Kill parent of zombie (will cause zombie to be reaped)
kill -9 <parent-pid>
# WARNING: This kills the parent; ensure it's not critical service

# Alternative: reparent zombie to init by killing parent
# The zombie will be reaped by init when parent dies

# Prevent new zombies by ensuring parent reaps children
# In code: use waitpid() or signal handlers properly
```

**Hung process recovery**:
```bash
# Try graceful termination first
kill -TERM <PID>
sleep 5

# Then force kill if needed
kill -9 <PID>

# Clean up process resources
rm -f /proc/<PID>/fd  # This won't work; resources auto-cleanup
# Instead: kernel cleans up when process terminates
```

**Commands to NEVER use in production**:
```bash
# ❌ NEVER: Kill random parent processes to cleanup zombies
#    Causes child process failures
# ❌ NEVER: Send SIGKILL (kill -9) before SIGTERM
#    Prevents graceful shutdown
# ❌ NEVER: Ignore growing zombie count
#    May indicate parent process leak; investigate root cause
```

---

## Scenario: Diagnosing Port Conflicts and Service Issues

**Prerequisites**: Port binding fails, service won't start, "Address already in use" error  
**Common Causes**: Port already in use, service didn't stop cleanly, privileged port access issue

```bash
# STEP 1: Check which process is using port
lsof -i :<port>
# Shows: Process using port, PID, user, connection state
# Alternative: netstat -tlnp | grep <port>

# STEP 2: Check all listening ports
ss -tlnp
# Shows: All TCP listening ports and associated processes
# CAVEAT: May require root to see all process names

# STEP 3: Check if port is in TIME_WAIT
netstat -an | grep TIME_WAIT | grep <port>
# Shows: Connections in TIME_WAIT state (port still reserved)
# Solution: Wait ~2 minutes or restart service with SO_REUSEADDR

# STEP 4: Check service status
systemctl status <service-name>
# Shows: Service state, PID if running, recent logs

# STEP 5: Check if port requires root
getent services <port>
# Shows: Port number and protocol name from /etc/services

# STEP 6: Verify service can bind to port
cat /proc/net/tcp | grep -i "<hex-port>"
# Shows: All TCP connections for that port

# STEP 7: Check firewall blocking port
iptables -L -n | grep <port>
firewall-cmd --list-all | grep <port>  # firewalld

# STEP 8: Check socket options
socket_dump <PID> <port>  # Custom tool or strace alternative

# STEP 9: Verify process can access port
su - <service-user> -c "netstat -tlnp" | grep <port>

# STEP 10: Check ulimit for file descriptors
ulimit -n
# May need to increase if hitting FD limit
```

**Port conflict resolution**:
```bash
# Kill process using port (if safe)
kill -9 $(lsof -t -i :<port>)
# WARNING: Verify process before killing

# Check if process respects SO_REUSEADDR
strace -e setsockopt <command> 2>&1 | grep -i reuse

# Force close socket by restarting service
systemctl restart <service-name>

# Wait for TIME_WAIT to clear
sleep 120  # Typical MSL * 2 is ~120 seconds

# Change port if conflict unavoidable
systemctl edit <service-name>
# Then: restart service
```

**Service startup debugging**:
```bash
# Run service in foreground with debug output
<service-command> --debug --foreground

# Check service logs
journalctl -u <service-name> -n 50

# Verify configuration syntax
<service-command> -t  # Test configuration (many services support this)

# Trace service startup
strace -e trace=network <service-command>
```

**Commands to NEVER use in production**:
```bash
# ❌ NEVER: Kill critical services to free port
#    Use alternative port or fix the real issue
# ❌ NEVER: Change port bindings without updating configs
#    Inconsistency causes failures
# ❌ NEVER: Disable firewall to fix port issues
#    Instead, update firewall rules properly
```

---

## Scenario: Diagnosing File Descriptor Exhaustion

**Prerequisites**: "Too many open files" error, application unable to open files  
**Common Causes**: Unclosed file handles, too many connections, ulimit too low, file descriptor leak

```bash
# STEP 1: Check system-wide file descriptor limit
cat /proc/sys/fs/file-max
# Shows: Maximum number of FDs system can handle

# STEP 2: Check current FD usage
cat /proc/sys/fs/file-nr
# Shows: allocated, unused, max (all FDs in system)

# STEP 3: Check per-process limit
ulimit -n
# Shows: Max FDs for current process

# STEP 4: Get process FD usage
ls -1 /proc/<PID>/fd | wc -l
# Shows: Number of open FDs for process
# Compare with: ulimit -n (process limit)

# STEP 5: Identify which process is leaking FDs
for pid in $(pgrep <process-name>); do 
  echo "$pid: $(ls -1 /proc/$pid/fd 2>/dev/null | wc -l)"
done

# STEP 6: See what files are open for process
lsof -p <PID> | head -30
# Shows: File type, descriptor number, file path

# STEP 7: Find unclosed pipes or sockets
lsof -p <PID> | grep -E "pipe|socket|REG"
# May reveal which FD types are accumulating

# STEP 8: Monitor FD growth over time
while true; do ls -1 /proc/<PID>/fd | wc -l; sleep 5; done

# STEP 9: Check for memory-mapped files
cat /proc/<PID>/maps | wc -l
# Shows: Number of mapped regions; may indicate FD issue

# STEP 10: Get strace of FD operations
strace -e trace=open,close,openat -p <PID> 2>&1 | head -50
# Shows: Which operations opening/closing FDs
```

**FD leak investigation**:
```bash
# Get FD details with descriptions
ls -la /proc/<PID>/fd/
# Shows: Type of each FD (REG=file, CHR=character, PIPE, SOCKET)

# Check for orphaned temporary files
find /tmp -type f -size 0 -mtime +1 -delete
# Removes empty files older than 1 day

# Monitor system-wide FD allocation
watch -n 1 'cat /proc/sys/fs/file-nr'

# Check FD usage by file type
lsof -p <PID> | awk '{print $5}' | sort | uniq -c | sort -rn
```

**FD limit adjustment**:
```bash
# Increase per-process limit
ulimit -n 65536
# Changes only for current shell session

# Permanent change (varies by system)
# Edit /etc/security/limits.conf:
# <domain> <type> <item> <value>
# Example: * soft nofile 65536

# Increase system-wide limit
sysctl -w fs.file-max=2097152

# Verify change
ulimit -n
```

**Commands to NEVER use in production**:
```bash
# ❌ NEVER: Set ulimit -n to unlimited
#    Can crash system if not enough memory for FD tables
# ❌ NEVER: Manually close FD while process is using it
#    Causes file corruption
# ❌ NEVER: Ignore FD exhaustion errors
#    Service will fail; fix root cause immediately
```

---

## Scenario: Diagnosing System Hang and Frozen State

**Prerequisites**: System unresponsive, keyboard/mouse frozen, no SSH access  
**Common Causes**: Out of memory, extreme I/O load, kernel panic, livelock, CPU stuck

```bash
# PREVENTION: Enable magic SysRq key (if possible to set before hang)
echo 1 > /proc/sys/kernel/sysrq

# STEP 1: Send magic SysRq commands (requires kernel support)
# On keyboard: Alt+SysRq+<key>
# Common keys:
#   r - Switch keyboard from raw mode to XLATE mode
#   e - Send SIGTERM to all processes except init
#   i - Send SIGKILL to all processes except init
#   u - Remount all mounted filesystems in read-only mode
#   s - Sync all mounted filesystems
#   b - Reboot immediately (unsafe, data loss)

# STEP 2: If SSH still works, diagnose remotely
top
# Shows: Load, CPU usage, memory if system responsive

# STEP 3: Check for OOM killer
dmesg | tail -20 | grep -i "oom\|killed process"

# STEP 4: Check kernel messages
dmesg | tail -50
# Look for: panic, kernel errors, driver crashes

# STEP 5: Check if system is in I/O wait
iostat -x 1 3
# Look for: %iowait near 100%

# STEP 6: Monitor system load before hang repeats
watch -n 1 'uptime; ps aux | awk "$8 ~ /D/"; free -h'

# STEP 7: Check for kernel panic in logs
journalctl -p err -n 50

# STEP 8: Check for hung tasks
cat /proc/sched_debug | grep -A 5 "hung_task"

# STEP 9: Enable kernel debugging if not already
echo 1 > /proc/sys/kernel/panic_on_oops
# Causes kernel to panic on oops (easier to recover from)

# STEP 10: Check for kthreads (kernel threads) consuming CPU
ps aux | grep kthread | head -10
```

**System recovery from hang**:
```bash
# If only SSH frozen but system alive, restart SSH
systemctl restart sshd

# If shell hung, send SIGTERM to processes (remote SSH)
killall -TERM <hung-process>

# Force sync to prevent data loss (magic SysRq)
# Alt+SysRq+s (if keyboard responsive)

# If nothing responds, graceful reboot (magic SysRq)
# Alt+SysRq+u (remount read-only)
# Wait 5 seconds
# Alt+SysRq+b (reboot)

# Last resort: hard reboot (power button 10+ seconds)
# Data loss likely; run fsck on reboot
```

**Hang prevention**:
```bash
# Monitor memory pressure
watch -n 1 'cat /proc/pressure/memory'

# Set panic timeout so system reboots on hang
sysctl -w kernel.panic=10  # Reboot after 10s panic

# Enable hang detection
sysctl -w kernel.hung_task_timeout_secs=120

# Configure swappiness to prevent thrashing
sysctl -w vm.swappiness=10
```

**Commands to NEVER use in production**:
```bash
# ❌ NEVER: Force hard reset without graceful shutdown
#    Filesystem corruption, data loss
# ❌ NEVER: Alt+SysRq+b (immediate reboot)
#    No graceful shutdown, no fsync
# ❌ NEVER: echo b > /proc/sysrq-trigger without backup
#    Immediate unclean reboot
```

---

## Scenario: Diagnosing Permission and Access Issues

**Prerequisites**: "Permission denied", cannot read file, cannot execute command  
**Common Causes**: Wrong file ownership, incorrect permissions bits, SELinux/AppArmor blocking, wrong user

```bash
# STEP 1: Check file permissions
ls -la <file>
# Shows: rwxrwxrwx (owner, group, other), owner, group

# STEP 2: Check current user
whoami
id
# Shows: UID, GID, group membership

# STEP 3: Check file ownership
stat <file> | grep -E "Access|Uid|Gid"

# STEP 4: Check group membership
groups
# Shows: All groups current user belongs to

# STEP 5: Check if file is executable
file <file>
# May reveal if binary permissions are wrong

# STEP 6: Check effective permissions (considering ACLs)
getfacl <file>
# Shows: Extended ACLs if present

# STEP 7: Check sudo permissions
sudo -l
# Shows: What commands you can run with sudo

# STEP 8: Check SELinux context (if enabled)
ls -Z <file>
# Shows: SELinux security context

# STEP 9: Get SELinux error details
getenforce  # Shows: enforcing/permissive/disabled
# If enforcing, check: audit log for denials

# STEP 10: Check AppArmor profile (if enabled)
cat /proc/self/attr/current
# Shows: AppArmor profile for current process
```

**Permission diagnosis**:
```bash
# Understand permission bits
stat <file> | grep Access
# Format: (0755/-rwxr-xr-x)
# First char: file type (- = regular, d = directory, l = link)
# Next 9: rwx for owner/group/other

# Check umask
umask
# Shows: Default permissions mask for new files

# Calculate actual permissions
# Bit: 4=r, 2=w, 1=x
# Owner bits: 4+2+1=7 (rwx)
# Group bits: 4+0+1=5 (r-x)  
# Other bits: 4+0+1=5 (r-x)
# Result: 755
```

**Permission fixes**:
```bash
# Change file ownership
chown <user>:<group> <file>
chown -R <user>:<group> <directory>  # Recursive

# Change permissions
chmod 755 <file>  # rwxr-xr-x
chmod 644 <file>  # rw-r--r--
chmod -R 755 <directory>  # Recursive

# Add execute permission
chmod +x <file>

# Remove write permission
chmod -w <file>

# Set default permissions for new files
umask 0022  # Results in 755 for dirs, 644 for files
```

**SELinux/AppArmor fixes**:
```bash
# Check SELinux denial log
grep denied /var/log/audit/audit.log | tail -10

# Generate SELinux policy from denials
audit2allow -a -M <policy-name>
semodule -i <policy-name>.pp

# Check AppArmor denials
grep DENIED /var/log/kern.log

# Reload AppArmor profiles
systemctl reload apparmor
```

**Commands to NEVER use in production**:
```bash
# ❌ NEVER: chmod 777 to "fix" permission issues
#    Creates huge security hole
# ❌ NEVER: chown root:root and chmod 700 on shared resources
#    Other users/services can't access
# ❌ NEVER: Disable SELinux/AppArmor to fix access denied
#    Reduces security; fix policy instead
# ❌ NEVER: sudo without understanding what command does
#    May create security vulnerabilities
```

---

## Scenario: Diagnosing Disk I/O Performance Issues

**Prerequisites**: High read/write latency, slow file operations, disk utilization high  
**Common Causes**: I/O contention, slow disk hardware, excessive page cache activity, bad sectors

```bash
# STEP 1: Check disk utilization
iostat -dx 1 5
# Shows: Disk read/write rates, utilization % per device
# PREREQUISITE: sysstat package installed

# STEP 2: Check I/O operations per second
iostat -x 1 5 | grep -E "rrqm/s|wrqm/s|r/s|w/s"
# Shows: Read/write requests, merges (higher merge = better)

# STEP 3: Check read/write latency
iostat -x 1 5 | grep -E "r_await|w_await"
# Shows: Average time for read/write in milliseconds
# Good < 5ms, degraded 5-20ms, poor > 20ms

# STEP 4: Identify processes doing I/O
iotop -o
# Shows: Real-time I/O usage by process
# PREREQUISITE: iotop package installed

# STEP 5: Monitor disk queue depth
iostat -x 1 5 | grep -E "aqu-sz"
# Shows: Average queue size; if > number of processes doing I/O, congestion

# STEP 6: Check filesystem type and options
mount | grep <filesystem>
# Shows: Filesystem type and mount options

# STEP 7: Check for bad sectors
smartctl -a /dev/<device>
# Shows: SMART status, reallocated sectors, pending sectors
# PREREQUISITE: smartmontools installed
# WARNING: Indicates imminent disk failure if non-zero

# STEP 8: Monitor sequential vs random I/O
iotop -o -b -d 1 | awk '{print $5}' | sort | uniq -c
# Reveals: Access pattern (sequential = better performance)

# STEP 9: Check for excessive context switching during I/O
vmstat 1 5 | awk '{print $11}'  # cs (context switches)

# STEP 10: Check page cache activity
vmstat 1 5 | awk '{print $7, $8}'  # in (interrupts), sy (system time)
```

**I/O profiling commands**:
```bash
# Trace I/O syscalls
strace -e trace=read,write,open,close -c <command>
# Shows: Time spent in I/O operations

# Detailed I/O trace
blktrace -d /dev/<device> -o - | blkparse -i -
# Captures kernel I/O operations
# PREREQUISITE: blktrace package, requires root

# Monitor filesystem cache
cat /proc/meminfo | grep -E "Buffers|Cached"
# Shows: Kernel page cache size
```

**I/O optimization commands**:
```bash
# Increase I/O scheduler buffer
sysctl -w vm.dirty_ratio=15  # Max % memory for dirty pages
sysctl -w vm.dirty_background_ratio=5

# Check current I/O scheduler
cat /sys/block/sda/queue/scheduler
# Shows: Available schedulers; noop, deadline, cfq, etc.

# Change to deadline scheduler (better for some workloads)
echo deadline > /sys/block/sda/queue/scheduler

# Increase read-ahead
blockdev --getra /dev/sda  # Get current value
blockdev --setra 8192 /dev/sda  # Set to 8192 sectors

# Optimize for SSD (disable atime)
mount -o remount,noatime <filesystem>
```

**Commands to NEVER use in production**:
```bash
# ❌ NEVER: Run fstrim on production SSDs without monitoring
#    Can cause performance dip if FTL busy
# ❌ NEVER: Change I/O scheduler during heavy I/O
#    May cause stalls or data corruption
# ❌ NEVER: Ignore SMART warnings about bad sectors
#    Disk failure imminent; prepare for replacement
```

---

## Scenario: Diagnosing Log File Issues

**Prerequisites**: Logs not being written, log rotation failing, disk full from logs  
**Common Causes**: Permission denied, inode exhaustion, log rotation misconfigured, pipe broken

```bash
# STEP 1: Check if log file exists and has space
ls -lh /var/log/<app>.log
# Shows: File size, timestamp, permissions

# STEP 2: Check if process can write to log directory
ls -ld /var/log/<app-dir>
# Look for: correct owner, group, write permission

# STEP 3: Verify process can access log file
ls -l /var/log/<app>.log | awk '{print $3, $4}'
# Compare with: user running application

# STEP 4: Check for log rotation configuration
cat /etc/logrotate.d/<app>
# Shows: Rotation rules, compression, retention

# STEP 5: Test log rotation manually
logrotate -d /etc/logrotate.d/<app>
# Shows: What would happen (dry-run)

# STEP 6: Check if log rotation is stuck
ps aux | grep logrotate
# If running > 5 minutes, likely hung

# STEP 7: Monitor log file being written
tail -f /var/log/<app>.log
# Should show new lines appearing

# STEP 8: Check if application is logging
grep -c "ERROR\|WARNING\|INFO" /var/log/<app>.log
# Reveals: Volume of log messages

# STEP 9: Check for permission issues
strace -e open,openat <app-command> 2>&1 | grep "/var/log"
# Shows: Log file access attempts

# STEP 10: Check file descriptor limit
lsof -p <PID> | grep log | wc -l
# Shows: Number of log files open by process
```

**Log issues diagnosis**:
```bash
# Check if log file has correct permissions
sudo -u <app-user> touch /var/log/<app>.log
# Should succeed if permissions correct

# Check if log directory is full
du -sh /var/log/<app-dir>

# Find large log files
find /var/log -type f -size +100M

# Check disk space
df -h /var/log

# Monitor log growth rate
watch -n 5 'wc -l /var/log/<app>.log'
```

**Log rotation fixes**:
```bash
# Manually rotate log file
mv /var/log/<app>.log /var/log/<app>.log.1
# Then restart application to create new log file

# Force log rotation
logrotate -f /etc/logrotate.d/<app>

# Compress old logs manually
gzip /var/log/<app>.log.*[0-9]

# Clear old logs while preserving current
find /var/log -name "<app>.log.*" -mtime +30 -delete
```

**Log configuration improvements**:
```bash
# Reduce log verbosity to prevent bloat
# Edit application config: log.level = WARN

# Enable log rotation in application if available
# Reduce max log file size

# Use syslog instead of file logging
# Easier to manage, rotate automatically
```

**Commands to NEVER use in production**:
```bash
# ❌ NEVER: rm -f /var/log/* to free space
#    Deletes important system logs; find specific files instead
# ❌ NEVER: chmod 777 /var/log/<app>.log
#    Creates security hole; use proper ownership instead
# ❌ NEVER: logrotate -f without testing first
#    May break logging immediately
```

---

## Scenario: Diagnosing Socket/Connection Exhaustion

**Prerequisites**: "Connection refused", "Too many open files", socket descriptor limit hit  
**Common Causes**: Too many connections, TIME_WAIT exhaustion, connection leak, socket options misconfigured

```bash
# STEP 1: Check socket statistics
netstat -s | head -30
# Shows: TCP/UDP statistics, retransmits, drops

# STEP 2: Count connections by state
netstat -an | awk '{print $6}' | sort | uniq -c | sort -rn
# Shows: Distribution of connection states

# STEP 3: Count TIME_WAIT connections
netstat -an | grep TIME_WAIT | wc -l
# High count (> 10000) indicates exhaustion risk

# STEP 4: Check TCP backlog queue
cat /proc/sys/net/ipv4/tcp_max_syn_backlog
# Shows: Maximum SYN backlog for new connections

# STEP 5: Get detailed socket information
ss -an | head -20
# More detailed than netstat; faster

# STEP 6: Monitor connections in real-time
watch -n 1 'netstat -an | grep ESTABLISHED | wc -l'

# STEP 7: Check for connection resets
netstat -s | grep -i reset

# STEP 8: Identify which process has most connections
for pid in $(pgrep <process>); do
  echo "$pid: $(netstat -an | grep ESTABLISHED | wc -l)"
done

# STEP 9: Check socket descriptor limit
cat /proc/sys/net/ipv4/tcp_max_tw_buckets

# STEP 10: Monitor socket syscalls
strace -e trace=socket,bind,listen,accept <command> 2>&1 | head -50
```

**Connection issues diagnosis**:
```bash
# Check if service is listening
netstat -tlnp | grep <port>

# Test connection directly
nc -zv <host> <port>
# Should connect quickly

# Check for FIN_WAIT states (incomplete closes)
netstat -an | grep FIN_WAIT | wc -l

# Monitor connection state transitions
watch -n 1 'netstat -an | awk "{print \$6}" | sort | uniq -c'
```

**Socket optimization**:
```bash
# Enable SO_REUSEADDR for faster port reuse
# In application code or sysctl:
sysctl -w net.ipv4.tcp_tw_reuse=1

# Reduce TIME_WAIT duration
sysctl -w net.ipv4.tcp_fin_timeout=30

# Increase connection backlog
sysctl -w net.ipv4.listen.backlog=4096

# Increase ephemeral port range
sysctl -w net.ipv4.ip_local_port_range="1024 65535"

# Monitor after changes
netstat -an | grep TIME_WAIT | wc -l
```

**Commands to NEVER use in production**:
```bash
# ❌ NEVER: Kill all connections with netstat | awk ...
#    May disconnect critical services
# ❌ NEVER: Set tcp_max_syn_backlog to 1
#    Breaks service connectivity
# ❌ NEVER: Disable tcp_tw_reuse permanently
#    Exhausts ephemeral ports faster
```

---

## Scenario: Diagnosing Systemd and Container Runtime Issues

**Prerequisites**: Containers not starting, services failing, kubelet stuck  
**Common Causes**: systemd service limits, cgroup creation failure, container runtime hung, resource limits

```bash
# STEP 1: Check systemd service status (kubelet, docker, containerd)
systemctl status kubelet
systemctl status docker  # or: containerd
# Shows: Active status, PID, recent logs

# STEP 2: Check systemd service limits
systemctl show kubelet | grep -i "limit"
# Shows: TasksMax, MemoryMax, CPUQuota limits

# STEP 3: Check if service failed recently
journalctl -u kubelet -n 50 --no-pager
# Shows: Last 50 lines of service logs

# STEP 4: Check systemd resource constraints
cat /proc/sys/fs/inotify/max_user_watches
# Important for kubelet file watching; if too low, watch failures

# STEP 5: Verify container runtime is running
ps aux | grep -E "docker|containerd|cri-o"
# Should show running processes

# STEP 6: Check container runtime socket
ls -la /var/run/docker.sock  # Docker
ls -la /run/containerd/containerd.sock  # containerd
ls -la /var/run/crio/crio.sock  # CRI-O

# STEP 7: Test container runtime connectivity
docker version  # Docker
ctr version  # containerd
# Should return version info without errors

# STEP 8: Check for hung container runtime
timeout 5 docker ps > /dev/null 2>&1
# If timeout, container runtime is hung

# STEP 9: Monitor systemd service restart count
systemctl show kubelet | grep NRestarts
# High count (> 10 in 1 hour) indicates recurring failures

# STEP 10: Check systemd cgroup configuration
cat /proc/<kubelet-pid>/cgroup
# Shows: Cgroup assignments for kubelet process

# STEP 11: Check container runtime cgroup limits
cat /sys/fs/cgroup/memory/docker/memory.limit_in_bytes  # Docker
cat /sys/fs/cgroup/memory/containerd/memory.limit_in_bytes  # containerd

# STEP 12: Verify systemd unit file syntax
systemd-analyze verify /etc/systemd/system/kubelet.service
# Catches configuration errors before loading
```

**Service recovery procedures**:
```bash
# Reload systemd after config changes
systemctl daemon-reload

# Restart service with debugging
systemctl restart kubelet --no-block
journalctl -u kubelet -f  # Follow logs

# Increase inotify watches for kubelet file watching
sysctl -w fs.inotify.max_user_watches=524288

# Check service dependencies
systemctl list-dependencies kubelet

# Mask service temporarily to prevent restart
systemctl mask kubelet
# Then: systemctl unmask kubelet (re-enable)

# Check memory/CPU limits on service
systemctl set-property kubelet MemoryMax=2G
systemctl set-property kubelet CPUQuota=200%
```

**Commands to NEVER use in production**:
```bash
# ❌ NEVER: systemctl daemon-reload during pod scheduling
#    Can cause temporary service unavailability
# ❌ NEVER: Kill container runtime processes (-9)
#    Use systemctl stop instead
# ❌ NEVER: Edit /etc/systemd/system/* without testing
#    Syntax errors can prevent service startup
```

---

## Scenario: Diagnosing Cgroup and Resource Limit Issues

**Prerequisites**: Pod evictions, containers killed unexpectedly, memory/CPU throttling  
**Common Causes**: Cgroup limits too low, memory pressure, swap disabled, CPU CFS quota exceeded

```bash
# STEP 1: Check if cgroups v1 or v2 is in use
cat /proc/mounts | grep cgroup
# Shows: cgroup mount points (v1 has multiple, v2 has single)

# STEP 2: Monitor cgroup memory pressure
cat /proc/pressure/memory
# Shows: some.avg10, some.avg60, some.avg300 (memory stall %)
# PREREQUISITE: cgroups v2 with PSI enabled

# STEP 3: Check container memory limits
cat /sys/fs/cgroup/memory/docker/<container-id>/memory.limit_in_bytes
# Convert bytes to human-readable: /1024/1024/1024

# STEP 4: Check container actual memory usage
cat /sys/fs/cgroup/memory/docker/<container-id>/memory.usage_in_bytes
# Compare with limit from STEP 3

# STEP 5: Get memory breakdown
cat /sys/fs/cgroup/memory/docker/<container-id>/memory.stat
# Shows: cache, rss, swap, mapped_file, etc.

# STEP 6: Check if container hit OOM
cat /sys/fs/cgroup/memory/docker/<container-id>/memory.oom_control
# oom_kill_disable: 0 = can be OOMKilled, 1 = protected

# STEP 7: Monitor CPU throttling
cat /sys/fs/cgroup/cpu/docker/<container-id>/cpu.stat
# Look for: nr_throttled (if > 0, CPU being throttled)
# Also check: throttled_time (total time throttled in microseconds)

# STEP 8: Check CPU CFS quota and period
cat /sys/fs/cgroup/cpu/docker/<container-id>/cpu.cfs_quota_us
cat /sys/fs/cgroup/cpu/docker/<container-id>/cpu.cfs_period_us
# Quota/Period = available CPU (e.g., 100000/100000 = 1 CPU)

# STEP 9: Monitor all container memory limits
for dir in /sys/fs/cgroup/memory/docker/*/; do
  container=$(basename $dir)
  limit=$(cat $dir/memory.limit_in_bytes)
  usage=$(cat $dir/memory.usage_in_bytes)
  echo "$container: $((usage/1024/1024))MB / $((limit/1024/1024))MB"
done

# STEP 10: Check for memory reclaim pressure
cat /proc/vmstat | grep -E "pgscan|pgsteal"
# If > 0, kernel is reclaiming memory
```

**Cgroup v2 specific checks**:
```bash
# Check memory.high limit (soft limit)
cat /sys/fs/cgroup/memory.high
# Shows: Soft memory limit; triggers reclaim when exceeded

# Check memory pressure stall information
cat /proc/pressure/memory
cat /proc/pressure/cpu
cat /proc/pressure/io

# Monitor across all containers
cat /sys/fs/cgroup/memory/memory.events
# Shows: OOM events, memory.max limit hits
```

**Resource limit optimization**:
```bash
# Increase cgroup memory limit for container
echo 2147483648 > /sys/fs/cgroup/memory/docker/<container-id>/memory.limit_in_bytes
# WARNING: Verify sufficient node memory first

# Adjust CPU quota
echo 200000 > /sys/fs/cgroup/cpu/docker/<container-id>/cpu.cfs_quota_us  # 2 CPUs
echo 100000 > /sys/fs/cgroup/cpu/docker/<container-id>/cpu.cfs_period_us  # 100ms period

# Disable OOM killer for critical container (dangerous!)
echo 1 > /sys/fs/cgroup/memory/docker/<container-id>/memory.oom_control

# Set memory.low (memory guarantee)
echo 536870912 > /sys/fs/cgroup/memory/docker/<container-id>/memory.low  # 512MB reserved
```

**Commands to NEVER use in production**:
```bash
# ❌ NEVER: Delete cgroup while container still running
#    Kernel may kill container abruptly
# ❌ NEVER: Disable OOM killer for multiple containers
#    System may become unresponsive due to OOM
# ❌ NEVER: Set memory.limit_in_bytes while container has dirty pages
#    Memory.max_usage_in_bytes may spike
```

---

## Scenario: Diagnosing Kubernetes Node Kubelet Issues

**Prerequisites**: Node showing NotReady status, kubelet logs show errors, pods not starting  
**Common Causes**: Kubelet crash loop, container runtime disconnected, API server unreachable, node registration failure

```bash
# STEP 1: Check kubelet service status
systemctl status kubelet
# Shows: Running/failed, recent status, active restart count

# STEP 2: Get kubelet logs from systemd
journalctl -u kubelet -n 100 --no-pager | tail -50
# Shows: Most recent kubelet activities and errors

# STEP 3: Check kubelet configuration
cat /etc/kubernetes/kubelet/kubelet-config.yaml
# Look for: imageRepository, podCIDR, maxPods, etc.

# STEP 4: Verify kubeconfig credentials
cat /etc/kubernetes/kubelet/kubeconfig
# Should contain: server URL, certificate paths, tokens

# STEP 5: Test kubelet connectivity to API server
timeout 5 curl -k --cert /var/lib/kubelet/pki/kubelet-client-current.pem \
  --key /var/lib/kubelet/pki/kubelet-client-current-key.pem \
  https://<api-server>:6443/api/v1/nodes/$(hostname)
# PREREQUISITE: Correct cert paths for your cluster

# STEP 6: Check node registration
cat /var/lib/kubelet/kubeadm-flags.env
# Shows: Kubelet startup flags

# STEP 7: Monitor kubelet memory usage
ps aux | grep kubelet | grep -v grep
# Check RSS column for memory usage

# STEP 8: Check kubelet process CPU
top -p $(pgrep kubelet) -n 1 | tail -2

# STEP 9: Verify kubelet can talk to container runtime
timeout 5 docker ps > /dev/null 2>&1 && echo "OK" || echo "FAILED"
# OR: timeout 5 ctr version > /dev/null 2>&1 && echo "OK" || echo "FAILED"

# STEP 10: Check pod log directory permissions
ls -ld /var/log/pods
# Should be owned by root, readable by kubelet

# STEP 11: Check kubelet certificate expiration
openssl x509 -in /var/lib/kubelet/pki/kubelet-client-current.pem \
  -text -noout | grep -A 2 "Validity"

# STEP 12: Monitor kubelet metrics
curl -s http://localhost:10255/metrics | head -20
# PREREQUISITE: kubelet read-only port enabled (localhost:10255)
# WARNING: Read-only port is deprecated; use metrics-server instead
```

**Kubelet recovery procedures**:
```bash
# Restart kubelet with debug logging
systemctl stop kubelet
kubelet --kubeconfig=/etc/kubernetes/kubelet/kubeconfig \
  --v=2 &  # Run in foreground with debug logs
# Press Ctrl+C, then: systemctl start kubelet

# Reset kubelet state
systemctl stop kubelet
rm -rf /var/lib/kubelet/cpu_manager_state  # CPU manager state
rm -rf /var/lib/kubelet/memory_manager_state  # Memory manager state
systemctl start kubelet

# Force node re-registration
kubectl delete node $(hostname) --ignore-not-found=true
# Then kubelet will re-register automatically

# Verify node is ready
kubectl get nodes
watch 'kubectl get node $(hostname) -o wide'
```

**Commands to NEVER use in production**:
```bash
# ❌ NEVER: rm -rf /var/lib/kubelet/pods
#    Destroys all container data on node
# ❌ NEVER: Kill kubelet process without stopping service
#    Service will auto-restart; use systemctl instead
# ❌ NEVER: Modify /var/lib/kubelet files while service running
#    Can corrupt container state
```

---

## Scenario: Diagnosing Network Namespace and Container Networking Issues

**Prerequisites**: Container cannot access network, DNS fails in pod, inter-pod communication broken  
**Common Causes**: Veth interface misconfigured, network policy issue, CNI plugin failure, IP address conflict

```bash
# STEP 1: List network namespaces
ip netns list
# Shows: All network namespaces on node

# STEP 2: Get container network namespace
ps aux | grep <container-id> | grep -v grep
# Shows: Container PID

# STEP 3: Access container network namespace
ip netns identify <container-pid>
# Maps PID to namespace

# STEP 4: View container's network interfaces from host
ip netns exec <namespace> ip addr show
# Shows: IP addresses inside container

# STEP 5: Check container veth interface on host
ip link show | grep veth
# Shows: Virtual ethernet interfaces

# STEP 6: View container's routing table
ip netns exec <namespace> ip route show
# Should show: default route to container gateway

# STEP 7: Test container connectivity from host
ip netns exec <namespace> ping -c 1 8.8.8.8
# Tests external connectivity from container

# STEP 8: Check iptables rules (if using kube-proxy)
iptables -L -n | grep <service-ip>
# Shows: NAT rules for services

# STEP 9: Monitor conntrack table (connection tracking)
cat /proc/sys/net/netfilter/nf_conntrack_count
cat /proc/sys/net/netfilter/nf_conntrack_max
# If count near max, connection table exhausted

# STEP 10: Check CNI plugin status
ls -la /etc/cni/net.d/
# Shows: CNI config files (Weave, Flannel, Calico, etc.)

# STEP 11: View CNI plugin logs
journalctl -u kubelet | grep -i cni
# May show CNI setup failures

# STEP 12: Check cluster node IP pools
# For Flannel: cat /run/flannel/subnet.env
# For Weave: weave status
# For Calico: calicoctl get ippool
```

**Network troubleshooting**:
```bash
# Trace network packets inside container
ip netns exec <namespace> tcpdump -i eth0 -n tcp
# Shows: Real-time packet capture

# Check DNS resolution inside container
ip netns exec <namespace> nslookup kubernetes.default
ip netns exec <namespace> cat /etc/resolv.conf

# Test service endpoint
ip netns exec <namespace> curl http://<service-ip>:<port>

# View DNS cache (if using systemd-resolved)
ip netns exec <namespace> systemd-resolve --statistics
```

**Network recovery commands**:
```bash
# Restart CNI plugin (if managed by systemd)
systemctl restart weave  # Weave example

# Force CNI reconfiguration
rm -rf /var/lib/cni/networks/*
# Then restart kubelet: systemctl restart kubelet

# Flush container network namespace
ip netns delete <namespace>
# WARNING: Only if container is stopped

# Reset iptables rules
iptables-restore < /etc/iptables/rules.v4  # If backup exists
# Or: systemctl restart ufw/firewalld
```

**Commands to NEVER use in production**:
```bash
# ❌ NEVER: ip netns delete while container running
#    Container loses network connectivity
# ❌ NEVER: iptables -F to "fix" networking
#    Destroys all networking rules; use flush with backup
# ❌ NEVER: Modify veth interface properties
#    Can cause permanent connectivity loss
```

---

## Scenario: Diagnosing Kernel Parameters and Performance Tuning Issues

**Prerequisites**: Pods/services not performing expected, network latency high, stability issues  
**Common Causes**: Suboptimal kernel parameters, TCP tuning needed, file descriptors too low, swappiness high

```bash
# STEP 1: Get all current kernel parameters
sysctl -a | head -50
# Shows: All kernel configuration parameters

# STEP 2: Check specific tuning for Kubernetes
sysctl net.ipv4.ip_forward  # Should be 1
sysctl net.ipv4.tcp_tw_reuse  # Should be 1 for high connection counts
sysctl net.ipv4.tcp_max_syn_backlog  # Check value
sysctl net.core.somaxconn  # Socket listen backlog

# STEP 3: Check memory-related parameters
sysctl vm.swappiness  # Should be low (5-10) for K8s
sysctl vm.overcommit_memory  # Should be 1 for container environments
sysctl vm.max_map_count  # May need increase for Java apps

# STEP 4: Check file descriptor limits
sysctl fs.file-max
sysctl fs.nr_open  # Max per-process FDs

# STEP 5: Monitor parameter changes during issue
grep -r "kernel" /etc/sysctl.d/
# Shows: All permanent sysctl configurations

# STEP 6: Check transparent huge pages (THP)
cat /sys/kernel/mm/transparent_hugepage/enabled
# Should be: madvise (not always on)

# STEP 7: Check CPU frequency scaling
cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
# Should be: performance (not powersave for Kubernetes)

# STEP 8: Verify cgroup memory reclaim parameters
sysctl vm.memory_pressure_level
sysctl vm.watermark_scale_factor

# STEP 9: Check network namespace isolation
sysctl net.ipv4.conf.all.rp_filter  # Reverse path filtering

# STEP 10: Monitor buffer cache
sysctl vm.dirty_ratio
sysctl vm.dirty_background_ratio
# Controls when kernel flushes dirty pages to disk
```

**Kubernetes-optimized kernel parameters**:
```bash
# Essential for Kubernetes nodes:

# Network optimization
sysctl -w net.ipv4.ip_forward=1
sysctl -w net.ipv4.tcp_tw_reuse=1
sysctl -w net.ipv4.tcp_max_syn_backlog=8096
sysctl -w net.core.somaxconn=32768
sysctl -w net.ipv4.ip_local_port_range=1024 65535

# Memory optimization
sysctl -w vm.swappiness=5
sysctl -w vm.overcommit_memory=1
sysctl -w vm.max_map_count=262144

# File descriptors
sysctl -w fs.file-max=2097152
sysctl -w fs.inotify.max_user_watches=524288

# CPU scheduling
sysctl -w kernel.sched_migration_cost_ns=5000000

# Connection tracking (for iptables/netfilter)
sysctl -w net.netfilter.nf_conntrack_max=1048576
sysctl -w net.netfilter.nf_conntrack_tcp_timeout_established=300

# Save permanently
cat >> /etc/sysctl.d/99-kubernetes.conf << EOF
net.ipv4.ip_forward = 1
net.ipv4.tcp_tw_reuse = 1
vm.swappiness = 5
vm.overcommit_memory = 1
fs.file-max = 2097152
fs.inotify.max_user_watches = 524288
EOF
sysctl -p /etc/sysctl.d/99-kubernetes.conf
```

**Performance monitoring**:
```bash
# Check buffer I/O performance
vmstat 1 5 | awk '{print "bi:", $9, "bo:", $10}'
# bi/bo = blocks in/out per second

# Monitor TCP retransmissions
netstat -s | grep -i retrans

# Check system call overhead
sysctl kernel.perf_event_paranoid
# Lower values = more perf data available
```

**Commands to NEVER use in production**:
```bash
# ❌ NEVER: sysctl -w vm.swappiness=0
#    Can cause OOM killer to trigger
# ❌ NEVER: sysctl -w net.ipv4.ip_forward=0 on K8s node
#    Breaks all pod-to-pod communication
# ❌ NEVER: Change kernel.sched_* parameters without testing
#    Can cause performance regression or hangs
```

---

## Scenario: Diagnosing Container Image Registry and Storage Issues

**Prerequisites**: Image pulls failing, disk full on /var/lib/docker, registry authentication issues  
**Common Causes**: Registry unreachable, credentials misconfigured, overlay storage fragmented, too many images

```bash
# STEP 1: Check container storage location
docker info | grep -E "Docker Root Dir|Storage Driver"
# For containerd: ctr info | grep snapshotter

# STEP 2: Check storage space usage
du -sh /var/lib/docker/
du -sh /var/lib/containerd/
# Shows: Total storage used

# STEP 3: List stored images
docker images | wc -l
ctr image list | wc -l  # containerd

# STEP 4: Check storage breakdown
docker system df
# Shows: Images, containers, volumes usage and waste

# STEP 5: Get registry credentials status
cat ~/.docker/config.json | jq '.auths'
# Shows: Configured registries

# STEP 6: Test registry connectivity
curl -I https://<registry>/v2/
# Should return 200 or 401 (not 503 or connection refused)

# STEP 7: Check image pull logs
docker pull <image> 2>&1 | tail -20
# Shows: Pull process and any errors

# STEP 8: Verify image layers are stored
docker inspect <image-id> | jq '.RootFS.Layers'
# Shows: SHA256 hashes of image layers

# STEP 9: Check storage driver details
docker info | grep -A 5 "Storage Driver"
# For overlay2: may show backing filesystem info

# STEP 10: Monitor image pull rate
watch -n 1 'du -sh /var/lib/docker/ && docker images | wc -l'

# STEP 11: Check for orphaned blobs
docker system prune --dry-run
# Shows: What would be cleaned

# STEP 12: Verify image pull secrets for private registries
kubectl get secret <image-pull-secret> -n <namespace> -o yaml | jq '.data[".dockerconfigjson"]' | base64 -d | jq .
```

**Storage diagnostics**:
```bash
# Check overlay filesystem details
df -i /var/lib/docker/overlay2
# Monitor inode usage; if near limit, too many layers

# Find large images
for image in $(docker images -q); do
  docker history $image --no-trunc --quiet | while read layer; do
    docker inspect $layer | jq '.Size'
  done | awk '{sum+=$1} END {print $image, sum/1024/1024 " MB"}'
done

# Check registry response time
time curl -I https://<registry>/v2/

# Monitor container storage growth
while true; do du -sh /var/lib/docker/; sleep 5; done
```

**Storage cleanup**:
```bash
# Remove unused images
docker image prune -a -f

# Remove unused containers
docker container prune -f

# Remove unused volumes
docker volume prune -f

# Full system cleanup (careful!)
docker system prune -a --volumes

# For containerd
ctr content prune  # Remove unused content blocks

# Clean dangling layers
docker layer prune  # (if available)

# Remove image pull cache
rm -rf ~/.docker/manifests  # Local manifest cache
```

**Private registry authentication**:
```bash
# Test registry with credentials
docker login <registry>
docker pull <registry>/<image>

# Check kubelet image pull secrets
cat /etc/kubernetes/kubelet/kubeconfig | jq '.users'

# Create image pull secret for private registry
kubectl create secret docker-registry regcred \
  --docker-server=<registry> \
  --docker-username=<user> \
  --docker-password=<pass> \
  --docker-email=<email>
```

**Commands to NEVER use in production**:
```bash
# ❌ NEVER: docker system prune -a without backup
#    Deletes all unused images; may need for rollback
# ❌ NEVER: rm -rf /var/lib/docker/* while daemon running
#    Corrupts database; use docker stop first
# ❌ NEVER: Store registry credentials in shell history
#    Use: cat > ~/.docker/config.json (pipe method)
```

---

## Scenario: Diagnosing CI/CD Pipeline and Build Issues on Linux

**Prerequisites**: Builds failing, agent hanging, out of disk during builds, flaky tests  
**Common Causes**: Resource limits too low, temporary directory full, build tool incompatibility, file descriptor leak

```bash
# STEP 1: Check build agent/runner status
systemctl status jenkins  # Jenkins
systemctl status gitlab-runner  # GitLab
ps aux | grep -E "jenkins|runner" | grep -v grep

# STEP 2: Monitor build process resources
top -p <build-pid>
# Check: CPU, memory, number of threads

# STEP 3: Check temporary directory during build
df /tmp /var/tmp
# Should have > 10GB free for typical builds

# STEP 4: Check build workspace
du -sh /var/lib/jenkins/workspace/*  # Jenkins example
# Find largest workspace, may need cleanup

# STEP 5: Monitor file descriptors during build
watch -n 1 'lsof -p <build-pid> | wc -l'
# Rapidly growing FD count = FD leak

# STEP 6: Check build tool subprocess count
ps aux | grep <build-tool> | wc -l
# Hanging = process spawned but not cleaned up

# STEP 7: Check system load during build
uptime
# Should return to normal after build completes

# STEP 8: Monitor network I/O for artifact downloads
iftop -i <interface> -n
# Shows: Bandwidth consumed during dependency download

# STEP 9: Check build cache
du -sh /var/lib/jenkins/.cache  # or similar tool-specific cache
# May grow unbounded without cleanup

# STEP 10: Monitor build output size
du -sh /var/lib/jenkins/jobs/*/builds/*/
# Large build logs consume disk space

# STEP 11: Check for hung processes
ps aux | awk '$8 ~ /D/'
# Processes in D state (I/O wait) during build

# STEP 12: Verify build tool can access resources
# For Docker builds:
docker ps  # Should return quickly
# For compilation:
gcc --version  # Tool availability
```

**Build system diagnostics**:
```bash
# Check build agent connectivity to controller
# Jenkins: curl http://<controller>:8080/api/json
# GitLab: curl http://<controller>/api/v4/runners

# Monitor build log growth
tail -f /var/lib/jenkins/jobs/<job>/builds/latest/log | wc -l

# Check artifact repository
du -sh /var/lib/jenkins/jobs/*/builds/*/archive  # Artifacts

# Verify build tool environment
echo $PATH
env | grep -i java/python/node  # Check configured interpreters

# Test network connectivity during builds
wget https://repo.maven.apache.org/maven2/  # For Maven
# Simulate download to check bandwidth
```

**Build performance optimization**:
```bash
# Clear build workspace
rm -rf /var/lib/jenkins/workspace/*
# WARNING: May lose uncommitted work

# Disable unneeded build plugins
# Edit Jenkins config, reload

# Implement workspace retention policy
# Configure job: discard old builds after N days

# Increase build agent memory
# Edit: /etc/default/jenkins or systemd unit

# Enable parallel builds
export MAKEFLAGS=-j$(nproc)  # For make-based builds
mvn -T 1C clean install  # Maven parallel (1 thread per core)

# Implement artifact cleanup
find /var/lib/jenkins -name "*.old" -mtime +30 -delete
```

**Commands to NEVER use in production**:
```bash
# ❌ NEVER: Kill build process mid-build
#    Leaves temporary files and locks
# ❌ NEVER: rm -rf workspace during active build
#    Corrupts build state
# ❌ NEVER: Increase build memory without monitoring
#    Can cause OOM on build node
# ❌ NEVER: Run full system cleanup during build window
#    Impacts build performance
```

---

## Scenario: Diagnosing Node Time Synchronization and Clock Issues

**Prerequisites**: Certificates rejected, timestamps inconsistent, pods fail to schedule  
**Common Causes**: NTP not running, system clock skewed, timezone misconfigured

```bash
# STEP 1: Check current system time
date
# Shows: Current time and timezone

# STEP 2: Check if NTP is running
systemctl status ntp
systemctl status chrony  # Alternative NTP daemon
systemctl status ntpd

# STEP 3: Check NTP sync status
timedatectl
# Shows: System clock synchronized, timezone, NTP service status

# STEP 4: View NTP sync sources
ntpq -p  # ntpd
chronyc sources  # chronyd
# Shows: NTP servers and sync quality

# STEP 5: Check system time drift
timedatectl show | grep -i ntp
# Shows: NTP-sync status

# STEP 6: Monitor time changes
watch -n 1 date
# Should increment by 1 second per second

# STEP 7: Check hardware clock
hwclock --show
# Should be close to system time

# STEP 8: Verify timezone configuration
cat /etc/timezone
ls -l /etc/localtime

# STEP 9: Check for large time jumps in logs
grep -i "time" /var/log/syslog | tail -20
# Look for: Clock adjustment messages

# STEP 10: Test NTP connectivity to pool
timeout 2 ntpdate -q 0.pool.ntp.org
# Should show NTP server times
```

**Time synchronization recovery**:
```bash
# Manually sync with NTP server
ntpdate 0.pool.ntp.org

# Start NTP service
systemctl start ntp  # or chrony, ntpd

# Set system time if significantly off
date -s "2026-01-17 14:30:00"
hwclock --systohc  # Sync hardware clock

# Restart service affected by time skew
systemctl restart kubelet
systemctl restart docker

# For Kubernetes clusters, restart affected pods
kubectl delete pod <pod-name> -n <namespace>
# Will reschedule on correctly time-synced node
```

**Time verification for Kubernetes**:
```bash
# Check time sync on all nodes
for node in $(kubectl get nodes -o name); do
  kubectl debug node/$node -it --image=busybox -- date
done

# Verify certificate validity
openssl x509 -in /var/lib/kubelet/pki/kubelet.crt -text -noout | grep -A 2 "Validity"

# Check etcd time (critical)
kubectl exec -n kube-system etcd-$(hostname) -- date
```

**Commands to NEVER use in production**:
```bash
# ❌ NEVER: Disable NTP to "simplify" infrastructure
#    Time drift causes cascading failures
# ❌ NEVER: Set system time without stopping NTP
#    NTP will immediately correct it
# ❌ NEVER: Step time forward in large jumps (>1000s)
#    Breaks certificate validation and logs
```

---

## Scenario: Diagnosing SELinux/AppArmor Issues (Container Security)

**Prerequisites**: Containers failing to start with permission denied, read-only filesystem errors  
**Common Causes**: SELinux context mismatch, AppArmor profile too restrictive, volume mount labeling

```bash
# STEP 1: Check SELinux status
getenforce  # Returns: enforcing, permissive, disabled

# STEP 2: Get SELinux context of file
ls -Z <file>
# Shows: user:role:type:level

# STEP 3: View SELinux denials
grep denied /var/log/audit/audit.log | tail -20

# STEP 4: Get detailed denial info
audit2why < /var/log/audit/audit.log | tail -10
# Explains why access was denied

# STEP 5: Check pod SELinux context
kubectl get pod <pod> -n <namespace> -o jsonpath='{.spec.securityContext.seLinuxOptions}'

# STEP 6: Check container mount point labels
ls -dZ /var/lib/kubelet/pods/<pod-id>/volumes/kubernetes.io~secret/<mount>/
# Shows: SELinux labels on mount

# STEP 7: Check AppArmor status
aa-status  # If AppArmor installed
# Shows: Loaded profiles, mode

# STEP 8: View AppArmor denials
grep DENIED /var/log/kern.log | tail -20
# Or: journalctl | grep AppArmor | grep DENIED

# STEP 9: Check AppArmor profile for pod
cat /etc/apparmor.d/containers/<profile-name>

# STEP 10: Verify volume mount permissions in container
kubectl exec -it <pod> -n <namespace> -- ls -la /mnt/volume
# Should be readable by container user
```

**SELinux issue resolution**:
```bash
# Add context to volume mount
chcon -R system_u:object_r:container_file_t:s0 /var/lib/kubelet/pods/

# Generate policy from denials
audit2allow -a -M custom_policy
semodule -i custom_policy.pp

# Put SELinux in permissive mode temporarily (for debugging)
semanage permissive -a container_t

# Relabel filesystem
restorecon -R /var/lib/kubelet/

# For pod volume, use pod security context:
# spec:
#   securityContext:
#     seLinuxOptions:
#       type: spc_t (privileged type)
```

**AppArmor issue resolution**:
```bash
# Put AppArmor profile in complain mode
aa-complain /etc/apparmor.d/containers/profile

# View generated rules from denials
# Then audit2apparmor can generate new rules

# Reload AppArmor profiles
apparmor_parser -r /etc/apparmor.d/profile

# For pod, specify AppArmor profile:
# metadata:
#   annotations:
#     container.apparmor.security.beta.kubernetes.io/container: localhost/profile-name
```

**Commands to NEVER use in production**:
```bash
# ❌ NEVER: setenforce 0 to "fix" SELinux issues
#    Disables all SELinux protections; debug instead
# ❌ NEVER: Create overly permissive SELinux policies
#    Defeats purpose of mandatory access control
# ❌ NEVER: Delete AppArmor profiles without backup
#    May prevent container startup
```

---

## Critical Production Debugging Principles

### General Best Practices
1. **Read-only first**: Use `cat`, `grep`, `ps` before making changes
2. **Establish baseline**: Know normal values before diagnosing abnormal
3. **Change one variable at a time**: Makes root cause analysis possible
4. **Document everything**: Timestamp, change, reason, expected outcome
5. **Monitor impact**: Verify change had intended effect
6. **Have rollback plan**: Know how to revert immediately
7. **Iterate systematically**: Move from high-level to deep investigation
8. **Use appropriate tools**: `strace` for detailed, `top` for overview
9. **Check prerequisites**: Tools needed, permissions required, system state
10. **Understand limits**: System limits, socket limits, file descriptors, memory

### Investigation Methodology
```
1. Gather metrics (top, iostat, netstat, vmstat)
   ↓
2. Identify problem area (CPU, memory, disk, network)
   ↓
3. Isolate process/component (ps, lsof, netstat)
   ↓
4. Deep dive investigation (strace, gdb, profiling)
   ↓
5. Implement fix
   ↓
6. Monitor for improvement
   ↓
7. Document root cause and solution
```

### Dangerous Commands Checklist
```bash
# CRITICAL - NEVER in production:
rm -rf / or similar recursive deletion    # System destruction
kill -9 random PIDs                       # May kill critical services
dd if=/dev/zero of=/dev/sda              # Disk destruction
echo 1 > /proc/sys/vm/overcommit_memory  # OOM explosion
iptables -F without save                 # Lose all firewall rules
chmod 777 critical directories           # Severe security hole
strace/gdb on critical processes         # Performance degradation
echo 3 > /proc/sys/vm/drop_caches       # Severe cache flush
reboot without shutdown                  # Data corruption
```

### Essential Tools for Production
```bash
Mandatory:
- top/htop (process monitoring)
- ps (process status)
- iostat (disk I/O)
- netstat/ss (network connections)
- vmstat (system statistics)
- lsof (open files)
- grep/awk (log analysis)
- tail/head (file viewing)
- kill/systemctl (process control)

Highly Recommended:
- strace (syscall tracing)
- gdb (debugging)
- iotop (I/O monitoring)
- tcpdump (packet capture)
- sar (historical statistics)
- blktrace (kernel I/O trace)
- perf (performance profiling)
- jq (JSON parsing)
```

### Monitoring Thresholds
```
CPU:
  - Utilization: < 80% = good, 80-95% = degraded, > 95% = critical
  - Load average: < nproc*1.5 = acceptable, > nproc*2 = investigate

Memory:
  - Available: > 20% = good, 10-20% = caution, < 10% = critical
  - Swap: > 0 = pressure, > 10% = severe pressure

Disk:
  - Usage: < 80% = good, 80-90% = caution, > 90% = critical
  - I/O latency: < 5ms = good, 5-20ms = degraded, > 20ms = poor

Network:
  - Packet loss: 0% = good, < 1% = acceptable, > 1% = investigate
  - Connection count: < 10K = normal, 10-50K = monitor, > 50K = caution

I/O Queue:
  - Depth: < avg processes doing I/O = acceptable, > 2x = contention

File Descriptors:
  - Usage: < 60% limit = good, 60-80% = caution, > 80% = adjust
```

### Pre-Production Checklist
- [ ] All debugging changes tested in staging
- [ ] Rollback procedure documented
- [ ] Monitoring in place for changes
- [ ] Backup of critical configurations
- [ ] Team communication plan
- [ ] Expected recovery time estimated
- [ ] Alternative solutions identified

---

**Last Updated**: January 2026  
**OS Versions**: Linux 4.15+, macOS 10.14+  
**Severity Level**: Production Critical  
**Review Frequency**: Quarterly
