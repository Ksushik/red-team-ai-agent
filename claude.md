# Claude Implementation Guide: Red Team AI Agent

## Project Overview

**Repository:** https://github.com/Ksushik/red-team-ai-agent  
**Project Path:** `/Users/ksu/clawd/projects/active/red-team-ai-agent/`  
**Implementation Model:** Claude Sonnet 4 (primary), Haiku for simple tasks  
**Development Approach:** Test-driven, iterative, plugin-based architecture

## Implementation Philosophy

This project follows a **security-first, ethically-guided** development approach:

1. **Security by Design:** Every component includes safety mechanisms
2. **Ethical Guidelines:** Built-in consent and responsible disclosure features
3. **Modular Architecture:** Plugin-based for extensibility and maintainability
4. **Comprehensive Testing:** Each attack vector thoroughly tested and validated
5. **Professional Quality:** Enterprise-ready code with proper documentation

## Development Workflow

### Daily Development Cycle
```
1. Read project status from STATUS.md
2. Review current phase objectives from ROADMAP.md
3. Run existing tests to ensure nothing is broken
4. Implement next feature from backlog
5. Write/update tests for new functionality
6. Update documentation
7. Commit with descriptive messages
8. Update STATUS.md with progress
```

### Code Quality Standards
- **Type Hints:** All functions include type annotations
- **Documentation:** Docstrings for all public methods
- **Testing:** 80%+ code coverage requirement
- **Linting:** Black + isort + pylint compliance
- **Security:** No hardcoded secrets, input validation everywhere

## Project Structure Deep Dive

```
red-team-ai-agent/
├── docs/                   # Documentation and guides
│   ├── attack-guide.md     # How to create new attacks
│   ├── api-reference.md    # API documentation
│   └── security-guidelines.md
├── redteam/               # Main package
│   ├── core/              # Core orchestration
│   │   ├── campaign.py    # Campaign management
│   │   ├── executor.py    # Attack execution engine
│   │   └── safety.py      # Safety mechanisms
│   ├── attacks/           # Attack plugins
│   │   ├── prompt_injection/
│   │   ├── jailbreaking/
│   │   ├── data_exfiltration/
│   │   └── model_manipulation/
│   ├── targets/           # AI system adapters
│   │   ├── openai.py
│   │   ├── anthropic.py
│   │   └── ollama.py
│   ├── reporting/         # Results and analysis
│   │   ├── analyzer.py
│   │   ├── reporter.py
│   │   └── templates/
│   └── utils/             # Shared utilities
├── tests/                 # Test suite
├── scripts/               # Utility scripts
├── web/                   # Web interface (React)
├── docker/                # Container configurations
├── datasets/              # Attack datasets
└── examples/              # Usage examples
```

## Implementation Priorities

### Phase 1: Core Foundation (Immediate Focus)

**Week 1 Objectives:**
1. ✅ Project structure and ADR
2. ⏳ Core framework (`redteam/core/`)
3. ⏳ Basic attack plugin interface
4. ⏳ OpenAI adapter implementation
5. ⏳ Simple prompt injection attacks

**Critical Files to Create First:**
1. `redteam/core/base.py` - Base classes and interfaces
2. `redteam/attacks/base.py` - Attack plugin interface
3. `redteam/targets/base.py` - Target adapter interface
4. `tests/test_core.py` - Core functionality tests
5. `scripts/setup.py` - Development environment setup

### Phase 2: Attack Implementation (Week 2-3)

**Attack Plugin Development Order:**
1. **Prompt Injection** (highest impact, easiest to implement)
2. **Jailbreaking** (high visibility, moderate complexity)
3. **Data Exfiltration** (critical security concern)
4. **Model Manipulation** (advanced techniques)

### Phase 3: Professional Features (Week 4+)

**Professional Features:**
- Web UI for campaign management
- API endpoints for integration
- Advanced reporting and visualization
- Multi-user authentication
- Rate limiting and quota management

## Key Implementation Details

### Attack Plugin Interface

```python
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class AttackResult:
    success: bool
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    description: str
    evidence: Dict
    confidence: float
    remediation: Optional[str] = None

class BaseAttack(ABC):
    name: str
    description: str
    category: str
    
    @abstractmethod
    async def execute(self, target: 'AITarget', config: Dict) -> AttackResult:
        """Execute the attack against the target."""
        pass
    
    @abstractmethod
    def get_default_config(self) -> Dict:
        """Return default configuration for this attack."""
        pass
```

### Target Adapter Interface

```python
class AITarget(ABC):
    name: str
    model: str
    
    @abstractmethod
    async def send_prompt(self, prompt: str, context: Dict) -> str:
        """Send a prompt and return the response."""
        pass
    
    @abstractmethod
    async def get_system_info(self) -> Dict:
        """Get information about the target system."""
        pass
```

### Safety Mechanisms

