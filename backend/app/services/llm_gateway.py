import os
import logging
from typing import List, Dict, Any, AsyncIterator, Optional
from openai import AzureOpenAI, AsyncAzureOpenAI
import tiktoken
from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMGateway:
    def __init__(self, model_name: str = "gpt-4o-mini"):
        self.model_name = model_name
        self.deployment_name = self._get_deployment_name(model_name)
        
        self.client = AzureOpenAI(
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
        )
        
        self.async_client = AsyncAzureOpenAI(
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
        )
        
        try:
            self.tokenizer = tiktoken.encoding_for_model(model_name)
        except KeyError:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
    
    def _get_deployment_name(self, model_name: str) -> str:
        deployment_map = {
            "gpt-4o-mini": settings.AZURE_OPENAI_DEPLOYMENT_NAME,
            "gpt-4": "gpt-4",
            "gpt-3.5-turbo": "gpt-35-turbo"
        }
        return deployment_map.get(model_name, settings.AZURE_OPENAI_DEPLOYMENT_NAME)
    
    def count_tokens(self, text: str) -> int:
        return len(self.tokenizer.encode(text))
    
    def count_messages_tokens(self, messages: List[Dict[str, str]]) -> int:
        total = 0
        for message in messages:
            total += 4
            for key, value in message.items():
                total += len(self.tokenizer.encode(value))
                if key == "role":
                    total -= 1
        total += 2
        return total
    
    def get_completion(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        try:
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=messages,
                **kwargs
            )
            
            return {
                "content": response.choices[0].message.content,
                "role": response.choices[0].message.role,
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
        except Exception as e:
            logger.error(f"Error getting completion: {e}")
            raise
    
    async def get_completion_async(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        try:
            response = await self.async_client.chat.completions.create(
                model=self.deployment_name,
                messages=messages,
                **kwargs
            )
            
            return {
                "content": response.choices[0].message.content,
                "role": response.choices[0].message.role,
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
        except Exception as e:
            logger.error(f"Error getting async completion: {e}")
            raise
    
    async def get_streaming_completion(
        self, 
        messages: List[Dict[str, str]], 
        **kwargs
    ) -> AsyncIterator[str]:
        try:
            kwargs['stream'] = True
            response = await self.async_client.chat.completions.create(
                model=self.deployment_name,
                messages=messages,
                **kwargs
            )
            
            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error(f"Error getting streaming completion: {e}")
            raise
    
    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        pricing = {
            "gpt-4o-mini": {"prompt": 0.00015, "completion": 0.0006},
            "gpt-4": {"prompt": 0.03, "completion": 0.06},
            "gpt-3.5-turbo": {"prompt": 0.0005, "completion": 0.0015}
        }
        
        model_pricing = pricing.get(self.model_name, pricing["gpt-4o-mini"])
        
        prompt_cost = (prompt_tokens / 1000) * model_pricing["prompt"]
        completion_cost = (completion_tokens / 1000) * model_pricing["completion"]
        
        return prompt_cost + completion_cost