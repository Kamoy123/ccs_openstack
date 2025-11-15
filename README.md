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

# Update the ip address in k8s-manifests/values.yaml to external IP of worker node
# and port mapped to 80 or 443. Use port mapped to 80 is TLS is not enabled.

# Release node tains - Do not use this command
kubectl taint nodes --all node.cloudprovider.kubernetes.io/uninitialized-
```


### Step 2: Deploy Mattermost Teams Edition
---
#### Note: current deployment does not have dynamic volume provisioner in place. Therefore, we need to manually create persistent volume for Mattermost. 
```bash
# First try to deploy mattermost and run the following commands to confirm what mattermost's persistent volume claim is requesting, the size in config map must match the size
kubectl -n mattermost get pvc mattermost-mattermost-team-edition -o yaml | egrep 'storage:|accessModes|storageClassName'
kubectl -n mattermost get pvc mattermost-mattermost-team-edition-plugins -o yaml | egrep 'storage:|accessModes|storageClassName'
kubectl -n mattermost get pvc mattermost-mysql -o yaml | egrep 'storage:|accessModes|storageClassName'

# Then, we need to pick a node to host data, run the following command to label the node, replace <NODE_NAME> with the worker node's name.
kubectl get nodes -o wide
kubectl label node <NODE_NAME> storage=mattermost --overwrite

# SSH into the node to manually prepare directories for matter, you can choose any folder but we picked /mnt folder because it's guranteed to be clean to write
# Do note write to /var because linux write system files to it and mattermost will refuse to bind if the directory is not empty. Manually clearing the directory won't work
ssh -i ~/.ssh/mykey core@<worker-node-ip> # <-- do this in the shell
sudo mkdir -p /mnt/mattermost/app /mnt/mattermost/plugins /mnt/mattermost/mysql
sudo chmod -R 0777 /mnt/mattermost   # quick-and-dirty; tighten later if needed

```
---
#### Deploy mattermost teams edition
```bash
# Create namespace
kubectl create namespace mattermost

# Add Helm repository
helm repo add mattermost https://helm.mattermost.com
helm repo update

# Provision Presistent Volume for mattermost to bind
kubectl apply -f 01-mm-pv-app.yaml -n mattermost
kubectl apply -f 02-mm-pv-plugins.yaml -n mattermost
kubectl apply -f 03-mm-pv-mysql.yaml -n mattermost

# install team edition
helm install mattermost -n mattermost \
  -f values.yaml \
  --set image.tag=5.35.3 \
  --set mysql.mysqlUser=sampleUser \
  --set mysql.mysqlPassword=samplePassword \
  mattermost/mattermost-team-edition


# get secret used by mattermost - ignore this
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
