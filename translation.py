import asyncio
import time
from typing import List
from openai import AsyncOpenAI
import logging
from extraction_term import find_text_in_db, process_text
import langdetect
import multiprocessing
from functools import partial
from concurrent.futures import ProcessPoolExecutor
import json, hashlib, os, logging
from postgre_sql import increment_terms_count
from prompt import translation_prompt, model
logger = logging.getLogger(__name__)

class TranslationService:
    """Service for translating text using OpenAI API"""


    def __init__(self, api_key: str, base_url: str = "https://openrouter.ai/api/v1"):
        self.api_key = api_key
        self.base_url = base_url
        self.client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key,
        )
        self.MAX_WORKERS = 100
        
    async def translate_text_single(self, text: str, source_language: str, target_language: str, max_retries=3) -> tuple[str, dict]:
        """Single text translation function with client instance support and 15-second timeout retry.
        Returns a tuple of (translated_text, references_dict).
        """
        references, source_types = find_text_in_db(text, src_lang=source_language, tgt_lang=target_language)
        # Increment usage counts only during translation phase when terms are found
        if references:
            try:
                increment_terms_count(list(references.keys()), source_language, target_language)
            except Exception as e:
                logger.warning(f"Failed to increment term counts: {e}")
        
        if references:
            ref_text = "\n".join([f"{src} -> {tgt}" for src, tgt in references.items()])
            prompt = translation_prompt.format(
                ref_text=ref_text,
                target_language=target_language
            )
        else:
            prompt = translation_prompt.format(
                ref_text="[]",
                target_language=target_language
            )
        logger.info(f"prompt: {prompt}")
        
        for attempt in range(max_retries):
            try:
                response = await self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {
                            "role": "system",
                            "content": prompt
                        },
                        {
                            "role": "user",
                            "content": text
                        }
                    ],
                    temperature=0.3
                )
              
                translated_text = response.choices[0].message.content.strip()
                print("translated_text: ",translated_text)
                return translated_text, references
            except Exception as e:
                import traceback
                logger.error(f"Translation attempt {attempt + 1}/{max_retries} failed: {e}")
                logger.error(f"Full traceback: {traceback.format_exc()}")
                
                if attempt == max_retries - 1:
                    # Last attempt failed, return original text
                    logger.error(f"All {max_retries} attempts failed for translation, returning original text")
                    return text, references
                
                # Wait before retry (exponential backoff)
                await asyncio.sleep(2 ** attempt)
            
    
    async def translate_texts_parallel(self, texts: List[str], source_language: str, target_language: str) -> List[tuple[str, dict]]:
        """Parallel translation of multiple texts. Returns list of (translated_text, references_dict) in input order."""
        if not texts:
            return []
        translated_texts: List[tuple[str, dict]] = [("", {})] * len(texts)
        # Preprocess texts in parallel using processes to extract and store words
        sem = asyncio.Semaphore(self.MAX_WORKERS)
        # 建立术语库
        async def sem_task(index,task):
            async with sem:
                logger.info(f"Extracting terms {index + 1}/{len(texts)}")
                await process_text(task, source_language, target_language)
        tasks = [sem_task(i, text) for i, text in enumerate(texts)]
        await asyncio.gather(*tasks)
       
        # 开始翻译
        async def translate_task(index, text):
            async with sem:
                translated_text, references = await self.translate_text_single(text, source_language, target_language)
                logger.info(f"Completed translation {index + 1}/{len(texts)}")
                return index, translated_text, references
            
        tasks = [translate_task(i, text) for i, text in enumerate(texts)]
        results = await asyncio.gather(*tasks)
        
        for index, translated_text, references in results:
            translated_texts[index] = (translated_text, references)
        
        return translated_texts 