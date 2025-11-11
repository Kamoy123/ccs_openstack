# OpenStack + Kubernetes + Mattermost on CloudLab

This repository contains a CloudLab profile for deploying a complete OpenStack environment with Kubernetes (Magnum) support, optimized for running Mattermost as a production-ready collaboration platform.

## 🚀 Quick Start

1. **Instantiate Profile on CloudLab**
   - Go to [CloudLab](https://www.cloudlab.us/)
   - Select this profile
   - Choose hardware type (recommended: `d430`)
   - Set number of compute nodes (minimum 2)
   - Click "Instantiate"

2. **Wait for Deployment** (~30-60 minutes)
   - Monitor logs on CloudLab experiment page
   - Wait for controller node status to show "ready"
   - Wait for startup scripts to finish (check "Startup" column)

3. **Deploy Kubernetes Cluster**
   ```bash
   # SSH into controller node
   ssh <username>@<controller-node-address>
   
   # Source OpenStack credentials
   source /opt/devstack/openrc admin admin
   
   # Create keypair
   ssh-keygen -t rsa -b 4096 -f ~/.ssh/mykey
   openstack keypair create --public-key ~/.ssh/mykey.pub mykey
   
   # Get cluster template UUID
   openstack coe cluster template list
   
   # Create Kubernetes cluster
   openstack coe cluster create \
     --cluster-template <TEMPLATE_UUID> \
     --master-count 1 \
     --node-count 2 \
     --keypair mykey \
     mattermost-k8s-cluster
   
   # Monitor cluster creation (takes 10-15 minutes)
   watch openstack coe cluster show mattermost-k8s-cluster
   ```

4. **Deploy Mattermost**
   ```bash
   # Get kubeconfig
   openstack coe cluster config mattermost-k8s-cluster
   export KUBECONFIG=~/config
   
   # Run automated deployment script
   chmod +x /local/repository/scripts/03-deploy-mattermost-k8s.sh
   /local/repository/scripts/03-deploy-mattermost-k8s.sh
   
   # Access Mattermost (URL will be displayed by the script)
   # Format: http://mattermost.<LOADBALANCER_IP>.nip.io
   ```

## 📁 Repository Structure

```
ccs_openstack/
├── osp.py                          # CloudLab profile definition (geni-lib)
├── profile.py                      # Profile reference
├── README.md                       # This file
├── MATTERMOST_K8S_GUIDE.md        # Comprehensive Mattermost deployment guide
├── scripts/
│   ├── 01-install-openstack.sh    # OpenStack installation script
│   ├── 02-configure-magnum.sh     # Magnum configuration script
│   └── 03-deploy-mattermost-k8s.sh # Mattermost deployment automation
└── k8s-manifests/
    ├── README.md                   # Manual deployment instructions
    ├── 01-postgres-pvc.yaml       # PostgreSQL persistent storage
    ├── 02-postgres-deployment.yaml # PostgreSQL database
    ├── 03-mattermost-db-secret.yaml # Database credentials
    ├── 04-mattermost-filestore-pvc.yaml # Mattermost file storage
    └── 05-mattermost-installation.yaml  # Mattermost configuration
```

## 🏗️ Architecture

### Infrastructure Layer
- **Controller Node**: Runs all OpenStack control plane services
  - Keystone (Identity)
  - Nova (Compute)
  - Neutron (Networking)
  - Glance (Image Service)
  - Cinder (Block Storage)
  - Heat (Orchestration)
  - Horizon (Dashboard)
  - Octavia (Load Balancer)
  - Magnum (Container Orchestration)

- **Compute Nodes**: Run Nova compute service and host VMs/containers
  - Configurable count (recommended: 2+)
  - Hosts Kubernetes worker nodes

### Kubernetes Layer (via Magnum)
- **Master Nodes**: Control plane (1 by default)
- **Worker Nodes**: Run application pods (2 by default)
- **Load Balancer**: Octavia-based (for ingress)

### Application Layer (Mattermost)
```
Internet
    ↓
NGINX Ingress Controller (LoadBalancer)
    ↓
Mattermost Pods (1+ replicas)
    ↓
├── PostgreSQL Database (10GB PVC)
└── File Storage (20GB PVC)
```

## 🎯 Features

### OpenStack Environment
- ✅ Full OpenStack deployment (Ubuntu 24.04)
- ✅ Multi-node setup (1 controller + N compute nodes)
- ✅ Magnum for Kubernetes cluster provisioning
- ✅ Octavia for load balancing
- ✅ Custom VM flavors optimized for Mattermost
- ✅ Horizon dashboard for GUI management
- ✅ Pre-configured networking and security groups

### Kubernetes Deployment
- ✅ One-command cluster creation via Magnum
- ✅ Integration with OpenStack networking
- ✅ Octavia-backed LoadBalancer services
- ✅ Persistent volume support (Cinder)
- ✅ Pre-configured cluster templates

### Mattermost Application
- ✅ Production-ready Kubernetes deployment
- ✅ NGINX Ingress Controller for routing
- ✅ PostgreSQL database with persistent storage
- ✅ Persistent file storage (20GB)
- ✅ Automated deployment script
- ✅ Manual deployment manifests
- ✅ Comprehensive documentation
- ✅ Scalable architecture (HA with Enterprise)

## 📚 Documentation

### Quick References
- **[Mattermost K8s Guide](MATTERMOST_K8S_GUIDE.md)** - Complete deployment and operations guide
- **[K8s Manifests README](k8s-manifests/README.md)** - Manual deployment instructions
- **Profile Instructions** - Built-in CloudLab experiment page docs

### Key Commands

#### OpenStack
```bash
# Source credentials
source /opt/devstack/openrc admin admin

# List resources
openstack server list
openstack network list
openstack image list
openstack flavor list

# Access Horizon dashboard
# URL: http://<controller-ip>/dashboard
# Credentials: admin / chocolateFrog!
```

#### Kubernetes
```bash
# Configure kubectl
openstack coe cluster config mattermost-k8s-cluster
export KUBECONFIG=~/config

# Cluster operations
kubectl get nodes
kubectl get pods -A
kubectl get svc -A

# View logs
kubectl logs -n mattermost -l app.kubernetes.io/name=mattermost
```

#### Mattermost
```bash
# Check status
kubectl get mattermost -n mattermost
kubectl get pods -n mattermost

# View logs
kubectl logs -n mattermost -l app.kubernetes.io/name=mattermost -f

# Get access URL
kubectl get ingress -n mattermost
```

## 🔧 Configuration

### Profile Parameters

When instantiating the profile, you can configure:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `osImage` | Ubuntu 24.04 | Operating system image |
| `hwType` | `d430` | Hardware type for all nodes |
| `computeNodeCount` | `2` | Number of compute nodes |
| `os_username` | `crookshanks` | OpenStack username |
| `os_password` | `chocolateFrog!` | OpenStack password |

### Mattermost Configuration

Default settings in `05-mattermost-installation.yaml`:

| Setting | Value | Customizable |
|---------|-------|--------------|
| Version | 9.11.0 | ✅ Yes |
| Size | 1000users | ✅ Yes (100, 1000, 5000, 10000, 25000) |
| Replicas | 1 | ✅ Yes (requires Enterprise for HA) |
| Database | PostgreSQL 15 | ✅ Yes |
| DB Storage | 10GB | ✅ Yes |
| File Storage | 20GB | ✅ Yes |

### Database Credentials

Default PostgreSQL credentials:
- **User**: `mmuser`
- **Password**: `chocolateFrog!`
- **Database**: `mattermost`

⚠️ **Security Note**: Change default passwords for production use!

## 🔍 Troubleshooting

### OpenStack Issues

**Dashboard not accessible**
```bash
# Check DevStack services
systemctl status devstack@*

# View installation logs
tail -f /opt/stack/logs/stack.sh.log
cat /tmp/install-openstack.log
```

**Magnum cluster creation fails**
```bash
# Check Magnum logs
cat /tmp/configure-magnum.log
tail -f /opt/stack/logs/magnum-*.log

# Check Heat stack
openstack stack list
openstack stack resource list <stack-id>
```

### Kubernetes Issues

**Cannot connect to cluster**
```bash
# Verify kubeconfig
cat ~/config

# Test connectivity
kubectl cluster-info
kubectl get nodes
```

**Pods not starting**
```bash
# Check pod status
kubectl get pods -n mattermost
kubectl describe pod -n mattermost <pod-name>

# Check events
kubectl get events -n mattermost --sort-by='.lastTimestamp'
```

### Mattermost Issues

**Cannot access Mattermost URL**
```bash
# Check ingress
kubectl get ingress -n mattermost
kubectl get svc -n ingress-nginx

# Verify LoadBalancer IP
kubectl get svc -n ingress-nginx nginx-ingress-ingress-nginx-controller
```

**Database connection errors**
```bash
# Check PostgreSQL
kubectl get pods -n mattermost -l app=postgres
kubectl logs -n mattermost -l app=postgres

# Test connection
kubectl exec -n mattermost <postgres-pod> -- pg_isready -U mmuser
```

For detailed troubleshooting, see [MATTERMOST_K8S_GUIDE.md](MATTERMOST_K8S_GUIDE.md).

## 📋 Requirements

### CloudLab Resources
- Minimum 3 nodes (1 controller + 2 compute)
- Recommended hardware: `d430` or similar
- Estimated setup time: 30-60 minutes

### Resource Allocation (per node)
- CPU: 16+ cores
- RAM: 32GB+ 
- Disk: 100GB+ 

### Software Versions
- Ubuntu: 24.04 LTS
- OpenStack: Latest (via DevStack)
- Kubernetes: Latest (via Magnum)
- PostgreSQL: 15
- Mattermost: 9.11.0 (configurable)

## 🚦 Deployment Timeline

| Phase | Duration | Description |
|-------|----------|-------------|
| Node Provisioning | 5-10 min | CloudLab allocates and boots nodes |
| OpenStack Installation | 20-40 min | DevStack installation on controller |
| Magnum Configuration | 5-10 min | Kubernetes templates and images |
| K8s Cluster Creation | 10-15 min | Magnum provisions Kubernetes |
| Mattermost Deployment | 5-10 min | Deploy all components |
| **Total** | **45-85 min** | From start to working Mattermost |

## 🔒 Security Considerations

### Default Credentials (CHANGE THESE!)
- OpenStack Admin: `admin / chocolateFrog!`
- OpenStack Demo: `demo / chocolateFrog!`
- PostgreSQL: `mmuser / chocolateFrog!`

### Security Checklist
- [ ] Change all default passwords
- [ ] Enable HTTPS/TLS for Mattermost
- [ ] Configure firewall rules
- [ ] Enable audit logging
- [ ] Regular security updates
- [ ] Backup database and files
- [ ] Implement network policies
- [ ] Use secrets management

## 📦 Deployment Options

### Option 1: Automated (Recommended)
Use the provided script for one-command deployment:
```bash
./scripts/03-deploy-mattermost-k8s.sh
```

### Option 2: Manual with Manifests
Apply Kubernetes manifests individually:
```bash
kubectl apply -f k8s-manifests/
```

### Option 3: Step-by-Step
Follow detailed instructions in the profile docs for learning and customization.

## 🔄 Updates and Upgrades

### Update Mattermost Version
```bash
kubectl edit mattermost -n mattermost mattermost
# Change spec.version to desired version
```

### Scale Mattermost
```bash
kubectl edit mattermost -n mattermost mattermost
# Change spec.replicas (requires Enterprise license for HA)
```

### Expand Storage
```bash
kubectl edit pvc -n mattermost mattermost-filestore-pvc
# Increase spec.resources.requests.storage
```

## 🧹 Cleanup

### Remove Mattermost Only
```bash
kubectl delete mattermost -n mattermost mattermost
```

### Remove Kubernetes Cluster
```bash
openstack coe cluster delete mattermost-k8s-cluster
```

### Remove Everything
Terminate the CloudLab experiment.

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## 📞 Support

- **CloudLab Help**: https://docs.cloudlab.us/
- **OpenStack Docs**: https://docs.openstack.org/
- **Mattermost Docs**: https://docs.mattermost.com/
- **Kubernetes Docs**: https://kubernetes.io/docs/

## 📄 License

This project follows CloudLab profile licensing guidelines.

## 🙏 Acknowledgments

- CloudLab for infrastructure
- OpenStack DevStack community
- Mattermost team for excellent documentation
- Kubernetes community

## 📈 Version History

- **v1.0** - Initial release with OpenStack + Magnum
- **v2.0** - Added automated Mattermost deployment with all dependencies

---

**Made with ❤️ for cloud-native collaboration**
