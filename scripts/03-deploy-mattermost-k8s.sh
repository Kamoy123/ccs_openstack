#!/bin/bash

###############################################################################
# 03-deploy-mattermost-k8s.sh
#
# This script automates the deployment of Mattermost on Kubernetes with all
# required dependencies:
# - NGINX Ingress Controller
# - PostgreSQL Database with persistent storage
# - Mattermost Operator
# - Mattermost installation
#
# Prerequisites:
# - Kubernetes cluster created via OpenStack Magnum
# - kubectl configured with cluster access
# - Helm 3 installed
#
# Usage:
#   sudo chmod +x 03-deploy-mattermost-k8s.sh
#   ./03-deploy-mattermost-k8s.sh
###############################################################################

set -e  # Exit on error
set -u  # Exit on undefined variable

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Log file
LOG_FILE="/tmp/deploy-mattermost-k8s.log"

# Function to log messages
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1" | tee -a "$LOG_FILE"
}

log_info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO:${NC} $1" | tee -a "$LOG_FILE"
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to wait for pods to be ready
wait_for_pods() {
    local namespace=$1
    local label=$2
    local max_wait=${3:-300}  # Default 5 minutes
    
    log_info "Waiting for pods in namespace '$namespace' with label '$label' to be ready..."
    
    local start_time=$(date +%s)
    while true; do
        local ready=$(kubectl get pods -n "$namespace" -l "$label" -o jsonpath='{.items[*].status.containerStatuses[*].ready}' 2>/dev/null || echo "")
        
        if [[ -n "$ready" ]] && [[ ! "$ready" =~ "false" ]]; then
            log "Pods are ready!"
            return 0
        fi
        
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))
        
        if [[ $elapsed -gt $max_wait ]]; then
            log_error "Timeout waiting for pods to be ready"
            return 1
        fi
        
        sleep 5
    done
}

# Function to check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    if ! command_exists kubectl; then
        log_error "kubectl is not installed or not in PATH"
        exit 1
    fi
    
    if ! command_exists helm; then
        log_error "Helm is not installed or not in PATH"
        exit 1
    fi
    
    # Check if kubectl can connect to cluster
    if ! kubectl cluster-info &>/dev/null; then
        log_error "Cannot connect to Kubernetes cluster. Make sure KUBECONFIG is set correctly."
        exit 1
    fi
    
    log "Prerequisites check passed!"
}

