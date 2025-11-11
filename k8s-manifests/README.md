# Kubernetes Manifests for Mattermost Deployment

This directory contains Kubernetes manifest files for deploying Mattermost with all required dependencies on your Kubernetes cluster.

## Overview

The deployment includes:
- **NGINX Ingress Controller** - Routes external traffic to Mattermost
- **PostgreSQL Database** - Persistent database with 10GB storage
- **Mattermost Operator** - Manages Mattermost installation
- **Mattermost** - The collaboration platform with 20GB file storage

## Prerequisites

Before deploying, ensure you have:
1. A running Kubernetes cluster (created via OpenStack Magnum)
2. `kubectl` configured with cluster access
3. Helm 3 installed
4. Cluster admin permissions

## Quick Start (Automated)

Use the automated deployment script:

```bash
# From the controller node
cd /local/repository/scripts
chmod +x 03-deploy-mattermost-k8s.sh
./03-deploy-mattermost-k8s.sh
```

This script will:
- Install NGINX Ingress Controller
- Deploy PostgreSQL with persistent storage
- Install Mattermost Operator
- Deploy Mattermost
- Display access information

## Manual Deployment Steps

If you prefer manual deployment, follow these steps:

### Step 1: Install NGINX Ingress Controller

```bash
# Add Helm repository
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update

# Create namespace
kubectl create namespace ingress-nginx

# Install NGINX Ingress
helm install nginx-ingress ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --set controller.service.type=LoadBalancer

# Get the LoadBalancer IP (save this for later)
kubectl get svc -n ingress-nginx
```

### Step 2: Deploy PostgreSQL

```bash
# Create namespace
kubectl create namespace mattermost

# Create PostgreSQL credentials secret
kubectl create secret generic postgres-secret \
  --from-literal=POSTGRES_USER=mmuser \
  --from-literal=POSTGRES_PASSWORD=chocolateFrog! \
  --from-literal=POSTGRES_DB=mattermost \
  --namespace mattermost

# Apply PostgreSQL manifests
kubectl apply -f 01-postgres-pvc.yaml
kubectl apply -f 02-postgres-deployment.yaml

# Verify PostgreSQL is running
kubectl get pods -n mattermost
kubectl logs -n mattermost -l app=postgres
```

### Step 3: Install Mattermost Operator

```bash
# Add Helm repository
helm repo add mattermost https://helm.mattermost.com
helm repo update

# Create namespace
kubectl create namespace mattermost-operator

# Install Mattermost Operator
helm install mattermost-operator mattermost/mattermost-operator \
  --namespace mattermost-operator

# Verify operator is running
kubectl get pods -n mattermost-operator
```

### Step 4: Deploy Mattermost

```bash
# Create database connection secret
kubectl apply -f 03-mattermost-db-secret.yaml

# Create filestore PVC
kubectl apply -f 04-mattermost-filestore-pvc.yaml

# Get your LoadBalancer IP
INGRESS_IP=$(kubectl get svc -n ingress-nginx nginx-ingress-ingress-nginx-controller \
  -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
echo "Your Ingress IP: $INGRESS_IP"

# Edit 05-mattermost-installation.yaml
# Replace all instances of ${INGRESS_IP} with your actual IP address
# Then apply:
kubectl apply -f 05-mattermost-installation.yaml

# Wait for Mattermost to be ready (may take 5-10 minutes)
kubectl get pods -n mattermost -w
```

### Step 5: Access Mattermost

```bash
# Get the access URL
INGRESS_IP=$(kubectl get svc -n ingress-nginx nginx-ingress-ingress-nginx-controller \
  -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
echo "Access Mattermost at: http://mattermost.${INGRESS_IP}.nip.io"

# Check deployment status
kubectl get mattermost -n mattermost
kubectl describe mattermost -n mattermost mattermost
```

## Manifest Files

