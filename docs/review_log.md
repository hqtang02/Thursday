# Code Review Log

A record of this project's AI-assisted code reviews (GitHub Copilot PR Review) and manual verification process.

- Repository: https://github.com/hqtang02/Thursday
- This file has two parts: Part 1 covers the Rainwater Smart Planner (`thq_test` → `main`, PR #3); Part 2 covers the SmartWater Optimizer (`ctt_test` → `main`, PR #1; `fix/pr1-copilot-findings` → `main`, PR #2).
- Evidence screenshots are stored in `screenshots/`; see the list at the end of this file.

---

# Part 1 · Rainwater Smart Planner (thq_test → main, PR #3)

## Round 1 · 2026-11-22 (commit `94f0933`, see the PR timeline)

### AI Review (GitHub Copilot Review)

> No actionable findings. The added workflow is valid, installs the declared dependencies, runs the intended `test_water_engine.py` suite, and the PR's GitHub Actions run completed successfully.

Conclusion: the AI found no issues. (This round was kept as text in the conversation; no dedicated screenshot was taken.)

### Manual Verification — Issues the AI Missed

1. **CI test scope too narrow**: `tests.yml` only ran `test_water_engine.py`, not the current app's `test_rainwater.py` and `test_recommendation.py`. The AI review confirmed "the intended test suite runs" but did not recognize that the test coverage did not match the actual application code.
2. **Default scenes contain no flexible tasks**: the default selection (Bathroom + Garden) consists entirely of fixed tasks, so the smart scheduler produces no optimization suggestions and the core feature cannot be demoed out of the box.
3. **Form boundary risk**: the `max_value` of Initial Storage / Minimum Reserve is linked to Tank Capacity; after shrinking the capacity, previously entered values could go out of range and raise errors.
4. **Results lacked parameter annotation**: the results section did not show the tank parameters and per-scene usage amounts used in the calculation, so users could not verify which inputs produced a result.
5. **Documentation/dependency mismatch**: the README described features inconsistent with the actual app; `requirements.txt` included unused folium and was missing the actual dependency streamlit-js-eval.

### Resolution: All Accepted and Fixed (commit `1b0e15c`)

- `main.py`: added Laundry (a flexible task) to the default scenes; storage/reserve values are now validated on submit with a clear error message; the results section now annotates parameters and usage amounts.
- `tests.yml`: CI changed to `pytest -q` to run the full suite.
- `requirements.txt` / `WebClick.bat`: removed folium, added streamlit-js-eval.
- `README.md`: rewritten to match the actual Rainwater Smart Planner app.
- Local regression: all `pytest -q` cases passed; the Streamlit app passed a startup health check.

### Lessons Recorded

AI code review is good at catching syntax, configuration, and security issues, but can miss problems that require project context — such as "does the CI test scope cover the current application code". AI review conclusions should be paired with manual verification.

## Round 2 · 2026-11-22 (commit `1b0e15c`, post-fix re-review)

### AI Review (GitHub Copilot Review)

> No actionable findings. The workflow is valid, installs the declared pytest dependency, targets Python 3.12, and the pull-request run completed successfully.

(This round was kept as text in the conversation; no dedicated screenshot was taken.)

### Verification Results

- CI triggered automatically on the PR; the full `pytest -q` suite passed ✅
- No new issues in the post-fix review; all issues found in Round 1 are closed ✅

## Round 3 · 2026-11-22 (final review before merging PR #3)

### AI Review (GitHub Copilot Review, instruction: review all PRs)

> Result: No actionable findings on open PR #3. CI passes, Python modules compile, and both engine test scripts pass. PR #3 appears safe to approve. PRs #1 and #2 are already merged.

Screenshot: `screenshots/pr3_copilot_review.png`; PR #3 all-green Checks and Ready to merge: `screenshots/pr3_ci_passed.png`.

### Resolution

After confirming there were no blocking issues, PR #3 was merged (merge commit `4b84b97`), bringing the `thq_test` development line into `main`. All Part 1 rounds closed ✅

---

# Part 2 · SmartWater Optimizer (PR #1: ctt_test → main; PR #2: fix/pr1-copilot-findings → main, the superset)

## Round 1 · 2026-11-22 · PR #1 (AI review: GitHub Copilot)

Screenshot: `screenshots/pr1_copilot_review.png`; PR #1 all-green Checks: `screenshots/pr1_ci_passed.png`.

### The AI Found 4 Actionable Issues

1. **High — Beijing billed at Hong Kong tariffs**: in `data/water_config.json`, Beijing's `tariff_key` is `hong_kong`, so selecting Beijing computes the bill with Hong Kong tiered pricing.
2. **Medium — Invalid tariff brackets accepted**: `_normalise_brackets` in `water_engine.py` allows a middle bracket to be null (unbounded), silently ignoring all subsequent brackets.
3. **Medium — Malformed URL parameters can crash the app**: URL state restoration only type-casts values without validating them; `?city=invalid` written into session_state triggers a KeyError.
4. **Medium — drought_mode has no actual effect**: the parameter is only validated and returned unchanged, never used in calculations, while the UI claims "the savings target has been automatically increased by a 10% safety margin".

### Manual Verification — All 4 Reproduced and Confirmed

- In the config file, `cities.beijing.tariff_key == "hong_kong"`, and the `tariffs` table has no Beijing pricing;
- a bracket table with a null middle bracket does pass validation;
- `?city=invalid` throws a KeyError at `cities[city_key]` on the results page;
- in the engine, `effective_target = target` — drought_mode never participates in the calculation, and the existing tests had codified this behavior.

### Resolution: All Fixed (commit `f4c8b0b`)

1. The city selector now only lists cities that have a local tariff table; Beijing is no longer selectable (its precipitation data is kept, so the drought-warning engine and tests are unaffected);
2. `_normalise_brackets` rejects bracket tables with a null middle bracket, with a clear error;
3. URL state restoration now validates values (city / view / language / month / people / usage); invalid values are silently ignored;
4. When drought_mode is enabled, `effective_target = target × 1.1`, matching the UI claim; corresponding test expectations updated.

Tests: updated the drought case (target 20 → 22) and added a rejection case for null middle brackets; **all 46 tests passed**.

## Round 2 · 2026-11-22 · PR #2 (AI re-review: GitHub Copilot)

### AI Conclusion

> PR 2 is the superset and should be preferred; PR 1 contains overlapping changes. Both CI suites pass: PR 1 — 45 tests, PR 2 — 46 tests.

Suggestion adopted: merge PR #2, close PR #1.

### The AI Found 1 New Issue

5. **Integer URL parameters truncated instead of rejected**: `int(float(raw))` parses `?people=2.9` as 2 and `?month=1.9` as 1; integer syntax should be enforced strictly.

### Manual Verification and Resolution

Confirmed: the truncation behavior let malformed parameters produce seemingly valid state. Fixed by switching to strict `int(raw)` parsing — invalid values raise ValueError, which the outer layer catches and silently ignores (commit `b09a4a9`). All 46 tests passed.

## Round 3 · 2026-11-22 · PR #2 Post-fix Re-review and Merge

### AI Re-review (GitHub Copilot, instruction: review all pull requests)

> Reviewed both open PRs. PR #2 is merge-ready; PR #1 is superseded and should be closed. Validation: 46 tests pass. CI passes, no blocking findings.

Screenshot: `screenshots/pr2_copilot_review.png`.

### Resolution

- Merged PR #2 (merge commit `1a23341`) and closed the superseded PR #1;
- the 4 issues from Round 1 and the integer-truncation issue from Round 2 are all closed ✅
- Final state of all three PRs (all merged): `screenshots/pr_overview.png`.

---

## Summary of Lessons

- AI review (Copilot Review) effectively catches real defects: data inconsistencies (Beijing tariffs), input validation gaps (URL parameters, null brackets), and behavior that contradicts UI claims (drought_mode);
- it can also miss things (e.g., the CI test scope not matching the actual application code required manual verification), so AI conclusions should be paired with human verification;
- every round of "AI review → manual reproduction → fix → regression tests → re-review" was documented, forming a complete closed loop.

## Appendix: Evidence Screenshot List

| File | Content |
| --- | --- |
| `screenshots/pr_overview.png` | All-PR overview: PR #1 / #2 / #3 all merged (captured 2026-11-23) |
| `screenshots/pr1_copilot_review.png` | Part 2 Round 1: Copilot found 4 actionable issues on PR #1 (45 tests passing locally) |
| `screenshots/pr1_ci_passed.png` | PR #1 (ctt_test → main) all-green Checks, Ready to merge |
| `screenshots/pr2_copilot_review.png` | Part 2 Round 3: post-fix re-review passed — PR #2 merge-ready, PR #1 superseded, 46 tests pass, CI passes |
| `screenshots/pr3_ci_passed.png` | PR #3 (thq_test → main) all-green Checks, Ready to merge |
| `screenshots/pr3_copilot_review.png` | Part 1 Round 3: Copilot re-reviewed all PRs — no actionable findings on PR #3, safe to merge; PR #1 / #2 already merged |

> Note: the Copilot reviews for Part 1 Round 1 / Round 2 and Part 2 Round 2 were kept as text in the conversation at the time (quoted verbatim in their respective sections); no dedicated screenshots were taken.
