# Content Formatting Guide for SRESource

This guide shows the recommended way to structure content for maximum readability.

## Problem: Before (Overloaded)

```
Check logs: tail -f /var/log/app.log # Follow logs in real-time for debugging purposes and monitoring application
List processes: ps aux | grep nginx # Show all running processes and filter for nginx specifically for checking if service is running
Check port: netstat -tulpn | grep 8080 # Display all listening ports with associated processes for port 8080
```

## Solution: After (Clean & Readable)

### View Application Logs

**Command:**
```bash
tail -f /var/log/app.log
```

**Purpose:** Follow logs in real-time for debugging and monitoring.

---

### List Running Processes

**Command:**
```bash
ps aux | grep nginx
```

**Purpose:** Show all running processes and filter for nginx to verify the service is running.

---

### Check Port Status

**Command:**
```bash
netstat -tulpn | grep 8080
```

**Purpose:** Display all listening ports and their associated processes, specifically checking port 8080.

---

## Recommended Structure

### 1. Use Admonitions for Context

!!! note "Quick Reference"
    For quick command lookup without explanations.

!!! tip "Pro Tip"
    Additional insights or best practices.

!!! warning "Important"
    Critical information users should know.

!!! danger "Caution"
    Warning about potentially harmful operations.

### 2. Use Tabs for Multiple Options

=== "Option 1: Simple"
    ```bash
    kubectl get pods
    ```

=== "Option 2: Detailed"
    ```bash
    kubectl get pods -o wide
    ```

=== "Option 3: YAML Output"
    ```bash
    kubectl get pods -o yaml
    ```

### 3. Use Tables for Comparisons

| Command | Purpose | When to Use |
|---------|---------|------------|
| `kubectl get` | List resources | Quick overview |
| `kubectl describe` | Detailed view | Debugging issues |
| `kubectl logs` | View logs | Troubleshooting |

### 4. Use Details (Expandable Sections)

??? "Click to expand: Advanced Debugging"
    These commands are more advanced and should only be used when basic troubleshooting fails.
    
    ```bash
    strace -p <pid>
    ```

### 5. Visual Hierarchy with Headers

```markdown
# Main Topic (Level 1)

## Subtopic (Level 2)

### Specific Command (Level 3)

**Command:**
```bash
your-command
```

**Output:**
```
expected output here
```

**Explanation:** Clear, concise explanation of what happened.
```

## Example: Kubernetes Debugging

### Check Pod Status

**Command:**
```bash
kubectl get pods
```

**Output:**
```
NAME                     READY   STATUS    RESTARTS   AGE
app-deployment-5d4fb47   1/1     Running   0          2d
nginx-6f8b8c4b8f-hj9l2   1/1     Running   1          5d
```

**Explanation:** Shows all pods in the current namespace with their status and uptime.

---

### Get Detailed Pod Information

**Command:**
```bash
kubectl describe pod <pod-name>
```

**Output:**
```
Name:         app-deployment-5d4fb47
Namespace:    default
Status:       Running
IP:           10.244.0.5
```

**Explanation:** Provides detailed information about a specific pod, useful for debugging.

---

### View Pod Logs

**Command:**
```bash
kubectl logs <pod-name>
```

**Options:**
- `-f` : Follow logs in real-time
- `--tail=50` : Show last 50 lines
- `-p` : Show previous logs (if pod restarted)

**Example:**
```bash
kubectl logs my-pod -f --tail=50
```

---

## Best Practices

1. **One concept per section** - Keep topics focused
2. **Command first** - Show the command prominently
3. **Output second** - Show what the output looks like
4. **Explanation last** - Explain what it means
5. **Use spacing** - Don't crowd content
6. **Use color/admonitions** - Highlight important info
7. **Add options** - Show common flags separately
8. **Real examples** - Use realistic output samples

## Result

This structure makes it easy to:

- ✅ **Scan quickly** - Find what you need fast
- ✅ **Copy commands** - Clear code blocks
- ✅ **Understand context** - Explanations are separate
- ✅ **Learn options** - See common variations
- ✅ **Remember output** - See realistic examples
