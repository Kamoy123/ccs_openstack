# Kubernetes Manifests for Mattermost Deployment

This directory contains Kubernetes manifest files for deploying Mattermost with all required dependencies on your Kubernetes cluster.

## Overview

The deployment includes:
- **NGINX Ingress Controller** - Routes external traffic to Mattermost
- **PostgreSQL Database** - Persistent database with 10GB storage
- **Mattermost Operator** - Manages Mattermost installation
- **Mattermost** - The collaboration platform with 20GB file storage

## Manual Deployment Steps

If you prefer manual deployment, follow these steps:

### Step 1: Install NGINX Ingress Controller

```bash
# Create namespace
kubectl create namespace ingress-nginx

# Add helm repo
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx

# Update helm repo
helm repo update

# Release node tains
kubectl taint nodes --all node.cloudprovider.kubernetes.io/uninitialized-

# Install ingress-nginx
helm install ingress-nginx ingress-nginx/ingress-nginx \
--version 4.3.0 \
--namespace ingress-nginx \
--create-namespace \
--set controller.service.type=NodePort

# Get the ingress controller's IP (save this for later)
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

# Confirm secrets creation
kubectl get secrets -n mattermost

# Apply PostgreSQL manifests\
kubectl apply -f 01-postgres-pvc.yaml
kubectl apply -f 02-postgres-pv.yaml
kubectl apply -f 03-postgres-deployment.yaml

# Note: you need to ssh into the worker node
# to manually create mount folder and give permissions
# using the following command. Otherwise postgres will
# receive permission deny issue
sudo mkdir -p /mnt/postgresql/data
sudo chown -R 999:999 /mnt/postgresql/data
sudo chmod 700 /mnt/postgresql/data
sudo chcon -Rt svirt_sandbox_file_t /mnt/postgresql/data

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

# check for chart version using:
# chart version must support k8s 1.23.3
helm search repo mattermost/mattermost-operator --versions | head

# Install Mattermost Operator
helm install mattermost-operator mattermost/mattermost-operator \
  --version 1.0.3 \
  --namespace mattermost-operator \
  --create-namespace \
  --set mattermostCR.enabled=false \
  --set mysqlOperator.enabled=false \
  --set minioOperator.enabled=false


# Verify operator is running
kubectl get pods -n mattermost-operator
```

### Step 4: Deploy Mattermost

```bash

# ssh into the worker node to create the following folders
sudo mkdir -p /mnt/k8s/mattermost-filestore
sudo chown 2000:2000 /mnt/k8s/mattermost-filestore
sudo chmod 700 /mnt/k8s/mattermost-filestore
sudo chcon -Rt /mnt/k8s/mattermost-filestore

# Create database connection secret
kubectl apply -f 04-mattermost-db-secret.yaml

# Create filestore PVC and PV
kubectl apply -f 05-mattermost-filestore-pvc.yaml
kubectl apply -f 06-mattermost-filestore-pv.yaml

# Get your LoadBalancer IP
INGRESS_IP=$(kubectl get svc -n ingress-nginx nginx-ingress-ingress-nginx-controller \
  -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
echo "Your Ingress IP: $INGRESS_IP"

# Edit 05-mattermost-installation.yaml
# Replace all instances of ${INGRESS_IP} with your actual IP address
# Then apply:
kubectl apply -f 07-mattermost-installation.yaml

# Wait for Mattermost to be ready (may take 5-10 minutes)
kubectl get pods -n mattermost -w
```

## Deploy Mattermost Teams Edition
```bash
helm uninstall mattermost -n mattermost
kubectl delete -f mm-plugins-pv.yaml
kubectl delete -f mm-data-pv.yaml

kubectl apply -f mm-plugins-pv.yaml
kubectl apply -f mm-data-pv.yaml
helm install mattermost -n mattermost -f values.yaml mattermost/mattermost-team-edition
```

### Step 5: Access Mattermost

```bash
# Get the access URL
kubectl get svc -n ingress-nginx ingress-nginx-controller 
# Access Mattermost at: http://mattermost.${INGRESS_IP}.nip.io"

# Check deployment status
kubectl get mattermost -n mattermost
kubectl describe mattermost -n mattermost mattermost
```
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
  version: 11.0.4
```

See [Mattermost Version Archive](https://docs.mattermost.com/product-overview/version-archive.html) for available versions.

### Resource Sizing

The deployment is configured for 1000 users. To change:
```yaml
spec:
  size: 1000users 
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
