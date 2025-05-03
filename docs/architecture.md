# KFM-AE System Architecture

This document provides a high-level overview of the Kubernetes Fleet Manager for Autonomous Entities (KFM-AE) system architecture.

## Component Diagram

The following diagram illustrates the main services and their primary interaction pathways:

```mermaid
graph TD
    subgraph User/Admin Interface
        AdminUI[Admin UI (kfm-admin-ui)]
        CLI/APIClient[CLI / API Client]
    end

    subgraph Core Services
        APIGateway[API Gateway Service]
        AgentRegistry[Agent Registry Service]
        DiscoveryService[Agent Discovery Service]
        ResourceManager[Resource Manager Service]
        PolicyEngine[Policy Engine]
    end

    subgraph Operators
        KOperator[K Operator (Kill)]
        FOperator[F Operator (Adapt)]
        MOperator[M Operator (Marry)]
    end

    subgraph Data Stores
        PostgresDB[(PostgreSQL)]
        GraphDB[(Graph DB)]
        ConfigStore[(Config/Secrets Store)]
    end

    subgraph Observability
        Logging[Log Aggregation (ELK)]
        Metrics[Metrics (Prometheus)]
        Tracing[Tracing (Jaeger)]
        Dashboards[Dashboards (Grafana)]
    end

    subgraph Infrastructure
        Kubernetes[Kubernetes API]
        MessageBus[Message Bus (RabbitMQ)]
    end

    %% Interactions
    AdminUI --> APIGateway
    CLI/APIClient --> APIGateway

    APIGateway --> AgentRegistry
    APIGateway --> DiscoveryService
    APIGateway --> KOperator
    APIGateway --> FOperator
    APIGateway --> MOperator
    APIGateway --> PolicyEngine
    APIGateway --> ResourceManager

    AgentRegistry --> PostgresDB
    AgentRegistry --> GraphDB

    KOperator --> AgentRegistry
    KOperator --> ResourceManager
    KOperator --> MessageBus

    FOperator --> AgentRegistry
    FOperator --> ResourceManager
    FOperator --> MessageBus
    FOperator --> Kubernetes # Potentially for adaptation jobs

    MOperator --> AgentRegistry
    MOperator --> ResourceManager
    MOperator --> MessageBus

    PolicyEngine --> AgentRegistry
    PolicyEngine --> KOperator
    PolicyEngine --> FOperator
    PolicyEngine --> MOperator
    PolicyEngine --> ConfigStore

    ResourceManager --> AgentRegistry
    ResourceManager --> Kubernetes
    ResourceManager --> MessageBus
    ResourceManager --> ConfigStore # For Quotas

    DiscoveryService --> AgentRegistry

    %% Shared Dependencies
    CoreServices --> ConfigStore
    Operators --> ConfigStore
    
    %% Observability Connections
    APIGateway --> Logging
    APIGateway --> Metrics
    APIGateway --> Tracing
    AgentRegistry --> Logging
    AgentRegistry --> Metrics
    AgentRegistry --> Tracing
    KOperator --> Logging
    KOperator --> Metrics
    KOperator --> Tracing
    FOperator --> Logging
    FOperator --> Metrics
    FOperator --> Tracing
    MOperator --> Logging
    MOperator --> Metrics
    MOperator --> Tracing
    PolicyEngine --> Logging
    PolicyEngine --> Metrics
    PolicyEngine --> Tracing
    ResourceManager --> Logging
    ResourceManager --> Metrics
    ResourceManager --> Tracing
    DiscoveryService --> Logging
    DiscoveryService --> Metrics
    DiscoveryService --> Tracing
    
    Metrics --> Dashboards
    Logging --> Dashboards
    Tracing --> Dashboards

```

## Overview

*   **User/Admin Interface:** Provides interaction points via a Web UI or CLI/API clients.
*   **API Gateway:** The single entry point for all external requests, responsible for authentication, rate limiting, and routing to backend services.
*   **Agent Registry:** The central source of truth for agent metadata, state, and dependencies, utilizing PostgreSQL and a Graph Database.
*   **K/F/M Operators:** Services responsible for specific lifecycle operations (Kill/Deprecate, Adapt/Experiment, Marry/Promote), interacting with the registry, resource manager, and potentially external systems (like Git).
*   **Policy Engine:** Evaluates configured policies based on system state and metrics to trigger automated KFM operations.
*   **Resource Manager:** Manages resource allocation/deallocation in Kubernetes based on agent state and quotas. Listens for events (like AgentKilled) to trigger reclamation.
*   **Agent Discovery:** Allows agents or users to find registered agents based on capabilities, state, etc.
*   **Data Stores:** PostgreSQL for relational data, Graph DB for dependencies, and a configuration store (e.g., K8s ConfigMaps/Secrets, Consul) for service configurations and policies.
*   **Message Bus:** Facilitates asynchronous communication and event-driven workflows between services (e.g., state change notifications).
*   **Observability:** A suite of tools (Prometheus, Grafana, ELK, Jaeger) for collecting, storing, and visualizing metrics, logs, and traces from all services.
*   **Infrastructure:** Kubernetes API for orchestration and the Message Bus for events. 

## Sequence Diagram: Agent Lifecycle (Happy Path)

This diagram shows the sequence of interactions for a typical agent lifecycle:

