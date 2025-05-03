import logging
from kubernetes import client, config
from kubernetes.client.exceptions import ApiException
from typing import Optional, Dict, Any

from resource_manager_service.core.config import settings

logger = logging.getLogger(__name__)

class K8sClientError(Exception):
    """Custom exception for Kubernetes client errors."""
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code

class K8sResourceNotFoundError(K8sClientError):
    """Raised when a Kubernetes resource is not found."""
    def __init__(self, message: str):
        super().__init__(message, status_code=404)

class KubernetesClient:
    """Wrapper for Kubernetes Python client operations."""
    
    def __init__(self):
        self.load_config()
        self.apps_v1_api = client.AppsV1Api()
        self.core_v1_api = client.CoreV1Api()
        # Add other API clients as needed (e.g., client.StorageV1Api for PVCs)

    def load_config(self):
        """Loads Kubernetes configuration (in-cluster or from kubeconfig)."""
        try:
            if settings.KUBE_CONFIG_PATH:
                logger.info(f"Loading Kubernetes config from file: {settings.KUBE_CONFIG_PATH}")
                config.load_kube_config(config_file=settings.KUBE_CONFIG_PATH)
            else:
                logger.info("Loading Kubernetes in-cluster config.")
                config.load_incluster_config()
            logger.info("Kubernetes configuration loaded successfully.")
        except config.ConfigException as e:
            logger.error(f"Failed to load Kubernetes configuration: {e}", exc_info=True)
            # Depending on requirements, might want to raise an exception to halt startup
            raise K8sClientError(f"Could not configure Kubernetes client: {e}") from e
        except Exception as e: # Catch other potential file/permission errors
            logger.error(f"An unexpected error occurred loading K8s config: {e}", exc_info=True)
            raise K8sClientError(f"Unexpected error loading K8s config: {e}") from e
            
    async def patch_namespaced_deployment_scale(self, name: str, namespace: str, replicas: int):
        """Patches the replica count of a Deployment."""
        logger.info(f"Patching scale for Deployment '{name}' in namespace '{namespace}' to {replicas} replicas.")
        patch = {"spec": {"replicas": replicas}}
        try:
            api_response = self.apps_v1_api.patch_namespaced_deployment_scale(
                name=name,
                namespace=namespace,
                body=patch
            )
            logger.info(f"Successfully patched scale for Deployment '{name}'.")
            return api_response.to_dict() # Return dict representation
        except ApiException as e:
            logger.error(f"API Exception patching Deployment scale '{name}': {e.status} - {e.reason}", exc_info=True)
            if e.status == 404:
                raise K8sResourceNotFoundError(f"Deployment '{name}' not found in namespace '{namespace}'.")
            raise K8sClientError(f"Failed to patch Deployment scale: {e.reason}", status_code=e.status) from e
        except Exception as e:
            logger.error(f"Unexpected error patching Deployment scale '{name}': {e}", exc_info=True)
            raise K8sClientError(f"Unexpected error: {e}") from e

    async def patch_namespaced_deployment_resources(self, name: str, namespace: str, container_name: str, resources: Dict[str, Any]):
        """Patches the resource requests/limits for a specific container in a Deployment."""
        logger.info(f"Patching resources for container '{container_name}' in Deployment '{name}/{namespace}'.")
        
        # Find the container index
        try:
            deployment = self.apps_v1_api.read_namespaced_deployment(name=name, namespace=namespace)
            container_index = -1
            for i, container in enumerate(deployment.spec.template.spec.containers):
                if container.name == container_name:
                    container_index = i
                    break
            
            if container_index == -1:
                raise K8sClientError(f"Container '{container_name}' not found in Deployment '{name}/{namespace}'.")

            # Create a strategic merge patch
            patch = {
                "spec": {
                    "template": {
                        "spec": {
                            "containers": [
                                {
                                    "name": container_name,
                                    "resources": resources
                                }
                            ]
                        }
                    }
                }
            }

            api_response = self.apps_v1_api.patch_namespaced_deployment(
                name=name,
                namespace=namespace,
                body=patch
            )
            logger.info(f"Successfully patched resources for container '{container_name}' in Deployment '{name}'.")
            return api_response.to_dict()
        except ApiException as e:
            logger.error(f"API Exception patching Deployment resources '{name}': {e.status} - {e.reason}", exc_info=True)
            if e.status == 404:
                raise K8sResourceNotFoundError(f"Deployment '{name}' not found in namespace '{namespace}'.")
            raise K8sClientError(f"Failed to patch Deployment resources: {e.reason}", status_code=e.status) from e
        except Exception as e:
            logger.error(f"Unexpected error patching Deployment resources '{name}': {e}", exc_info=True)
            raise K8sClientError(f"Unexpected error: {e}") from e

    async def delete_namespaced_deployment(self, name: str, namespace: str):
        """Deletes a Deployment."""
        logger.warning(f"Deleting Deployment '{name}' in namespace '{namespace}'.")
        try:
            api_response = self.apps_v1_api.delete_namespaced_deployment(
                name=name,
                namespace=namespace,
                body=client.V1DeleteOptions(
                    propagation_policy='Foreground', # Ensures dependent objects are deleted first
                    grace_period_seconds=5
                )
            )
            logger.info(f"Successfully initiated deletion for Deployment '{name}'. Status: {api_response.status}")
            return api_response.to_dict()
        except ApiException as e:
            logger.error(f"API Exception deleting Deployment '{name}': {e.status} - {e.reason}", exc_info=True)
            if e.status == 404:
                logger.warning(f"Deployment '{name}' already deleted or not found.")
                return None # Or raise specific error?
            raise K8sClientError(f"Failed to delete Deployment: {e.reason}", status_code=e.status) from e
        except Exception as e:
            logger.error(f"Unexpected error deleting Deployment '{name}': {e}", exc_info=True)
            raise K8sClientError(f"Unexpected error: {e}") from e

    # Add methods for other resources (Services, PVCs, StatefulSets) as needed
    # e.g., delete_namespaced_service, delete_namespaced_persistent_volume_claim

# Singleton instance (optional, can also use FastAPI dependency injection)
# k8s_client = KubernetesClient() 