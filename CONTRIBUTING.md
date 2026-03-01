# Contributing to Discord Music Bot

Thank you for your interest in contributing! This project welcomes contributions from everyone — whether you're fixing a typo, adding a new audio source, or improving the dashboard UI. This guide will walk you through everything you need to get your changes accepted.

---

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Branch Naming Convention](#branch-naming-convention)
4. [Commit Message Style](#commit-message-style)
5. [Pull Request Process](#pull-request-process)
6. [PR Checklist](#pr-checklist)
7. [CI Requirements](#ci-requirements)
8. [Review Process](#review-process)
9. [Internal Team: develop → main Promotion](#internal-team-develop--main-promotion)
10. [Setting Up GitHub Secrets for Deployment](#setting-up-github-secrets-for-deployment)
11. [Reporting Bugs & Requesting Features](#reporting-bugs--requesting-features)

---

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/version/2/1/code_of_conduct/). By participating, you agree to uphold a welcoming and respectful environment for everyone. Report unacceptable behaviour to the maintainers via GitHub Issues.

---

## Getting Started

Before contributing, make sure you can run the project locally. Follow the full setup instructions in the [README Quick Start](README.md#quick-start-local-development) section, which covers:

- Cloning the repo
- Installing Python dependencies (`pip install -e ".[dev]"`)
- Configuring `.env`
- Running the bot (`python -m bot`)
- Running the dashboard (`npm run dev` in `dashboard/`)

Once you can run the project locally, you're ready to contribute.

---

## Branch Naming Convention

All branches must be created from `develop`. Use a short, descriptive name with one of these prefixes:

| Prefix | Use for |
| --- | --- |
| `feat/` | New features |
| `fix/` | Bug fixes |
| `chore/` | Maintenance tasks (deps, config, CI) |
| `docs/` | Documentation-only changes |

**Examples:**

```
feat/add-spotify-support
feat/dashboard-volume-slider
fix/queue-crash-on-empty
fix/oauth-redirect-loop
chore/upgrade-discord-py-2.4
chore/add-dependabot-config
docs/improve-api-reference
docs/add-screenshots
```

---

## Commit Message Style

Write commit messages in the **imperative, present tense** — describe what the commit *does*, not what you *did*.

**Good:**
```
Add Spotify URL resolver
Fix queue crash when bot is not in a voice channel
Update README with new API routes
```

**Avoid:**
```
Added Spotify URL resolver
Fixed queue crash
Updated README
```

Keep the subject line under 72 characters. For larger changes, add a blank line after the subject and write a short body explaining the *why*.

---

## Pull Request Process

1. **Fork** the repository to your GitHub account (external contributors only; team members clone directly).
2. **Create a branch** from `develop`:
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feat/your-feature-name
   ```
3. **Make your changes** — keep commits focused and atomic.
4. **Run all checks locally** before pushing (see [CI Requirements](#ci-requirements)).
5. **Push your branch** and open a PR targeting `develop`:
   ```bash
   git push origin feat/your-feature-name
   ```
6. **Fill in the PR description** — explain what changed, why, and how to test it.
7. **Wait for CI** — all checks must pass before review begins.
8. **Address review feedback** — push additional commits to the same branch; do not force-push after review has started.

> PRs targeting `main` directly will not be accepted. All changes go through `develop` first.

---

## PR Checklist

Copy this checklist into your PR description and check off each item before requesting review:

```markdown
- [ ] I have read CONTRIBUTING.md
- [ ] My branch is based on `develop` (not `main`)
- [ ] All tests pass: `pytest --tb=short`
- [ ] Linting is clean: `ruff check bot/`
- [ ] Dashboard typechecks: `cd dashboard && npm run typecheck`
- [ ] I have added or updated tests for new behaviour
- [ ] I have updated documentation if public-facing behaviour changed
- [ ] The PR description explains what changed and why
- [ ] I have not committed `.env` or any secrets
```

---

## CI Requirements

Every PR to `develop` runs the following checks automatically via the [`ci.yml`](.github/workflows/ci.yml) workflow. **All must pass before your PR can be merged:**

| Check | Command | What it validates |
| --- | --- | --- |
| Pytest (full suite) | `pytest --tb=short` | Unit tests in `tests/unit/` and integration tests in `tests/integration/` |
| Ruff linting | `ruff check bot/` | PEP8 compliance (E, F, W rules) and common Python errors |
| TypeScript typecheck | `npm run typecheck` (in `dashboard/`) | TypeScript types across the entire React dashboard |

If any check fails, the PR cannot be merged. Fix the failure and push again — CI reruns automatically.

To run all checks locally before pushing:

```bash
# Python
pytest --tb=short
ruff check bot/

# Dashboard
cd dashboard
npm run typecheck
```

---

## Review Process

- Maintainers aim to review PRs within **2–3 business days**.
- At least **one maintainer approval** is required before merging.
- If your PR has been waiting more than a week without feedback, feel free to leave a comment asking for a review.
- Maintainers may request changes — address each point with a new commit and re-request review.

---

## Internal Team: develop → main Promotion

> This section is for team members with write access to the repository.

The branch strategy keeps `develop` as the integration branch and `main` as the stable production branch.

**Promotion process:**

1. Ensure `develop` is green — CI must be passing.
2. Verify the dev environment (deployed automatically on every `develop` push) looks correct.
3. Open a **PR from `develop` to `main`** with a summary of what's being promoted:
   ```
   Title: chore: promote develop → main (YYYY-MM-DD)
   Body: list of changes included since last promotion
   ```
4. Get at least one other team member to review the promotion PR.
5. **Merge** (do not squash — preserve the individual commits for history).
6. The [`deploy-prod.yml`](.github/workflows/deploy-prod.yml) workflow triggers automatically on the `main` push, runs CI, and deploys to the production server.
7. Monitor the GitHub Actions run and confirm the production deploy step completes successfully.

**Rollback:** If production is broken after a promotion, revert the merge commit on `main`:

```bash
git revert -m 1 <merge-commit-sha>
git push origin main
```

This triggers a new production deploy with the reverted code.

---

## Setting Up GitHub Secrets for Deployment

> This section applies to team members who manage deployment infrastructure.

The deploy workflows use `appleboy/ssh-action` to connect to servers over SSH and run `docker compose` commands. Two sets of secrets are required — one per environment.

### Development environment secrets

Navigate to **GitHub → Settings → Environments → development** and add:

| Secret | Description |
| --- | --- |
| `DEV_HOST` | Hostname or IP address of the dev server |
| `DEV_USER` | SSH username (e.g. `deploy` or `ubuntu`) |
| `DEV_SSH_KEY` | Private SSH key (RSA or Ed25519, PEM format) — the corresponding public key must be in `~/.ssh/authorized_keys` on the server |
| `DEV_DEPLOY_PATH` | Absolute path to the `docker-compose.yml` directory on the dev server (e.g. `/home/deploy/discord-music-bot`) |

### Production environment secrets

Navigate to **GitHub → Settings → Environments → production** and add:

| Secret | Description |
| --- | --- |
| `PROD_HOST` | Hostname or IP address of the production server |
| `PROD_USER` | SSH username |
| `PROD_SSH_KEY` | Private SSH key — the corresponding public key must be in `~/.ssh/authorized_keys` on the production server |
| `PROD_DEPLOY_PATH` | Absolute path to the `docker-compose.yml` directory on the production server |

### Application environment variables

Each server also needs a `.env` file in the deploy path with all required variables (see [Environment Variables](README.md#environment-variables) in the README). Never commit `.env` to the repository.

### Branch protection

To enforce CI checks on `develop`, enable branch protection in **GitHub → Settings → Branches → develop**:

- Check **Require status checks to pass before merging**
- Add `Test Bot (Python 3.11)` and `Lint Dashboard (Node.js 20)` as required status checks
- Check **Require branches to be up to date before merging**

---

## Reporting Bugs & Requesting Features

Use **[GitHub Issues](https://github.com/lopesmarcello/discord-music-bot/issues)** for all bug reports and feature requests.

**Bug reports** should include:
- What you expected to happen
- What actually happened
- Steps to reproduce
- Relevant log output or error messages
- Your environment (OS, Python version, Node version, Docker version)

**Feature requests** should describe:
- The problem you're trying to solve
- Your proposed solution or approach
- Any alternatives you considered

Check existing Issues first to avoid duplicates. If you want to work on an Issue, comment to let maintainers know before opening a PR.
