"""
Agents Package Initializer
===========================
Exports all sub-agents for use by the root agent.
"""

from agents.auth_agent import auth_agent
from agents.policy_manager import policy_manager_agent
from agents.comparison_agent import comparison_agent
from agents.suggestion_agent import suggestion_agent
from agents.purchase_agent import purchase_agent
from agents.retention_agent import retention_agent

__all__ = [
    'auth_agent',
    'policy_manager_agent',
    'comparison_agent',
    'suggestion_agent',
    'purchase_agent',
    'retention_agent'
]
