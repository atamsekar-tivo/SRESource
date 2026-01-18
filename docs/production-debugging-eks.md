# Production Debugging Commands for AWS EKS

> **Critical Context**: EKS cluster misconfiguration can cause complete service outage. Always use separate dev/staging clusters for testing. Enable cluster logging before issues occur. Have rollback procedures ready. Test upgrades on non-production first. Document all manual changes.

---

## EKS Cluster Creation and Initial Setup

### Scenario: Creating EKS Cluster with Proper Configuration

**Prerequisites**: AWS account, proper IAM permissions, VPC configured, subnets tagged  
**Common Causes**: Missing IAM role, subnet configuration wrong, security group misconfigured, logging not enabled

#### EKS Cluster Creation Prerequisites and Planning

```bash
# STEP 1: Verify AWS account and credentials
aws sts get-caller-identity
# Shows: Account ID, user ARN

# STEP 2: Check AWS CLI version (EKS requires recent version)
aws --version
# Minimum: AWS CLI v2

# STEP 3: Verify IAM permissions for creating EKS cluster
aws iam get-user
# User must have eks:CreateCluster, ec2:*, iam:* permissions

# STEP 4: Create EKS cluster IAM role
aws iam create-role --role-name eks-cluster-role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {"Service": "eks.amazonaws.com"},
        "Action": "sts:AssumeRole"
      }
    ]
  }'

# STEP 5: Attach required policy to EKS cluster role
aws iam attach-role-policy --role-name eks-cluster-role \
  --policy-arn arn:aws:iam::aws:policy/AmazonEKSClusterPolicy
aws iam attach-role-policy --role-name eks-cluster-role \
  --policy-arn arn:aws:iam::aws:policy/AmazonEKSServiceRolePolicy

# STEP 6: Create VPC and subnets (if not existing)
# Must have 2+ public and 2+ private subnets in different AZs
aws ec2 create-vpc --cidr-block 10.0.0.0/16

# STEP 7: Tag subnets for EKS discovery
# Public subnets: kubernetes.io/role/elb=1
# Private subnets: kubernetes.io/role/internal-elb=1
aws ec2 create-tags --resources <subnet-id> \
  --tags Key=kubernetes.io/role/elb,Value=1

# STEP 8: Create security group for cluster
aws ec2 create-security-group --group-name eks-cluster-sg \
  --description "EKS cluster security group" --vpc-id <vpc-id>

# STEP 9: Allow control plane to communicate with nodes
aws ec2 authorize-security-group-ingress --group-id <cluster-sg-id> \
  --protocol tcp --port 443 --source-security-group-id <node-sg-id>

# STEP 10: Verify VPC has DNS enabled
aws ec2 describe-vpc-attribute --vpc-id <vpc-id> --attribute enableDnsHostnames
# Should show: true

# STEP 11: Verify internet gateway and route tables
aws ec2 describe-internet-gateways --filters Name=attachment.vpc-id,Values=<vpc-id>
aws ec2 describe-route-tables --filters Name=vpc-id,Values=<vpc-id>

# STEP 12: Get cluster role ARN
aws iam get-role --role-name eks-cluster-role --query Role.Arn
```

#### EKS Cluster Creation and Configuration

```bash
# STEP 1: Create EKS cluster with all settings
aws eks create-cluster \
  --name <cluster-name> \
  --version 1.28 \
  --role-arn arn:aws:iam::<account>:role/eks-cluster-role \
  --resources-vpc-config subnetIds=<subnet-1>,<subnet-2>,<subnet-3>,<subnet-4> \
  --logging '{"clusterLogging":[{"enabled":true,"types":["api","audit","authenticator","controllerManager","scheduler"]}]}' \
  --tags Name=<cluster-name>,Environment=production

# STEP 2: Wait for cluster to reach ACTIVE state
aws eks wait cluster-active --name <cluster-name>
# May take 10-15 minutes

# STEP 3: Get cluster details
aws eks describe-cluster --name <cluster-name>
# Shows: Endpoint, status, version

# STEP 4: Get cluster endpoint
aws eks describe-cluster --name <cluster-name> \
  --query 'cluster.endpoint' --output text

# STEP 5: Get cluster CA certificate
aws eks describe-cluster --name <cluster-name> \
  --query 'cluster.certificateAuthority.data' --output text | base64 -d

# STEP 6: Update kubeconfig
aws eks update-kubeconfig --name <cluster-name> --region <region>
# Adds cluster to ~/.kube/config

# STEP 7: Verify kubectl connectivity
kubectl cluster-info
# Shows: Kubernetes master location, CoreDNS

# STEP 8: Check default namespaces
kubectl get namespaces
# Should show: default, kube-system, kube-public, kube-node-lease

# STEP 9: Check control plane components
kubectl get pods -n kube-system | head -10
# Shows: coredns, aws-node, kube-proxy, etc.

# STEP 10: Verify cluster logging is enabled
aws eks describe-cluster --name <cluster-name> \
  --query 'cluster.logging.clusterLogging' --output json

# STEP 11: Check CloudWatch log groups
aws logs describe-log-groups --log-group-name-prefix /aws/eks/<cluster-name>/

# STEP 12: Verify CNI plugin is running
kubectl get daemonset -n kube-system
# Should show: aws-node (VPC CNI), kube-proxy
```

#### EKS Node Group Creation

