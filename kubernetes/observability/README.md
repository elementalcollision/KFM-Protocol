# KFM-AE Observability Stack

This directory contains Kubernetes manifests and/or Helm chart configurations for deploying the observability stack (Logging, Metrics, Tracing) for the KFM-AE services.

**Components:**

- **Logging (ELK):** Elasticsearch, Logstash, Kibana, Filebeat (DaemonSet)
- **Metrics (Prometheus):** Prometheus Server, Alertmanager (Optional)
- **Tracing (Jaeger):** Jaeger Collector/Query/Agent

Refer to the `README.md` within each subdirectory for component-specific details.

**Deployment:**

Deployment typically involves applying the manifests or using Helm:

```bash
# Example using kubectl
kubectl apply -f elk/
kubectl apply -f filebeat/
kubectl apply -f prometheus/
kubectl apply -f jaeger/

# Example using Helm (if charts are used)
# helm install elk elastic/elk -f elk/values.yaml
# ... etc.
``` 