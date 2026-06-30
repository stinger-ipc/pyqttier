---
name: release-pyqttier
description: >-
  Automate a standard Python release workflow for the `pyqttier` project.
  Bump version, format code with black, run type checks and tests, then offer
  to commit, tag, build, and optionally publish with uv.
---

# release-pyqttier

## Description
Automate a standard Python release workflow for the `pyqttier` project.
- Steps: bump package version, format with `black`, run `mypy`, run unit tests, then offer to commit+tag and run build/publish commands.

## High-level steps
1. Verify working tree is clean (no unstaged or uncommitted changes).
2. Bump the version in `pyproject.toml` (patch/minor/major as requested).
3. Run `black` across the repository.
4. Run `mypy` type checks.
5. Run unit tests (e.g., `pytest`).
6. Run the smoke test against a live broker (`examples/smoke_test.py`). Requires an MQTT broker on `localhost:1883`; abort the release if it is unreachable or any scenario fails.
7. If all of the above succeed, prompt the user: "Commit and tag the release?" If yes, create a commit and annotated tag.
8. Run `uv build` and report the build result.
9. Prompt the user: "Publish with `uv publish` now?" If yes, run `uv publish`.

## Commands (examples)
- Check git status:

  git status --porcelain

- View current version:

  `uv version`

- Bump version (patch):

  `uv version --bump=patch`

- Bump version (minor):

  `uv version --bump=minor`

- Bump version (major):

  `uv version --bump=major`

- Format:

  `uv run black src/ examples/ tests/`

- Type check:

  `uv run mypy src tests`

- Run tests:

  `uv run pytest`

- Run smoke test (requires a broker on `localhost:1883`):
  `uv pip install .`
  `uv run examples/smoke_test.py`

- Build and publish:

  `uv build`
  `uv publish`

## Agent workflow guidance (implementation notes)
- Always verify the working tree is clean before making changes. Abort and ask the user to commit or stash if not.
- Ask the user which type of version bump they want: `patch`, `minor`, `major`. By default use `patch`.
- Update `pyproject.toml` in-place and commit only the `pyproject.toml` change alongside any generated `CHANGELOG.md` if you add it.
- Use `black` first so `mypy` sees formatted source.
- Fail fast: stop at the first failing check and show the user the output.
- The smoke test (`examples/smoke_test.py`) needs a live MQTT broker on `localhost:1883`. Before running it, check whether a broker is reachable; if not, tell the user and let them start one (e.g., `docker run --rm -p 1883:1883 eclipse-mosquitto`) or skip the smoke test with explicit confirmation. The smoke test exits non-zero if the broker is unreachable or any scenario fails.
- If all checks pass, show a summarized list of actions to be performed (commit message, tag name) and get confirmation before performing git operations.
- After tagging and committing, run `uv build`. If `uv build` succeeds, ask the user whether to run `uv publish`.

## Prompts for user
- "Which version bump would you like: patch/minor/major? (default: patch)"
- "Working tree is not clean. Commit or stash changes and retry?"
- "All checks passed. Commit and tag release vX.Y.Z now? (yes/no)"
- "Build succeeded. Publish with `uv publish` now? (yes/no)"

## Example agent prompt to run the skill
- "Run release-pyqttier and create a patch release."

## Notes and safety
- This skill will perform git commits and tags only after explicit confirmation from the user.
- It will not publish without explicit confirmation.

## What release-pyqttier produces
- Updated `pyproject.toml` with a bumped version
- A `git` commit containing version bump (if user confirms)
- An annotated git tag for the release (if user confirms)
- Optionally runs `uv build` and `uv publish` when confirmed

## Related customizations
- Add automated generation of `CHANGELOG.md` using commit messages.
- Add an option to run `pre-commit` hooks before committing.
- Add integration to upload build artifacts to an artifact server.
