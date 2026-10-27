# Rules for AI agents

Governance is provided by jtc-gov (`gov`, installed as a uv tool: `uv tool install git+https://github.com/tsuyama1990/cheeze_gyudon`).

1. **Design first.** A change to `src/` together with tests or specs needs a human-approved design: `.specs/<REQ>/approval.json` with state `open`. Write the design and its test specification together in `.specs/<REQ>/` (`01_req_spec.md` + `01_acceptance_tests.feature` … `04_detail_design.md` + `04_unit_tests.md`). Approval files are created by a human.
2. **Every test function carries `@pytest.mark.requirement("REQ-YYYY-NNN-Fnn")`** whose tag exists in that requirement's `01_req_spec.md`.
3. **Run `scripts/gate.sh`** before finishing. Do not copy its thresholds anywhere else (they live in `pyproject.toml`).
4. Do not weaken tests to make code pass.
