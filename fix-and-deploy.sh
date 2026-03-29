#!/bin/bash
# Quick fix and deployment script for SRESource pods

set -e

echo "🔧 SRESource Pod Fix and Deployment Script"
echo "=========================================="

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker."
    exit 1
fi

# Build the new image
echo "📦 Building Docker image..."
docker build -t sresource:latest .

echo "✅ Docker image built successfully"

# If user wants to test locally with docker-compose
if command -v docker-compose &> /dev/null; then
    echo ""
    read -p "🐳 Do you want to test with docker-compose? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🚀 Starting services with docker-compose..."
        docker-compose up -d
        echo "✅ Services started"
        echo ""
        echo "Testing the application..."
        sleep 5
        
        if curl -s http://localhost:8080/ > /dev/null; then
            echo "✅ Homepage is accessible"
        else
            echo "❌ Homepage is not accessible"
            docker-compose logs sresource
            exit 1
        fi
        
        echo ""
        echo "📋 Local testing completed. Services are running at http://localhost:8080"
        read -p "Stop services? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            docker-compose down
            echo "✅ Services stopped"
        fi
    fi
fi

# Check if kubectl is available for Kubernetes deployment
if command -v kubectl &> /dev/null; then
    echo ""
    read -p "☸️  Do you want to deploy to Kubernetes? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🚀 Deploying to Kubernetes..."
        
        # Get current namespace
        NAMESPACE=$(kubectl config view --minify -o jsonpath='{.contexts[0].context.namespace}' 2>/dev/null || echo "default")
        echo "Using namespace: $NAMESPACE"
        
        # Delete existing pods to force restart
        echo "Deleting old pods..."
        kubectl delete pods -l app=sresource -n $NAMESPACE --ignore-not-found=true
        
        # Apply deployment
        echo "Applying deployment..."
        kubectl apply -f kubernetes/deployment.yaml -n $NAMESPACE
        
        echo "✅ Deployment applied"
        echo ""
        echo "⏳ Waiting for pods to be ready (max 60 seconds)..."
        
        # Wait for deployment
        if kubectl rollout status deployment/sresource -n $NAMESPACE --timeout=60s 2>/dev/null; then
            echo "✅ Pods are ready!"
            echo ""
            echo "📊 Pod status:"
            kubectl get pods -l app=sresource -n $NAMESPACE
            echo ""
            echo "📋 Recent logs:"
            kubectl logs -l app=sresource -n $NAMESPACE --tail=10 --all-containers=true
        else
            echo "⚠️  Pods did not become ready in time"
            echo "Running kubectl describe for debugging..."
            kubectl describe pods -l app=sresource -n $NAMESPACE
            exit 1
        fi
    fi
fi

echo ""
echo "🎉 SRESource pod fix completed!"
echo ""
echo "📚 Documentation: See POD_FIX_SUMMARY.md for details on what was fixed"
