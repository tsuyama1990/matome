# Rules for AI agents

Governance is provided by jtc-gov (`gov`, installed as a uv tool: `uv tool install git+https://github.com/tsuyama1990/cheeze_gyudon`).

Common rules. The same table is in every repository; change all copies together (the source is the jtc-gov repository, `.specs/REQ-2026-011/02_system_design.md` §5).

"Enforced by" names the mechanism that stops a violation. An agent hook only works where the harness has it installed (not every agent has one); `text only` means nothing stops you, so follow the rule yourself.

<!-- gov:rules v1 -->
| ID | Rule | Enforced by |
|---|---|---|
| R01 | Do not put new behavior on `main` before a human has approved its design (`.specs/<REQ>/approval.json`, state `open`). | gate (`gov check`, K) |
| R02 | Approval files are created by a human, never by an agent. | agent hook (asks) |
| R03 | Do not commit or edit directly on `main` / `master`. | agent hook; remote ruleset |
| R04 | Name branches `<type>/<topic>`. | text only |
| R05 | Do not run `git add -A` / `git add .`; stage by path. | agent hook |
| R06 | Merge into `main` only through `merge-to-main.sh`. | agent hook (denies `git merge` on `main`) |
| R07 | The gate passes before merge. | merge script; CI |
| R08 | The merge message states requirement → evidence. | merge script (message check) |
| R09 | Push only when the user asks. | agent hook (asks) |
| R10 | A change that alters results needs the user's approval before merge. | agent hook (asks before the merge script) |
| R11 | Run bonsai before merge; report the net line change and what was removed. | merge script (message check) |
| R12 | Uncommitted changes in the working repository pass the gate; after 3 failures at the same gate, stop and report. | agent hook (Stop) |
| R13 | Work in this order: design, tests, code. Do not write code before its test. | text only |
| R14 | Every test carries a requirement marker whose tag exists in the spec. | gate (`gov check`, T) |
| R15 | If the implementation must diverge from an approved design, fix the design and get re-approval first. | text only |
| R16 | Do not weaken tests to make code pass. | text only |
| R17 | When you replace code, delete the old code in the same commit. | gate (dead-code check, partial) |
| R18 | Delegate to a separate worktree and branch; the receiver re-runs the gate and does not trust self-reports. | text only (R07 re-runs the gate) |
| R19 | Escalate to a human only for human acts (approval, push, merging a change that alters results), anything that leaves the machine, or anything irreversible. Otherwise decide with a checkpoint commit and, where it matters, one ledger line, and keep going. Approval is the human's answer to one question; the agent does the hashing and writing (replaces C1 of REQ-2026-010 via DEC-062). Details: `.specs/REQ-2026-013/02_system_design.md` in the jtc-gov repository. | text only |
<!-- /gov:rules -->

## This repository

1. **Design first.** A change to `src/` together with tests or specs needs a human-approved design: `.specs/<REQ>/approval.json` with state `open`. Write the design and its test specification together in `.specs/<REQ>/` (`01_req_spec.md` + `01_acceptance_tests.feature` … `04_detail_design.md` + `04_unit_tests.md`).
2. **Every test function carries `@pytest.mark.requirement("REQ-YYYY-NNN-Fnn")`** whose tag exists in that requirement's `01_req_spec.md`.
3. **Run `scripts/gate.sh`** before finishing. Do not copy its thresholds anywhere else (they live in `pyproject.toml`).
