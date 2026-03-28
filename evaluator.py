"""
Main Evaluator - Orchestrates all agents using CrewAI

This module coordinates multiple specialized agents to perform comprehensive
automated peer review of arXiv research papers.
"""

import os
import tempfile
from typing import Dict, List
from datetime import datetime
from pathlib import Path
from loguru import logger
from crewai import Task, Crew, Process

from core.llm_manager import get_llm_manager
from core.arxiv_client import ArxivClient
from agents import create_all_agents


class ArxivEvaluator:
    """
    Main orchestrator for comprehensive research paper evaluation.
    
    Coordinates 5 specialized agents to perform multi-dimensional analysis:
    - Consistency: Methodology vs Results alignment
    - Grammar: Writing quality and professionalism
    - Novelty: Uniqueness vs existing literature  
    - Fact-Check: Verification of claims and data
    - Authenticity: Fabrication probability assessment
    """
    
    def __init__(self):
        self.llm_manager = get_llm_manager()
        self.arxiv_client = ArxivClient()
        self.agents = create_all_agents()
    
    def _create_tasks(self, paper_data: Dict) -> List[Task]:
        """Create tasks for all agents"""
        
        # Prepare context
        title = paper_data['title']
        abstract = paper_data['abstract']
        full_text = paper_data['full_text']
        sections = paper_data['sections']
        
        # Chunk text if needed
        methodology_text = sections.get('Methodology', sections.get('Method', ''))
        results_text = sections.get('Results', sections.get('Experiments', ''))
        
        tasks = []
        
        # Task 1: Consistency Analysis
        consistency_task = Task(
            description=f"""Analyze the consistency between methodology and results for this paper:

Title: {title}

Abstract: {abstract}

Methodology Section:
{methodology_text[:8000]}

Results Section:
{results_text[:8000]}

Score the consistency from 0-100 and identify:
1. Claims that are well-supported by methodology
2. Claims that lack methodological support
3. Logical gaps or inconsistencies
4. Methodological flaws

Format your response as:
CONSISTENCY SCORE: [0-100]
SUPPORTED CLAIMS: [list]
UNSUPPORTED CLAIMS: [list]
ISSUES: [list]
""",
            agent=self.agents['consistency'],
            expected_output="Consistency score (0-100) with detailed analysis of methodology-results alignment"
        )
        tasks.append(consistency_task)
        
        # Task 2: Grammar & Language Quality
        grammar_task = Task(
            description=f"""Evaluate the language quality and professional tone of this paper:

Title: {title}

Text sample (first 6000 chars):
{full_text[:6000]}

Assess:
1. Grammar and syntax errors
2. Clarity of writing
3. Professional academic tone
4. Sentence structure quality

Rate as: HIGH / MEDIUM / LOW
Provide specific examples of issues found.

Format your response as:
GRAMMAR RATING: [HIGH/MEDIUM/LOW]
TONE QUALITY: [description]
CLARITY SCORE: [description]
MAJOR ISSUES: [list with examples]
MINOR ISSUES: [list]
""",
            agent=self.agents['grammar'],
            expected_output="Grammar rating (HIGH/MEDIUM/LOW) with detailed quality assessment"
        )
        tasks.append(grammar_task)
        
        # Task 3: Novelty Assessment
        novelty_task = Task(
            description=f"""Assess the novelty and originality of this research:

Title: {title}
Abstract: {abstract}
Categories: {paper_data.get('categories', [])}

Based on your knowledge of similar work:
1. Identify the main contributions claimed
2. List similar prior work (if known)
3. Determine what is genuinely novel
4. Assess the significance of contributions

Format your response as:
NOVELTY INDEX: [Novel / Incremental / Derivative]
MAIN CONTRIBUTIONS: [list]
SIMILAR WORK: [list of related papers/topics]
NOVEL ASPECTS: [what's genuinely new]
INCREMENTAL ASPECTS: [what builds on existing work]
""",
            agent=self.agents['novelty'],
            expected_output="Novelty assessment with comparison to existing literature"
        )
        tasks.append(novelty_task)
        
        # Task 4: Fact Checking
        factcheck_task = Task(
            description=f"""Verify factual claims, formulas, and data in this paper:

Title: {title}

Text sample:
{full_text[:8000]}

Check:
1. Mathematical formulas (if any)
2. Cited constants or values
3. Statistical methods mentioned
4. Historical facts or established results
5. Dataset descriptions

Create a fact-check log.

Format your response as:
VERIFIED CLAIMS: [list with ✓]
UNVERIFIED CLAIMS: [list with ⚠]
QUESTIONABLE CLAIMS: [list with ✗]
FORMULA CHECK: [status]
DATA INTEGRITY: [assessment]
""",
            agent=self.agents['factcheck'],
            expected_output="Fact-check log categorizing verified and unverified claims"
        )
        tasks.append(factcheck_task)
        
        # Task 5: Authenticity Audit
        authenticity_task = Task(
            description=f"""Calculate the fabrication probability for this research:

Title: {title}
Abstract: {abstract}

Results section:
{results_text[:6000]}

Look for red flags:
1. Unrealistically perfect results
2. Missing error bars or uncertainty measures
3. Too-convenient data patterns
4. Logical leaps without justification
5. Inconsistent statistical reporting
6. Missing experimental details

Calculate fabrication risk as a percentage (0-100%).

Format your response as:
FABRICATION RISK: [0-100%]
RED FLAGS: [list]
SUSPICIOUS PATTERNS: [list]
CREDIBILITY FACTORS: [positive indicators]
RISK ASSESSMENT: [Low/Medium/High]
""",
            agent=self.agents['authenticity'],
            expected_output="Fabrication probability score (0-100%) with risk assessment"
        )
        tasks.append(authenticity_task)
        
        return tasks
    
    def evaluate_paper(self, arxiv_id: str) -> Dict:
        """
        Main evaluation pipeline
        
        Args:
            arxiv_id: arXiv paper ID or URL
            
        Returns:
            Comprehensive evaluation report
        """
        logger.info(f"Starting evaluation for {arxiv_id}")
        start_time = datetime.now()
        
        # Step 1: Download and parse paper
        logger.info("Step 1: Downloading and parsing paper...")
        paper_data = self.arxiv_client.get_paper(arxiv_id)
        
        # Step 2: Create and execute tasks
        logger.info("Step 2: Creating evaluation tasks...")
        tasks = self._create_tasks(paper_data)
        
        # Create crew
        logger.info("Step 3: Assembling agent crew...")
        crew = Crew(
            agents=[
                self.agents['consistency'],
                self.agents['grammar'],
                self.agents['novelty'],
                self.agents['factcheck'],
                self.agents['authenticity']
            ],
            tasks=tasks,
            process=Process.sequential,  # Run agents in sequence
            verbose=False
        )
        
        # Execute evaluation
        logger.info("Step 4: Running multi-agent evaluation...")
        result = crew.kickoff()
        
        # Step 5: Compile final report with task outputs
        logger.info("Step 5: Compiling final report...")
        report = self._compile_report(paper_data, tasks, result, start_time)
        
        logger.info(f"Evaluation complete in {(datetime.now() - start_time).total_seconds():.1f}s")
        
        return report
    
    def _compile_report(self, paper_data: Dict, tasks: List, agent_results: any, start_time: datetime) -> Dict:
        """
        Compile final evaluation report from all agent outputs.
        
        Extracts scores and findings from each task output directly.
        """
        
        # Initialize findings and scores with defaults
        findings = {
            'consistency_analysis': '',
            'grammar_analysis': '',
            'novelty_analysis': '',
            'factcheck_log': '',
            'authenticity_analysis': ''
        }
        
        scores = {
            'consistency': 50,
            'grammar': 'MEDIUM',
            'novelty': 'Incremental',
            'authenticity': 50
        }
        
        # Access individual task outputs from the tasks list
        # In CrewAI, each task has an output attribute after execution
        
        # Task 0: Consistency Analysis
        if len(tasks) > 0 and hasattr(tasks[0], 'output'):
            consistency_text = str(tasks[0].output.raw if hasattr(tasks[0].output, 'raw') else tasks[0].output)
            findings['consistency_analysis'] = consistency_text[:3000]
            scores['consistency'] = self._extract_score(consistency_text, 'CONSISTENCY SCORE', 50)
            logger.info(f"Consistency Score: {scores['consistency']}")
        
        # Task 1: Grammar Analysis  
        if len(tasks) > 1 and hasattr(tasks[1], 'output'):
            grammar_text = str(tasks[1].output.raw if hasattr(tasks[1].output, 'raw') else tasks[1].output)
            findings['grammar_analysis'] = grammar_text[:3000]
            scores['grammar'] = self._extract_rating(grammar_text, 'GRAMMAR RATING', 'MEDIUM')
            logger.info(f"Grammar Rating: {scores['grammar']}")
        
        # Task 2: Novelty Analysis
        if len(tasks) > 2 and hasattr(tasks[2], 'output'):
            novelty_text = str(tasks[2].output.raw if hasattr(tasks[2].output, 'raw') else tasks[2].output)
            findings['novelty_analysis'] = novelty_text[:3000]
            scores['novelty'] = self._extract_novelty(novelty_text, 'NOVELTY INDEX')
            logger.info(f"Novelty Index: {scores['novelty']}")
        
        # Task 3: Fact Check
        if len(tasks) > 3 and hasattr(tasks[3], 'output'):
            factcheck_text = str(tasks[3].output.raw if hasattr(tasks[3].output, 'raw') else tasks[3].output)
            findings['factcheck_log'] = factcheck_text[:3000]
            logger.info("Fact-check completed")
        
        # Task 4: Authenticity Analysis
        if len(tasks) > 4 and hasattr(tasks[4], 'output'):
            authenticity_text = str(tasks[4].output.raw if hasattr(tasks[4].output, 'raw') else tasks[4].output)
            findings['authenticity_analysis'] = authenticity_text[:5000]
            scores['authenticity'] = self._extract_score(authenticity_text, 'FABRICATION RISK', 50)
            logger.info(f"Authenticity/Fabrication Risk: {scores['authenticity']}%")
        
        # Calculate overall score using all four dimensions
        grammar_numeric = {'HIGH': 100, 'MEDIUM': 60, 'LOW': 20}.get(scores['grammar'], 60)
        novelty_numeric = {'Novel': 100, 'Incremental': 60, 'Derivative': 20}.get(scores['novelty'], 60)
        overall_score = int(
            scores['consistency'] * 0.30 +
            (100 - scores['authenticity']) * 0.30 +
            grammar_numeric * 0.20 +
            novelty_numeric * 0.20
        )

        # Determine recommendation
        recommendation = 'NEEDS_REVISION'
        if scores['consistency'] >= 75 and scores['authenticity'] <= 30 and overall_score >= 70:
            recommendation = 'ACCEPT'
        elif scores['consistency'] < 40 or scores['authenticity'] > 70 or overall_score < 40:
            recommendation = 'REJECT'
        
        # Compile final report
        report = {
            'metadata': {
                'arxiv_id': paper_data['arxiv_id'],
                'title': paper_data['title'],
                'authors': paper_data['authors'],
                'published': str(paper_data['published']),
                'categories': paper_data['categories'],
                'evaluation_date': datetime.now().isoformat(),
                'evaluation_time_seconds': (datetime.now() - start_time).total_seconds()
            },
            'scores': scores,
            'findings': findings,
            'recommendation': recommendation,
            'overall_score': overall_score
        }
        
        logger.info(f"Report compiled - Overall Score: {overall_score}, Recommendation: {recommendation}")
        return report
    
    def evaluate_from_pdf(self, pdf_bytes: bytes, filename: str = "uploaded_paper.pdf") -> Dict:
        """
        Evaluate a locally uploaded PDF file.

        Args:
            pdf_bytes: Raw PDF file contents
            filename: Original filename (used as the paper title fallback)

        Returns:
            Comprehensive evaluation report
        """
        logger.info(f"Starting PDF evaluation for: {filename}")
        start_time = datetime.now()

        # Write bytes to a temp file so PyMuPDF can open it
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".pdf")
        try:
            with os.fdopen(tmp_fd, "wb") as f:
                f.write(pdf_bytes)

            content = self.arxiv_client.extract_text_from_pdf(Path(tmp_path))
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

        # Build a minimal paper_data dict (no arXiv metadata)
        title = filename.replace(".pdf", "").replace("_", " ").replace("-", " ")
        abstract = content["sections"].get("Abstract", content["full_text"][:800])

        paper_data = {
            "arxiv_id": "local_upload",
            "title": title,
            "authors": ["Unknown"],
            "abstract": abstract,
            "published": datetime.now(),
            "categories": [],
            **content,
        }

        tasks = self._create_tasks(paper_data)

        crew = Crew(
            agents=list(self.agents.values()),
            tasks=tasks,
            process=Process.sequential,
            verbose=False,
        )
        result = crew.kickoff()

        report = self._compile_report(paper_data, tasks, result, start_time)
        logger.info(f"PDF evaluation complete in {(datetime.now() - start_time).total_seconds():.1f}s")
        return report

    def _split_task_outputs(self, text: str) -> List[str]:
        """
        Split the combined result text into individual task outputs.
        Uses task markers or natural boundaries.
        """
        outputs = []
        
        # Try to split by common markers
        markers = [
            'CONSISTENCY SCORE',
            'GRAMMAR RATING',
            'NOVELTY INDEX',
            'VERIFIED CLAIMS',
            'FABRICATION RISK'
        ]
        
        for i, marker in enumerate(markers):
            start_idx = text.find(marker)
            if start_idx == -1:
                outputs.append('')
                continue
            
            # Find next marker
            next_idx = len(text)
            if i + 1 < len(markers):
                next_marker_idx = text.find(markers[i + 1], start_idx)
                if next_marker_idx != -1:
                    next_idx = next_marker_idx
            
            output = text[start_idx:next_idx].strip()
            outputs.append(output)
        
        return outputs
    
    def _extract_score(self, text: str, marker: str, default: int = 50) -> int:
        """Extract a numeric score from text following a marker"""
        try:
            idx = text.find(marker)
            if idx == -1:
                return default
            
            # Get the line after marker
            line_end = text.find('\n', idx)
            if line_end == -1:
                line_end = idx + 100
            
            line = text[idx:line_end]
            
            # Extract numbers
            digits = ''.join(filter(str.isdigit, line))
            if digits:
                score = int(digits)
                return min(100, max(0, score))
        except Exception as e:
            logger.warning(f"Failed to extract score from {marker}: {e}")
        
        return default
    
    def _extract_rating(self, text: str, marker: str, default: str = 'MEDIUM') -> str:
        """Extract a rating (HIGH/MEDIUM/LOW) from text"""
        try:
            idx = text.find(marker)
            if idx == -1:
                return default
            
            section = text[idx:idx + 500]
            
            if 'HIGH' in section:
                return 'HIGH'
            elif 'LOW' in section:
                return 'LOW'
            else:
                return 'MEDIUM'
        except:
            pass
        
        return default
    
    def _extract_novelty(self, text: str, marker: str = 'NOVELTY INDEX') -> str:
        """Extract novelty classification"""
        try:
            idx = text.find(marker)
            if idx == -1:
                return 'Incremental'
            
            section = text[idx:idx + 500]
            
            if 'Derivative' in section:
                return 'Derivative'
            elif 'Novel' in section:
                return 'Novel'
            else:
                return 'Incremental'
        except:
            pass
        
        return 'Incremental'


if __name__ == "__main__":
    # Test the evaluator
    evaluator = ArxivEvaluator()
    report = evaluator.evaluate_paper("2303.08774")  # GPT-4 paper
    
    print("\n=== EVALUATION REPORT ===")
    print(f"Title: {report['metadata']['title']}")
    print(f"Overall Score: {report['overall_score']}/100")
    print(f"Recommendation: {report['recommendation']}")
