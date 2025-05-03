from prometheus_client import Counter, Gauge, Histogram, CollectorRegistry

# Create a registry for custom metrics (optional, but good practice)
# Using the default registry is also possible: from prometheus_client import REGISTRY
REGISTRY = CollectorRegistry()

# --- Define Custom Metrics ---

# Counter for resource allocation attempts/results
RESOURCE_ALLOCATION_ATTEMPTS = Counter(
    'kfm_resource_allocation_attempts_total',
    'Total attempts to allocate/modify resources for an agent',
    ['agent_id', 'agent_state', 'resource_type', 'status'], # Labels: e.g., status='success'/'failure'/'quota_exceeded'
    registry=REGISTRY
)

# Counter for resource reclamation attempts/results
RESOURCE_RECLAMATION_ATTEMPTS = Counter(
    'kfm_resource_reclamation_attempts_total',
    'Total attempts to reclaim resources for an agent',
    ['agent_id', 'agent_state', 'resource_type', 'status'], # Labels: e.g., status='success'/'failure'/'scaled_down'/'deleted'
    registry=REGISTRY
)

# Gauge for current quota utilization (potentially set by a background job)
# This is more complex as it requires knowing total quota vs current usage
# For now, we can track allocation counts/sizes instead, or implement this later.
# RESOURCE_QUOTA_UTILIZATION = Gauge(
#     'kfm_resource_quota_utilization_percent',
#     'Current resource quota utilization percentage',
#     ['quota_scope', 'resource_type'], # e.g., scope='state_EXPERIMENTAL', resource='cpu'
#     registry=REGISTRY
# )

# Histogram for the duration of resource management operations
RESOURCE_OPERATION_DURATION = Histogram(
    'kfm_resource_operation_duration_seconds',
    'Latency of resource management operations (allocation/reclamation)',
    ['operation_type', 'resource_type'], # e.g., operation='allocate'/'reclaim', resource='deployment'
    registry=REGISTRY,
    # Define buckets appropriate for expected operation times
    buckets=(0.1, 0.5, 1, 2.5, 5, 10, 30, 60) 
)

# TODO: Add more specific metrics as the service logic develops.

# Example usage (to be called from service logic):
# RESOURCE_ALLOCATION_ATTEMPTS.labels(agent_id='xyz', agent_state='STABLE', resource_type='cpu', status='success').inc()
# with RESOURCE_OPERATION_DURATION.labels(operation_type='reclaim', resource_type='deployment').time():
#     # Perform the K8s deletion call
#     pass 