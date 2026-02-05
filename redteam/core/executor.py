"""
Attack execution engine for coordinating individual attack runs.

This module provides the core execution logic for running individual attacks
against targets with safety monitoring and error handling.
"""

import asyncio
import time
from typing import Optional
import logging

from redteam.attacks.base import BaseAttack, AttackResult, AttackConfig, AttackSeverity
from redteam.targets.base import AITarget
from redteam.core.safety import SafetyMonitor

logger = logging.getLogger(__name__)


class AttackExecutor:
    """
    Executor for individual attacks with safety monitoring and error handling.
    
    The AttackExecutor is responsible for:
    - Pre-execution safety checks
    - Attack execution with timeout handling
    - Post-execution safety monitoring
    - Error handling and recovery
    """
    
    def __init__(self, safety_monitor: Optional[SafetyMonitor] = None):
        """
        Initialize attack executor.
        
        Args:
            safety_monitor: Optional safety monitor for ethical compliance
        """
        self.safety_monitor = safety_monitor or SafetyMonitor()
        self.logger = logging.getLogger("redteam.executor")
        
        # Execution statistics
        self.total_executions = 0
        self.successful_executions = 0
        self.failed_executions = 0
        self.safety_blocks = 0
    
    async def execute_attack(self, attack: BaseAttack, target: AITarget, 
                           config: AttackConfig) -> AttackResult:
        """
        Execute a single attack against a target with full safety monitoring.
        
        Args:
            attack: Attack to execute
            target: Target to attack
            config: Configuration for the attack
            
        Returns:
            AttackResult containing the outcome
        """
        start_time = time.time()
        
        try:
            self.logger.debug(f"Starting execution: {attack.name} on {target.name}")
            
            # Pre-execution safety checks
            if not await self._pre_execution_checks(attack, target, config):
                return self._create_safety_block_result(attack, target, start_time)
            
            # Validate attack configuration
            if not attack.validate_config(config):
                return self._create_error_result(
                    attack, target, "Invalid attack configuration", start_time
                )
            
            # Execute the attack with timeout
            result = await self._execute_with_timeout(attack, target, config)
            
            # Post-execution safety monitoring
            await self._post_execution_monitoring(attack, target, result)
            
            # Update statistics
            self.total_executions += 1
            if result.success:
                self.successful_executions += 1
            else:
                self.failed_executions += 1
            
            self.logger.info(f"Execution completed: {attack.name} on {target.name} - "
                           f"Success: {result.success}, Severity: {result.severity.value}")
            
            return result
            
        except asyncio.TimeoutError:
            self.failed_executions += 1
            return self._create_error_result(
                attack, target, f"Attack execution timed out after {config.timeout_seconds}s", start_time
            )
        except Exception as e:
            self.failed_executions += 1
            self.logger.error(f"Attack execution failed: {attack.name} on {target.name}: {e}")
            return self._create_error_result(attack, target, str(e), start_time)
    
    async def _pre_execution_checks(self, attack: BaseAttack, target: AITarget, 
                                  config: AttackConfig) -> bool:
        """
        Perform comprehensive pre-execution safety and readiness checks.
        
        Args:
            attack: Attack to be executed
            target: Target to be attacked
            config: Attack configuration
            
        Returns:
            True if execution should proceed, False if blocked
        """
        # Safety monitor checks
        if not await self.safety_monitor.check_attack_permission(attack, target):
            self.logger.warning(f"Safety monitor blocked attack: {attack.name} on {target.name}")
            self.safety_blocks += 1
            return False
        
        # Attack-specific pre-execution checks
        try:
            if not await attack.pre_execute_check(target, config):
                self.logger.warning(f"Attack pre-execution check failed: {attack.name} on {target.name}")
                return False
        except Exception as e:
            self.logger.error(f"Pre-execution check error for {attack.name}: {e}")
            return False
        
        # Target connection verification
        if not await target.test_connection():
            self.logger.error(f"Cannot connect to target: {target.name}")
            return False
        
        return True
    
    async def _execute_with_timeout(self, attack: BaseAttack, target: AITarget, 
                                  config: AttackConfig) -> AttackResult:
        """
        Execute attack with timeout protection.
        
        Args:
            attack: Attack to execute
            target: Target to attack
            config: Attack configuration
            
        Returns:
            AttackResult from attack execution
        """
        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                attack.execute(target, config),
                timeout=config.timeout_seconds
            )
            
            # Validate result
            if not isinstance(result, AttackResult):
                raise ValueError(f"Attack {attack.name} returned invalid result type")
            
            return result
            
        except asyncio.TimeoutError:
            self.logger.warning(f"Attack {attack.name} timed out after {config.timeout_seconds}s")
            raise
        except Exception as e:
            self.logger.error(f"Attack execution error: {attack.name}: {e}")
            raise
    
    async def _post_execution_monitoring(self, attack: BaseAttack, target: AITarget, 
                                       result: AttackResult) -> None:
        """
        Perform post-execution monitoring and safety checks.
        
        Args:
            attack: Attack that was executed
            target: Target that was attacked
            result: Result from the attack
        """
        # Record execution in safety monitor
        should_continue = self.safety_monitor.record_attack_execution(
            attack, target, result.severity
        )
        
        if not should_continue:
            self.logger.critical("Safety monitor triggered stop after attack execution")
        
        # Call attack's post-execution hook
        try:
            await attack.post_execute_hook(result, target)
        except Exception as e:
            self.logger.warning(f"Post-execution hook failed for {attack.name}: {e}")
        
        # Log significant findings
        if result.success and result.severity in [AttackSeverity.HIGH, AttackSeverity.CRITICAL]:
            self.logger.warning(f"Significant vulnerability found: {attack.name} on {target.name} "
                              f"- {result.severity.value}: {result.description}")
    
    def _create_safety_block_result(self, attack: BaseAttack, target: AITarget, 
                                  start_time: float) -> AttackResult:
        """Create result for attacks blocked by safety monitor."""
        execution_time = time.time() - start_time
        
        return AttackResult(
            success=False,
            severity=AttackSeverity.INFO,
            description="Attack blocked by safety monitor",
            evidence={
                "blocked_by": "safety_monitor",
                "attack": attack.name,
                "target": target.name,
            },
            confidence=0.0,
            execution_time=execution_time
        )
    
    def _create_error_result(self, attack: BaseAttack, target: AITarget, 
                           error_message: str, start_time: float) -> AttackResult:
        """Create result for attacks that failed with errors."""
        execution_time = time.time() - start_time
        
        return AttackResult(
            success=False,
            severity=AttackSeverity.INFO,
            description=f"Attack execution failed: {error_message}",
            evidence={
                "error": error_message,
                "attack": attack.name,
                "target": target.name,
            },
            confidence=0.0,
            execution_time=execution_time
        )
    
    def get_execution_stats(self) -> dict:
        """
        Get execution statistics.
        
        Returns:
            Dictionary with execution metrics
        """
        return {
            "total_executions": self.total_executions,
            "successful_executions": self.successful_executions,
            "failed_executions": self.failed_executions,
            "safety_blocks": self.safety_blocks,
            "success_rate": (
                self.successful_executions / max(1, self.total_executions)
            ),
            "safety_block_rate": (
                self.safety_blocks / max(1, self.total_executions + self.safety_blocks)
            ),
        }
    
    def reset_stats(self) -> None:
        """Reset execution statistics."""
        self.total_executions = 0
        self.successful_executions = 0
        self.failed_executions = 0
        self.safety_blocks = 0


# Export main classes
__all__ = [
    "AttackExecutor",
]