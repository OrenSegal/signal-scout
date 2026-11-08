# Decisions

Five decisions that shape the code. Where the reasoning at the time was not written down, this says "not recorded".

## 1. Verification is a lexical check against the live page, not a model judgment

**Context.** The model that writes a claim about a prospect also used to grade its own `evidence_quality`. Nothing made it reopen the source, so an invented detail could score well.

**Decision.** `verify_sources.py` fetches every `source_url` and checks that the quoted evidence is on the page. Numbers, capitalized names and identifiers such as `Series A` must appear verbatim; otherwise the prospect is tagged Not on page and `finalize.py` stops before writing a report.

**Alternatives considered.** An LLM or NLI grounding model (Vectara HHEM, Ragas and similar score a claim against text you supply). Rejected because it adds a model dependency and a second judgment that can itself be wrong, and the scripts are stdlib only (decision 3). Not recorded whether this was weighed in more detail.

**Consequences.** Cheap, deterministic and testable offline. It does not read context: a wrong number that appears elsewhere on the page passes, and a correct paraphrase can be tagged Paraphrased. The README says both.

**Evidence.** f0dea88 (first version), 346a0f8 / #10 (specifics check ported from cited), tests in `skills/signal-scout/scripts/test_verification.py`.

## 2. The CI eval runs the deterministic code on fixtures, and says it does not cover the LLM

**Context.** 2bd773a added a litmus gate and the 1.6.2 changelog said it caught regressions in the skill's behavior. It graded hand-written example outputs against a baseline, so no change to the skill could change its result.

**Decision.** `evals/pipeline/run.py` calls the real `finalize.validate()`, `compute_score()` and `verify_sources.main()` on four fixture reports, with saved pages instead of the network, and fails on any output change. The litmus step was kept but renamed to say it does not run the skill.

**Alternatives considered.** Recording real LLM runs in CI: rejected for cost and run-to-run variance (see `evals/README.md`). Deleting the litmus step: rejected because it still checks the assertions and schema.

**Consequences.** Three planted bugs each turned the job red (#3). The LLM steps (finding, classifying, rating, writing openers) have no automated check.

**Evidence.** f2aaa15 / #3, CHANGELOG "Correction to 1.6.2".

## 3. Scripts use only the Python standard library

**Context.** The skill is copied into `~/.claude/skills` or `~/.agents/skills` and run by whatever Python the host has.

**Decision.** No pip installs for the skill's scripts. The MCP server is the exception and has its own `requirements.txt`.

**Alternatives considered.** `requests`/`httpx` for fetching, `jinja2` for the report. Not recorded in detail. `AGENTS.md` states the rule ("Scripts are Python 3.10+ stdlib only — no new dependencies") but not the reason for it; the reason is not recorded.

**Consequences.** `safe_fetch.py` reimplements redirect and address checks on `urllib`, and `generate_report.py` builds HTML with f-strings in one file of about 1,550 lines (decision 5).

**Evidence.** `AGENTS.md` ("Scripts are Python 3.10+ stdlib only"), CI installs only pytest.

## 4. No named people by default on anything public

**Context.** A report can name individuals. A public example, a directory listing or a reachable MCP server should not.

**Decision.** `finalize.py --no-people` (or `"people": false`) drops Individuals before verification, drops prospects whose only source is a personal profile, and redacts names, handles, personal emails and profile URLs. The MCP server defaults to `people=False`. The committed example is a `--no-people` run.

**Alternatives considered.** Relying on `--focus companies`: rejected because it only prioritizes and people still appear. Named-entity recognition: not used; the filter is pattern matching plus the recorded Individual names, and COMPLIANCE.md says what that misses.

**Consequences.** A person named only in a quote, never recorded as an Individual, is not caught; a human has to read a public report before publishing.

**Evidence.** e528d6b / #7, `skills/signal-scout/scripts/test_people_filter.py`, `COMPLIANCE.md`.

## 5. `generate_report.py` stays one file

**Context.** At about 1,550 lines it is the largest file in the repo.

**Decision.** Keep it as one file for now. It is a single f-string template plus its CSS and JS, and the HTML it writes is self-contained by design (one file a user can email or open offline).

**Alternatives considered.** Splitting into data, CSS and render modules. Deferred: tests in `test_generate_report.py` cover its output, and the evals do not depend on its internals. Revisit if the template needs a second report type.

**Consequences.** Hard to review in one sitting; CSS and markup changes land in a Python file.

**Evidence.** `skills/signal-scout/scripts/test_generate_report.py`.
