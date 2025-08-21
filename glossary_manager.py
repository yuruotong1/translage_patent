import pandas as pd
import json
import asyncio
from typing import List, Dict, Tuple, Optional
from openai import AsyncOpenAI
from prompt import term_prompt, api_key, base_url, model
import logging
import os

logger = logging.getLogger(__name__)

class GlossaryManager:
    """Glossary management without database dependency"""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.glossary_dict = {}  # {source_text: target_text}
        
    async def extract_terms_with_gemini(self, text: str, tgt_lang: str, max_retries: int = 3) -> List[Dict[str, str]]:
        """Extract and translate terms using Gemini 2.0 structured output with retry mechanism"""
        
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
        
        for attempt in range(max_retries):
            try:
                response = await self.client.chat.completions.create(
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
        
        return []

    async def generate_glossary_from_text(self, text: str, src_lang: str, tgt_lang: str) -> List[Dict[str, str]]:
        """Generate glossary from text using AI extraction"""
        terms = await self.extract_terms_with_gemini(text, tgt_lang)
        return terms

    def save_glossary_to_excel(self, terms: List[Dict[str, str]], output_path: str) -> str:
        """Save glossary terms to Excel file"""
        try:
            # Create DataFrame with required columns
            df = pd.DataFrame(terms)
            
            # Ensure we have the required columns
            if not df.empty:
                df = df[['source_text', 'target_text']]
                df.columns = ['Source Content', 'Target Content']
            else:
                # Create empty DataFrame with required columns
                df = pd.DataFrame(columns=['Source Content', 'Target Content'])
            
            # Save to Excel
            df.to_excel(output_path, index=False, engine='openpyxl')
            logger.info(f"Glossary saved to {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Error saving glossary to Excel: {e}")
            raise

    def load_glossary_from_excel(self, excel_path: str) -> Dict[str, str]:
        """Load glossary from Excel file and return as dictionary"""
        try:
            df = pd.read_excel(excel_path, engine='openpyxl')
            
            # Check if required columns exist
            required_columns = ['Source Content', 'Target Content']
            if not all(col in df.columns for col in required_columns):
                raise ValueError(f"Excel file must contain columns: {required_columns}")
            
            # Convert to dictionary
            glossary_dict = {}
            for _, row in df.iterrows():
                source = str(row['Source Content']).strip()
                target = str(row['Target Content']).strip()
                if source and target and source != 'nan' and target != 'nan':
                    glossary_dict[source] = target
            
            self.glossary_dict = glossary_dict
            logger.info(f"Loaded {len(glossary_dict)} terms from Excel")
            return glossary_dict
        except Exception as e:
            logger.error(f"Error loading glossary from Excel: {e}")
            raise

    def find_terms_in_text(self, text: str) -> Tuple[Dict[str, str], Dict[str, str]]:
        """Find terms from loaded glossary in the given text"""
        found_translations = {}
        source_types = {}
        
        for source_text, target_text in self.glossary_dict.items():
            if source_text.lower() in text.lower():
                found_translations[source_text] = target_text
                source_types[source_text] = 'usr'  # All loaded terms are user terms
        
        return found_translations, source_types

    def clear_glossary(self):
        """Clear the current glossary"""
        self.glossary_dict.clear()

    def get_glossary_size(self) -> int:
        """Get the number of terms in current glossary"""
        return len(self.glossary_dict)
