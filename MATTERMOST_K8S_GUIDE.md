# Mattermost on Kubernetes - Quick Reference Guide

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    External Traffic                          │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              NGINX Ingress Controller                        │
│              (LoadBalancer Service)                          │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                  Mattermost Pods                             │
│              (Managed by Operator)                           │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  Mattermost  │  │  Mattermost  │  │  Mattermost  │     │
│  │   Replica 1  │  │   Replica 2  │  │   Replica N  │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│         │                  │                  │              │
│         └──────────────────┴──────────────────┘              │
│                            │                                 │
└────────────────────────────┼─────────────────────────────────┘
                             │
                ┌────────────┴────────────┐
                │                         │
                ▼                         ▼
    ┌──────────────────┐      ┌─────────────────────┐
    │   PostgreSQL     │      │  File Storage PVC   │
    │   (Database)     │      │   (20GB Volume)     │
    │  with PVC (10GB) │      └─────────────────────┘
    └──────────────────┘
```

## Component Summary

### 1. NGINX Ingress Controller
- **Purpose**: Routes HTTP/HTTPS traffic from external sources to Mattermost
- **Type**: LoadBalancer service (uses OpenStack Octavia)
- **Namespace**: `ingress-nginx`
- **Key Configuration**:
  - Proxy body size: 100MB (for file uploads)
  - Timeouts: 600 seconds
  - WebSocket support enabled

### 2. PostgreSQL Database
- **Purpose**: Stores all Mattermost data (users, channels, messages, etc.)
- **Namespace**: `mattermost`
- **Image**: `postgres:15`
- **Storage**: 10GB persistent volume
- **Credentials**:
  - User: `mmuser`
  - Password: `chocolateFrog!`
  - Database: `mattermost`
- **Service**: `postgres.mattermost.svc.cluster.local:5432`

### 3. Mattermost Operator
- **Purpose**: Manages Mattermost lifecycle (installation, upgrades, scaling)
- **Namespace**: `mattermost-operator`
- **Installed via**: Helm chart
- **Repository**: https://helm.mattermost.com

### 4. Mattermost Application
- **Purpose**: The collaboration platform
- **Namespace**: `mattermost`
- **Version**: 9.11.0 (configurable)
- **Sizing**: 1000users (configurable)
- **Storage**: 20GB persistent volume for file uploads
- **Replicas**: 1 (can be scaled for HA with Enterprise license)

## Deployment Methods

### Method 1: Automated Script (Recommended)
```bash
chmod +x /local/repository/scripts/03-deploy-mattermost-k8s.sh
./03-deploy-mattermost-k8s.sh
```
**Time**: ~10-15 minutes
**Best for**: Quick deployment, testing

### Method 2: Manual with Manifests
```bash
# Follow steps in k8s-manifests/README.md
kubectl apply -f k8s-manifests/
```
**Time**: ~20-30 minutes
**Best for**: Understanding components, custom configuration

### Method 3: Step-by-Step Commands
```bash
# Follow commands in profile instructions
# See "Deploy Mattermost on Kubernetes" section
```
**Time**: ~30-45 minutes
**Best for**: Learning, debugging, customization

## Common Commands

### Check Deployment Status
```bash
# Get all Mattermost resources
kubectl get all -n mattermost

# Check Mattermost custom resource
kubectl get mattermost -n mattermost

# View detailed status
kubectl describe mattermost -n mattermost mattermost
```

### View Logs
```bash
# Mattermost application logs
kubectl logs -n mattermost -l app.kubernetes.io/name=mattermost -f

# PostgreSQL logs
kubectl logs -n mattermost -l app=postgres -f

# Operator logs
kubectl logs -n mattermost-operator -l app.kubernetes.io/name=mattermost-operator -f

# Ingress controller logs
kubectl logs -n ingress-nginx -l app.kubernetes.io/name=ingress-nginx -f
```

### Debug Issues
```bash
# Check pod status
kubectl get pods -n mattermost
kubectl describe pod -n mattermost <pod-name>

# Check events
kubectl get events -n mattermost --sort-by='.lastTimestamp'

# Check persistent volumes
kubectl get pv
kubectl get pvc -n mattermost