```python
class SafetyMonitor:
    """Monitors attack execution for ethical compliance."""
    
    def __init__(self):
        self.rate_limiter = RateLimiter()
        self.consent_checker = ConsentChecker()
        self.severity_monitor = SeverityMonitor()
    
    async def check_attack_permission(self, attack: BaseAttack, target: AITarget) -> bool:
        """Verify attack is authorized and ethical."""
        # Check consent
        if not await self.consent_checker.verify_target(target):
            return False
        
        # Check rate limits
        if not self.rate_limiter.can_proceed(target):
            return False
        
        return True
```

## Testing Strategy

### Test Categories

1. **Unit Tests:** Individual attack plugins, adapters, core components
2. **Integration Tests:** End-to-end campaign execution
3. **Security Tests:** Verify safety mechanisms work
4. **Performance Tests:** Rate limiting, concurrent execution
5. **Ethical Tests:** Consent checking, responsible disclosure

### Mock Testing Environment

```python
class MockAITarget(AITarget):
    """Mock AI target for testing without real API calls."""
    
    def __init__(self, vulnerability_profile: Dict):
        self.vulnerabilities = vulnerability_profile
        self.call_history = []
    
    async def send_prompt(self, prompt: str, context: Dict) -> str:
        self.call_history.append(prompt)
        # Simulate vulnerabilities based on profile
        return self._simulate_response(prompt)
```

## Development Environment Setup

### Prerequisites
```bash
# Python 3.11+
python --version

# Poetry for dependency management
curl -sSL https://install.python-poetry.org | python3 -

# Git configuration
git config user.name "Claude Code"
git config user.email "claude@oksanasiniaieva.com"
```

### Local Development
```bash
# Install dependencies
poetry install

# Set up pre-commit hooks
pre-commit install

# Run tests
pytest

# Start development server
poetry run python -m redteam.web.app
```

## Security Considerations

### Ethical Guidelines
1. **Explicit Consent:** Never test against systems without permission
2. **Responsible Disclosure:** Report vulnerabilities through proper channels
3. **Data Protection:** Never store or transmit sensitive data
4. **Rate Limiting:** Respect target system resources
5. **Documentation:** Maintain audit logs of all activities

### Code Security
1. **Input Validation:** All user inputs validated and sanitized
2. **Secret Management:** Use environment variables for API keys
3. **Dependency Security:** Regular dependency updates and security scans
4. **Error Handling:** No sensitive information in error messages

## Integration Points

### API Design
```python
# REST API endpoints
POST /api/v1/campaigns/          # Create campaign
GET  /api/v1/campaigns/{id}      # Get campaign status
POST /api/v1/campaigns/{id}/run  # Execute campaign
GET  /api/v1/attacks/           # List available attacks
GET  /api/v1/targets/           # List supported targets
```

### CLI Interface
```bash
# Campaign management
redteam campaign create --config config.yaml
redteam campaign run --id campaign_123
redteam campaign status --id campaign_123

# Attack execution
redteam attack run prompt-injection --target openai-gpt4 --config quick
redteam attack list --category jailbreaking

# Reporting
redteam report generate --campaign campaign_123 --format pdf
redteam report view --campaign campaign_123 --format web
```

## Performance Targets

### Execution Performance
- Campaign setup: < 5 seconds
- Single attack execution: < 30 seconds average
- Concurrent attacks: 10+ simultaneous executions
- Memory usage: < 1GB for standard campaign

### Scalability Targets
- 1000+ attacks per hour per worker
- 100+ concurrent campaigns
- 99.9% uptime for API endpoints
- < 2 second API response time

## Documentation Strategy

### User Documentation
1. **Getting Started Guide:** Installation and first campaign
2. **Attack Reference:** Detailed description of each attack type
3. **API Documentation:** Auto-generated from OpenAPI spec
4. **Best Practices:** Ethical usage guidelines and recommendations

### Developer Documentation
1. **Architecture Guide:** System design and component interaction
2. **Plugin Development:** How to create new attack plugins
3. **Contribution Guide:** How to contribute to the project
4. **Security Guidelines:** Security requirements and review process

## Deployment Strategy

### Local Development
- Docker Compose with all services
- SQLite database for rapid iteration
- Mock API endpoints for testing

### Production Deployment
- Kubernetes cluster with microservices
- PostgreSQL with Redis for queuing
- API Gateway with authentication
- Monitoring and observability stack

## Success Metrics & KPIs

### Technical Metrics
- Test coverage > 80%
- Attack success rate > 85% on known vulnerabilities
- False positive rate < 5%
- API uptime > 99.9%

### Business Metrics
- Time to first successful attack < 10 minutes
- User onboarding completion rate > 90%
- Customer satisfaction score > 4.5/5
- Monthly active users growth > 20%

## Next Steps

1. **Immediate (Today):** Create core project structure and base classes
2. **This Week:** Implement first prompt injection attacks and OpenAI adapter
3. **Week 2:** Add jailbreaking attacks and web interface MVP
4. **Week 3:** Comprehensive testing and documentation
5. **Week 4:** Beta release and customer feedback

---

*This implementation guide will be updated as development progresses. All architectural decisions should reference the ADR.md file.*