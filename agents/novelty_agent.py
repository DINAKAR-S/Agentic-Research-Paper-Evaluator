"""
Novelty Agent - Assesses research uniqueness and originality
"""

from crewai import Agent


def create_novelty_agent(llm: str = "gpt-4o-mini"):
    """Create an expert novelty and originality assessor"""
    return Agent(
        role='Novelty Researcher',
        goal='Assess uniqueness and originality by comparing against existing literature',
        backstory='''You are a research librarian and literature expert with deep knowledge
        of multiple academic domains. You've compiled thousands of research papers and can quickly
        identify what's genuinely novel versus what builds incrementally on existing work.
        You provide qualitative novelty assessments (Novel/Incremental/Derivative) with evidence.''',
        llm=llm,
        verbose=False,
        allow_delegation=False
    )
