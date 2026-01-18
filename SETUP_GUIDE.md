# SRESource Setup Guide

Complete SRESource project has been created locally at `/Users/anirudh.tamsekar/SRESource/`. Follow these steps to push to GitHub and get it running.

## Step 1: Create Repository on GitHub

1. Go to [https://github.com/new](https://github.com/new)
2. Fill in the form:
   - **Repository name**: `SRESource`
   - **Description**: `Comprehensive production debugging guide for SRE/DevOps/Platform Engineers`
   - **Public/Private**: Public (recommended for knowledge sharing)
   - **Initialize**: NO (we already have files)
   - **License**: None (we're using CC-BY-SA 4.0 in the repo)
3. Click "Create repository"

## Step 2: Push to GitHub

Run these commands in your terminal:

```bash
cd /Users/anirudh.tamsekar/SRESource

# Add GitHub as remote origin
git remote add origin https://github.com/atamsekar-tivo/SRESource.git

# Rename branch to main (if needed)
git branch -M main

# Push to GitHub
git push -u origin main

# Verify
git remote -v
```

Expected output:
```
origin  https://github.com/atamsekar-tivo/SRESource.git (fetch)
origin  https://github.com/atamsekar-tivo/SRESource.git (push)
```

## Step 3: Set Up GitHub Secrets (for Docker Hub pushes)

For automated Docker image builds:

1. Go to [https://github.com/atamsekar-tivo/SRESource/settings/secrets/actions](https://github.com/atamsekar-tivo/SRESource/settings/secrets/actions)
2. Click "New repository secret"
3. Add two secrets:
   - **Name**: `DOCKER_USERNAME`  
     **Value**: Your Docker Hub username
   - **Name**: `DOCKER_PASSWORD`  
     **Value**: Your Docker Hub token (or password)

If you don't have Docker Hub account:
- Sign up: [https://hub.docker.com/signup](https://hub.docker.com/signup)
- Create token: Go to Account Settings → Security → New Access Token

## Step 4: Test Local Build

```bash
cd /Users/anirudh.tamsekar/SRESource

# Build Docker image locally
docker build -t sresource:local .

# Run container
docker run -p 8080:8080 sresource:local

# Visit http://localhost:8080 in browser
# Press Ctrl+C to stop
```

## Step 5: Test with Docker Compose (Recommended for Development)

```bash
cd /Users/anirudh.tamsekar/SRESource

# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Visit http://localhost:8080

# Stop services
docker-compose down
```

## Step 6: Deploy to Kubernetes

### Option A: Kubernetes Manifests Only

```bash
cd /Users/anirudh.tamsekar/SRESource

# Apply all manifests
kubectl apply -f kubernetes/

# Check deployment
kubectl get deployments
kubectl get svc
kubectl logs -f deployment/sresource

# Port forward
kubectl port-forward svc/sresource 8080:80

# Visit http://localhost:8080
```

### Option B: Using Helm (Recommended)

```bash
cd /Users/anirudh.tamsekar/SRESource

# Install with Helm
helm install sresource ./helm/sresource

# Check deployment
helm list
helm status sresource
kubectl get pods -l app=sresource

# Port forward
kubectl port-forward svc/sresource 8080:80

# Visit http://localhost:8080

# Later: Upgrade
helm upgrade sresource ./helm/sresource --values helm/sresource/values.yaml

# Later: Uninstall
helm uninstall sresource
```

### Option C: Using Kustomize

```bash
cd /Users/anirudh.tamsekar/SRESource

# Apply with Kustomize
kubectl apply -k kubernetes/

# Port forward
kubectl port-forward svc/sresource 8080:80

# Visit http://localhost:8080
```

## Step 7: Configure DNS & Ingress (Production)

For real production deployment, configure ingress with your domain:

```bash
# Edit ingress manifest or values
# Update sresource.example.com to your actual domain

# Install ingress controller (if not already installed)
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.1/deploy/static/provider/cloud/deploy.yaml

# Install cert-manager for HTTPS
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Create certificate issuer
kubectl apply -f - << 'EOF'
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: your-email@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF

# Deploy SRESource
helm install sresource ./helm/sresource \
  --set ingress.enabled=true \
  --set ingress.hosts[0].host=sresource.example.com

# Check certificate creation (takes a minute)
kubectl get certificates
kubectl get secret sresource-tls
```

## Step 8: Set Up CI/CD Pipeline

The GitHub Actions workflow automatically builds and pushes Docker images:

1. Workflow file location: `.github/workflows/build-and-push.yml`
2. Triggered on:
   - Push to `main` branch
   - Push to `develop` branch
   - Push of tags (v*.*.*)
   - Pull requests to `main`

3. What it does:
   - Builds multi-stage Docker image
   - Scans for vulnerabilities (Trivy)
   - Pushes to Docker Hub (if secrets configured)
   - Caches layers for speed

4. View builds:
   - Go to [https://github.com/atamsekar-tivo/SRESource/actions](https://github.com/atamsekar-tivo/SRESource/actions)

## Step 9: Update Documentation (Optional)

To add or edit content:

```bash
cd /Users/anirudh.tamsekar/SRESource

# Edit docs
vim docs/kubernetes-debugging-commands.md

# Or add new guide
cp docs/template.md docs/my-new-guide.md

# Update mkdocs.yml navigation if adding new file
vim mkdocs.yml

# Test locally
docker-compose up
# Visit http://localhost:8080

# Commit and push
git add .
git commit -m "docs: add new debugging guide"
git push origin main

# Docker image automatically builds and pushes
```

## Troubleshooting

### Docker build fails
```bash
# Check Docker daemon
docker ps

# Clear build cache
docker system prune -a

# Rebuild
docker build --no-cache -t sresource:local .
```

### Kubernetes deployment not starting
```bash
# Check events
kubectl describe pod <pod-name>

# Check logs
kubectl logs <pod-name>

# Check resource availability
kubectl top nodes
kubectl top pods
```

### Cannot push to GitHub
```bash
# Verify SSH key or HTTPS credentials
git remote -v
git config user.email "your@email.com"
git config user.name "Your Name"

# Test connection
ssh -T git@github.com  # For SSH
# or
curl -I https://github.com  # For HTTPS
```

### Docker Hub push fails in GitHub Actions
```bash
# Verify secrets are set correctly
# Go to Settings → Secrets → Review DOCKER_USERNAME and DOCKER_PASSWORD
# Check Docker Hub token hasn't expired
# Verify docker.io is reachable
```

## Project Statistics

| Metric | Value |
|--------|-------|
| Documentation Files | 9 |
| Total Lines | ~30,000 |
| Debugging Scenarios | 60+ |
| Production Commands | 400+ |
| Kubernetes Manifests | 4 |
| Helm Templates | 5 |
| Docker Image Size | ~120MB |
| Container Memory (req) | 128Mi |
| Container Memory (limit) | 256Mi |

## Next Steps

1. **Push to GitHub** - Follow Step 2
2. **Set up Docker secrets** - Follow Step 3 (optional)
3. **Test locally** - Follow Step 4 or 5
4. **Deploy to Kubernetes** - Follow Step 6
5. **Share with team** - GitHub URL or deployed link
6. **Monitor CI/CD** - Watch automated builds in Actions

## Project Structure Verification

```bash
tree -L 2 /Users/anirudh.tamsekar/SRESource/
```

Expected output:
```
SRESource/
├── .github/workflows/    # CI/CD pipelines
│   └── build-and-push.yml
├── .gitignore
├── Dockerfile            # Multi-stage build
├── LICENSE               # CC-BY-SA 4.0
├── README.md
├── docker-compose.yml    # Local dev
├── docs/                 # All markdown
│   ├── index.md
│   ├── kubernetes-debugging-commands.md
│   ├── production-debugging-unix-linux.md
│   ├── production-networking-debugging.md
│   ├── production-debugging-ci-cd-tools.md
│   ├── production-debugging-iam.md
│   ├── production-debugging-eks.md
│   ├── production-debugging-databases.md
│   └── TOOLS_GUIDE.md
├── helm/                 # Helm chart
│   └── sresource/
│       ├── Chart.yaml
│       ├── values.yaml
│       └── templates/
├── kubernetes/           # K8s manifests
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   └── kustomization.yaml
└── mkdocs.yml            # Documentation config
```

## Support

- **Issues**: [Create GitHub Issue](https://github.com/atamsekar-tivo/SRESource/issues)
- **Documentation**: See README.md
- **Local Testing**: docker-compose.yml

---

**Ready to deploy!** Start with Step 2 to push to GitHub.
