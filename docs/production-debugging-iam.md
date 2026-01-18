# Production Debugging Commands for IAM and Access Control

> **Critical Context**: IAM misconfigurations can cause complete service outage or expose sensitive systems. Always use least-privilege principle. Test changes in staging first. Audit all IAM modifications. Never share credentials; use signed URLs or temporary tokens. Document all policy changes with business justification.

---

## Kubernetes RBAC Production Debugging

### Scenario: Diagnosing Kubernetes RBAC Permission Issues

**Prerequisites**: User/service account gets "forbidden" errors, cannot access resources  
**Common Causes**: Role/RoleBinding misconfigured, service account not bound, API group mismatch, namespace isolation

#### Kubernetes Authentication and Authorization Basics

```bash
# STEP 1: Check current authenticated user
kubectl auth whoami
# Shows: Current user, groups

# STEP 2: Verify user can perform specific action
kubectl auth can-i <verb> <resource> --as=<user>
# Examples:
kubectl auth can-i get pods --as=system:serviceaccount:default:mysa
kubectl auth can-i create deployments --as=<username>
kubectl auth can-i delete nodes --as=<username>

# STEP 3: Check all permissions for current user
kubectl auth can-i --list
# Shows: All permissions granted to current user

# STEP 4: Check all permissions for specific service account
kubectl auth can-i --list --as=system:serviceaccount:kube-system:default

# STEP 5: View current kubeconfig
cat ~/.kube/config | grep -A 5 "current-context\|users:"
# Shows: Current context and configured users

# STEP 6: Get current context and cluster info
kubectl config current-context
kubectl cluster-info
kubectl config view

# STEP 7: Check service account in pod
kubectl get sa -n <namespace>
# Shows: Service accounts in namespace

# STEP 8: Verify service account token is valid
kubectl get secret -n <namespace> | grep token
# Shows: Token secrets for service accounts

# STEP 9: Decode and inspect service account token
kubectl get secret <token-secret> -n <namespace> -o jsonpath='{.data.token}' | base64 -d | head -c 50
# WARNING: Contains sensitive data; don't share

# STEP 10: Check role assignments
kubectl get rolebindings -n <namespace>
kubectl get clusterrolebindings | head -20

# STEP 11: Get service account impersonation status
# Check if user/service account can impersonate others
kubectl auth can-i impersonate serviceaccounts --as=<user>

# STEP 12: Verify pod has mounted service account token
kubectl exec -it <pod> -n <namespace> -- ls -la /run/secrets/kubernetes.io/serviceaccount/
# Should show: ca.crt, namespace, token files
```

#### Kubernetes Role and RoleBinding Debugging

```bash
# STEP 1: List all roles in namespace
kubectl get roles -n <namespace>
kubectl get clusterroles | grep -v "system:" | head -20

# STEP 2: Describe specific role to see permissions
kubectl describe role <role-name> -n <namespace>
# Shows: Resources, verbs, API groups covered

# STEP 3: Get role YAML for modification
kubectl get role <role-name> -n <namespace> -o yaml

# STEP 4: Check for wildcard permissions (dangerous)
kubectl get clusterroles -o yaml | grep -B 2 '- "\*"'
# May show roles with unlimited permissions

# STEP 5: List all role bindings
kubectl get rolebindings -n <namespace>
kubectl get clusterrolebindings | grep -v "system:"

# STEP 6: Describe role binding to see assignments
kubectl describe rolebinding <binding-name> -n <namespace>
# Shows: Which subjects (users/groups) have which role

# STEP 7: Find all bindings for specific user
kubectl get rolebindings,clusterrolebindings -A \
  -o jsonpath='{range .items[*]}{.metadata.namespace}{"\t"}{.metadata.name}{"\t"}{range .subjects[?(@.kind=="User")]}{.name}{end}{"\n"}{end}' \
  | grep <username>

# STEP 8: Check for aggregated roles (combined permissions)
kubectl get clusterroles -l rbac.authorization.k8s.io/aggregate-to-admin
# Shows: Roles that aggregate to other roles

# STEP 9: Find all cluster admins
kubectl get clusterrolebindings -o wide | grep cluster-admin

# STEP 10: Check for service account role bindings
kubectl get rolebindings,clusterrolebindings -A \
  -o jsonpath='{range .items[*]}{.subjects[?(@.kind=="ServiceAccount")].name}{"\t"}{.roleRef.name}{"\n"}{end}'

# STEP 11: Verify RBAC is enabled
kubectl api-resources | grep -i rbac
# Should show: roles.rbac.authorization.k8s.io

# STEP 12: Get API authorization mode
kubectl get apiservices -A | grep authorization
# Check: Which authorization module is active
```

#### Kubernetes RBAC Policy Verification and Testing