```bash
# STEP 1: Create IAM role for EC2 nodes
aws iam create-role --role-name eks-node-role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "ec2.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# STEP 2: Attach required policies to node role
aws iam attach-role-policy --role-name eks-node-role \
  --policy-arn arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy
aws iam attach-role-policy --role-name eks-node-role \
  --policy-arn arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy
aws iam attach-role-policy --role-name eks-node-role \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly

# STEP 3: Create instance profile for nodes
aws iam create-instance-profile --instance-profile-name eks-node-instance-profile
aws iam add-role-to-instance-profile --instance-profile-name eks-node-instance-profile \
  --role-name eks-node-role

# STEP 4: List available EKS-optimized AMIs
aws eks describe-nodegroup-image --query 'images[0]'

# STEP 5: Create node group with auto-scaling
aws eks create-nodegroup \
  --cluster-name <cluster-name> \
  --nodegroup-name <nodegroup-name> \
  --scaling-config minSize=2,maxSize=10,desiredSize=3 \
  --subnets <subnet-1> <subnet-2> <subnet-3> \
  --node-role-arn arn:aws:iam::<account>:role/eks-node-role \
  --ami-type AL2_x86_64 \
  --instance-types t3.medium \
  --disk-size 50 \
  --tags Name=<nodegroup-name>,Environment=production

# STEP 6: Wait for node group to reach ACTIVE state
aws eks wait nodegroup-active --cluster-name <cluster-name> --nodegroup-name <nodegroup-name>

# STEP 7: Verify nodes are joining cluster
kubectl get nodes
# Should show: nodes in Ready state

# STEP 8: Check node readiness
kubectl get nodes -o wide
# Shows: IP, OS image, kubelet version

# STEP 9: Check node capacity
kubectl describe nodes | grep -A 5 "Allocated resources"
# Shows: CPU, memory available

# STEP 10: Verify node security group
aws ec2 describe-security-groups --group-ids <node-sg-id>
# Should allow ingress from cluster security group

# STEP 11: Check node IAM role policies
aws iam list-attached-role-policies --role-name eks-node-role

# STEP 12: Monitor node status from AWS
aws eks describe-nodegroup --cluster-name <cluster-name> \
  --nodegroup-name <nodegroup-name> --query 'nodegroup.status'
```

#### EKS Cluster Initial Configuration

```bash
# STEP 1: Install metrics-server for HPA
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
kubectl wait --for=condition=ready pod -l k8s-app=metrics-server -n kube-system --timeout=300s

# STEP 2: Verify metrics-server running
kubectl get deployment -n kube-system metrics-server

# STEP 3: Install AWS Load Balancer Controller (for ALB/NLB ingress)
# First, create IAM policy
curl -o iam_policy.json https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/v2.6.0/docs/install/iam_policy.json
aws iam create-policy --policy-name AWSLoadBalancerControllerIAMPolicy --policy-document file://iam_policy.json

# STEP 4: Create service account for load balancer controller
kubectl create serviceaccount aws-load-balancer-controller -n kube-system

# STEP 5: Annotate service account with IAM role
kubectl annotate serviceaccount aws-load-balancer-controller -n kube-system \
  eks.amazonaws.com/role-arn=arn:aws:iam::<account>:role/<role-name>

# STEP 6: Install load balancer controller via Helm
helm repo add eks https://aws.github.io/eks-charts
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system --set serviceAccount.create=false --set serviceAccount.name=aws-load-balancer-controller

# STEP 7: Verify load balancer controller running
kubectl get deployment -n kube-system aws-load-balancer-controller

# STEP 8: Install EBS CSI driver for persistent volumes
aws eks create-addon --cluster-name <cluster-name> --addon-name aws-ebs-csi-driver \
  --addon-version v1.20.0-eksbuild.1

# STEP 9: Verify EBS CSI driver
kubectl get daemonset -n kube-system ebs-csi-node

# STEP 10: Install VPC CNI metrics
kubectl apply -f https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/master/config/v1.8/cni-metrics-helper.yaml

# STEP 11: Enable CoreDNS addon
aws eks create-addon --cluster-name <cluster-name> --addon-name coredns

# STEP 12: Verify all critical add-ons
kubectl get daemonset -n kube-system
kubectl get deployment -n kube-system
```

#### Commands to NEVER use in production

```bash
# ❌ NEVER: aws eks create-cluster without logging enabled
#    Loses audit trail; can't debug issues later
# ❌ NEVER: Create cluster with single AZ
#    Single point of failure; AWS recommends 2+ AZs
# ❌ NEVER: Use default VPC for production cluster
#    May conflict with other services; hard to manage
# ❌ NEVER: Create node group without scaling configuration
#    Nodes won't auto-scale; may run out of capacity
# ❌ NEVER: Manually modify cluster security groups
#    May break node communication; update via API instead
```

---

## EKS Cluster Upgrades

### Scenario: Planning and Executing EKS Control Plane Upgrade

**Prerequisites**: Current cluster version known, upgrade path valid, node groups compatible  
**Common Causes**: Nodes older than control plane, addons not compatible, PodDisruptionBudgets block drain

#### EKS Control Plane Upgrade Planning

```bash
# STEP 1: Check current cluster version
aws eks describe-cluster --name <cluster-name> \
  --query 'cluster.version' --output text

# STEP 2: Check current node group versions
aws eks describe-nodegroup --cluster-name <cluster-name> \
  --nodegroup-name <nodegroup-name> \
  --query 'nodegroup.version' --output text

# STEP 3: Check supported Kubernetes versions
aws eks describe-addon-versions --addon-name vpc-cni \
  --query 'addonVersions[].kubernetesVersion'

# STEP 4: Check upgrade path (AWS supports N-1, N-2 version upgrades)
# From 1.26 can upgrade to 1.27 or 1.28
# Cannot skip versions: 1.26 -> 1.29 fails

# STEP 5: Get release notes for target version
# Visit: https://kubernetes.io/releases/

# STEP 6: Check addon compatibility with target version
aws eks describe-addon --cluster-name <cluster-name> --addon-name vpc-cni \
  --query 'addon.addonVersion'

# STEP 7: Create backup of cluster configuration
kubectl get all -A -o yaml > cluster-backup.yaml
kubectl get pvc -A -o yaml >> cluster-backup.yaml

# STEP 8: Check for pod disruption budgets that may block draining
kubectl get poddisruptionbudgets -A
# Shows: Pods that can't be disrupted

# STEP 9: Verify node termination grace period
kubectl get nodes -o jsonpath='{.items[*].spec.terminationGracePeriodSeconds}'

# STEP 10: Check cluster autoscaler compatibility
# Must be compatible with both old and new K8s versions during upgrade

# STEP 11: Verify stateful workloads have replicas in multiple nodes
kubectl get statefulset -A -o wide
# Check: replicas and node spread

# STEP 12: Drain test node to verify PDB compatibility
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data --dry-run=client
# Tests if drain would succeed
```

