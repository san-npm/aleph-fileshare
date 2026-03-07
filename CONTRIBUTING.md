# Contributing to AlephFileShare

Thank you for your interest in contributing! This document explains how to get started.

## Development Setup

1. Fork and clone the repo
2. Copy `.env.example` to `.env` and fill in your values
3. Run `docker-compose up` to start the full local stack
4. Frontend at `http://localhost:3000`, API docs at `http://localhost:8000/docs`

## Branching Convention

- `main` — stable, production-ready
- `dev` — integration branch for features
- Feature branches: `feat/short-description`
- Bug branches: `fix/short-description`

## Commit Convention

We use [Conventional Commits](https://www.conventionalcommits.org):

```
feat: add file expiry date support
fix: handle IPFS timeout on large uploads
docs: update deployment guide
refactor: split scanner agent into modules
test: add unit tests for auth service
```

## Pull Request Process

1. Open a PR against `dev` (not `main`)
2. Fill in the PR template
3. Ensure all CI checks pass
4. Request review from a maintainer
5. PRs are squash-merged

## Code Style

- **Python**: `black` formatter, `ruff` linter, type hints required
- **TypeScript**: `eslint` + `prettier`, strict mode
- **Commits**: Conventional commits enforced by CI

## Good First Issues

Look for issues labeled `good first issue` or `help wanted` in the Issues tab.

## Questions?

Open a GitHub Discussion or join us on [Discord](https://discord.aleph.cloud).
