# evals

Two separate checks live here. They catch different things, and neither one runs the LLM.

## 1. `evals/pipeline/`: the deterministic code, run for real

```bash
python3 evals/pipeline/run.py -v
```

Each case in `evals/pipeline/cases/<id>/` has an `input.json` (an analysis.json, the file the skill's LLM step writes), a `pages.json` (saved page text served in place of the network), and an `expected.json`. `run.py` calls the actual code in `skills/signal-scout/scripts/`:

- `finalize.validate()`: schema rules and the score-drift check
- `signal_scout_core.compute_score()`: the dimension weights
- `verify_sources.main()`: verification tiers, Wayback/archive.ph fallback, bot-wall handling, `opener_grounding_note`, handoff filtering, and the exit code

It compares the results to `expected.json` and exits 1 on any mismatch. A change to that code that alters its output on these inputs fails CI. No network access and no API key are needed.

To add a case, copy an existing case directory, edit `input.json` and `pages.json`, and write the `expected.json` you believe is correct. Page text under 200 characters is treated as unreadable, and a "verified" tier needs the evidence quoted from the page.

## 2. `evals/cases/` + `evals/runs/`: litmus grader check on hand-written outputs

```bash
pip install git+https://github.com/OrenSegal/litmus.git
python3 -m litmus.cli gate evals --baseline evals/baseline.json
```

The files in `evals/runs/` are hand-written examples of what a good run could look like (placeholder names such as "A. Maintainer", placeholder URLs, typed-in cost and token numbers). They were not produced by running the skill. CI grades these same files against `baseline.json` on every push, so this check cannot detect a change in the skill's behavior. What it does catch: a change to the assertions in `evals/cases/`, to `signal-scout.schema.json`, or to litmus itself that flips the verdict on these examples.

## Recording real runs

To test the skill's LLM behavior (classification, openers, whether it calls `finalize.py`), record real runs and grade those. This costs API usage and the results vary between runs, so it is not part of CI.

```bash
# from a directory where the signal-scout skill is installed and resolvable by the Claude CLI
python3 -m litmus.cli capture "<the case's input as a prompt>" \
  --model <model> --cwd <that directory> \
  --out evals/runs/<case-id>/sample-02.json
python3 -m litmus.cli run evals
```

Notes:

- `capture` fills `output` only if the final message contains the analysis JSON (a fenced json block or bare JSON). Ask for it in the prompt.
- Claude Code records script calls as `Bash` tool calls, so the `must_run: finalize.py` assertion in case 01 will not match a real capture as written. Adjust that assertion before relying on it.
- Once real samples replace the hand-written ones, delete the hand-written files, run `python3 -m litmus.cli bless evals`, and commit the new baseline. Until then, treat a green result from this suite as a check of the grader, not of the skill.
