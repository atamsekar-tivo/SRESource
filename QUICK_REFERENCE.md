# Quick Reference - Common Commands

## Local Development

```bash
# Start with Docker Compose
docker-compose up -d
docker-compose logs -f
docker-compose down

# Build image
docker build -t sresource:local .
docker run -p 8080:8080 sresource:local

# MkDocs (direct)
pip install mkdocs mkdocs-material
mkdocs serve
```

## Git Operations

```bash
# First time setup
cd /Users/anirudh.tamsekar/SRESource
git remote add origin https://github.com/atamsekar-tivo/SRESource.git
git branch -M main
git push -u origin main

# Daily operations
git status
git add .
git commit -m "your message"
git push origin main

# View logs
git log --oneline -10
```

## Kubernetes Deployment

```bash
# Using kubectl
kubectl apply -f kubernetes/
kubectl get deployments
kubectl get svc
kubectl port-forward svc/sresource 8080:80

# Using Helm
helm install sresource ./helm/sresource
helm upgrade sresource ./helm/sresource
helm uninstall sresource

# Using Kustomize
kubectl apply -k kubernetes/
kubectl delete -k kubernetes/

# Debugging
kubectl logs -f deployment/sresource
kubectl describe pod <pod-name>
kubectl exec -it <pod-name> -- sh
```

## Docker Hub

```bash
# Login
docker login

# Build and tag
docker build -t username/sresource:latest .
docker tag sresource:local username/sresource:v1.0.0

# Push
docker push username/sresource:latest
docker push username/sresource:v1.0.0

# Pull from registry
docker pull username/sresource:latest
```

## Content Updates

```bash
# Edit documentation
vim docs/kubernetes-debugging-commands.md

# Add new guide
cp docs/TOOLS_GUIDE.md docs/my-new-guide.md

# Update nav in mkdocs.yml
vim mkdocs.yml

# Commit changes
git add docs/ mkdocs.yml
git commit -m "docs: add new debugging guide"
git push origin main
```

## Monitoring

```bash
# Docker stats
docker stats

# Kubernetes resources
kubectl top nodes
kubectl top pods

# View container logs
docker logs <container-id>

# View pod logs (Kubernetes)
kubectl logs <pod-name>
kubectl logs <pod-name> -f  # Follow
kubectl logs <pod-name> --previous  # Previous (crashed) pod
```

---

Save this file as `QUICK_REFERENCE.md` in the project root for easy access.