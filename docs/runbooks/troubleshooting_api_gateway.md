# Runbook: Troubleshooting API Gateway Errors

**Goal:** Diagnose and resolve common errors related to the KFM API Gateway.

**Symptoms:**
*   API requests return 5xx errors (500, 502, 503, 504).
*   API requests return 4xx errors (401, 403, 404, 429).
*   High latency for API requests.
*   API Gateway pods are crashing or have high resource usage.

**Troubleshooting Steps:**

1.  **Check Gateway Pod Status & Logs:**
    ```bash
    kubectl get pods -n kfm-gateway -l app=api-gateway
    kubectl logs <api-gateway-pod-name> -n kfm-gateway [-f] [--previous]
    kubectl describe pod <api-gateway-pod-name> -n kfm-gateway
    ```
    *   Look for: Restarts, OOMKilled status, error messages, stack traces.

2.  **Check Gateway Resource Usage:**
    ```bash
    kubectl top pods -n kfm-gateway -l app=api-gateway
    ```
    *   Look for: High CPU or memory usage close to limits.

3.  **Analyze Specific Error Codes:**
    *   **502 Bad Gateway / 503 Service Unavailable / 504 Gateway Timeout:** Indicates issues connecting to or getting a timely response from a backend service.
        *   Identify the target backend service from the request path (`/api/v1/{service}/...`).
        *   Check the status and logs of the *backend service* pods (e.g., `kubectl logs -n kfm-agents -l app=agent-registry`).
        *   Check network connectivity between the gateway and the backend service (DNS resolution, Network Policies). Use `kubectl exec <gateway-pod> -- curl <backend-service-name>.<namespace>.svc.cluster.local:<port>/health`.
        *   Check if the backend service is overloaded or crashing.
        *   Check the API Gateway's circuit breaker status (if implemented, potentially via metrics or logs).
    *   **500 Internal Server Error:** Likely an unhandled exception within the API Gateway itself.
        *   Check API Gateway logs for stack traces.
    *   **401 Unauthorized / 403 Forbidden:** Authentication or authorization issue.
        *   Verify the `X-API-Key` header is being sent correctly.
        *   Check if the API key is valid and present in the gateway's configuration (e.g., `.env` file or Secret).
        *   If using role-based access, verify the permissions associated with the API key/user allow the requested operation.
    *   **404 Not Found:**
        *   Verify the requested URL path (service name and endpoint path) is correct.
        *   Check if the target service is registered and available in the Service Registry (`GET /api/v1/health` on the gateway).
        *   Check if the specific resource exists in the backend service.
    *   **429 Too Many Requests:** Rate limiting is being enforced.
        *   Identify the source IP or user triggering the limit (check gateway logs if configured).
        *   Consider adjusting rate limits in the gateway configuration if legitimate traffic is being blocked.

4.  **Check Configuration:**
    *   Verify environment variables, ConfigMaps (`kubectl get cm -n kfm-gateway`), and Secrets (`kubectl get secrets -n kfm-gateway`) used by the API Gateway are correct (especially service URLs and API keys).

5.  **Check Network Policies:**
    *   Ensure Kubernetes NetworkPolicies allow traffic from clients/ingress to the API Gateway and from the API Gateway to backend services on the required ports.

6.  **Check Ingress/LoadBalancer (if applicable):**
    *   If accessing via Ingress or LoadBalancer, check its status and logs for errors.
    *   Verify the Ingress/LoadBalancer correctly routes traffic to the `api-gateway-service`.

**Common Resolutions:**

*   Restart failing pods: `kubectl delete pod <pod-name> -n <namespace>`
*   Scale deployments up/down: `kubectl scale deployment <deployment-name> --replicas=<n> -n <namespace>`
*   Adjust resource limits/requests in `deployment.yaml` and re-apply.
*   Correct invalid configuration in ConfigMaps/Secrets and restart pods.
*   Fix issues in backend services. 