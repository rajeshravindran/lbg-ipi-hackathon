"""
Management Tools - Mid-term adjustments, renewals, cancellation retention,
document retrieval, and coverage changes.

Provides tools for existing customers to manage their active policies
through conversational interactions.
"""

import json
import os
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")


def _load_json(filename: str) -> list:
    """Load a JSON data file from the data directory."""
    with open(os.path.join(DATA_DIR, filename), "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(filename: str, data: list) -> None:
    """Save data back to a JSON file in the data directory."""
    with open(os.path.join(DATA_DIR, filename), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _log_audit(action: str, details: str, customer_id: str, policy_id: str) -> None:
    """Append an entry to the audit log."""
    log = _load_json("audit_log.json")
    log.append({
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "customer_id": customer_id,
        "policy_id": policy_id,
        "details": details
    })
    _save_json("audit_log.json", log)


# ------------------------------------------------------------------
# Tool: Process a Mid-Term Adjustment (MTA)
# ------------------------------------------------------------------
def process_mta(
    policy_id: str,
    change_type: str,
    new_value: str,
    additional_info: str = ""
) -> dict:
    """
    Process a mid-term adjustment to an existing policy.

    Calculates the premium impact of changes and provides a breakdown
    of costs before the customer confirms.

    Args:
        policy_id: The policy to adjust.
        change_type: Type of change — 'address', 'vehicle', 'named_driver',
                     'mileage', 'usage_type', 'excess'.
        new_value: The new value to apply (e.g. new address, new VRN).
        additional_info: Any additional details needed for the change.

    Returns:
        dict with status, premium impact, new premium, and a
        confirmation message.
    """
    try:
        policies = _load_json("policies.json")
        policy = next((p for p in policies if p["policy_id"] == policy_id), None)

        if not policy:
            return {
                "status": "error",
                "error_message": f"Policy '{policy_id}' not found."
            }

        if policy["status"] != "active":
            return {
                "status": "error",
                "error_message": "Only active policies can be adjusted."
            }

        # Calculate premium adjustment based on change type
        current_premium = policy["annual_premium"]
        admin_fee = 25.00
        premium_change = 0.0
        change_description = ""

        if change_type.lower() == "address":
            # Address changes affect regional risk profile
            premium_change = 100.0  # Simplified calculation
            change_description = f"Address updated to {new_value}. Regional risk profile recalculated."

        elif change_type.lower() == "vehicle":
            premium_change = 150.0
            change_description = f"Vehicle changed to {new_value}. Premium recalculated based on new vehicle profile."

        elif change_type.lower() == "named_driver":
            premium_change = 550.0
            change_description = f"Named driver '{new_value}' added to the policy."

        elif change_type.lower() == "mileage":
            try:
                new_mileage = int(new_value)
                if new_mileage < 6000:
                    premium_change = -80.0
                elif new_mileage > 12000:
                    premium_change = 60.0
                else:
                    premium_change = 0.0
                change_description = f"Annual mileage updated to {new_mileage} miles."
            except ValueError:
                premium_change = 0.0
                change_description = f"Mileage updated to {new_value}."

        elif change_type.lower() == "usage_type":
            if "business" in new_value.lower():
                premium_change = 120.0
            else:
                premium_change = -50.0
            change_description = f"Usage type changed to {new_value}."

        elif change_type.lower() == "excess":
            try:
                new_excess = int(new_value)
                if new_excess >= 500:
                    premium_change = -80.0
                elif new_excess >= 350:
                    premium_change = -40.0
                elif new_excess <= 150:
                    premium_change = 50.0
                change_description = f"Voluntary excess changed to £{new_excess}."
            except ValueError:
                change_description = f"Excess updated to {new_value}."

        elif change_type.lower() == "coverage":
            change_description = f"Coverage updated to {new_value}."
            premium_change = 0.0

        else:
            change_description = f"{change_type.replace('_', ' ').title()} updated to {new_value}."

        # Calculate remaining days and pro-rata
        end_date = datetime.strptime(policy["end_date"], "%Y-%m-%d")
        remaining_days = (end_date - datetime.now()).days
        if remaining_days < 0:
            remaining_days = 0
        pro_rata_change = round((premium_change / 365) * remaining_days, 2)

        new_annual = round(current_premium + premium_change, 2)
        new_monthly = round(new_annual / 12, 2)

        return {
            "status": "success",
            "change_description": change_description,
            "current_annual_premium": current_premium,
            "premium_adjustment": premium_change,
            "admin_fee": admin_fee,
            "pro_rata_amount_due": pro_rata_change + admin_fee if pro_rata_change > 0 else admin_fee,
            "new_annual_premium": new_annual,
            "new_monthly_premium": new_monthly,
            "remaining_days": remaining_days,
            "message": (
                f"{change_description}\n\n"
                f"**Premium impact:** {'+'  if premium_change >= 0 else ''}£{premium_change:.2f}/year\n"
                f"**New annual premium:** £{new_annual:.2f}\n"
                f"**New monthly premium:** £{new_monthly:.2f}\n"
                f"**Administration fee:** £{admin_fee:.2f}\n\n"
                f"Would you like to proceed with this change?"
            )
        }
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Unable to process the adjustment: {str(e)}. Please try again or contact us on 0800 051 0962."
        }


# ------------------------------------------------------------------
# Tool: Process renewal with adjustments
# ------------------------------------------------------------------
def process_renewal(
    policy_id: str,
    adjustments: str = ""
) -> dict:
    """
    Process or preview a policy renewal, optionally with adjustments.

    If the customer mentions high renewal price, suggests mileage/excess
    adjustments to reduce the cost.

    Args:
        policy_id: The policy to renew.
        adjustments: Optional JSON string of adjustments, e.g.
                     '{"annual_mileage": 6000, "voluntary_excess": 500}'

    Returns:
        dict with status, renewal quote, and savings information.
    """
    policies = _load_json("policies.json")
    policy = next((p for p in policies if p["policy_id"] == policy_id), None)

    if not policy:
        return {
            "status": "error",
            "error_message": f"Policy '{policy_id}' not found."
        }

    current_premium = policy["annual_premium"]
    # Simulate a typical 5-8% renewal increase
    renewal_increase = round(current_premium * 0.06, 2)
    base_renewal = round(current_premium + renewal_increase, 2)

    savings = 0.0
    savings_details = []

    # Apply adjustments if provided
    if adjustments:
        try:
            adj_dict = json.loads(adjustments) if isinstance(adjustments, str) else adjustments
            if "annual_mileage" in adj_dict:
                new_mileage = adj_dict["annual_mileage"]
                if new_mileage < 8000:
                    saving = 35.0
                    savings += saving
                    savings_details.append(f"Reduced mileage to {new_mileage}: -£{saving}")

            if "voluntary_excess" in adj_dict:
                new_excess = adj_dict["voluntary_excess"]
                if new_excess >= 500:
                    saving = 45.0
                    savings += saving
                    savings_details.append(f"Increased excess to £{new_excess}: -£{saving}")
        except (json.JSONDecodeError, TypeError):
            pass

    final_renewal = round(base_renewal - savings, 2)
    monthly_renewal = round(final_renewal / 12, 2)

    return {
        "status": "success",
        "policy_id": policy_id,
        "current_premium": current_premium,
        "renewal_increase": renewal_increase,
        "base_renewal_premium": base_renewal,
        "savings_applied": savings,
        "savings_details": savings_details,
        "final_renewal_premium": final_renewal,
        "monthly_premium": monthly_renewal,
        "renewal_date": policy["end_date"],
        "message": (
            f"Your renewal premium is **£{final_renewal:.2f}/year** (£{monthly_renewal:.2f}/month).\n"
            + (f"You're saving **£{savings:.2f}** with your adjustments!\n" if savings > 0 else "")
            + f"Would you like to set this to auto-renew using your card ending in {policy.get('card_last_four', '****')}?"
        )
    }


# ------------------------------------------------------------------
# Tool: Get retention offers for cancellation
# ------------------------------------------------------------------
def get_retention_offers(policy_id: str) -> dict:
    """
    Retrieve retention offers to present to a customer who wants to cancel.

    The system should always present these offers before processing
    a cancellation to attempt to retain the customer.

    Args:
        policy_id: The policy the customer wants to cancel.

    Returns:
        dict with status and a list of applicable retention offers
        including discounts, enhanced cover, and incentives.
    """
    policies = _load_json("policies.json")
    policy = next((p for p in policies if p["policy_id"] == policy_id), None)

    if not policy:
        return {
            "status": "error",
            "error_message": f"Policy '{policy_id}' not found."
        }

    offers = _load_json("retention_offers.json")
    customers = _load_json("customers.json")
    customer = next((c for c in customers if c["customer_id"] == policy["customer_id"]), None)

    # Calculate tenure
    tenure_months = 0
    if customer:
        since = datetime.strptime(customer["customer_since"], "%Y-%m-%d")
        tenure_months = (datetime.now() - since).days // 30

    # Filter applicable offers
    applicable = []
    for offer in offers:
        if policy["policy_type"] in offer["applicable_policy_types"]:
            if tenure_months >= offer["min_tenure_months"]:
                applicable.append({
                    "offer_id": offer["offer_id"],
                    "title": offer["title"],
                    "description": offer["description"],
                    "type": offer["offer_type"],
                    "discount_percentage": offer["discount_percentage"],
                    "valid_for_days": offer["valid_for_days"]
                })

    return {
        "status": "success",
        "policy_id": policy_id,
        "customer_tenure_months": tenure_months,
        "offers": applicable,
        "message": (
            "Before you go, we'd hate to lose you as a valued customer. "
            "Here are some exclusive offers we can apply to your policy:"
        )
    }


# ------------------------------------------------------------------
# Tool: Get policy documents
# ------------------------------------------------------------------
def get_policy_documents(policy_id: str, doc_type: str = "") -> dict:
    """
    Retrieve policy documents such as certificates, schedules, or NCD proof.

    Args:
        policy_id: The policy to retrieve documents for.
        doc_type: Optional filter — 'certificate_of_insurance',
                  'policy_schedule', 'ncd_proof'. Leave empty for all.

    Returns:
        dict with status and list of available documents.
    """
    documents = _load_json("documents.json")
    results = [d for d in documents if d["policy_id"] == policy_id]

    if doc_type:
        results = [d for d in results if d["doc_type"] == doc_type]

    if not results:
        return {
            "status": "no_results",
            "message": f"No documents found for policy {policy_id}" + (f" of type '{doc_type}'" if doc_type else "") + "."
        }

    return {
        "status": "success",
        "documents": results,
        "message": (
            f"Found {len(results)} document(s) for policy {policy_id}. "
            "I can email these to your registered email address or provide download links."
        )
    }


# ------------------------------------------------------------------
# Tool: Update coverage levels
# ------------------------------------------------------------------
def update_coverage(policy_id: str, coverage_type: str, action: str) -> dict:
    """
    Add or remove specific coverage items from a policy.

    Args:
        policy_id: The policy to modify.
        coverage_type: The coverage to change (e.g. 'breakdown_cover',
                       'legal_expenses', 'personal_possessions').
        action: 'add' or 'remove'.

    Returns:
        dict with status, premium impact, and confirmation.
    """
    try:
        coverages = _load_json("policy_coverages.json")
        policy_covs = [c for c in coverages if c["policy_id"] == policy_id]

        # If no coverage records exist for this policy, create default ones
        if not policy_covs:
            policies = _load_json("policies.json")
            policy = next((p for p in policies if p["policy_id"] == policy_id), None)
            if not policy:
                return {
                    "status": "error",
                    "error_message": f"Policy '{policy_id}' not found."
                }

            # Determine default coverages based on policy type
            if policy["policy_type"] == "auto":
                default_types = [
                    ("breakdown_cover", False),
                    ("legal_expenses", False),
                    ("personal_possessions", False),
                    ("personal_accident", True),
                    ("courtesy_car", False),
                    ("protected_ncd", False),
                    ("new_car_replacement", False),
                ]
            else:
                default_types = [
                    ("home_emergency", False),
                    ("accidental_damage_contents", False),
                    ("family_legal_cover", False),
                    ("personal_possessions", True),
                ]

            # Generate coverage records
            max_id = 0
            for c in coverages:
                try:
                    num = int(c["coverage_id"].split("-")[-1])
                    if num > max_id:
                        max_id = num
                except (ValueError, IndexError):
                    pass

            for cov_type, included in default_types:
                max_id += 1
                new_cov = {
                    "coverage_id": f"COV-{max_id:03d}",
                    "policy_id": policy_id,
                    "coverage_type": cov_type,
                    "included": included,
                    "description": cov_type.replace("_", " ").title()
                }
                coverages.append(new_cov)

            _save_json("policy_coverages.json", coverages)
            policy_covs = [c for c in coverages if c["policy_id"] == policy_id]

        # Find the specific coverage
        target = next((c for c in policy_covs if c["coverage_type"] == coverage_type), None)

        # Premium impact estimates per coverage type
        premium_impacts = {
            "breakdown_cover": 45.00,
            "legal_expenses": 30.00,
            "personal_possessions": 35.00,
            "personal_accident": 25.00,
            "courtesy_car": 20.00,
            "home_emergency": 40.00,
            "accidental_damage_contents": 35.00,
            "accidental_damage_buildings": 35.00,
            "family_legal_cover": 25.00,
            "protected_ncd": 30.00,
            "new_car_replacement": 50.00,
            "buildings": 0.00,
            "contents": 0.00,
            "theft": 0.00,
            "fire": 0.00,
            "windscreen": 15.00,
        }

        impact = premium_impacts.get(coverage_type, 30.00)

        if action.lower() == "add":
            if target and target.get("included", False):
                return {
                    "status": "info",
                    "message": f"{coverage_type.replace('_', ' ').title()} is already included in your policy."
                }
            premium_adj = impact
            desc = f"Added {coverage_type.replace('_', ' ').title()}"
        elif action.lower() == "remove":
            if target and not target.get("included", False):
                return {
                    "status": "info",
                    "message": f"{coverage_type.replace('_', ' ').title()} is not currently on your policy."
                }
            if not target:
                return {
                    "status": "info",
                    "message": f"{coverage_type.replace('_', ' ').title()} is not available for this policy type."
                }
            premium_adj = -impact
            desc = f"Removed {coverage_type.replace('_', ' ').title()}"
        else:
            return {
                "status": "error",
                "error_message": f"Invalid action '{action}'. Please use 'add' or 'remove'."
            }

        # Update the coverage record
        if target:
            for i, c in enumerate(coverages):
                if c["coverage_id"] == target["coverage_id"]:
                    coverages[i]["included"] = (action.lower() == "add")
                    break
            _save_json("policy_coverages.json", coverages)
        else:
            # Add a new coverage record for this type
            max_id = 0
            for c in coverages:
                try:
                    num = int(c["coverage_id"].split("-")[-1])
                    if num > max_id:
                        max_id = num
                except (ValueError, IndexError):
                    pass
            new_cov = {
                "coverage_id": f"COV-{max_id + 1:03d}",
                "policy_id": policy_id,
                "coverage_type": coverage_type,
                "included": True,
                "description": coverage_type.replace("_", " ").title()
            }
            coverages.append(new_cov)
            _save_json("policy_coverages.json", coverages)

        # --- Persist premium change to the policy record ---
        policies = _load_json("policies.json")
        policy_index = next(
            (i for i, p in enumerate(policies) if p["policy_id"] == policy_id), None
        )
        if policy_index is not None:
            old_annual = policies[policy_index]["annual_premium"]
            new_annual = round(old_annual + premium_adj, 2)
            new_monthly = round(new_annual / 12, 2)
            policies[policy_index]["annual_premium"] = new_annual
            policies[policy_index]["monthly_premium"] = new_monthly
            _save_json("policies.json", policies)
            _log_audit(
                "premium_update",
                f"Coverage change ({desc}): £{old_annual:.2f} → £{new_annual:.2f}/year",
                policies[policy_index].get("customer_id", ""),
                policy_id,
            )

        # Log the coverage change
        _log_audit("coverage_change", desc, "", policy_id)

        return {
            "status": "success",
            "change": desc,
            "annual_premium_impact": premium_adj,
            "monthly_premium_impact": round(premium_adj / 12, 2),
            "new_annual_premium": new_annual if policy_index is not None else None,
            "new_monthly_premium": new_monthly if policy_index is not None else None,
            "message": (
                f"{desc}.\n"
                f"**Premium impact:** {'+'  if premium_adj > 0 else ''}£{premium_adj:.2f}/year "
                f"({'+'  if premium_adj > 0 else ''}£{premium_adj/12:.2f}/month).\n"
                + (f"**New annual premium:** £{new_annual:.2f}\n"
                   f"**New monthly premium:** £{new_monthly:.2f}\n"
                   if policy_index is not None else "")
                + "Would you like to confirm this change?"
            )
        }
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Unable to update coverage: {str(e)}. Please try again or contact us on 0800 051 0962."
        }

