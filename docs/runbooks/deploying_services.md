# Runbook: Deploying KFM-AE Services to Kubernetes

**Goal:** Deploy all KFM-AE services to a target Kubernetes cluster.

**Prerequisites:**
*   `kubectl` configured for the target cluster.
*   Necessary Kubernetes namespaces created (e.g., `kfm-gateway`, `kfm-agents`, `kfm-operators`, `kfm-system`, `kfm-observability`).
*   Container images for all services built and pushed to the container registry.
*   Kubernetes manifests (`kubernetes/base/`) updated with the correct image tags.
*   Required ConfigMaps and Secrets created in the cluster (database credentials, API keys, etc.). See `kubernetes/base/config/` examples.

**Steps:**

1.  **Verify Prerequisites:** Double-check all prerequisites listed above.
2.  **Apply Base ConfigMaps/Secrets:**
    ```bash
    kubectl apply -f kubernetes/base/config/
    ```
3.  **Apply Service Manifests (Order can matter depending on dependencies):**
    ```bash
    # Apply database-dependent services first?
    kubectl apply -f kubernetes/base/agent_registry_service/
    kubectl apply -f kubernetes/base/m_operator_service/ # Check dependencies
    
    # Apply core system services
    kubectl apply -f kubernetes/base/policy_engine/
    kubectl apply -f kubernetes/base/resource_manager_service/

    # Apply Operators
    kubectl apply -f kubernetes/base/f_operator_service/
    kubectl apply -f kubernetes/base/k_operator_service/
    
    # Apply Gateway last?
    kubectl apply -f kubernetes/base/api_gateway_service/
    
    # Apply Discovery Service (if implemented)
    # kubectl apply -f kubernetes/base/discovery_service/
    ```
4.  **Apply Observability Stack (If not already running):**
    ```bash
    kubectl apply -f kubernetes/observability/
    ```
5.  **Verify Deployments:**
    *   Check rollout status for each deployment:
        ```bash
        kubectl rollout status deployment/<deployment-name> -n <namespace>
        # e.g., kubectl rollout status deployment/agent-registry-deployment -n kfm-agents
        ```
    *   Check pod status:
        ```bash
        kubectl get pods -n <namespace>
        ```
    *   Check service endpoints:
        ```bash
        kubectl get svc -n <namespace>
        ```
6.  **Initial Testing:** Perform basic health checks via the API Gateway or Admin UI to ensure services are responsive.

**Rollback:**
*   If a deployment fails, check pod logs (`kubectl logs <pod-name> -n <namespace>`).
*   Use `kubectl rollout undo deployment/<deployment-name> -n <namespace>` to revert to the previous version.
*   Delete resources in reverse order of application if a full rollback is needed. 