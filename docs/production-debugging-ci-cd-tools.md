# Production Debugging Commands for CI/CD Tools

> **Critical Context**: CI/CD debugging often reveals secrets, credentials, and sensitive build artifacts. Always audit logs before sharing. Use read-only mode initially. Never modify pipelines during active builds. Document all changes with audit trail.

---

## Jenkins Production Debugging

### Scenario: Diagnosing Jenkins Build Failures and Agent Issues

**Prerequisites**: Builds failing, jobs not running, agents unreachable  
**Common Causes**: Agent connection lost, workspace full, executor limit hit, plugin conflict

#### Getting Jenkins System Status

```bash
# STEP 1: Check Jenkins service status
systemctl status jenkins
sudo systemctl restart jenkins  # If needed

# STEP 2: Access Jenkins logs
tail -f /var/log/jenkins/jenkins.log
# For Docker: docker logs -f jenkins-container

# STEP 3: Monitor Jenkins JVM memory
jcmd $(pgrep -f jenkins.jar) GC.heap_info
# Shows: Heap usage and configuration

# STEP 4: Check Jenkins disk space
du -sh /var/lib/jenkins
du -sh /var/lib/jenkins/jobs
du -sh /var/lib/jenkins/workspace

# STEP 5: Verify agent connectivity
# Via Jenkins UI: Manage Jenkins > Manage Nodes
# Via CLI:
java -jar jenkins-cli.jar -s http://localhost:8080 list-nodes
java -jar jenkins-cli.jar -s http://localhost:8080 online-nodes

# STEP 6: Check executor availability
curl -s http://localhost:8080/api/json | jq '.busyExecutors, .totalExecutors'
# Shows: Active jobs / total executors

# STEP 7: Check for stuck builds
curl -s http://localhost:8080/api/json | jq '.jobs[] | select(.lastBuild | .result == null)'
# Shows: Running/stuck jobs (null result)

# STEP 8: Monitor build queue
curl -s http://localhost:8080/queue/api/json | jq '.items[] | {name, why}'
# Shows: Queued jobs and reason for queue

# STEP 9: Check plugin load errors
curl -s http://localhost:8080/api/json | jq '.plugins[] | select(.active == false)'
# Shows: Inactive/broken plugins

# STEP 10: Verify Jenkins connectivity to SCM
# Via UI: Configure System > Source Code Management test
# Via CLI: test git/svn connectivity from Jenkins user

# STEP 11: Check webhook delivery status
# GitHub/GitLab: Check webhook delivery logs in platform UI
# Jenkins: Monitor: Manage Jenkins > System Log

# STEP 12: Monitor Jenkins thread count
ps -eLf | grep jenkins | wc -l
# Compare with: ps aux | grep jenkins | wc -l (main process count)
```

#### Jenkins Build and Job Diagnostics

```bash
# Get specific job build history
curl -s http://localhost:8080/job/<job-name>/api/json | jq '.builds[] | {number, result, duration}'

# Get last failed build logs
curl -s http://localhost:8080/job/<job-name>/<build-number>/consoleText | tail -100

# Check job configuration
curl -s http://localhost:8080/job/<job-name>/config.xml | head -50

# Monitor build resource usage
# Inside build: measure via: top -b -n 1, df -h, free -h

# Check if build aborted due to timeout
grep -i "timeout\|kill\|abort" /var/lib/jenkins/jobs/<job>/builds/<build>/log

# Verify build artifact storage
du -sh /var/lib/jenkins/jobs/<job>/builds/<build>/archive

# Check build workspace cleanliness
ls -la /var/lib/jenkins/workspace/<job>/
# Look for: Stale files, permission issues
```

#### Jenkins Master and Agent Connection Recovery

```bash
# Restart agent gracefully
# Via Jenkins UI: Node > Mark offline > Disconnect > Reconnect

# Via CLI:
java -jar jenkins-cli.jar -s http://localhost:8080 \
  offline-node <agent-name> -m "Manual restart"
java -jar jenkins-cli.jar -s http://localhost:8080 \
  online-node <agent-name>

# Test agent connection
# On agent:
java -jar agent.jar -jnlpUrl http://<jenkins-master>:8080/computer/<agent>/slave-agent.jnlp

# Check agent logs
tail -f /var/log/jenkins-agent/agent.log  # Or wherever running

# Clear agent workspace if corrupted
rm -rf /var/lib/jenkins/workspace/<job-name>
# Agent will recreate on next build

# Verify agent JVM parameters
ps aux | grep "java.*agent.jar" | grep -v grep
# Check: Xmx (max memory), port bindings
```

