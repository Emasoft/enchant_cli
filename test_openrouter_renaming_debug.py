#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug OpenRouter API for renaming
"""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from renamenovels import make_openai_request
import logging

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_api_directly():
    """Test OpenRouter API directly"""
    
    api_key = os.environ.get('OPENROUTER_API_KEY')
    if not api_key:
        print("❌ OPENROUTER_API_KEY not found")
        return False
    
    print(f"✅ Using API key: {api_key[:10]}...")
    
    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant that extracts metadata from Chinese novel text."
        },
        {
            "role": "user", 
            "content": """Extract metadata from this Chinese novel text and return a JSON object:

第一章 重生归来

陈凡睁开眼睛，发现自己回到了十年前。

Return only a JSON object with these fields:
- novel_title_original: The original Chinese title
- novel_title_english: The English translation of the title
- author_name_original: The original Chinese author name
- author_name_english: The English translation of the author name
- author_name_romanized: The romanized (pinyin) version of the author name"""
        }
    ]
    
    try:
        print("\n📡 Calling OpenRouter API...")
        response = make_openai_request(
            api_key=api_key,
            model="gpt-4o-mini",
            temperature=0.0,
            messages=messages
        )
        
        print("\n✅ API Response received:")
        print(f"Model used: {response.get('model', 'N/A')}")
        
        if 'usage' in response:
            usage = response['usage']
            print(f"Tokens: {usage.get('total_tokens', 'N/A')}")
            print(f"Cost: ${usage.get('cost', 0):.6f}")
        
        if 'choices' in response and len(response['choices']) > 0:
            content = response['choices'][0]['message']['content']
            print(f"\nResponse content:\n{content}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_api_directly()
    sys.exit(0 if success else 1)