#### EKS Control Plane Upgrade Execution

```bash
# STEP 1: Announce maintenance window to team
# Send notification with: start time, expected duration (20-30 min), impact

# STEP 2: Verify no deployments in pending state
kubectl get pods -A | grep Pending

# STEP 3: Update cluster addons first (before control plane)
aws eks describe-addon --cluster-name <cluster-name> \
  --addon-name vpc-cni --query 'addon.addonVersion'

# STEP 4: Check addon update available
aws eks describe-addon-versions --addon-name vpc-cni \
  --kubernetes-version 1.28 --query 'addonVersions[0].addonVersion'

# STEP 5: Update VPC CNI addon
aws eks update-addon --cluster-name <cluster-name> \
  --addon-name vpc-cni --addon-version <new-version>

# STEP 6: Monitor addon update progress
aws eks describe-addon --cluster-name <cluster-name> \
  --addon-name vpc-cni --query 'addon.addonVersion'

# STEP 7: Wait for addon update to complete
sleep 30 && aws eks describe-addon --cluster-name <cluster-name> \
  --addon-name vpc-cni --query 'addon.health.issues'

# STEP 8: Update control plane (this is the critical step)
aws eks update-cluster-version --name <cluster-name> \
  --kubernetes-version 1.28

# STEP 9: Monitor control plane upgrade progress
aws eks describe-cluster --name <cluster-name> \
  --query 'cluster.status' --output text
# Shows: UPDATING -> ACTIVE

# STEP 10: Check upgrade history
aws eks describe-cluster --name <cluster-name> \
  --query 'cluster.platformVersion'

# STEP 11: Verify cluster connectivity during upgrade
kubectl cluster-info
# May timeout temporarily during upgrade

# STEP 12: Verify all control plane components running
kubectl get componentstatuses
# Shows: scheduler, controller-manager status
```

#### EKS Node Group Upgrade

```bash
# STEP 1: Check node group upgrade availability
aws eks describe-nodegroup --cluster-name <cluster-name> \
  --nodegroup-name <nodegroup-name> \
  --query 'nodegroup.version'

# STEP 2: Get latest EKS-optimized AMI for version
aws ssm get-parameters \
  --names /aws/service/eks/optimized-ami/1.28/amazon-linux-2/recommended/image_id \
  --region <region> --query 'Parameters[0].Value' --output text

# STEP 3: Update node group to new version (managed rolling update)
aws eks update-nodegroup-version --cluster-name <cluster-name> \
  --nodegroup-name <nodegroup-name>

# STEP 4: Monitor node group upgrade
# Nodes will terminate and recreate; pods will be rescheduled
aws eks describe-nodegroup --cluster-name <cluster-name> \
  --nodegroup-name <nodegroup-name> \
  --query 'nodegroup.status'

# STEP 5: Watch pod rescheduling during upgrade
watch -n 5 'kubectl get pods -A | grep -E "Pending|Terminating" | wc -l'

# STEP 6: Check node readiness after update
kubectl get nodes -o wide
# All nodes should be Ready

# STEP 7: Verify kubelet version on nodes
kubectl get nodes -o json | jq '.items[].status.nodeInfo.kubeletVersion' | sort | uniq

# STEP 8: Check for nodes in upgrade
kubectl get nodes --show-labels | grep managed-node-group

# STEP 9: Verify workload replicas active during upgrade
kubectl get deployment -A --no-headers | awk '{print $2, $4}' | awk '$2 < $1 {print "UNDERREPLICATED: " $0}'

# STEP 10: Wait for all nodes to be Ready
kubectl wait --for=condition=Ready node --all --timeout=10m

# STEP 11: Update remaining node groups if any
# Repeat steps 3-10 for each node group

# STEP 12: Verify cluster fully upgraded
aws eks describe-cluster --name <cluster-name> \
  --query 'cluster.version'
# Should match target version
```

#### EKS Addon Upgrade and Management

```bash
# STEP 1: List all installed addons
aws eks list-addons --cluster-name <cluster-name>

# STEP 2: Check addon versions
aws eks describe-addon --cluster-name <cluster-name> --addon-name vpc-cni \
  --query 'addon.addonVersion'

# STEP 3: Check addon health
aws eks describe-addon --cluster-name <cluster-name> \
  --addon-name vpc-cni --query 'addon.health'

# STEP 4: Get available addon versions for target K8s version
aws eks describe-addon-versions --addon-name vpc-cni \
  --kubernetes-version 1.28 --query 'addonVersions[].addonVersion'

# STEP 5: Update addon (usually required during K8s upgrade)
aws eks update-addon --cluster-name <cluster-name> \
  --addon-name vpc-cni --addon-version <new-version>

# STEP 6: Monitor addon update
aws eks describe-addon --cluster-name <cluster-name> \
  --addon-name vpc-cni --query 'addon.addonVersion'

# STEP 7: Check addon service account RBAC
kubectl get clusterrole -n kube-system | grep cni
kubectl get clusterrolebinding -n kube-system | grep cni

# STEP 8: Verify addon pods are running
kubectl get pods -n kube-system -l app=aws-node
# Shows: CNI pods on each node

# STEP 9: Check addon container image
kubectl get pods -n kube-system -l app=aws-node -o jsonpath='{.items[0].spec.containers[0].image}'

# STEP 10: Review addon release notes
# Visit: https://github.com/aws/amazon-vpc-cni-k8s/releases

# STEP 11: Rollback addon if needed
aws eks update-addon --cluster-name <cluster-name> \
  --addon-name vpc-cni --addon-version <previous-version>

# STEP 12: Validate addon functionality post-update
# Test: Pod IP assignment, security group/pod ENI attachment
kubectl run test-pod --image=busybox -- sleep 300
kubectl get pods -o wide
```