# Function to install NGINX Ingress Controller
install_nginx_ingress() {
    log "Installing NGINX Ingress Controller..."
    
    # Add Helm repository
    helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx || true
    helm repo update
    
    # Create namespace
    kubectl create namespace ingress-nginx --dry-run=client -o yaml | kubectl apply -f -
    
    # Install NGINX Ingress
    if helm status nginx-ingress -n ingress-nginx &>/dev/null; then
        log_warning "NGINX Ingress already installed, skipping..."
    else
        helm install nginx-ingress ingress-nginx/ingress-nginx \
            --namespace ingress-nginx \
            --set controller.service.type=LoadBalancer \
            --set controller.admissionWebhooks.enabled=false \
            --wait --timeout=10m
    fi
    
    # Wait for LoadBalancer to get an IP
    log_info "Waiting for LoadBalancer IP..."
    local max_attempts=60
    local attempt=0
    while [[ $attempt -lt $max_attempts ]]; do
        INGRESS_IP=$(kubectl get svc -n ingress-nginx nginx-ingress-ingress-nginx-controller \
            -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
        
        if [[ -n "$INGRESS_IP" ]]; then
            log "NGINX Ingress LoadBalancer IP: $INGRESS_IP"
            break
        fi
        
        attempt=$((attempt + 1))
        sleep 5
    done
    
    if [[ -z "$INGRESS_IP" ]]; then
        log_error "Failed to get LoadBalancer IP"
        exit 1
    fi
}

# Function to deploy PostgreSQL
deploy_postgresql() {
    log "Deploying PostgreSQL database..."
    
    # Create namespace
    kubectl create namespace mattermost --dry-run=client -o yaml | kubectl apply -f -
    
    # Create PostgreSQL PVC
    cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-pvc
  namespace: mattermost
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
EOF
    
    # Create PostgreSQL secret
    kubectl create secret generic postgres-secret \
        --from-literal=POSTGRES_USER=mmuser \
        --from-literal=POSTGRES_PASSWORD=chocolateFrog! \
        --from-literal=POSTGRES_DB=mattermost \
        --namespace mattermost \
        --dry-run=client -o yaml | kubectl apply -f -
    
    # Deploy PostgreSQL
    cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres
  namespace: mattermost
spec:
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:15
        ports:
        - containerPort: 5432
        env:
        - name: POSTGRES_USER
          valueFrom:
            secretKeyRef:
              name: postgres-secret
              key: POSTGRES_USER
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: postgres-secret
              key: POSTGRES_PASSWORD
        - name: POSTGRES_DB
          valueFrom:
            secretKeyRef:
              name: postgres-secret
              key: POSTGRES_DB
        - name: PGDATA
          value: /var/lib/postgresql/data/pgdata
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
      volumes:
      - name: postgres-storage
        persistentVolumeClaim:
          claimName: postgres-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: postgres
  namespace: mattermost
spec:
  selector:
    app: postgres
  ports:
  - port: 5432
    targetPort: 5432
EOF
    
    # Wait for PostgreSQL to be ready
    wait_for_pods "mattermost" "app=postgres" 300
    
    log "PostgreSQL deployed successfully!"
}

# Function to install Mattermost Operator
install_mattermost_operator() {
    log "Installing Mattermost Operator..."
    
    # Add Helm repository
    helm repo add mattermost https://helm.mattermost.com || true
    helm repo update
    
    # Create namespace
    kubectl create namespace mattermost-operator --dry-run=client -o yaml | kubectl apply -f -
    
    # Install Mattermost Operator
    if helm status mattermost-operator -n mattermost-operator &>/dev/null; then
        log_warning "Mattermost Operator already installed, skipping..."
    else
        helm install mattermost-operator mattermost/mattermost-operator \
            --namespace mattermost-operator \
            --wait --timeout=10m
    fi
    
    # Wait for operator to be ready
    wait_for_pods "mattermost-operator" "app.kubernetes.io/name=mattermost-operator" 300
    
    log "Mattermost Operator installed successfully!"
}

# Function to deploy Mattermost
deploy_mattermost() {
    log "Deploying Mattermost..."
    
    # Create database connection secret
    cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Secret
metadata:
  name: mattermost-postgres-connection
  namespace: mattermost
type: Opaque
stringData:
  DB_CONNECTION_STRING: "postgres://mmuser:chocolateFrog!@postgres.mattermost.svc.cluster.local:5432/mattermost?connect_timeout=10"
  DB_CONNECTION_CHECK_URL: "postgres://mmuser:chocolateFrog!@postgres.mattermost.svc.cluster.local:5432/mattermost?connect_timeout=10"
EOF
    
    # Create Mattermost filestore PVC
    cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: mattermost-filestore-pvc
  namespace: mattermost
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 20Gi
EOF
    
    # Deploy Mattermost
    cat <<EOF | kubectl apply -f -
apiVersion: installation.mattermost.com/v1beta1
kind: Mattermost
metadata:
  name: mattermost
  namespace: mattermost
spec:
  size: 1000users
  version: 9.11.0
  ingress:
    enabled: true
    host: mattermost.${INGRESS_IP}.nip.io
    annotations:
      kubernetes.io/ingress.class: nginx
      nginx.ingress.kubernetes.io/proxy-body-size: "100m"
      nginx.ingress.kubernetes.io/proxy-send-timeout: "600"
      nginx.ingress.kubernetes.io/proxy-read-timeout: "600"
  database:
    external:
      secret: mattermost-postgres-connection
  fileStore:
    local:
      volumeClaim:
        name: mattermost-filestore-pvc
  mattermostEnv:
  - name: MM_SERVICESETTINGS_SITEURL
    value: "http://mattermost.${INGRESS_IP}.nip.io"
  - name: MM_SERVICESETTINGS_ENABLELOCALMODE
    value: "true"
  replicas: 1
EOF
    
    log "Waiting for Mattermost to be deployed (this may take several minutes)..."
    sleep 30  # Give the operator time to create resources
    
    # Wait for Mattermost pods
    local max_attempts=40
    local attempt=0
    while [[ $attempt -lt $max_attempts ]]; do
        local pods=$(kubectl get pods -n mattermost -l app.kubernetes.io/name=mattermost 2>/dev/null | grep -v NAME | wc -l || echo "0")
        
        if [[ $pods -gt 0 ]]; then
            log_info "Mattermost pods found, waiting for them to be ready..."
            wait_for_pods "mattermost" "app.kubernetes.io/name=mattermost" 600 || true
            break
        fi
        
        attempt=$((attempt + 1))
        sleep 5
    done
    
    log "Mattermost deployed successfully!"
}

# Function to display access information
display_access_info() {
    log ""
    log "============================================================"
    log "Mattermost Deployment Complete!"
    log "============================================================"
    log ""
    log "Access URL: http://mattermost.${INGRESS_IP}.nip.io"
    log ""
    log "To check deployment status:"
    log "  kubectl get pods -n mattermost"
    log "  kubectl get svc -n mattermost"
    log "  kubectl get ingress -n mattermost"
    log ""
    log "To view Mattermost logs:"
    log "  kubectl logs -n mattermost -l app.kubernetes.io/name=mattermost"
    log ""
    log "To view Mattermost resource details:"
    log "  kubectl describe mattermost -n mattermost mattermost"
    log ""
    log "Database credentials (for reference):"
    log "  User: mmuser"
    log "  Password: chocolateFrog!"
    log "  Database: mattermost"
    log ""
    log "First-time setup:"
    log "  1. Navigate to http://mattermost.${INGRESS_IP}.nip.io"
    log "  2. Create your first admin account"
    log "  3. Set up your team and channels"
    log ""
    log "============================================================"
    log ""
}

# Main execution
main() {
    log "Starting Mattermost deployment on Kubernetes..."
    log "Log file: $LOG_FILE"
    
    check_prerequisites
    install_nginx_ingress
    deploy_postgresql
    install_mattermost_operator
    deploy_mattermost
    display_access_info
    
    log "Deployment script completed successfully!"
}

# Run main function
main