```bash
# Create temporary test role to verify RBAC engine
kubectl create role test-role -n <namespace> --verb=get --resource=pods

# Create test role binding
kubectl create rolebinding test-binding -n <namespace> \
  --clusterrole=view --serviceaccount=<namespace>:test-sa

# Test with service account
kubectl auth can-i get pods -n <namespace> \
  --as=system:serviceaccount:<namespace>:test-sa

# Remove test role binding
kubectl delete rolebinding test-binding -n <namespace>
kubectl delete role test-role -n <namespace>

# Audit RBAC decisions
# Enable audit logging: check kube-apiserver flags
ps aux | grep kube-apiserver | grep -i audit

# Check audit log policy
cat /etc/kubernetes/audit-policy.yaml | head -20

# Monitor RBAC rejections in logs
kubectl get events -A --field-selector reason=Forbidden
```

#### Common Kubernetes RBAC Issues and Resolution

```bash
# ISSUE 1: Service account cannot list pods
# Check: Role has "get" but not "list"
# Fix: Add list verb to role
kubectl edit role <role-name> -n <namespace>
# Then add: - get, list, watch

# ISSUE 2: User cannot access resource in different namespace
# Check: Role binding only in specific namespace
# Fix: Create RoleBinding in target namespace OR use ClusterRoleBinding

# ISSUE 3: External user cannot authenticate
# Check: User cert/token in kubeconfig valid
# Fix: Update kubeconfig with new certificate/token

# ISSUE 4: Service account in pod gets permission denied
# Check: Token mounted? (/run/secrets/kubernetes.io/serviceaccount/token)
# Fix: Verify ServiceAccount defined, pod spec has serviceAccountName

# ISSUE 5: Cross-namespace pod reference fails
# Check: Only local namespace pods accessible by default
# Fix: Use RBAC to allow cross-namespace access if needed

# Comprehensive permission audit for user
kubectl get clusterroles,clusterrolebindings,roles,rolebindings -A -o wide | \
  grep -E "<username>|<service-account>"

# Find all permissions for user/service account
for role in $(kubectl get roles -A -o jsonpath='{.items[*].metadata.name}'); do
  kubectl get role $role -A -o yaml | grep -q "<user>" && echo "Found in role: $role"
done
```

#### Commands to NEVER use in production

```bash
# ❌ NEVER: kubectl create clusterrolebinding with cluster-admin for debugging
#    Creates permanent super-admin; huge security hole
# ❌ NEVER: kubectl delete all clusterrolebindings
#    Breaks all authentication; recovery requires manual intervention
# ❌ NEVER: kubectl edit role while pods using it are running
#    Changes take effect immediately; service interruption
# ❌ NEVER: Store kubeconfig with credentials in Git
#    Credentials exposed forever; rotate immediately
```

---

## AWS IAM Production Debugging

### Scenario: Diagnosing AWS IAM Permission Denied Errors

**Prerequisites**: User/role gets "Access Denied" in AWS API calls, AssumeRole failing  
**Common Causes**: Missing permission in policy, condition mismatch, trust relationship broken, STS session expired

#### AWS IAM Policy and Permission Debugging

```bash
# STEP 1: Get current AWS identity
aws sts get-caller-identity
# Shows: AWS account, user ARN, user ID

# STEP 2: Get current user permissions
aws iam get-user
# Shows: ARN, created date, path

# STEP 3: List all attached policies for user
aws iam list-attached-user-policies --user-name <username>
# Shows: Managed policies attached to user

# STEP 4: List inline policies for user
aws iam list-user-policies --user-name <username>

# STEP 5: Get specific policy version
aws iam get-user-policy --user-name <username> --policy-name <policy-name>
# Shows: Policy JSON (may be prettified)

# STEP 6: Simulate policy against action
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::ACCOUNT:user/<username> \
  --action-names s3:GetObject \
  --resource-arns arn:aws:s3:::bucket/key
# Shows: ALLOWED or DENIED with reason

# STEP 7: Test if user can perform action
aws iam simulate-custom-policy \
  --policy-input-list file://policy.json \
  --action-names ec2:DescribeInstances \
  --resource-arns arn:aws:ec2:*:ACCOUNT:instance/*
# Simulates custom policy

# STEP 8: Get permission boundary for user (if set)
aws iam get-user --user-name <username> | jq '.User.PermissionsBoundary'
# Shows: Permission boundary ARN if configured

# STEP 9: Check if user is in any groups with permissions
aws iam list-groups-for-user --user-name <username>
# Shows: Groups that grant permissions

# STEP 10: List policies attached to group
aws iam list-attached-group-policies --group-name <group-name>
# Shows: Managed policies for group

# STEP 11: Check policy conditions
aws iam get-role-policy --role-name <role-name> --policy-name <policy-name> | jq '.RolePolicy.Statement[].Condition'
# Shows: Any conditions on policy (IP, time-based, etc.)

# STEP 12: Test with different principal (user/role)
aws sts assume-role --role-arn arn:aws:iam::ACCOUNT:role/<role-name> --role-session-name test
# Verify role can be assumed
```

