import openai
from postgre_sql import check_duplicate, insert_translation, get_translation
import langdetect
import json
import asyncio
from openai import AsyncOpenAI
from prompt import translation_prompt, term_prompt, api_key, base_url, model
import concurrent.futures
import hashlib
import os
import logging
import threading

# Cache directory and file removed - no longer needed

# Schema for structured term extraction using Gemini 2.0
TERM_EXTRACTION_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "strict": True,
        "name": "term_extraction",
        "schema": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "source_text": {"type": "string"},
                    "target_text": {"type": "string"}
                },
                "required": ["source_text", "target_text"]
            }
        }
    }
}

async def extract_terms_with_gemini(text: str, tgt_lang: str, max_retries: int = 3) -> list[tuple[str, str]]:
    """Extract and translate terms using Gemini 2.0 structured output with retry mechanism"""
    client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    
    for attempt in range(max_retries):
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": term_prompt.format(tgt_lang=tgt_lang)},
                    {"role": "user", "content": text}
                ],
                response_format=TERM_EXTRACTION_SCHEMA
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
        except Exception as e:
            import traceback
            logging.error(f"Attempt {attempt + 1}/{max_retries} failed: {e}")
            logging.error(f"Full traceback: {traceback.format_exc()}")
            
            if attempt == max_retries - 1:
                # Last attempt failed, return empty list
                logging.error(f"All {max_retries} attempts failed for extract_terms_with_gemini")
                return []
            
            # Wait before retry (exponential backoff)
            await asyncio.sleep(2 ** attempt)
    



async def process_text(text: str, src_lang: str, tgt_lang: str) -> None:
    """
    Extract and translate terms using Gemini 2.0 one-step process.
    Check for duplicates before storing to avoid redundant entries.
    """
    # Extract and translate terms using Gemini 2.0 in one step
    terms = await extract_terms_with_gemini(text, tgt_lang)
    
    tasks = []
    for term in terms:
        source_text = term['source_text']
        target_text = term['target_text']
        # Check for similar/duplicate words before processing
        if not check_duplicate(source_text, src_lang, tgt_lang):
            print(f"Inserting term: {source_text} -> {target_text}")
            insert_translation(source_text, src_lang, target_text, tgt_lang)


def find_text_in_db(text: str, src_lang: str = 'english', tgt_lang: str = 'chinese') -> tuple[dict, dict]:
    """
    Find translations in the database for terms that appear in the text.
    Returns a tuple of (translations_dict, source_types_dict) where:
    - translations_dict: source words to their translations
    - source_types_dict: source words to their source_type ('usr', 'sys', etc.)
    """
    from postgre_sql import find_terms_in_text
    found_terms = find_terms_in_text(text, src_lang, tgt_lang)
    # Convert the result to dictionary formats
    translations = {}
    source_types = {}
    for source_text, target_text, source_type in found_terms:
        translations[source_text] = target_text
        source_types[source_text] = source_type
    return translations, source_types

if __name__ == "__main__":
    # translated_paragraphs = word_translator.process_document_dual_output(
    #                 "test.docx", "contrast.docx", "translation_only.docx", "英文"
    #             )
    # process_text("Barack Obama was born in Hawaii.")
    # query_text = "Barack Obama was born in Hawaii."  # Example input
    # found_translations = find_text_in_db(query_text, tgt_lang='chinese')
    # if found_translations:
    #     print("Found translations in DB:")
    #     for source, target in found_translations.items():
    #         print(f"{source} -> {target}")
    # else:
    #     print("No related words found in DB.")
    # 获取所有支持的语言列表
    # 获取支持的语言清单（从服务器）
    # 调用内部的官方模型列表函数
    pass 
   