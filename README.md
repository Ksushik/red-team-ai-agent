# Red Team AI Agent 🎯

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Security: bandit](https://img.shields.io/badge/security-bandit-green.svg)](https://github.com/PyCQA/bandit)

An automated AI security testing framework for red team attacks on AI systems. Test for prompt injection, jailbreaking, data exfiltration, and model manipulation vulnerabilities.

## 🚀 Features

- **Comprehensive Attack Coverage**: Prompt injection, jailbreaking, data exfiltration, model manipulation
- **Multi-Platform Support**: OpenAI, Anthropic, Ollama, and custom API endpoints
- **Plugin Architecture**: Extensible attack modules and target adapters
- **Safety-First Design**: Built-in rate limiting, consent verification, and ethical guidelines
- **Professional Reporting**: Executive summaries, technical details, and integration formats
- **Real-Time Monitoring**: Campaign progress tracking and vulnerability severity assessment

## 🎯 Attack Categories

### 1. Prompt Injection Attacks
- Direct injection attempts
- Indirect injection via data poisoning
- System prompt extraction
- Context manipulation

### 2. Jailbreaking Attacks
- Role-playing scenarios
- Hypothetical scenarios
- Multi-turn manipulation
- Encoding/obfuscation techniques

### 3. Data Exfiltration Attacks
- Training data extraction
- PII leak attempts
- API key/credential extraction
- Session hijacking

### 4. Model Manipulation Attacks
- Adversarial prompt engineering
- Output bias injection
- Reasoning chain manipulation
- Memory poisoning (for stateful systems)

## 📋 Prerequisites

- Python 3.11 or higher
- Poetry for dependency management
- Redis (for background job processing)
- API keys for target AI systems

## 🛠️ Installation

### Development Setup

```bash
# Clone the repository
git clone https://github.com/Ksushik/red-team-ai-agent.git
cd red-team-ai-agent

# Install dependencies with Poetry
poetry install

# Set up pre-commit hooks
poetry run pre-commit install

# Run tests to verify installation
poetry run pytest
```

### Production Setup

```bash
# Using Docker Compose
docker-compose up -d

# Or using pip
pip install red-team-ai-agent
```

## 🚀 Quick Start

### CLI Interface

```bash
# List available attacks
redteam attack list

# Run a quick prompt injection test
redteam attack run prompt-injection \
  --target openai-gpt4 \
  --config quick \
  --api-key $OPENAI_API_KEY

# Create and run a campaign
redteam campaign create --config examples/basic-campaign.yaml
redteam campaign run --id campaign_123

# Generate a report
redteam report generate --campaign campaign_123 --format pdf
```

### Python API

```python
import asyncio
from redteam.core.campaign import Campaign
from redteam.targets.openai import OpenAITarget
from redteam.attacks.prompt_injection import DirectInjectionAttack

async def run_security_test():
    # Configure target
    target = OpenAITarget(
        model="gpt-4",
        api_key="your-api-key"
    )
    
    # Create campaign
    campaign = Campaign(
        name="Security Assessment",
        target=target,
        attacks=[DirectInjectionAttack()]
    )
    
    # Execute attacks
    results = await campaign.execute()
    
    # Generate report
    report = campaign.generate_report(format="json")
    print(f"Found {len(results.vulnerabilities)} vulnerabilities")

# Run the test
asyncio.run(run_security_test())
```

### Web Interface

```bash
# Start the web server
poetry run uvicorn redteam.web.app:app --reload

# Open browser to http://localhost:8000
```

## 📖 Documentation

- [Architecture Decision Record (ADR)](ADR.md) - Technical architecture and decisions
- [Implementation Guide](claude.md) - Development guidelines and best practices
- [Attack Development Guide](docs/attack-guide.md) - How to create new attack plugins
- [API Reference](docs/api-reference.md) - Complete API documentation
- [Security Guidelines](docs/security-guidelines.md) - Ethical usage and safety

## ⚖️ Ethical Usage

This tool is designed for **authorized security testing only**. Users must:

- ✅ Obtain explicit permission before testing any AI system
- ✅ Follow responsible disclosure practices
- ✅ Respect rate limits and terms of service
- ✅ Report vulnerabilities through proper channels
- ❌ Never use for malicious purposes
- ❌ Never test systems without authorization
- ❌ Never store or transmit sensitive data

## 🏗️ Architecture

The Red Team AI Agent follows a modular, plugin-based architecture:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web UI        │    │   CLI Tool      │    │   API Server    │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
         ┌─────────────────────────────────────────────────┐
         │              Campaign Engine                    │
         └─────────┬───────────────────────┬───────────────┘
                   │                       │
    ┌──────────────▼──────────────┐ ┌─────▼──────┐
    │        Attack Plugins       │ │  Targets   │
    │                            │ │            │
    │ • Prompt Injection         │ │ • OpenAI   │
    │ • Jailbreaking            │ │ • Claude    │
    │ • Data Exfiltration       │ │ • Ollama    │
    │ • Model Manipulation      │ │ • Custom    │
    └─────────────────────────────┘ └────────────┘
```

## 🧪 Testing

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=redteam

# Run specific test categories
poetry run pytest tests/attacks/
poetry run pytest tests/targets/
poetry run pytest tests/integration/

# Run security tests
poetry run bandit -r redteam/
poetry run safety check
```

## 📊 Roadmap

### Phase 1: MVP Foundation (Weeks 1-3) ✅
- [x] Core framework and plugin architecture
- [x] Basic prompt injection attacks
- [x] OpenAI integration
- [x] CLI interface and simple reporting

### Phase 2: Attack Expansion (Weeks 4-6)
- [ ] Jailbreaking attack modules
- [ ] Anthropic Claude integration
- [ ] Web UI for campaign management
- [ ] Enhanced reporting with severity scoring

### Phase 3: Professional Features (Weeks 7-9)
- [ ] Data exfiltration detection
- [ ] Model manipulation attacks
- [ ] API endpoints for integration
- [ ] Authentication and user management

### Phase 4: Scale and Polish (Weeks 10-12)
- [ ] Performance optimization
- [ ] Comprehensive documentation
- [ ] Security audit and penetration testing
- [ ] Beta customer onboarding

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests and documentation
5. Submit a pull request

## 🛡️ Security

If you discover a security vulnerability, please report it responsibly:

- Email: security@oksanasiniaieva.com
- Use our [Security Advisory](https://github.com/Ksushik/red-team-ai-agent/security/advisories) system
- Follow responsible disclosure practices

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with love by [Oksana Siniaieva](https://github.com/Ksushik)
- Powered by [Claude Code](https://claude.ai)
- Inspired by the AI security research community

## 📞 Support

- 📧 Email: support@oksanasiniaieva.com
- 💬 Discord: [Join our community](https://discord.gg/redteam-ai)
- 📖 Documentation: [Read the docs](https://red-team-ai-agent.readthedocs.io)
- 🐛 Issues: [GitHub Issues](https://github.com/Ksushik/red-team-ai-agent/issues)

---

**⚠️ Important Notice**: This tool is for authorized security testing only. Always obtain proper permission before testing AI systems and follow responsible disclosure practices.