#### AWS IAM Role and AssumeRole Debugging

```bash
# STEP 1: Get role details
aws iam get-role --role-name <role-name>
# Shows: Role ARN, creation date, trust relationship

# STEP 2: View trust relationship (who can assume role)
aws iam get-role --role-name <role-name> | jq '.Role.AssumeRolePolicyDocument'
# JSON policy showing who can assume this role

# STEP 3: List all policies attached to role
aws iam list-attached-role-policies --role-name <role-name>

# STEP 4: List inline policies for role
aws iam list-role-policies --role-name <role-name>

# STEP 5: Check if service can assume role
aws iam get-role-policy --role-name <role-name> --policy-name <policy-name>
# Look for: AssumeRole permission for specific service

# STEP 6: Simulate assume-role with conditions
# Test if user can assume role with specific conditions
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::ACCOUNT:user/<user> \
  --action-names sts:AssumeRole \
  --resource-arns arn:aws:iam::ACCOUNT:role/<role>

# STEP 7: Check role session duration
aws iam get-role --role-name <role-name> | jq '.Role.MaxSessionDuration'
# Shows: Max session time in seconds

# STEP 8: Test assume-role with MFA
# If MFA required, must provide device serial and code
aws sts assume-role \
  --role-arn arn:aws:iam::ACCOUNT:role/<role> \
  --role-session-name <session-name> \
  --serial-number arn:aws:iam::ACCOUNT:mfa/<device> \
  --token-code <6-digit-mfa-code>

# STEP 9: Check for cross-account assume-role
# Trust relationship should allow principal from other account
aws iam get-role --role-name <role> | grep "AWS\|Principal"

# STEP 10: Verify external ID for cross-account access
# If using external ID, must be provided in assume-role
aws sts assume-role \
  --role-arn arn:aws:iam::ACCOUNT:role/<role> \
  --role-session-name <session> \
  --external-id <external-id>

# STEP 11: Check STS credentials validity
aws sts get-session-token
# Get temporary credentials; test if valid

# STEP 12: Monitor STS activity
aws cloudtril lookup-events --lookup-attributes AttributeKey=EventName,AttributeValue=AssumeRole
# Shows: Recent assume-role events
```

#### AWS IAM Policy Analysis and Least Privilege Verification

```bash
# Get all inline policies for user
aws iam list-user-policies --user-name <username> --query PolicyNames --output text | \
  xargs -I {} sh -c 'echo "Policy: {}"; aws iam get-user-policy --user-name <username> --policy-name {} --query UserPolicy.PolicyDocument'

# Convert inline policies to readable format
aws iam get-user-policy --user-name <username> --policy-name <policy> | \
  jq '.UserPolicy.PolicyDocument'

# Check for overly permissive policies (action: *)
aws iam list-attached-user-policies --user-name <username> --query AttachedPolicies[].PolicyName --output text | \
  xargs -I {} aws iam get-policy-version --policy-arn arn:aws:iam::aws:policy/{} --version-id v1 | \
  grep -i '"\*"'

# Audit all users with admin access
aws iam list-users --query Users[].UserName --output text | \
  xargs -I {} sh -c 'echo "User: {}"; aws iam list-attached-user-policies --user-name {} | jq ".AttachedPolicies[] | select(.PolicyName | contains(\"Admin\"))"'

# Find policies not used recently
aws iam get-credential-report && \
  cat /tmp/credential-report.csv | awk -F',' '{if($5=="true" && $(NF-1)=="N/A") print $1 " - Never used"}'

# Check for wildcard resources in policies
aws iam get-user-policy --user-name <username> --policy-name <policy> | \
  jq '.UserPolicy.PolicyDocument.Statement[] | select(.Resource | contains("*"))'
```

#### AWS IAM Federation and External Identity Provider Debugging

```bash
# STEP 1: List identity providers configured
aws iam list-open-id-connect-providers
aws iam list-saml-providers

# STEP 2: Get SAML provider details
aws iam get-saml-provider --saml-provider-arn <arn>
# Shows: Certificate, creation date

# STEP 3: Check OpenID Connect provider thumbprint
aws iam get-open-id-connect-provider --open-id-connect-provider-arn <arn>

# STEP 4: Test SAML assumption
# Requires SAML response; typically done by IdP

# STEP 5: Check for SAML metadata
# Usually available at: https://idp-provider.com/metadata

# STEP 6: Verify role trust relationship for federation
# Must include Principal with SAML provider ARN
aws iam get-role --role-name <federated-role> | \
  jq '.Role.AssumeRolePolicyDocument.Statement[] | select(.Principal.Federated)'

# STEP 7: Monitor failed federation attempts
aws cloudtrail lookup-events --lookup-attributes AttributeKey=EventName,AttributeValue=AssumeRoleWithSAML
```