# Test database connectivity
kubectl exec -n mattermost -it <postgres-pod> -- psql -U mmuser -d mattermost -c '\dt'
```

### Access Mattermost
```bash
# Get LoadBalancer IP
INGRESS_IP=$(kubectl get svc -n ingress-nginx nginx-ingress-ingress-nginx-controller -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

# Display access URL
echo "http://mattermost.$INGRESS_IP.nip.io"

# Check ingress configuration
kubectl get ingress -n mattermost
kubectl describe ingress -n mattermost
```

### Scale Mattermost
```bash
# Edit Mattermost resource
kubectl edit mattermost -n mattermost mattermost

# Change replicas:
spec:
  replicas: 2  # Requires Enterprise license for HA
```

### Update Mattermost Version
```bash
# Edit Mattermost resource
kubectl edit mattermost -n mattermost mattermost

# Change version:
spec:
  version: 9.12.0  # Update to desired version
```

## Storage Management

### Check Storage Usage
```bash
# View PVCs
kubectl get pvc -n mattermost

# Describe PVC
kubectl describe pvc -n mattermost postgres-pvc
kubectl describe pvc -n mattermost mattermost-filestore-pvc
```

### Expand Storage
```bash
# Edit PVC to increase size (if storage class supports it)
kubectl edit pvc -n mattermost postgres-pvc

# Update storage size:
spec:
  resources:
    requests:
      storage: 20Gi  # Increase from 10Gi
```

### Backup Data
```bash
# Backup PostgreSQL database
kubectl exec -n mattermost <postgres-pod> -- pg_dump -U mmuser mattermost > mattermost-backup.sql

# Backup file storage
kubectl exec -n mattermost <mattermost-pod> -- tar czf /tmp/files-backup.tar.gz /mattermost/data
kubectl cp mattermost/<mattermost-pod>:/tmp/files-backup.tar.gz ./files-backup.tar.gz
```

## Troubleshooting Guide

### Issue: Pods not starting
```bash
# Check pod status
kubectl get pods -n mattermost

# Check pod events
kubectl describe pod -n mattermost <pod-name>

# Common causes:
# - PVC not binding (check storage class)
# - Image pull errors (check network/registry)
# - Resource constraints (check node resources)
```

### Issue: Cannot access Mattermost URL
```bash
# Verify ingress has address
kubectl get ingress -n mattermost

# Check ingress controller
kubectl get svc -n ingress-nginx

# Test connectivity
curl -v http://mattermost.$INGRESS_IP.nip.io

# Common causes:
# - LoadBalancer not assigned IP
# - DNS not resolving (use nip.io)
# - Firewall/security group rules
```

### Issue: Database connection errors
```bash
# Check PostgreSQL is running
kubectl get pods -n mattermost -l app=postgres

# Test database connectivity
kubectl exec -n mattermost <postgres-pod> -- pg_isready -U mmuser

# Check secrets
kubectl get secret -n mattermost mattermost-postgres-connection -o yaml

# Common causes:
# - Wrong credentials in secret
# - PostgreSQL not ready
# - Network policy blocking traffic
```

### Issue: File uploads failing
```bash
# Check PVC is bound
kubectl get pvc -n mattermost mattermost-filestore-pvc

# Check available space
kubectl exec -n mattermost <mattermost-pod> -- df -h /mattermost/data

# Check Mattermost configuration
kubectl exec -n mattermost <mattermost-pod> -- cat /mattermost/config/config.json | grep -A 10 FileSettings

# Common causes:
# - PVC full (expand storage)
# - Wrong permissions
# - Upload size limit (check nginx.ingress.kubernetes.io/proxy-body-size)
```

## Performance Tuning

### Resource Limits
```yaml
# Edit Mattermost resource
kubectl edit mattermost -n mattermost mattermost

# Adjust resources:
spec:
  resources:
    requests:
      cpu: "1000m"
      memory: "1Gi"
    limits:
      cpu: "4000m"
      memory: "4Gi"
```

### Database Optimization
```bash
# Connect to PostgreSQL
kubectl exec -n mattermost -it <postgres-pod> -- psql -U mmuser -d mattermost

# Check database size
SELECT pg_size_pretty(pg_database_size('mattermost'));

# Vacuum database
VACUUM ANALYZE;

# Check slow queries
SELECT * FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;
```

### Enable Metrics
```bash
# Add to Mattermost env
kubectl edit mattermost -n mattermost mattermost

# Add:
spec:
  mattermostEnv:
  - name: MM_METRICSSETTINGS_ENABLE
    value: "true"
  - name: MM_METRICSSETTINGS_LISTENADDRESS
    value: ":8067"
```

## Security Best Practices

### 1. Change Default Passwords
```bash
# Update PostgreSQL password
kubectl create secret generic postgres-secret \
  --from-literal=POSTGRES_PASSWORD=YourSecurePassword123! \
  --namespace mattermost \
  --dry-run=client -o yaml | kubectl apply -f -

# Update Mattermost DB connection secret accordingly
```

### 2. Enable HTTPS
```bash
# Add cert-manager for TLS
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Configure Let's Encrypt issuer
# Update ingress with TLS configuration
```

### 3. Network Policies
```bash
# Restrict traffic to PostgreSQL
kubectl apply -f - <<EOF
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: postgres-netpol
  namespace: mattermost
spec:
  podSelector:
    matchLabels:
      app: postgres
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app.kubernetes.io/name: mattermost
    ports:
    - protocol: TCP
      port: 5432
EOF
```

### 4. Enable Audit Logging
```bash
kubectl edit mattermost -n mattermost mattermost

# Add:
spec:
  mattermostEnv:
  - name: MM_EXPERIMENTALAUDITSETTINGS_FILEENABLED
    value: "true"
```

## Cleanup

### Remove Mattermost Only
```bash
kubectl delete mattermost -n mattermost mattermost
```

### Remove All Components
```bash
# Delete Mattermost
kubectl delete mattermost -n mattermost mattermost

# Delete operator
helm uninstall mattermost-operator -n mattermost-operator

# Delete PostgreSQL and storage
kubectl delete deployment,svc,pvc,secret -n mattermost --all

# Delete ingress
helm uninstall nginx-ingress -n ingress-nginx

# Delete namespaces
kubectl delete namespace mattermost mattermost-operator ingress-nginx
```

## Additional Resources

- **Official Docs**: https://docs.mattermost.com/deployment-guide/server/deploy-kubernetes.html
- **Operator Repo**: https://github.com/mattermost/mattermost-operator
- **Helm Charts**: https://github.com/mattermost/mattermost-helm
- **Community Forum**: https://forum.mattermost.com/
- **Support**: https://mattermost.com/support/
