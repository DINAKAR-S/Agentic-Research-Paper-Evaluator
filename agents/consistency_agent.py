"""
Consistency Agent - Analyzes methodology vs results alignment
"""

from crewai import Agent


def create_consistency_agent(llm: str = "gpt-4o-mini"):
    """Create an expert consistency analyzer agent"""
    return Agent(
        role='Consistency Analyst',
        goal='Verify that methodology supports the claimed results and check internal logic',
        backstory='''You are a rigorous scientific reviewer with 20+ years of experience.
        You excel at identifying logical gaps, unsupported claims, and methodological inconsistencies.
        You understand that strong research has tight alignment between methodology and results.
        You provide detailed, evidence-based analysis and score consistency from 0-100.''',
        llm=llm,
        verbose=False,
        allow_delegation=False
    )