#### Commands to NEVER use in production

```bash
# ❌ NEVER: Skip multiple Kubernetes versions (1.26 -> 1.29)
#    Unsupported; must upgrade sequentially
# ❌ NEVER: Upgrade control plane without updating nodes first (or at same time)
#    Nodes incompatible; pods may fail to schedule
# ❌ NEVER: Force drain nodes with --force flag
#    May cause pod data loss; remove --force and fix PDBs
# ❌ NEVER: Upgrade during peak traffic
#    Pod rescheduling may cause temporary service degradation
```

---

## EKS Cluster Debugging and Troubleshooting

### Scenario: Diagnosing EKS Node Launch Failures

**Prerequisites**: Node group creation failing, nodes not joining cluster  
**Common Causes**: IAM role missing permissions, security group misconfigured, subnet issues, AMI incompatibility

#### EKS Node Launch Troubleshooting

```bash
# STEP 1: Check node group status
aws eks describe-nodegroup --cluster-name <cluster-name> \
  --nodegroup-name <nodegroup-name> --query 'nodegroup.status'

# STEP 2: Get node group error details
aws eks describe-nodegroup --cluster-name <cluster-name> \
  --nodegroup-name <nodegroup-name> --query 'nodegroup.health'

# STEP 3: Check EC2 instances in node group
aws ec2 describe-instances --filters \
  Name=tag:eks:nodegroup-name,Values=<nodegroup-name> \
  --query 'Reservations[].Instances[].[InstanceId,State.Name,LaunchTime]'

# STEP 4: Get instance launch error (if stuck)
aws ec2 describe-instances --instance-ids <instance-id> \
  --query 'Reservations[0].Instances[0].StateTransitionReason'

# STEP 5: Check instance IAM role
aws ec2 describe-instances --instance-ids <instance-id> \
  --query 'Reservations[0].Instances[0].IamInstanceProfile'

# STEP 6: Verify IAM role has required policies
aws iam list-attached-role-policies --role-name eks-node-role

# STEP 7: Check security group rules
aws ec2 describe-security-groups --group-ids <node-sg-id> \
  --query 'SecurityGroups[0].IpPermissions'

# STEP 8: Verify security group allows cluster communication
# Inbound: port 443 from cluster security group
aws ec2 describe-security-group-rules --filters \
  Name=group-id,Values=<node-sg-id> \
  Name=cidr,Values=0.0.0.0/0

# STEP 9: Check subnet availability
aws ec2 describe-subnets --subnet-ids <subnet-id> \
  --query 'Subnets[0].[AvailabilityZone,AvailableIpAddressCount]'

# STEP 10: Check for IP address exhaustion in subnet
# If available IPs < number of nodes, allocation fails
aws ec2 describe-subnets --subnet-ids <subnet-id> \
  --query 'Subnets[0].AvailableIpAddressCount'

# STEP 11: Verify AMI is available in region
aws ec2 describe-images --image-ids ami-xxxxxxxx \
  --query 'Images[0].State'

# STEP 12: Check CloudWatch logs for node launch errors
aws logs tail /aws/eks/<cluster-name>/cluster --follow
# May show: bootstrap script failures, IAM errors
```

#### EKS Nodes Not Ready Troubleshooting

```bash
# STEP 1: Check node status in Kubernetes
kubectl get nodes -o wide

# STEP 2: Describe problematic node
kubectl describe node <node-name>
# Shows: Conditions, capacity, allocated resources

# STEP 3: Check node conditions
kubectl get nodes -o json | jq '.items[].status.conditions'
# Look for: Ready, DiskPressure, MemoryPressure

# STEP 4: Check kubelet status on node via Systems Manager
aws ssm start-session --target <instance-id>
# Inside session: sudo systemctl status kubelet

# STEP 5: Check kubelet logs
aws ssm start-session --target <instance-id>
# Inside: sudo journalctl -u kubelet -f --lines=50

# STEP 6: Verify CNI plugin is running on node
kubectl get pods -n kube-system -o wide | grep aws-node
# Should have pod on each node

# STEP 7: Check ENI attachment on EC2 instance
aws ec2 describe-network-interfaces \
  --filters Name=attachment.instance-id,Values=<instance-id>
# Shows: ENIs and IP addresses

# STEP 8: Verify node can reach Kubernetes API
aws ssm start-session --target <instance-id>
# Inside: curl -k https://<cluster-endpoint>:443/api/v1/namespaces

# STEP 9: Check container runtime status
aws ssm start-session --target <instance-id>
# Inside: sudo systemctl status containerd

# STEP 10: Check disk space on node
aws ssm start-session --target <instance-id>
# Inside: df -h | grep -E "dev/xvda|Filesystem"

# STEP 11: Check node resource reservation
kubectl get nodes -o json | jq '.items[] | {name: .metadata.name, allocatable: .status.allocatable, reserved: .status.capacity}'

# STEP 12: Force node health check to refresh
kubectl delete node <node-name>
# Triggers recreate; only if node is truly unhealthy
```

#### EKS Pod Networking Troubleshooting

