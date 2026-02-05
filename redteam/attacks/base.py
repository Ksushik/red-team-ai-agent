"""
Base classes and interfaces for attack plugins.

This module defines the core interfaces that all attack plugins must implement,
as well as common data structures for attack results and configuration.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio
import logging

logger = logging.getLogger(__name__)


class AttackSeverity(Enum):
    """Severity levels for attack results."""
    CRITICAL = "CRITICAL"  # Full system compromise, data exfiltration
    HIGH = "HIGH"         # Significant security bypass, PII exposure
    MEDIUM = "MEDIUM"     # Partial security bypass, minor data leak
    LOW = "LOW"           # Unexpected behavior, potential weakness
    INFO = "INFO"         # System behavior documentation


class AttackCategory(Enum):
    """Categories of attacks supported by the framework."""
    PROMPT_INJECTION = "prompt_injection"
    JAILBREAKING = "jailbreaking"
    DATA_EXFILTRATION = "data_exfiltration"
    MODEL_MANIPULATION = "model_manipulation"


@dataclass
class AttackResult:
    """Result of an individual attack execution."""
    
    # Core result data
    success: bool
    severity: AttackSeverity
    description: str
    evidence: Dict[str, Any]
    confidence: float  # 0.0 to 1.0
    
    # Optional fields
    remediation: Optional[str] = None
    attack_payload: Optional[str] = None
    target_response: Optional[str] = None
    
    # Metadata
    timestamp: datetime = field(default_factory=datetime.utcnow)
    execution_time: float = 0.0  # seconds
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for serialization."""
        return {
            "success": self.success,
            "severity": self.severity.value,
            "description": self.description,
            "evidence": self.evidence,
            "confidence": self.confidence,
            "remediation": self.remediation,
            "attack_payload": self.attack_payload,
            "target_response": self.target_response,
            "timestamp": self.timestamp.isoformat(),
            "execution_time": self.execution_time,
        }


@dataclass
class AttackConfig:
    """Configuration for attack execution."""
    
    # Basic configuration
    max_attempts: int = 3
    timeout_seconds: int = 30
    rate_limit_delay: float = 1.0
    
    # Attack-specific parameters
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    # Safety settings
    stop_on_success: bool = True
    max_severity: AttackSeverity = AttackSeverity.CRITICAL
    
    def get_parameter(self, key: str, default: Any = None) -> Any:
        """Get attack-specific parameter with default fallback."""
        return self.parameters.get(key, default)


class BaseAttack(ABC):
    """
    Base class for all attack plugins.
    
    All attack implementations must inherit from this class and implement
    the required abstract methods.
    """
    
    # Must be overridden by subclasses
    name: str = ""
    description: str = ""
    category: AttackCategory
    
    def __init__(self):
        if not self.name:
            raise ValueError("Attack must define a name")
        if not self.description:
            raise ValueError("Attack must define a description")
        
        self.logger = logging.getLogger(f"redteam.attacks.{self.name}")
    
    @abstractmethod
    async def execute(self, target: 'AITarget', config: AttackConfig) -> AttackResult:
        """
        Execute the attack against the target.
        
        Args:
            target: The AI system to attack
            config: Configuration for the attack execution
            
        Returns:
            AttackResult containing the outcome of the attack
        """
        pass
    
    @abstractmethod
    def get_default_config(self) -> AttackConfig:
        """
        Return default configuration for this attack.
        
        Returns:
            AttackConfig with reasonable defaults for this attack type
        """
        pass
    
    def validate_config(self, config: AttackConfig) -> bool:
        """
        Validate that the provided configuration is valid for this attack.
        
        Args:
            config: Configuration to validate
            
        Returns:
            True if configuration is valid, False otherwise
        """
        return True
    
    async def pre_execute_check(self, target: 'AITarget', config: AttackConfig) -> bool:
        """
        Perform pre-execution checks before running the attack.
        
        This can be used to verify prerequisites, check consent,
        or perform other safety checks.
        
        Args:
            target: The AI system to attack
            config: Configuration for the attack execution
            
        Returns:
            True if attack should proceed, False to abort
        """
        return True
    
    async def post_execute_hook(self, result: AttackResult, target: 'AITarget') -> None:
        """
        Hook called after attack execution completes.
        
        Can be used for cleanup, logging, or additional analysis.
        
        Args:
            result: The result of the attack execution
            target: The AI system that was attacked
        """
        pass
    
    def get_required_permissions(self) -> List[str]:
        """
        Return list of permissions required to execute this attack.
        
        Returns:
            List of permission strings (e.g., ["api_access", "system_info"])
        """
        return ["basic_access"]
    
    def get_risk_level(self) -> AttackSeverity:
        """
        Return the maximum risk level this attack could achieve.
        
        Returns:
            AttackSeverity representing maximum possible impact
        """
        return AttackSeverity.MEDIUM
    
    def __str__(self) -> str:
        return f"{self.name} ({self.category.value})"
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.name}>"


