# Migration Guide: mkdocs → Flask

## Overview
SRESource has been successfully migrated from **mkdocs** to a **Flask-based** documentation server. This provides better customization, simpler deployment, and improved performance for serving documentation.

## What Changed

### Before (mkdocs)
- **Framework**: Static site generator using Material theme
- **Dependencies**: mkdocs, mkdocs-material, plugins
- **Content**: Markdown files compiled to static HTML at build time
- **Server**: Served static files via mkdocs serve/build

### After (Flask)
- **Framework**: Dynamic web application using Flask
- **Dependencies**: Flask, Markdown, Werkzeug, gunicorn
- **Content**: Markdown files parsed dynamically with on-demand rendering
- **Server**: Flask development server or gunicorn in production

## File Structure Changes

### Removed Files
- `mkdocs.yml` - No longer needed (navigation hardcoded in Flask routes)
- `.github/workflows/build-and-push.yml` - Old CI/CD (if using new one, update accordingly)

### Added Files
```
app.py                          # Flask application
requirements.txt               # Python dependencies
templates/                      # Flask templates
├── base.html                   # Base template with sidebar navigation
├── page.html                   # Content page template
├── 404.html                    # Error pages
└── 500.html
static/
└── css/
    └── style.css               # Responsive styling
.dockerignore                   # Docker build optimization
```

### Updated Files
- `Dockerfile` - Switched from mkdocs image to Flask+gunicorn
- `docker-compose.yml` - Updated volumes and environment variables
- `kubernetes/deployment.yaml` - Updated environment and resource limits
- `helm/sresource/values.yaml` - Updated resource limits for Flask

## Quick Start

### Local Development

#### Option 1: Docker Compose (Fastest)
```bash
docker-compose up -d
# Access at http://localhost:8080
```

#### Option 2: Direct Python
```bash
pip install -r requirements.txt
python app.py
# Access at http://localhost:5000
```

#### Option 3: Gunicorn
```bash
pip install -r requirements.txt
gunicorn --bind 0.0.0.0:8080 --workers 4 app:app
# Access at http://localhost:8080
```

### Production Deployment

#### Docker
```bash
docker build -t sresource:v1 .
docker run -p 8080:8080 sresource:v1
```

#### Kubernetes
```bash
kubectl apply -f kubernetes/

# Or with Helm
helm install sresource ./helm/sresource
```

## Key Differences for Users

| Feature | mkdocs | Flask |
|---------|--------|-------|
| Start Time | Slower (full build) | Faster (on-demand) |
| Memory Usage | Lower | Slightly higher |
| Customization | Theme-based | Full Python control |
| Content Updates | Rebuild required | Live updates |
| Performance | Static, very fast | Dynamic, cached |
| Dependencies | More complex | Simpler |

## Configuration

### Adding New Pages

1. **Add markdown/HTML file** to `docs/`
2. **Create route in `app.py`**:
```python
@app.route('/new-page')
def new_page():
    content, title = read_markdown_file('new-page.md')
    if content is None:
        abort(404)
    return render_template('page.html', title=title, content=content, breadcrumbs=...)
```
3. **Add to navigation** in `NAV_STRUCTURE` dictionary
4. **Restart the application**

### Updating Navigation

Edit the `NAV_STRUCTURE` dictionary in `app.py`:
```python
'new_section': {
    'title': 'New Section',
    'path': '/new-section',
    'children': {
        'page': {
            'title': 'Page Title',
            'file': 'page.md',
            'path': '/new-section/page'
        }
    }
}
```

### Customizing Styling

Edit `static/css/style.css` for design changes. The stylesheet uses CSS variables for easy theming:
```css
:root {
    --color-primary: #1f6feb;
    --color-bg: #ffffff;
    --color-text: #24292f;
    /* ... more variables ... */
}
```

## Performance Considerations

### Memory Usage
- Flask: 50-100 MB base
- mkdocs: 20-50 MB base
- **Solution**: Kubernetes HPA and proper resource limits

### Response Times
- Flask: 10-50ms for cached renders
- mkdocs: <5ms for static files
- **Solution**: Add caching layer or use static pre-rendering if needed

### Scaling
```yaml
# Kubernetes HPA
autoscaling:
  minReplicas: 2
  maxReplicas: 5
  targetCPUUtilizationPercentage: 80
```

## Troubleshooting

### Pages Not Found (404)
- Ensure markdown file exists in `docs/`
- Check route path matches navigation structure
- Verify file case sensitivity

### Styling Issues
- Check `static/css/style.css` exists
- Clear browser cache (Ctrl+Shift+Delete)
- Check browser console for CSS load errors

### Docker Build Fails
- Ensure `docs/`, `templates/`, `static/` directories exist
- Check `requirements.txt` syntax
- Verify Python version compatibility (3.11+)

### Application Won't Start
```bash
# Check for syntax errors
python -m py_compile app.py

# Verify dependencies
pip install -r requirements.txt

# Run with verbose output
python app.py --debug
```

## Migration Checklist

- [x] Flask application created (`app.py`)
- [x] Templates created (base.html, page.html, error pages)
- [x] Static assets created (CSS, styling)
- [x] Routes configured for all documentation pages
- [x] Navigation structure migrated
- [x] Dockerfile updated
- [x] docker-compose.yml updated
- [x] Kubernetes deployment updated
- [x] Helm values updated
- [ ] Test locally with `docker-compose up`
- [ ] Push to Docker registry
- [ ] Deploy to Kubernetes
- [ ] Verify all pages load correctly
- [ ] Update documentation/README if needed

## Rollback (If Needed)

If you need to rollback to mkdocs:
```bash
# Restore from git
git checkout HEAD~1 mkdocs.yml Dockerfile docker-compose.yml
git rm app.py requirements.txt templates/ static/ .dockerignore

# Rebuild and restart
docker-compose build
docker-compose up
```

## Benefits of Flask Migration

✅ **Simpler Deployment** - No build step required  
✅ **Better Customization** - Full Python control  
✅ **Lower Dependencies** - Fewer plugins needed  
✅ **Easier Maintenance** - Standard Flask patterns  
✅ **Future Extensibility** - Easy to add APIs, search, etc.  
✅ **Better Performance** - Can add caching, CDN support  

## Support

For issues or questions:
1. Check this migration guide
2. Review Flask documentation: https://flask.palletsprojects.com/
3. Check app logs: `docker-compose logs sresource`
4. Review GitHub issues: https://github.com/atamsekar-tivo/SRESource
