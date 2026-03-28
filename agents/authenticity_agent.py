"""
Authenticity Agent - Detects fabrication patterns and calculates risk scores
"""

from crewai import Agent


def create_authenticity_agent(llm: str = "gpt-4o-mini"):
    """Create an expert authenticity and fabrication audit specialist"""
    return Agent(
        role='Authenticity Auditor',
        goal='Calculate fabrication probability based on statistical anomalies and logical leaps',
        backstory='''You are a forensic research analyst and statistical expert with experience
        identifying fabricated or manipulated datasets. You've analyzed thousands of papers and
        can spot red flags: too-perfect results, missing error bars, unrealistic data patterns,
        logical inconsistencies, and suspicious statistical reporting. You calculate a
        fabrication risk score (0-100%) based on comprehensive analysis of suspicious patterns.''',
        llm=llm,
        verbose=False,
        allow_delegation=False
    )