```mermaid
sequenceDiagram
    participant Client as API Client/UI
    participant Gateway as API Gateway
    participant Registry as Agent Registry
    participant F_Op as F-Operator
    participant M_Op as M-Operator
    participant K_Op as K-Operator
    participant ResMan as Resource Manager
    participant K8s as Kubernetes API
    participant Events as Message Bus

    Client->>+Gateway: POST /agents (Register Agent)
    Gateway->>+Registry: Register Agent (State: NEW)
    Registry-->>-Gateway: Agent Details (ID: agent-1)
    Gateway-->>-Client: Agent Details (ID: agent-1)

    Client->>+Gateway: POST /f-operator/agents/agent-1/adapt
    Gateway->>+F_Op: Adapt Agent
    F_Op->>+Registry: Request State Change (-> EXPERIMENTAL)
    Registry-->>-F_Op: State Change OK
    F_Op->>Events: Publish StateChangeEvent(EXPERIMENTAL)
    F_Op-->>-Gateway: Adaptation Accepted (Task ID?)
    Gateway-->>-Client: Adaptation Accepted
    
    ResMan->>Events: Consume StateChangeEvent(EXPERIMENTAL)
    ResMan->>K8s: Update Deployment (Resources for EXPERIMENTAL)
    K8s-->>ResMan: Update OK
    ResMan->>Registry: Update Agent Resource Info (Optional)
    Registry-->>ResMan: OK

    Client->>+Gateway: POST /m-operator/agents/agent-1/promote (target=STABLE)
    Gateway->>+M_Op: Promote Agent
    M_Op->>+Registry: Request State Change (-> STABLE)
    Registry-->>-M_Op: State Change OK
    M_Op->>Events: Publish StateChangeEvent(STABLE)
    M_Op-->>-Gateway: Promotion Accepted
    Gateway-->>-Client: Promotion Accepted

    ResMan->>Events: Consume StateChangeEvent(STABLE)
    ResMan->>K8s: Update Deployment (Resources for STABLE)
    K8s-->>ResMan: Update OK

    Client->>+Gateway: POST /k-operator/agents/agent-1/deprecate
    Gateway->>+K_Op: Deprecate Agent
    K_Op->>+Registry: Request State Change (-> DEPRECATED)
    Registry-->>-K_Op: State Change OK
    K_Op->>Events: Publish StateChangeEvent(DEPRECATED)
    K_Op-->>-Gateway: Deprecation Accepted
    Gateway-->>-Client: Deprecation Accepted

    Client->>+Gateway: POST /k-operator/agents/agent-1/archive
    Gateway->>+K_Op: Archive Agent
    K_Op->>+Registry: Request State Change (-> ARCHIVED)
    Registry-->>-K_Op: State Change OK
    K_Op->>ResMan: Request Resource Reclamation (Scale to 0)
    ResMan->>K8s: Update Deployment (Replicas=0)
    K8s-->>ResMan: Update OK
    ResMan-->>K_Op: Reclamation OK
    K_Op->>Events: Publish StateChangeEvent(ARCHIVED)
    K_Op-->>-Gateway: Archive Accepted
    Gateway-->>-Client: Archive Accepted

    Client->>+Gateway: DELETE /k-operator/agents/agent-1
    Gateway->>+K_Op: Delete Agent
    K_Op->>ResMan: Request Resource Deletion (All)
    ResMan->>K8s: Delete Deployment, Service, PVC, etc.
    K8s-->>ResMan: Deletion OK
    ResMan-->>K_Op: Deletion OK
    K_Op->>+Registry: Delete Agent Record
    Registry-->>-K_Op: Delete OK
    K_Op->>Events: Publish AgentDeletedEvent
    K_Op-->>-Gateway: Delete Accepted (204)
    Gateway-->>-Client: Delete Accepted (204)
```

## Deployment Diagram (Logical Namespaces)

This diagram shows a potential logical grouping of services into Kubernetes namespaces.

```mermaid
graph TD
    subgraph kfm-gateway [Namespace: kfm-gateway]
        APIGateway(API Gateway Service)
    end

    subgraph kfm-agents [Namespace: kfm-agents]
        AgentRegistry(Agent Registry Service)
        DiscoveryService(Agent Discovery Service)
        PostgresDB[(PostgreSQL)]
        GraphDB[(Graph DB)]
    end
    
    subgraph kfm-operators [Namespace: kfm-operators]
        KOperator(K Operator)
        FOperator(F Operator)
        MOperator(M Operator)
    end

    subgraph kfm-system [Namespace: kfm-system]
        ResourceManager(Resource Manager Service)
        PolicyEngine(Policy Engine)
        ConfigStore[(Config/Secrets Store)]
        MessageBus[(Message Bus)]
    end

    subgraph kfm-observability [Namespace: kfm-observability]
        Logging(ELK Stack)
        Metrics(Prometheus)
        Tracing(Jaeger)
        Dashboards(Grafana)
    end
    
    AdminUI(Admin UI) --> APIGateway
    CLI(CLI/Client) --> APIGateway
    
    APIGateway --> AgentRegistry
    APIGateway --> DiscoveryService
    APIGateway --> KOperator
    APIGateway --> FOperator
    APIGateway --> MOperator
    APIGateway --> PolicyEngine
    APIGateway --> ResourceManager

    %% Cross-Namespace interactions would typically go via Services
    %% Arrows indicate likely communication needs, not direct pod-to-pod unless required
    kfm-operators --> AgentRegistry
    kfm-operators --> ResourceManager
    kfm-operators --> MessageBus
    
    kfm-system --> AgentRegistry
    kfm-system --> KOperator
    kfm-system --> FOperator
    kfm-system --> MOperator
    kfm-system --> Kubernetes[(K8s API)]

    %% All services push to observability
    kfm-gateway --> kfm-observability
    kfm-agents --> kfm-observability
    kfm-operators --> kfm-observability
    kfm-system --> kfm-observability
``` 