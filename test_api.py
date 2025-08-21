#!/usr/bin/env python3
"""
Test API connection and authentication
"""
import asyncio
from openai import AsyncOpenAI
from prompt import api_key, base_url, model

async def test_api():
    """Test API connection"""
    try:
        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        
        print(f"Testing API connection...")
        print(f"API Key: {api_key[:20]}...{api_key[-10:]}")
        print(f"Base URL: {base_url}")
        print(f"Model: {model}")
        print("-" * 50)
        
        # Simple test request
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": "Hello, test message"}
            ],
            max_tokens=50
        )
        
        print("✓ API connection successful!")
        print(f"Response: {response.choices[0].message.content}")
        
    except Exception as e:
        print(f"✗ API connection failed: {e}")
        print(f"Error type: {type(e).__name__}")
        
        # Check if it's an authentication error
        if "401" in str(e) or "authentication" in str(e).lower():
            print("\n解决建议:")
            print("1. 检查API密钥是否正确")
            print("2. 确认OpenRouter账户状态是否正常") 
            print("3. 检查API密钥是否有足够的使用权限")
            print("4. 尝试重新生成API密钥")
        
if __name__ == "__main__":
    asyncio.run(test_api())