#### Commands to NEVER use in production

```bash
# ❌ NEVER: aws iam attach-user-policy with AdministratorAccess for one-off task
#    Makes user permanent admin; huge security risk
# ❌ NEVER: Create long-lived access keys for humans
#    Use temporary STS credentials instead
# ❌ NEVER: Use root account credentials
#    Always use IAM users; root is restricted to account and billing
# ❌ NEVER: Store AWS credentials in application source code
#    Use IAM roles, environment variables, or credential files
```

---

## Google Cloud IAM Production Debugging

### Scenario: Diagnosing Google Cloud IAM Permission Denied

**Prerequisites**: User/service account gets permission denied, role binding not working  
**Common Causes**: Role not granted, custom role misconfigured, service account impersonation denied

#### Google Cloud IAM Permissions and Roles

```bash
# STEP 1: Get current Google Cloud identity
gcloud auth list
# Shows: Logged-in accounts

# STEP 2: Get current project and authenticated user
gcloud config list
gcloud auth application-default print-access-token | jq -R 'split(".")[1] | @base64d | fromjson'

# STEP 3: Check user roles in project
gcloud projects get-iam-policy <project-id> \
  --flatten="bindings[].members" \
  --format="table(bindings.role)" \
  --filter="bindings.members:<user-email>"

# STEP 4: List all role bindings for project
gcloud projects get-iam-policy <project-id> --format=json | jq '.bindings'

# STEP 5: Check if user has specific permission
gcloud projects test-iam-permissions <project-id> \
  --permissions=compute.instances.create,storage.buckets.get \
  --condition="<condition>"

# STEP 6: Simulate permission check (not exact, but helpful)
# Actually test by attempting action or use test-iam-permissions

# STEP 7: List all predefined roles
gcloud iam roles list --format="table(name,description)" | head -20

# STEP 8: Describe specific role
gcloud iam roles describe roles/compute.admin
# Shows: Permissions included in role

# STEP 9: List custom roles for organization
gcloud iam roles list --organization <org-id>

# STEP 10: Get custom role details
gcloud iam roles describe <role-id> --organization <org-id>

# STEP 11: Check condition-based role binding
gcloud projects get-iam-policy <project-id> --format=json | \
  jq '.bindings[] | select(.condition != null)'
# Shows: Time-based or resource-based conditions

# STEP 12: Verify service account has impersonation role
gcloud iam service-accounts get-iam-policy <sa-email>
# Shows: Who can impersonate this service account
```

#### Google Cloud Service Account Debugging

```bash
# STEP 1: List service accounts in project
gcloud iam service-accounts list

# STEP 2: Get service account details
gcloud iam service-accounts describe <sa-email>
# Shows: Creation time, email, unique ID

# STEP 3: List keys for service account
gcloud iam service-accounts keys list --iam-account=<sa-email>
# Shows: Keys and their status

# STEP 4: Get service account IAM policy
gcloud iam service-accounts get-iam-policy <sa-email>
# Shows: Who can use/manage this service account

# STEP 5: Check if service account can be impersonated
# Try: gcloud iam service-accounts impersonate <sa-email> \
#   --token-format=json

# STEP 6: Verify credentials file for service account
gcloud auth activate-service-account --key-file=<json-file>
# Tests if service account JSON key is valid

# STEP 7: Check service account role bindings
gcloud projects get-iam-policy <project-id> \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:<sa-email>"

# STEP 8: Test service account permissions
# After activating service account:
gcloud projects test-iam-permissions <project-id> \
  --permissions=compute.instances.list

# STEP 9: Monitor service account activity
gcloud logging read "protoPayload.authenticationInfo.principalEmail=<sa-email>" \
  --project=<project-id> --format=json | head -20

# STEP 10: Check for unused service accounts
# Monitor lastAuthenticatedTime in service account details

# STEP 11: Verify workload identity binding (for Kubernetes)
# GKE service account must have Google service account annotated
kubectl get sa <k8s-sa> -n <namespace> -o yaml | grep iam.gke.io

# STEP 12: Check workload identity federation setup
gcloud iam workload-identity-pools list --location=global
```

#### Google Cloud Custom Roles and Permission Debugging

