# profile.py: A geni-lib script to deploy a multi-node
# OpenStack + Kubernetes environment on CloudLab.

"""
Multi-node OpenStack + Kubernetes deployment optimized for Mattermost on Ubuntu 24.04.
This profile provisions a production-ready OpenStack environment with:
- OpenStack core services (Nova, Neutron, Cinder, Glance, Heat, Horizon)
- Octavia Load Balancer for high availability
- Kubernetes support via OpenStack Magnum
- VM flavors optimized for Mattermost (4GB+ RAM)
- One controller node and user-defined number of compute nodes

Instructions:
## Basic Instructions

**PATIENCE IS KEY!** The OpenStack installation and configuration process is complex and can take 30-60 minutes to complete.
- While the experiment nodes are being provisioned, you can monitor the `logs` on the project page.
- When the nodes start booting, you can inspect their status either in `Topology View` or `List View`.
- Once a node is booted and it's 'Status' column shows 'ready', you can click on the settings gear icon on the right side of the experiment page to open a shell to the node.
    - You can monitor the setup progress by viewing log files or by inspecting running services.
    - Browse to `/opt/stack/logs/`. You can use `tail -f <logfile>` to monitor log files in real-time.
    - Use `$ systemctl status <service>` to check the status of services.

Once the controller node's `Status` changes to `ready`, and profile configuration scripts finish configuring OpenStack (indicated by `Startup` column changing to `Finished`), you'll be able to visit and log in to [the OpenStack Dashboard](http://{host-controller}/dashboard).
Default dashboard credentials are:
1. `admin` / `chocolateFrog!`
2. `demo` / `chocolateFrog!`

### OpenStack Login Credentials
Default: `crookshanks` / `chocolateFrog!`
If you changed the default values and forgot what you set it to, click on the `Bindings` tab on the experiment page to see the custom settings.

### Deploying Mattermost

This profile is optimized for Mattermost deployment with two approaches:

#### Option 1: Direct VM Deployment
1. Create a VM with PostgreSQL database
2. Create a VM with Mattermost application server
3. Optional: Use Octavia load balancer for high availability

#### Option 2: Kubernetes Deployment
1. Deploy a Kubernetes cluster using Magnum (see instructions below)
2. Install Mattermost using Helm chart
3. Use Kubernetes LoadBalancer service type with Octavia

### Some commands to run on the controller node

Click on the settings gear icon on the right side of the experiment page to open a shell to the controller node.

#### Run every time you open a new shell
```bash
$ source /opt/devstack/openrc admin admin
```

#### Create Keypair and Deploy a Kubernetes Cluster
```bash
$ ssh-keygen -t rsa -b 4096 -f ~/.ssh/mykey
$ openstack keypair create --public-key ~/.ssh/mykey.pub mykey
$ chmod 600 ~/.ssh/mykey.pub  # Permissions for the private key.
$ openstack keypair list	# To Confirm the keypair was created.

$ openstack [option] --help
$ openstack coe cluster template list # This shows a list of custom K8s templates. # Note the UUID of the required template.

$ openstack coe cluster create --cluster-template <UUID> --master-count 1 --node-count 2 --keypair mykey  mattermost-k8s-cluster	# Creates a K8s deployment named 'mattermost-k8s-cluster' with 2 worker nodes. Replace <UUID> with the actual UUID as noted previously.
$ watch openstack coe cluster show mattermost-k8s-cluster    # Monitor the cluster creation process.

$ openstack stack list  # Note the stack ID of the cluster.
$ watch openstack stack resource list <stack_id>  # Replace <stack_id> with the actual stack ID.

# If cluster creation is unsuccessful, note it's Stack name and resource name to see the error message:
$ openstack stack list  # Note the stack name of the failed cluster.
$ openstack stack resource list <failed-stack-name> # Replace <failed-stack-name> with the actual stack name and note the failed resource's name.
$ openstack stack resource show <failed-stack-name> <failed-resource-name>  # Replace <failed-stack-name> and <failed-resource-name> with actual values to see the error message.
```

After the cluster is successfully created, you can ssh into a node using `ssh -i ~/.ssh/mykey core@<node-ip>`. You can get the node IPs from the [dashboard](http://{host-controller}/dashboard) or by running `openstack server list`.

#### Deploy Mattermost on Kubernetes

Mattermost requires three key components:
1. **NGINX Ingress Controller** - for routing external traffic
2. **PostgreSQL Database** - for data storage with persistent volumes
3. **Persistent Storage** - for file uploads and attachments

##### Step 1: Get Kubernetes Cluster Access
```bash
# Get kubeconfig for your cluster
$ openstack coe cluster config mattermost-k8s-cluster
$ export KUBECONFIG=~/config

# Verify cluster connectivity
$ kubectl get nodes
```

##### Step 2: Install Helm (if not already installed)
```bash
$ curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
$ helm version
```

##### Step 3: Install NGINX Ingress Controller
```bash
# Add NGINX Ingress Helm repository
$ helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
$ helm repo update

# Create namespace for ingress
$ kubectl create namespace ingress-nginx

# Install NGINX Ingress Controller
$ helm install nginx-ingress ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --set controller.service.type=LoadBalancer

# Verify installation
$ kubectl get pods -n ingress-nginx
$ kubectl get svc -n ingress-nginx

# Get the LoadBalancer IP (note this for later)
$ kubectl get svc -n ingress-nginx nginx-ingress-ingress-nginx-controller
```

##### Step 4: Deploy PostgreSQL Database
```bash
# Create namespace for Mattermost
$ kubectl create namespace mattermost

# Create PostgreSQL persistent volume claim
$ cat <<EOF | kubectl apply -f -
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
$ kubectl create secret generic postgres-secret \
  --from-literal=POSTGRES_USER=mmuser \
  --from-literal=POSTGRES_PASSWORD=chocolateFrog! \
  --from-literal=POSTGRES_DB=mattermost \
  --namespace mattermost

# Deploy PostgreSQL
$ cat <<EOF | kubectl apply -f -
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

# Verify PostgreSQL is running
$ kubectl get pods -n mattermost
$ kubectl logs -n mattermost -l app=postgres
```

##### Step 5: Install Mattermost Operator
```bash
# Add Mattermost Helm repository
$ helm repo add mattermost https://helm.mattermost.com
$ helm repo update

# Create namespace for Mattermost Operator
$ kubectl create namespace mattermost-operator

# Install Mattermost Operator
$ helm install mattermost-operator mattermost/mattermost-operator \
  --namespace mattermost-operator

# Verify Operator installation
$ kubectl get pods -n mattermost-operator
```

##### Step 6: Create Database Connection Secret
```bash
# Create base64-encoded database connection strings
# Connection string format: postgres://mmuser:chocolateFrog!@postgres.mattermost.svc.cluster.local:5432/mattermost?connect_timeout=10

# For convenience, create the secret directly
$ cat <<EOF | kubectl apply -f -
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
```

##### Step 7: Create Mattermost Filestore PVC
```bash
# Create persistent volume claim for Mattermost files
$ cat <<EOF | kubectl apply -f -
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
```

##### Step 8: Deploy Mattermost
```bash
# Get the LoadBalancer IP from NGINX Ingress
$ INGRESS_IP=$(kubectl get svc -n ingress-nginx nginx-ingress-ingress-nginx-controller -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
$ echo "Ingress IP: $INGRESS_IP"

# Create Mattermost installation manifest
$ cat <<EOF | kubectl apply -f -
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
    host: mattermost.$INGRESS_IP.nip.io
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
    value: "http://mattermost.$INGRESS_IP.nip.io"
  - name: MM_SERVICESETTINGS_ENABLELOCALMODE
    value: "true"
  replicas: 1
EOF

# Wait for Mattermost to be ready
$ kubectl get pods -n mattermost -w
```

##### Step 9: Access Mattermost
```bash
# Check Mattermost pods status
$ kubectl get pods -n mattermost

# Check Mattermost service
$ kubectl get svc -n mattermost

# Check ingress
$ kubectl get ingress -n mattermost

# Get the access URL
$ INGRESS_IP=$(kubectl get svc -n ingress-nginx nginx-ingress-ingress-nginx-controller -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
$ echo "Access Mattermost at: http://mattermost.$INGRESS_IP.nip.io"

# Troubleshooting: Check logs if needed
$ kubectl logs -n mattermost -l app.kubernetes.io/name=mattermost
$ kubectl describe mattermost -n mattermost mattermost
```

##### Alternative: Quick Deployment Script
You can use the automated deployment script:
```bash
$ chmod +x /local/repository/scripts/03-deploy-mattermost-k8s.sh
$ /local/repository/scripts/03-deploy-mattermost-k8s.sh
```

This script automatically:
- Installs NGINX Ingress Controller
- Deploys PostgreSQL with persistent storage
- Installs Mattermost Operator
- Deploys Mattermost with proper configuration
- Displays access URL

> **Note**
> - It may happen that OpenStack does not get installed properly on the first attempt. If you encounter issues logging into the dashboard or if the `openstack` CLI commands do not work, browse `/tmp/install-openstack.log` on the controller node to see what went wrong. If you continue to face issues, consider re-instantiating the profile with a different hardware type.
> - If you face issues with Magnum/Kubernetes, browse `/tmp/configure-magnum.log` and `/opt/stack/logs/` on the controller node to see what went wrong.
> - If the cluster creation fails due to insufficient resources, try increasing the number of compute nodes when instantiating the profile, or decreasing the number of worker nodes for the cluster.
> - Using `watch` option is optional, it just refreshes the output every 2 seconds. Use `Ctrl+C` to exit watch.

### Additional Files

This profile includes automated deployment scripts and Kubernetes manifests:

#### Deployment Scripts
- `scripts/01-install-openstack.sh` - Installs and configures OpenStack
- `scripts/02-configure-magnum.sh` - Configures Magnum for Kubernetes
- `scripts/03-deploy-mattermost-k8s.sh` - Automated Mattermost deployment on K8s

#### Kubernetes Manifests
The `k8s-manifests/` directory contains:
- PostgreSQL database deployment with persistent storage
- Mattermost Operator configuration
- Mattermost installation manifests
- NGINX Ingress configuration templates
- Detailed README with deployment instructions

See `k8s-manifests/README.md` for manual deployment steps and troubleshooting.

### Resources
- [CloudLab Documentation](https://docs.cloudlab.us/)
- [OpenStack Documentation](https://docs.openstack.org/)
- [Mattermost Installation Guide](https://docs.mattermost.com/install/install-ubuntu.html)
- [Mattermost Kubernetes Deployment](https://docs.mattermost.com/deployment-guide/server/deploy-kubernetes.html)
- [Mattermost Operator](https://github.com/mattermost/mattermost-operator)
- [Mattermost Helm Chart](https://github.com/mattermost/mattermost-helm)
- [Kubernetes Documentation](https://kubernetes.io/docs/home/)
- [NGINX Ingress Controller](https://kubernetes.github.io/ingress-nginx/)
- [DevStack Documentation](https://docs.openstack.org/devstack/latest/)
- [Magnum Documentation](https://docs.openstack.org/magnum/latest/)
- [Octavia Documentation](https://docs.openstack.org/octavia/latest/)
- [Keystone Documentation](https://docs.openstack.org/keystone/latest/)
- [Horizon Documentation](https://docs.openstack.org/horizon/latest/)
- [Nova Documentation](https://docs.openstack.org/nova/latest/)
- [Neutron Documentation](https://docs.openstack.org/neutron/latest/)
- [Glance Documentation](https://docs.openstack.org/glance/latest/)
- [Cinder Documentation](https://docs.openstack.org/cinder/latest/)
"""

