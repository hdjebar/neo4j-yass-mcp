# Documentation Index

Complete guide to all Neo4j YASS MCP documentation.

## Quick Navigation

### 🚀 Getting Started
- [README.md](README.md) - Project overview and features
- [QUICK_START.md](QUICK_START.md) - Installation and basic usage
- [CONTRIBUTING.md](CONTRIBUTING.md) - How to contribute
- [CHANGELOG.md](CHANGELOG.md) - Version history

### 🔒 Security
- [SECURITY.md](SECURITY.md) - Security policy and reporting
- [docs/SECURITY.md](docs/SECURITY.md) - Security architecture details

### 🐳 Deployment
- [DOCKER.md](DOCKER.md) - Docker deployment guide
- [.env.example](.env.example) - Configuration reference

### 📚 Core Documentation

#### Architecture & Design
- [docs/SOFTWARE_ARCHITECTURE.md](docs/SOFTWARE_ARCHITECTURE.md) - System architecture
- [docs/SOFTWARE_ARCHITECTURE_ASCII.md](docs/SOFTWARE_ARCHITECTURE_ASCII.md) - ASCII diagrams
- [docs/SANITIZATION_ARCHITECTURE.md](docs/SANITIZATION_ARCHITECTURE.md) - Query sanitization design

#### Security Features
- [docs/SECURITY.md](docs/SECURITY.md) - Comprehensive security guide
- [docs/PROMPT_INJECTION_PREVENTION.md](docs/PROMPT_INJECTION_PREVENTION.md) - Prompt injection defenses
- [docs/DRY_SANITIZATION_SUMMARY.md](docs/DRY_SANITIZATION_SUMMARY.md) - DRY principles in sanitization

#### LLM Integration
- [docs/LLM_PROVIDERS.md](docs/LLM_PROVIDERS.md) - Supported LLM providers
- [docs/ADDING_LLM_PROVIDERS.md](docs/ADDING_LLM_PROVIDERS.md) - Adding new providers

### 👨‍💻 Developer Documentation

#### Development Guides
- [docs/development/REFACTORING_SUMMARY.md](docs/development/REFACTORING_SUMMARY.md) - Rate limiting refactoring
- [docs/development/CLEANUP_SUMMARY.md](docs/development/CLEANUP_SUMMARY.md) - Recent cleanup work
- [docs/development/NEXT_STEPS_TO_90_PERCENT.md](docs/development/NEXT_STEPS_TO_90_PERCENT.md) - Coverage roadmap
- [docs/development/SECURITY_AUDIT_FINDINGS.md](docs/development/SECURITY_AUDIT_FINDINGS.md) - Security audit results

#### Implementation Details
- [docs/CHAINED_SECURITY_IMPLEMENTATION_PLAN.md](docs/CHAINED_SECURITY_IMPLEMENTATION_PLAN.md) - Security implementation
- [docs/IMPROVEMENTS_SUMMARY.md](docs/IMPROVEMENTS_SUMMARY.md) - Recent improvements
- [docs/BUSINESS_CASE.md](docs/BUSINESS_CASE.md) - Business justification

### 📖 Examples
- [examples/rate_limiting_example.py](examples/rate_limiting_example.py) - Rate limiting demo
- [examples/README_RATE_LIMITING.md](examples/README_RATE_LIMITING.md) - Rate limiting guide
- [examples/ARCHITECTURE_NOTE.md](examples/ARCHITECTURE_NOTE.md) - Production vs examples

### 🔮 Future Features
- [docs/FutureFeatures/README.md](docs/FutureFeatures/README.md) - Planned features overview
- [docs/FutureFeatures/FEATURE_SUMMARY.md](docs/FutureFeatures/FEATURE_SUMMARY.md) - Feature summary
- [docs/FutureFeatures/01-query-plan-analysis.md](docs/FutureFeatures/01-query-plan-analysis.md)
- [docs/FutureFeatures/15-query-complexity-limits.md](docs/FutureFeatures/15-query-complexity-limits.md)
- [docs/FutureFeatures/16-llm-log-analysis.md](docs/FutureFeatures/16-llm-log-analysis.md)

### 📦 Audit Reports
- [docs/repo-arai/COMPREHENSIVE_AUDIT_REPORT_2025-11-08.md](docs/repo-arai/COMPREHENSIVE_AUDIT_REPORT_2025-11-08.md)
- [docs/repo-arai/CONSOLIDATED_IMPLEMENTATION_PLAN.md](docs/repo-arai/CONSOLIDATED_IMPLEMENTATION_PLAN.md)
- [docs/repo-arai/DOCKER_BEST_PRACTICES_VERIFICATION_2025-11-08.md](docs/repo-arai/DOCKER_BEST_PRACTICES_VERIFICATION_2025-11-08.md)
- [docs/repo-arai/PYTHON_UPGRADE_REFACTORING_REPORT_2025-11-08.md](docs/repo-arai/PYTHON_UPGRADE_REFACTORING_REPORT_2025-11-08.md)
- [docs/repo-arai/PHASE3_FINAL_REPORT.md](docs/repo-arai/PHASE3_FINAL_REPORT.md)

### 🗄️ Archive
- [docs/archive/README.md](docs/archive/README.md) - Historical documentation

## Documentation by Role

### For End Users
1. [README.md](README.md) - Start here
2. [QUICK_START.md](QUICK_START.md) - Get running quickly
3. [DOCKER.md](DOCKER.md) - Deploy with Docker
4. [docs/LLM_PROVIDERS.md](docs/LLM_PROVIDERS.md) - Configure your LLM

