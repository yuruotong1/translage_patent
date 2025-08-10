#!/usr/bin/env python3
"""
GPU and Stanza model test script
"""

import torch
import stanza
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_gpu():
    """Test GPU functionality"""
    logger.info("Testing GPU...")
    

    logger.info(f"GPU available: {torch.cuda.get_device_name()}")
    logger.info(f"GPU count: {torch.cuda.device_count()}")
    
    # Test basic GPU operations
    x = torch.randn(100, 100).cuda()
    y = torch.randn(100, 100).cuda()
    z = torch.matmul(x, y)
    logger.info(f"GPU computation test passed: {z.shape}")
    
    # Clear memory
    del x, y, z
    torch.cuda.empty_cache()
    return True


def test_stanza():
    """Test Stanza model loading"""
    logger.info("Testing Stanza models...")
    
    try:
        # Test English
        logger.info("Loading English model...")
        start_time = time.time()
        nlp_en = stanza.Pipeline('en', processors='tokenize,pos', use_gpu=True)
        load_time = time.time() - start_time
        logger.info(f"English model loaded in {load_time:.2f} seconds")
        
        # Test processing
        doc = nlp_en("This is a test sentence.")
        logger.info(f"English processing test: {len(doc.sentences)} sentences")
        
        # Test Chinese
        logger.info("Loading Chinese model...")
        start_time = time.time()
        nlp_zh = stanza.Pipeline('zh-hans', processors='tokenize,pos', use_gpu=True)
        load_time = time.time() - start_time
        logger.info(f"Chinese model loaded in {load_time:.2f} seconds")
        
        # Test processing
        doc = nlp_zh("这是一个测试句子。")
        logger.info(f"Chinese processing test: {len(doc.sentences)} sentences")
        
        return True
        
    except Exception as e:
        logger.error(f"Stanza test failed: {e}")
        return False

def main():
    """Main test function"""
    logger.info("Starting GPU and Stanza tests...")
    
    # Test GPU
    gpu_ok = test_gpu()
    
    # Test Stanza
    stanza_ok = test_stanza()
    
    if gpu_ok and stanza_ok:
        logger.info("All tests passed! System is ready.")
    else:
        logger.warning("Some tests failed. Check the logs above.")
    
    return gpu_ok and stanza_ok

if __name__ == "__main__":
    main()
