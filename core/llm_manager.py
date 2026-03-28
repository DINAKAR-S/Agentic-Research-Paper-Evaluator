"""
LLM Manager - Handles multiple LLM providers with token management
Supports OpenRouter (free models) and Google Gemini with automatic fallback
"""

import os
from typing import Optional, Dict, Any, List
from loguru import logger
import tiktoken
from openai import OpenAI
from dotenv import load_dotenv

try:
    import google.generativeai as genai
    _GENAI_AVAILABLE = True
except ImportError:
    genai = None
    _GENAI_AVAILABLE = False

# Load environment variables
load_dotenv()


class LLMManager:
    """Manages LLM providers with automatic fallback and token management"""
    
    def __init__(self):
        self.max_tokens = int(os.getenv("MAX_TOKENS_PER_CALL", "16000"))
        self.primary_model = os.getenv("PRIMARY_MODEL", "google/gemini-2.0-flash-exp:free")
        self.backup_model = os.getenv("BACKUP_MODEL", "meta/llama-3.3-70b-instruct:free")
        
        # Initialize OpenAI client
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.openai_client = None
        if self.openai_key:
            self.openai_client = OpenAI(api_key=self.openai_key)
            logger.info("OpenAI client initialized")
        
        # Initialize OpenRouter client
        self.openrouter_key = os.getenv("OPENROUTER_API_KEY")
        self.openrouter_client = None
        if self.openrouter_key:
            self.openrouter_client = OpenAI(
                api_key=self.openrouter_key,
                base_url="https://openrouter.ai/api/v1"
            )
            logger.info("OpenRouter client initialized")
        
        # Initialize Gemini client
        self.google_key = os.getenv("GOOGLE_API_KEY")
        if self.google_key and _GENAI_AVAILABLE:
            genai.configure(api_key=self.google_key)
            logger.info("Google Gemini client initialized")
        elif self.google_key and not _GENAI_AVAILABLE:
            logger.warning("GOOGLE_API_KEY set but google-generativeai not installed; Gemini unavailable")
        
        # Token encoder
        self.encoder = tiktoken.get_encoding("cl100k_base")
        
    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        return len(self.encoder.encode(text))
    
    def chunk_text(self, text: str, max_tokens: int = None, overlap: int = 200) -> List[str]:
        """
        Split text into chunks that fit within token limit
        
        Args:
            text: Text to chunk
            max_tokens: Maximum tokens per chunk (default: self.max_tokens - 1000 for safety)
            overlap: Number of tokens to overlap between chunks
            
        Returns:
            List of text chunks
        """
        if max_tokens is None:
            max_tokens = self.max_tokens - 1000  # Leave room for prompt
        
        # Tokenize the entire text
        tokens = self.encoder.encode(text)
        
        if len(tokens) <= max_tokens:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(tokens):
            end = start + max_tokens
            chunk_tokens = tokens[start:end]
            chunk_text = self.encoder.decode(chunk_tokens)
            chunks.append(chunk_text)
            
            start = end - overlap  # Overlap for context
        
        logger.info(f"Split text into {len(chunks)} chunks (max {max_tokens} tokens each)")
        return chunks
    
    def call_llm(
        self,
        prompt: str,
        system_prompt: str = "",
        model: str = None,
        temperature: float = 0.7,
        max_output_tokens: int = 4000
    ) -> str:
        """
        Call LLM with automatic provider fallback
        
        Args:
            prompt: User prompt
            system_prompt: System instructions
            model: Model to use (defaults to PRIMARY_MODEL)
            temperature: Sampling temperature
            max_output_tokens: Maximum tokens in response
            
        Returns:
            LLM response text
        """
        if model is None:
            model = self.primary_model
        
        # Check token count
        total_input = f"{system_prompt}\n{prompt}"
        token_count = self.count_tokens(total_input)
        
        if token_count > self.max_tokens:
            logger.warning(f"Input tokens ({token_count}) exceed limit ({self.max_tokens})")
            raise ValueError(f"Input too long: {token_count} tokens (max {self.max_tokens})")
        
        logger.info(f"Calling LLM with {token_count} input tokens using {model}")
        
        try:
            # Try OpenAI first if it's a gpt model
            if self.openai_client and "gpt" in model.lower():
                return self._call_openai(
                    prompt, system_prompt, model, temperature, max_output_tokens
                )
            
            # Try OpenRouter next
            elif self.openrouter_client and ":" in model:  # OpenRouter model format
                return self._call_openrouter(
                    prompt, system_prompt, model, temperature, max_output_tokens
                )
            
            # Fallback to Gemini
            elif self.google_key and _GENAI_AVAILABLE and "gemini" in model.lower():
                return self._call_gemini(
                    prompt, system_prompt, temperature, max_output_tokens
                )
            
            else:
                raise ValueError("No valid LLM provider configured")
                
        except Exception as e:
            logger.error(f"Primary LLM call failed: {e}")
            
            # Try backup model
            if self.backup_model and self.backup_model != model:
                logger.info(f"Attempting fallback to {self.backup_model}")
                try:
                    return self.call_llm(
                        prompt, system_prompt, self.backup_model, temperature, max_output_tokens
                    )
                except Exception as backup_error:
                    logger.error(f"Backup LLM call failed: {backup_error}")
            
            raise Exception(f"All LLM providers failed: {e}")
    
    def _call_openai(
        self,
        prompt: str,
        system_prompt: str,
        model: str,
        temperature: float,
        max_tokens: int
    ) -> str:
        """Call OpenAI API"""
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        response = self.openai_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return response.choices[0].message.content
    
    def _call_openrouter(
        self,
        prompt: str,
        system_prompt: str,
        model: str,
        temperature: float,
        max_tokens: int
    ) -> str:
        """Call OpenRouter API"""
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        response = self.openrouter_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return response.choices[0].message.content
    
    def _call_gemini(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float,
        max_tokens: int
    ) -> str:
        """Call Google Gemini API"""
        model = genai.GenerativeModel(
            model_name='gemini-2.0-flash-exp',
            generation_config={
                'temperature': temperature,
                'max_output_tokens': max_tokens,
            }
        )
        
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        
        response = model.generate_content(full_prompt)
        return response.text
    
    def call_with_chunking(
        self,
        text: str,
        task_prompt: str,
        system_prompt: str = "",
        aggregation_strategy: str = "concatenate"
    ) -> str:
        """
        Process long text by chunking and aggregating results
        
        Args:
            text: Long text to process
            task_prompt: Task instruction template (use {chunk} placeholder)
            system_prompt: System instructions
            aggregation_strategy: How to combine results ("concatenate" or "summarize")
            
        Returns:
            Aggregated response
        """
        chunks = self.chunk_text(text)
        
        if len(chunks) == 1:
            # Text fits in one call
            final_prompt = task_prompt.replace("{chunk}", text)
            return self.call_llm(final_prompt, system_prompt)
        
        # Process each chunk
        results = []
        for i, chunk in enumerate(chunks):
            logger.info(f"Processing chunk {i+1}/{len(chunks)}")
            chunk_prompt = task_prompt.replace("{chunk}", chunk)
            result = self.call_llm(chunk_prompt, system_prompt)
            results.append(result)
        
        # Aggregate results
        if aggregation_strategy == "concatenate":
            return "\n\n---\n\n".join(results)
        
        elif aggregation_strategy == "summarize":
            combined = "\n\n".join([f"Section {i+1}:\n{r}" for i, r in enumerate(results)])
            summary_prompt = f"""Synthesize these partial analyses into a coherent final analysis:

{combined}

Provide a unified, comprehensive analysis that integrates all findings."""
            
            return self.call_llm(summary_prompt, system_prompt)
        
        else:
            raise ValueError(f"Unknown aggregation strategy: {aggregation_strategy}")


# Singleton instance
_llm_manager = None

def get_llm_manager() -> LLMManager:
    """Get or create LLM manager singleton"""
    global _llm_manager
    if _llm_manager is None:
        _llm_manager = LLMManager()
    return _llm_manager
