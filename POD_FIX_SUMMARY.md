# SRESource Pods Internal Error Fix

## Issues Fixed

### 1. **Template Rendering Error (Primary Issue)**
   - **Problem**: `page.html` was attempting to override the content block but `is_html` variable wasn't always defined
   - **Solution**: Added proper template variable checking with `is_html is defined`
   - **Files Modified**: `templates/page.html`, `templates/base.html`

### 2. **Missing is_html Flag in Routes**
   - **Problem**: Some routes weren't explicitly setting `is_html=False` for markdown content
   - **Solution**: Updated routes to always pass `is_html` flag (False for markdown, True for pre-generated HTML)
   - **Files Modified**: `app.py` (updated index and getting_started routes)

### 3. **Inadequate Error Handling**
   - **Problem**: File reading errors weren't being logged or handled gracefully
   - **Solution**: Added try-catch blocks with logging to all file reading functions
   - **Files Modified**: `app.py` (read_markdown_file, read_html_file functions)

### 4. **Missing Error Context in Templates**
   - **Problem**: Error handler templates weren't receiving nav_structure
   - **Solution**: Updated error handlers to pass nav_structure to templates
   - **Files Modified**: `app.py` (errorhandler decorators)

### 5. **File Permission Issues in Docker**
   - **Problem**: Non-root user couldn't read docs, templates, or static files
   - **Solution**: Added explicit chmod 755 for all application directories in Dockerfile
   - **Files Modified**: `Dockerfile`

### 6. **Suboptimal Gunicorn Configuration**
   - **Problem**: Inline gunicorn command could be improved for better logging and debugging
   - **Solution**: Created dedicated gunicorn_config.py with proper worker configuration
   - **Files Modified**: `Dockerfile`, new file `gunicorn_config.py`

### 7. **Logging Not Configured**
   - **Problem**: Application wasn't logging errors to stdout for pod visibility
   - **Solution**: Added proper logging configuration to app.py and gunicorn
   - **Files Modified**: `app.py`

## Deployment Steps

### For Local Testing:

```bash
# Build the image
docker build -t sresource:latest .

# Run with docker-compose
docker-compose up --build

# Test the application
curl http://localhost:8080/
curl http://localhost:8080/getting-started
curl http://localhost:8080/kubernetes/debugging
```

### For Kubernetes Deployment:

```bash
# Using kubectl with existing deployment
kubectl delete pods -l app=sresource

# Or using helm
helm upgrade sresource ./helm/sresource/ -f helm/values.yaml

# Check pod status
kubectl get pods -l app=sresource
kubectl logs -f -l app=sresource
```

### If pods still fail, debug with:

```bash
# Check pod status and events
kubectl describe pod <pod-name>

# Stream logs from pod
kubectl logs -f <pod-name>

# Execute into pod
kubectl exec -it <pod-name> -- sh

# Inside pod, test Flask app directly
cd /app
python3 -c "from app import app; print(app.config['DOCS_DIR'])"
ls -la /app/docs/
```

## Key Changes Summary

| Component | Change | Impact |
|-----------|--------|--------|
| templates/page.html | Added `is_html is defined` check | Prevents UndefinedError |
| templates/base.html | Removed duplicate content rendering | Prevents double rendering |
| app.py | Added error logging and file existence checks | Better error visibility |
| app.py | Error handlers now pass nav_structure | Error pages render correctly |
| Dockerfile | Added chmod for directories | Non-root user can read files |
| Dockerfile | Uses gunicorn config file | Better logging and worker config |
| gunicorn_config.py | New file with proper WSGI config | Improved performance and debugging |

## Verification Checklist

- [ ] Docker image builds successfully: `docker build -t sresource:latest .`
- [ ] Container starts: `docker run -p 8080:8080 sresource:latest`
- [ ] Homepage loads: `curl http://localhost:8080/`
- [ ] Documentation pages load: `curl http://localhost:8080/kubernetes/debugging`
- [ ] Kubernetes pod becomes ready: `kubectl get pods -l app=sresource`
- [ ] Health check passes: `kubectl describe pod <pod-name> | grep -A 10 Health`
- [ ] Logs show no errors: `kubectl logs <pod-name>`

## Notes

- The application runs on port 8080 as specified in the deployment
- Gunicorn runs with multiple workers for better concurrency
- All errors are logged with timestamps for troubleshooting
- The docs directory is mounted as read-only in the container
- Non-root user (flask) runs the application for security
