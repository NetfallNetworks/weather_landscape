# Contributing to Weather Landscape

## Welcome!

Thank you for contributing to the Weather Landscape project. This document provides guidelines for contributing code, tests, and documentation.

---

## Table of Contents
1. [Getting Started](#getting-started)
2. [Development Workflow](#development-workflow)
3. [Definition of Done](#definition-of-done)
4. [Quality Gates](#quality-gates)
5. [Code Review Process](#code-review-process)
6. [Style Guide](#style-guide)

---

## Getting Started

### Prerequisites

Before contributing, ensure you have:

- [ ] Python 3.12+ installed
- [ ] Node.js 20+ installed (for wrangler CLI)
- [ ] uv package manager installed
- [ ] Git configured
- [ ] Cloudflare account set up
- [ ] OpenWeatherMap API key obtained
- [ ] Repository cloned locally

### First-Time Setup

```bash
# Clone repository
git clone https://github.com/NetfallNetworks/weather_landscape.git
cd weather_landscape

# Create Python virtual environment
./makevenv.sh

# Install Node dependencies (for wrangler)
npm install -g wrangler

# Authenticate with Cloudflare
wrangler login

# Set up local config (generates wrangler local configs from templates)
./setup-local-config.sh

# Run local image generation test
python run_test.py
```

---

## Development Workflow

### 1. Pick a Task

- Check GitHub Issues for available tasks
- Check `plan/` for phased work items
- Get approval before starting major features

### 2. Create Feature Branch

```bash
git checkout main
git pull origin main
git checkout -b feature/your-feature-name
```

**Branch Naming:**
- `feature/` - New features
- `bugfix/` - Bug fixes
- `refactor/` - Code improvements
- `docs/` - Documentation
- `test/` - Test additions

### 3. Develop with TDD

```bash
# 1. Write failing test
# 2. Implement feature
# 3. Make test pass
# 4. Refactor
# 5. Repeat
```

### 4. Test Thoroughly

```bash
# Run local generation test
python run_test.py

# Test with API calls
python test_local_generation.py

# Test individual workers locally
cd workers/web && npx wrangler dev

# Deploy all workers to verify
./deploy-all.sh
```

### 5. Commit Changes

```bash
git add <specific-files>
git commit -m "feat: add new weather encoding feature"
```

**Commit Message Format:**
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation
- `style` - Formatting
- `refactor` - Code restructuring
- `test` - Test changes
- `chore` - Maintenance

**Examples:**
```bash
feat(landscape): add fog rendering for low visibility
fix(fetcher): handle timeout from OpenWeatherMap API
docs(readme): update deployment instructions
test(generator): add edge case for sub-zero temperatures
```

### 6. Push and Create PR

```bash
git push origin feature/your-feature-name
```

---

## Definition of Done

### Code Level DoD

**Required for every code change:**

- [ ] **Functionality Complete**
  - Feature works as specified
  - Handles edge cases
  - No known bugs

- [ ] **Code Quality**
  - Follows project style guide
  - No commented-out code
  - No hardcoded values (use environment variables or KV)
  - No print statements in production code (use proper logging)

- [ ] **Documentation**
  - Docstrings for public functions
  - Inline comments for complex logic
  - README updated if needed
  - API changes documented

- [ ] **Security**
  - No secrets in code
  - Input validation present
  - Error handling implemented
  - Security implications considered

### Testing Level DoD

**Required for every code change:**

- [ ] **Functional Tests**
  - Local generation produces correct output
  - All test scripts pass
  - Edge cases covered

- [ ] **Worker Tests**
  - Worker starts without errors via `wrangler dev`
  - Queue processing works end-to-end
  - R2 uploads succeed
  - KV reads/writes function correctly

- [ ] **Visual Verification**
  - Generated landscape images render correctly
  - All output formats (rgb_light, rgb_dark, bw, eink, bwi) verified
  - Sprites render at correct positions
  - Temperature curves display accurately

- [ ] **Performance**
  - No performance regressions
  - Image generation completes within worker CPU limits
  - R2 upload latency acceptable

### Review Level DoD

**Required before merge:**

- [ ] **Code Review**
  - At least 1 approval
  - All review comments addressed
  - No unresolved discussions

- [ ] **QA Review** (for phase completions)
  - 4-agent QA review run (see `plan/README.md`)
  - All CRITICAL and HIGH findings fixed
  - MEDIUM findings documented or fixed

- [ ] **Git Hygiene**
  - Commit messages follow convention
  - No merge conflicts
  - Branch up to date with base branch
  - Logical, atomic commits

### Deployment Level DoD

**Required for production deployment:**

- [ ] **Deployment Verification**
  - All 5 workers deploy successfully via `deploy-all.sh`
  - Cron triggers fire correctly
  - Queue pipeline processes end-to-end
  - Web interface serves images correctly

- [ ] **Monitoring**
  - Check Cloudflare dashboard for worker errors
  - Verify R2 bucket contains fresh images
  - Confirm KV stores have current weather data

- [ ] **Rollback Plan**
  - Previous worker versions identified
  - Rollback procedure tested if applicable

---

## Quality Gates

### Pre-Commit Gates

Before committing:

```bash
# 1. Run local tests
python run_test.py

# 2. Verify image output visually
# 3. Check for secrets or hardcoded values
# 4. If any fail -> do not commit
```

### Pre-Push Gates

Before pushing to remote:

```bash
# Required to pass:
python run_test.py          # Local generation works
python test_local_generation.py  # API-connected test works
```

### Deployment Gates

**Before deploying to production:**

- [ ] All local tests pass
- [ ] Worker-level testing complete
- [ ] Visual verification of generated images
- [ ] QA review complete (for phase completions)
- [ ] `deploy-all.sh` succeeds without errors

---

## Code Review Process

### For Authors

**Before Requesting Review:**

1. Self-review your code
2. Run all test scripts
3. Visually verify generated images
4. Update documentation
5. Write clear PR description

### For Reviewers

**Review Checklist:**

**Code Quality:**
- [ ] Code is readable and maintainable
- [ ] Follows project conventions (Python style guide)
- [ ] No unnecessary complexity
- [ ] Error handling adequate

**Functionality:**
- [ ] Solves the stated problem
- [ ] Handles edge cases (missing weather data, API failures, etc.)
- [ ] No obvious bugs
- [ ] Performance acceptable within worker limits

**Security:**
- [ ] No API keys or secrets in code
- [ ] Input validation present for external data
- [ ] Error messages don't leak sensitive info

**Use Conventional Comments:**

- `nitpick:` - Minor suggestion, not blocking
- `question:` - Requesting clarification
- `suggestion:` - Proposed improvement
- `issue:` - Problem that must be fixed
- `praise:` - Positive feedback

---

## Style Guide

### Python

**Follow PEP 8 with these project conventions:**

**Naming:**
```python
# Variables and functions: snake_case
chat_id = 123
def validate_weather_data(): ...

# Classes: PascalCase
class WeatherParser: ...

# Constants: UPPER_SNAKE_CASE
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 10000

# Boolean variables: use is/has/can prefix
is_valid = True
has_precipitation = False
```

**Functions:**
```python
# GOOD: Small, single responsibility
def extract_temperature(weather_data):
    return weather_data.get("main", {}).get("temp")

# BAD: Too large, multiple responsibilities
def handle_weather(data):
    # 50 lines of code doing multiple things
    ...
```

**Error Handling:**
```python
# GOOD: Specific errors with context
raise ValueError(f"Invalid ZIP code: {zip_code}")

# BAD: Generic errors
raise Exception("Error")
```

**Docstrings for public APIs:**
```python
def generate_landscape(weather_data, format_type="rgb_light"):
    """Generate a landscape image from weather forecast data.

    Args:
        weather_data: Dict containing OpenWeatherMap API response.
        format_type: Output format - one of rgb_light, rgb_dark, bw, eink, bwi.

    Returns:
        PIL.Image: Generated landscape image.

    Raises:
        ValueError: If format_type is not recognized.
    """
    ...
```

### Worker Code

- Each worker is isolated — minimal dependencies by design
- Keep `pyproject.toml` dependencies to the absolute minimum
- Use KV for shared state between workers, Queues for message passing
- Never import modules from other workers directly

---

**Document Version:** 1.0
**Last Updated:** 2026-03-12
**Maintained By:** Lead Engineer
