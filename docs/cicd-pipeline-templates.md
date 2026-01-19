# CI/CD Pipeline Templates (Production-Ready, Copy/Paste)

> **Goal**: Quickly bootstrap pipelines for common stacks with sane defaults—caching, secrets handling, artifact promotion, and rollback hooks. Templates assume least-privilege, pinned actions/images, and guarded deployments.

---

## GitHub Actions (Container Build + Push + Deploy to Staging)

```yaml
name: build-and-deploy

on:
  push:
    branches: [ main ]

jobs:
  build:
    runs-on: ubuntu-22.04
    permissions:
      contents: read
      packages: write
      id-token: write  # for OIDC to cloud
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Set up QEMU (multi-arch)
        uses: docker/setup-qemu-action@v3
      - name: Set up Buildx
        uses: docker/setup-buildx-action@v3

      - name: Build and push image
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ghcr.io/your-org/app:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Sign image (cosign)
        run: cosign sign ghcr.io/your-org/app:${{ github.sha }}

  deploy-staging:
    needs: [build]
    runs-on: ubuntu-22.04
    environment: staging
    steps:
      - uses: actions/checkout@v4
      - uses: azure/setup-kubectl@v4
      - name: Render manifest with image SHA
        run: |
          kustomize edit set image app=ghcr.io/your-org/app:${GITHUB_SHA}
          kustomize build overlays/staging | kubectl apply -f -
      - name: Smoke test
        run: kubectl -n staging rollout status deploy/app --timeout=120s
```

---

## GitLab CI (Build, Test, Promote with Manual Prod Gate)

```yaml
stages: [lint, test, build, deploy_staging, promote_prod]

variables:
  DOCKER_TLS_CERTDIR: ""
  IMAGE: registry.gitlab.com/your-org/app:$CI_COMMIT_SHORT_SHA

lint:
  stage: lint
  image: python:3.11
  script:
    - pip install pre-commit
    - pre-commit run --all-files

test:
  stage: test
  image: python:3.11
  script:
    - pip install -r requirements.txt
    - pytest -q

build:
  stage: build
  image: docker:24
  services: [docker:24-dind]
  script:
    - docker build -t $IMAGE .
    - docker push $IMAGE

deploy_staging:
  stage: deploy_staging
  image: bitnami/kubectl:1.30
  script:
    - kubectl config use-context $STAGING_CONTEXT
    - kustomize edit set image app=$IMAGE
    - kustomize build overlays/staging | kubectl apply -f -
    - kubectl -n staging rollout status deploy/app --timeout=120s

promote_prod:
  stage: promote_prod
  when: manual
  allow_failure: false
  image: bitnami/kubectl:1.30
  script:
    - kubectl config use-context $PROD_CONTEXT
    - kustomize edit set image app=$IMAGE
    - kustomize build overlays/prod | kubectl apply -f -
    - kubectl -n prod rollout status deploy/app --timeout=180s
```

---

## Jenkins Declarative Pipeline (Blue/Green Toggle)

```groovy
pipeline {
  agent any
  environment {
    IMAGE = "ghcr.io/your-org/app:${env.GIT_COMMIT}"
    KUBE_CONTEXT = "staging"
  }
  stages {
    stage('Checkout') {
      steps { checkout scm }
    }
    stage('Build') {
      steps { sh "docker build -t ${IMAGE} ." }
    }
    stage('Test') {
      steps { sh "pytest -q" }
    }
    stage('Push') {
      steps { sh "docker push ${IMAGE}" }
    }
    stage('Deploy Blue') {
      steps {
        sh """
        kubectl config use-context ${KUBE_CONTEXT}
        kustomize edit set image app=${IMAGE}
        kustomize build overlays/blue | kubectl apply -f -
        kubectl -n staging rollout status deploy/app-blue --timeout=120s
        """
      }
    }
    stage('Flip Traffic') {
      steps {
        sh "kubectl -n staging patch svc app --type='json' -p='[{\"op\":\"replace\",\"path\":\"/spec/selector/color\",\"value\":\"blue\"}]'"
      }
    }
  }
}
```

---

## Argo Workflows (S3 Artifact, Fan-Out Tests)

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: app-ci-
spec:
  entrypoint: main
  templates:
  - name: main
    steps:
      - - name: build
          template: build-image
      - - name: tests
          template: run-tests
          withItems:
            - unit
            - integration
      - - name: upload
          template: upload-artifacts

  - name: build-image
    container:
      image: gcr.io/kaniko-project/executor:latest
      args: ["--dockerfile=Dockerfile", "--destination=ghcr.io/your-org/app:{{workflow.uid}}"]

  - name: run-tests
    inputs:
      parameters:
      - name: suite
    container:
      image: python:3.11
      command: [sh, -c]
      args: ["pytest -q tests/{{inputs.parameters.suite}}"]

  - name: upload-artifacts
    container:
      image: amazon/aws-cli
      command: [sh, -c]
      args: ["aws s3 cp reports/ s3://ci-artifacts/{{workflow.uid}}/ --recursive"]
```

---

## Tekton (Build + Promote)

```yaml
apiVersion: tekton.dev/v1
kind: Pipeline
metadata:
  name: build-promote
spec:
  params:
    - name: image
      default: ghcr.io/your-org/app
  tasks:
    - name: build
      taskRef:
        name: buildah
        kind: ClusterTask
      params:
        - name: IMAGE
          value: $(params.image):$(context.pipelineRun.uid)
    - name: deploy
      runAfter: [build]
      taskSpec:
        steps:
          - name: kubectl-apply
            image: bitnami/kubectl:1.30
            script: |
              kubectl config use-context staging
              kustomize edit set image app=$(params.image):$(context.pipelineRun.uid)
              kustomize build overlays/staging | kubectl apply -f -
              kubectl -n staging rollout status deploy/app --timeout=120s
```

---

### Production Guardrails to Copy Everywhere
- Timeouts + retries on fetch/build/push and kubectl rollouts.  
- Immutable images tagged with commit SHA and signed (cosign).  
- Manual approval for prod; separate credentials/contexts per env.  
- Rollback hook: keep previous image tag; `kubectl rollout undo` ready.  
- Caching: GHA cache or remote cache for docker buildx; Python deps via pip cache.  
- Secrets: use OIDC to cloud/vendor; avoid long-lived tokens.  
- Observability: emit logs + metrics for queue time, build time, deploy success.  
