# SRESource

> **Comprehensive production debugging and operations guide for SRE/DevOps/Platform Engineers**

![Build Status](https://github.com/atamsekar-tivo/SRESource/workflows/Build%20and%20Push%20Docker%20Image/badge.svg)
![License](https://img.shields.io/badge/license-CC%20BY--SA%204.0-blue)
![Kubernetes](https://img.shields.io/badge/kubernetes-1.20+-blue)

SRESource is a **self-hosted, production-ready knowledge base** for Site Reliability Engineers, DevOps professionals, and Platform Engineers. It provides comprehensive debugging commands, operational procedures, and best practices across multiple domains.

## 📚 Content Coverage

- **Kubernetes** - Debugging, EKS, troubleshooting
- **Linux/Unix** - System performance, troubleshooting, administration
- **Networking** - Network debugging, multi-cloud connectivity
- **CI/CD** - Jenkins, GitHub Actions, ArgoCD, GitLab CI, Spinnaker
- **Cloud & Infrastructure** - IAM, AWS, GCP, Azure debugging
- **Databases** - MySQL & PostgreSQL production debugging
- **Tools & Resources** - Essential SRE/DevOps tools guide

**Total**: 60+ debugging scenarios | 400+ production-ready commands | ~30,000 lines of content

## 🚀 Quick Start

### Option 1: Docker Compose (Local Development)

```bash
# Clone the repository
git clone https://github.com/atamsekar-tivo/SRESource.git
cd SRESource

# Start with Docker Compose
docker-compose up -d

# Access at http://localhost:8080
```

### Option 2: Kubernetes Deployment

```bash
# Using kubectl
kubectl apply -f kubernetes/

# Or using Helm (recommended)
helm install sresource ./helm/sresource \
  --values helm/sresource/values.yaml

# Port forward to access
kubectl port-forward svc/sresource 8080:80

# Access at http://localhost:8080
```

### Option 3: Helm Chart

```bash
# Add to your values
helm repo add sresource https://charts.example.com
helm repo update

# Install with Helm
helm install sresource sresource/sresource \
  --set ingress.hosts[0].host=sresource.example.com
```

## 🐳 Docker Image

Pre-built images available:

```bash
# Latest version
docker pull atamsekar/sresource:latest

# Specific version
docker pull atamsekar/sresource:v1.0.0

# Run locally
docker run -p 8080:8080 atamsekar/sresource:latest
```

Images are automatically built and pushed on every commit to `main` branch.

## 📋 Structure

```
SRESource/
├── docs/                           # All markdown documentation
│   ├── index.md                   # Homepage
│   ├── kubernetes-debugging-commands.md
│   ├── production-debugging-unix-linux.md
│   ├── production-networking-debugging.md
│   ├── production-debugging-ci-cd-tools.md
│   ├── production-debugging-iam.md
│   ├── production-debugging-eks.md
│   ├── TOOLS_GUIDE.md
│   └── production-debugging-databases.md
├── kubernetes/                     # K8s manifests
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   └── kustomization.yaml
├── helm/                           # Helm chart
│   └── sresource/
│       ├── Chart.yaml
│       ├── values.yaml
│       └── templates/
├── .github/workflows/              # CI/CD automation
│   └── build-and-push.yml
├── Dockerfile                      # Multi-stage Docker build
├── docker-compose.yml              # Local development
├── mkdocs.yml                      # MkDocs configuration
└── README.md                       # This file
```

## 🔧 Features

- ✅ **Fast Search** - Full-text search across all content
- ✅ **Dark Mode** - Eye-friendly dark theme
- ✅ **Code Highlighting** - Syntax highlighting for all code blocks
- ✅ **Mobile Responsive** - Works on mobile, tablet, desktop
- ✅ **Auto-generated TOC** - Automatic table of contents
- ✅ **Git Integration** - Shows last modified date
- ✅ **Multiple Themes** - Material Design theme
- ✅ **Low Resource** - ~256MB memory, ~100m CPU per pod
- ✅ **Highly Available** - Multi-pod deployment with anti-affinity
- ✅ **Secure** - Non-root user, read-only filesystem, drop all capabilities

## 📊 Performance Specs

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

## 🛠️ Development

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Kubernetes 1.20+ (for K8s deployment)
- Helm 3+ (for Helm chart)

### Local Development

```bash
# Install Python dependencies
pip install mkdocs mkdocs-material mkdocs-git-revision-date-localized-plugin

# Run MkDocs server (live reload)
mkdocs serve

# Access at http://localhost:8000
```

### Building Docker Image

```bash
# Build locally
docker build -t sresource:local .

# Run
docker run -p 8080:8080 sresource:local

# Test
curl http://localhost:8080
```

## 📝 Contributing

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

## 🚀 Deployment Examples

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

## 📚 Content Statistics

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

## 🔐 Security

- ✅ Non-root user (UID 1000)
- ✅ Read-only root filesystem
- ✅ Dropped all capabilities
- ✅ No privileged container mode
- ✅ Security scanning in CI/CD (Trivy)
- ✅ Minimal base image (Alpine Linux)
- ✅ Health checks configured
- ✅ Resource limits enforced

## 📖 Documentation

- [Official MkDocs Documentation](https://www.mkdocs.org/)
- [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Helm Documentation](https://helm.sh/docs/)

## 🐛 Issues & Support

Found a bug? Have a suggestion? [Create an issue](https://github.com/atamsekar-tivo/SRESource/issues)

## 📄 License

This project is licensed under the **Creative Commons Attribution-ShareAlike 4.0 International License** - see [LICENSE](LICENSE) file for details.

## 👨‍💼 Author

**Anirudh Tamsekar**
- GitHub: [@atamsekar-tivo](https://github.com/atamsekar-tivo)
- Email: atamsekar@example.com

## 🙏 Acknowledgments

- [MkDocs](https://www.mkdocs.org/) - Static site generator
- [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/) - Beautiful theme
- [Kubernetes](https://kubernetes.io/) - Orchestration platform
- [Helm](https://helm.sh/) - Kubernetes package manager

---

**Made with ❤️ for the SRE/DevOps community**

⭐ If you find this useful, please star the repository!