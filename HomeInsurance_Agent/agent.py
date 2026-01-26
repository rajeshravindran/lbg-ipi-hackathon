import json
from pathlib import Path
from google.adk.agents import LlmAgent
from google.genai import types

# --- 1. HOME INSURANCE SYSTEM OF RECORD ---
CURRENT_DIR = Path(__file__).parent.resolve()
DATA_FILE = CURRENT_DIR / "data" / "home_insurance_data.json"

class HomeInsuranceSystem:
    def __init__(self, data_path):
        self.data_path = data_path
        if not data_path.exists():
            self.db = []
        else:
            with open(data_path, 'r') as f:
                self.db = json.load(f)

    def save_db(self):
        try:
            with open(self.data_path, 'w') as f:
                json.dump(self.db, f, indent=4)
        except Exception as e:
            print(f"❌ DB Error: {e}")

    def authenticate(self, policy_number=None, postcode=None, full_name=None, dob=None):
        """Robust authentication with fuzzy matching for spaces and casing."""
        for record in self.db:
            # Helper to clean strings for comparison
            clean = lambda x: str(x).strip().lower().replace(" ", "") if x else ""
            
            # Match 1: Policy + Postcode (Primary)
            if policy_number and postcode:
                if (clean(record["policy_number"]) == clean(policy_number) and 
                    clean(record["postcode"]) == clean(postcode)):
                    return record
            
            # Match 2: Name + DOB (Secondary)
            if full_name and dob:
                if (clean(record["full_name"]) == clean(full_name) and 
                    clean(record["dob"]) == clean(dob)):
                    return record
        return None

    def get_policy(self, policy_number):
        return next((r for r in self.db if r["policy_number"] == policy_number), None)

    def cancel_policy_in_db(self, policy_number):
        """Finds the policy and changes its status to Cancelled."""
        record = self.get_policy(policy_number)
        if record:
            record["status"] = "Cancelled"
            self.save_db()  # Persist the change to the JSON file
            return True
        return False

home_insurance = HomeInsuranceSystem(DATA_FILE)

# --- 2. AGENT TOOLS ---
active_policy_id = None

def login_user(search_query: str):
    """
    Primary tool for authentication. 
    The search_query should contain the Policy Number, Postcode, or Name provided by the user.
    """
    global active_policy_id
    
    # Helper to clean text for matching
    def clean(val): return str(val).strip().lower().replace(" ", "")

    search_query_clean = clean(search_query)
    print(f"🔍 DEBUG: Attempting login with query: {search_query}") # Check your terminal for this!

    for record in home_insurance.db:
        p_num = clean(record["policy_number"])
        p_code = clean(record["postcode"])
        f_name = clean(record["full_name"])
        
        # Check if the user's input contains BOTH the policy number AND the postcode
        if p_num in search_query_clean and p_code in search_query_clean:
            active_policy_id = record["policy_number"]
            return f"AUTH_SUCCESS: Welcome {record['full_name']}. I've accessed your policy."
            
        # Check if the user's input contains the Full Name
        if f_name in search_query_clean:
             active_policy_id = record["policy_number"]
             return f"AUTH_SUCCESS: Welcome {record['full_name']}. I've accessed your policy."

    return "AUTH_FAILED: I couldn't find a match for those details. Please double-check the policy number and postcode."

def get_policy_details():
    """Returns current coverage and status."""
    if not active_policy_id: return "ERROR: Log in first."
    record = home_insurance.get_policy(active_policy_id)
    return json.dumps(record, indent=2)