#!/usr/bin/env python

# Import the necessary geni-lib libraries.
# geni.portal is used for defining user-configurable parameters.
# geni.rspec.pg is for defining the resources in the ProtoGENI RSpec format.
import geni.portal as portal
import geni.rspec.pg as pg
import geni.rspec.emulab as emulab
import geni.rspec.igext as ig

# Create a portal context object.
# This is the main interface to the CloudLab portal environment.
pc = portal.Context()

# === Profile Parameters ===
# Define user-configurable parameters that will appear
# on the CloudLab instantiation page.

# Parameter for selecting the OS image.
# Note: You can find other images and their URNs at:
# https://www.cloudlab.us/images.php
pc.defineParameter(
    "osImage", "Operating System Image",
    portal.ParameterType.IMAGE,
    "urn:publicid:IDN+emulab.net+image+emulab-ops:UBUNTU24-64-STD",
    longDescription="OS image for all nodes. Ubuntu 24.04 is used here."
)

# Parameter for selecting the physical hardware type.
# An empty string lets CloudLab choose the best available type.
# Specifying a type (e.g., 'd430', 'm510') ensures hardware homogeneity.[11]
pc.defineParameter(
    "hwType", "Hardware Type",
    portal.ParameterType.NODETYPE,
    "d430", # Default to d430 nodes.
    longDescription="Specify a hardware type for all nodes. Clear Selection for any available type."
)

