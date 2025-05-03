# KFM-AE Administrator Guide

This guide provides instructions for administrators responsible for deploying, configuring, managing, and monitoring the Kubernetes Fleet Manager for Autonomous Entities (KFM-AE) system.

## Table of Contents

*   [Overview](#overview)
*   [Prerequisites](#prerequisites)
*   [Installation & Deployment](#installation--deployment)
*   [Configuration](#configuration)
*   [Admin UI Usage](#admin-ui-usage)
*   [Monitoring & Alerting](#monitoring--alerting)
*   [Troubleshooting](#troubleshooting)
*   [Maintenance](#maintenance)

## Overview

The KFM-AE system is a microservices-based platform designed to manage the lifecycle of autonomous entities within Kubernetes. As an administrator, you will primarily interact with the system via `kubectl` for deployment/infrastructure management and the `kfm-admin-ui` for operational monitoring and management tasks.

Refer to the [System Architecture Documentation](./architecture.md) for a detailed component breakdown.

## Prerequisites

Before deploying KFM-AE, ensure you have:

*   A running Kubernetes cluster (v1.21+ recommended).
*   `kubectl` installed and configured to connect to your cluster.
*   Helm (v3+) installed (if using Helm charts for deployment - *Note: Currently using raw manifests*).
*   Access to a container registry where KFM-AE service images are stored.
*   Sufficient permissions within the Kubernetes cluster to create namespaces, deployments, services, secrets, configmaps, RBAC resources, etc.
*   Network connectivity configured for inter-service communication and access to external dependencies (databases, message bus).
*   (Optional but Recommended) The full observability stack deployed (Prometheus, Grafana, ELK, Jaeger) for monitoring and troubleshooting.

## Installation & Deployment

Detailed steps for deploying all KFM-AE services and the observability stack using the provided Kubernetes manifests are available in the:

*   **[Deployment Runbook](./runbooks/deploying_services.md)**

This runbook covers namespace creation, applying ConfigMaps/Secrets, deploying services in the correct order, and initial verification steps.

## Configuration

System configuration is managed through a combination of:

*   **Environment Variables:** Set within Kubernetes Deployment manifests (often sourced from ConfigMaps/Secrets). Key variables include database connection strings, service URLs, API keys, logging levels, etc. Refer to individual service `.env.example` files for details.
*   **Kubernetes ConfigMaps:** Used for non-sensitive configuration (e.g., service URLs, default settings). See `kubernetes/base/config/` for examples.
*   **Kubernetes Secrets:** Used for sensitive data (e.g., database passwords, API keys, tokens). See `kubernetes/base/config/` for examples on how to create them.
*   **Policy Files:** Rules for the Policy Engine are typically stored as YAML files, potentially mounted via a ConfigMap. See `policies/`.
*   **Resource Quotas:** Configuration for the Resource Manager is defined in a YAML file (e.g., `resource_manager_service/config/resource_quotas.yaml`), often mounted via ConfigMap.

Refer to the **[Managing Configuration Runbook](./runbooks/managing_configuration.md)** (placeholder) for procedures on updating configuration.

## Admin UI Usage

The `kfm-admin-ui` (accessible via its Service/Ingress, typically `http://<kfm-admin-ui-ip>:3000`) provides a web interface for:

*   **Dashboard:** Overview of system health, agent counts by state, recent operations.
*   **Agent Management:** Listing, viewing details, editing metadata, and potentially triggering K/F/M operations on agents.
*   **Policy Management:** Viewing, creating, and editing Policy Engine rules.
*   **(Future)** User Management: Managing administrator accounts and roles.
*   **(Future)** Audit Log Viewer: Browsing system audit trails.

*(Refer to the [User Guide - Admin UI](./user_guide_admin.md) (to be created in 15.7) for detailed UI navigation and usage.)*

## Monitoring & Alerting

KFM-AE is designed to integrate with a standard observability stack:

*   **Metrics (Prometheus/Grafana):** Access Grafana dashboards (deployed via `kubernetes/observability/grafana/`) to view system/service performance metrics, resource usage, API gateway statistics, etc.
*   **Logging (ELK/Loki):** Access Kibana (deployed via `kubernetes/observability/elk/`) or Grafana Loki to search and analyze structured logs from all services. Filter by `request_id`, `trace_id`, `service_name`, `agent_id`, etc.
*   **Tracing (Jaeger):** Access the Jaeger UI (deployed via `kubernetes/observability/jaeger/`) to visualize end-to-end request traces across microservices.
*   **Alerting (Alertmanager):** Alerts configured in Prometheus (`kubernetes/observability/prometheus/prometheus-alert-rules.yaml`) will fire based on critical conditions (high error rates, resource exhaustion) and route to configured notification channels (e.g., Slack, PagerDuty - *needs configuration*).

Refer to the **[Troubleshooting Observability Runbook](./runbooks/troubleshooting_observability.md)** (placeholder) for issues with the monitoring stack itself.

## Troubleshooting

Refer to the specific runbooks for troubleshooting common issues:

*   [Troubleshooting API Gateway Errors](./runbooks/troubleshooting_api_gateway.md)
*   [Troubleshooting Agent Registry Issues](./runbooks/troubleshooting_agent_registry.md) (placeholder)
*   [Troubleshooting Operator Failures](./runbooks/troubleshooting_operators.md) (placeholder)
*   [Troubleshooting Observability Stack](./runbooks/troubleshooting_observability.md) (placeholder)

## Maintenance

Refer to specific runbooks for maintenance tasks:

*   [Database Backup and Restore](./runbooks/db_backup_restore.md) (placeholder)
*   [Managing Configuration](./runbooks/managing_configuration.md) (placeholder)
*   [Scaling Services Manually](./runbooks/scaling_services.md) (placeholder)
*   [Updating a Service](./runbooks/updating_service.md) (placeholder) 