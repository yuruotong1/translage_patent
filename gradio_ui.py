import gradio as gr
import asyncio
import os
import tempfile
import shutil

from word_translation_service import WordTranslationService
from glossary_manager import GlossaryManager
from prompt import api_key, base_url
import logging

class GradioTranslationApp:
    def __init__(self):
        self.glossary_manager = GlossaryManager()
        self.translator = WordTranslationService(api_key, base_url, self.glossary_manager)
        
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
    
    def sync_generate_glossary(self, file, source_lang, target_lang):
        """Generate glossary from uploaded document (synchronous wrapper)"""
        if file is None:
            return None, "Please upload a document first."
        
        try:
            # Read document content
            file_ext = os.path.splitext(file.name)[1].lower()
            
            if file_ext == '.docx':
                import docx
                doc = docx.Document(file.name)
                text = '\n'.join([para.text for para in doc.paragraphs if para.text.strip()])
            elif file_ext == '.doc':
                import docx2txt
                text = docx2txt.process(file.name)
            else:
                return None, "Unsupported file format. Please upload a .doc or .docx file."
            
            if not text.strip():
                return None, "Document appears to be empty."
            
            # Generate glossary using AI in a new thread
            import concurrent.futures
            import threading
            
            def run_async_in_thread():
                # Create new event loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(
                        self.glossary_manager.generate_glossary_from_text(text, source_lang, target_lang)
                    )
                finally:
                    loop.close()
            
            # Run in executor to avoid event loop conflicts
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_async_in_thread)
                terms = future.result(timeout=300)  # 5 minute timeout
            
            if not terms:
                return None, "No terms found in the document."
            
            # Create temporary Excel file
            temp_dir = tempfile.mkdtemp()
            original_name = os.path.splitext(os.path.basename(file.name))[0]
            excel_path = os.path.join(temp_dir, f"{original_name}_glossary.xlsx")
            
            # Save to Excel
            self.glossary_manager.save_glossary_to_excel(terms, excel_path)
            
            return excel_path, f"Glossary generated successfully! Found {len(terms)} terms."
            
        except Exception as e:
            import traceback
            logging.error(f"Error generating glossary: {traceback.format_exc()}")
            return None, f"Error generating glossary: {str(e)}"
    
    def load_glossary(self, file):
        """Load glossary from uploaded Excel file"""
        if file is None:
            return "Please upload a glossary Excel file first."
        
        try:
            glossary_dict = self.glossary_manager.load_glossary_from_excel(file.name)
            return f"Glossary loaded successfully! {len(glossary_dict)} terms available for translation."
        except Exception as e:
            return f"Error loading glossary: {str(e)}"

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
            - Generate and use custom glossaries
            """
        )
        
        # Tab-based layout
        with gr.Tabs():
            # Glossary Generation Tab
            with gr.TabItem("🔤 Generate Glossary"):
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("### Step 1: Generate Glossary from Document")
                        
                        glossary_file_input = gr.File(
                            label="Upload Document for Glossary Generation",
                            file_types=[".doc", ".docx"],
                            type="filepath"
                        )
                        
                        glossary_source_lang = gr.Dropdown(
                            choices=language_options,
                            value="english",
                            label="Source Language",
                            info="Language of the original document"
                        )
                        
                        glossary_target_lang = gr.Dropdown(
                            choices=language_options,
                            value="chinese",
                            label="Target Language", 
                            info="Language to generate glossary for"
                        )
                        
                        generate_glossary_btn = gr.Button(
                            "📋 Generate Glossary",
                            variant="primary",
                            size="lg"
                        )
                    
                    with gr.Column(scale=1):
                        gr.Markdown("### Download Generated Glossary")
                        
                        glossary_status = gr.Textbox(
                            label="Status",
                            placeholder="Upload a document and click generate glossary...",
                            interactive=False,
                            lines=3
                        )
                        
                        glossary_download = gr.File(
                            label="Download Glossary Excel",
                            interactive=False
                        )
                        
                        gr.Markdown(
                            """
                            **Instructions:**
                            1. Upload your document
                            2. Select source and target languages
                            3. Click "Generate Glossary" to extract terms
                            4. Download the Excel file
                            5. Edit the glossary as needed
                            6. Use it in the translation tab
                            """
                        )
            
            # Translation Tab
            with gr.TabItem("🔄 Translate Document"):
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
                            value="english",
                            label="Source Language",
                            info="Language of the original document"
                        )
                        
                        target_lang = gr.Dropdown(
                            choices=language_options,
                            value="chinese",
                            label="Target Language", 
                            info="Language to translate to"
                        )
                        
                        translation_type = gr.Radio(
                            choices=translation_types,
                            value="Translation Only",
                            label="Output Type",
                            info="Choose between translation only or side-by-side comparison"
                        )
                        
                        # Glossary upload section
                        gr.Markdown("### Optional: Upload Custom Glossary")
                        
                        glossary_file = gr.File(
                            label="Upload Glossary Excel (Optional)",
                            file_types=[".xlsx"],
                            type="filepath"
                        )
                        
                        glossary_load_status = gr.Textbox(
                            label="Glossary Status",
                            placeholder="No glossary loaded",
                            interactive=False,
                            lines=2
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
        
        # Glossary generation
        generate_glossary_btn.click(
            fn=app.sync_generate_glossary,
            inputs=[glossary_file_input, glossary_source_lang, glossary_target_lang],
            outputs=[glossary_download, glossary_status],
            show_progress=True
        )
        
        # Glossary auto-loading when file is uploaded
        glossary_file.change(
            fn=app.load_glossary,
            inputs=[glossary_file],
            outputs=[glossary_load_status],
            show_progress=False
        )
        
        # Document translation
        translate_btn.click(
            fn=app.sync_translate_document,
            inputs=[file_input, source_lang, target_lang, translation_type],
            outputs=[download_file, status_text],
            show_progress=True
        )
        
        # Usage instructions
        gr.Markdown(
            """
            ### 📝 Usage Instructions
            
            **For Glossary Generation:**
            1. Go to "Generate Glossary" tab
            2. Upload your document
            3. Select source and target languages  
            4. Click "Generate Glossary" and wait for processing
            5. Download the Excel file and edit as needed
            
            **For Translation:**
            1. Go to "Translate Document" tab
            2. Upload your document to translate
            3. (Optional) Upload your edited glossary Excel file (it will load automatically)
            4. Select languages and output type
            5. Click "Translate Document" and wait for processing
            6. Download the translated result
            
            ### ⚠️ Notes
            
            - Processing time depends on document length
            - Large documents may take several minutes
            - The service preserves formatting, images, and tables
            - Custom glossary terms will be highlighted in contrast mode
            - Glossary Excel format: two columns "Source Content" and "Target Content"
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