# Parameter for the number of compute nodes.
# The total number of nodes will be this value + 1 (for the controller).
pc.defineParameter(
    "computeNodeCount", "Number of Compute Nodes",
    portal.ParameterType.INTEGER,
    2,
    longDescription="The number of OpenStack compute nodes to provision. Total number of nodes will be n+1 (including controller node). Recommended: 2 or more. Try increasing this if Kubernetes Cluster creation fails due to insufficient resources."
)

# Parameters for OpenStack authentication.
# These will be used in the DevStack configuration.
# Default values are provided for convenience but should be changed.
pc.defineParameter(
    "os_username", "OpenStack Username", 
    portal.ParameterType.STRING, 
    "crookshanks",
    longDescription="Custom username for OpenStack authentication (required). Defaulting to 'crookshanks'."
)

pc.defineParameter(
    "os_password", "OpenStack Password",
    portal.ParameterType.STRING,
    "chocolateFrog!",
    longDescription="Custom password for OpenStack authentication (required). Defaulting to 'chocolateFrog!'."
)

# Retrieve the bound parameters from the portal context.
params = pc.bindParameters()

# === Resource Specification ===
# Create a request object to start building the RSpec.
request = pc.makeRequestRSpec()

# Create a LAN object to connect all nodes.
lan = request.LAN("lan")