```bash
# Create custom role (testing)
gcloud iam roles create <role-name> \
  --project=<project-id> \
  --title="Custom Role" \
  --permissions=compute.instances.list,compute.instances.get

# Test custom role permissions
gcloud projects get-iam-policy <project-id> --format=json | \
  jq '.bindings[] | select(.role | contains("custom"))'

# Compare built-in role permissions
gcloud iam roles describe roles/viewer --format=json | jq '.includedPermissions | sort' > viewer-perms.json

# Verify permission is in role
gcloud iam roles describe <role-name> --project=<project-id> --format=json | \
  jq '.includedPermissions[] | select(. == "desired-permission")'

# Test granular permission granting
# Instead of full role, grant specific permissions via custom role
gcloud iam roles create least-privilege-role \
  --permissions=storage.buckets.get,storage.objects.list
```

#### Commands to NEVER use in production

```bash
# ❌ NEVER: gcloud projects add-iam-policy-binding with roles/editor for troubleshooting
#    User gets edit permissions on all resources
# ❌ NEVER: Store service account JSON key in Git
#    Credentials permanently exposed
# ❌ NEVER: gcloud auth login as root/shared account
#    Use individual user accounts for audit trail
# ❌ NEVER: Remove all role bindings without backup
#    Service becomes inaccessible
```

---

## Azure RBAC Production Debugging

### Scenario: Diagnosing Azure RBAC Access Denied

**Prerequisites**: User/service principal denied access, role assignment not working  
**Common Causes**: Role not assigned, scope wrong, managed identity misconfigured

#### Azure RBAC Roles and Permissions

```bash
# STEP 1: Get current Azure identity
az account show
# Shows: Current user, tenant, subscription

# STEP 2: List role assignments in subscription
az role assignment list --subscription <subscription-id>

# STEP 3: List role assignments for specific user
az role assignment list --assignee <user-email> --subscription <subscription-id>

# STEP 4: Get specific role definition
az role definition list --name "Contributor"
# Shows: Role permissions and description

# STEP 5: List all built-in roles
az role definition list --query "[].name" --output table | head -20

# STEP 6: Create custom role (for testing)
az role definition create --role-definition @role-definition.json
# role-definition.json must contain role structure

# STEP 7: Test if user has specific permission
# Unfortunately, Azure doesn't have direct permission test
# Workaround: attempt action or use deployment What-if

# STEP 8: Check role assignments at different scopes
az role assignment list --scope /subscriptions/<subscription-id>  # Subscription
az role assignment list --scope /subscriptions/<sub>/resourceGroups/<rg>  # Resource group
az role assignment list --scope /subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.Compute/virtualMachines/<vm>  # Resource

# STEP 9: Get inherited role assignments
# Roles assigned at higher scope inherited by lower scope

# STEP 10: Check if managed identity can perform action
az role assignment list --assignee-object-id $(az identity show -g <rg> -n <name> --query principalId -o tsv)

# STEP 11: Verify service principal permissions
az sp list --query "[].{appId: appId, displayName: displayName}" --output table | head -20

# STEP 12: Check for conditional access policies
# May block access even with correct permissions
az ad conditional-access policy list
```

#### Azure Service Principal and Managed Identity Debugging

```bash
# STEP 1: List service principals
az ad sp list --all --query "[].{appId: appId, displayName: displayName}"

# STEP 2: Get service principal details
az ad sp show --id <service-principal-id>

# STEP 3: List credentials for service principal
az ad app credential list --id <app-id>

# STEP 4: List managed identities
az identity list -g <resource-group>

# STEP 5: Get managed identity details
az identity show -g <resource-group> -n <identity-name>

# STEP 6: Assign role to managed identity
az role assignment create \
  --role "Contributor" \
  --assignee-object-id $(az identity show -g <rg> -n <name> --query principalId -o tsv) \
  --scope /subscriptions/<subscription-id>

# STEP 7: Test managed identity access from VM
# SSH to VM and run: curl -s http://169.254.169.254/metadata/identity/oauth2/token?api-version=2017-09-01&resource=https://management.azure.com | jq .

# STEP 8: Check federated credentials (for OIDC/GitHub Actions)
az identity federated-credential list -g <rg> --identity-name <identity-name>

# STEP 9: Verify app registration permissions
az ad app permission list --id <app-id>

# STEP 10: Check for admin consent requirements
# Azure Graph API permissions may require admin approval

# STEP 11: Test service principal authentication
az login --service-principal -u <app-id> -p <password> --tenant <tenant-id>

# STEP 12: Monitor service principal activity
az monitor metrics list -g <rg> -n <resource> --interval PT1M
```

#### Commands to NEVER use in production

```bash
# ❌ NEVER: az role assignment create with Owner role for troubleshooting
#    User gets full subscription access
# ❌ NEVER: Store service principal credentials in environment variables
#    Use Azure Key Vault or managed identity instead
# ❌ NEVER: Use shared/service principal account for individual work
#    No audit trail; use personal account
# ❌ NEVER: Remove all role assignments from resource
#    Resource becomes inaccessible
```