#### Jenkins Configuration and Plugin Management

```bash
# List installed plugins and versions
curl -s http://localhost:8080/pluginManager/api/json | jq '.plugins[] | {name, version, active}'

# Check for plugin dependency issues
# Jenkins UI: Manage Jenkins > Plugin Manager > Updates

# Backup Jenkins configuration
tar -czf jenkins-backup-$(date +%Y%m%d).tar.gz /var/lib/jenkins/

# Reload Jenkins configuration from disk
curl -X POST http://localhost:8080/reload

# Check Jenkins system properties
curl -s http://localhost:8080/api/json | jq '.systemProperties'

# Monitor Jenkins performance metrics
curl -s http://localhost:8080/metrics/key-metrics/ | jq .
# Requires Metrics plugin

# Get Jenkins version
curl -s http://localhost:8080/api/json | jq '.version'
```

#### Commands to NEVER use in production

```bash
# ❌ NEVER: pkill -9 java (kill Jenkins forcefully)
#    Use: systemctl stop jenkins
# ❌ NEVER: rm -rf /var/lib/jenkins/jobs (delete all jobs)
#    No recovery possible; loss of CI/CD infrastructure
# ❌ NEVER: Modify Jenkins XML configs while daemon running
#    Corruption; use Jenkins UI or reload after changes
# ❌ NEVER: Scale down agents while builds running
#    Aborts active jobs; incomplete artifacts
```

---

## GitHub Actions Production Debugging

### Scenario: Diagnosing GitHub Actions Workflow Failures

**Prerequisites**: Workflows not triggering, jobs timing out, runners unreachable  
**Common Causes**: Trigger condition mismatch, self-hosted runner down, secrets misconfigured, API rate limiting

#### GitHub Actions Workflow Status and Logs

```bash
# STEP 1: Check workflow runs via GitHub API
curl -H "Authorization: token <GITHUB_TOKEN>" \
  https://api.github.com/repos/<owner>/<repo>/actions/runs \
  | jq '.workflow_runs[] | {name, status, conclusion, created_at}'

# STEP 2: Get detailed run information
curl -H "Authorization: token <GITHUB_TOKEN>" \
  https://api.github.com/repos/<owner>/<repo>/actions/runs/<run_id> \
  | jq '.'

# STEP 3: List workflow files in repository
curl -H "Authorization: token <GITHUB_TOKEN>" \
  https://api.github.com/repos/<owner>/<repo>/actions/workflows \
  | jq '.workflows[] | {name, path, state}'

# STEP 4: Check if workflow is disabled
# Via UI: Actions > select workflow > check if enabled
# Via API: state field should be "active"

# STEP 5: Verify trigger events are correct
# Check .github/workflows/<workflow>.yml:
cat .github/workflows/<workflow>.yml | grep -A 5 "^on:"

# STEP 6: Check for branch protection rule blocking
# UI: Settings > Branches > check required status checks
# May prevent merge if workflow required but failing

# STEP 7: Monitor job execution logs
# Via UI: Actions > select run > select job > see logs
# Via API: get job logs from run details

# STEP 8: Check for secrets in logs (security concern)
# Search logs: grep -i "secret\|password\|token" <log-file>
# If found, rotate credentials immediately

# STEP 9: Verify runner availability
# Via UI: Settings > Actions > Runners
# Shows: Online/offline status, assigned jobs

# STEP 10: Check webhook delivery status
# UI: Settings > Webhooks > Recent Deliveries
# Shows: Trigger events and delivery status

# STEP 11: Monitor action usage
curl -H "Authorization: token <GITHUB_TOKEN>" \
  https://api.github.com/repos/<owner>/<repo>/actions/cache/usage \
  | jq '.'
# Shows: Cache size and limits

# STEP 12: Check for rate limiting
curl -H "Authorization: token <GITHUB_TOKEN>" \
  https://api.github.com/rate_limit | jq '.rate_limit'
```

#### GitHub Actions Self-Hosted Runner Diagnostics

