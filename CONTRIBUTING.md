# Contributing

## Setup

```bash
git clone https://github.com/OrenSegal/signal-scout.git
cd signal-scout
```

No dependency install needed to read or edit the skill — the scripts under `skills/signal-scout/scripts/` use only the Python standard library plus `pytest` for tests.

## Running tests

```bash
pip install pytest
python3 -m pytest skills/signal-scout/scripts/ -v
```

This is the exact command CI runs on every push and PR — if it passes locally, it'll pass in CI.

## Making changes

- **`scripts/verify_sources.py` is the trust boundary** — it's what turns "don't re-check this by hand" from a hopeful claim into an honest one. Any change here needs a test proving a claim that isn't actually on the cited page still gets caught and dropped.
- **Keep the three prospect types (Individual / Segment / Company) scored on their own dimensions.** Don't add a shared "one score fits all" path — that's the exact flattening this project exists to avoid.
- **`diff_reports.py` and `recalibrate.py` read a product's full saved run history, not just the latest snapshot.** If you touch either, make sure a prospect who resurfaced or already has a logged outcome is still classified correctly, not re-announced as new.
- Don't add a benchmarked cost or performance claim to the README unless you're also adding what backs it (a script, a result) — this project deliberately doesn't claim numbers it hasn't earned.

## Pull requests

Open against `main`. Include the failing case your change fixes (or the passing test your feature adds) — this project relies on `verify_sources.py`'s and `diff_reports.py`'s tests being real regression coverage, not just present.
