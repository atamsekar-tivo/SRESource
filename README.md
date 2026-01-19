# SRESource

> **Comprehensive production debugging and operations guide for SRE/DevOps/Platform Engineers**

![Build Status](https://github.com/atamsekar-tivo/SRESource/workflows/Build%20and%20Push%20Docker%20Image/badge.svg)
![License](https://img.shields.io/badge/license-CC%20BY--SA%204.0-blue)
![Kubernetes](https://img.shields.io/badge/kubernetes-1.20+-blue)
![Python](https://img.shields.io/badge/python-3.11+-blue)
![Flask](https://img.shields.io/badge/flask-3.0+-blue)

SRESource is a **self-hosted, production-ready knowledge base** built on **Flask + Gunicorn** for SRE/DevOps/Platform teams. It renders Markdown/HTML docs dynamically, ships as a container, and is ready for Kubernetes/Helm.

## Content Coverage

- **Kubernetes** - Debugging, EKS, troubleshooting
- **Linux/Unix** - System performance, troubleshooting, administration
- **Networking** - Network debugging, multi-cloud connectivity
- **CI/CD** - Jenkins, GitHub Actions, ArgoCD, GitLab CI, Spinnaker
- **Cloud & Infrastructure** - IAM, AWS, GCP, Azure debugging
- **Databases** - MySQL & PostgreSQL production debugging
- **Tools & Resources** - Essential SRE/DevOps tools guide

**Total**: 60+ debugging scenarios | 400+ production-ready commands | ~30,000 lines of content

##  Getting Started

### Local Development (Docker Compose)

```bash
git clone https://github.com/atamsekar-tivo/SRESource.git
cd SRESource

docker-compose up -d
# Application at http://localhost:8080
```

### Local (Python)

```bash
pip install -r requirements.txt
python app.py            # http://localhost:5000
```

### Production Deployment (Kubernetes)

**With kubectl:**
```bash
kubectl apply -f kubernetes/
kubectl port-forward svc/sresource 8080:80
# Access at http://localhost:8080
```

**With Helm (Recommended):**
```bash
helm install sresource ./helm/sresource \
  --namespace sresource-prod \
  --create-namespace

kubectl get svc -n sresource-prod
```

## Docker Image

The container bundles the Flask app + docs and runs under gunicorn (non-root, port 8080):

```bash
# Build locally
docker build -t sresource:latest .

# Run container
docker run -p 8080:8080 sresource:latest
```

**Image Specifications:**
- **Base:** Python 3.11 Alpine
- **Server:** Gunicorn (4 workers, 2 threads)
- **Port:** 8080
- **Security:** Non-root user (uid: 1000), health checks included

## Project Structure

```
SRESource/
├── app.py                    # Flask application (routes + rendering)
├── templates/                # Jinja2 templates (base/page/404/500)
├── static/css/style.css      # UI theme (dark mode, responsive)
├── docs/                     # Markdown/HTML content (served dynamically)
├── kubernetes/               # K8s manifests
├── helm/sresource/           # Helm chart
├── docker-compose.yml        # Local dev (gunicorn)
├── Dockerfile                # Multi-stage build (gunicorn, non-root)
├── FLASK_README.md           # Migration quick reference
├── MIGRATION_GUIDE.md        # mkdocs → Flask deep dive
├── FLASK_MIGRATION_SUMMARY.md# Summary of changes
├── FLASK_MIGRATION_CHECKLIST.md# Verification checklist
└── mkdocs.yml                # Legacy (kept for reference, not used)
```

## Features

- - Dynamic Flask rendering of docs (Markdown/HTML) with code highlighting
- - Responsive UI + dark mode (Jinja2 templates + CSS)
- - Health checks, non-root user, resource limits, HPA-ready
- - Helm chart + K8s manifests + docker-compose for local dev
- - Fast startup (no mkdocs build step), gunicorn workers/threads tuned

## Performance Specs

| Metric | Value |
|--------|-------|
| Image Size | ~120MB |
| Memory (request) | 128Mi |
| Memory (limit) | 256Mi |
| CPU (request) | 100m |
| CPU (limit) | 500m |
| Build Time | ~2-3 minutes |
| Startup Time | ~5-10 seconds |
| Response Time | <100ms (typical) |

## Development

- Python 3.11+, Docker/Docker Compose, Kubernetes 1.20+, Helm 3+.  
- Local dev: `python app.py` (or `FLASK_ENV=development python app.py`) for hot reload.  
- Container dev: `docker-compose up -d` (gunicorn).  
- MkDocs is retired; `mkdocs.yml` remains only for historical reference.

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Editing Content

All documentation is in `docs/` directory as Markdown files:

```bash
# Edit existing guide
vim docs/kubernetes-debugging-commands.md

# Or add new guide
cp docs/template.md docs/my-new-guide.md
```

Changes automatically appear in MkDocs when saved.

##  Deployment Examples

### Kubernetes with Ingress

```bash
# Deploy with custom domain
helm install sresource ./helm/sresource \
  --set ingress.enabled=true \
  --set ingress.hosts[0].host=sresource.example.com

# Create certificate (if using cert-manager)
kubectl apply -f - << EOF
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: sresource-cert
spec:
  secretName: sresource-tls
  issuerRef:
    name: letsencrypt-prod
  dnsNames:
  - sresource.example.com
EOF
```

### EKS Deployment

```bash
# Deploy to EKS cluster
helm install sresource ./helm/sresource \
  --kubeconfig=$AWS_KUBECONFIG \
  --set image.repository=<your-ecr-repo>/sresource
```

### Multi-Environment

```bash
# Production
helm install sresource ./helm/sresource \
  -f helm/values-prod.yaml

# Staging
helm install sresource ./helm/sresource \
  -f helm/values-staging.yaml

# Development
helm install sresource ./helm/sresource \
  -f helm/values-dev.yaml
```

## Content Statistics

| Category | Count | Lines |
|----------|-------|-------|
| Kubernetes | 2 guides | 4,500+ |
| Linux/Unix | 1 guide | 3,500+ |
| Networking | 1 guide | 2,800+ |
| CI/CD | 1 guide | 2,200+ |
| IAM | 1 guide | 2,000+ |
| EKS | 1 guide | 3,000+ |
| Tools | 1 guide | 2,500+ |
| Databases | 1 guide | 4,000+ |
| **Total** | **9 guides** | **~30,000 lines** |

## Security

- - Non-root user (UID 1000)
- - Read-only root filesystem
- - Dropped all capabilities
- - No privileged container mode
- - Security scanning in CI/CD (Trivy)
- - Minimal base image (Alpine Linux)
- - Health checks configured
- - Resource limits enforced

## Documentation

- [Official MkDocs Documentation](https://www.mkdocs.org/)
- [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Helm Documentation](https://helm.sh/docs/)

## Issues & Support

Found a bug? Have a suggestion? [Create an issue](https://github.com/atamsekar-tivo/SRESource/issues)

## License

This project is licensed under the **Creative Commons Attribution-ShareAlike 4.0 International License** - see [LICENSE](LICENSE) file for details.

## Author

**Anirudh Tamsekar**
- GitHub: [@atamsekar-tivo](https://github.com/atamsekar-tivo)
- Email: atamsekar@example.com

## Acknowledgments

- [MkDocs](https://www.mkdocs.org/) - Static site generator
- [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/) - Beautiful theme
- [Kubernetes](https://kubernetes.io/) - Orchestration platform
- [Helm](https://helm.sh/) - Kubernetes package manager

---

If you find this useful, please star the repository.
