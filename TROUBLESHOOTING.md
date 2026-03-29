# SRESource Pod Troubleshooting & Debugging Guide

## Quick Start - What Was Fixed

The internal errors were caused by:
1. Undefined template variable `is_html` 
2. Missing error context in templates
3. File permission issues in Docker
4. Inadequate error logging

**All issues have been fixed.** To deploy:
```bash
./fix-and-deploy.sh
```

---

## Debugging Pod Issues

### Step 1: Check Pod Status

```bash
# See all sresource pods
kubectl get pods -l app=sresource -o wide

# Describe a specific pod
kubectl describe pod <pod-name>

# Check for recent errors
kubectl get events --sort-by='.lastTimestamp' | grep sresource
```

### Step 2: Check Logs

```bash
# Stream logs from all pods
kubectl logs -f -l app=sresource --all-containers=true

# Get logs from specific pod
kubectl logs <pod-name>

# Get last 50 lines with timestamps
kubectl logs <pod-name> --timestamps=true --tail=50

# Get logs from previous container (if it crashed)
kubectl logs <pod-name> --previous
```

### Step 3: Test Pod Connectivity

```bash
# Port-forward to test locally
kubectl port-forward svc/sresource 8080:8080

# Then test in another terminal
curl http://localhost:8080/
curl http://localhost:8080/kubernetes/debugging
```

### Step 4: Execute Commands in Pod

```bash
# Get a shell in the pod
kubectl exec -it <pod-name> -- sh

# Once inside, you can:
ls -la /app/
ls -la /app/docs/
python3 -c "from app import app; print(app.config['DOCS_DIR'])"
curl localhost:8080/
```

---

## Common Issues & Solutions

### Issue: "Internal Server Error" on page access

**Symptoms:**
- 500 errors when accessing pages
- Logs show "UndefinedError: 'is_html' is undefined"

**Solution:**
```bash
# Ensure app.py line has is_html defined
# Should be: return render_template('page.html', ..., is_html=True/False)

# Rebuild image
docker build -t sresource:latest .

# Force pod restart
kubectl delete pods -l app=sresource
```

### Issue: "File not found" errors

**Symptoms:**
- Logs show "File not found: /app/docs/..."
- 404 errors even for existing pages

**Solution:**
```bash
# Check if docs directory exists in pod
kubectl exec <pod-name> -- ls -la /app/docs/

# If empty, rebuild with COPY docs/
docker build -t sresource:latest .

# Or check docker build context
ls -la ./docs/
```

### Issue: "Permission denied" errors

**Symptoms:**
- Pod crashes or can't read files
- Logs show "Permission denied"

**Solution:**
```bash
# Check Dockerfile has proper chmod
# Should have: chmod -R 755 /app/docs /app/templates /app/static

# Verify in pod
kubectl exec <pod-name> -- ls -la /app/docs/

# Rebuild image with fixed Dockerfile
docker build -t sresource:latest .
```

### Issue: Pod in "CrashLoopBackOff" state

**Symptoms:**
- Pod keeps restarting
- Status shows "CrashLoopBackOff"

**Solution:**
```bash
# Check logs from last crash
kubectl logs <pod-name> --previous

# Common causes:
# 1. Python import errors - check requirements.txt
# 2. Port already in use - check service config
# 3. App crashes on startup - check app.py syntax

# To debug startup:
docker run -it sresource:latest sh
# Inside container, run: python3 -c "from app import app"
```

### Issue: Health check failing

**Symptoms:**
- Pod status shows "Unhealthy"
- Deployment not reaching desired replica count

**Solution:**
```bash
# Check health check configuration
kubectl get deployment sresource -o yaml | grep -A 10 livenessProbe

# Test endpoint manually
kubectl exec <pod-name> -- curl http://localhost:8080/

# If fails, check:
# 1. Is Flask app running? ps aux | grep python
# 2. Is port 8080 listening? netstat -tlnp | grep 8080
# 3. Check app.py __main__ section
```

---

## File Structure Verification

The container should have this structure:
```
/app/
├── app.py                 # Main Flask app
├── gunicorn_config.py    # WSGI config
├── templates/
│   ├── base.html
│   ├── page.html
│   ├── 404.html
│   └── 500.html
├── static/
│   ├── css/
│   │   └── style.css
│   └── favicon.ico
└── docs/
    ├── index.md
    ├── *.html            # Pre-generated HTML files
    └── *.md              # Markdown documentation files
```

