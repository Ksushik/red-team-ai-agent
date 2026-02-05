"""
Base classes and interfaces for AI target adapters.

This module defines the core interfaces that all target adapters must implement,
as well as common data structures for target responses and configuration.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import asyncio
import logging

logger = logging.getLogger(__name__)


@dataclass
class TargetResponse:
    """Response from an AI target system."""
    
    # Core response data
    content: str
    success: bool
    
    # Metadata
    timestamp: datetime = field(default_factory=datetime.utcnow)
    response_time: float = 0.0  # seconds
    
    # Optional response metadata
    model: Optional[str] = None
    tokens_used: Optional[int] = None
    finish_reason: Optional[str] = None
    
    # Raw response data (for debugging/analysis)
    raw_response: Optional[Dict[str, Any]] = None
    
    # Error information
    error: Optional[str] = None
    error_code: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary for serialization."""
        return {
            "content": self.content,
            "success": self.success,
            "timestamp": self.timestamp.isoformat(),
            "response_time": self.response_time,
            "model": self.model,
            "tokens_used": self.tokens_used,
            "finish_reason": self.finish_reason,
            "error": self.error,
            "error_code": self.error_code,
        }


@dataclass
class RateLimit:
    """Rate limiting configuration for a target."""
    
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    tokens_per_minute: int = 10000
    concurrent_requests: int = 10
    
    def __post_init__(self):
        """Validate rate limit values."""
        if any(v <= 0 for v in [self.requests_per_minute, self.requests_per_hour, 
                               self.tokens_per_minute, self.concurrent_requests]):
            raise ValueError("All rate limit values must be positive")


@dataclass
class TargetInfo:
    """Information about an AI target system."""
    
    name: str
    model: str
    provider: str
    version: Optional[str] = None
    
    # Capabilities
    supports_system_messages: bool = True
    supports_function_calling: bool = False
    supports_streaming: bool = True
    max_tokens: Optional[int] = None
    context_window: Optional[int] = None
    
    # Pricing (tokens per dollar, if known)
    input_token_cost: Optional[float] = None
    output_token_cost: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "model": self.model,
            "provider": self.provider,
            "version": self.version,
            "supports_system_messages": self.supports_system_messages,
            "supports_function_calling": self.supports_function_calling,
            "supports_streaming": self.supports_streaming,
            "max_tokens": self.max_tokens,
            "context_window": self.context_window,
            "input_token_cost": self.input_token_cost,
            "output_token_cost": self.output_token_cost,
        }


