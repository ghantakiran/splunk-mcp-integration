# Project Scripts

This directory contains utility scripts for the Splunk MCP Integration project.

## Available Scripts

### monitor_claude_files.py
Monitors CLAUDE.md files across the project to ensure they stay within manageable token limits.

**Usage:**
```bash
python scripts/monitor_claude_files.py
```

**Features:**
- Scans all CLAUDE.md files in the project
- Estimates token count using character-based heuristics
- Provides color-coded status (OK, WARNING, CRITICAL)
- Shows file statistics (lines, words, characters, tokens)
- Summarizes total project documentation size

**Token Limits:**
- **OK**: < 20,000 tokens (green)
- **WARNING**: 20,000-25,000 tokens (yellow)
- **CRITICAL**: > 25,000 tokens (red)

**Files Monitored:**
- `CLAUDE.md` (main project file)
- `services/*/CLAUDE.md` (service-specific files)
- `frontend/CLAUDE.md` (frontend documentation)
- `infrastructure/CLAUDE.md` (infrastructure documentation)

## Adding New Scripts

When adding new scripts:

1. Create the script file with appropriate permissions
2. Add a shebang line (`#!/usr/bin/env python3`)
3. Include proper documentation and error handling
4. Update this README with script description
5. Test the script thoroughly

## Development Guidelines

- Use Python 3.9+ for all scripts
- Include proper error handling and logging
- Follow project coding standards
- Add type hints where appropriate
- Include docstrings for functions and classes