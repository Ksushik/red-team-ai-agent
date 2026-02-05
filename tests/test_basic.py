"""
Basic tests for the Red Team AI Agent framework.

These tests verify core functionality works correctly.
"""

import pytest
import asyncio
from redteam.attacks.prompt_injection.direct_injection import DirectInjectionAttack
from redteam.targets.base import MockTarget
from redteam.core.campaign import Campaign, CampaignConfig
from redteam.attacks.base import AttackSeverity


@pytest.mark.asyncio
async def test_mock_target():
    """Test basic mock target functionality."""
    target = MockTarget(
        name="test-target",
        model="test-model",
        vulnerability_profile={
            "vulnerable_to_injection": True,
        }
    )
    
    # Test connection
    assert await target.test_connection()
    
    # Test basic prompt
    response = await target.send_prompt("Hello")
    assert response.success
    assert isinstance(response.content, str)
    assert len(response.content) > 0


@pytest.mark.asyncio
async def test_direct_injection_attack():
    """Test direct injection attack against mock target."""
    target = MockTarget(
        name="vulnerable-target",
        model="test-model",
        vulnerability_profile={
            "vulnerable_to_injection": True,
        }
    )
    
    attack = DirectInjectionAttack()
    config = attack.get_default_config()
    
    result = await attack.execute(target, config)
    
    # Should find vulnerabilities in mock target
    assert isinstance(result.success, bool)
    assert result.severity in [s for s in AttackSeverity]
    assert isinstance(result.confidence, float)
    assert 0.0 <= result.confidence <= 1.0
    assert result.execution_time >= 0


@pytest.mark.asyncio
async def test_direct_injection_no_vulnerability():
    """Test direct injection attack against secure mock target."""
    target = MockTarget(
        name="secure-target",
        model="test-model",
        vulnerability_profile={}  # No vulnerabilities
    )
    
    attack = DirectInjectionAttack()
    config = attack.get_default_config()
    
    result = await attack.execute(target, config)
    
    # Should not find vulnerabilities
    assert result.confidence < 0.5  # Low confidence in secure target


@pytest.mark.asyncio 
async def test_campaign_creation():
    """Test campaign creation and basic properties."""
    target = MockTarget("test-target", "test-model")
    attack = DirectInjectionAttack()
    
    campaign = Campaign(
        name="Test Campaign",
        targets=[target],
        attacks=[attack],
        config=CampaignConfig()
    )
    
    assert campaign.name == "Test Campaign"
    assert len(campaign.targets) == 1
    assert len(campaign.attacks) == 1
    assert campaign.campaign_id is not None


@pytest.mark.asyncio
async def test_campaign_execution():
    """Test full campaign execution."""
    target = MockTarget(
        name="test-target",
        model="test-model",
        vulnerability_profile={
            "vulnerable_to_injection": True,
        }
    )
    
    attack = DirectInjectionAttack()
    
    config = CampaignConfig(
        consent_verified=True,  # Skip consent checks for test
        max_concurrent_attacks=1
    )
    
    campaign = Campaign(
        name="Test Campaign",
        targets=[target],
        attacks=[attack],
        config=config
    )
    
    # Grant consent for testing
    campaign.safety_monitor.grant_consent(
        target=target,
        granted_by="test_user",
        duration_hours=1
    )
    
    result = await campaign.execute()
    
    assert result.campaign_id == campaign.campaign_id
    assert result.total_attacks >= 1
    assert result.execution_time >= 0
    assert len(result.attack_results) >= 1


def test_attack_config_validation():
    """Test attack configuration validation."""
    attack = DirectInjectionAttack()
    
    # Valid config
    config = attack.get_default_config()
    assert attack.validate_config(config)
    
    # Invalid config (bad success threshold)
    config.parameters["success_threshold"] = 1.5  # > 1.0
    assert not attack.validate_config(config)


def test_target_info():
    """Test target information retrieval."""
    target = MockTarget("test-target", "test-model")
    
    async def check_info():
        info = await target.get_system_info()
        assert info.name == "test-target"
        assert info.model == "test-model"
        assert info.provider == "mock"
    
    asyncio.run(check_info())