#!/usr/bin/env python3
"""
DEPRECATED: Test OpenAI Official Client Integration

⚠️  WARNING: This script is DEPRECATED but preserved for safety.
    OpenAI integration is now part of the main LLM system.

This script tests OpenAI client integration in isolation.
The main system now has integrated OpenAI functionality with proper configuration.

PRESERVED FOR SAFETY: Contains OpenAI testing patterns that could be useful.
TODO: Integrate OpenAI testing features into main system testing, then remove this script.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.llm.client import LLMClient, LLMConfig, LLMProvider


async def test_openai_official_client():
    """Test OpenAI using official client library"""
    print("🧪 Testing OpenAI Official Client...")
    
    # Get API key from environment
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ No OPENAI_API_KEY environment variable found")
        print("   Set it with: export OPENAI_API_KEY='your-key-here'")
        return False
    
    try:
        # Create LLM client with official library
        config = LLMConfig(
            provider=LLMProvider.OPENAI,
            model="gpt-5-mini",  # Use the cost-effective model
            api_key=api_key,
            max_tokens=1000,
            temperature=0.1
        )
        
        client = LLMClient(config)
        
        # Test simple request
        print("📤 Sending request to OpenAI...")
        response = await client.generate_response(
            "Respond with JSON: {\"status\": \"working\", \"client\": \"official_openai\"}"
        )
        
        print("✅ OpenAI Official Client Test Successful!")
        print(f"   Provider: {config.provider.value}")
        print(f"   Model: {config.model}")
        print(f"   Response: {response}")
        
        return True
        
    except Exception as e:
        print(f"❌ OpenAI Official Client Test Failed: {e}")
        return False


async def test_direct_openai():
    """Test direct OpenAI client usage (as suggested by user)"""
    print("\n🧪 Testing Direct OpenAI Client...")
    
    try:
        from openai import AsyncOpenAI
        
        # Get API key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("❌ No OPENAI_API_KEY environment variable found")
            return False
        
        # Create client directly
        client = AsyncOpenAI(api_key=api_key)
        
        # Test request (using chat.completions instead of responses for compatibility)
        response = await client.chat.completions.create(
            model="gpt-5-mini",
            messages=[{"role": "user", "content": "Write a one-sentence bedtime story about a unicorn."}],
            max_tokens=100
        )
        
        print("✅ Direct OpenAI Client Test Successful!")
        print(f"   Story: {response.choices[0].message.content}")
        
        return True
        
    except Exception as e:
        print(f"❌ Direct OpenAI Client Test Failed: {e}")
        return False


async def main():
    """Run all tests"""
    print("🚀 OpenAI Official Client Test Suite")
    print("=" * 50)
    
    # Test 1: Our LLM client wrapper
    wrapper_ok = await test_openai_official_client()
    
    # Test 2: Direct OpenAI client
    direct_ok = await test_direct_openai()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    print(f"   LLM Client Wrapper: {'✅ PASS' if wrapper_ok else '❌ FAIL'}")
    print(f"   Direct OpenAI Client: {'✅ PASS' if direct_ok else '❌ FAIL'}")
    
    if wrapper_ok and direct_ok:
        print("\n🎉 All tests passed! Official OpenAI client integration is working.")
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")


if __name__ == "__main__":
    asyncio.run(main())
