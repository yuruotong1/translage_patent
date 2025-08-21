#!/usr/bin/env python3
"""
Startup script for Word Translation Service
"""
import multiprocessing as mp

import os
import sys

import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def setup_environment():
    """Set up environment variables"""
    mp.set_start_method("spawn", force=True) 
    os.environ['OMP_NUM_THREADS'] = '4'
    

def main():
    """Main startup function"""
    # Display system information
    logger.info(f"Python version: {sys.version}")
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
