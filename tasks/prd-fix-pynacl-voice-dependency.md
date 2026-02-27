# PRD: Fix PyNaCl Missing Dependency for Discord Voice

## Introduction

The Discord music bot crashes with `RuntimeError: PyNaCl library needed in order to use voice` whenever a user runs `/play`. `discord.py` requires `PyNaCl` for all voice channel operations (encryption of the audio stream). The library is missing from `pyproject.toml` and therefore never installed into the Docker image.

## Goals

- Add `PyNaCl` to the project's declared dependencies so it is installed in all environments.
- Ensure the Docker image includes the `libsodium` system library that `PyNaCl` links against.
- Rebuild the container and confirm `/play` connects to a voice channel without error.

## User Stories

### US-001: Add PyNaCl to Python dependencies

**Description:** As a developer, I want `PyNaCl` declared in `pyproject.toml` so it is installed automatically in every environment (local, CI, Docker).

**Acceptance Criteria:**
- [ ] Change `"discord.py>=2.0"` to `"discord.py[voice]>=2.0"` in `pyproject.toml` (the `[voice]` extra pulls in `PyNaCl` as a declared transitive dependency)
- [ ] Alternatively, add `"PyNaCl>=1.5"` as an explicit entry in the `dependencies` list
- [ ] `pip install .` in a clean virtualenv succeeds and `python -c "import nacl"` exits without error

### US-002: Add libsodium system package to the Dockerfile

**Description:** As a developer, I want the Docker image to include the `libsodium` system library so `PyNaCl` can link against it reliably on Debian/Ubuntu-based images.

**Acceptance Criteria:**
- [ ] `libsodium23` (or `libsodium-dev`) is added to the `apt-get install` line in `Dockerfile` alongside `ffmpeg`
- [ ] `docker build .` completes without errors
- [ ] `docker run` starts the bot without import errors related to nacl/libsodium

### US-003: End-to-end smoke verification

**Description:** As a developer, I want to confirm that a rebuilt container lets the bot join a voice channel so the fix is verified in the real runtime environment.

**Acceptance Criteria:**
- [ ] `docker compose up --build` rebuilds the image successfully
- [ ] Bot starts and connects to the Discord gateway (INFO log: "has connected to Gateway")
- [ ] Running `/play <url>` in a Discord server where the bot has voice permissions does NOT produce `RuntimeError: PyNaCl library needed in order to use voice` in the logs
- [ ] Bot joins the voice channel and begins audio playback

## Functional Requirements

- FR-1: `pyproject.toml` must declare `discord.py[voice]>=2.0` (or include `PyNaCl>=1.5` as a direct dependency) so `PyNaCl` is installed by `pip install .`.
- FR-2: The `Dockerfile` `apt-get install` step must include `libsodium23` to provide the native shared library that `PyNaCl` links against.
- FR-3: No other application code changes are required; the crash is purely a missing-dependency issue.

## Non-Goals

- No changes to bot commands, audio logic, or queue management.
- No changes to CI pipeline or test suite (tests mock the voice client and are unaffected).
- No performance tuning or audio quality improvements.

## Technical Considerations

- `discord.py[voice]` is the idiomatic way to pull in voice dependencies; it pins a compatible version of `PyNaCl` automatically.
- `PyNaCl` wheels for Linux (`manylinux`) bundle `libsodium` internally, so the system package may be redundant for wheel installs — but it is still good practice and avoids breakage if the package is ever installed from source.
- The `python:3.12-slim` base image does not include `libsodium23` by default; it must be added explicitly.
- After changes, the Docker image must be **rebuilt** (`docker compose up --build`) for them to take effect — simply restarting the existing container is not enough.

## Success Metrics

- Zero occurrences of `RuntimeError: PyNaCl library needed in order to use voice` after the image is rebuilt.
- `/play` successfully connects the bot to a voice channel on first invocation.

## Open Questions

- None. Root cause is fully identified; fix is deterministic.
