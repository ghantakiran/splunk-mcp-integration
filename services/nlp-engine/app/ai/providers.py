"""
AI Provider interfaces and implementations for NLP Engine service
"""

import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, AsyncGenerator
from dataclasses import dataclass
import asyncio

import openai
import anthropic
import tiktoken
from tenacity import retry, stop_after_attempt, wait_exponential

from ..core.config import settings
from ..core.logging import get_logger, NLPMetrics

logger = get_logger(__name__)
nlp_metrics = NLPMetrics(logger)


@dataclass
class AIResponse:
    """Standardized AI response structure"""
    content: str
    provider: str
    model: str
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    processing_time: Optional[float] = None
    finish_reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class AIRequest:
    """Standardized AI request structure"""
    messages: List[Dict[str, str]]
    model: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    system_prompt: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class BaseAIProvider(ABC):
    """Abstract base class for AI providers"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
        self.metrics = NLPMetrics(self.logger)
    
    @abstractmethod
    async def generate_response(self, request: AIRequest) -> AIResponse:
        """Generate a response from the AI provider"""
        pass
    
    @abstractmethod
    async def stream_response(self, request: AIRequest) -> AsyncGenerator[str, None]:
        """Stream a response from the AI provider"""
        pass
    
    @abstractmethod
    def count_tokens(self, text: str, model: Optional[str] = None) -> int:
        """Count tokens in the given text"""
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the model"""
        pass