```bash
# STEP 1: Check runner status
# Runner machine: ps aux | grep -E "runner.*.sh|Runner.Listener"
# Shows: Runner process running

# STEP 2: Monitor runner logs
# Location: ~/actions-runner/_diag/
ls -la ~/actions-runner/_diag/ | tail -10
tail -f ~/actions-runner/_diag/Runner_*.log

# STEP 3: Test runner connectivity to GitHub
# On runner:
curl -I https://api.github.com
# Should return 200

# STEP 4: Verify runner registration token not expired
# Token expires after 1 hour if registration incomplete
# UI: Settings > Actions > Runners > Add runner (get new token)

# STEP 5: Check runner labels match workflow requirements
# Workflow: runs-on: [self-hosted, linux, x64]
# Runner registration: must include matching labels

# STEP 6: Monitor runner disk space
df -h /home/runner  # Or wherever runner is installed
# Builds may fail if < 5GB free

# STEP 7: Monitor runner memory during builds
# While build running: free -h && ps aux | grep -i java/docker

# STEP 8: Check runner network connectivity
# Test GitHub: timeout 5 curl https://github.com
# Test artifact server: timeout 5 curl https://<artifact-server>

# STEP 9: Verify runner can execute actions
# Check Docker installation (if Docker actions used):
docker ps  # Must work without sudo
# Check Python/Node (if scripted actions):
python3 --version && node --version

# STEP 10: Test concurrent job capacity
# Runner config: concurrent value in .runner config
# Check: watch -n 1 'ps aux | grep -c runner'

# STEP 11: Monitor system load during jobs
# While build: uptime && top -b -n 1 | head -5

# STEP 12: Check runner configuration file
cat ~/actions-runner/.runner

# Location usually:
# Linux: /home/<user>/actions-runner/
# macOS: /Users/<user>/actions-runner/
# Windows: C:\actions-runner\
```

#### GitHub Actions Secrets and Credentials Management

```bash
# STEP 1: Verify secrets are defined at correct level
# Repository secrets: Settings > Secrets
# Organization secrets: Settings > Secrets (org level)
# Environment secrets: Settings > Environments > select > Secrets

# STEP 2: Check secret usage in workflows
grep -r "secrets\." .github/workflows/
# Shows: Which secrets referenced in workflows

# STEP 3: Verify masked secrets in logs
# GitHub automatically masks known secrets
# Check logs for: *** (indicates masked value)

# STEP 4: Monitor secret rotation
# Regularly rotate: Settings > Secrets > Update

# STEP 5: Test secret availability in job context
# Add to workflow: run: echo "Test: ${{ secrets.MY_SECRET }}"
# Should output: Test: ***

# STEP 6: Check for hardcoded secrets
grep -r "password\|token\|secret" .github/workflows/ | grep -v "secrets\."
# May indicate leaked credential

# STEP 7: Verify environment-specific secrets
# For prod: use Environment protection rules
# UI: Settings > Environments > select > Deployment protection rules
```

#### GitHub Actions API Rate Limiting and Performance

```bash
# Check API rate limits
curl -H "Authorization: token <GITHUB_TOKEN>" \
  https://api.github.com/rate_limit | jq '.resources'
# Shows: Remaining requests and reset time

# Monitor workflow runs in bulk
curl -H "Authorization: token <GITHUB_TOKEN>" \
  "https://api.github.com/repos/<owner>/<repo>/actions/runs?status=queued" \
  | jq '.total_count'
# Shows: Number of queued runs

# Get performance metrics per workflow
curl -H "Authorization: token <GITHUB_TOKEN>" \
  https://api.github.com/repos/<owner>/<repo>/actions/runs \
  | jq '.workflow_runs[] | {name, run_number, duration_ms: (.updated_at - .created_at)}'

# Check action caching efficiency
curl -H "Authorization: token <GITHUB_TOKEN>" \
  https://api.github.com/repos/<owner>/<repo>/actions/cache \
  | jq '.actions_caches[] | {key, size_in_bytes, created_at}'
```

#### Commands to NEVER use in production

```bash
# ❌ NEVER: curl -X DELETE to remove all action runs
#    Loss of build history; audit trail destroyed
# ❌ NEVER: Commit GitHub token to repository
#    Exposes credentials; anyone can impersonate workflow
# ❌ NEVER: Disable branch protection while fixing workflow
#    Allows untested code to merge
# ❌ NEVER: Scale down runners without stopping active jobs
#    Aborts builds; incomplete deployments
```

---

## ArgoCD Production Debugging

### Scenario: Diagnosing ArgoCD Application Sync Failures

**Prerequisites**: Applications out of sync, deployments not updating, GitOps not working  
**Common Causes**: Git repository unreachable, credentials invalid, Kubernetes cluster disconnected, hook failure

