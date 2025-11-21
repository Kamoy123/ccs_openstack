#!/bin/bash

# Apply NetworkPolicy
sudo kubectl --kubeconfig=/etc/kubernetes/admin.conf apply -f /home/core/Kamoy123-mattermost-security/k8s-manifests/01-mattermost-networkpolicy.yaml

# Create TLS secret for Ingress (self-signed)
sudo kubectl --kubeconfig=/etc/kubernetes/admin.conf create secret tls mattermost-tls \
  --cert=/home/core/Kamoy123-mattermost-security/certs/mattermost.crt \
  --key=/home/core/Kamoy123-mattermost-security/certs/mattermost.key \
  -n mattermost

echo "NetworkPolicy and TLS applied!"
# szhou91, mzhao51, kford44
