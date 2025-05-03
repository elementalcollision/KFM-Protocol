# Promotion Workflow

This document describes the promotion process managed by the M Operator Service.

## Overview

(Add high-level description)

## Approval Workflow

1.  **Initiation:** A promotion review is initiated (e.g., via POST `/api/v1/promotions/reviews`).
2.  **Stakeholder Assignment:** Based on the `workflow_type` (defined in `config/default-config.yaml`), the `promotion_service` identifies required stakeholder roles and creates pending `PromotionApproval` records.
3.  **Notification:** Stakeholders are notified (placeholder).
4.  **Sign-off:** Stakeholders submit their approval/rejection via POST `/api/v1/promotions/reviews/{review_id}/approvals`.
5.  **Status Update:** The `promotion_service` updates the `PromotionApproval` record.
6.  **Completion Check:** The service checks if all required approvals are met or if a rejection occurred.
7.  **Review Update:** The `PromotionReview` status is updated to `APPROVED` or `REJECTED`.
8.  **Promotion Actions (if APPROVED):** Triggers actions defined in Subtask 7.4 (placeholder).

## Sequence Diagram

```mermaid
sequenceDiagram
    participant User
    participant M_Operator_API
    participant PromotionService
    participant CRUD
    participant NotificationService

    User->>+M_Operator_API: POST /reviews (initiate)
    M_Operator_API->>+PromotionService: initiate_promotion_review_workflow(review_id)
    PromotionService->>+CRUD: get_promotion_review(review_id)
    CRUD-->>-PromotionService: review_data
    PromotionService->>PromotionService: _get_stakeholders_for_review(review)
    loop Assign Approvals
        PromotionService->>+CRUD: create_approval(stakeholder)
        CRUD-->>-PromotionService: 
    end
    PromotionService->>+NotificationService: _notify_stakeholders(review_id, stakeholders)
    NotificationService-->>-PromotionService: 
    PromotionService-->>-M_Operator_API: review_response (status: INITIATED/APPROVAL_PENDING)
    M_Operator_API-->>-User: 201 Created

    Note over User, NotificationService: Stakeholder Receives Notification

    User->>+M_Operator_API: POST /reviews/{id}/approvals (submit)
    M_Operator_API->>+PromotionService: submit_approval(review_id, stakeholder_id, status)
    PromotionService->>+CRUD: get_pending_approval(...)
    CRUD-->>-PromotionService: pending_approval_record
    PromotionService->>+CRUD: update_approval_status(...)
    CRUD-->>-PromotionService: updated_approval_record
    PromotionService->>+PromotionService: check_review_signoff_completion(review_id)
    PromotionService->>+CRUD: get_promotion_review(review_id)
    CRUD-->>-PromotionService: review_data
    PromotionService->>+CRUD: get_approvals_by_review(review_id)
    CRUD-->>-PromotionService: all_approvals
    alt All Approved / Threshold Met
        PromotionService->>+CRUD: update_promotion_review(status=APPROVED)
        CRUD-->>-PromotionService: 
        PromotionService->>PromotionService: _trigger_promotion_actions(review)
    else Rejected
        PromotionService->>+CRUD: update_promotion_review(status=REJECTED)
        CRUD-->>-PromotionService: 
    end
    PromotionService-->>-M_Operator_API: updated_review_response
    M_Operator_API-->>-User: 200 OK

```

## Configuration

Approval workflows are defined in `config/default-config.yaml` under the `approval_workflows` key. 