| File | Description |
|------|-------------|
| `01-postgres-pvc.yaml` | PostgreSQL persistent volume claim (10GB) |
| `02-postgres-deployment.yaml` | PostgreSQL deployment and service |
| `03-mattermost-db-secret.yaml` | Database connection credentials |
| `04-mattermost-filestore-pvc.yaml` | Mattermost file storage PVC (20GB) |
| `05-mattermost-installation.yaml` | Mattermost custom resource definition |

## Configuration

### Database Credentials

Default PostgreSQL credentials (defined in secrets):
- **User**: `mmuser`
- **Password**: `chocolateFrog!`
- **Database**: `mattermost`

To change these, update both:
1. The `postgres-secret` in Step 2
2. The connection string in `03-mattermost-db-secret.yaml`

### Storage Sizes

Default storage allocations:
- **PostgreSQL**: 10GB (can be increased in `01-postgres-pvc.yaml`)
- **Mattermost Files**: 20GB (can be increased in `04-mattermost-filestore-pvc.yaml`)

### Mattermost Version

To deploy a different Mattermost version, edit `05-mattermost-installation.yaml`:
```yaml
spec:
  version: 9.11.0  # Change this to your desired version
```

See [Mattermost Version Archive](https://docs.mattermost.com/product-overview/version-archive.html) for available versions.

### Resource Sizing

The deployment is configured for 1000 users. To change:
```yaml
spec:
  size: 1000users  # Options: 100users, 1000users, 5000users, 10000users, 25000users
```

## Troubleshooting

### Check Pod Status
```bash
kubectl get pods -n mattermost
kubectl get pods -n mattermost-operator
kubectl get pods -n ingress-nginx
```

### View Logs
```bash
# Mattermost logs
kubectl logs -n mattermost -l app.kubernetes.io/name=mattermost

# PostgreSQL logs
kubectl logs -n mattermost -l app=postgres

# Operator logs
kubectl logs -n mattermost-operator -l app.kubernetes.io/name=mattermost-operator
```

### Check Mattermost Resource
```bash
kubectl describe mattermost -n mattermost mattermost
kubectl get mattermost -n mattermost -o yaml
```

### Common Issues

**Issue**: Pods stuck in `Pending` state
- **Solution**: Check PVC binding: `kubectl get pvc -n mattermost`
- **Solution**: Check storage class: `kubectl get storageclass`

**Issue**: Cannot access Mattermost URL
- **Solution**: Verify ingress: `kubectl get ingress -n mattermost`
- **Solution**: Check LoadBalancer IP: `kubectl get svc -n ingress-nginx`

**Issue**: Database connection errors
- **Solution**: Verify PostgreSQL is running: `kubectl get pods -n mattermost`
- **Solution**: Check secret: `kubectl get secret -n mattermost mattermost-postgres-connection -o yaml`

## Cleanup

To remove the entire deployment:

```bash
# Delete Mattermost
kubectl delete -f 05-mattermost-installation.yaml

# Delete operator
helm uninstall mattermost-operator -n mattermost-operator
kubectl delete namespace mattermost-operator

# Delete PostgreSQL and storage
kubectl delete -f 02-postgres-deployment.yaml
kubectl delete -f 01-postgres-pvc.yaml
kubectl delete -f 03-mattermost-db-secret.yaml
kubectl delete -f 04-mattermost-filestore-pvc.yaml
kubectl delete namespace mattermost

# Delete NGINX Ingress
helm uninstall nginx-ingress -n ingress-nginx
kubectl delete namespace ingress-nginx
```

## Additional Resources

- [Mattermost Kubernetes Documentation](https://docs.mattermost.com/deployment-guide/server/deploy-kubernetes.html)
- [Mattermost Operator GitHub](https://github.com/mattermost/mattermost-operator)
- [NGINX Ingress Controller](https://kubernetes.github.io/ingress-nginx/)
- [PostgreSQL on Kubernetes](https://www.postgresql.org/docs/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