class OpenAIProvider(BaseAIProvider):
    """OpenAI API provider implementation"""
    
    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.client = openai.AsyncOpenAI(api_key=api_key)
        self.default_model = settings.openai_model
        self.max_tokens = settings.openai_max_tokens
        self.temperature = settings.openai_temperature
        self.timeout = settings.openai_timeout
        
        # Initialize tokenizer for token counting
        try:
            self.tokenizer = tiktoken.encoding_for_model(self.default_model)
        except KeyError:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")  # GPT-4 default
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def generate_response(self, request: AIRequest) -> AIResponse:
        """Generate a response using OpenAI API"""
        start_time = time.time()
        
        try:
            # Prepare messages
            messages = []
            if request.system_prompt:
                messages.append({"role": "system", "content": request.system_prompt})
            messages.extend(request.messages)
            
            # Count input tokens
            input_text = "\n".join([msg["content"] for msg in messages])
            input_tokens = self.count_tokens(input_text, request.model or self.default_model)
            
            # Make API call
            response = await self.client.chat.completions.create(
                model=request.model or self.default_model,
                messages=messages,
                max_tokens=request.max_tokens or self.max_tokens,
                temperature=request.temperature or self.temperature,
                timeout=self.timeout
            )
            
            processing_time = time.time() - start_time
            
            # Extract response data
            choice = response.choices[0]
            content = choice.message.content
            finish_reason = choice.finish_reason
            
            # Count output tokens
            output_tokens = self.count_tokens(content, request.model or self.default_model)
            
            # Log metrics
            self.metrics.log_ai_api_call(
                provider="openai",
                model=request.model or self.default_model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                processing_time=processing_time,
                success=True
            )
            
            return AIResponse(
                content=content,
                provider="openai",
                model=request.model or self.default_model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                processing_time=processing_time,
                finish_reason=finish_reason,
                metadata=request.metadata
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.metrics.log_ai_api_call(
                provider="openai",
                model=request.model or self.default_model,
                processing_time=processing_time,
                success=False,
                error=str(e)
            )
            self.logger.error(f"OpenAI API error: {e}")
            raise
    
    async def stream_response(self, request: AIRequest) -> AsyncGenerator[str, None]:
        """Stream a response using OpenAI API"""
        try:
            # Prepare messages
            messages = []
            if request.system_prompt:
                messages.append({"role": "system", "content": request.system_prompt})
            messages.extend(request.messages)
            
            # Make streaming API call
            stream = await self.client.chat.completions.create(
                model=request.model or self.default_model,
                messages=messages,
                max_tokens=request.max_tokens or self.max_tokens,
                temperature=request.temperature or self.temperature,
                stream=True
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            self.logger.error(f"OpenAI streaming error: {e}")
            raise
    
    def count_tokens(self, text: str, model: Optional[str] = None) -> int:
        """Count tokens using tiktoken"""
        try:
            return len(self.tokenizer.encode(text))
        except Exception as e:
            self.logger.warning(f"Token counting failed: {e}")
            # Fallback to rough estimation
            return len(text.split()) * 1.3
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get OpenAI model information"""
        return {
            "provider": "openai",
            "model": self.default_model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "supports_streaming": True,
            "supports_function_calling": True
        }


class AnthropicProvider(BaseAIProvider):
    """Anthropic API provider implementation"""
    
    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.default_model = settings.anthropic_model
        self.max_tokens = settings.anthropic_max_tokens
        self.temperature = settings.anthropic_temperature
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def generate_response(self, request: AIRequest) -> AIResponse:
        """Generate a response using Anthropic API"""
        start_time = time.time()
        
        try:
            # Prepare messages for Anthropic format
            messages = []
            system_prompt = request.system_prompt
            
            for msg in request.messages:
                # Convert role if necessary
                role = msg["role"]
                if role == "assistant":
                    role = "assistant"
                elif role == "user":
                    role = "user"
                elif role == "system":
                    # Anthropic handles system prompts separately
                    system_prompt = msg["content"]
                    continue
                    
                messages.append({
                    "role": role,
                    "content": msg["content"]
                })
            
            # Count input tokens (rough estimation for Anthropic)
            input_text = "\n".join([msg["content"] for msg in messages])
            if system_prompt:
                input_text = system_prompt + "\n" + input_text
            input_tokens = self.count_tokens(input_text)
            
            # Make API call
            kwargs = {
                "model": request.model or self.default_model,
                "messages": messages,
                "max_tokens": request.max_tokens or self.max_tokens,
                "temperature": request.temperature or self.temperature
            }
            
            if system_prompt:
                kwargs["system"] = system_prompt
            
            response = await self.client.messages.create(**kwargs)
            
            processing_time = time.time() - start_time
            
            # Extract response data
            content = response.content[0].text if response.content else ""
            
            # Count output tokens
            output_tokens = self.count_tokens(content)
            
            # Log metrics
            self.metrics.log_ai_api_call(
                provider="anthropic",
                model=request.model or self.default_model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                processing_time=processing_time,
                success=True
            )
            
            return AIResponse(
                content=content,
                provider="anthropic",
                model=request.model or self.default_model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                processing_time=processing_time,
                finish_reason=response.stop_reason,
                metadata=request.metadata
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.metrics.log_ai_api_call(
                provider="anthropic",
                model=request.model or self.default_model,
                processing_time=processing_time,
                success=False,
                error=str(e)
            )
            self.logger.error(f"Anthropic API error: {e}")
            raise
    
    async def stream_response(self, request: AIRequest) -> AsyncGenerator[str, None]:
        """Stream a response using Anthropic API"""
        try:
            # Prepare messages
            messages = []
            system_prompt = request.system_prompt
            
            for msg in request.messages:
                role = msg["role"]
                if role == "system":
                    system_prompt = msg["content"]
                    continue
                messages.append({"role": role, "content": msg["content"]})
            
            # Make streaming API call
            kwargs = {
                "model": request.model or self.default_model,
                "messages": messages,
                "max_tokens": request.max_tokens or self.max_tokens,
                "temperature": request.temperature or self.temperature,
                "stream": True
            }
            
            if system_prompt:
                kwargs["system"] = system_prompt
            
            async with self.client.messages.stream(**kwargs) as stream:
                async for text in stream.text_stream:
                    yield text
                    
        except Exception as e:
            self.logger.error(f"Anthropic streaming error: {e}")
            raise
    
    def count_tokens(self, text: str, model: Optional[str] = None) -> int:
        """Count tokens for Anthropic (estimation)"""
        # Rough estimation since Anthropic doesn't provide exact tokenizer
        return int(len(text.split()) * 1.3)
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get Anthropic model information"""
        return {
            "provider": "anthropic",
            "model": self.default_model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "supports_streaming": True,
            "supports_function_calling": False
        }


class AIProviderFactory:
    """Factory for creating AI provider instances"""
    
    @staticmethod
    def create_provider(provider_name: str) -> BaseAIProvider:
        """Create an AI provider instance"""
        provider_name = provider_name.lower()
        
        if provider_name == "openai":
            if not settings.openai_api_key:
                raise ValueError("OpenAI API key not configured")
            return OpenAIProvider(settings.openai_api_key)
        
        elif provider_name == "anthropic":
            if not settings.anthropic_api_key:
                raise ValueError("Anthropic API key not configured")
            return AnthropicProvider(settings.anthropic_api_key)
        
        else:
            raise ValueError(f"Unknown AI provider: {provider_name}")
    
    @staticmethod
    def get_available_providers() -> List[str]:
        """Get list of available providers based on configuration"""
        providers = []
        
        if settings.openai_api_key:
            providers.append("openai")
        
        if settings.anthropic_api_key:
            providers.append("anthropic")
        
        return providers
    
    @staticmethod
    def get_default_provider() -> BaseAIProvider:
        """Get the default configured provider"""
        return AIProviderFactory.create_provider(settings.default_ai_provider)


class AIProviderManager:
    """Manager for handling multiple AI providers with fallback"""
    
    def __init__(self):
        self.providers = {}
        self.available_providers = AIProviderFactory.get_available_providers()
        self.default_provider_name = settings.default_ai_provider
        
        # Initialize all available providers
        for provider_name in self.available_providers:
            try:
                self.providers[provider_name] = AIProviderFactory.create_provider(provider_name)
                logger.info(f"Initialized {provider_name} provider")
            except Exception as e:
                logger.warning(f"Failed to initialize {provider_name} provider: {e}")
    
    async def generate_response(
        self, 
        request: AIRequest, 
        provider_name: Optional[str] = None,
        enable_fallback: bool = True
    ) -> AIResponse:
        """Generate response with optional fallback to other providers"""
        target_provider = provider_name or self.default_provider_name
        
        # Try primary provider
        if target_provider in self.providers:
            try:
                return await self.providers[target_provider].generate_response(request)
            except Exception as e:
                logger.warning(f"Primary provider {target_provider} failed: {e}")
                
                if not enable_fallback:
                    raise
        
        # Try fallback providers if enabled
        if enable_fallback:
            for fallback_name, provider in self.providers.items():
                if fallback_name != target_provider:
                    try:
                        logger.info(f"Attempting fallback to {fallback_name}")
                        return await provider.generate_response(request)
                    except Exception as e:
                        logger.warning(f"Fallback provider {fallback_name} failed: {e}")
                        continue
        
        raise Exception("All AI providers failed")
    
    async def stream_response(
        self, 
        request: AIRequest, 
        provider_name: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Stream response from specified provider"""
        target_provider = provider_name or self.default_provider_name
        
        if target_provider not in self.providers:
            raise ValueError(f"Provider {target_provider} not available")
        
        async for chunk in self.providers[target_provider].stream_response(request):
            yield chunk
    
    def get_provider_info(self, provider_name: Optional[str] = None) -> Dict[str, Any]:
        """Get information about a provider"""
        target_provider = provider_name or self.default_provider_name
        
        if target_provider not in self.providers:
            raise ValueError(f"Provider {target_provider} not available")
        
        return self.providers[target_provider].get_model_info()
    
    def get_all_provider_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all available providers"""
        return {
            name: provider.get_model_info() 
            for name, provider in self.providers.items()
        }


# Global AI provider manager instance
ai_manager = AIProviderManager()