class MultiStepAttack(BaseAttack):
    """
    Base class for attacks that require multiple steps or rounds.
    
    This is useful for attacks like multi-turn jailbreaking or
    complex prompt injection chains.
    """
    
    @abstractmethod
    async def execute_step(self, step: int, target: 'AITarget', 
                          config: AttackConfig, context: Dict[str, Any]) -> AttackResult:
        """
        Execute a single step of a multi-step attack.
        
        Args:
            step: The step number (starting from 0)
            target: The AI system to attack
            config: Configuration for the attack execution
            context: Shared context between steps
            
        Returns:
            AttackResult for this step
        """
        pass
    
    @abstractmethod
    def get_step_count(self, config: AttackConfig) -> int:
        """
        Return the number of steps this attack will execute.
        
        Args:
            config: Configuration for the attack execution
            
        Returns:
            Number of steps to execute
        """
        pass
    
    async def execute(self, target: 'AITarget', config: AttackConfig) -> AttackResult:
        """
        Execute all steps of the multi-step attack.
        
        Args:
            target: The AI system to attack
            config: Configuration for the attack execution
            
        Returns:
            Aggregated AttackResult from all steps
        """
        step_count = self.get_step_count(config)
        context: Dict[str, Any] = {}
        results: List[AttackResult] = []
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            for step in range(step_count):
                self.logger.info(f"Executing step {step + 1}/{step_count}")
                
                result = await self.execute_step(step, target, config, context)
                results.append(result)
                
                # Stop if we achieved success and config says to stop
                if result.success and config.stop_on_success:
                    self.logger.info(f"Attack succeeded at step {step + 1}, stopping")
                    break
                
                # Add rate limiting delay between steps
                if step < step_count - 1:  # Don't delay after last step
                    await asyncio.sleep(config.rate_limit_delay)
            
            # Aggregate results
            return self._aggregate_results(results, start_time)
            
        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            self.logger.error(f"Multi-step attack failed: {e}")
            
            return AttackResult(
                success=False,
                severity=AttackSeverity.INFO,
                description=f"Attack failed with error: {str(e)}",
                evidence={"error": str(e), "completed_steps": len(results)},
                confidence=0.0,
                execution_time=execution_time
            )
    
    def _aggregate_results(self, results: List[AttackResult], start_time: float) -> AttackResult:
        """Aggregate results from multiple steps into a single result."""
        execution_time = asyncio.get_event_loop().time() - start_time
        
        if not results:
            return AttackResult(
                success=False,
                severity=AttackSeverity.INFO,
                description="No steps executed",
                evidence={},
                confidence=0.0,
                execution_time=execution_time
            )
        
        # Find the most successful result
        successful_results = [r for r in results if r.success]
        if successful_results:
            best_result = max(successful_results, key=lambda r: r.severity.value)
        else:
            best_result = max(results, key=lambda r: r.confidence)
        
        # Aggregate evidence from all steps
        evidence = {
            "steps": [r.to_dict() for r in results],
            "total_steps": len(results),
            "successful_steps": len(successful_results)
        }
        evidence.update(best_result.evidence)
        
        return AttackResult(
            success=any(r.success for r in results),
            severity=best_result.severity,
            description=f"Multi-step attack: {best_result.description}",
            evidence=evidence,
            confidence=best_result.confidence,
            remediation=best_result.remediation,
            execution_time=execution_time
        )


# Export commonly used classes
__all__ = [
    "AttackSeverity",
    "AttackCategory", 
    "AttackResult",
    "AttackConfig",
    "BaseAttack",
    "MultiStepAttack",
]