#!/usr/bin/env python3
"""
Command-Line Interface for Agentic Research Paper Evaluator
"""

import argparse
import sys
import json
from pathlib import Path
from datetime import datetime
from loguru import logger

from evaluator import ArxivEvaluator
from core.arxiv_client import ArxivClient


def setup_logging(verbose: bool = False):
    """Configure logging"""
    logger.remove()
    level = "DEBUG" if verbose else "INFO"
    
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level=level
    )
    
    # Also log to file
    log_dir = Path("./logs")
    log_dir.mkdir(exist_ok=True)
    
    logger.add(
        log_dir / f"evaluation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
        rotation="10 MB",
        level="DEBUG"
    )


def print_report(report: dict, detailed: bool = True):
    """Pretty-print evaluation report to console"""
    
    metadata = report['metadata']
    scores = report['scores']
    
    print("\n" + "="*80)
    print("AGENTIC RESEARCH PAPER EVALUATION REPORT")
    print("="*80)
    
    print(f"\n[PAPER INFORMATION]")
    print(f"   Title:      {metadata['title']}")
    print(f"   Authors:    {', '.join(metadata['authors'][:3])}" + 
          (f" et al." if len(metadata['authors']) > 3 else ""))
    print(f"   arXiv ID:   {metadata['arxiv_id']}")
    print(f"   Published:  {metadata['published']}")
    print(f"   Categories: {', '.join(metadata['categories'])}")
    
    print(f"\n[EVALUATION METADATA]")
    print(f"   Date:       {metadata['evaluation_date']}")
    print(f"   Duration:   {metadata['evaluation_time_seconds']:.1f} seconds")
    
    print(f"\n[EVALUATION SCORES]")
    print(f"   Overall Score:      {report['overall_score']}/100")
    print(f"   Consistency:        {scores['consistency']}/100")
    print(f"   Grammar:            {scores['grammar']}")
    print(f"   Novelty:            {scores['novelty']}")
    print(f"   Fabrication Risk:   {scores['authenticity']}%")
    
    print(f"\n[RECOMMENDATION]")
    rec = report['recommendation']
    if rec == 'ACCEPT':
        print(f"   [ACCEPT] - Paper meets quality standards")
    elif rec == 'REJECT':
        print(f"   [REJECT] - Significant issues detected")
    else:
        print(f"   [NEEDS_REVISION] - Further examination needed")
    
    if detailed:
        findings = report['findings']
        
        print(f"\n[DETAILED FINDINGS]")
        
        if findings.get('consistency_analysis'):
            print(f"\n   CONSISTENCY ANALYSIS:")
            print(f"   {'-'*76}")
            for line in str(findings['consistency_analysis']).split('\n')[:10]:
                safe_line = line.encode('utf-8', 'ignore').decode('utf-8')[:76]
                print(f"   {safe_line}")
        
        if findings.get('grammar_analysis'):
            print(f"\n   GRAMMAR ANALYSIS:")
            print(f"   {'-'*76}")
            for line in str(findings['grammar_analysis']).split('\n')[:10]:
                safe_line = line.encode('utf-8', 'ignore').decode('utf-8')[:76]
                print(f"   {safe_line}")
        
        if findings.get('authenticity_analysis'):
            print(f"\n   AUTHENTICITY ANALYSIS:")
            print(f"   {'-'*76}")
            for line in str(findings['authenticity_analysis']).split('\n')[:10]:
                safe_line = line.encode('utf-8', 'ignore').decode('utf-8')[:76]
                print(f"   {safe_line}")
    
    print("\n" + "="*80 + "\n")


def save_report(report: dict, output_path: Path, format: str):
    """Save report to file"""
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    if format == 'json':
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)
        logger.info(f"Report saved to {output_path}")
    
    elif format == 'markdown':
        with open(output_path, 'w') as f:
            f.write(f"# Evaluation Report: {report['metadata']['title']}\n\n")
            f.write(f"**arXiv ID**: {report['metadata']['arxiv_id']}\n\n")
            f.write(f"**Evaluated**: {report['metadata']['evaluation_date']}\n\n")
            f.write(f"## Scores\n\n")
            f.write(f"- Overall: {report['overall_score']}/100\n")
            f.write(f"- Consistency: {report['scores']['consistency']}/100\n")
            f.write(f"- Grammar: {report['scores']['grammar']}\n")
            f.write(f"- Novelty: {report['scores']['novelty']}\n")
            f.write(f"- Fabrication Risk: {report['scores']['authenticity']}%\n\n")
            f.write(f"## Recommendation\n\n{report['recommendation']}\n\n")
            f.write(f"## Detailed Findings\n\n")
            f.write(report['findings'].get('consistency_analysis', ''))
        logger.info(f"Report saved to {output_path}")
    
    elif format == 'pdf':
        logger.warning("PDF generation not yet implemented")
    
    else:
        logger.error(f"Unknown format: {format}")


def main():
    """Main CLI entry point"""
    
    parser = argparse.ArgumentParser(
        description="Agentic Research Paper Evaluator - AI-powered peer review for arXiv papers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Evaluate by arXiv ID
  %(prog)s --arxiv-id 2303.08774
  
  # Evaluate by URL
  %(prog)s --url https://arxiv.org/abs/2303.08774
  
  # Save report as JSON
  %(prog)s --arxiv-id 2303.08774 --output report.json --format json
  
  # Detailed output with verbose logging
  %(prog)s --arxiv-id 2303.08774 --detailed --verbose
        """
    )
    
    # Input arguments
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        '--arxiv-id',
        type=str,
        help='arXiv paper ID (e.g., 2303.08774)'
    )
    input_group.add_argument(
        '--url',
        type=str,
        help='arXiv paper URL (e.g., https://arxiv.org/abs/2303.08774)'
    )
    
    # Output arguments
    parser.add_argument(
        '--output',
        type=str,
        help='Output file path (default: ./reports/evaluation_ARXIV_ID.EXT)'
    )
    parser.add_argument(
        '--format',
        choices=['json', 'markdown', 'pdf'],
        default='json',
        help='Output format (default: json)'
    )
    
    # Behavior arguments
    parser.add_argument(
        '--detailed',
        action='store_true',
        help='Show detailed analysis in console output'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    parser.add_argument(
        '--no-cache',
        action='store_true',
        help='Force re-download of paper (ignore cache)'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    
    # Get paper identifier
    paper_id = args.arxiv_id or args.url
    
    logger.info(f"Starting evaluation for: {paper_id}")
    
    try:
        # Initialize evaluator
        evaluator = ArxivEvaluator()
        
        # Run evaluation
        logger.info("Running multi-agent evaluation...")
        report = evaluator.evaluate_paper(paper_id)
        
        # Print to console
        print_report(report, detailed=args.detailed)
        
        # Save to file if requested
        if args.output or args.format:
            arxiv_id = report['metadata']['arxiv_id']
            
            if args.output:
                output_path = Path(args.output)
            else:
                ext = args.format
                output_path = Path(f"./reports/evaluation_{arxiv_id}.{ext}")
            
            save_report(report, output_path, args.format)
        
        logger.success("✅ Evaluation complete!")
        return 0
    
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Evaluation interrupted by user")
        return 130
    
    except Exception as e:
        logger.error(f"❌ Evaluation failed: {str(e)}")
        if args.verbose:
            logger.exception(e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