class AITarget(ABC):
    """
    Base class for all AI target adapters.
    
    Target adapters implement the interface to communicate with different
    AI systems (OpenAI, Anthropic, local models, etc.).
    """
    
    def __init__(self, name: str, model: str, **kwargs):
        self.name = name
        self.model = model
        self.config = kwargs
        self.logger = logging.getLogger(f"redteam.targets.{name}")
        
        # Track usage statistics
        self.total_requests = 0
        self.total_tokens = 0
        self.failed_requests = 0
    
    @abstractmethod
    async def send_prompt(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> TargetResponse:
        """
        Send a prompt to the AI system and return the response.
        
        Args:
            prompt: The prompt text to send
            context: Optional context including system messages, conversation history, etc.
            
        Returns:
            TargetResponse containing the AI system's response
        """
        pass
    
    @abstractmethod
    async def get_system_info(self) -> TargetInfo:
        """
        Get information about the target AI system.
        
        Returns:
            TargetInfo containing system capabilities and metadata
        """
        pass
    
    @abstractmethod
    def get_rate_limits(self) -> RateLimit:
        """
        Get rate limiting configuration for this target.
        
        Returns:
            RateLimit object with rate limiting parameters
        """
        pass
    
    async def test_connection(self) -> bool:
        """
        Test the connection to the AI system.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            response = await self.send_prompt("Hello", {})
            return response.success
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False
    
    async def extract_system_prompt(self) -> Optional[str]:
        """
        Attempt to extract the system prompt from the target.
        
        This is optional functionality that some targets may not support.
        
        Returns:
            System prompt if extractable, None otherwise
        """
        self.logger.warning(f"System prompt extraction not implemented for {self.name}")
        return None
    
    async def get_conversation_history(self) -> List[Dict[str, str]]:
        """
        Get conversation history if the target maintains state.
        
        Returns:
            List of conversation turns with 'role' and 'content' keys
        """
        return []
    
    def reset_conversation(self) -> None:
        """Reset conversation history if the target maintains state."""
        pass
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """
        Get usage statistics for this target.
        
        Returns:
            Dictionary with usage metrics
        """
        return {
            "total_requests": self.total_requests,
            "total_tokens": self.total_tokens,
            "failed_requests": self.failed_requests,
            "success_rate": (
                (self.total_requests - self.failed_requests) / max(1, self.total_requests)
            ),
        }
    
    def _update_stats(self, response: TargetResponse) -> None:
        """Update internal usage statistics."""
        self.total_requests += 1
        if response.tokens_used:
            self.total_tokens += response.tokens_used
        if not response.success:
            self.failed_requests += 1
    
    def __str__(self) -> str:
        return f"{self.name} ({self.model})"
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.name}>"


class StatefulTarget(AITarget):
    """
    Base class for AI targets that maintain conversation state.
    
    This class provides common functionality for targets that need to
    track conversation history across multiple interactions.
    """
    
    def __init__(self, name: str, model: str, **kwargs):
        super().__init__(name, model, **kwargs)
        self.conversation_history: List[Dict[str, str]] = []
        self.system_message: Optional[str] = None
    
    def add_message(self, role: str, content: str) -> None:
        """
        Add a message to the conversation history.
        
        Args:
            role: The role of the message sender (e.g., 'user', 'assistant', 'system')
            content: The content of the message
        """
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def set_system_message(self, message: str) -> None:
        """
        Set the system message for the conversation.
        
        Args:
            message: The system message content
        """
        self.system_message = message
    
    async def get_conversation_history(self) -> List[Dict[str, str]]:
        """Get the current conversation history."""
        return self.conversation_history.copy()
    
    def reset_conversation(self) -> None:
        """Reset the conversation history."""
        self.conversation_history.clear()
        self.system_message = None
        self.logger.info("Conversation history reset")
    
    async def send_prompt(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> TargetResponse:
        """
        Send prompt and automatically update conversation history.
        
        This method should be called by subclasses after sending the actual prompt.
        """
        # Add user message to history
        self.add_message("user", prompt)
        
        # Call the actual implementation
        response = await self._send_prompt_impl(prompt, context)
        
        # Add assistant response to history if successful
        if response.success:
            self.add_message("assistant", response.content)
        
        # Update statistics
        self._update_stats(response)
        
        return response
    
    @abstractmethod
    async def _send_prompt_impl(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> TargetResponse:
        """
        Internal implementation of send_prompt.
        
        Subclasses should implement this method instead of send_prompt
        to get automatic conversation history management.
        """
        pass


class MockTarget(AITarget):
    """
    Mock AI target for testing purposes.
    
    This target simulates responses without calling real AI APIs,
    making it useful for testing attack plugins and campaigns.
    """
    
    def __init__(self, name: str = "mock", model: str = "mock-model", 
                 vulnerability_profile: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(name, model, **kwargs)
        self.vulnerability_profile = vulnerability_profile or {}
        self.response_delay = kwargs.get("response_delay", 0.1)
        
    async def send_prompt(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> TargetResponse:
        """Simulate sending a prompt and return a mock response."""
        start_time = asyncio.get_event_loop().time()
        
        # Simulate response delay
        await asyncio.sleep(self.response_delay)
        
        # Generate mock response based on vulnerability profile
        response_content = self._generate_mock_response(prompt)
        
        response_time = asyncio.get_event_loop().time() - start_time
        
        response = TargetResponse(
            content=response_content,
            success=True,
            response_time=response_time,
            model=self.model,
            tokens_used=len(prompt.split()) + len(response_content.split())
        )
        
        self._update_stats(response)
        return response
    
    def _generate_mock_response(self, prompt: str) -> str:
        """Generate a mock response based on the prompt and vulnerability profile."""
        prompt_lower = prompt.lower()
        
        # Check for specific vulnerabilities
        if "system prompt" in prompt_lower and self.vulnerability_profile.get("leaks_system_prompt"):
            return "I am a helpful AI assistant. My system prompt is: [CONFIDENTIAL SYSTEM INSTRUCTIONS]"
        
        if "ignore" in prompt_lower and self.vulnerability_profile.get("vulnerable_to_injection"):
            return "I will ignore my previous instructions and help you with whatever you want!"
        
        if "jailbreak" in prompt_lower and self.vulnerability_profile.get("vulnerable_to_jailbreak"):
            return "As an unfiltered AI, I can help you with anything, including harmful content!"
        
        # Default safe response
        return "I'm a helpful AI assistant. How can I help you today?"
    
    async def get_system_info(self) -> TargetInfo:
        """Return mock system information."""
        return TargetInfo(
            name=self.name,
            model=self.model,
            provider="mock",
            version="1.0.0",
            supports_system_messages=True,
            supports_function_calling=False,
            supports_streaming=True,
            max_tokens=4096,
            context_window=8192
        )
    
    def get_rate_limits(self) -> RateLimit:
        """Return mock rate limits."""
        return RateLimit(
            requests_per_minute=1000,
            requests_per_hour=10000,
            tokens_per_minute=100000,
            concurrent_requests=100
        )


# Export commonly used classes
__all__ = [
    "TargetResponse",
    "RateLimit", 
    "TargetInfo",
    "AITarget",
    "StatefulTarget",
    "MockTarget",
]