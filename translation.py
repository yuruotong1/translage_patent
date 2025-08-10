import asyncio
import time
from typing import List
from openai import AsyncOpenAI
import logging
from find_and_store import find_text_in_db, process_text, sync_process_text
import langdetect
import stanza
from find_and_store import get_supported_langs
import multiprocessing
from functools import partial
from concurrent.futures import ProcessPoolExecutor
import json, hashlib, os, logging
from find_and_store import NOUNS_CACHE_FILE
from postgre_sql import increment_terms_count
logger = logging.getLogger(__name__)

class TranslationService:
    """Service for translating text using OpenAI API"""

    LANGUAGE_MAP = {  # Add class-level dictionary for language mapping
        'chinese': 'zh-hans',
        'english': 'en',
        'french': 'fr',
        'spanish': 'es',
        'german': 'de',
        # Add more mappings as needed
    }

    def __init__(self, api_key: str, base_url: str = "https://openrouter.ai/api/v1"):
        self.api_key = api_key
        self.base_url = base_url
        self.client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key,
        )
        
        # Concurrency settings
        self.MAX_WORKERS = 100
        self.RATE_LIMIT_DELAY = 0.1
        self.MAX_PROCESSES = multiprocessing.cpu_count()
        
    async def translate_text_single(self, text: str, source_language: str, target_language: str, max_retries=3) -> tuple[str, dict]:
        """Single text translation function with client instance support and 15-second timeout retry.
        Returns a tuple of (translated_text, references_dict).
        """
        # Get language code for database using mapping
        src_lang_code = self.LANGUAGE_MAP[source_language.lower()]
        tgt_lang_code = self.LANGUAGE_MAP[target_language.lower()]
        # Check corpus for noun translations
        references, source_types = find_text_in_db(text, src_lang=src_lang_code, tgt_lang=tgt_lang_code)
        # Increment usage counts only during translation phase when terms are found
        if references:
            try:
                increment_terms_count(list(references.keys()), src_lang_code, tgt_lang_code)
            except Exception as e:
                logger.warning(f"Failed to increment term counts: {e}")
        
        if references:
            ref_text = "\n".join([f"{src} -> {tgt}" for src, tgt in references.items()])
            prompt = f"参考以下术语翻译：\n{ref_text}\n\n请将以下文本翻译为{target_language}，只输出译文，不要输出任何其他内容：\n\n{text}"
        else:
            prompt = f"请将以下文本翻译为{target_language}，只输出译文，不要输出任何其他内容：\n\n{text}"
        print("prompt: ",prompt)
        for attempt in range(max_retries):
            await asyncio.sleep(self.RATE_LIMIT_DELAY)
            response = await self.client.chat.completions.create(
                model="google/gemini-2.0-flash-001",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ],
                extra_headers={
                    "HTTP-Referer": "https://yy.xbrain.site",
                    "X-Title": "yiyuan",
                },
                extra_body={},
                temperature=0.3
            )
          
            translated_text = response.choices[0].message.content.strip()
            print("translated_text: ",translated_text)
            return translated_text, references
            
    
    async def translate_texts_parallel(self, texts: List[str], source_language: str, target_language: str) -> List[tuple[str, dict]]:
        """Parallel translation of multiple texts. Returns list of (translated_text, references_dict) in input order."""
        if not texts:
            return []
        

        start_time = time.time()
        translated_texts: List[tuple[str, dict]] = [("", {})] * len(texts)
        
        # Get language codes for database using mapping
        src_lang_code = self.LANGUAGE_MAP[source_language.lower()]
        tgt_lang_code = self.LANGUAGE_MAP[target_language.lower()]
        stanza.download(src_lang_code)
        # Preprocess texts in parallel using processes (reduced to 2 to avoid GPU conflicts)
        with ProcessPoolExecutor(max_workers=20) as executor:
            loop = asyncio.get_running_loop()
            process_tasks = [loop.run_in_executor(executor, partial(sync_process_text, src_lang=src_lang_code, tgt_lang=tgt_lang_code), text) for text in texts]
            results = await asyncio.gather(*process_tasks)
        
        # logger.info("Preprocessing completed. Starting translations...")
        
        # Update cache with results from all texts
        cache = {}
        if os.path.exists(NOUNS_CACHE_FILE):
            with open(NOUNS_CACHE_FILE, 'r', encoding='utf-8') as f:
                try:
                    cache = json.load(f)
                except json.JSONDecodeError:
                    logging.warning("Cache file is invalid or empty. Initializing empty cache.")
                    cache = {}
        
        for seen_list, text_hash in results:
            cache[f"{text_hash}_{src_lang_code}"] = seen_list
        
        with open(NOUNS_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=4)
        
        sem = asyncio.Semaphore(self.MAX_WORKERS)
        async def translate_task(index, text):
            async with sem:
                translated_text, references = await self.translate_text_single(text, source_language, target_language)
                logger.info(f"Completed translation {index + 1}/{len(texts)}")
                return index, translated_text, references
            
        tasks = [translate_task(i, text) for i, text in enumerate(texts)]
        results = await asyncio.gather(*tasks)
        
        for index, translated_text, references in results:
            translated_texts[index] = (translated_text, references)
        
        end_time = time.time()
        logger.info(f"Parallel translation completed in {end_time - start_time:.2f} seconds")
        return translated_texts 