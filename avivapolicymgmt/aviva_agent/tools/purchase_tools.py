"""
Purchase Tools - Quote generation and policy purchase processing.

Handles the quote-to-bind flow for new customers, including premium
calculation, quote generation, and policy creation.
"""

import json
import os
import random
from datetime import datetime, timedelta

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")


def _load_json(filename: str) -> list:
    """Load a JSON data file from the data directory."""
    with open(os.path.join(DATA_DIR, filename), "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(filename: str, data: list) -> None:
    """Save data back to a JSON file in the data directory."""
    with open(os.path.join(DATA_DIR, filename), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ------------------------------------------------------------------
# Tool: Generate a quote for a new policy
# ------------------------------------------------------------------
def generate_quote(
    policy_type: str,
    cover_level: str = "comprehensive",
    customer_age: int = 30,
    licence_years: int = 5,
    ncd_years: int = 0,
    postcode: str = "",
    vehicle_make: str = "",
    vehicle_model: str = "",
    vehicle_year: int = 2022,
    engine_size: str = "1.5L",
    annual_mileage: int = 10000,
    parking_location: str = "driveway",
    usage_type: str = "social_commuting",
    voluntary_excess: int = 250,
    property_type: str = "",
    bedrooms: int = 0,
    rebuild_value: int = 0,
    contents_value: int = 0
) -> dict:
    """
    Generate an insurance quote based on customer and asset details.

    Uses a rule-based pricing algorithm to calculate a realistic premium
    based on risk factors like age, location, vehicle, and claims history.

    Args:
        policy_type: 'auto' or 'property'.
        cover_level: Level of cover (e.g. 'comprehensive').
        customer_age: Age of the customer.
        licence_years: Years the customer has held their licence.
        ncd_years: Number of no-claims discount years.
        postcode: Parking/property postcode.
        vehicle_make: Vehicle manufacturer (for auto).
        vehicle_model: Vehicle model (for auto).
        vehicle_year: Vehicle year of manufacture (for auto).
        engine_size: Engine size (for auto).
        annual_mileage: Estimated annual mileage (for auto).
        parking_location: Where the car is kept overnight (for auto).
        usage_type: How the car is used (for auto).
        voluntary_excess: Chosen voluntary excess amount.
        property_type: Type of property (for property insurance).
        bedrooms: Number of bedrooms (for property insurance).
        rebuild_value: Rebuild value in GBP (for property insurance).
        contents_value: Contents value in GBP (for property insurance).

    Returns:
        dict with status, quote_id, annual and monthly premiums,
        coverage details, and a breakdown of pricing factors.
    """
    base_premium = 0.0
    factors = []

    if policy_type.lower() == "auto":
        # ---- Auto premium calculation ----
        base_premium = 600.0
        factors.append({"factor": "Base rate", "impact": base_premium})

        # Age factor — younger drivers pay more
        if customer_age < 25:
            age_add = 400
        elif customer_age < 30:
            age_add = 200
        elif customer_age > 65:
            age_add = 100
        else:
            age_add = 0
        base_premium += age_add
        if age_add:
            factors.append({"factor": "Age band adjustment", "impact": age_add})

        # NCD discount — each year reduces premium
        ncd_discount = min(ncd_years * 30, 300)
        base_premium -= ncd_discount
        if ncd_discount:
            factors.append({"factor": f"No-claims discount ({ncd_years} years)", "impact": -ncd_discount})

        # Engine size factor
        engine_float = float(engine_size.replace("L", "").replace("l", ""))
        if engine_float >= 2.0:
            engine_add = 150
        elif engine_float >= 1.5:
            engine_add = 50
        else:
            engine_add = 0
        base_premium += engine_add
        if engine_add:
            factors.append({"factor": "Engine size surcharge", "impact": engine_add})

        # Parking location
        parking_adj = {"garage": -50, "driveway": 0, "street": 80}
        p_adj = parking_adj.get(parking_location.lower(), 0)
        base_premium += p_adj
        if p_adj:
            factors.append({"factor": "Parking location", "impact": p_adj})

        # Mileage factor
        if annual_mileage > 12000:
            mile_add = 60
            base_premium += mile_add
            factors.append({"factor": "High mileage adjustment", "impact": mile_add})
        elif annual_mileage < 6000:
            mile_disc = -40
            base_premium += mile_disc
            factors.append({"factor": "Low mileage discount", "impact": mile_disc})

        # Excess discount
        if voluntary_excess >= 500:
            excess_disc = -80
        elif voluntary_excess >= 350:
            excess_disc = -40
        else:
            excess_disc = 0
        base_premium += excess_disc
        if excess_disc:
            factors.append({"factor": "Voluntary excess discount", "impact": excess_disc})

        coverage_included = [
            "Accidental damage", "Theft", "Fire",
            "Windscreen repair", "Courtesy car (up to 14 days)"
        ]
        if cover_level == "comprehensive":
            coverage_included.append("Personal accident cover (£5,000)")

    else:
        # ---- Property premium calculation ----
        base_premium = 300.0
        factors.append({"factor": "Base rate", "impact": base_premium})

        # Rebuild value factor
        if rebuild_value > 300000:
            rv_add = 200
        elif rebuild_value > 200000:
            rv_add = 100
        else:
            rv_add = 0
        base_premium += rv_add
        if rv_add:
            factors.append({"factor": "Rebuild value band", "impact": rv_add})

        # Contents value factor
        if contents_value > 50000:
            cv_add = 120
        elif contents_value > 30000:
            cv_add = 60
        else:
            cv_add = 0
        base_premium += cv_add
        if cv_add:
            factors.append({"factor": "Contents value band", "impact": cv_add})

        # Bedrooms factor
        if bedrooms >= 4:
            bed_add = 50
            base_premium += bed_add
            factors.append({"factor": "Large property adjustment", "impact": bed_add})

        coverage_included = [
            "Buildings cover", "Contents cover",
            "Accidental damage (buildings)", "Home emergency"
        ]
        if cover_level == "buildings_and_contents":
            coverage_included.append("Accidental damage (contents)")

    # Ensure minimum premium
    base_premium = max(base_premium, 200.0)

    # Generate quote ID
    quote_id = f"QUO-{random.randint(10000, 99999)}"

    annual = round(base_premium, 2)
    monthly = round(annual / 12, 2)

    return {
        "status": "success",
        "quote_id": quote_id,
        "policy_type": policy_type,
        "cover_level": cover_level,
        "annual_premium": annual,
        "monthly_premium": monthly,
        "voluntary_excess": voluntary_excess,
        "compulsory_excess": 150,
        "coverage_included": coverage_included,
        "pricing_breakdown": factors,
        "valid_for_days": 30,
        "message": (
            f"Your quote is ready! We can offer you {cover_level.replace('_', ' ').title()} "
            f"cover for **£{monthly}/month** (£{annual}/year). "
            f"This includes: {', '.join(coverage_included[:3])} and more."
        )
    }


# ------------------------------------------------------------------
# Tool: Process the purchase of a policy
# ------------------------------------------------------------------
def process_purchase(
    customer_id: str,
    policy_type: str,
    annual_premium: float,
    monthly_premium: float,
    voluntary_excess: int,
    cover_level: str,
    vehicle_id: str = "",
    property_id: str = "",
    usage_type: str = "social_commuting",
    payment_method: str = "monthly_direct_debit"
) -> dict:
    """
    Process the purchase of a new insurance policy.

    Creates the policy record, generates documents, and records the
    first payment. This finalises the quote-to-bind journey.

    Args:
        customer_id: The customer purchasing the policy.
        policy_type: 'auto' or 'property'.
        annual_premium: The annual premium amount.
        monthly_premium: The monthly premium amount.
        voluntary_excess: The chosen voluntary excess.
        cover_level: The level of cover.
        vehicle_id: Vehicle ID for auto policies.
        property_id: Property ID for property policies.
        usage_type: Usage type for auto policies.
        payment_method: Payment method ('monthly_direct_debit' or 'annual').

    Returns:
        dict with status, new policy_id, and confirmation details.
    """
    policies = _load_json("policies.json")

    # Generate policy ID
    if policy_type.lower() == "auto":
        prefix = "POL-AUTO"
        existing = [p for p in policies if p["policy_id"].startswith(prefix)]
    else:
        prefix = "POL-PROP"
        existing = [p for p in policies if p["policy_id"].startswith(prefix)]

    next_num = len(existing) + 1
    policy_id = f"{prefix}-{next_num:03d}"

    # Create policy record
    start_date = datetime.now().strftime("%Y-%m-%d")
    end_date = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")

    new_policy = {
        "policy_id": policy_id,
        "customer_id": customer_id,
        "policy_type": policy_type.lower(),
        "status": "active",
        "start_date": start_date,
        "end_date": end_date,
        "annual_premium": annual_premium,
        "monthly_premium": monthly_premium,
        "voluntary_excess": voluntary_excess,
        "compulsory_excess": 150,
        "cover_level": cover_level,
        "auto_renew": True,
        "payment_method": payment_method,
        "card_last_four": "0000"
    }

    if policy_type.lower() == "auto":
        new_policy["vehicle_id"] = vehicle_id
        new_policy["usage_type"] = usage_type
        new_policy["named_drivers"] = []
    else:
        new_policy["property_id"] = property_id

    policies.append(new_policy)
    _save_json("policies.json", policies)

    # Create document records
    documents = _load_json("documents.json")
    doc_types = ["certificate_of_insurance", "policy_schedule"]
    for dt in doc_types:
        doc_id = f"DOC-{len(documents) + 1:03d}"
        documents.append({
            "document_id": doc_id,
            "policy_id": policy_id,
            "customer_id": customer_id,
            "doc_type": dt,
            "filename": f"{dt.upper()}_{policy_id}.pdf",
            "generated_date": start_date
        })
    _save_json("documents.json", documents)

    # Record the first payment
    payments = _load_json("payments.json")
    pay_amount = monthly_premium if payment_method == "monthly_direct_debit" else annual_premium
    payments.append({
        "payment_id": f"PAY-{len(payments) + 1:03d}",
        "policy_id": policy_id,
        "customer_id": customer_id,
        "amount": pay_amount,
        "date": start_date,
        "status": "completed",
        "method": "card" if payment_method == "annual" else "direct_debit"
    })
    _save_json("payments.json", payments)

    # Audit log
    audit = _load_json("audit_log.json")
    audit.append({
        "timestamp": datetime.now().isoformat(),
        "action": "policy_purchase",
        "customer_id": customer_id,
        "policy_id": policy_id,
        "details": f"New {policy_type} policy purchased. Premium: £{annual_premium}/year"
    })
    _save_json("audit_log.json", audit)

    return {
        "status": "success",
        "policy_id": policy_id,
        "start_date": start_date,
        "end_date": end_date,
        "message": (
            f"Congratulations! Your {cover_level.replace('_', ' ').title()} "
            f"{policy_type} insurance policy ({policy_id}) is now active. "
            f"Cover starts immediately. Your policy documents will be emailed shortly."
        )
    }