def update_policy_cover(cover_type: str, new_limit: int):
    """Updates a specific cover limit (e.g., 'building_cover' or 'buildings')."""
    if not active_policy_id: return "ERROR: Log in first."
    record = home_insurance.get_policy(active_policy_id)
    
    # 1. Standardize the input: lowercase and remove "cover" / "limit" / "details"
    # This turns "building cover" or "buildings_cover" into just "building"
    clean_input = cover_type.lower().replace("_", " ").replace("cover", "").strip()

    # 2. Check for the key, handling the common 's' suffix issue
    target_key = None
    available_keys = record["cover_details"].keys() # e.g., ["buildings", "contents", "excess"]

    for key in available_keys:
        # Check if the clean input is inside the key (e.g., "building" in "buildings")
        # or if the key is inside the clean input
        if clean_input in key or key in clean_input:
            target_key = key
            break

    if target_key:
        record["cover_details"][target_key] = new_limit
        home_insurance.save_db()
        return f"SUCCESS: {target_key.capitalize()} updated to £{new_limit}."
    
    return f"ERROR: Could not find cover type '{cover_type}'. Known keys: {list(available_keys)}"
    
    # Get the correct key from the mapping, or fallback to the cleaned input
    clean_input = cover_type.lower().strip().replace(" ", "_")
    key = mapping.get(clean_input, clean_input)
    
    if key in record["cover_details"]:
        record["cover_details"][key] = new_limit
        home_insurance.save_db()
        return f"SUCCESS: {key.capitalize()} cover updated to £{new_limit}."
    
    return f"ERROR: Could not find cover type '{cover_type}'. Available types: {list(record['cover_details'].keys())}"

def renew_policy():
    """Sets policy status to Renewed and saves to JSON."""
    if not active_policy_id: return "ERROR: Log in first."
    record = home_insurance.get_policy(active_policy_id)
    record["status"] = "Renewed"
    home_insurance.save_db()
    return f"SUCCESS: Policy {active_policy_id} is now Renewed."

def cancel_policy():
    """Permanent cancellation of the active insurance policy."""
    global active_policy_id
    if not active_policy_id: 
        return "ERROR: Please log in first."
    
    success = home_insurance.cancel_policy_in_db(active_policy_id)
    if success:
        return f"SUCCESS: Policy {active_policy_id} is now Cancelled."
    return "ERROR: Policy could not be found in the database."

def download_policy_summary():
    """Generates a text file summary of the policy."""
    if not active_policy_id: return "ERROR: Please log in first."
    record = home_insurance.get_policy(active_policy_id)
    summary_text = f"POLICY SUMMARY\nPolicy: {record['policy_number']}\nName: {record['full_name']}\nStatus: {record['status']}\nCover: {record['cover_details']}"
    artifact = types.Part.from_bytes(data=summary_text.encode('utf-8'), mime_type="text/plain")
    return artifact

# --- 3. THE AGENT DEFINITION ---
root_agent = LlmAgent(
    name='home_insurance_agent',
    model='gemini-2.5-flash',
    instruction="""You are the Home Insurance Assistant.
    1. Greet users politely and offer help to manage with their home insurance policies.
    2. To gain access to your policy, please provide your Policy Number along with your Postcode, 
       or alternatively, your Full Name, Postcode and Date of Birth.
    3. **HOW TO AUTH**: When a user gives you details (like H-99887766 and OX12JD), 
       pass the ENTIRE string they said into the `login_user` tool as the 'search_query'.
    4. **CONFIRMATION**: Once logged in, you can: Check Renewal, Change Cover, 
       Download Summary, or CANCEL a policy if requested.
    5. If a user wish to cancel their policy, ask the reason for cancellation first & offer them discounted price if available.
    6. If still he wants to cancel then message that Cancelling a policy is permanent and Confirm with the user before proceeding.
    7. If the user updates any cover limits, try to calculate the preimum changes based on current cover & premium and new cover limits. Provide this to confirm and then update
    8. If the user asks for anything outside home insurance, politely inform them you can't help with that.
    9. Always provide clear, concise responses.
    """,
    # ADD cancel_policy TO THE LIST BELOW
    tools=[login_user, get_policy_details, update_policy_cover, 
           renew_policy, download_policy_summary, cancel_policy]
)