---

## Cross-Cloud and Hybrid IAM Scenarios

### Scenario: Diagnosing Kubernetes Service Account to Cloud IAM Binding

**Prerequisites**: Pod needs to access cloud resources (AWS, GCP, Azure), workload identity or IRSA misconfigured  
**Common Causes**: Annotation mismatch, trust relationship missing, token validation fails

#### AWS IRSA (IAM Roles for Service Accounts) Debugging

```bash
# STEP 1: Verify OIDC provider is configured
aws iam list-open-id-connect-providers

# STEP 2: Get OIDC provider details
aws iam get-open-id-connect-provider-configuration --open-id-connect-provider-arn <arn>

# STEP 3: Check service account has OIDC annotation
kubectl get sa -n <namespace> <sa-name> -o yaml | grep iam.amazonaws.com

# STEP 4: Verify role trust relationship allows OIDC provider
aws iam get-role --role-name <role-name> | jq '.Role.AssumeRolePolicyDocument'
# Should reference OIDC provider and service account

# STEP 5: Check if pod can get STS credentials
# Inside pod:
curl -s $AWS_WEB_IDENTITY_TOKEN_FILE | jq . 2>/dev/null || \
  echo "Token endpoint: $AWS_WEB_IDENTITY_TOKEN_FILE"

# STEP 6: Test assume-role with web identity
aws sts assume-role-with-web-identity \
  --role-arn arn:aws:iam::ACCOUNT:role/<role> \
  --role-session-name test \
  --web-identity-token $(cat $AWS_WEB_IDENTITY_TOKEN_FILE)

# STEP 7: Verify pod environment variables are set
kubectl exec -it <pod> -n <namespace> -- env | grep -E "AWS_ROLE|AWS_WEB_IDENTITY"

# STEP 8: Check pod service account token
kubectl get secret $(kubectl get sa -n <namespace> <sa-name> -o jsonpath='{.secrets[0].name}') \
  -n <namespace> -o jsonpath='{.data.token}' | base64 -d | head -c 50

# STEP 9: Monitor assume-role API calls
aws cloudtrail lookup-events --lookup-attributes AttributeKey=EventName,AttributeValue=AssumeRoleWithWebIdentity

# STEP 10: Verify AWS SigV4 signing works
# Check AWS SDK logs in application

# STEP 11: Test role assumption from pod
kubectl exec -it <pod> -n <namespace> -- aws sts get-caller-identity

# STEP 12: Check for missing IAM policy
# If role assumed but action fails, verify policy has permission
aws iam get-role-policy --role-name <role> --policy-name <policy>
```

#### Google Cloud Workload Identity Debugging

```bash
# STEP 1: Enable workload identity on cluster
gcloud container clusters update <cluster> --workload-pool=<project>.svc.id.goog

# STEP 2: Create Google service account
gcloud iam service-accounts create <gsa-name>

# STEP 3: Create Kubernetes service account annotation
kubectl annotate serviceaccount <ksa-name> -n <namespace> \
  iam.gke.io/gcp-service-account=<gsa-name>@<project>.iam.gserviceaccount.com

# STEP 4: Bind Kubernetes SA to Google SA
gcloud iam service-accounts add-iam-policy-binding \
  <gsa-name>@<project>.iam.gserviceaccount.com \
  --role roles/iam.workloadIdentityUser \
  --member serviceAccount:<project>.svc.id.goog[<namespace>/<ksa-name>]

# STEP 5: Verify workload identity annotation
kubectl get sa <ksa-name> -n <namespace> -o yaml

# STEP 6: Test token exchange from pod
kubectl exec -it <pod> -n <namespace> -- \
  gcloud auth application-default print-access-token

# STEP 7: Verify pod can access Google Cloud resources
kubectl exec -it <pod> -n <namespace> -- \
  gsutil ls gs://<bucket-name>/

# STEP 8: Check token path environment variable
kubectl exec -it <pod> -n <namespace> -- \
  echo $GOOGLE_APPLICATION_CREDENTIALS

# STEP 9: Monitor workload identity API calls
gcloud logging read "protoPayload.authenticationInfo.principalEmail=<gsa-email>" \
  --project=<project-id> --limit=20

# STEP 10: Verify GKE cluster workload identity config
gcloud container clusters describe <cluster> --format='value(workloadIdentityConfig)'

# STEP 11: Check for pod-level security context issues
# Workload identity requires: runAsNonRoot may conflict
kubectl get pod <pod> -n <namespace> -o yaml | grep -A 5 securityContext

# STEP 12: Test with older workload identity (ambient credentials)
# If using exec credential source instead of pod OIDC
```

