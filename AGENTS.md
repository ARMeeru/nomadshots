# NomadShots — Code Review & Agent Guidelines

NomadShots is a privacy-first photo metadata tool. Its entire value is trust. Review every change against these rules; violations of the Privacy Invariants section are always Critical severity.

## Privacy Invariants (Critical — block merge)

- Source files must never be opened for writing. Any code path that modifies, moves, renames, or deletes a file inside an input directory is a critical defect, including "temporary" in-place edits.
- No network calls anywhere in the default code path. Any import or use of requests, urllib, httpx, sockets, or subprocess curl/wget outside an explicitly flagged opt-in module is a critical defect. Reverse geocoding must use the bundled offline dataset.
- Image contents and metadata must never appear in logs, error messages, or analytics. Log filenames and counts only. GPS coordinates must never be printed except in the user-requested audit report.
- Scrub verification must be whitelist-based: assert that only allowed tags remain (orientation, ICC profile, image structure), never only that known-bad tags are absent. Verification must use a different parser than the code that performed the strip.
- A file that fails verification must be excluded from output and cause a non-zero exit code. Silently passing unverified files is a critical defect.

## Security Rules

- All file paths from user input must be validated and resolved; no path traversal into directories outside the user-specified input/output.
- Subprocess calls (exiftool) must use argument lists, never shell=True or string interpolation of filenames.
- No secrets, tokens, or API keys anywhere in the codebase or tests. No telemetry.
- Dependencies: minimal and pinned. Flag any new dependency in review; question whether it is necessary.

## Testing Requirements

- Every scrub/export change requires golden-file tests: fixture images with known metadata (GPS, device info, HEIC and JPEG variants) where tests assert byte-level absence of stripped tags and presence of allowed tags.
- The verification module must have negative tests: deliberately corrupted/partial strips must FAIL.
- Original-immutability test: after any pipeline run in tests, assert input fixture checksums are unchanged.
- CLI commands require an end-to-end test against the fixture corpus.

## Code Conventions

- Python 3.11+, typer for CLI, type hints required on public functions.
- Errors: fail loud with actionable messages; never swallow exceptions in the pipeline.
- Keep the dependency on exiftool isolated behind a single adapter module so the backend can be swapped.

## Review Focus for Agents

- Prioritize: privacy invariants > correctness of metadata handling > path/subprocess safety > test coverage > style.
- Ignore: style nits in test fixtures, complexity warnings in fixture-generation scripts.
- When a PR touches the scrub or verify modules, always check the diff against the whitelist rule and the independent-parser rule explicitly.