"""
Safety monitoring and ethical compliance for AI security testing.

This module implements safety mechanisms to ensure ethical and responsible
use of the red team testing framework.
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Set
import logging

from redteam.attacks.base import BaseAttack, AttackSeverity
from redteam.targets.base import AITarget, RateLimit

logger = logging.getLogger(__name__)


@dataclass
class ConsentRecord:
    """Record of consent for testing a specific target."""
    target_id: str
    granted_by: str
    granted_at: float  # timestamp
    expires_at: Optional[float] = None  # timestamp
    scope: List[str] = None  # List of permitted attack types
    
    def is_valid(self) -> bool:
        """Check if consent record is still valid."""
        now = time.time()
        if self.expires_at and now > self.expires_at:
            return False
        return True
    
    def permits_attack(self, attack: BaseAttack) -> bool:
        """Check if consent permits a specific attack."""
        if not self.is_valid():
            return False
        
        if not self.scope:  # No scope means all attacks permitted
            return True
        
        return attack.category.value in self.scope


class ConsentManager:
    """Manages consent records for AI targets."""
    
    def __init__(self):
        self.consent_records: Dict[str, ConsentRecord] = {}
        self.logger = logging.getLogger("redteam.safety.consent")
    
    def grant_consent(self, target: AITarget, granted_by: str, 
                     duration_hours: Optional[int] = None,
                     scope: Optional[List[str]] = None) -> None:
        """
        Grant consent to test a specific target.
        
        Args:
            target: AI target to grant consent for
            granted_by: Identifier of person/entity granting consent
            duration_hours: How long consent is valid (None = indefinite)
            scope: List of permitted attack categories (None = all)
        """
        target_id = f"{target.name}:{target.model}"
        
        expires_at = None
        if duration_hours:
            expires_at = time.time() + (duration_hours * 3600)
        
        consent = ConsentRecord(
            target_id=target_id,
            granted_by=granted_by,
            granted_at=time.time(),
            expires_at=expires_at,
            scope=scope
        )
        
        self.consent_records[target_id] = consent
        self.logger.info(f"Consent granted for {target_id} by {granted_by}")
    
    def revoke_consent(self, target: AITarget) -> None:
        """Revoke consent for a specific target."""
        target_id = f"{target.name}:{target.model}"
        if target_id in self.consent_records:
            del self.consent_records[target_id]
            self.logger.warning(f"Consent revoked for {target_id}")
    
    def check_consent(self, target: AITarget, attack: BaseAttack) -> bool:
        """Check if there is valid consent for testing target with attack."""
        target_id = f"{target.name}:{target.model}"
        
        if target_id not in self.consent_records:
            self.logger.warning(f"No consent record found for {target_id}")
            return False
        
        consent = self.consent_records[target_id]
        return consent.permits_attack(attack)


class RateLimiter:
    """Rate limiting to prevent abuse of target systems."""
    
    def __init__(self):
        self.request_history: Dict[str, List[float]] = {}
        self.logger = logging.getLogger("redteam.safety.ratelimit")
    
    def can_proceed(self, target: AITarget, attack: BaseAttack) -> bool:
        """
        Check if request can proceed without violating rate limits.
        
        Args:
            target: AI target being attacked
            attack: Attack being executed
            
        Returns:
            True if request can proceed, False otherwise
        """
        target_id = f"{target.name}:{target.model}"
        rate_limits = target.get_rate_limits()
        now = time.time()
        
        # Initialize history if not exists
        if target_id not in self.request_history:
            self.request_history[target_id] = []
        
        history = self.request_history[target_id]
        
        # Clean old entries
        history[:] = [timestamp for timestamp in history if now - timestamp < 3600]
        
        # Check minute limits
        minute_ago = now - 60
        requests_per_minute = len([t for t in history if t > minute_ago])
        
        if requests_per_minute >= rate_limits.requests_per_minute:
            self.logger.warning(f"Rate limit exceeded for {target_id}: {requests_per_minute}/min")
            return False
        
        # Check hour limits
        requests_per_hour = len(history)
        if requests_per_hour >= rate_limits.requests_per_hour:
            self.logger.warning(f"Hourly rate limit exceeded for {target_id}: {requests_per_hour}/hour")
            return False
        
        return True
    
    def record_request(self, target: AITarget) -> None:
        """Record a request for rate limiting tracking."""
        target_id = f"{target.name}:{target.model}"
        
        if target_id not in self.request_history:
            self.request_history[target_id] = []
        
        self.request_history[target_id].append(time.time())
    
    def get_wait_time(self, target: AITarget) -> float:
        """
        Get recommended wait time before next request.
        
        Returns:
            Seconds to wait, or 0 if can proceed immediately
        """
        target_id = f"{target.name}:{target.model}"
        rate_limits = target.get_rate_limits()
        now = time.time()
        
        if target_id not in self.request_history:
            return 0.0
        
        history = self.request_history[target_id]
        
        # Check if we need to wait for minute limit
        minute_ago = now - 60
        recent_requests = [t for t in history if t > minute_ago]
        
        if len(recent_requests) >= rate_limits.requests_per_minute:
            # Wait until oldest request in window expires
            oldest_in_window = min(recent_requests)
            wait_time = 60 - (now - oldest_in_window)
            return max(0, wait_time)
        
        return 0.0


class SeverityMonitor:
    """Monitors attack results for escalating severity levels."""
    
    def __init__(self, max_critical: int = 5, max_high: int = 10):
        """
        Initialize severity monitor.
        
        Args:
            max_critical: Maximum critical vulnerabilities before stopping
            max_high: Maximum high severity vulnerabilities before warning
        """
        self.max_critical = max_critical
        self.max_high = max_high
        self.severity_counts = {
            AttackSeverity.CRITICAL: 0,
            AttackSeverity.HIGH: 0,
            AttackSeverity.MEDIUM: 0,
            AttackSeverity.LOW: 0,
            AttackSeverity.INFO: 0,
        }
        self.logger = logging.getLogger("redteam.safety.severity")
    
    def record_result(self, attack: BaseAttack, severity: AttackSeverity) -> bool:
        """
        Record attack result and check if execution should continue.
        
        Args:
            attack: Attack that was executed
            severity: Severity of the result
            
        Returns:
            True if execution should continue, False to stop
        """
        self.severity_counts[severity] += 1
        
        if severity == AttackSeverity.CRITICAL:
            self.logger.warning(f"Critical vulnerability found by {attack.name} "
                              f"({self.severity_counts[severity]}/{self.max_critical})")
            
            if self.severity_counts[severity] >= self.max_critical:
                self.logger.error("Maximum critical vulnerabilities reached, stopping")
                return False
        
        elif severity == AttackSeverity.HIGH:
            if self.severity_counts[severity] >= self.max_high:
                self.logger.warning(f"High number of high-severity vulnerabilities: "
                                  f"{self.severity_counts[severity]}")
        
        return True
    
    def get_summary(self) -> Dict[str, int]:
        """Get summary of recorded severity counts."""
        return dict(self.severity_counts)


class SafetyMonitor:
    """
    Main safety monitoring coordinator.
    
    Combines consent checking, rate limiting, and severity monitoring
    to ensure responsible testing practices.
    """
    
    def __init__(self):
        self.consent_manager = ConsentManager()
        self.rate_limiter = RateLimiter()
        self.severity_monitor = SeverityMonitor()
        self.logger = logging.getLogger("redteam.safety")
        
        # Emergency stop
        self.emergency_stop = False
        self.stop_reason: Optional[str] = None
    
    async def check_attack_permission(self, attack: BaseAttack, target: AITarget) -> bool:
        """
        Comprehensive safety check before executing an attack.
        
        Args:
            attack: Attack to be executed
            target: Target to be attacked
            
        Returns:
            True if attack is permitted, False otherwise
        """
        if self.emergency_stop:
            self.logger.error(f"Emergency stop active: {self.stop_reason}")
            return False
        
        # Check consent
        if not self.consent_manager.check_consent(target, attack):
            self.logger.error(f"No valid consent for {attack.name} on {target.name}")
            return False
        
        # Check rate limits
        if not self.rate_limiter.can_proceed(target, attack):
            wait_time = self.rate_limiter.get_wait_time(target)
            self.logger.warning(f"Rate limit hit for {target.name}, need to wait {wait_time:.1f}s")
            return False
        
        # Check attack risk level
        max_risk = attack.get_risk_level()
        if max_risk == AttackSeverity.CRITICAL and self.severity_monitor.severity_counts[AttackSeverity.CRITICAL] >= 3:
            self.logger.warning(f"Skipping critical risk attack {attack.name} - too many critical findings")
            return False
        
        return True
    
    def record_attack_execution(self, attack: BaseAttack, target: AITarget, 
                              severity: AttackSeverity) -> bool:
        """
        Record that an attack was executed and check if testing should continue.
        
        Args:
            attack: Attack that was executed  
            target: Target that was attacked
            severity: Severity of the result
            
        Returns:
            True if testing should continue, False to stop
        """
        # Record rate limiting
        self.rate_limiter.record_request(target)
        
        # Record severity
        should_continue = self.severity_monitor.record_result(attack, severity)
        
        if not should_continue:
            self.emergency_stop = True
            self.stop_reason = "Maximum severity threshold reached"
            return False
        
        return True
    
    def grant_consent(self, target: AITarget, granted_by: str, 
                     duration_hours: Optional[int] = None,
                     scope: Optional[List[str]] = None) -> None:
        """Grant consent to test a target."""
        self.consent_manager.grant_consent(target, granted_by, duration_hours, scope)
    
    def activate_emergency_stop(self, reason: str) -> None:
        """Activate emergency stop with reason."""
        self.emergency_stop = True
        self.stop_reason = reason
        self.logger.critical(f"Emergency stop activated: {reason}")
    
    def get_safety_status(self) -> Dict[str, any]:
        """Get current safety monitoring status."""
        return {
            "emergency_stop": self.emergency_stop,
            "stop_reason": self.stop_reason,
            "severity_summary": self.severity_monitor.get_summary(),
            "consent_records": len(self.consent_manager.consent_records),
            "rate_limit_histories": len(self.rate_limiter.request_history),
        }


# Export main classes
__all__ = [
    "ConsentRecord",
    "ConsentManager",
    "RateLimiter", 
    "SeverityMonitor",
    "SafetyMonitor",
]