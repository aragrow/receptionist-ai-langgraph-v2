# Contributing Guide

Thank you for considering contributing to the AI Receptionist System! This guide will help you get started.

---

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Setup](#development-setup)
4. [Making Changes](#making-changes)
5. [Testing](#testing)
6. [Code Style](#code-style)
7. [Commit Guidelines](#commit-guidelines)
8. [Pull Request Process](#pull-request-process)
9. [Issue Guidelines](#issue-guidelines)
10. [Community](#community)

---

## Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inclusive environment for everyone, regardless of:
- Age, body size, disability, ethnicity, gender identity
- Level of experience, education, socio-economic status
- Nationality, personal appearance, race, religion
- Sexual identity and orientation

### Expected Behavior

- Use welcoming and inclusive language
- Be respectful of differing viewpoints
- Accept constructive criticism gracefully
- Focus on what's best for the community
- Show empathy towards others

### Unacceptable Behavior

- Trolling, insulting/derogatory comments
- Public or private harassment
- Publishing others' private information
- Other conduct which could reasonably be considered inappropriate

### Reporting

Report unacceptable behavior to: conduct@yourdomain.com

---

## Getting Started

### Prerequisites

- **Python**: 3.11+
- **Git**: 2.30+
- **Docker**: 20.10+ (optional but recommended)
- **MongoDB**: 7.0+ (or use Docker)

### First-Time Contributors

1. **Star the repository** ⭐
2. **Fork the repository** to your account
3. **Clone your fork**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/ai-receptionist.git
   cd ai-receptionist
   ```
4. **Add upstream remote**:
   ```bash
   git remote add upstream https://github.com/ORIGINAL_OWNER/ai-receptionist.git
   ```

### Find an Issue

Good first issues are labeled:
- `good first issue` - Easy for newcomers
- `help wanted` - Extra attention needed
- `bug` - Something isn't working
- `enhancement` - New feature request
- `documentation` - Documentation improvements

---

## Development Setup

### 1. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

### 2. Install Dependencies

```bash
# Production dependencies
pip install -r requirements.txt

# Development dependencies
pip install -r requirements-dev.txt
```

**requirements-dev.txt**:
```txt
# Testing
pytest==7.4.0
pytest-asyncio==0.21.0
pytest-cov==4.1.0
pytest-mock==3.11.1

# Code quality
black==23.7.0
isort==5.12.0
flake8==6.0.0
pylint==2.17.5
mypy==1.4.1

# Pre-commit hooks
pre-commit==3.3.3

# Documentation
mkdocs==1.5.0
mkdocs-material==9.1.21
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your values
nano .env
```

### 4. Start Database

```bash
# Option A: Docker
docker-compose up -d mongodb

# Option B: Local MongoDB
sudo systemctl start mongod
```

### 5. Run Migrations

```bash
python src/utilities/migrate_routing_collections.py
python src/utilities/seed_l1_prompts.py
python src/utilities/seed_l2_prompts.py
```

### 6. Install Pre-commit Hooks

```bash
pre-commit install
```

**.pre-commit-config.yaml**:
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.7.0
    hooks:
      - id: black
        language_version: python3.11
  
  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
  
  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
        args: [--max-line-length=100]
  
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
```

### 7. Verify Setup

```bash
# Run tests
pytest

# Start application
uvicorn main:app --reload

# Open browser
open http://localhost:8000/docs
```

---

## Making Changes

### 1. Create a Branch

```bash
# Update main
git checkout main
git pull upstream main

# Create feature branch
git checkout -b feature/your-feature-name

# Or for bugfix
git checkout -b fix/issue-number-description
```

**Branch Naming**:
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation only
- `refactor/` - Code refactoring
- `test/` - Adding tests
- `chore/` - Maintenance tasks

### 2. Make Your Changes

**Best Practices**:
- Keep changes focused and atomic
- Write clear, self-documenting code
- Add comments for complex logic
- Update documentation
- Add tests for new features

### 3. Follow Code Style

**Python Style** (PEP 8):
```python
# Good
def process_call(caller_phone: str, speech_text: str) -> CallResponse:
    """
    Process incoming call and return response.
    
    Args:
        caller_phone: Caller's phone in E.164 format
        speech_text: Transcribed speech text
        
    Returns:
        CallResponse object with routing decision
    """
    # Implementation
    pass


# Bad
def processCall(callerPhone,speechText):
    # no docstring, wrong naming convention
    pass
```

**Type Hints** (Required):
```python
# Always use type hints
from typing import Optional, List, Dict

def get_session(session_id: str) -> Optional[SessionState]:
    pass

def extract_entities(text: str) -> Dict[str, Any]:
    pass
```

### 4. Write Tests

**Test Structure**:
```python
# tests/test_feature.py
import pytest
from src.feature import FeatureClass


class TestFeatureClass:
    """Test suite for FeatureClass"""
    
    def test_basic_functionality(self):
        """Test basic feature functionality"""
        feature = FeatureClass()
        result = feature.process("input")
        assert result == "expected"
    
    def test_edge_case(self):
        """Test edge case handling"""
        feature = FeatureClass()
        with pytest.raises(ValueError):
            feature.process(None)
    
    @pytest.mark.asyncio
    async def test_async_method(self):
        """Test async method"""
        feature = FeatureClass()
        result = await feature.async_process("input")
        assert result is not None
```

**Test Coverage**:
- Aim for >80% code coverage
- Test happy paths and edge cases
- Test error handling
- Use fixtures for common setups

---

## Testing

### Run All Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_feature.py

# Run specific test
pytest tests/test_feature.py::TestClass::test_method

# Run tests matching pattern
pytest -k "test_routing"

# Verbose output
pytest -v

# Stop on first failure
pytest -x
```

### Test Types

**Unit Tests**:
```python
# Test individual functions/methods
def test_mask_phone():
    from src.utilities.pii_masking import PIIMasker
    assert PIIMasker.mask_phone("+14155551234") == "+1415555****"
```

**Integration Tests**:
```python
# Test multiple components together
@pytest.mark.asyncio
async def test_l1_to_l2_routing():
    state = WorkflowState(raw_prompt="book a cleaning")
    state = await receptionist_l1_node(state)
    state = await route_to_l2(state)
    assert state.current_tier == "L2"
```

**End-to-End Tests**:
```python
# Test complete workflows
@pytest.mark.asyncio
async def test_complete_booking_flow():
    # Test from user input to booking confirmation
    response = await client.post("/call", json={
        "caller_phone": "+14155551234",
        "speech_text": "I want to book a cleaning",
        "call_sid": "test-001"
    })
    assert response.status_code == 200
```

### Fixtures

```python
# conftest.py
import pytest
from src.services.database_service import DatabaseService


@pytest.fixture
async def db_service():
    """Provide database service for tests"""
    service = DatabaseService()
    await service.connect()
    yield service
    await service.disconnect()


@pytest.fixture
def sample_workflow_state():
    """Provide sample workflow state"""
    return WorkflowState(
        caller_phone="+14155551234",
        raw_prompt="test message",
        caller_type=CallerType.CLIENT
    )
```

---

## Code Style

### Formatting

**Black** (Code Formatter):
```bash
# Format all Python files
black src/ tests/

# Check without modifying
black --check src/

# Format specific file
black src/feature.py
```

**isort** (Import Sorting):
```bash
# Sort imports
isort src/ tests/

# Check only
isort --check-only src/
```

**Configuration** (pyproject.toml):
```toml
[tool.black]
line-length = 100
target-version = ['py311']
include = '\.pyi?$'

[tool.isort]
profile = "black"
line_length = 100
multi_line_output = 3
```

### Linting

**Flake8**:
```bash
# Lint code
flake8 src/ tests/

# Configuration in setup.cfg
```

**setup.cfg**:
```ini
[flake8]
max-line-length = 100
exclude = .git,__pycache__,venv
ignore = E203,W503
```

**Pylint**:
```bash
# Run pylint
pylint src/

# Configuration in .pylintrc
```

### Type Checking

**MyPy**:
```bash
# Type check
mypy src/

# Configuration in mypy.ini
```

**mypy.ini**:
```ini
[mypy]
python_version = 3.11
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = True
```

---

## Commit Guidelines

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style (formatting, semicolons, etc.)
- `refactor`: Code refactoring
- `test`: Adding tests
- `chore`: Maintenance tasks

**Examples**:
```bash
# Good commits
git commit -m "feat(routing): add confidence-based L2 selection"
git commit -m "fix(session): handle expired session gracefully"
git commit -m "docs(api): update endpoint documentation"
git commit -m "test(l1): add unit tests for intent classification"

# Bad commits
git commit -m "fixed stuff"
git commit -m "WIP"
git commit -m "updates"
```

**Detailed Example**:
```
feat(clarification): add multi-slot clarification support

Previously, clarification questions only asked for one missing slot
at a time. This change allows the L2 agent to ask for multiple
missing slots in a single question, reducing the number of
clarification rounds needed.

Changes:
- Updated L2 agent to generate multi-slot questions
- Added tests for multi-slot extraction
- Updated documentation

Closes #123
```

### Commit Best Practices

- Write in imperative mood: "add feature" not "added feature"
- Keep subject line under 50 characters
- Separate subject from body with blank line
- Wrap body at 72 characters
- Explain *what* and *why*, not *how*
- Reference issues and pull requests

---

## Pull Request Process

### 1. Prepare Your PR

```bash
# Update your branch with latest main
git fetch upstream
git rebase upstream/main

# Run tests
pytest

# Check code style
black --check src/
flake8 src/
mypy src/

# If all pass, push
git push origin feature/your-feature
```

### 2. Create Pull Request

**PR Title**:
Follow commit message format:
```
feat: Add multi-slot clarification support
fix: Handle expired sessions gracefully
docs: Update API reference documentation
```

**PR Description Template**:
```markdown
## Description
Brief description of changes

## Motivation
Why is this change needed?

## Changes Made
- Change 1
- Change 2
- Change 3

## Testing
How was this tested?
- [ ] Unit tests added
- [ ] Integration tests added
- [ ] Manual testing performed

## Screenshots (if applicable)
[Add screenshots]

## Checklist
- [ ] Code follows project style guidelines
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] No breaking changes
- [ ] CHANGELOG.md updated (if applicable)

## Related Issues
Closes #123
Fixes #456
```

### 3. Code Review Process

**What Reviewers Look For**:
- Code correctness and functionality
- Test coverage
- Code style and consistency
- Documentation completeness
- Performance implications
- Security considerations

**Responding to Reviews**:
- Be open to feedback
- Ask questions if unclear
- Make requested changes promptly
- Mark conversations as resolved
- Re-request review when ready

### 4. Merge Requirements

Before merging, ensure:
- [ ] All CI checks pass
- [ ] At least 1 approval from maintainer
- [ ] No merge conflicts
- [ ] Branch is up to date with main
- [ ] All conversations resolved

---

## Issue Guidelines

### Creating Issues

**Bug Report Template**:
```markdown
## Bug Description
Clear description of the bug

## Steps to Reproduce
1. Step 1
2. Step 2
3. Step 3

## Expected Behavior
What should happen

## Actual Behavior
What actually happens

## Environment
- OS: [e.g., Ubuntu 22.04]
- Python: [e.g., 3.11.5]
- Docker: [e.g., 24.0.5]

## Logs
```
Relevant log output
```

## Additional Context
Any other relevant information
```

**Feature Request Template**:
```markdown
## Feature Description
Clear description of the proposed feature

## Problem It Solves
What problem does this solve?

## Proposed Solution
How should this be implemented?

## Alternatives Considered
What other approaches were considered?

## Additional Context
Any other relevant information
```

### Issue Labels

| Label | Description |
|-------|-------------|
| `bug` | Something isn't working |
| `enhancement` | New feature or request |
| `documentation` | Documentation improvements |
| `good first issue` | Good for newcomers |
| `help wanted` | Extra attention needed |
| `question` | Further information requested |
| `wontfix` | Will not be worked on |
| `duplicate` | Duplicate of another issue |
| `invalid` | Invalid issue |

---

## Community

### Communication Channels

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: Questions and general discussions
- **Slack**: #ai-receptionist channel (invite link)
- **Email**: dev@yourdomain.com

### Getting Help

**Before Asking**:
1. Check existing issues and discussions
2. Read documentation
3. Search for similar questions

**When Asking**:
- Provide context and details
- Include error messages and logs
- Describe what you've tried
- Be patient and respectful

### Recognition

Contributors are recognized in:
- CONTRIBUTORS.md file
- Release notes
- Annual contributor awards

---

## Release Process

### Versioning

We use [Semantic Versioning](https://semver.org/):
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes

### Release Checklist

- [ ] All tests pass
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Version bumped in relevant files
- [ ] Git tag created
- [ ] Release notes written
- [ ] Docker image built and pushed

---

## Additional Resources

### Documentation

- [README.md](README.md) - Project overview
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - System design
- [API_REFERENCE.md](docs/API_REFERENCE.md) - API documentation
- [DEPLOYMENT.md](docs/DEPLOYMENT.md) - Deployment guide

### Tools

- [GitHub Desktop](https://desktop.github.com/) - GUI for Git
- [VSCode](https://code.visualstudio.com/) - Recommended IDE
- [Postman](https://www.postman.com/) - API testing
- [MongoDB Compass](https://www.mongodb.com/products/compass) - Database GUI

### Learning

- [Python Style Guide (PEP 8)](https://pep8.org/)
- [Git Documentation](https://git-scm.com/doc)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [MongoDB Documentation](https://docs.mongodb.com/)

---

## Thank You!

Thank you for contributing to the AI Receptionist System! Your contributions help make this project better for everyone.

**Questions?** Feel free to reach out:
- Email: dev@yourdomain.com
- Slack: #ai-receptionist

---

**Document Version**: 1.0  
**Last Updated**: October 2025