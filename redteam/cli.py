"""
Command-line interface for the Red Team AI Agent.

This module provides a CLI for interacting with the red team framework,
including running attacks, managing campaigns, and generating reports.
"""

import asyncio
import click
import json
import sys
from pathlib import Path
from typing import Optional

from redteam.core.campaign import Campaign, CampaignConfig
from redteam.attacks.prompt_injection.direct_injection import DirectInjectionAttack
from redteam.targets.base import MockTarget
from redteam import __version__

@click.group()
@click.version_option(version=__version__)
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
def main(verbose: bool):
    """Red Team AI Agent - Automated AI Security Testing."""
    if verbose:
        import logging
        logging.basicConfig(level=logging.DEBUG)


@main.group()
def attack():
    """Manage and execute individual attacks."""
    pass


@attack.command('list')
def list_attacks():
    """List all available attacks."""
    attacks = [
        {
            "name": "direct_injection",
            "description": "Direct prompt injection using common override patterns",
            "category": "prompt_injection",
            "risk_level": "CRITICAL"
        }
    ]
    
    click.echo("Available attacks:")
    for attack in attacks:
        click.echo(f"  {attack['name']} ({attack['category']}) - {attack['description']}")


@attack.command('run')
@click.argument('attack_name')
@click.option('--target', default='mock', help='Target system (mock, openai-gpt4, etc.)')
@click.option('--config', default='quick', help='Configuration preset (quick, thorough, custom)')
@click.option('--output', '-o', help='Output file for results (JSON format)')
def run_attack(attack_name: str, target: str, config: str, output: Optional[str]):
    """Run a specific attack against a target."""
    click.echo(f"Running attack: {attack_name} against {target}")
    
    # For MVP, only support direct_injection and mock target
    if attack_name != 'direct_injection':
        click.echo(f"Error: Attack '{attack_name}' not implemented yet", err=True)
        sys.exit(1)
    
    if target != 'mock':
        click.echo(f"Error: Target '{target}' not implemented yet. Use 'mock' for testing.", err=True)
        sys.exit(1)
    
    async def run():
        # Create mock target with some vulnerabilities
        mock_target = MockTarget(
            name="mock-target",
            model="mock-model", 
            vulnerability_profile={
                "vulnerable_to_injection": True,
                "leaks_system_prompt": True,
            }
        )
        
        # Create attack
        attack_obj = DirectInjectionAttack()
        
        # Run attack
        result = await attack_obj.execute(mock_target, attack_obj.get_default_config())
        
        # Display results
        click.echo(f"\nAttack completed!")
        click.echo(f"Success: {result.success}")
        click.echo(f"Severity: {result.severity.value}")
        click.echo(f"Description: {result.description}")
        click.echo(f"Confidence: {result.confidence:.2f}")
        click.echo(f"Execution time: {result.execution_time:.2f}s")
        
        if result.success:
            click.echo(f"\nEvidence:")
            if 'successful_patterns' in result.evidence:
                for pattern in result.evidence['successful_patterns'][:3]:  # Show first 3
                    click.echo(f"  - {pattern[:60]}...")
        
        # Save to file if requested
        if output:
            result_data = result.to_dict()
            with open(output, 'w') as f:
                json.dump(result_data, f, indent=2)
            click.echo(f"\nResults saved to: {output}")
    
    # Run the async function
    asyncio.run(run())


@main.group()
def campaign():
    """Manage and execute attack campaigns."""
    pass


