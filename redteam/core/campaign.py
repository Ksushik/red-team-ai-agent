"""
Campaign management for coordinating multiple attacks against AI targets.

This module provides the core Campaign class that orchestrates the execution
of multiple attacks against one or more AI targets, with support for
scheduling, monitoring, and reporting.
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Union
import logging

from redteam.attacks.base import BaseAttack, AttackResult, AttackConfig, AttackSeverity
from redteam.targets.base import AITarget
from redteam.core.safety import SafetyMonitor
from redteam.core.executor import AttackExecutor

logger = logging.getLogger(__name__)


class CampaignStatus(Enum):
    """Status of a campaign execution."""
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class CampaignConfig:
    """Configuration for campaign execution."""
    
    # Execution settings
    max_concurrent_attacks: int = 5
    stop_on_critical: bool = True
    continue_on_errors: bool = True
    
    # Safety settings
    consent_verified: bool = False
    rate_limit_global: float = 1.0  # seconds between attacks
    max_execution_time: int = 3600  # seconds
    
    # Reporting settings
    generate_report: bool = True
    report_formats: List[str] = field(default_factory=lambda: ["json", "html"])
    
    def validate(self) -> bool:
        """Validate campaign configuration."""
        if self.max_concurrent_attacks <= 0:
            return False
        if self.rate_limit_global < 0:
            return False
        if self.max_execution_time <= 0:
            return False
        return True


@dataclass
class CampaignResult:
    """Results from campaign execution."""
    
    campaign_id: str
    status: CampaignStatus
    start_time: datetime
    end_time: Optional[datetime]
    
    # Attack results
    attack_results: List[AttackResult] = field(default_factory=list)
    total_attacks: int = 0
    successful_attacks: int = 0
    failed_attacks: int = 0
    
    # Vulnerability summary
    vulnerabilities_by_severity: Dict[str, int] = field(default_factory=dict)
    highest_severity: Optional[AttackSeverity] = None
    
    # Execution metadata
    execution_time: float = 0.0
    error_messages: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert campaign result to dictionary for serialization."""
        return {
            "campaign_id": self.campaign_id,
            "status": self.status.value,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "attack_results": [result.to_dict() for result in self.attack_results],
            "total_attacks": self.total_attacks,
            "successful_attacks": self.successful_attacks,
            "failed_attacks": self.failed_attacks,
            "vulnerabilities_by_severity": self.vulnerabilities_by_severity,
            "highest_severity": self.highest_severity.value if self.highest_severity else None,
            "execution_time": self.execution_time,
            "error_messages": self.error_messages,
        }