#### Azure Managed Identity with AKS Debugging

```bash
# STEP 1: Check if cluster has managed identity
az aks show -g <rg> -n <cluster> --query identityProfile

# STEP 2: Assign role to managed identity
az role assignment create \
  --role "Contributor" \
  --assignee $(az aks show -g <rg> -n <cluster> --query identityProfile.kubeletIdentity.objectId -o tsv) \
  --scope /subscriptions/<subscription-id>

# STEP 3: Create pod-managed identity (if using aad-pod-identity)
kubectl label pod <pod> aadpodidbinding=<binding-name>

# STEP 4: Check pod identity binding status
kubectl get azureidentitybinding -n <namespace>

# STEP 5: Verify service principal binding
kubectl get azureidentity -n <namespace> -o yaml

# STEP 6: Test managed identity access from pod
kubectl exec -it <pod> -n <namespace> -- \
  curl -s http://169.254.169.254/metadata/identity/oauth2/token?api-version=2017-09-01&resource=https://management.azure.com | jq .

# STEP 7: Check pod annotations for managed identity
kubectl get pod <pod> -n <namespace> -o yaml | grep aadpodidbinding

# STEP 8: Monitor managed identity API calls
az monitor activity-log list --resource-group <rg> --max-items 20

# STEP 9: Verify federated credentials for GitHub Actions
# If using OIDC federation with GitHub
az identity federated-credential show -g <rg> --identity-name <identity> -n github

# STEP 10: Test federated credential token
# GitHub Actions will use OIDC token to assume role

# STEP 11: Check for mutual TLS between pod and metadata service
# Azure metadata service requires specific headers

# STEP 12: Verify network policies allow metadata service
kubectl exec -it <pod> -n <namespace> -- \
  timeout 5 curl -I http://169.254.169.254/metadata/
```

#### Commands to NEVER use in production

```bash
# ❌ NEVER: Bind cloud admin role to Kubernetes service account permanently
#    Service account compromise = full cloud access
# ❌ NEVER: Share OIDC provider configuration across clusters
#    Allows cross-cluster impersonation
# ❌ NEVER: Create workload identity with wildcard permissions
#    Pod can access all resources
```

---

## IAM Policies and Permission Auditing

### Scenario: Auditing IAM Configuration and Drift Detection

**Prerequisites**: Need to audit permissions, detect policy violations, find overly permissive access  
**Common Causes**: Manual changes not tracked, multiple team members modifying IAM, compliance drift

#### IAM Policy Audit and Compliance

```bash
# Kubernetes RBAC audit
# Export all RBAC configuration
kubectl get roles,rolebindings,clusterroles,clusterrolebindings -A -o yaml > rbac-backup.yaml

# Find cluster admins
kubectl get clusterrolebindings -o wide | grep cluster-admin

# Find service accounts with wildcard permissions
kubectl get roles,clusterroles -A -o json | \
  jq -r '.items[] | select(.rules[]? | select(.verbs[]? == "*" or .resources[]? == "*" or .apiGroups[]? == "*")) | "\(.kind): \(.metadata.name)"'

# Check for privileged pod security policies
kubectl get psp --all-namespaces -o yaml | grep -i "privileged\|hostPath"

# AWS IAM audit
# Find IAM users without MFA
aws iam get-credential-report && \
  cat credential-report.csv | awk -F',' '{if($4=="false") print $1 " - MFA NOT ENABLED"}'

# Find admin users
aws iam list-entities-for-policy --policy-arn arn:aws:iam::aws:policy/AdministratorAccess

# Find unused credentials
aws iam list-users --query Users[].UserName --output text | \
  xargs -I {} sh -c 'echo "User: {}"; aws iam get-user-login-profile --user-name {} 2>/dev/null || echo "  No login profile"'

# GCP IAM audit
# Find project editors/owners
gcloud projects get-iam-policy <project-id> --format=json | \
  jq '.bindings[] | select(.role | contains("roles/editor") or contains("roles/owner")) | .members'

# Find unused service accounts
gcloud iam service-accounts list --format=json | \
  jq '.[] | select(.displayName | contains("unused")) | .email'

# Azure RBAC audit
# Find subscription-level admin roles
az role assignment list --scope /subscriptions/<sub-id> | \
  grep -i "Owner\|Contributor"

# Find unused service principals
az ad sp list --all --query "[].{appId: appId, createdDateTime: createdDateTime}" --output table
```

#### IAM Compliance and Policy Enforcement

