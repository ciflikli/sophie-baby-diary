# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

sophie-baby-diary is a lightweight application designed to scale image sizes to fit Sophie the Giraffe baby diary format.

## Project Status

Active development following IMPLEMENTATION_PLAN.md with phased rollout.

## Development Workflow

### Code Review Rule

**After completion of each phase, critically assess the code for:**

1. **Minimalism**: Only building what is needed, no over-engineering, YAGNI principle
2. **Logic**: Correctness, edge cases, algorithm soundness
3. **Accuracy**: Math correctness, type safety, unit conversions
4. **Modularity**: Separation of concerns, reusability, coupling
5. **Performance**: Time/space complexity, unnecessary operations, caching opportunities
6. **Maintainability**: Readability, documentation, testability, debugging ease
7. **Best Practices**: Python idioms, type hints, error handling, security

**Format**: Provide scorecard (1-10) for each criterion with:
- Issues found (with line references)
- Severity (blocking/high/medium/low)
- Recommended fixes
- Overall verdict (proceed/fix-first)

**Trigger**: Automatically after phase commit, before proceeding to next phase.

## License

MIT License - see LICENSE file for details.
