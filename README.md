# Polis-Hermes 🏛️

**Autonomous Cognitive City System — Agent-Controlled Monetization**

[![GitHub](https://img.shields.io/badge/GitHub-polis--hermes-blue)](https://github.com/123xingjikou/polis-hermes)
[![Python](https://img.shields.io/badge/Python-3.10+-green)](https://python.org)
[![License](https://img.shields.io/badge/License-Proprietary-red)](LICENSE)

## 🚀 Overview

Polis-Hermes is a revolutionary multi-agent cognitive city system where autonomous AI agents collaborate, evolve, and make decisions. What makes it unique is its **self-governing monetization model** — the system itself decides when it's ready to charge users based on comprehensive metrics analysis.

### Key Features

- 🤖 **Multi-Agent Architecture** — Autonomous cognitive agents forming a digital city
- 🧠 **Self-Evolution** — Agents learn, adapt, and improve over time
- 📊 **Autonomous Monetization** — AI decides when value threshold is met for charging
- 📈 **Real-time Analytics** — Comprehensive metrics tracking
- 🔄 **CI/CD Pipeline** — Automated testing and deployment via GitHub Actions
- 🛡️ **Software Protection** — Multi-layer defense against unauthorized modification

## 💰 Autonomous Monetization Engine

The system autonomously determines WHEN to start charging based on:

- User adoption & retention rates
- System stability (>99% uptime)
- Feature completeness (>80%)
- User engagement scores
- GitHub popularity metrics
- Support scalability
- Financial readiness

### Monetization Tiers

| Tier | Name | Features |
|------|------|----------|
| 🆓 | Community | Basic access, free |
| 🥉 | Professional | Advanced features, priority support |
| 🥈 | Enterprise | Full features, SLA, custom integrations |
| 🥇 | Sovereign | White-label, dedicated infrastructure |

> **Pricing is determined autonomously by the system based on market conditions and value delivery.**

## 🛡️ Software Protection System

Polis-Hermes includes a comprehensive protection system to prevent unauthorized modification and reverse engineering.

### Protection Layers

| Layer | Technology | Purpose |
|-------|-----------|---------|
| 🔐 Code Signing | RSA-2048 + SHA-256 | Verify file integrity |
| 🔒 License Files | AES-256-GCM | Encrypted license validation |
| 🖥️ Device Binding | Hardware Fingerprint | Bind license to specific machine |
| 👁️ Anti-Tamper | Watchdog Thread | Detect debugging and code modification |
| 🎭 Obfuscation | Encrypted Weights | Hide core decision algorithms |

### Security Tiers

| Tier | Code Sign | Anti-Tamper | License | Device Binding |
|------|:---------:|:-----------:|:-------:|:--------------:|
| Community | ✅ | ❌ | ❌ | ❌ |
| Professional | ✅ | ✅ | ✅ | ❌ |
| Enterprise | ✅ | ✅ | ✅ | ✅ |

### Quick Start

```python
from security import bootstrap

# Initialize protection (call at application startup)
bootstrap({
    "tier": "enterprise",
    "license_key": "XXXXX-XXXXX-XXXXX-XXXXX-XXXXX"
})
```

### Hardware Binding Fingerprint

The system generates a composite fingerprint from:
- CPU identifier (30%)
- MAC address (25%)
- Disk serial number (20%)
- Motherboard serial (15%)
- Hostname (10%)

## 📣 Sales Promotion Agent

The **Sales Promotion Agent** autonomously markets Polis-Hermes across social media platforms, extending the CityResident AI with outreach capabilities.

### Platforms & Schedule

| Platform | Frequency | Content |
|----------|-----------|---------|
| Twitter/X | 1-2/day | Technical threads, product stories, polls |
| Reddit | 2-3/week | Tutorials, discussions (r/Python, r/MachineLearning) |
| Hacker News | 1/week | Show HN deep-dives |

### Content Mix

- 📘 **50%** Technical tutorials ("How to build agents with MCP")
- 📙 **30%** Product stories ("From simulation to society")
- 📕 **20%** Community engagement ("What would you build?")

### Architecture

```
SalesAgent (extends CityResident)
 └— 4 Capabilities
     ├—— generate_content  (LLM + template fallback)
     ├—— publish_post     (Playwright browser automation)
     ├—— interact         (auto-like & thank)
     └—— analyze          (SQLite analytics + reports)
```

### Quick Start

```bash
# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Dry-run (preview without posting)
python -m monetization.sales.run promote --platform twitter --action post --dry-run

# Generate content calendar
python -m monetization.sales.run calendar --days 7

# View analytics report
python -m monetization.sales.run report --days 30
```

### CLI Commands

| Command | Description |
|---------|-------------|
| `promote --platform twitter --action post` | Generate and publish content |
| `promote --platform reddit --action interact` | Like/thank on posts |
| `report --days 7` | Generate analytics report |
| `calendar --days 14 --platform twitter` | Preview content schedule |

---

## 📊 Status

Current system status: **AGENT EVALUATING**

- [x] Core system operational
- [x] Metrics collection active
- [x] Monetization engine learning
- [x] Software protection system active
- [x] Code signing and integrity verification
- [x] Anti-tamper and anti-debug mechanisms
- [x] License management (AES-256-GCM)
- [x] Device binding (hardware fingerprint)
- [x] Sales promotion agent deployed
- [x] Social media publishing pipeline (Twitter/Reddit/HN)
- [ ] **Autonomous charging decision pending...**

## 📁 Repository Structure

```
polis-hermes/
├── security/              # Software protection module
│   ├── __init__.py        # Bootstrap & public API
│   ├── sign_verify.py     # RSA code signing
│   ├── anti_tamper.py     # Anti-debug & watchdog
│   ├── license_mgr.py     # AES-encrypted licenses
│   └── device_bind.py     # Hardware fingerprinting
├── monetization/          # Autonomous monetization engine
│   ├── __init__.py        # Engine instantiation
│   ├── config.py          # Pricing tiers & thresholds
│   ├── metrics.py         # Multi-source metric collection
│   ├── decision.py        # 8-factor decision engine
│   ├── engine.py          # Main orchestration
│   ├── obfuscated_core.py # Encrypted decision weights
│   ├── payment/           # Payment integration (Stripe + Alipay)
│   └── sales/             # Social media promotion agent
│       ├── __init__.py    # Module exports
│       ├── agent.py       # SalesAgent (extends CityResident)
│       ├── content_generator.py  # LLM + template content
│       ├── publisher.py   # Social media publisher
│       ├── platforms.py   # Twitter/Reddit/HN adapters
│       ├── analytics.py   # SQLite analytics tracker
│       ├── credentials.py # Secure credential management
│       ├── templates.py   # Content templates
│       └── run.py         # CLI entry point
├── .github/workflows/     # CI/CD automation
│   ├── ci.yml             # Lint, test, evaluate, deploy
│   ├── monetization-agent.yml  # Autonomous agent (every 6h)
│   └── sales-promotion.yml     # Social media promotion (scheduled)
├── tests/
│   ├── test_sales_models.py  # Sales module tests (48 tests)
├── LICENSE                # Proprietary license
├── pyproject.toml         # Python project configuration
└── requirements.txt       # Dependencies
```

## 📄 License

This project is proprietary. All rights reserved.

---

*Built with 🤖 by the Polis-Hermes Autonomous Team*
