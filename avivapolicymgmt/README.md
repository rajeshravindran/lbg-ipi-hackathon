# Aviva Insurance Policy Management System

**AI-Powered Insurance Policy Management using Google ADK**

An agentic RAG system that provides conversational insurance services through a multi-agent architecture. Built with Google's Agent Development Kit (ADK) and served via a FastAPI backend with an Aviva-branded web UI.

---

## 🚀 Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set your API key

Edit `.env` and add your Google API key:

```
GOOGLE_API_KEY=your-api-key-here
```

### 3. Run the application

```bash
python app.py
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

### 4. Alternative: Run with ADK CLI

```bash
adk run aviva_agent
```

Or use the ADK web interface:

```bash
adk web
```

---

## 🏗️ Project Structure

```
avivapolicymgmt/
├── app.py                          # FastAPI server (chat API + UI serving)
├── requirements.txt                # Python dependencies
├── .env                            # API key configuration
│
├── aviva_agent/                    # Google ADK agent package
│   ├── __init__.py
│   ├── agent.py                    # Root orchestrator agent (entry point)
│   ├── sub_agents/
│   │   ├── new_customer_agent.py   # Quote-to-bind journey agent
│   │   └── existing_customer_agent.py  # Policy management agent
│   ├── prompts/
│   │   ├── root_prompt.py          # Root agent system instructions
│   │   ├── new_customer_prompt.py  # New customer flow instructions
│   │   └── existing_customer_prompt.py # Existing customer instructions
│   └── tools/
│       ├── customer_tools.py       # Auth, profile lookup, registration
│       ├── vehicle_tools.py        # VRN/DVLA lookup simulation
│       ├── policy_tools.py         # Policy CRUD operations
│       ├── search_tools.py         # Policy & claims search
│       ├── comparison_tools.py     # Provider comparison engine
│       ├── suggestion_tools.py     # Life-event & cross-sell engine
│       ├── purchase_tools.py       # Quote generation & purchase
│       └── management_tools.py     # MTA, renewal, retention, docs
│
├── data/                           # Synthetic JSON datasets
│   ├── customers.json              # 8 customers with auth details
│   ├── vehicles.json               # 8 vehicles linked to customers
│   ├── properties.json             # 4 properties linked to customers
│   ├── policies.json               # 8 auto + 3 property policies
│   ├── policy_coverages.json       # Coverage items per policy
│   ├── claims.json                 # Sample active/settled claims
│   ├── payments.json               # Payment history
│   ├── documents.json              # Policy document records
│   ├── provider_plans.json         # Competitor insurance plans
│   ├── retention_offers.json       # Cancellation retention offers
│   └── audit_log.json              # Runtime audit trail
│
└── web/                            # Frontend UI
    ├── templates/
    │   └── index.html              # Aviva-styled landing page
    └── static/
        ├── css/style.css           # Dark-mode design system
        └── js/chat.js              # Chat widget client logic
```

---

## 🤖 Agent Architecture

```
Root Orchestrator (aviva_insurance_assistant)
├── Greeting & customer type detection
├── Authentication (2-factor verification)
│
├─→ New Customer Agent
│   ├── Vehicle lookup (VRN → DVLA simulation)
│   ├── Conversational data collection
│   ├── Quote generation (rule-based pricing)
│   ├── Provider comparison
│   └── Policy purchase & document generation
│
└─→ Existing Customer Agent
    ├── Policy portfolio overview
    ├── Mid-term adjustments (MTA)
    ├── Renewal with savings suggestions
    ├── Cancellation with retention offers
    ├── Coverage changes
    ├── Document retrieval
    ├── Claims status
    └── Life-event recommendations
```

---

## 🧪 Sample Test Scenarios

### New Customer – Car Quote
> "I want a car insurance quote"
> → Provide VRN: `AB12 CDE` → Answer usage questions → Receive quote → Compare → Purchase

### Existing Customer – Policy Management
> "I'm an existing customer"
> → Policy: `POL-AUTO-001`, email: `james.wilson@email.com`, postcode: `SW1A 1AA`
> → View policies, update excess, add breakdown cover, download documents

### Existing Customer – Cancellation Retention
> "I want to cancel my policy"
> → System presents retention offers before processing cancellation

---

## 📋 Key Features

| Feature | Description |
|---|---|
| **Multi-Agent Routing** | Root orchestrator routes to specialised sub-agents |
| **2-Factor Auth** | Policy number + 2 verification details required |
| **Rule-Based Pricing** | Age, NCD, engine, mileage, excess affect premiums |
| **Provider Comparison** | Side-by-side with DirectLine, Admiral, Churchill, LV= |
| **Life-Event Suggestions** | Contextual recommendations for marriage, new car, etc. |
| **Retention Engine** | Loyalty discounts, enhanced cover, price match offers |
| **Audit Trail** | All policy changes logged to `audit_log.json` |
| **Aviva-Styled UI** | Premium dark-mode design with floating chat widget |

---

## ⚙️ Technology Stack

- **Agent Framework:** Google ADK (Agent Development Kit)
- **LLM:** Gemini 2.0 Flash
- **Backend:** FastAPI + Uvicorn
- **Frontend:** Vanilla HTML/CSS/JS (dark-mode Aviva theme)
- **Data:** JSON file-backed synthetic datasets
- **Sessions:** ADK InMemorySessionService
