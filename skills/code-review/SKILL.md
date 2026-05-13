---
name: code-review
description: Smart code review tool
allowed-tools:
  - read_file
  - grep
  - glob
  - shell
when_to_use: "Use when the user wants to review code changes"
argument-hint: "[file-pattern]"
arguments:
  - file-pattern
user-invocable: true
context: inline
---

# Code Review

## Inputs
- `$file-pattern`: Glob pattern for files to review (default: all changed files)

## Goal
Perform a thorough code review and provide actionable feedback.

## Steps

### 1. Identify Changes
Run `git diff` to see what changed.

**Success criteria**: Complete diff is available.

### 2. Analyze Code Quality
Review each change for:
- Potential bugs
- Performance issues
- Security concerns
- Code style

**Success criteria**: All changes reviewed.

### 3. Report Findings
Summarize findings with file/line references.
