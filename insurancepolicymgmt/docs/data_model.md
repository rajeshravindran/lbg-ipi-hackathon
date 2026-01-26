# Insurance Policy Management System - Data Model

## Overview
This document describes the data model for the insurance policy management system.

## Entity Relationship Diagram

```mermaid
erDiagram
    CUSTOMER ||--o{ POLICY : has
    CUSTOMER ||--o{ LIFE_EVENT : experiences
    POLICY ||--o{ TRANSACTION : generates
    POLICY ||--|| LIFE_POLICY : extends
    POLICY ||--|| PROPERTY_POLICY : extends
    POLICY ||--|| VEHICLE_POLICY : extends
    OFFER }o--o{ CUSTOMER : "applies to"

    CUSTOMER {
        string id PK
        string name
        string email UK
        string phone UK
        date dob
        string ssn_last4
        string customer_type
        datetime registration_date
        string address
    }

    POLICY {
        string id PK
        string customer_id FK
        string policy_type
        string status
        float coverage_amount
        float monthly_premium
        date start_date
        date end_date
        datetime created_at
        datetime updated_at
    }

    LIFE_POLICY {
        string policy_id PK_FK
        string beneficiary_name
        string beneficiary_relation
        int term_years
        float death_benefit
        bool smoker
        string health_category
    }

    PROPERTY_POLICY {
        string policy_id PK_FK
        string property_address
        string property_type
        float property_value
        float deductible
        bool flood_coverage
        bool fire_coverage
    }

    VEHICLE_POLICY {
        string policy_id PK_FK
        string vehicle_vin
        string make
        string model
        int year
        string coverage_type
        float deductible
    }

    LIFE_EVENT {
        string id PK
        string customer_id FK
        string event_type
        date event_date
        bool processed
        string suggested_policies
    }

    TRANSACTION {
        string id PK
        string policy_id FK
        string type
        float amount
        datetime transaction_date
        string description
    }

    OFFER {
        string id PK
        string name
        string offer_type
        float discount_percent
        string description
        date valid_from
        date valid_until
        bool active
    }
```

## Entity Descriptions

### Customer
Primary entity representing both existing and new customers.
- **customer_type**: Determines authentication flow and available actions
- **ssn_last4**: Used for identity verification of existing customers

### Policy
Base policy entity with common attributes across all policy types.
- **status**: Tracks policy lifecycle (active → cancelled/expired)
- Linked to specific policy type through inheritance pattern

### Life/Property/Vehicle Policy
Type-specific policy details extending the base Policy entity.

### Life Event
Tracks customer life events for proactive policy suggestions.
- **processed**: Indicates if suggestions were already made
- **suggested_policies**: JSON array of policy types to suggest

### Transaction
Audit trail of all policy-related financial activities.

### Offer
Promotional offers used primarily for customer retention.
- **offer_type**: retention offers target cancelling customers
