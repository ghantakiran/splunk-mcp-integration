"""
AI Integration layer for NLP Engine service

Provides interfaces to various AI providers (OpenAI, Anthropic) 
for natural language processing tasks.
"""

from .providers import (
    AIRequest,
    AIResponse,
    BaseAIProvider,
    OpenAIProvider,
    AnthropicProvider,
    AIProviderFactory,
    AIProviderManager,
    ai_manager
)
from .nlp_service import (
    SPLTranslationRequest,
    SPLTranslationResponse,
    IntentClassificationResult,
    EntityExtractionResult,
    NLPService,
    nlp_service
)

__all__ = [
    "AIRequest",
    "AIResponse", 
    "BaseAIProvider",
    "OpenAIProvider",
    "AnthropicProvider",
    "AIProviderFactory",
    "AIProviderManager",
    "ai_manager",
    "SPLTranslationRequest",
    "SPLTranslationResponse",
    "IntentClassificationResult",
    "EntityExtractionResult", 
    "NLPService",
    "nlp_service"
]