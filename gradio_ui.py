import gradio as gr
import asyncio
import os
import tempfile
import shutil
import torch
from word_translation_service import WordTranslationService
from prompt import api_key, base_url
import logging

class GradioTranslationApp:
    def __init__(self):
        self.translator = WordTranslationService(api_key, base_url)
        
    async def translate_document(self, file_path, source_lang, target_lang, translation_type):
        """Translate document and return output file paths"""
        # Create temporary directory for outputs
        temp_dir = tempfile.mkdtemp()
        
        # Get original filename without extension
        original_name = os.path.splitext(os.path.basename(file_path))[0]
        
        # Define output paths
        contrast_output = os.path.join(temp_dir, f"{original_name}_contrast.docx")
        translation_only_output = os.path.join(temp_dir, f"{original_name}_translation.docx")
        
        # Check file extension and process accordingly
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext == '.docx':
            # Process DOCX file
            results = await self.translator.process_document_dual_output(
                file_path, 
                contrast_output, 
                translation_only_output,
                source_lang, 
                target_lang
            )
        elif file_ext == '.doc':
            # Process DOC file
            results = await self.translator.extract_and_translate_doc(
                file_path,
                contrast_output,
                translation_only_output,
                source_lang,
                target_lang
            )
        else:
            raise ValueError("Unsupported file format. Please upload a .doc or .docx file.")
        
        # Return appropriate file based on translation type
        if translation_type == "Contrast (Original + Translation)":
            return contrast_output, f"Translation completed! {len(results)} paragraphs processed."
        else:
            return translation_only_output, f"Translation completed! {len(results)} paragraphs processed."
            
    
    def sync_translate_document(self, file, source_lang, target_lang, translation_type):
        """Synchronous wrapper for the async translation function"""
        if file is None:
            return None, "Please upload a document first."
        
        try:
            # Run the async function
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            output_file, message = loop.run_until_complete(
                self.translate_document(file.name, source_lang, target_lang, translation_type)
            )
            loop.close()
            
            if output_file and os.path.exists(output_file):
                return output_file, message
            else:
                return None, message
                
        except Exception as e:
            import traceback
            logging.error(f"Error: {traceback.format_exc()}")
            return None, f"Error: {str(e)}"

def create_interface():
    """Create and configure the Gradio interface"""
    app = GradioTranslationApp()
    
    # Define language options
    language_options = [
        "english",
        "chinese",
        "thai"
    ]
    
    # Define translation type options
    translation_types = [
        "Translation Only",
        "Contrast (Original + Translation)"
    ]
    
    with gr.Blocks(title="Document Translation Service", theme=gr.themes.Soft()) as interface:
        gr.Markdown(
            """
            # 📄 Document Translation Service
            
            Upload a Word document (.doc or .docx) and get it translated while preserving formatting.
            
            **Features:**
            - Supports .doc and .docx formats
            - Preserves original formatting
            - Two output modes: translation only or side-by-side comparison
            - Terminology highlighting in contrast mode
            """
        )
        
        with gr.Row():
            with gr.Column(scale=1):
                # Input section
                gr.Markdown("### Upload & Configure")
                
                file_input = gr.File(
                    label="Upload Document",
                    file_types=[".doc", ".docx"],
                    type="filepath"
                )
                
                source_lang = gr.Dropdown(
                    choices=language_options,
                    value="English",
                    label="Source Language",
                    info="Language of the original document"
                )
                
                target_lang = gr.Dropdown(
                    choices=language_options,
                    value="Chinese",
                    label="Target Language", 
                    info="Language to translate to"
                )
                
                translation_type = gr.Radio(
                    choices=translation_types,
                    value="Translation Only",
                    label="Output Type",
                    info="Choose between translation only or side-by-side comparison"
                )
                
                translate_btn = gr.Button(
                    "🔄 Translate Document",
                    variant="primary",
                    size="lg"
                )
            
            with gr.Column(scale=1):
                # Output section
                gr.Markdown("### Download Result")
                
                status_text = gr.Textbox(
                    label="Status",
                    placeholder="Upload a document and click translate to begin...",
                    interactive=False,
                    lines=3
                )
                
                download_file = gr.File(
                    label="Download Translated Document",
                    interactive=False
                )
        
        # Event handlers
        translate_btn.click(
            fn=app.sync_translate_document,
            inputs=[file_input, source_lang, target_lang, translation_type],
            outputs=[download_file, status_text],
            show_progress=True
        )
        
        # Example section
        gr.Markdown(
            """
            ### 📝 Usage Instructions
            
            1. **Upload**: Choose a .doc or .docx file
            2. **Configure**: Select source and target languages
            3. **Choose Output**: 
               - *Translation Only*: Get only the translated document
               - *Contrast*: Get original and translation side-by-side with terminology highlighting
            4. **Translate**: Click the translate button and wait for processing
            5. **Download**: Download the result when ready
            
            ### ⚠️ Notes
            
            - Processing time depends on document length
            - Large documents may take several minutes
            - The service preserves formatting, images, and tables
            - In contrast mode, terminology is highlighted with alternating colors
            """
        )
    
    return interface

if __name__ == "__main__":
    # Create and launch the interface
    interface = create_interface()
    interface.launch(
        server_name="0.0.0.0",
        server_port=7888,
        share=False,
        debug=True
    )
