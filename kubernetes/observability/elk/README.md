# ELK Stack (Elasticsearch, Logstash, Kibana)

Place Kubernetes manifests or Helm chart values (`values.yaml`) for the ELK stack components here.

**Key Components:**
- **Elasticsearch:** StatefulSet (for stable storage), Service, ConfigMap, PersistentVolumeClaims.
- **Logstash:** Deployment, Service, ConfigMap (for pipelines).
- **Kibana:** Deployment, Service.

**Configuration:**
- **Logstash Pipelines:** Define input (e.g., Beats input for Filebeat), filter (e.g., grok, json filter for structured logs), and output (Elasticsearch) stages.
- Ensure components can communicate via Kubernetes Services.
- Configure resource requests/limits appropriately. 