```bash
# STEP 1: Check if pod got IP address
kubectl get pods -n <namespace> -o wide
# Shows: Pod IP, node assignment

# STEP 2: Check CNI plugin logs
kubectl logs -n kube-system -l k8s-app=aws-node --tail=50

# STEP 3: Verify ENI resources available
# Each node has limited ENI slots; pods use secondary IPs
aws ec2 describe-instances --instance-ids <instance-id> \
  --query 'Reservations[0].Instances[0].NetworkInterfaces | length(@)'

# STEP 4: Check pod IP address allocation
kubectl exec -it <pod> -- ip addr show
# Shows: Pod's eth0 IP address

# STEP 5: Test pod-to-pod connectivity
# Pod A to Pod B
kubectl exec -it <pod-a> -- ping <pod-b-ip>

# STEP 6: Test pod to external connectivity
kubectl exec -it <pod> -- ping 8.8.8.8

# STEP 7: Check security group for pods
# Pods use node security group for networking
aws ec2 describe-security-group-rules --filters \
  Name=group-id,Values=<node-sg-id>

# STEP 8: Check VPC CNI MTU (1500 standard)
kubectl exec -it <pod> -- ip link show eth0 | grep mtu

# STEP 9: Test DNS resolution from pod
kubectl exec -it <pod> -- nslookup kubernetes.default
# Should resolve to service IP

# STEP 10: Verify service DNS from pod
kubectl exec -it <pod> -- nslookup <service-name>.<namespace>.svc.cluster.local

# STEP 11: Check network policies
kubectl get networkpolicies -n <namespace>
# May block pod traffic

# STEP 12: Verify VPC has DNS enabled
aws ec2 describe-vpc-attribute --vpc-id <vpc-id> \
  --attribute enableDnsHostnames
```

#### EKS Control Plane API Availability Issues

```bash
# STEP 1: Check cluster health
aws eks describe-cluster --name <cluster-name> \
  --query 'cluster.status'

# STEP 2: Test cluster API connectivity
kubectl cluster-info

# STEP 3: Check CloudWatch metrics for API server
aws cloudwatch get-metric-statistics --namespace AWS/EKS \
  --metric-name ClusterNodeCount --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) --period 300 --statistics Average

# STEP 4: Check for control plane API throttling
# If many API calls, API may be throttled
kubectl top nodes

# STEP 5: Review recent API server events
kubectl get events -A --sort-by='.lastTimestamp' | tail -20

# STEP 6: Check API audit logs in CloudWatch
aws logs tail /aws/eks/<cluster-name>/cluster --follow | grep -i "forbidden\|error"

# STEP 7: Verify cluster endpoint accessibility
curl -k --max-time 5 https://$(aws eks describe-cluster --name <cluster-name> --query 'cluster.endpoint' --output text | cut -d'/' -f3)

# STEP 8: Check cluster security group ingress rules
aws ec2 describe-security-groups --group-ids <cluster-sg-id> \
  --query 'SecurityGroups[0].IpPermissions' | grep -i 443

# STEP 9: Verify kubeconfig is valid
kubectl auth can-i create pods
# If fails: kubeconfig issue

# STEP 10: Check for authentication issues
kubectl get pods --all-namespaces 2>&1 | grep -i "unauthorized\|forbidden"

# STEP 11: Verify IAM permissions for current user
aws iam get-user

# STEP 12: Check for DNS resolution of cluster endpoint
nslookup $(aws eks describe-cluster --name <cluster-name> --query 'cluster.endpoint' --output text | cut -d'/' -f3)
```

#### EKS Storage Troubleshooting

```bash
# STEP 1: Check PVC status
kubectl get pvc -n <namespace>
# Should show: Bound

# STEP 2: Describe PVC for binding errors
kubectl describe pvc <pvc-name> -n <namespace>

# STEP 3: Check PV status
kubectl get pv

# STEP 4: Check EBS CSI driver status
kubectl get daemonset -n kube-system ebs-csi-node

# STEP 5: Check EBS CSI driver logs
kubectl logs -n kube-system -l app=ebs-csi-controller --tail=50

# STEP 6: Verify EBS volume was created
aws ec2 describe-volumes --filters Name=tag:kubernetes.io/cluster/<cluster-name>,Values=owned \
  --query 'Volumes[*].[VolumeId,State,Size]'

# STEP 7: Check volume attachment to node
aws ec2 describe-volumes --volume-ids <vol-id> \
  --query 'Volumes[0].Attachments'

# STEP 8: Check storage class configuration
kubectl get storageclass
kubectl describe storageclass <name>

# STEP 9: Verify EBS CSI driver IAM permissions
aws iam get-role-policy --role-name <ebs-csi-role> --policy-name <policy-name>

# STEP 10: Check pod mount status
kubectl exec -it <pod> -- mount | grep ebs

# STEP 11: Check disk usage in pod
kubectl exec -it <pod> -- df -h /data

# STEP 12: Verify volume encryption settings
aws ec2 describe-volumes --volume-ids <vol-id> \
  --query 'Volumes[0].Encrypted'
```

#### EKS Autoscaling and Cluster Capacity Issues

```bash
# STEP 1: Check Cluster Autoscaler deployment
kubectl get deployment -n kube-system cluster-autoscaler 2>/dev/null || \
  echo "Karpenter or other scaler in use"

# STEP 2: Check for pending pods (indicates capacity issue)
kubectl get pods -A --field-selector=status.phase=Pending

# STEP 3: Check node group desired vs current size
aws eks describe-nodegroup --cluster-name <cluster-name> \
  --nodegroup-name <nodegroup-name> \
  --query 'nodegroup.scalingConfig'

# STEP 4: Check node group status
aws eks describe-nodegroup --cluster-name <cluster-name> \
  --nodegroup-name <nodegroup-name> --query 'nodegroup.status'

# STEP 5: Check autoscaling group configuration
aws autoscaling describe-auto-scaling-groups \
  --filters Name=tag:eks:nodegroup-name,Values=<nodegroup-name>

# STEP 6: Check ASG target capacity
aws autoscaling describe-auto-scaling-groups \
  --filters Name=tag:eks:nodegroup-name,Values=<nodegroup-name> \
  --query 'AutoScalingGroups[0].[MinSize,MaxSize,DesiredCapacity]'

# STEP 7: Check ASG current instances
aws autoscaling describe-auto-scaling-groups \
  --filters Name=tag:eks:nodegroup-name,Values=<nodegroup-name> \
  --query 'AutoScalingGroups[0].Instances[].InstanceId'

# STEP 8: Check for failed autoscaling activities
aws autoscaling describe-scaling-activities \
  --auto-scaling-group-name <asg-name> --query 'Activities[-5:].StatusMessage'

# STEP 9: Check EC2 capacity availability
# Some instance types/AZs may be capacity-constrained
aws ec2 describe-spot-price-history --instance-types t3.medium \
  --start-time $(date -u -d '10 minutes ago' +%Y-%m-%dT%H:%M:%S)

# STEP 10: Check resource requests and limits on pods
kubectl get pods -A -o json | jq '.items[] | {name: .metadata.name, cpu: .spec.containers[].resources.requests.cpu, memory: .spec.containers[].resources.requests.memory}'

# STEP 11: Monitor cluster capacity over time
# Manual scaling if autoscaling insufficient
aws eks update-nodegroup-config --cluster-name <cluster-name> \
  --nodegroup-name <nodegroup-name> \
  --scaling-config minSize=2,maxSize=20,desiredSize=5

# STEP 12: Use Karpenter for advanced autoscaling
# Superior to Cluster Autoscaler; consolidates unused nodes
kubectl apply -f karpenter-provisioner.yaml
```