#### ArgoCD Application and Sync Status

```bash
# STEP 1: Check ArgoCD server status
kubectl get pods -n argocd
# Should show: argocd-server, argocd-repo-server, argocd-application-controller, argocd-dex-server

# STEP 2: Get all applications and sync status
argocd app list
kubectl get application -n argocd -o wide

# STEP 3: Get detailed application status
argocd app get <app-name>
kubectl describe application <app-name> -n argocd

# STEP 4: Check application sync policy
argocd app get <app-name> | grep -A 5 "syncPolicy"
# Shows: Auto-sync enabled, prune, self-heal settings

# STEP 5: Monitor application resources
argocd app resources <app-name>
kubectl get all -n <app-namespace> -l app.kubernetes.io/instance=<app-name>

# STEP 6: Check Git repository connectivity
argocd repo list
kubectl get repo -n argocd

# STEP 7: Test specific repository
argocd repo get https://<git-repo>
# Should show: Connection successful

# STEP 8: Check application manifest generation
argocd app manifests <app-name> --local
# Shows: Generated manifests from Git repository

# STEP 9: Monitor ArgoCD application controller logs
kubectl logs -n argocd deployment/argocd-application-controller -f --all-containers
# Look for: sync errors, reconciliation failures

# STEP 10: Check ArgoCD repo server logs
kubectl logs -n argocd deployment/argocd-repo-server -f --all-containers
# Look for: Git fetch errors, manifest rendering issues

# STEP 11: Monitor ArgoCD API server
kubectl logs -n argocd deployment/argocd-server -f --all-containers
# Look for: Authentication errors, API issues

# STEP 12: Check resource quotas and limits
kubectl describe namespace <app-namespace>
# May show: Limits preventing application deployment
```

#### ArgoCD Git Repository and Sync Issues

```bash
# STEP 1: Verify Git credentials
argocd repo list | grep <repo-url>
# Check: Status field (should show "Successful")

# STEP 2: Test Git SSH key connectivity
# Add SSH key to ArgoCD:
argocd repo add git@github.com:<owner>/<repo>.git --ssh-client-cert-file <cert-path>
# Or via UI: Settings > Repositories > Connect

# STEP 3: Check commit hash in application
argocd app get <app-name> | grep "Revision"
# Shows: Current synced commit

# STEP 4: Compare with latest Git commit
argocd app get <app-name> --refresh hard
# Forces Git fetch to get latest

# STEP 5: Check for sync errors
kubectl get application <app-name> -n argocd -o jsonpath='{.status.conditions}'
# Shows: Error conditions if sync failed

# STEP 6: View application events
kubectl describe application <app-name> -n argocd | grep -A 20 "Events:"
# Shows: Recent application state changes

# STEP 7: Manually trigger sync
argocd app sync <app-name>
# Initiates immediate synchronization

# STEP 8: Dry-run application to see changes
argocd app diff <app-name> --local
# Shows: What would be applied without actually applying

# STEP 9: Check Git branch for app
kubectl get application <app-name> -n argocd -o jsonpath='{.spec.source.targetRevision}'
# Shows: Configured branch (e.g., "main", "master", tag)

# STEP 10: Verify Kustomize/Helm configuration
# For Kustomize: check kustomization.yaml in Git
# For Helm: check helm values in ArgoCD application
kubectl get application <app-name> -n argocd -o yaml | grep -A 10 "source:"

# STEP 11: Monitor application resource drift
argocd app wait <app-name> --sync
# Waits for application to reach desired state

# STEP 12: Check application health status
kubectl get application <app-name> -n argocd -o jsonpath='{.status.health.status}'
# Shows: Healthy, Degraded, Unknown, Progressing
```

#### ArgoCD Server and Controller Management