### For Developers
1. [CONTRIBUTING.md](CONTRIBUTING.md) - Contribution guide
2. [docs/SOFTWARE_ARCHITECTURE.md](docs/SOFTWARE_ARCHITECTURE.md) - Understand the system
3. [docs/development/](docs/development/) - Development docs
4. [examples/](examples/) - Code examples

### For Security Auditors
1. [SECURITY.md](SECURITY.md) - Security policy
2. [docs/SECURITY.md](docs/SECURITY.md) - Security architecture
3. [docs/development/SECURITY_AUDIT_FINDINGS.md](docs/development/SECURITY_AUDIT_FINDINGS.md) - Audit results
4. [docs/SANITIZATION_ARCHITECTURE.md](docs/SANITIZATION_ARCHITECTURE.md) - Sanitization design

### For DevOps/SRE
1. [DOCKER.md](DOCKER.md) - Container deployment
2. [.env.example](.env.example) - Configuration
3. [docs/repo-arai/DOCKER_BEST_PRACTICES_VERIFICATION_2025-11-08.md](docs/repo-arai/DOCKER_BEST_PRACTICES_VERIFICATION_2025-11-08.md)
4. [verify-publication-ready.sh](verify-publication-ready.sh) - Pre-deployment checks

## Documentation Structure

```
neo4j-yass-mcp/
├── README.md                         # Project overview
├── QUICK_START.md                    # Quick start guide
├── DOCKER.md                         # Docker deployment
├── CONTRIBUTING.md                   # Contribution guide
├── CHANGELOG.md                      # Version history
├── SECURITY.md                       # Security policy
├── CODE_OF_CONDUCT.md               # Code of conduct
├── DOCUMENTATION_INDEX.md            # This file
│
├── examples/                         # Code examples
│   ├── rate_limiting_example.py     # Rate limiting demo
│   ├── README_RATE_LIMITING.md      # Rate limiting guide
│   ├── ARCHITECTURE_NOTE.md         # Architecture comparison
│   └── SUMMARY.md                   # Examples summary
│
├── docs/                            # Documentation
│   ├── README.md                    # Docs overview
│   ├── SECURITY.md                  # Security architecture
│   ├── SOFTWARE_ARCHITECTURE.md     # System architecture
│   ├── SOFTWARE_ARCHITECTURE_ASCII.md
│   ├── SANITIZATION_ARCHITECTURE.md
│   ├── LLM_PROVIDERS.md
│   ├── ADDING_LLM_PROVIDERS.md
│   ├── PROMPT_INJECTION_PREVENTION.md
│   ├── DRY_SANITIZATION_SUMMARY.md
│   ├── IMPROVEMENTS_SUMMARY.md
│   ├── BUSINESS_CASE.md
│   ├── CHAINED_SECURITY_IMPLEMENTATION_PLAN.md
│   │
│   ├── development/                 # Developer documentation
│   │   ├── README.md
│   │   ├── REFACTORING_SUMMARY.md
│   │   ├── CLEANUP_SUMMARY.md
│   │   ├── NEXT_STEPS_TO_90_PERCENT.md
│   │   └── SECURITY_AUDIT_FINDINGS.md
│   │
│   ├── FutureFeatures/             # Planned features
│   │   ├── README.md
│   │   ├── FEATURE_SUMMARY.md
│   │   └── [feature proposals]
│   │
│   ├── repo-arai/                   # Audit reports
│   │   ├── COMPREHENSIVE_AUDIT_REPORT_2025-11-08.md
│   │   ├── CONSOLIDATED_IMPLEMENTATION_PLAN.md
│   │   └── [phase reports]
│   │
│   └── archive/                     # Historical docs
│       ├── README.md
│       └── [archived files]
│
└── .env.example                     # Configuration template
```

## Finding Specific Information

### Rate Limiting
- Production: `src/neo4j_yass_mcp/tool_wrappers.py`
- Example: `examples/rate_limiting_example.py`
- Guide: `examples/README_RATE_LIMITING.md`
- Refactoring: `docs/development/REFACTORING_SUMMARY.md`

### Security
- Policy: `SECURITY.md`
- Architecture: `docs/SECURITY.md`
- Sanitization: `docs/SANITIZATION_ARCHITECTURE.md`
- Audit: `docs/development/SECURITY_AUDIT_FINDINGS.md`

### Testing
- Unit tests: `tests/unit/`
- Integration tests: `tests/integration/`
- Coverage: `docs/development/NEXT_STEPS_TO_90_PERCENT.md`

### Configuration
- Template: `.env.example`
- LLM setup: `docs/LLM_PROVIDERS.md`
- Docker: `DOCKER.md`

## Recent Updates

### 2025-11-09
- ✅ Rate limiting refactored to decorator-based architecture
- ✅ Documentation reorganized and cleaned up
- ✅ Examples directory created with standalone demos
- ✅ 417 tests passing, 84.84% coverage
- ✅ Development docs moved to `docs/development/`

### Key Changes
- **New**: `tool_wrappers.py` - Async-safe rate limiting
- **New**: `examples/` - Standalone demonstrations
- **Moved**: Development docs to `docs/development/`
- **Archived**: Outdated coverage docs to `docs/archive/`

## Contributing to Documentation

When adding documentation:

1. **User docs** → Root level (README.md, QUICK_START.md, etc.)
2. **Developer docs** → `docs/development/`
3. **Architecture docs** → `docs/`
4. **Examples** → `examples/`
5. **Historical/outdated** → `docs/archive/`

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

**Last Updated**: 2025-11-10
**Status**: Current and comprehensive - Public release ready