#### Commands to NEVER use in production

```bash
# ❌ NEVER: kubectl drain <node> --force --ignore-daemonsets
#    May cause pod data loss; may hang indefinitely
# ❌ NEVER: Manually modify security groups on EKS nodes
#    May break node-to-control-plane communication
# ❌ NEVER: Delete node group without waiting for drain completion
#    Pods terminated abruptly; data loss potential
# ❌ NEVER: Modify kubelet configuration directly on nodes
#    Changes lost after node replacement; use nodegroup UserData instead
```

---

## EKS Cluster Monitoring and Diagnostics

### Scenario: Comprehensive EKS Cluster Health Check

**Prerequisites**: Cluster operational, metrics-server running, CloudWatch configured  
**Common Causes**: Resource exhaustion, unhealthy nodes, high API load, misconfigured monitoring

#### EKS Cluster Health Diagnostics

```bash
# STEP 1: Overall cluster status
aws eks describe-cluster --name <cluster-name> \
  --query 'cluster.status' --output text

# STEP 2: Control plane version and platform version
aws eks describe-cluster --name <cluster-name> \
  --query 'cluster.[version,platformVersion]'

# STEP 3: Node count and status
kubectl get nodes --output=custom-columns=NAME:.metadata.name,STATUS:.status.conditions[-1].type,READY:.status.conditions[-1].status

# STEP 4: Nodes with issues
kubectl get nodes -o json | jq '.items[] | select(.status.conditions[] | select(.status=="False")) | .metadata.name'

# STEP 5: Pod distribution across nodes
kubectl get pods -A -o wide | awk '{print $7}' | sort | uniq -c | sort -rn

# STEP 6: Resource utilization
kubectl top nodes
kubectl top pods -A --sort-by=memory | head -20

# STEP 7: Critical workload status
kubectl get deployment -A -o wide | awk '$4 != $5 {print}'
# Shows: Deployments with replicas != desired

# STEP 8: Pending pods
kubectl get pods -A --field-selector=status.phase=Pending

# STEP 9: Failed pods
kubectl get pods -A --field-selector=status.phase=Failed

# STEP 10: Service and endpoint status
kubectl get svc -A -o wide
kubectl get ep -A | grep -v addresses

# STEP 11: Persistent volume status
kubectl get pvc -A | grep -v Bound
kubectl get pv | grep -v Bound

# STEP 12: System namespace pod health
kubectl get pods -n kube-system
# All should be Running
```

#### EKS Monitoring and Alerting Setup

```bash
# STEP 1: Enable Container Insights for EKS
aws eks update-cluster-config --name <cluster-name> \
  --logging '{"clusterLogging":[{"enabled":true,"types":["api","audit","authenticator","controllerManager","scheduler"]}]}'

# STEP 2: Create IAM role for CloudWatch Logs
aws iam create-role --role-name eks-cloudwatch-logs \
  --assume-role-policy-document '{...}'

# STEP 3: Install Container Insights monitoring
kubectl apply -f https://raw.githubusercontent.com/aws-samples/amazon-cloudwatch-container-insights/latest/k8s-deployment-manifest-templates/deployment-mode/daemonset/container-insights-monitoring/quickstart/cwagent-fluentd-quickstart.yaml

# STEP 4: Verify CloudWatch agent running
kubectl get daemonset -n amazon-cloudwatch

# STEP 5: Check CloudWatch log groups
aws logs describe-log-groups --log-group-name-prefix /aws/containerinsights/<cluster-name>

# STEP 6: Create CloudWatch dashboard for cluster
aws cloudwatch put-dashboard --dashboard-name eks-<cluster-name> \
  --dashboard-body file://dashboard.json

# STEP 7: Set up node CPU utilization alarm
aws cloudwatch put-metric-alarm --alarm-name eks-node-cpu-high \
  --alarm-actions arn:aws:sns:region:account:topic-name \
  --metric-name CPUUtilization --namespace AWS/EC2 --statistic Average \
  --period 300 --threshold 80 --comparison-operator GreaterThanThreshold

# STEP 8: Set up node memory pressure alarm
aws cloudwatch put-metric-alarm --alarm-name eks-node-memory \
  --metric-name MemoryUtilization --statistic Average \
  --threshold 85 --comparison-operator GreaterThanThreshold

# STEP 9: Set up pod pending alarm
# Custom metric from scripting

# STEP 10: Enable detailed monitoring for nodes
aws ec2 monitor-instances --instance-ids <instance-id>

# STEP 11: Create log insights queries for API latency
# Query: fields @timestamp, @duration | stats avg(@duration), max(@duration) by bin(5m)

# STEP 12: Set up SNS notifications for alarms
aws sns create-topic --name eks-alerts
aws sns subscribe --topic-arn <topic-arn> --protocol email --notification-endpoint <email>
```

#### EKS Disaster Recovery and Backup