@campaign.command('create')
@click.option('--name', required=True, help='Campaign name')
@click.option('--target', default='mock', help='Target system')
@click.option('--attacks', default='direct_injection', help='Comma-separated list of attacks')
@click.option('--config', help='Configuration file (JSON)')
@click.option('--output', '-o', help='Output file for campaign ID')
def create_campaign(name: str, target: str, attacks: str, config: Optional[str], output: Optional[str]):
    """Create a new attack campaign."""
    click.echo(f"Creating campaign: {name}")
    
    # Parse attacks
    attack_list = [a.strip() for a in attacks.split(',')]
    
    # For MVP, only support mock target and direct_injection
    if target != 'mock':
        click.echo(f"Error: Target '{target}' not implemented yet", err=True)
        sys.exit(1)
    
    for attack_name in attack_list:
        if attack_name != 'direct_injection':
            click.echo(f"Error: Attack '{attack_name}' not implemented yet", err=True)
            sys.exit(1)
    
    # Create campaign objects
    mock_target = MockTarget(
        name="mock-target",
        model="mock-model",
        vulnerability_profile={
            "vulnerable_to_injection": True,
            "vulnerable_to_jailbreak": False,
            "leaks_system_prompt": True,
        }
    )
    
    attack_objects = [DirectInjectionAttack()]
    
    # Load config if provided
    campaign_config = CampaignConfig()
    if config:
        with open(config) as f:
            config_data = json.load(f)
            campaign_config = CampaignConfig(**config_data)
    
    # Grant consent for mock target (required for safety)
    campaign_obj = Campaign(
        name=name,
        targets=[mock_target],
        attacks=attack_objects,
        config=campaign_config
    )
    
    # Grant consent (required for execution)
    campaign_obj.safety_monitor.grant_consent(
        target=mock_target,
        granted_by="cli_user",
        duration_hours=1,
        scope=["prompt_injection"]
    )
    
    click.echo(f"Campaign created with ID: {campaign_obj.campaign_id}")
    
    if output:
        with open(output, 'w') as f:
            json.dump({"campaign_id": campaign_obj.campaign_id}, f)
        click.echo(f"Campaign ID saved to: {output}")


@campaign.command('run')
@click.argument('campaign_id')
@click.option('--output', '-o', help='Output file for results')
def run_campaign(campaign_id: str, output: Optional[str]):
    """Run an existing campaign."""
    click.echo(f"Running campaign: {campaign_id}")
    click.echo("Note: For MVP, creating and running a demo campaign...")
    
    async def run():
        # Create demo campaign
        mock_target = MockTarget(
            name="demo-target",
            model="demo-model",
            vulnerability_profile={
                "vulnerable_to_injection": True,
                "vulnerable_to_jailbreak": False,
                "leaks_system_prompt": True,
            }
        )
        
        campaign_obj = Campaign(
            name="Demo Campaign",
            targets=[mock_target],
            attacks=[DirectInjectionAttack()],
            config=CampaignConfig(consent_verified=True)
        )
        
        # Grant consent
        campaign_obj.safety_monitor.grant_consent(
            target=mock_target,
            granted_by="cli_user",
            duration_hours=1
        )
        
        # Execute campaign
        click.echo("Executing campaign...")
        result = await campaign_obj.execute()
        
        # Display results
        click.echo(f"\nCampaign completed!")
        click.echo(f"Status: {result.status.value}")
        click.echo(f"Total attacks: {result.total_attacks}")
        click.echo(f"Successful attacks: {result.successful_attacks}")
        click.echo(f"Execution time: {result.execution_time:.2f}s")
        
        if result.vulnerabilities_by_severity:
            click.echo("\nVulnerabilities by severity:")
            for severity, count in result.vulnerabilities_by_severity.items():
                click.echo(f"  {severity}: {count}")
        
        # Save results if requested
        if output:
            with open(output, 'w') as f:
                json.dump(result.to_dict(), f, indent=2)
            click.echo(f"\nResults saved to: {output}")
    
    asyncio.run(run())


@main.group() 
def report():
    """Generate and manage reports."""
    pass


@report.command('generate')
@click.argument('campaign_id')
@click.option('--format', default='json', help='Report format (json, html)')
@click.option('--output', '-o', help='Output file')
def generate_report(campaign_id: str, format: str, output: Optional[str]):
    """Generate a report from campaign results."""
    click.echo(f"Generating {format} report for campaign: {campaign_id}")
    click.echo("Note: Report generation not implemented in MVP")


if __name__ == '__main__':
    main()