```bash
# STEP 1: Check ArgoCD RBAC configuration
kubectl get clusterrole,clusterrolebinding -n argocd
# Shows: ArgoCD service account permissions

# STEP 2: Verify ArgoCD can access target clusters
argocd cluster list
# Should show: Clusters and their connection status

# STEP 3: Test cluster authentication
argocd cluster info <cluster-name>
# Verifies: ArgoCD can connect to cluster

# STEP 4: Check ArgoCD memory usage
kubectl top pod -n argocd
# Monitor: repo-server and application-controller memory

# STEP 5: Monitor ArgoCD notification system
kubectl get secret argocd-notifications-cm -n argocd -o yaml
# Shows: Notification configuration (email, Slack, etc.)

# STEP 6: Check notification delivery
argocd app get <app-name> | grep -i "notification\|webhook"
# May show notification status

# STEP 7: Verify ArgoCD TLS certificate
# For Kubernetes secret:
kubectl get secret argocd-server-tls -n argocd -o yaml
# Check: cert validity period

# STEP 8: Check ArgoCD UI accessibility
kubectl get svc -n argocd | grep argocd-server
# Get: Service IP/port for access

# STEP 9: Monitor ArgoCD performance metrics
# If Prometheus enabled:
kubectl port-forward -n argocd svc/argocd-metrics 8082:8082
curl -s http://localhost:8082/metrics | grep argocd

# STEP 10: Check ArgoCD admin password status
argocd account list
# Shows: Configured user accounts

# STEP 11: Verify webhook secret configuration
kubectl get secret -n argocd | grep webhook
# Used for GitHub/GitLab webhook verification

# STEP 12: Monitor ArgoCD SSO configuration
kubectl get secret argocd-secret -n argocd -o yaml
# Contains: OIDC, LDAP configuration
```

#### ArgoCD Helm and Kustomize Rendering

```bash
# STEP 1: Test Helm rendering locally
helm template <release-name> <chart-path> -f <values.yaml>
# Shows: Generated manifests

# STEP 2: Verify Helm repositories in ArgoCD
argocd repo list | grep helm
# Should list: Helm repository URLs

# STEP 3: Test Helm chart fetch
argocd repo get <helm-repo-url>
# Verifies: Can access Helm repository

# STEP 4: Check Kustomize build
kustomize build .
# Shows: Generated manifests from Kustomize

# STEP 5: Verify values file resolution
kubectl get application <app-name> -n argocd -o yaml | grep -A 5 "helm:"
# Shows: Chart, version, values configured

# STEP 6: Test Helm values overrides
helm template <chart> --values <override.yaml>
# Validates: Override values work as expected

# STEP 7: Check for circular Kustomize bases
# In Git: ensure bases don't reference each other
cat kustomization.yaml | grep "bases:"

# STEP 8: Verify Helm plugin installation
argocd app get <app-name> --show-operation
# Shows: Which rendering tool and parameters used

# STEP 9: Monitor slow rendering (repo-server logs)
kubectl logs -n argocd deployment/argocd-repo-server | grep -i "render\|timeout"
# May indicate: Complex chart or large manifests

# STEP 10: Test manifest size limits
# ArgoCD limit ~100MB manifests
wc -l /tmp/generated-manifests.yaml
# If > 1M lines, may exceed limits
```

#### ArgoCD Continuous Deployment Workflow

```bash
# Retrieve environment variables from secret
kubectl get secret argocd-secret -n argocd -o jsonpath='{.data}'

# Example: Extract Git credentials
kubectl get secret argocd-secret -n argocd \
  -o jsonpath='{.data.github_key}' | base64 -d

# Export ArgoCD CLI token
argocd login <argocd-server> --username admin --password <password>
export ARGOCD_OPTS='--grpc-web'

# View current ArgoCD configuration
cat ~/.argocd/config
# Contains: Server, auth token (SENSITIVE!)
```

#### Commands to NEVER use in production

```bash
# ❌ NEVER: argocd app delete <app-name> --cascade without confirmation
#    Deletes all associated Kubernetes resources
# ❌ NEVER: kubectl delete all -n argocd
#    Destroys ArgoCD completely; recovery difficult
# ❌ NEVER: Modify ArgoCD YAML directly while controller running
#    May cause reconciliation conflicts
# ❌ NEVER: Force push to Git branch while ArgoCD syncing
#    May cause out-of-sync state or rollback
```

---

## GitLab CI/CD Production Debugging

### Scenario: Diagnosing GitLab CI Pipeline Failures

**Prerequisites**: Pipelines not triggering, jobs failing, runners not picking up jobs  
**Common Causes**: `.gitlab-ci.yml` syntax error, runner offline, artifacts storage full, API token expired

#### GitLab CI Pipeline Status and Logs