# --- Controller Node Definition ---
# This node will run all OpenStack control plane services and
# orchestrate the deployment.
controller = request.RawPC("controller")
controller.disk_image = params.osImage
if params.hwType:
    controller.hardware_type = params.hwType

# Add the controller node to the LAN.
iface_controller = controller.addInterface("if0")
lan.addInterface(iface_controller)

# Add post-boot execution services to the controller node.
# These commands are executed sequentially after the OS boots.
# The repository is cloned to /local/repository automatically.
controller.addService(pg.Execute(shell="sh", command="sudo chmod +x /local/repository/scripts/01-install-openstack.sh"))
controller.addService(pg.Execute(shell="sh", command="sudo -H /local/repository/scripts/01-install-openstack.sh {}".format(params.os_password)))
controller.addService(pg.Execute(shell="sh", command="sudo chmod +x /local/repository/scripts/02-configure-magnum.sh"))
controller.addService(pg.Execute(shell="sh", command="sudo -H /local/repository/scripts/02-configure-magnum.sh"))

# --- Compute Nodes Definition ---
# These nodes will run the OpenStack Nova compute service and host the VMs.
for i in range(params.computeNodeCount):
    node_name = "compute-{}".format(i+1)
    node = request.RawPC(node_name)
    node.disk_image = params.osImage
    if params.hwType:
        node.hardware_type = params.hwType
    
    # Add the compute node to the LAN.
    iface_compute = node.addInterface("if0")
    lan.addInterface(iface_compute)
    

# Set the instructions to be displayed on the experiment page.
# tour = ig.Tour()
# tour.Description = (ig.Tour.MARKDOWN, description)
# tour.Instructions(ig.Tour.MARKDOWN,instructions)
# request.addTour(tour)

# === Finalization ===
# Print the generated RSpec to the CloudLab portal, which will then use it
# to provision the experiment.
pc.printRequestRSpec(request)