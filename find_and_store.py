import stanza
import openai
from postgre_sql import check_duplicate, insert_translation, get_translation
import langdetect
import json
import asyncio
from openai import AsyncOpenAI
from stanza.resources.common import load_resources_json
from prompt import translation_prompt, api_key, base_url
import concurrent.futures
import hashlib
import os
import logging
import threading

CACHE_DIR = 'cache'
NOUNS_CACHE_FILE = os.path.join(CACHE_DIR, 'nouns_cache.json')

if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

# Global pipeline cache with thread safety
_pipeline_cache = {}
_pipeline_lock = threading.Lock()

def get_pipeline(lang_code: str):
    """Get or create a Stanza pipeline for the given language code"""
    with _pipeline_lock:
        if lang_code not in _pipeline_cache:
            logging.info(f"Creating new Stanza pipeline for language: {lang_code}")
            _pipeline_cache[lang_code] = stanza.Pipeline(
                lang_code,
                processors='tokenize,pos',
                use_gpu=True,
                pos_batch_size=1000,  # Reduced batch size
                download_method=None
            )
        return _pipeline_cache[lang_code]


def get_supported_langs():
    resources = load_resources_json()
    return sorted(resources.keys())

async def translate_and_store(text: str, src_lang: str, tgt_lang: str) -> None:
    """
    Translate a single word/phrase from src_lang to tgt_lang using OpenAI
    and store the result in the glossary if it does not already exist.
    """
    client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    response = await client.chat.completions.create(
        model="google/gemini-2.0-flash-001",
        messages=[{"role": "user", "content": translation_prompt.format(text=text, src_lang=src_lang, tgt_lang=tgt_lang)}],
        response_format={"type": "json_schema",
                        "json_schema": {
                            "strict": True,
                            "name": "translation",
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "target_text": {"type": "string"}
                                },
                                "required": ["target_text"]
                            }
                        }
                        }
    )
    translation = json.loads(response.choices[0].message.content)['target_text']
    insert_translation(text, src_lang, translation, tgt_lang)
    print(f"Translated and inserted: {text} -> {translation}")

async def process_text(text: str, src_lang: str, tgt_lang: str) -> None:
    """
    Tokenize the input text with Stanza and translate each token asynchronously.
    """
    nlp = get_pipeline(src_lang)
    doc = nlp(text)

    tasks = []
    seen = set()
    for sentence in doc.sentences:
        for word in sentence.words:
            if word.upos == 'NOUN' and word.text not in seen and not check_duplicate(word.text, src_lang):
                seen.add(word.text)
                tasks.append(translate_and_store(word.text, src_lang=src_lang, tgt_lang=tgt_lang))
    # 控制并发量为100
    semaphore = asyncio.Semaphore(100)
    async def sem_task(task):
        async with semaphore:
            return await task
    await asyncio.gather(*(sem_task(t) for t in tasks))

    text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
    seen_list = list(seen)
    
    cache = {}
    if os.path.exists(NOUNS_CACHE_FILE):
        with open(NOUNS_CACHE_FILE, 'r', encoding='utf-8') as f:
            cache = json.load(f)
    
    cache[f"{text_hash}_{src_lang}"] = seen_list
    
    with open(NOUNS_CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=4)

def sync_translate_and_store(text: str, src_lang: str, tgt_lang: str) -> None:
    """Synchronous version to translate a single word/phrase and store in glossary."""
    client = openai.OpenAI(api_key=api_key, base_url=base_url)
    response = client.chat.completions.create(
        model="google/gemini-2.0-flash-001",
        messages=[{"role": "user", "content": translation_prompt.format(text=text, src_lang=src_lang, tgt_lang=tgt_lang)}],
        response_format={"type": "json_schema",
                        "json_schema": {
                            "strict": True,
                            "name": "translation",
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "target_text": {"type": "string"}
                                },
                                "required": ["target_text"]
                            }
                        }
                        }
    )
    translation = json.loads(response.choices[0].message.content)['target_text']
    insert_translation(text, src_lang, translation, tgt_lang)
    print(f"Translated and inserted: {text} -> {translation}")

def sync_process_text(text: str, src_lang: str, tgt_lang: str) -> tuple[list, str]:
    """Synchronous version to tokenize text and translate nouns using threads for concurrency."""
    nlp = get_pipeline(src_lang)
    doc = nlp(text)

    tasks = []
    seen = set()
    for sentence in doc.sentences:
        for word in sentence.words:
            if word.upos == 'NOUN' and word.text not in seen and not check_duplicate(word.text, src_lang):
                seen.add(word.text)
                tasks.append(word.text)

    if tasks:
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(sync_translate_and_store, word, src_lang, tgt_lang) for word in tasks]
            concurrent.futures.wait(futures)

    text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
    seen_list = list(seen)
    
    return seen_list, text_hash

def find_text_in_db(text: str, src_lang: str = 'en', tgt_lang: str = 'zh') -> tuple[dict, dict]:
    """
    Find translations in the database for terms that appear in the text.
    Returns a tuple of (translations_dict, source_types_dict) where:
    - translations_dict: source words to their translations
    - source_types_dict: source words to their source_type ('usr', 'sys', etc.)
    """
    from postgre_sql import find_terms_in_text
    
    # Use find_terms_in_text to directly search for terms in the text
    found_terms = find_terms_in_text(text, src_lang)
    
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
    # found_translations = find_text_in_db(query_text, tgt_lang='zh')
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
   