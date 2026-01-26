"""
Tools Package Initializer
==========================
Exports all tool functions for use by agents.
"""

# Data Tools
from tools.data_tools import (
    load_json,
    save_json,
    get_customer_by_id,
    get_customer_by_email,
    get_customer_by_phone,
    get_policies_by_customer,
    get_policy_by_id,
    get_policy_details,
    get_life_events_by_customer,
    get_offers,
    get_competitors,
    add_customer,
    add_transaction
)

# Authentication Tools
from tools.auth_tools import (
    lookup_customer,
    verify_existing_customer,
    register_new_customer,
    get_customer_summary
)

# Policy Tools
from tools.policy_tools import (
    create_policy,
    update_policy,
    renew_policy,
    cancel_policy,
    modify_coverage,
    list_customer_policies
)

# Comparison Tools
from tools.comparison_tools import (
    compare_policies,
    compare_customer_policy,
    get_best_quote
)

# Suggestion Tools
from tools.suggestion_tools import (
    analyze_life_events,
    get_coverage_gaps,
    get_recommendations,
    mark_event_processed,
    suggest_for_new_customer
)

# Retention Tools
from tools.retention_tools import (
    get_retention_offers,
    present_retention_offers,
    apply_retention_offer,
    get_cancellation_reasons,
    process_cancellation_with_reason,
    calculate_loyalty_score
)