```bash
# STEP 1: Check CI/CD pipeline status
# Via API:
curl -H "PRIVATE-TOKEN: <token>" \
  https://gitlab.example.com/api/v4/projects/<project-id>/pipelines \
  | jq '.[0] | {id, status, created_at}'

# STEP 2: Get detailed pipeline information
curl -H "PRIVATE-TOKEN: <token>" \
  https://gitlab.example.com/api/v4/projects/<project-id>/pipelines/<pipeline-id> \
  | jq '.'

# STEP 3: Check job status and logs
curl -H "PRIVATE-TOKEN: <token>" \
  https://gitlab.example.com/api/v4/projects/<project-id>/pipelines/<pipeline-id>/jobs \
  | jq '.[] | {id, name, status, stage}'

# STEP 4: Get job logs
curl -H "PRIVATE-TOKEN: <token>" \
  https://gitlab.example.com/api/v4/projects/<project-id>/jobs/<job-id>/log

# STEP 5: Validate `.gitlab-ci.yml` syntax
# Via API:
curl -X POST -H "PRIVATE-TOKEN: <token>" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "dry_run=true&content=<file-content>" \
  https://gitlab.example.com/api/v4/projects/<project-id>/ci/lint

# STEP 6: Check GitLab CI configuration
cat .gitlab-ci.yml
# Look for: stages, jobs, only/except, variables

# STEP 7: Verify pipeline trigger settings
# Via API: Webhook delivery
curl -H "PRIVATE-TOKEN: <token>" \
  https://gitlab.example.com/api/v4/projects/<project-id>/hooks

# STEP 8: Monitor CI/CD variables
# Via API:
curl -H "PRIVATE-TOKEN: <token>" \
  https://gitlab.example.com/api/v4/projects/<project-id>/variables

# STEP 9: Check pipeline schedules (for scheduled jobs)
curl -H "PRIVATE-TOKEN: <token>" \
  https://gitlab.example.com/api/v4/projects/<project-id>/pipeline_schedules

# STEP 10: Monitor protected branch pipeline restrictions
# Via API: branch protection rules

# STEP 11: Check runner group assignment
curl -H "PRIVATE-TOKEN: <token>" \
  https://gitlab.example.com/api/v4/projects/<project-id>/runners

# STEP 12: Get artifact information
curl -H "PRIVATE-TOKEN: <token>" \
  https://gitlab.example.com/api/v4/projects/<project-id>/pipelines/<pipeline-id>/artifacts
```

#### GitLab Runner Management

```bash
# STEP 1: Check runner status
# Via UI: Admin > Runners (if admin access)
# Via API:
curl -H "PRIVATE-TOKEN: <admin-token>" \
  https://gitlab.example.com/api/v4/runners

# STEP 2: Check runner health
# On runner machine:
gitlab-runner verify
# Shows: Configuration and connectivity status

# STEP 3: Monitor runner processes
ps aux | grep gitlab-runner
# Should show: Main process and job processes

# STEP 4: Check runner logs
tail -f /var/log/gitlab-runner/system.log
# For systemd: journalctl -u gitlab-runner -f

# STEP 5: Test runner connectivity to GitLab
# On runner:
curl -I https://gitlab.example.com
# Should return 200

# STEP 6: Verify runner can execute jobs
gitlab-runner --version
gitlab-runner verify --delete

# STEP 7: Check runner cache status
# Locate cache directory (in config.toml: cache_dir)
du -sh <cache-dir>
# If full, may prevent job execution

# STEP 8: Verify runner Docker/VM connectivity
# If Docker executor:
docker ps  # Should work
# If VM executor:
ps aux | grep qemu  # Check VM processes

# STEP 9: Monitor runner resource usage
top -p $(pgrep -f gitlab-runner)
# Watch: CPU, memory, threads during builds

# STEP 10: Check runner auto-scale setting
# In config.toml: [runners.machine]
# Check: max_builds, idle_count, idle_time

# STEP 11: Register new runner if needed
gitlab-runner register \
  --url https://gitlab.example.com/ \
  --registration-token <token> \
  --executor docker \
  --docker-image alpine:latest

# STEP 12: Update runner configuration
sudo nano /etc/gitlab-runner/config.toml
sudo gitlab-runner restart
```

#### Commands to NEVER use in production

```bash
# ❌ NEVER: gitlab-runner uninstall without backing up config.toml
#    Loses runner configuration permanently
# ❌ NEVER: Commit .gitlab-ci.yml with hardcoded credentials
#    Use CI/CD variables instead
# ❌ NEVER: Kill running jobs to free resources
#    Use: gitlab-runner stop to gracefully stop
# ❌ NEVER: Fill runner cache without cleanup
#    Prevents new builds; run: gitlab-runner cache-clear
```

---

## Spinnaker Production Debugging

