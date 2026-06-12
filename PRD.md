# NomadShots — Product Requirements Document

**Version:** 0.1 · **Owner:** Meeru · **Date:** 2026-06-12
**One-liner:** Publish your travel photos without leaking where you sleep.

## 1. Problem

Travel photos carry embedded metadata that exposes the photographer's exact movements. In a validation run on a real library (2024 Vietnam trip, iPhone 15 Pro), **501 of 501 photos (100%) contained GPS coordinates**, plus device make/model, iOS version, and capture timestamps. From metadata alone, the full four-week route was reconstructable day by day (HCMC → Da Nang → Son Tra → Hue → Hoi An → Ha Giang → Hanoi), down to guesthouse-level coordinates. Anyone receiving these files — blog readers, social platforms that don't strip EXIF, chat recipients — gets this data for free.

Existing tools (exiftool, ImageOptim) are powerful but unopinionated: users must know what to strip, how to verify it, and how to avoid corrupting originals. NomadShots is the opinionated, safe-by-default pipeline.

## 2. Target users

Digital nomads and travel bloggers publishing photos regularly; privacy-conscious individuals sharing photos of family; OSINT-aware professionals. Primary persona: a travel blogger with thousands of unorganized iPhone photos who wants a safe "camera roll → blog" path.

## 3. Product

A local-first CLI tool. Python, distributed via pipx/Homebrew. Open source.

### Commands (MVP order)

**v0.1 — `nomadshots audit <folder>`** (ship first, standalone value)
Scans a folder, reports per file: GPS present, nearest location name, device info, timestamps, other sensitive fields. Output: terminal summary + `audit-report.md`. Headline output: "X of Y photos contain GPS coordinates."

**v0.2 — `nomadshots scrub <folder> --out <dir>`**
Copies files to output dir; strips all metadata except orientation and color profile. Originals are NEVER modified.

**v0.3 — `nomadshots export <folder> --out <dir>`**
Scrub + resize (default 2048px long edge) + format conversion (HEIC→JPEG q85, optional WebP).

**v0.4 — `nomadshots scan <folder>`**
Clusters photos into trips using date gaps + GPS distance. Foundation for `timeline`.

**Backlog:** `timeline` (human-readable trip narrative from metadata — validated manually 2026-06-12); `--paranoid` flag (replace ICC profile with generic sRGB, randomize file order/names); XMP sidecar auditing (Lightroom users); osxphotos integration (read directly from macOS Photos library, read-only); watch mode.

## 4. Hard requirements (non-negotiable invariants)

1. **Originals are read-only.** No command ever modifies, moves, or deletes a source file.
2. **Offline by default.** No network calls. Reverse geocoding uses an offline dataset; anything requiring network must be behind an explicit opt-in flag.
3. **Verification is independent and whitelist-based.** After scrubbing, verification must assert that ONLY allowed tags remain (orientation, ICC profile, image structure) — not merely that known-bad tags are absent. Verification must not reuse the same code path that performed the strip.
4. **HEIC support is first-class.** Validation corpus was 100% HEIC.
5. **Fail loud.** Any file that cannot be verified clean is reported as FAIL and excluded from output; exit code non-zero.

## 5. Documented decisions

- **ICC profile retained by default.** Display P3 profile contains "Apple Computer Inc." strings — not personally identifying (shared by hundreds of millions of devices), and stripping it shifts colors. Revisit under `--paranoid`.
- **Defaults:** JPEG quality 85, 2048px long edge — validated visually on the 501-photo corpus.
- **exiftool as backend** for metadata read/strip (battle-tested); independent verification via a second parser (e.g. Pillow/pillow-heif or a minimal binary scan) to satisfy requirement 3.

## 6. Validation evidence (2026-06-12, manual pipeline via QoderWork)

501 HEIC originals processed: 100% contained GPS; 0 contained device serials; scrub + export produced 501 JPEGs; verification 501/501 PASS; independently confirmed with manual exiftool sweep (zero sensitive tags across folder) and spot-check diff against originals.

## 7. Success criteria

v0.1: `audit` runs on a 500+ photo folder in under a minute and its report matches a manual exiftool sweep. Launch post published using own-library data. v0.3: full pipeline reproduces the manual validation run with one command. Adoption signal: 100 GitHub stars / first external issue filed.

## 8. Non-goals

No cloud service, no accounts, no photo editing/filters, no upload integrations in v0.x. The tool's credibility IS its offline, local-only posture.