```bash
# Kubernetes Network Policy audit (related to RBAC)
kubectl get networkpolicies -A

# Test pod isolation with network policies
# Create test pods, verify communication blocked

# Check pod security policies (deprecated in K8s 1.25+)
kubectl get psp

# Verify security context requirements
kubectl get pods -A -o yaml | grep -A 3 securityContext | head -20

# AWS Access Analyzer
# Check external access to resources
aws accessanalyzer start-resource-scan --resource-arn arn:aws:s3:::bucket-name

# GCP Organization Policy audit
gcloud resource-manager org-policies list --project=<project-id>

# Azure Policy audit
az policy state summarize --subscription <sub-id>

# Monitor IAM changes (audit trail)
# Kubernetes: kubectl get events -A | grep -i "rbac\|role\|permission"
# AWS: aws cloudtrail lookup-events --lookup-attributes AttributeKey=EventName,AttributeValue=PutRolePolicy
# GCP: gcloud logging read "protoPayload.methodName=~\".*SetIamPolicy\""
# Azure: az monitor activity-log list --resource-group <rg> --operations "Microsoft.Authorization/roleAssignments/write"
```

#### Commands to NEVER use in production

```bash
# ❌ NEVER: kubectl delete all clusterrolebindings
#    Breaks authentication for all users
# ❌ NEVER: aws iam put-user-policy without review
#    May grant unintended permissions
# ❌ NEVER: Delete audit logs to "clean up"
#    Destroys compliance trail; may violate regulations
```

---

## Critical IAM Debugging Principles

### IAM Security Best Practices

1. **Least Privilege**: Grant minimum permissions needed
2. **Audit Trail**: Enable logging for all IAM changes
3. **Regular Review**: Audit permissions quarterly
4. **MFA**: Require for sensitive accounts
5. **Rotation**: Rotate credentials regularly
6. **Segregation**: Separate roles for different functions
7. **No Wildcards**: Avoid * in actions or resources
8. **Default Deny**: Default deny, explicitly allow
9. **Conditions**: Use time/IP-based conditions
10. **Testing**: Test policies in staging first

### IAM Debugging Checklist

```
Before granting permissions:
- [ ] What is the minimum permission needed?
- [ ] Is this for a human or service?
- [ ] How long are credentials valid?
- [ ] Are there any IP/time/MFA conditions?
- [ ] Has this been approved by security?
- [ ] Is audit logging enabled?

When debugging permission denied:
- [ ] Verify user/service account exists
- [ ] Check all role assignments (all scopes)
- [ ] Verify policy conditions don't block
- [ ] Test with simulation tools
- [ ] Check trust relationships (cross-account)
- [ ] Verify credentials haven't expired
- [ ] Look for service-level permissions
- [ ] Check for deny policies overriding allow
```

### Common IAM Mistakes and Fixes

| Mistake | Issue | Fix |
|---------|-------|-----|
| Overly broad permissions | Security risk | Use least-privilege roles |
| Long-lived credentials | Exposure risk | Use temporary tokens |
| Hardcoded credentials | Breach risk | Use environment or managed identity |
| No audit logging | Compliance violation | Enable CloudTrail/Cloud Audit Logs |
| Unused permissions granted | Privilege creep | Audit and remove regularly |
| Service account admin access | Attack surface | Grant minimal permissions |
| Password-based auth | Weak security | Use MFA and temporary tokens |
| No condition-based access | Over-exposure | Add time/IP/device conditions |

### IAM Verification Commands Quick Reference

```bash
# Kubernetes
kubectl auth can-i get pods --as=system:serviceaccount:default:default

# AWS
aws iam simulate-principal-policy --policy-source-arn <arn> --action-names s3:GetObject

# GCP
gcloud projects test-iam-permissions <project> --permissions=compute.instances.list

# Azure
az role assignment list --assignee <email>
```

### Documentation and References

**Kubernetes RBAC**
- Official: https://kubernetes.io/docs/reference/access-authn-authz/rbac/
- Best Practices: https://kubernetes.io/docs/concepts/security/rbac-good-practices/

**AWS IAM**
- Official: https://docs.aws.amazon.com/iam/
- Policy Simulator: https://policysim.aws.amazon.com/
- Best Practices: https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html

**Google Cloud IAM**
- Official: https://cloud.google.com/iam/docs
- Understanding Roles: https://cloud.google.com/iam/docs/understanding-roles
- Best Practices: https://cloud.google.com/iam/docs/best-practices

**Azure RBAC**
- Official: https://learn.microsoft.com/en-us/azure/role-based-access-control/
- Understanding Scopes: https://learn.microsoft.com/en-us/azure/role-based-access-control/scope-overview
- Best Practices: https://learn.microsoft.com/en-us/azure/role-based-access-control/best-practices

---

**Last Updated**: January 2026  
**Platforms Covered**: Kubernetes RBAC, AWS IAM, GCP IAM, Azure RBAC, Cross-Cloud Workload Identity  
**Severity Level**: Production Critical  
**Review Frequency**: Monthly (compliance requirement)