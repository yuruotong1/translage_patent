#!/usr/bin/env python3
"""
Startup script for Word Translation Service with optimized GPU management
"""
import multiprocessing as mp

import os
import sys
import torch
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def setup_environment():
    """Set up environment variables for optimal GPU usage"""
    mp.set_start_method("spawn", force=True) 
    os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'max_split_size_mb:512'
    os.environ['OMP_NUM_THREADS'] = '4'
    os.environ['CUDA_LAUNCH_BLOCKING'] = '0'
    

def main():
    """Main startup function"""
    # Display system information
    logger.info(f"Python version: {sys.version}")
    logger.info(f"PyTorch version: {torch.__version__}")
    logger.info(f"CUDA version: {torch.version.cuda}")
    logger.info(f"GPU count: {torch.cuda.device_count()}")
    # logger.info(f"GPU name: {torch.cuda.get_device_name(0)}")
   
    logger.info(f"GPU memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
    logger.info(f"GPU is available: {torch.cuda.is_available()}")
    logger.info("Starting Word Translation Service...")
    
    # Setup environment
    setup_environment()
    # Import and start the Gradio app
    try:
        from gradio_ui import create_interface
        logger.info("Creating Gradio interface...")
        
        interface = create_interface()
        logger.info("Starting server on http://0.0.0.0:7888")
        
        interface.launch(
            server_name="0.0.0.0",
            server_port=7888,
            share=False,
            debug=False,
            show_error=True
        )
        
    except Exception as e:
        logger.error(f"Failed to start service: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
