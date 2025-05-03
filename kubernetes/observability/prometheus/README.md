# Prometheus

Place Kubernetes manifests or Helm chart values (`values.yaml`) for Prometheus deployment here.

**Key Components:**
- Prometheus Server (Deployment/StatefulSet)
- Service Discovery Config (ConfigMap)
- Alertmanager (Optional, often deployed separately)
- RBAC (ServiceAccount, ClusterRole, ClusterRoleBinding)

**Configuration:**
- The `prometheus.yml` (in ConfigMap) needs `scrape_configs` to target the `/metrics` endpoints of KFM-AE services.
- Use Kubernetes service discovery (e.g., targeting services with specific labels or annotations). 