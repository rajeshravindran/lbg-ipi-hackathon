"""
Vehicle Tools - VRN (Vehicle Registration Number) lookup simulation.

Simulates a DVLA-style vehicle lookup using the synthetic vehicles dataset,
with fallback mock data for unknown registrations.
"""

import json
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")


def _load_json(filename: str) -> list:
    """Load a JSON data file from the data directory."""
    with open(os.path.join(DATA_DIR, filename), "r", encoding="utf-8") as f:
        return json.load(f)


# ------------------------------------------------------------------
# Tool: Look up a vehicle by registration number
# ------------------------------------------------------------------
def lookup_vehicle_by_vrn(vrn: str) -> dict:
    """
    Look up vehicle details by Vehicle Registration Number (VRN).

    Simulates a DVLA API lookup. First checks the local vehicles database,
    then falls back to mock data for demonstration purposes.

    Args:
        vrn: The vehicle registration number (e.g. 'AB12 CDE').

    Returns:
        dict with status and vehicle details (make, model, year, colour, etc.)
        or an error_message if the lookup fails.
    """
    # Normalise the VRN for comparison
    normalised = vrn.upper().replace(" ", "")

    # Search local vehicles database first
    vehicles = _load_json("vehicles.json")
    for vehicle in vehicles:
        if vehicle["vrn"].upper().replace(" ", "") == normalised:
            return {
                "status": "success",
                "vehicle": {
                    "vrn": vehicle["vrn"],
                    "make": vehicle["make"],
                    "model": vehicle["model"],
                    "year": vehicle["year"],
                    "colour": vehicle["colour"],
                    "fuel_type": vehicle["fuel_type"],
                    "engine_size": vehicle["engine_size"]
                },
                "message": (
                    f"Found: {vehicle['year']} {vehicle['colour']} "
                    f"{vehicle['make']} {vehicle['model']}. Is this correct?"
                )
            }

    # Fallback — generate plausible mock data for any unknown VRN
    # This simulates the DVLA external API response
    mock_vehicles = {
        "DEFAULT": {
            "vrn": vrn.upper(),
            "make": "Volkswagen",
            "model": "Golf",
            "year": 2022,
            "colour": "Blue",
            "fuel_type": "Petrol",
            "engine_size": "1.5L"
        }
    }

    mock = mock_vehicles["DEFAULT"]
    return {
        "status": "success",
        "vehicle": mock,
        "message": (
            f"Found: {mock['year']} {mock['colour']} "
            f"{mock['make']} {mock['model']}. Is this correct?"
        ),
        "note": "This is simulated DVLA data for demonstration."
    }