```bash
# STEP 1: Backup cluster configuration
kubectl get all -A -o yaml > cluster-full-backup-$(date +%Y%m%d).yaml

# STEP 2: Backup persistent volumes
# Use Velero for automated backups: https://velero.io
helm repo add velero https://vmware-tanzu.github.io/helm-charts
helm install velero velero/velero \
  --namespace velero --create-namespace \
  --values values.yaml

# STEP 3: Create velero backup schedule
velero schedule create weekly-backup --schedule="0 2 * * 0"

# STEP 4: Backup EBS volumes directly
# For critical data, snapshot volumes:
aws ec2 create-snapshot --volume-id <vol-id> --description "Weekly backup"

# STEP 5: Verify backup completion
velero backup get
kubectl get backups -n velero

# STEP 6: Document cluster configuration
# DNS endpoints, security groups, IAM roles, VPC config
aws eks describe-cluster --name <cluster-name> > cluster-config.json

# STEP 7: Create disaster recovery runbook
# Document: recovery procedures, RTO, RPO requirements

# STEP 8: Test cluster restoration procedure
# In staging: velero restore create test-restore --from-backup <backup-name>

# STEP 9: Backup external resources
# Load balancer configs, RDS databases, etc.

# STEP 10: Monitor backup job status
watch -n 30 'velero backup logs $(velero backup get --max=1 -o json | jq -r ".items[0].metadata.name")'

# STEP 11: Verify backup integrity periodically
# Attempt restore in dev environment

# STEP 12: Document backup location and access
# S3 bucket where backups stored, encryption keys, IAM access
```

#### Commands to NEVER use in production

```bash
# ❌ NEVER: kubectl delete all --all (across all namespaces)
#    Deletes entire cluster; disaster
# ❌ NEVER: Disable cluster logging during issue investigation
#    Hides root cause; violates compliance
# ❌ NEVER: Skip backup verification testing
#    Backups may be corrupted; only discovered during restore
# ❌ NEVER: Use default CloudWatch retention (infinite)
#    Logs grow unbounded; costs increase indefinitely
```

---

## EKS Performance Tuning and Optimization

### Scenario: Optimizing EKS for Performance and Cost

**Prerequisites**: Cluster running, workloads identified, performance baselines established  
**Common Causes**: Over-provisioned nodes, inefficient workload placement, high inter-pod latency

#### EKS Performance Analysis

```bash
# STEP 1: Analyze pod resource utilization
kubectl top pods -A --sort-by=cpu | head -20
kubectl top pods -A --sort-by=memory | head -20

# STEP 2: Check for resource over-provisioning
# Compare: limits vs actual utilization
kubectl get pods -A -o json | jq '.items[] | {name: .metadata.name, cpu_limit: .spec.containers[].resources.limits.cpu, cpu_request: .spec.containers[].resources.requests.cpu}'

# STEP 3: Check pod eviction risk
# Pods with memory requests but no limits may be evicted under pressure
kubectl get pods -A -o json | jq '.items[] | select(.spec.containers[].resources.requests.memory and .spec.containers[].resources.limits.memory == null) | .metadata.name'

# STEP 4: Analyze network latency
# Deploy iperf/netperf to measure inter-pod throughput

# STEP 5: Check for noisy neighbor problem
# High CPU pod affecting others on same node
kubectl top nodes --all-namespaces | sort -k3 -r

# STEP 6: Analyze API server latency
# Monitor: kubectl apply times, watch latency
kubectl get apiservicelist

# STEP 7: Check node resource fragmentation
# Many small pods; few large pod slots available
kubectl describe nodes | grep -A 5 "Allocated resources"

# STEP 8: Verify node instance type sizing
# Right-sizing based on workload requirements
aws ec2 describe-instances --instance-ids <instance-id> \
  --query 'Reservations[0].Instances[0].InstanceType'

# STEP 9: Check for pod anti-affinity bottlenecks
# May prevent scaling if replicas constrained to specific nodes
kubectl get pods -A -o json | jq '.items[] | select(.spec.affinity.podAntiAffinity) | .metadata.name'

# STEP 10: Monitor API call rate and latency
# High: may indicate misconfigured controllers or debug tooling
kubectl top nodes

# STEP 11: Check container startup time
# Slow: may indicate large image size or slow app initialization
kubectl get pods -A -o json | jq '.items[].status.containerStatuses[].state'

# STEP 12: Analyze kubelet eviction thresholds
aws ssm start-session --target <instance-id>
# Inside: grep eviction-hard /etc/kubernetes/kubelet/kubelet-config.json
```

#### EKS Cost Optimization

```bash
# STEP 1: Analyze EC2 spend using Spot Instances
# Up to 90% savings vs On-Demand
aws ec2 describe-spot-price-history --instance-types t3.medium \
  --query 'SpotPriceHistory[0:5].SpotPrice'

# STEP 2: Configure mixed node group (On-Demand + Spot)
aws eks create-nodegroup \
  --cluster-name <cluster-name> \
  --nodegroup-name spot-nodes \
  --capacity-type spot \
  --instance-types t3.medium t3.large t3a.medium

# STEP 3: Use graviton instances (ARM-based, cheaper)
aws ec2 describe-instance-types --query 'InstanceTypes[?ProcessorInfo.SupportedArchitectures[?==`arm64`]].InstanceType'

# STEP 4: Implement right-sizing via autoscaling
# Reduce reserved capacity; improve utilization
kubectl autoscale deployment <name> --min=2 --max=10

# STEP 5: Use reserved instances for baseline capacity
# 30-40% savings for committed usage
aws ec2 describe-reserved-instances --filters Name=state,Values=active

# STEP 6: Configure pod disruption budgets for cost optimization
# Allows safe node consolidation
kubectl create pdb <name> --min-available=1 --selector app=web

# STEP 7: Implement namespace quotas to prevent runaway costs
kubectl create quota <quota-name> -n <namespace> --hard=requests.cpu=10,requests.memory=20Gi

# STEP 8: Analyze data transfer costs
# EKS egress to internet can be expensive; use VPC endpoints

# STEP 9: Use Fargate for bursty workloads (no node management)
aws eks create-fargate-profile --cluster-name <cluster> \
  --fargate-profile-name <profile> --selectors namespace=batch

# STEP 10: Implement multi-AZ cost awareness
# Some AZs cheaper than others
aws ec2 describe-spot-price-history --start-time <time> \
  --query 'SpotPriceHistory[].[AvailabilityZone,SpotPrice]' | sort -k2 -n

# STEP 11: Monitor unused EBS volumes
aws ec2 describe-volumes --filters Name=status,Values=available

# STEP 12: Right-size NAT Gateway usage
# Can be expensive; consolidate if possible
aws ec2 describe-nat-gateways --query 'NatGateways[].State'
```

