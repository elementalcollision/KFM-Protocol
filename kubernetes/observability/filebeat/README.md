# Filebeat (Log Shipper)

Place Kubernetes manifests for Filebeat deployment here.

Typically deployed as a **DaemonSet** to run on every node.

**Key Components:**
- DaemonSet
- ConfigMap (`filebeat.yml`)
- RBAC (ServiceAccount, ClusterRole, ClusterRoleBinding - to read pod logs)

**Configuration (`filebeat.yml`):**
- Configure inputs to autodiscover and read container logs (e.g., from `/var/log/containers/*.log`).
- Use hints-based autodiscovery or Kubernetes provider to enrich logs with pod/node metadata.
- Configure outputs to send logs to the Logstash service endpoint. 