**Verify in pod:**
```bash
kubectl exec <pod-name> -- find /app -type f -name "*.md" -o -name "*.html" | head -20
```

---

## Performance & Optimization

### Check resource usage
```bash
# Monitor CPU/Memory
kubectl top pods -l app=sresource

# Check resource requests/limits
kubectl describe pod <pod-name> | grep -A 5 "Limits\|Requests"
```

### Optimize if needed
```yaml
# In kubernetes/deployment.yaml, adjust:
resources:
  requests:
    memory: "128Mi"    # Increase if OOMKilled
    cpu: "100m"        # Increase if CPU throttled
  limits:
    memory: "512Mi"
    cpu: "500m"
```

---

## Logs Analysis

### Log format:
```
2026-01-20 02:15:30,123 - gunicorn.access - INFO - 127.0.0.1 - - [timestamp] "GET / HTTP/1.1" 200 5234 "-" "curl/7.68.0"
```

### Important log levels:
- **ERROR**: Problem that needs immediate attention
- **WARNING**: Potential issue, application still running
- **INFO**: Normal operation information
- **DEBUG**: Detailed troubleshooting information

### Commands to filter logs:
```bash
# Only errors
kubectl logs <pod-name> | grep ERROR

# Only warnings and errors
kubectl logs <pod-name> | grep -E "ERROR|WARNING"

# Specific route access
kubectl logs <pod-name> | grep "/kubernetes/debugging"

# Slow requests (check duration)
kubectl logs <pod-name> | awk -F' ' '{print $(NF-1)}' | sort -rn | head
```

---

## Reset & Redeploy

If issues persist, do a clean reset:

```bash
# 1. Delete deployment
kubectl delete deployment sresource

# 2. Rebuild image
docker build -t sresource:latest .

# 3. Re-apply deployment
kubectl apply -f kubernetes/deployment.yaml

# 4. Monitor pods
kubectl get pods -l app=sresource --watch

# 5. Check logs
kubectl logs -f -l app=sresource
```

---

## Advanced Debugging

### Enable debug logging
```bash
# Edit app.py and set debug=True (for development only)
# Or set environment variable:
kubectl set env deployment/sresource DEBUG=1

# Restart pods
kubectl rollout restart deployment/sresource
```

### Inspect network connectivity
```bash
# From pod, test external connectivity
kubectl exec <pod-name> -- curl https://www.google.com

# Check DNS
kubectl exec <pod-name> -- nslookup kubernetes.default

# Check service discovery
kubectl exec <pod-name> -- env | grep SERVICE
```

### Resource limits investigation
```bash
# Check if pod is memory limited
kubectl describe pod <pod-name> | grep -A 5 "Last State"

# Increase limits and redeploy
# Edit kubernetes/deployment.yaml and increase memory/cpu limits
```

---

## Contact & Escalation

If issues persist after trying all steps:

1. **Collect diagnostic bundle:**
```bash
kubectl describe all -l app=sresource > diagnostic_info.txt
kubectl logs -l app=sresource --all-containers=true > pod_logs.txt
docker inspect sresource:latest > image_info.json
```

2. **Check recent changes:**
   - Review git diff for recent commits
   - Compare with working version
   - Check for missing dependencies

3. **Rebuild from scratch:**
   - Delete old images: `docker rmi sresource`
   - Clean build: `docker build --no-cache -t sresource:latest .`
   - Force pod recreation: `kubectl delete pods -l app=sresource`

---

## Prevention Best Practices

1. **Always test locally first:**
   ```bash
   docker-compose up
   curl http://localhost:8080/
   docker-compose down
   ```

2. **Monitor logs regularly:**
   ```bash
   kubectl logs -f -l app=sresource
   ```

3. **Set up alerts for:**
   - CrashLoopBackOff state
   - Failed health checks
   - High error rates

4. **Keep documentation updated:**
   - Update this guide when adding features
   - Document any custom configurations
   - Maintain runbooks for common issues

5. **Version your images:**
   ```bash
   docker tag sresource:latest sresource:v1.0.0
   docker push sresource:v1.0.0
   ```
