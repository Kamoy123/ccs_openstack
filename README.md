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

# Get the worker node IP (save this for later)
kubectl get nodes -o wide

# Get nginx port mapping
kubectl get svc -n ingress-nginx
```


### Step 2: Deploy Mattermost Teams Edition
```bash

# Add Helm repository
helm repo add mattermost https://helm.mattermost.com
helm repo update

# install team edition
helm install mattermost -n mattermost \
  -f 08-values.yaml \
  --set image.tag=5.35.3 \
  --set mysql.mysqlUser=sampleUser \
  --set mysql.mysqlPassword=samplePassword \
  mattermost/mattermost-team-edition


# get secret used by mattermost
kubectl get secret mattermost-mattermost-team-edition-mattermost-dbsecret -n mattermost -o jsonpath='{.data.mattermost\.dbsecret}' | base64 -d; echo

# commands to delete
helm uninstall mattermost -n mattermost
```

### Step 3: Access Mattermost

```bash
# Get the access URL
kubectl get svc -n ingress-nginx ingress-nginx-controller 
# Access Mattermost at: http://mattermost.${INGRESS_IP}.nip.io"

# Check deployment status
kubectl get mattermost -n mattermost
kubectl describe mattermost -n mattermost mattermost
```

## Troubleshooting

### Check Pod Status
```bash
kubectl get pods -n mattermost
kubectl get pods -n ingress-nginx
```


### Check Mattermost Resource
```bash
kubectl describe mattermost -n mattermost mattermost
kubectl get mattermost -n mattermost -o yaml
```

## Cleanup

To remove the entire deployment:

```bash
# Delete Mattermost
helm uninstall mattermost -n mattermost
kubectl delete namespace mattermost

# Delete NGINX Ingress
helm uninstall nginx-ingress -n ingress-nginx
kubectl delete namespace ingress-nginx
```

## Additional Resources

- [Mattermost Kubernetes Documentation](https://docs.mattermost.com/deployment-guide/server/deploy-kubernetes.html)
- [Mattermost Operator GitHub](https://github.com/mattermost/mattermost-operator)
- [NGINX Ingress Controller](https://kubernetes.github.io/ingress-nginx/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
