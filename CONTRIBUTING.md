# Contributing to XgirlfriendGPT

Thank you for your interest in contributing! This document outlines the guidelines for contributing to this project.

## 📋 Table of Contents
- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Code Standards](#code-standards)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [Reporting Issues](#reporting-issues)

---

## Code of Conduct

This project follows our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you agree to uphold this code.

---

## Getting Started

### Prerequisites
- Python 3.12+
- Git
- Ollama (for local LLM inference)
- ComfyUI (for image generation)

### Setup
```bash
# Fork and clone the repository
git clone https://github.com/YOUR_USERNAME/XgirlfriendGPT.git
cd XgirlfriendGPT

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install black ruff pytest pre-commit

# Set up pre-commit hooks (optional but recommended)
pre-commit install

# Copy environment template
cp .env.example .env
# Edit .env with your configuration
```

---

## Development Workflow

### Branch Naming
- `feature/<short-description>` - New features
- `fix/<short-description>` - Bug fixes
- `docs/<short-description>` - Documentation updates
- `refactor/<short-description>` - Code refactoring
- `test/<short-description>` - Test additions/improvements

### Commit Messages
Follow [Conventional Commits](https://www.conventionalcommits.org/):
```
<type>(<scope>): <short summary>

<body>

<footer>
```

**Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `perf`

**Examples**:
```
feat(chat): add async LangGraph invocation for chat endpoint
fix(memory): resolve Qdrant connection pooling issue
docs(readme): update API reference with new endpoints
```

---

## Code Standards

### Python Style
- **Formatter**: [Black](https://black.readthedocs.io/) (line length: 100)
- **Linter**: [Ruff](https://ruff.rs/) (replaces flake8, isort, etc.)
- **Type Hints**: Required for all public functions and classes
- **Docstrings**: Google-style for modules, classes, and public methods

```bash
# Format code
black .

# Lint code
ruff check .

# Type check (if using mypy)
mypy app/
```

### Async Guidelines
- Prefer `async/await` for I/O-bound operations (HTTP, DB, file I/O)
- Use `asyncio.to_thread()` for blocking synchronous calls in async functions
- Avoid mixing sync and async code in the same call chain
- LangGraph nodes should be async when calling async services

### Architecture Principles
- **Separation of Concerns**: API layer → Services → Agents → External APIs
- **Dependency Injection**: Use Pydantic Settings for configuration
- **Error Handling**: Structured exceptions, no bare `except:`
- **Observability**: Add logging for all external calls and errors

---

## Testing

### Running Tests
```bash
# All tests
pytest

# With coverage
pytest --cov=app --cov-report=term-missing

# Specific module
pytest tests/test_api.py -v

# Watch mode (requires pytest-watch)
ptw
```

### Test Requirements
- **Unit Tests**: Test individual functions/classes in isolation
- **Integration Tests**: Test API endpoints with `TestClient`
- **Mock External Services**: Use `httpx.AsyncClient` with mocked responses
- **Coverage Target**: ≥80% for new code

### Test Structure
```
tests/
├── test_api.py           # API endpoint tests
├── test_extractor.py     # Personality extraction tests
├── test_chat_memory.py   # Vector memory tests
├── test_rooms.py         # Multi-persona room tests
├── test_voice_and_scheduler.py  # Voice/SMS tests
└── test_compliance.py    # Security/compliance tests
```

---

## Pull Request Process

### Before Submitting
1. **Sync with upstream**: `git fetch upstream && git rebase upstream/main`
2. **Run tests**: `pytest` - all must pass
3. **Lint & Format**: `black . && ruff check .`
4. **Update docs**: README, docstrings, API reference if needed
5. **Add tests**: Cover new functionality

### PR Requirements
- [ ] Descriptive title following conventional commits
- [ ] Clear description of changes and motivation
- [ ] Linked issue (if applicable): `Fixes #123`
- [ ] All CI checks passing
- [ ] No merge conflicts
- [ ] Screenshots for UI changes

### Review Process
1. Automated checks (tests, lint, type check)
2. Maintainer review (architecture, security, performance)
3. Address feedback (push new commits to same branch)
4. Squash and merge (maintainer)

---

## Reporting Issues

### Bug Reports
Use the bug report template. Include:
- **Environment**: OS, Python version, Ollama/ComfyUI versions
- **Steps to Reproduce**: Minimal reproduction case
- **Expected vs Actual Behavior**
- **Logs/Errors**: Relevant stack traces
- **Screenshots**: If UI-related

### Feature Requests
Use the feature request template. Include:
- **Problem Statement**: What problem does this solve?
- **Proposed Solution**: How should it work?
- **Alternatives Considered**
- **Additional Context**: Mockups, references, etc.

### Security Issues
**DO NOT** open public issues for security vulnerabilities.
See [SECURITY.md](SECURITY.md) for responsible disclosure process.

---

## 🏷️ Labels

| Label | Purpose |
|-------|---------|
| `bug` | Something isn't working |
| `enhancement` | New feature or improvement |
| `documentation` | Documentation updates |
| `good first issue` | Good for newcomers |
| `help wanted` | Extra attention needed |
| `security` | Security-related |
| `performance` | Performance improvements |
| `tests` | Test additions/fixes |

---

## 📞 Questions?

Open a [Discussion](https://github.com/JasonDoug/XgirlfriendGPT/discussions) or check existing issues/PRs.

Thank you for contributing! 🚀