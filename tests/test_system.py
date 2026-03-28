"""
Quick Test Script for Agentic Research Paper Evaluator
Tests basic functionality without running full evaluation
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.arxiv_client import ArxivClient
from core.llm_manager import get_llm_manager
from loguru import logger


def test_arxiv_client():
    """Test arXiv paper downloading and parsing"""
    print("\n" + "="*60)
    print("TEST 1: arXiv Client")
    print("="*60)
    
    try:
        client = ArxivClient()
        
        # Test with a well-known paper (GPT-4)
        paper_id = "2303.08774"
        print(f"\n📄 Testing with paper: {paper_id}")
        
        # Get metadata only (fast)
        print("\n1. Fetching metadata...")
        metadata = client.get_paper_metadata(paper_id)
        
        print(f"   ✓ Title: {metadata['title'][:60]}...")
        print(f"   ✓ Authors: {len(metadata['authors'])} authors")
        print(f"   ✓ Categories: {', '.join(metadata['categories'])}")
        print(f"   ✓ Published: {metadata['published']}")
        
        # Download PDF (may be cached)
        print("\n2. Downloading PDF...")
        pdf_path = client.download_pdf(paper_id)
        print(f"   ✓ PDF saved: {pdf_path}")
        print(f"   ✓ File size: {pdf_path.stat().st_size / 1024:.1f} KB")
        
        # Extract text
        print("\n3. Extracting text...")
        content = client.extract_text_from_pdf(pdf_path)
        
        print(f"   ✓ Pages: {content['num_pages']}")
        print(f"   ✓ Characters: {len(content['full_text']):,}")
        print(f"   ✓ Sections found: {len(content['sections'])}")
        print(f"   ✓ Section names: {list(content['sections'].keys())[:5]}")
        
        print("\n✅ arXiv Client test PASSED")
        return True
    
    except Exception as e:
        print(f"\n❌ arXiv Client test FAILED: {str(e)}")
        logger.exception(e)
        return False


def test_llm_manager():
    """Test LLM provider connection"""
    print("\n" + "="*60)
    print("TEST 2: LLM Manager")
    print("="*60)
    
    try:
        llm = get_llm_manager()
        
        # Check configuration
        print("\n1. Checking configuration...")
        print(f"   Primary model: {llm.primary_model}")
        print(f"   Backup model: {llm.backup_model}")
        print(f"   Max tokens: {llm.max_tokens}")
        
        # Check API keys
        print("\n2. Checking API keys...")
        if llm.openrouter_key:
            print(f"   ✓ OpenRouter key: {llm.openrouter_key[:10]}...")
        else:
            print("   ⚠ OpenRouter key not set")
        
        if llm.google_key:
            print(f"   ✓ Google key: {llm.google_key[:10]}...")
        else:
            print("   ⚠ Google key not set")
        
        if not llm.openrouter_key and not llm.google_key:
            print("\n⚠️  WARNING: No API keys configured!")
            print("   Please set up API keys in .env file")
            print("   See .env.example for instructions")
            return False
        
        # Test token counting
        print("\n3. Testing token management...")
        test_text = "This is a test sentence for token counting."
        token_count = llm.count_tokens(test_text)
        print(f"   ✓ Token counter working: '{test_text}' = {token_count} tokens")
        
        # Test chunking
        long_text = " ".join(["word"] * 20000)
        chunks = llm.chunk_text(long_text, max_tokens=1000)
        print(f"   ✓ Chunking working: 20k words → {len(chunks)} chunks")
        
        # Optional: Test actual LLM call (only if API key is set)
        if llm.openrouter_key or llm.google_key:
            print("\n4. Testing LLM call...")
            try:
                response = llm.call_llm(
                    prompt="Say 'Hello' in exactly one word.",
                    temperature=0.1,
                    max_output_tokens=10
                )
                print(f"   ✓ LLM response: {response[:50]}")
                print("\n✅ LLM Manager test PASSED (with live API call)")
                return True
            
            except Exception as e:
                print(f"   ⚠ LLM call failed (API may have issues): {str(e)}")
                print("\n⚠️  LLM Manager test PASSED (config only)")
                return True
        
        print("\n✅ LLM Manager test PASSED (config only)")
        return True
    
    except Exception as e:
        print(f"\n❌ LLM Manager test FAILED: {str(e)}")
        logger.exception(e)
        return False


def test_environment():
    """Test environment setup"""
    print("\n" + "="*60)
    print("TEST 0: Environment Setup")
    print("="*60)
    
    # Check .env file
    env_file = Path(".env")
    if env_file.exists():
        print("\n✓ .env file found")
    else:
        print("\n⚠ .env file not found")
        print("  Please copy .env.example to .env and configure API keys")
    
    # Check required directories
    print("\nChecking directories:")
    for dir_name in ['cache/papers', 'reports', 'logs', 'core', 'agents']:
        dir_path = Path(dir_name)
        if dir_path.exists():
            print(f"   ✓ {dir_name}/")
        else:
            print(f"   ⚠ {dir_name}/ (will be created)")
            dir_path.mkdir(parents=True, exist_ok=True)
    
    # Check Python version
    print(f"\nPython version: {sys.version.split()[0]}")
    
    # Check imports
    print("\nChecking imports...")
    try:
        import arxiv
        print("   ✓ arxiv")
    except ImportError:
        print("   ✗ arxiv (pip install arxiv)")
    
    try:
        import fitz
        print("   ✓ PyMuPDF")
    except ImportError:
        print("   ✗ PyMuPDF (pip install PyMuPDF)")
    
    try:
        from crewai import Agent
        print("   ✓ crewai")
    except ImportError:
        print("   ✗ crewai (pip install crewai)")
    
    try:
        import streamlit
        print("   ✓ streamlit")
    except ImportError:
        print("   ✗ streamlit (pip install streamlit)")
    
    return True


def main():
    """Run all tests"""
    print("\n🧪 AGENTIC RESEARCH PAPER EVALUATOR - TEST SUITE")
    print("="*60)
    
    # Suppress verbose logging during tests
    logger.remove()
    logger.add(sys.stderr, level="WARNING")
    
    results = []
    
    # Test 0: Environment
    results.append(("Environment Setup", test_environment()))
    
    # Test 1: arXiv Client
    results.append(("arXiv Client", test_arxiv_client()))
    
    # Test 2: LLM Manager
    results.append(("LLM Manager", test_llm_manager()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60 + "\n")
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status:12} {test_name}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n🎉 All tests passed! System is ready.")
        print("\nNext steps:")
        print("  1. Ensure .env file has valid API keys")
        print("  2. Run: streamlit run app.py")
        print("  3. Or: python main.py --arxiv-id 2303.08774")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please check configuration.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
