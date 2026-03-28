"""
arXiv Client - Download and parse arXiv papers
"""

import os
import re
from typing import Dict, Optional
from pathlib import Path
import arxiv
import fitz  # PyMuPDF
from loguru import logger


class ArxivClient:
    """Client for downloading and parsing arXiv papers"""
    
    def __init__(self, cache_dir: str = "./cache/papers"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.client = arxiv.Client()
    
    def extract_arxiv_id(self, url_or_id: str) -> str:
        """
        Extract arXiv ID from URL or ID string
        
        Examples:
            https://arxiv.org/abs/2301.12345 -> 2301.12345
            https://arxiv.org/pdf/2301.12345.pdf -> 2301.12345
            2301.12345v1 -> 2301.12345
            2301.12345 -> 2301.12345
        """
        # Remove version suffix if present
        url_or_id = re.sub(r'v\d+$', '', url_or_id)
        
        # Extract from URL
        match = re.search(r'(\d{4}\.\d{4,5})', url_or_id)
        if match:
            return match.group(1)
        
        # Assume it's already an ID
        return url_or_id
    
    def get_paper_metadata(self, arxiv_id: str) -> Dict:
        """
        Fetch paper metadata from arXiv
        
        Returns:
            Dict with keys: title, authors, abstract, published, categories, pdf_url
        """
        arxiv_id = self.extract_arxiv_id(arxiv_id)
        logger.info(f"Fetching metadata for arXiv:{arxiv_id}")
        
        search = arxiv.Search(id_list=[arxiv_id])
        result = next(self.client.results(search))
        
        metadata = {
            'arxiv_id': arxiv_id,
            'title': result.title,
            'authors': [author.name for author in result.authors],
            'abstract': result.summary,
            'published': result.published,
            'updated': result.updated,
            'categories': result.categories,
            'pdf_url': result.pdf_url,
            'entry_id': result.entry_id,
            'primary_category': result.primary_category,
            'doi': result.doi if hasattr(result, 'doi') else None,
            'comment': result.comment if hasattr(result, 'comment') else None,
        }
        
        logger.info(f"Retrieved paper: {metadata['title'][:100]}...")
        return metadata
    
    def download_pdf(self, arxiv_id: str, force_download: bool = False) -> Path:
        """
        Download paper PDF
        
        Args:
            arxiv_id: arXiv paper ID
            force_download: Re-download even if cached
            
        Returns:
            Path to downloaded PDF
        """
        arxiv_id = self.extract_arxiv_id(arxiv_id)
        pdf_path = self.cache_dir / f"{arxiv_id}.pdf"
        
        if pdf_path.exists() and not force_download:
            logger.info(f"Using cached PDF: {pdf_path}")
            return pdf_path
        
        logger.info(f"Downloading PDF for arXiv:{arxiv_id}")
        
        search = arxiv.Search(id_list=[arxiv_id])
        result = next(self.client.results(search))
        
        result.download_pdf(dirpath=str(self.cache_dir), filename=f"{arxiv_id}.pdf")
        
        logger.info(f"PDF downloaded: {pdf_path}")
        return pdf_path
    
    def extract_text_from_pdf(self, pdf_path: Path) -> Dict[str, any]:
        """
        Extract text and structure from PDF
        
        Returns:
            Dict with keys:
                - full_text: Complete paper text
                - sections: Dict mapping section names to text
                - metadata: PDF metadata
                - num_pages: Page count
        """
        logger.info(f"Parsing PDF: {pdf_path}")
        
        doc = fitz.open(pdf_path)
        full_text = ""
        sections = {}
        current_section = "Abstract"
        current_text = []
        
        # Common section headers
        section_patterns = [
            r'^(?:1\.?\s+)?Introduction\s*$',
            r'^(?:\d+\.?\s+)?Related Work\s*$',
            r'^(?:\d+\.?\s+)?Background\s*$',
            r'^(?:\d+\.?\s+)?Methodology\s*$',
            r'^(?:\d+\.?\s+)?Method\s*$',
            r'^(?:\d+\.?\s+)?Approach\s*$',
            r'^(?:\d+\.?\s+)?Experiments?\s*$',
            r'^(?:\d+\.?\s+)?Results?\s*$',
            r'^(?:\d+\.?\s+)?Discussion\s*$',
            r'^(?:\d+\.?\s+)?Evaluation\s*$',
            r'^(?:\d+\.?\s+)?Conclusion\s*$',
            r'^(?:\d+\.?\s+)?References?\s*$',
            r'^Abstract\s*$',
        ]
        
        for page_num, page in enumerate(doc):
            text = page.get_text()
            full_text += text + "\n"
            
            # Try to detect section headers
            lines = text.split('\n')
            for line in lines:
                line_stripped = line.strip()
                
                # Check if line matches a section header
                is_section_header = False
                for pattern in section_patterns:
                    if re.match(pattern, line_stripped, re.IGNORECASE):
                        # Save previous section
                        if current_text:
                            sections[current_section] = '\n'.join(current_text)
                        
                        # Start new section
                        current_section = line_stripped
                        current_text = []
                        is_section_header = True
                        break
                
                if not is_section_header and line_stripped:
                    current_text.append(line_stripped)
        
        # Save last section
        if current_text:
            sections[current_section] = '\n'.join(current_text)
        
        # If no sections detected, use the full text
        if not sections or len(sections) == 1:
            sections = {
                "Full Paper": full_text
            }
        
        logger.info(f"Extracted {len(full_text)} characters from {doc.page_count} pages")
        logger.info(f"Detected sections: {list(sections.keys())}")
        
        return {
            'full_text': full_text,
            'sections': sections,
            'metadata': doc.metadata,
            'num_pages': doc.page_count
        }
    
    def get_paper(self, arxiv_id: str) -> Dict:
        """
        Complete workflow: fetch metadata, download PDF, extract text
        
        Returns:
            Dict containing metadata and parsed content
        """
        arxiv_id = self.extract_arxiv_id(arxiv_id)
        
        # Get metadata
        metadata = self.get_paper_metadata(arxiv_id)
        
        # Download and parse PDF
        pdf_path = self.download_pdf(arxiv_id)
        content = self.extract_text_from_pdf(pdf_path)
        
        return {
            **metadata,
            **content,
            'pdf_path': str(pdf_path)
        }


# Example usage
if __name__ == "__main__":
    client = ArxivClient()
    
    # Test with GPT-4 paper
    paper = client.get_paper("2303.08774")
    
    print(f"Title: {paper['title']}")
    print(f"Authors: {', '.join(paper['authors'][:3])}...")
    print(f"Published: {paper['published']}")
    print(f"Pages: {paper['num_pages']}")
    print(f"\nSections found: {list(paper['sections'].keys())}")
    print(f"\nText length: {len(paper['full_text'])} characters")
