# SRESource - GitHub Deployment Steps

## STEP 1: Create GitHub Repository

Go to **https://github.com/new** and fill in:

```
Repository name: SRESource
Description: Comprehensive production debugging guide for SRE/DevOps/Platform Engineers
Public/Private: Public
Initialize repository: NO (unchecked - we have files)
Add .gitignore: NO
Add license: NO (we have CC-BY-SA 4.0)
```

Click **"Create repository"**

---

## STEP 2: Push Code to GitHub

Run these commands in terminal:

```bash
cd /Users/anirudh.tamsekar/SRESource

# Add GitHub as remote
git remote add origin https://github.com/atamsekar-tivo/SRESource.git

# Ensure on main branch
git branch -M main

# Push all commits
git push -u origin main

# Verify
git remote -v
```

Expected output:
```
origin  https://github.com/atamsekar-tivo/SRESource.git (fetch)
origin  https://github.com/atamsekar-tivo/SRESource.git (push)
```

---

## STEP 3: Configure GitHub Secrets (Optional - For Automated Docker Builds)

### If you want automated Docker Hub pushes:

1. Go to: `https://github.com/atamsekar-tivo/SRESource/settings/secrets/actions`
2. Click "New repository secret"
3. Add secret `DOCKER_USERNAME`:
   - Value: Your Docker Hub username
4. Click "Add secret"
5. Click "New repository secret" again
6. Add secret `DOCKER_PASSWORD`:
   - Value: Your Docker Hub token/password
7. Click "Add secret"

### To get Docker Hub credentials:

If you don't have Docker Hub:
- Sign up: https://hub.docker.com/signup
- Log in: https://hub.docker.com/login

If you have Docker Hub:
- Go to: https://hub.docker.com/settings/security
- Create new "Personal Access Token"
- Use this token as DOCKER_PASSWORD

### Without secrets: CI/CD will still test build (just won't push to Docker Hub)

---

## STEP 4: Test Everything Works

### Test Local Build:

```bash
cd /Users/anirudh.tamsekar/SRESource

# Build image
docker build -t sresource:test .

# Run
docker run -p 8080:8080 sresource:test

# Visit http://localhost:8080 in browser
# Press Ctrl+C to stop
```

### Test with Docker Compose:

```bash
cd /Users/anirudh.tamsekar/SRESource

# Start
docker-compose up -d

# View logs
docker-compose logs -f

# Visit http://localhost:8080

# Stop
docker-compose down
```

---

## STEP 5: Share with Your Team

Your SRESource is now:

- ✅ On GitHub: `https://github.com/atamsekar-tivo/SRESource`
- ✅ Publicly accessible
- ✅ Automatically building with CI/CD
- ✅ Ready to deploy anywhere

Share these URLs:
- **GitHub Repo**: https://github.com/atamsekar-tivo/SRESource
- **Local Test**: http://localhost:8080 (after docker-compose up)
- **Documentation**: See README.md in the repo

---

## VERIFICATION CHECKLIST

After following steps above, verify:

```bash
# ✅ Repository pushed
git remote -v
# Should show: origin https://github.com/atamsekar-tivo/SRESource.git

# ✅ All commits visible
git log --oneline | head
# Should show 3+ commits starting with initial commit

# ✅ Files on GitHub
# Check: https://github.com/atamsekar-tivo/SRESource
# Should see all 30 files

# ✅ GitHub Actions running (if secrets configured)
# Check: https://github.com/atamsekar-tivo/SRESource/actions
# Should see workflow execution

# ✅ Local Docker build works
docker build -t test . 2>&1 | tail
# Should show: Successfully tagged test:latest

# ✅ Docker Compose works
docker-compose up -d && sleep 5 && docker ps
# Should show sresource container running
docker-compose down
```

---

## TROUBLESHOOTING

### Issue: "fatal: remote origin already exists"
```bash
git remote remove origin
git remote add origin https://github.com/atamsekar-tivo/SRESource.git
```

### Issue: "Permission denied (publickey)"
Use HTTPS instead of SSH:
```bash
git remote set-url origin https://github.com/atamsekar-tivo/SRESource.git
```

### Issue: "fatal: not a git repository"
Ensure you're in correct directory:
```bash
cd /Users/anirudh.tamsekar/SRESource
git status
```

### Issue: Docker build fails
```bash
# Clear cache
docker system prune -a

# Rebuild
docker build --no-cache -t sresource:local .
```

### Issue: Port 8080 already in use
```bash
# Use different port
docker run -p 9090:8080 sresource:local
# Visit http://localhost:9090
```

---

## NEXT STEPS (AFTER GITHUB)

### 1. Deploy to Kubernetes
```bash
# Using kubectl
kubectl apply -f kubernetes/

# Or using Helm
helm install sresource ./helm/sresource

# Port forward
kubectl port-forward svc/sresource 8080:80
# Visit http://localhost:8080
```

### 2. Configure Custom Domain
Edit `kubernetes/ingress.yaml` or Helm values:
```yaml
ingress:
  hosts:
    - host: sresource.example.com  # Change this
      paths:
        - path: /
```

### 3. Add More Documentation
```bash
# Edit existing guide
vim docs/kubernetes-debugging-commands.md

# Add new guide
cp docs/TOOLS_GUIDE.md docs/my-new-guide.md

# Update navigation
vim mkdocs.yml

# Commit and push
git add docs/ mkdocs.yml
git commit -m "docs: add new guide"
git push origin main
```

### 4. Monitor CI/CD Pipeline
Visit: `https://github.com/atamsekar-tivo/SRESource/actions`

Watch Docker builds automatically:
- ✅ Build Docker image
- ✅ Scan for vulnerabilities
- ✅ Push to Docker Hub (if secrets configured)

---

## COMMANDS SUMMARY

### One-time setup:
```bash
cd /Users/anirudh.tamsekar/SRESource
git remote add origin https://github.com/atamsekar-tivo/SRESource.git
git branch -M main
git push -u origin main
```

### Daily operations:
```bash
# Make changes
vim docs/kubernetes-debugging-commands.md

# Commit
git add .
git commit -m "docs: update kubernetes guide"

# Push (auto builds Docker image)
git push origin main
```

### Deployment:
```bash
# Local testing
docker-compose up -d
docker-compose down

# Kubernetes
kubectl apply -f kubernetes/

# Helm
helm install sresource ./helm/sresource
```

---

## SUPPORT

**Documentation**:
- README.md - Overview
- SETUP_GUIDE.md - Deployment details
- QUICK_REFERENCE.md - Common commands

**Links**:
- GitHub: https://github.com/atamsekar-tivo/SRESource
- MkDocs: https://www.mkdocs.org/
- Docker: https://docs.docker.com/
- Kubernetes: https://kubernetes.io/docs/

---

**Ready? Let's go!** Start with STEP 1 above.
