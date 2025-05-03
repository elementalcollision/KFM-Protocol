# Jaeger

Place Kubernetes manifests or Helm chart values (`values.yaml`) for Jaeger deployment here.

**Options:**
- **All-in-one:** Simple deployment for testing/development (Deployment, Service).
- **Production:** Separate components (Collector, Query, Agent DaemonSet, Storage backend like Elasticsearch or Cassandra).

**Configuration:**
- Ensure KFM-AE services are configured (via environment variables) to export traces to the Jaeger Collector service endpoint. 