### Scenario: Diagnosing Spinnaker Deployment Pipeline Failures

**Prerequisites**: Deployments not progressing, pipeline stages failing, integration with cloud provider broken  
**Common Causes**: Provider account misconfigured, deployment manifest invalid, gate timeout, insufficient permissions

#### Spinnaker Pipeline and Stage Monitoring

```bash
# STEP 1: Check Spinnaker microservices status
kubectl get pods -n spinnaker
# Should show: deck, gate, orca, clouddriver, front50, rosco

# STEP 2: Get pipeline execution status
# Via API:
curl -H "X-Auth-Token: <token>" \
  http://localhost:8084/applications/<app>/pipelines

# STEP 3: Get execution details
curl -H "X-Auth-Token: <token>" \
  http://localhost:8084/applications/<app>/executions/<execution-id>

# STEP 4: Check pipeline stage status
curl -H "X-Auth-Token: <token>" \
  http://localhost:8084/applications/<app>/executions/<execution-id> \
  | jq '.stages[] | {name, status, startTime}'

# STEP 5: Monitor Spinnaker logs
kubectl logs -n spinnaker deployment/orca -f  # Orchestration
kubectl logs -n spinnaker deployment/clouddriver -f  # Cloud integration
kubectl logs -n spinnaker deployment/rosco -f  # Artifact building (AMI, etc.)

# STEP 6: Check Spinnaker front end connectivity
curl -I http://localhost:9000
# Should return 200 (Deck UI)

# STEP 7: Verify cloud provider credentials
# For AWS:
kubectl get secret -n spinnaker | grep aws
# For GCP:
kubectl get secret -n spinnaker | grep gcp

# STEP 8: Check application configuration
kubectl get application <app> -n spinnaker
# Shows: Pipeline configuration and current executions

# STEP 9: Monitor Spinnaker thread usage
kubectl exec -it deployment/orca -n spinnaker -- \
  curl -s http://localhost:8083/health | jq '.details'

# STEP 10: Check for deployment manifest issues
# Validate manifest in UI or via:
curl -X POST http://localhost:8084/generic/validateManifest \
  -H "Content-Type: application/json" \
  -d '@manifest.json'

# STEP 11: Verify canary analysis configuration (if using)
# Check: canary stage settings, baseline, canary configurations

# STEP 12: Monitor Spinnaker object storage (front50)
kubectl logs -n spinnaker deployment/front50 | grep -i "storage\|s3"
```

#### Commands to NEVER use in production

```bash
# ❌ NEVER: kubectl delete all -n spinnaker
#    Destroys Spinnaker; all pipelines broken
# ❌ NEVER: Modify Spinnaker ConfigMap while orca running
#    May cause inconsistent state
# ❌ NEVER: Force delete executing pipeline
#    In-flight deployments may become orphaned
```

---

## Recommended Additional CI/CD Tools and Debugging

### GitOps and Deployment Tools

**Flux CD** - GitOps operator for continuous deployment
```bash
# Check Flux status
flux check

# Get flux resources
kubectl get all -n flux-system

# View Flux logs
flux logs --follow

# Reference: https://fluxcd.io/docs/guides/troubleshooting/
```

**Helm** - Package manager for Kubernetes
```bash
# Verify Helm chart syntax
helm lint <chart-path>

# Dry-run deployment
helm install --dry-run --debug <release> <chart>

# Reference: https://helm.sh/docs/
```

**Terraform** - Infrastructure as Code
```bash
# Validate Terraform syntax
terraform validate

# Plan changes (dry-run)
terraform plan -out=tfplan

# Check Terraform state
terraform state list

# Reference: https://www.terraform.io/docs/
```

### Test and Build Automation

**SonarQube** - Code quality and security scanning
```bash
# Check SonarQube server status
curl -s http://localhost:9000/api/system/status | jq '.status'

# Get project analysis results
curl -s http://localhost:9000/api/projects/search | jq '.components[]'

# Reference: https://docs.sonarqube.org/
```

**JFrog Artifactory** - Artifact management
```bash
# Check Artifactory health
curl -u<user>:<pass> -I http://artifactory:8081/artifactory

# List repositories
curl -u<user>:<pass> http://artifactory:8081/artifactory/api/repositories

# Reference: https://www.jfrog.com/confluence/display/JFROG/Artifactory
```

**Docker Registry** - Container image storage
```bash
# Check registry health
curl http://localhost:5000/v2/_catalog

# List images
curl http://localhost:5000/v2/_catalog | jq '.repositories'

# Reference: https://docs.docker.com/registry/
```

