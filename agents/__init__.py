"""
Agents Module - All specialized evaluation agents

This module provides a collection of specialized AI agents for comprehensive
research paper evaluation using CrewAI framework.
"""

from .consistency_agent import create_consistency_agent
from .grammar_agent import create_grammar_agent
from .novelty_agent import create_novelty_agent
from .factcheck_agent import create_factcheck_agent
from .authenticity_agent import create_authenticity_agent


__all__ = [
    'create_consistency_agent',
    'create_grammar_agent',
    'create_novelty_agent',
    'create_factcheck_agent',
    'create_authenticity_agent',
]


def create_all_agents(model: str = None):
    """Factory function to create and return all agents.

    Args:
        model: LLM model name to use. Reads PRIMARY_MODEL from env if not given.
               Defaults to 'gpt-4o-mini'.
    """
    import os
    from dotenv import load_dotenv
    load_dotenv()
    llm = model or os.getenv("PRIMARY_MODEL", "gpt-4o-mini")
    return {
        'consistency': create_consistency_agent(llm=llm),
        'grammar': create_grammar_agent(llm=llm),
        'novelty': create_novelty_agent(llm=llm),
        'factcheck': create_factcheck_agent(llm=llm),
        'authenticity': create_authenticity_agent(llm=llm),
    }
