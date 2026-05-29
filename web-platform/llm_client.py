#!/usr/bin/env python3
"""
Unified LLM client supporting multiple providers:
- MiniMax
- DeepSeek
- OpenAI compatible APIs
- Custom API (OpenAI-compatible)
"""

import json
import os
from pathlib import Path

class LLMClient:
    SUPPORTED_MODELS = {
        'minimax': {
            'name': 'MiniMax',
            'models': ['MiniMax-M2.7'],
            'requires_api_key': 'minimax_api_key',
            'default_model': 'MiniMax-M2.7',
            'default_base_url': 'https://api.minimaxi.com/anthropic'
        },
        'deepseek': {
            'name': 'DeepSeek',
            'models': ['deepseek-chat'],
            'requires_api_key': 'deepseek_api_key',
            'default_model': 'deepseek-chat',
            'default_base_url': 'https://api.deepseek.com/v1'
        },
        'openai': {
            'name': 'OpenAI',
            'models': ['gpt-4o', 'gpt-4', 'gpt-3.5-turbo'],
            'requires_api_key': 'openai_api_key',
            'default_model': 'gpt-4o',
            'default_base_url': 'https://api.openai.com/v1'
        },
        'custom': {
            'name': '自定义 API',
            'models': [],
            'requires_api_key': 'custom_api_key',
            'default_model': '',
            'default_base_url': ''
        }
    }
    
    def __init__(self, provider, api_key, model=None, base_url=None):
        self.provider = provider.lower()
        self.api_key = api_key
        
        provider_info = self.SUPPORTED_MODELS.get(self.provider)
        if provider_info:
            self.model = model or provider_info['default_model']
            self.base_url = base_url or provider_info['default_base_url']
        else:
            self.model = model or ''
            self.base_url = base_url or ''
            
        self.client = None
        self._init_client()
    
    def _init_client(self):
        if self.provider == 'minimax':
            self._init_minimax()
        elif self.provider == 'deepseek':
            self._init_deepseek()
        elif self.provider == 'openai' or self.provider == 'custom':
            self._init_openai()
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
    
    def _init_minimax(self):
        try:
            import anthropic
        except ImportError:
            import subprocess
            import sys
            subprocess.run([sys.executable, '-m', 'pip', 'install', 'anthropic', '-q'], check=True)
            import anthropic
        
        self.client = anthropic.Anthropic(
            base_url=self.base_url,
            api_key=self.api_key,
        )
    
    def _init_deepseek(self):
        try:
            from openai import OpenAI
        except ImportError:
            import subprocess
            import sys
            subprocess.run([sys.executable, '-m', 'pip', 'install', 'openai', '-q'], check=True)
            from openai import OpenAI
        
        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
        )
    
    def _init_openai(self):
        try:
            from openai import OpenAI
        except ImportError:
            import subprocess
            import sys
            subprocess.run([sys.executable, '-m', 'pip', 'install', 'openai', '-q'], check=True)
            from openai import OpenAI
        
        client_kwargs = {'api_key': self.api_key}
        if self.base_url:
            client_kwargs['base_url'] = self.base_url
        
        self.client = OpenAI(**client_kwargs)
    
    def generate(self, system_prompt, user_prompt, max_tokens=8192):
        if self.provider == 'minimax':
            return self._generate_minimax(system_prompt, user_prompt, max_tokens)
        elif self.provider == 'deepseek' or self.provider == 'openai' or self.provider == 'custom':
            return self._generate_openai_compatible(system_prompt, user_prompt, max_tokens)
    
    def _generate_minimax(self, system_prompt, user_prompt, max_tokens):
        message = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": [{"type": "text", "text": user_prompt}]}],
        )
        
        article_text = ""
        for block in message.content:
            if block.type == "text":
                article_text = block.text
                break
        return article_text
    
    def _generate_openai_compatible(self, system_prompt, user_prompt, max_tokens):
        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        return response.choices[0].message.content

def get_available_models(config):
    """Get list of available models based on configured API keys."""
    available = []
    for provider, info in LLMClient.SUPPORTED_MODELS.items():
        api_key = config.get(info['requires_api_key'], '').strip()
        if api_key:
            model_key = f'{provider}_model'
            base_url_key = f'{provider}_base_url'
            available.append({
                'provider': provider,
                'name': info['name'],
                'models': info['models'],
                'default_model': config.get(model_key, info['default_model']),
                'base_url': config.get(base_url_key, info['default_base_url'])
            })
    return available

def get_model_config(config):
    """Get default model configuration."""
    available = get_available_models(config)
    if available:
        return available[0]
    return None