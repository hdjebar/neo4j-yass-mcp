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
- [examples/query_analysis_examples.py](examples/query_analysis_examples.py) - Query analysis examples
- [examples/README_QUERY_ANALYSIS.md](examples/README_QUERY_ANALYSIS.md) - Query analysis guide

### 🔮 Future Features
- [docs/FutureFeatures/README.md](docs/FutureFeatures/README.md) - Planned features overview
- [docs/FutureFeatures/FEATURE_SUMMARY.md](docs/FutureFeatures/FEATURE_SUMMARY.md) - Feature summary
- [docs/FutureFeatures/01-query-plan-analysis.md](docs/FutureFeatures/01-query-plan-analysis.md)
- [docs/FutureFeatures/15-query-complexity-limits.md](docs/FutureFeatures/15-query-complexity-limits.md)
- [docs/FutureFeatures/16-llm-log-analysis.md](docs/FutureFeatures/16-llm-log-analysis.md)

### 📊 Query Analysis Tool (NEW - Highest ROI Feature)
- [docs/inprogress/QUERY_PLAN_ANALYSIS_IMPLEMENTATION_PLAN.md](docs/inprogress/QUERY_PLAN_ANALYSIS_IMPLEMENTATION_PLAN.md) - Implementation plan
- [docs/inprogress/QUERY_ANALYSIS_USER_GUIDE.md](docs/inprogress/QUERY_ANALYSIS_USER_GUIDE.md) - Comprehensive user guide
- [docs/inprogress/QUERY_ANALYSIS_QUICK_REFERENCE.md](docs/inprogress/QUERY_ANALYSIS_QUICK_REFERENCE.md) - Quick reference card
- [examples/query_analysis_examples.py](examples/query_analysis_examples.py) - Practical examples

### 📦 AI Analysis & Reviews (ARAI)
- [docs/repo-arai/README.md](docs/repo-arai/README.md) - Index of AI-assisted analysis
- [docs/repo-arai/FINAL_SUMMARY.md](docs/repo-arai/FINAL_SUMMARY.md) - Query plan analysis refactoring (v1.4.0)
- [docs/repo-arai/SOFTWARE_ARCHITECTURE_DOCUMENT.md](docs/repo-arai/SOFTWARE_ARCHITECTURE_DOCUMENT.md) - System architecture
- [docs/repo-arai/archive/](docs/repo-arai/archive/) - Historical audits and phase reports
- [docs/repo-arai/llm-analysis/](docs/repo-arai/llm-analysis/) - AI architecture reviews

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
3. [docs/repo-arai/archive/DOCKER_BEST_PRACTICES_VERIFICATION_2025-11-08.md](docs/repo-arai/archive/DOCKER_BEST_PRACTICES_VERIFICATION_2025-11-08.md)
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
│   ├── repo-arai/                   # AI analysis & reviews
│   │   ├── README.md                # ARAI index
│   │   ├── FINAL_SUMMARY.md         # Current work summary
│   │   ├── archive/                 # Historical audits
│   │   └── llm-analysis/            # AI reviews
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

### 2025-11-15
- ✅ Query plan analysis refactoring complete (v1.4.0)
- ✅ PROFILE mode safety guards implemented
- ✅ Documentation cleanup and reorganization
- ✅ All tests passing (519/519, 46.11% coverage for affected modules)
- ✅ AI analysis directory (repo-arai) reorganized with proper index
- ✅ Outdated planning documents archived

### Key Changes
- **Fixed**: QueryPlanAnalyzer now surfaces real Neo4j execution plans
- **Fixed**: No unnecessary record materialization
- **Fixed**: Sanitizer no longer blocks URLs in string literals
- **Added**: PROFILE mode blocks write queries by default (safe by default)
- **Updated**: All documentation aligned with implementation
- **Organized**: `docs/repo-arai/` with archive/ and llm-analysis/ subdirectories
- **Archived**: Outdated planning docs (ARCHITECTURE_REFACTORING_PLAN, etc.)

## Contributing to Documentation

When adding documentation:

1. **User docs** → Root level (README.md, QUICK_START.md, etc.)
2. **Developer docs** → `docs/development/`
3. **Architecture docs** → `docs/`
4. **Examples** → `examples/`
5. **Historical/outdated** → `docs/archive/`

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

**Last Updated**: 2025-11-15
**Status**: Current and comprehensive - v1.4.0
