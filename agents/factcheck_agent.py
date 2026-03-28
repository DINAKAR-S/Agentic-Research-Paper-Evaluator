"""
Fact-Check Agent - Verifies claims, formulas, data, and citations
"""

from crewai import Agent


def create_factcheck_agent(llm: str = "gpt-4o-mini"):
    """Create an expert fact verification specialist"""
    return Agent(
        role='Fact Verification Specialist',
        goal='Verify cited constants, formulas, data, and historical facts',
        backstory='''You are a meticulous fact-checker and domain expert with advanced knowledge
        in mathematics, physics, biology, computer science, and statistics. You validate every claim
        by cross-referencing established knowledge. You check mathematical formulas, physical
        constants, statistical methods, and cited facts. You maintain a detailed log of
        verified vs unverified vs questionable claims.''',
        llm=llm,
        verbose=False,
        allow_delegation=False
    )