#### Commands to NEVER use in production

```bash
# ❌ NEVER: Over-aggressively schedule pods without limits
#    Node OOM-kills workloads; unpredictable
# ❌ NEVER: Use all-Spot node group for stateful workloads
#    Node termination causes pod loss
# ❌ NEVER: Disable cluster autoscaling to save money
#    Cluster becomes capacity-constrained; degrades reliability
# ❌ NEVER: Set extremely high resource requests
#    Pod scheduling fails; cluster under-utilized
```

---

## Critical EKS Debugging Principles

### EKS Operations Best Practices

1. **Testing**: Always test upgrades in dev/staging first
2. **Logging**: Enable all control plane logs; audit trail essential
3. **Monitoring**: Set up CloudWatch/Container Insights before issues occur
4. **Backup**: Regular, tested backups mandatory
5. **RBAC**: Implement least-privilege AWS IAM roles
6. **Security**: Use security groups, network policies, pod security standards
7. **Capacity**: Plan for growth; autoscaling requires buffer
8. **Documentation**: Track manual changes; maintain runbooks
9. **Automation**: Infrastructure as Code (Terraform) for repeatability
10. **Communication**: Notify teams of maintenance; track incidents

### EKS Debugging Decision Tree

```
EKS Issue Encountered
│
├─ Cluster not accessible
│  └─ Check: Cluster status, API endpoint, kubeconfig, IAM permissions
│
├─ Nodes not joining
│  └─ Check: IAM role, security groups, subnet config, node logs
│
├─ Pods not scheduling
│  └─ Check: Node resources, affinity rules, PDBs, autoscaler status
│
├─ Pod networking broken
│  └─ Check: CNI plugin, security groups, DNS, network policies
│
├─ Upgrade failing
│  └─ Check: Node compatibility, addon versions, drain issues
│
└─ Performance degraded
   └─ Check: Resource utilization, API latency, inter-pod throughput
```

### EKS Incident Response Checklist

```
Incident Response:
- [ ] Assess severity and impact
- [ ] Notify on-call team
- [ ] Begin capturing logs and metrics
- [ ] Identify affected workloads/users
- [ ] Execute relevant diagnostic steps (from above scenarios)
- [ ] Implement immediate mitigation
- [ ] Document findings and actions taken
- [ ] Schedule post-incident review
- [ ] Update runbooks with new learnings
```

### Common EKS Issues Quick Reference

| Issue | Symptoms | Diagnosis | Fix |
|-------|----------|-----------|-----|
| Node NotReady | kubectl get nodes shows NotReady | kubectl describe node, check kubelet logs | Restart node or terminate for ASG replacement |
| PVC Pending | kubectl get pvc shows Pending | Check EBS CSI driver, volume creation | Verify IAM, subnet, volume limits |
| Pod Pending | Pods stuck in Pending | Check node capacity, resource requests | Scale nodes or reduce pod resource requests |
| Upgrade stuck | Control plane stuck in UPDATING | Check addon compatibility, events | Rollback or contact AWS Support |
| High API latency | kubectl commands slow | Check API server logs, request rate | Scale API server or reduce query volume |
| Network issues | Pods can't communicate | Check security groups, network policies, CNI | Verify CNI plugin status, update security rules |

### EKS Verification Commands Quick Reference

```bash
# Cluster health
aws eks describe-cluster --name <cluster> --query 'cluster.status'

# Node status
kubectl get nodes -o wide

# Pod distribution
kubectl get pods -A -o wide

# Resource utilization
kubectl top nodes && kubectl top pods -A

# Upgrade status
aws eks describe-cluster --name <cluster> --query 'cluster.[version,status]'

# Addon status
aws eks list-addons --cluster-name <cluster>

# Node group status
aws eks describe-nodegroup --cluster-name <cluster> --nodegroup-name <nodegroup>
```

### Documentation and References

**AWS EKS Official**
- Getting Started: https://docs.aws.amazon.com/eks/latest/userguide/getting-started.html
- Best Practices: https://docs.aws.amazon.com/eks/latest/userguide/best-practices.html
- Troubleshooting: https://docs.aws.amazon.com/eks/latest/userguide/troubleshooting.html

**EKS Add-ons**
- VPC CNI: https://github.com/aws/amazon-vpc-cni-k8s
- EBS CSI Driver: https://github.com/kubernetes-sigs/aws-ebs-csi-driver
- Load Balancer Controller: https://kubernetes-sigs.github.io/aws-load-balancer-controller/

**Kubernetes Upgrades**
- Release Notes: https://kubernetes.io/releases/
- Version Skew Policy: https://kubernetes.io/releases/version-skew-policy/

**Monitoring and Logging**
- Container Insights: https://docs.aws.amazon.com/AmazonCloudWatch/latest/containerinsights/
- CloudTrail: https://docs.aws.amazon.com/awscloudtrail/latest/userguide/

**Cost Optimization**
- EC2 Spot Instances: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-spot-instances.html
- AWS Fargate: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/what-is-fargate.html
- Reserved Instances: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-reserved-instances.html

---

**Last Updated**: January 2026  
**Platforms Covered**: AWS EKS (1.20 - 1.28+), EC2, VPC, IAM, CloudWatch  
**Severity Level**: Production Critical  
**Review Frequency**: Monthly (with Kubernetes release cycle)