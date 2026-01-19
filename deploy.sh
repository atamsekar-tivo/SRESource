#!/bin/bash
# SRESource Flask Deployment Script
# This script helps deploy the Flask-based SRESource application

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}SRESource Flask Application - Deployment Helper${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

# Function to print success
success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Function to print error
error() {
    echo -e "${RED}✗ $1${NC}"
    exit 1
}

# Function to print info
info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Function to print warning
warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Check if Docker is installed
check_docker() {
    info "Checking Docker installation..."
    if command -v docker &> /dev/null; then
        success "Docker found: $(docker --version)"
    else
        error "Docker not installed. Please install Docker first."
    fi
}

# Check if Docker Compose is installed
check_docker_compose() {
    info "Checking Docker Compose installation..."
    if command -v docker-compose &> /dev/null; then
        success "Docker Compose found: $(docker-compose --version)"
    else
        warning "Docker Compose not found. You can still use 'docker compose' (v2)."
    fi
}

# Verify Flask application
verify_app() {
    info "Verifying Flask application..."
    
    if [ ! -f "app.py" ]; then
        error "app.py not found in current directory"
    fi
    success "app.py found"
    
    if [ ! -f "requirements.txt" ]; then
        error "requirements.txt not found"
    fi
    success "requirements.txt found"
    
    if [ ! -d "templates" ]; then
        error "templates directory not found"
    fi
    success "templates directory found"
    
    if [ ! -d "static" ]; then
        error "static directory not found"
    fi
    success "static directory found"
    
    if [ ! -d "docs" ]; then
        error "docs directory not found"
    fi
    success "docs directory found"
}

# Deploy options
show_menu() {
    echo ""
    echo -e "${BLUE}Select deployment option:${NC}"
    echo "  1) Local Development (Docker Compose)"
    echo "  2) Local Python (Direct)"
    echo "  3) Build Docker Image"
    echo "  4) Deploy to Kubernetes (kubectl)"
    echo "  5) Deploy with Helm"
    echo "  6) Verify Installation"
    echo "  7) Exit"
    echo ""
}

# Deploy with Docker Compose
deploy_docker_compose() {
    info "Starting with Docker Compose..."
    
    if [ ! -f "docker-compose.yml" ]; then
        error "docker-compose.yml not found"
    fi
    
    warning "Building Docker image (this may take a few minutes)..."
    docker-compose build || error "Docker Compose build failed"
    
    success "Starting services..."
    docker-compose up -d || error "Failed to start services"
    
    info "Waiting for application to start..."
    sleep 3
    
    # Check health
    if curl -f http://localhost:8080/ > /dev/null 2>&1; then
        success "Application is running!"
        echo ""
        echo -e "${GREEN}Access the application at: ${BLUE}http://localhost:8080${NC}"
        echo ""
        echo "Common commands:"
        echo "  View logs:      docker-compose logs -f sresource"
        echo "  Stop:           docker-compose down"
        echo "  Restart:        docker-compose restart"
    else
        warning "Application may still be starting. Check with: docker-compose logs sresource"
    fi
}

# Deploy with Python directly
deploy_python() {
    info "Setting up Python environment..."
    
    # Check Python version
    if ! command -v python3 &> /dev/null; then
        error "Python 3 not found. Please install Python 3.9+"
    fi
    
    info "Python version: $(python3 --version)"
    
    # Create virtual environment if needed
    if [ ! -d "venv" ]; then
        info "Creating virtual environment..."
        python3 -m venv venv || error "Failed to create virtual environment"
        success "Virtual environment created"
    fi
    
    # Activate and install
    info "Installing dependencies..."
    source venv/bin/activate
    pip install -r requirements.txt || error "Failed to install dependencies"
    success "Dependencies installed"
    
    # Run Flask
    info "Starting Flask application..."
    echo ""
    warning "Starting Flask dev server on http://localhost:5000"
    warning "Press Ctrl+C to stop"
    echo ""
    
    python app.py
}

# Build Docker image
build_docker_image() {
    info "Building Docker image..."
    
    if [ ! -f "Dockerfile" ]; then
        error "Dockerfile not found"
    fi
    
    read -p "Enter image name (default: sresource): " IMAGE_NAME
    IMAGE_NAME=${IMAGE_NAME:-sresource}
    
    read -p "Enter image tag (default: latest): " IMAGE_TAG
    IMAGE_TAG=${IMAGE_TAG:-latest}
    
    FULL_IMAGE="$IMAGE_NAME:$IMAGE_TAG"
    
    warning "Building image: $FULL_IMAGE (this may take a few minutes)..."
    docker build -t "$FULL_IMAGE" . || error "Docker build failed"
    
    success "Docker image built successfully: $FULL_IMAGE"
    
    echo ""
    echo "Next steps:"
    echo "  1. Run locally:    docker run -p 8080:8080 $FULL_IMAGE"
    echo "  2. Push to registry: docker tag $FULL_IMAGE yourregistry/$FULL_IMAGE"
    echo "                       docker push yourregistry/$FULL_IMAGE"
}

# Deploy to Kubernetes
deploy_kubernetes() {
    info "Deploying to Kubernetes..."
    
    if ! command -v kubectl &> /dev/null; then
        error "kubectl not found. Please install kubectl."
    fi
    
    # Check cluster connection
    if ! kubectl cluster-info &> /dev/null; then
        error "Cannot connect to Kubernetes cluster. Check your kubeconfig."
    fi
    
    success "Connected to Kubernetes cluster"
    
    if [ ! -f "kubernetes/deployment.yaml" ]; then
        error "kubernetes/deployment.yaml not found"
    fi
    
    info "Applying Kubernetes manifests..."
    kubectl apply -f kubernetes/ || error "Failed to apply Kubernetes manifests"
    
    success "Kubernetes manifests applied"
    
    echo ""
    echo "Deployment status:"
    kubectl get deployments -l app=sresource
    echo ""
    echo "Next steps:"
    echo "  1. Check pods:        kubectl get pods -l app=sresource"
    echo "  2. View logs:         kubectl logs -f -l app=sresource"
    echo "  3. Port forward:      kubectl port-forward svc/sresource 8080:80"
    echo "  4. Scale replicas:    kubectl scale deployment sresource --replicas=3"
}

# Deploy with Helm
deploy_helm() {
    info "Deploying with Helm..."
    
    if ! command -v helm &> /dev/null; then
        error "Helm not found. Please install Helm."
    fi
    
    success "Helm found: $(helm version --short)"
    
    if [ ! -f "helm/sresource/Chart.yaml" ]; then
        error "helm/sresource/Chart.yaml not found"
    fi
    
    read -p "Enter release name (default: sresource): " RELEASE_NAME
    RELEASE_NAME=${RELEASE_NAME:-sresource}
    
    read -p "Enter namespace (default: default): " NAMESPACE
    NAMESPACE=${NAMESPACE:-default}
    
    info "Installing Helm chart..."
    helm install "$RELEASE_NAME" ./helm/sresource \
        --namespace "$NAMESPACE" \
        --create-namespace || error "Failed to install Helm chart"
    
    success "Helm chart installed successfully"
    
    echo ""
    echo "Release status:"
    helm status "$RELEASE_NAME" -n "$NAMESPACE"
    echo ""
    echo "Next steps:"
    echo "  1. Check pods:        kubectl get pods -n $NAMESPACE"
    echo "  2. View logs:         kubectl logs -f -n $NAMESPACE -l app=sresource"
    echo "  3. Upgrade:           helm upgrade $RELEASE_NAME ./helm/sresource -n $NAMESPACE"
    echo "  4. Uninstall:         helm uninstall $RELEASE_NAME -n $NAMESPACE"
}

# Verify installation
verify_installation() {
    info "Verifying installation..."
    echo ""
    
    # Check Python dependencies
    info "Checking Python dependencies..."
    if command -v python3 &> /dev/null; then
        python3 -m pip list | grep -E "Flask|Markdown|Werkzeug|gunicorn" || warning "Some dependencies may not be installed"
    fi
    
    # Check Docker
    if command -v docker &> /dev/null; then
        info "Docker status: $(docker ps -q | wc -l) containers running"
        success "Docker is available"
    else
        warning "Docker not installed"
    fi
    
    # Check Kubernetes
    if command -v kubectl &> /dev/null; then
        if kubectl cluster-info &> /dev/null; then
            CONTEXT=$(kubectl config current-context)
            success "Kubernetes cluster: $CONTEXT"
            kubectl get nodes --no-headers | wc -l | xargs echo "Number of nodes:"
        else
            warning "kubectl found but cannot connect to cluster"
        fi
    fi
    
    # Check Helm
    if command -v helm &> /dev/null; then
        success "Helm is available"
    fi
    
    # Check application files
    info "Checking application files..."
    for file in app.py requirements.txt Dockerfile docker-compose.yml; do
        if [ -f "$file" ]; then
            success "$file found"
        else
            error "$file not found"
        fi
    done
    
    for dir in templates static docs kubernetes helm; do
        if [ -d "$dir" ]; then
            success "$dir directory found"
        else
            error "$dir directory not found"
        fi
    done
}

# Main loop
main() {
    check_docker
    check_docker_compose
    echo ""
    verify_app
    
    while true; do
        show_menu
        read -p "Enter option (1-7): " choice
        
        case $choice in
            1)
                deploy_docker_compose
                ;;
            2)
                deploy_python
                ;;
            3)
                build_docker_image
                ;;
            4)
                deploy_kubernetes
                ;;
            5)
                deploy_helm
                ;;
            6)
                verify_installation
                ;;
            7)
                echo -e "${BLUE}Goodbye!${NC}"
                exit 0
                ;;
            *)
                error "Invalid option. Please try again."
                ;;
        esac
        
        read -p "Press Enter to continue..."
    done
}

# Run main function
main
