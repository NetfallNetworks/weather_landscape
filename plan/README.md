# Weather Landscape — Development Methodology

## What is this?

This folder contains the development methodology, agent team definitions, and quality processes for the **Weather Landscape** project — a weather visualization system that encodes forecast data into landscape imagery, deployed as an event-driven pipeline on Cloudflare Workers.

## Plan Structure

| File | Contents |
|------|----------|
| [README.md](./README.md) | Methodology, agent team, QA process — start here |

## Key Decisions (Locked)

- **Platform:** Cloudflare Workers — 5 isolated workers connected via Queues
- **Language:** Python (Workers Python beta) + Pillow for image generation
- **Data Source:** OpenWeatherMap API for weather data
- **Storage:** R2 for generated images, KV for weather data and configuration
- **Architecture:** Event-driven pipeline (Scheduler → Fetcher → Dispatcher → Generator → R2)
- **Deployment:** Template-based wrangler config, one-command deploy via `deploy-all.sh`
- **Output Formats:** rgb_light, rgb_dark, bw, eink, bwi (managed via admin dashboard)
- **Testing:** Every change tested. Local test scripts + worker-level wrangler dev.

## Agent Team

| Agent | Model | Role |
|-------|-------|------|
| **Architect** (Matt + Claude Opus 4.6) | Opus 4.6 | Architecture, code review, complex debugging, prompt engineering |
| **Security Researcher** | Opus 4.6 | Threat modeling, code audit, config review (at milestone gates) |
| **Builder** | Sonnet 4.6 | Primary implementation — Worker code, image generation, pipeline logic |
| **Integrator** | Sonnet 4.6 | OpenWeatherMap API, Cloudflare bindings (KV, R2, Queues), E-Ink module |
| **Tester** | Sonnet 4.6 | Test scripts, edge cases, deployment verification, format validation |

## QA Review Process

After each phase's implementation is complete (code + tests passing), run a **4-agent QA review** before marking the phase done. This catches issues that the builder misses — test quality gaps, security oversights, maintainability debt, and code quality problems.

### How to Run

Launch **4 parallel Sonnet agents** (use `subagent_type: "Explore"`, `model: "sonnet"`), each with a distinct review lens. Give each agent access to all source files and tests changed in the phase.

### The 4 Review Lenses

| Agent | Focus | What It Looks For |
|-------|-------|-------------------|
| **Code Quality** | Implementation correctness | Stack overflows, redundant operations, dead code, inconsistent error handling, missing edge cases, naming issues |
| **Security Hardening** | Attack surface | Injection vectors, credential leaks, TOCTOU races, missing validation, error message information disclosure |
| **Test Quality** | Test suite integrity | Vacuous assertions, tests that test mocks instead of behavior, missing negative cases, weak assertions |
| **Maintainability** | Long-term health | Undocumented constraints, magic numbers, implicit coupling, missing cross-references, migration hazards |

### Agent Prompt Template

Each agent gets a prompt like:

> You are reviewing [files list] as a [LENS] reviewer. Your job is to find real issues, not nitpick style.
>
> Rate each finding: CRITICAL (breaks in production), HIGH (will cause bugs or security issues), MEDIUM (tech debt that compounds), LOW (nice-to-have).
>
> For each finding, provide: the file and line, what's wrong, why it matters, and a concrete fix.
>
> Do NOT suggest: adding comments to obvious code, extracting helpers for one-time operations, adding type annotations to clear code, or changing code style preferences.

### Triage and Fix

1. Collect all findings from the 4 agents
2. Consolidate duplicates (agents often find the same issue from different angles)
3. Fix all CRITICAL and HIGH findings immediately
4. Fix MEDIUM findings if they're quick; otherwise document them as known debt
5. LOW findings are fix-if-convenient
6. Run full test suite after fixes, commit, then mark phase complete

## Task Lifecycle

Every task must be in one of these states at all times:

| State | Meaning | When to use |
|-------|---------|-------------|
| **Not Started** | Work hasn't begun | Default state for new tasks |
| **In Progress** | Actively being worked on | Mark BEFORE starting work |
| **Done** | Fully complete, verified | Mark AFTER work is verified |
| **Deferred** | Paused, not currently active | Stopped working but plan to return |
| **Cancelled** | Will not be done | Decided against doing it |

**Rules:**
1. Mark a task **In Progress** before you start working on it.
2. Mark a task **Done** as soon as it's verified complete.
3. If you stop working on a task but plan to return, mark it **Deferred**.
4. If a task will never be done, mark it **Cancelled**.
5. No task should be left dangling in an ambiguous state.

## Stop-Ship Evaluation Process

After QA reviews complete, evaluate findings before moving to the next phase:

1. **Collect** all findings from review agents.
2. **Deduplicate** — agents often flag the same issue from different angles.
3. **Triage by severity:**
   - **CRITICAL**: Breaks in production. **Must fix before phase closes.** Stop-ship.
   - **HIGH**: Will cause bugs or security issues. **Must fix before phase closes.** Stop-ship.
   - **MEDIUM**: Tech debt that compounds. Fix if quick (<15 min); otherwise document as known debt.
   - **LOW**: Nice-to-have. Fix only if convenient.
4. **Implement** all CRITICAL and HIGH fixes.
5. **Run full test suite** — all tests must pass after fixes.
6. **Commit** fixes with clear messages referencing the review findings.
7. Only then: mark the phase as complete.
