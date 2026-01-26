# Insurance Policy Management System

A multi-agent RAG system for insurance policy management built with Google's Agent Development Kit (ADK).

## Features

- **Customer Authentication**: Smart detection of new vs existing customers
- **Policy Management**: Full CRUD operations on Life, Property, and Vehicle policies
- **Competitor Comparison**: Compare policies with market offerings
- **Intelligent Suggestions**: Life event-based recommendations
- **Retention System**: Offers and discounts to retain customers

## Project Structure

```
insurancepolicymgmt/
├── agent.py              # Root orchestrator agent
├── agents/               # Specialized sub-agents
│   ├── auth_agent.py
│   ├── policy_manager.py
│   ├── comparison_agent.py
│   ├── suggestion_agent.py
│   ├── purchase_agent.py
│   └── retention_agent.py
├── tools/                # Business logic functions
│   ├── data_tools.py
│   ├── auth_tools.py
│   ├── policy_tools.py
│   ├── comparison_tools.py
│   ├── suggestion_tools.py
│   └── retention_tools.py
├── data/                 # JSON data stores
│   ├── customers.json
│   ├── policies.json
│   └── ...
└── docs/                 # Documentation
```

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   Edit `.env` file with your API keys

3. **Run the agent:**
   ```bash
   adk web
   ```

## Test Scenarios

| Scenario | What to Say |
|----------|-------------|
| Existing customer | "Hi, my email is john.smith@email.com" |
| View policies | "Show me my policies" |
| Compare coverage | "Compare my car insurance with others" |
| Life event | "My son is turning 18 next month" |
| Buy new policy | "I want to buy life insurance" |
| Cancel policy | "I want to cancel my vehicle insurance" |

## Data Model

See [docs/data_model.md](docs/data_model.md) for complete entity relationship diagram.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Root Agent                         │
│            (Orchestrator / Router)                   │
└───────┬─────┬─────┬─────┬─────┬─────┬───────────────┘
        │     │     │     │     │     │
   ┌────▼──┐ ┌▼───┐ ┌▼───┐ ┌▼───┐ ┌▼───┐ ┌▼────────┐
   │ Auth  │ │Pol │ │Comp│ │Sugg│ │Purc│ │Retention│
   │ Agent │ │Mgr │ │    │ │    │ │hase│ │  Agent  │
   └───────┘ └────┘ └────┘ └────┘ └────┘ └─────────┘
        │     │     │     │     │     │
   ┌────▼─────▼─────▼─────▼─────▼─────▼───────────────┐
   │              Tools Layer (Business Logic)         │
   └───────────────────────┬──────────────────────────┘
                           │
   ┌───────────────────────▼──────────────────────────┐
   │              JSON Data Store                      │
   └──────────────────────────────────────────────────┘
```