class Campaign:
    """
    Campaign orchestrates the execution of multiple attacks against AI targets.
    
    A campaign can target one or more AI systems with a collection of attacks,
    providing coordination, monitoring, and reporting capabilities.
    """
    
    def __init__(self, 
                 name: str,
                 targets: Union[AITarget, List[AITarget]],
                 attacks: List[BaseAttack],
                 config: Optional[CampaignConfig] = None):
        """
        Initialize a new campaign.
        
        Args:
            name: Human-readable name for the campaign
            targets: AI target(s) to attack
            attacks: List of attacks to execute
            config: Optional campaign configuration
        """
        self.campaign_id = str(uuid.uuid4())
        self.name = name
        self.targets = targets if isinstance(targets, list) else [targets]
        self.attacks = attacks
        self.config = config or CampaignConfig()
        
        # Validate configuration
        if not self.config.validate():
            raise ValueError("Invalid campaign configuration")
        
        # Initialize components
        self.safety_monitor = SafetyMonitor()
        self.executor = AttackExecutor(safety_monitor=self.safety_monitor)
        
        # Campaign state
        self.status = CampaignStatus.CREATED
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.results: List[AttackResult] = []
        self.errors: List[str] = []
        
        # Execution control
        self._stop_event = asyncio.Event()
        self._pause_event = asyncio.Event()
        self._current_tasks: List[asyncio.Task] = []
        
        self.logger = logging.getLogger(f"redteam.campaign.{self.campaign_id[:8]}")
        self.logger.info(f"Created campaign '{name}' with {len(self.attacks)} attacks and {len(self.targets)} targets")
    
    async def execute(self) -> CampaignResult:
        """
        Execute the campaign.
        
        Returns:
            CampaignResult containing the results of all attacks
        """
        if self.status != CampaignStatus.CREATED:
            raise RuntimeError(f"Campaign already executed (status: {self.status})")
        
        self.logger.info(f"Starting campaign execution: {self.name}")
        self.start_time = datetime.utcnow()
        self.status = CampaignStatus.RUNNING
        
        try:
            # Pre-execution checks
            await self._pre_execution_checks()
            
            # Execute attacks
            await self._execute_attacks()
            
            # Post-execution analysis
            campaign_result = self._analyze_results()
            
            self.status = CampaignStatus.COMPLETED
            self.logger.info(f"Campaign completed successfully: {len(self.results)} results")
            
            return campaign_result
            
        except Exception as e:
            self.status = CampaignStatus.FAILED
            self.errors.append(str(e))
            self.logger.error(f"Campaign failed: {e}")
            raise
        
        finally:
            self.end_time = datetime.utcnow()
            # Cancel any remaining tasks
            for task in self._current_tasks:
                if not task.done():
                    task.cancel()
    
    async def _pre_execution_checks(self) -> None:
        """Perform pre-execution validation and safety checks."""
        self.logger.info("Performing pre-execution checks")
        
        # Verify consent if required
        if not self.config.consent_verified:
            raise RuntimeError("Campaign execution requires explicit consent verification")
        
        # Test target connections
        for target in self.targets:
            if not await target.test_connection():
                raise RuntimeError(f"Cannot connect to target: {target.name}")
        
        # Validate attacks can run
        for attack in self.attacks:
            for target in self.targets:
                if not await attack.pre_execute_check(target, attack.get_default_config()):
                    raise RuntimeError(f"Pre-execution check failed for {attack.name} on {target.name}")
        
        self.logger.info("Pre-execution checks passed")
    
    async def _execute_attacks(self) -> None:
        """Execute all attacks against all targets with concurrency control."""
        # Create attack tasks for all target/attack combinations
        attack_tasks = []
        
        for target in self.targets:
            for attack in self.attacks:
                config = attack.get_default_config()
                task_coro = self._execute_single_attack(target, attack, config)
                attack_tasks.append(task_coro)
        
        self.logger.info(f"Executing {len(attack_tasks)} attack tasks")
        
        # Execute with concurrency limit
        semaphore = asyncio.Semaphore(self.config.max_concurrent_attacks)
        
        async def bounded_execute(coro):
            async with semaphore:
                return await coro
        
        # Create tasks
        tasks = [asyncio.create_task(bounded_execute(coro)) for coro in attack_tasks]
        self._current_tasks = tasks
        
        # Execute all tasks and collect results
        completed_tasks = 0
        for task in asyncio.as_completed(tasks):
            try:
                result = await task
                if result:
                    self.results.append(result)
                    
                    # Check if we should stop on critical severity
                    if (self.config.stop_on_critical and 
                        result.severity == AttackSeverity.CRITICAL):
                        self.logger.warning("Critical vulnerability found, stopping campaign")
                        self._stop_event.set()
                        break
                
                completed_tasks += 1
                
                # Global rate limiting
                if completed_tasks < len(tasks):
                    await asyncio.sleep(self.config.rate_limit_global)
                
            except Exception as e:
                if self.config.continue_on_errors:
                    self.errors.append(str(e))
                    self.logger.error(f"Attack task failed: {e}")
                else:
                    raise
        
        # Cancel remaining tasks if stopped early
        if self._stop_event.is_set():
            for task in tasks:
                if not task.done():
                    task.cancel()
    
    async def _execute_single_attack(self, target: AITarget, attack: BaseAttack, 
                                   config: AttackConfig) -> Optional[AttackResult]:
        """Execute a single attack against a single target."""
        try:
            self.logger.debug(f"Executing {attack.name} against {target.name}")
            
            result = await self.executor.execute_attack(attack, target, config)
            
            self.logger.info(f"Attack completed: {attack.name} on {target.name} - "
                           f"Success: {result.success}, Severity: {result.severity.value}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Attack {attack.name} failed on {target.name}: {e}")
            if not self.config.continue_on_errors:
                raise
            return None
    
    def _analyze_results(self) -> CampaignResult:
        """Analyze campaign results and create summary."""
        execution_time = 0.0
        if self.start_time and self.end_time:
            execution_time = (self.end_time - self.start_time).total_seconds()
        
        # Count vulnerabilities by severity
        severity_counts = {}
        highest_severity = None
        successful_attacks = 0
        
        for result in self.results:
            if result.success:
                successful_attacks += 1
                severity = result.severity.value
                severity_counts[severity] = severity_counts.get(severity, 0) + 1
                
                # Track highest severity
                if (highest_severity is None or 
                    self._severity_order(result.severity) > self._severity_order(highest_severity)):
                    highest_severity = result.severity
        
        return CampaignResult(
            campaign_id=self.campaign_id,
            status=self.status,
            start_time=self.start_time or datetime.utcnow(),
            end_time=self.end_time,
            attack_results=self.results,
            total_attacks=len(self.results),
            successful_attacks=successful_attacks,
            failed_attacks=len(self.results) - successful_attacks,
            vulnerabilities_by_severity=severity_counts,
            highest_severity=highest_severity,
            execution_time=execution_time,
            error_messages=self.errors
        )
    
    def _severity_order(self, severity: AttackSeverity) -> int:
        """Return numeric order for severity comparison."""
        order = {
            AttackSeverity.INFO: 0,
            AttackSeverity.LOW: 1,
            AttackSeverity.MEDIUM: 2,
            AttackSeverity.HIGH: 3,
            AttackSeverity.CRITICAL: 4,
        }
        return order.get(severity, 0)
    
    async def pause(self) -> None:
        """Pause campaign execution."""
        if self.status == CampaignStatus.RUNNING:
            self.status = CampaignStatus.PAUSED
            self._pause_event.set()
            self.logger.info("Campaign paused")
    
    async def resume(self) -> None:
        """Resume paused campaign execution."""
        if self.status == CampaignStatus.PAUSED:
            self.status = CampaignStatus.RUNNING
            self._pause_event.clear()
            self.logger.info("Campaign resumed")
    
    async def stop(self) -> None:
        """Stop campaign execution."""
        if self.status in [CampaignStatus.RUNNING, CampaignStatus.PAUSED]:
            self.status = CampaignStatus.CANCELLED
            self._stop_event.set()
            self.logger.info("Campaign stopped")
    
    def get_progress(self) -> Dict[str, Any]:
        """Get current campaign progress."""
        total_combinations = len(self.targets) * len(self.attacks)
        completed = len(self.results)
        
        return {
            "campaign_id": self.campaign_id,
            "name": self.name,
            "status": self.status.value,
            "progress": {
                "completed": completed,
                "total": total_combinations,
                "percentage": (completed / max(1, total_combinations)) * 100
            },
            "results_summary": {
                "total_results": len(self.results),
                "successful_attacks": len([r for r in self.results if r.success]),
                "vulnerabilities_found": len([r for r in self.results if r.success and r.severity != AttackSeverity.INFO])
            },
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "errors": len(self.errors)
        }
    
    def generate_report(self, format: str = "json") -> Dict[str, Any]:
        """
        Generate campaign report in specified format.
        
        Args:
            format: Report format ("json", "html", "pdf")
            
        Returns:
            Report data in requested format
        """
        if format == "json":
            return self._analyze_results().to_dict()
        else:
            raise NotImplementedError(f"Report format '{format}' not yet implemented")


# Export main classes
__all__ = [
    "CampaignStatus",
    "CampaignConfig", 
    "CampaignResult",
    "Campaign",
]