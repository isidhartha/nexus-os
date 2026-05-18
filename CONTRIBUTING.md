# Contributing to NexusOS

Thank you for your interest in contributing!

## Getting Started

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Run tests: `pytest`
5. Run linter: `ruff check . && ruff format .`
6. Commit: `git commit -m "feat: add my feature"`
7. Push and open a Pull Request

## Code Style

- Python: follow PEP 8, enforced via `ruff`
- TypeScript: use strict mode, Prettier formatting
- Commit messages: follow Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`)

## Reporting Issues

Use GitHub Issues. Include:
- OS and Python version
- Steps to reproduce
- Expected vs actual behavior
- Relevant logs

## Voice / Hardware Components

When contributing to voice pipeline components, test with both real hardware and mock mode.