---

## Critical CI/CD Debugging Principles

### Investigation Methodology

```
1. Identify failing component (pipeline, job, stage)
   ↓
2. Check component status and health
   ↓
3. Review recent logs (last 50-100 lines)
   ↓
4. Trace through dependencies (Git, artifact store, runners)
   ↓
5. Verify credentials and permissions
   ↓
6. Test with minimal configuration (dry-run)
   ↓
7. Check resource availability (disk, memory, CPU)
   ↓
8. Document and implement fix
   ↓
9. Verify resolution with test run
   ↓
10. Update documentation/runbooks
```

### Common Failure Patterns

| Pattern | Cause | Solution |
|---------|-------|----------|
| Timeout in Git fetch | Network latency, large repo | Increase timeout, optimize clone |
| "No space left" error | Disk full | Clean workspace, artifacts |
| Runner offline | Network issue, crash | Restart runner, check logs |
| Artifact not found | Build failed, incorrect path | Check build logs, verify path |
| Credential error | Token expired, wrong secret | Rotate credentials, update secret |
| Manifest invalid | YAML/JSON syntax error | Validate with linter, show diff |
| Rate limit hit | Too many API calls | Implement backoff, cache results |

### Pre-Production Debugging Checklist

- [ ] All logs configured and accessible
- [ ] Metrics/monitoring in place
- [ ] Runbooks documented
- [ ] Credentials rotated recently
- [ ] Backups exist for critical data
- [ ] Resource limits verified
- [ ] Integration tests passing
- [ ] Rollback procedure tested
- [ ] On-call alerting configured
- [ ] Access controls verified

### Tools and Commands Quick Reference

```bash
# Jenkins
systemctl status jenkins
tail -f /var/log/jenkins/jenkins.log
curl -s http://localhost:8080/api/json | jq '.jobs'

# GitHub Actions
curl -H "Authorization: token $TOKEN" \
  https://api.github.com/repos/<owner>/<repo>/actions/runs

# ArgoCD
argocd app list
argocd app get <app-name>
kubectl logs -n argocd deployment/argocd-application-controller

# GitLab CI
curl -H "PRIVATE-TOKEN: $TOKEN" \
  https://gitlab.com/api/v4/projects/<id>/pipelines

# Spinnaker
curl -H "X-Auth-Token: $TOKEN" \
  http://localhost:8084/applications/<app>/pipelines
```

### Dangerous CI/CD Commands

```bash
# CRITICAL - NEVER in production:
rm -rf /var/lib/jenkins/jobs                  # Delete all jobs
kubectl delete all -n <ci-cd-system>          # Delete CI/CD system
Clear artifact storage without backup         # Loss of build artifacts
Force push to protected branch                # Bypass protections
Delete pipeline without snapshots             # Lose pipeline config
Kill running deployment jobs                  # Incomplete deployments
Remove credentials without rotation           # Service outage
```

### Documentation References

**Jenkins**
- Official Docs: https://www.jenkins.io/doc/
- Plugin Documentation: https://plugins.jenkins.io/
- Pipeline Guide: https://www.jenkins.io/doc/book/pipeline/

**GitHub Actions**
- Official Docs: https://docs.github.com/en/actions
- Troubleshooting: https://docs.github.com/en/actions/troubleshooting-workflow-runs
- API Reference: https://docs.github.com/en/rest/actions

**ArgoCD**
- Official Docs: https://argo-cd.readthedocs.io/
- Troubleshooting: https://argo-cd.readthedocs.io/en/stable/faq/
- Application Spec: https://argo-cd.readthedocs.io/en/stable/user-guide/application/

**GitLab CI/CD**
- Official Docs: https://docs.gitlab.com/ee/ci/
- Runner Guide: https://docs.gitlab.com/runner/
- YAML Reference: https://docs.gitlab.com/ee/ci/yaml/

**Spinnaker**
- Official Docs: https://spinnaker.io/docs/
- Troubleshooting: https://spinnaker.io/docs/troubleshooting/
- Architecture: https://spinnaker.io/docs/reference/architecture/

---

**Last Updated**: January 2026  
**CI/CD Platforms Covered**: Jenkins, GitHub Actions, ArgoCD, GitLab CI, Spinnaker, Flux, and more  
**Severity Level**: Production Critical  
**Review Frequency**: Monthly (tools update frequently)