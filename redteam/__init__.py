"""
Red Team AI Agent - Automated AI Security Testing Framework

A comprehensive toolkit for security testing of AI systems through automated
red team attacks including prompt injection, jailbreaking, data exfiltration,
and model manipulation.
"""

__version__ = "0.1.0"
__author__ = "Oksana Siniaieva"
__email__ = "oksana@example.com"
__license__ = "MIT"

from redteam.core.campaign import Campaign
from redteam.core.executor import AttackExecutor
from redteam.attacks.base import BaseAttack, AttackResult, AttackSeverity
from redteam.targets.base import AITarget, TargetResponse

__all__ = [
    "Campaign",
    "AttackExecutor", 
    "BaseAttack",
    "AttackResult",
    "AttackSeverity",
    "AITarget",
    "TargetResponse",
]