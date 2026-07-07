# AI Interactions Log

> **Stretch features only.** Only fill in the sections that apply to stretch features you attempted. If you did not attempt a stretch feature, leave its section blank or delete it. This file is not required for the core project.

---

## Agent Workflow (SF7)

> Document your experience using an AI agent (e.g., Cursor Agent, Claude, Copilot) to make multi-step changes autonomously.

**What task did you give the agent?**

Across several turns in one agent session I asked Claude Code to: (1) "reflect the algorithmic layer in the UI" — wire `app.py`'s display logic to the `Scheduler` methods instead of showing raw insertion-ordered lists; (2) finalize `diagrams/uml_final.mmd` by comparing it directly against the final `pawpal_system.py`; (3) polish `README.md` with a Features list and a real Demo Walkthrough (including actual `main.py` output, not placeholder text); (4) complete every structured prompt in `reflection.md`; and finally (5) add a third, more advanced scheduling capability — a "find next available slot" method — to earn the Agent Mode stretch credit, and make sure it was properly tested and documented before committing.

**What did the agent do?**

Files touched: `app.py`, `pawpal_system.py`, `tests/test_pawpal.py`, `main.py`, `README.md`, `reflection.md`, `diagrams/uml_final.mmd`. Concretely, the agent:

- Removed leftover debug instrumentation (`inspect.signature`/`inspect.getsource` dumps) it found still sitting in `app.py` from an earlier pass.
- Rewired the pet task list in `app.py` to use `Scheduler.sort_by_time()` and `Scheduler.filter_tasks()` (via an All/Pending/Completed radio), and `Scheduler.detect_conflicts()` for per-pet warnings; then upgraded that same display to `st.table`/`st.success`/`st.warning` for a cleaner look.
- Read `pawpal_system.py` end-to-end and rewrote `diagrams/uml_final.mmd` to match reality — catching that `build_plan(pet, date)` had become `build_plan(owner, plan_date)`, that `DailyPlan.pet` had become `DailyPlan.owner`, and that `Scheduler` had become stateless.
- Ran `python main.py` to capture real CLI output before pasting it into the README, rather than writing a plausible-looking fake transcript.
- Implemented `Scheduler.find_next_available_slot()`, added four new tests for it (before-first-task, gap-between-tasks, full-day/no-slot, and ignoring untimed tasks), wired a demo call into `main.py`, and re-ran the full suite (34 passed) before touching the README/reflection docs.
- Committed and pushed the work, after being asked to check `git status`/`pytest`/`py_compile` first.

**What did you have to verify or fix manually?**

I had to explicitly stop and confirm before the agent pushed to `main` directly — its own safety classifier flagged a direct push to the default branch and asked me to choose between pushing to `main` or opening a PR; I chose direct-push. I also caught that the diagram PNG the agent initially referenced predated the finalized `.mmd` source (it was exported before the diagram was updated), so I had to re-export a fresh PNG from the corrected Mermaid source myself rather than trust the stale file. Everything else (the UML diff, the new slot-finder's edge cases, the README's CLI transcript) I verified by re-reading the diffs and re-running `pytest`/`main.py` myself rather than accepting the agent's summary at face value.

---

## Prompt Comparison (SF11)

> Compare two different prompts (or two different models) on the same task.

Both runs used the same model/tool (Claude Code, Sonnet 5) on the same underlying task — improving how `app.py` presents Scheduler output — but with prompts of very different specificity, in two separate turns of the same session.

| | Option A: vague | Option B: specific |
|-|----------|----------|
| **Model / tool used** | Claude Code (Sonnet 5) | Claude Code (Sonnet 5) |
| **Prompt** | "Update your display logic in app.py to use the methods from your Scheduler class (like sorting or conflict warnings)." | "Use Streamlit components like `st.success`, `st.warning`, or `st.table` to make the sorted and filtered data look professional. If your Scheduler flags a task conflict, how should that warning be presented in the Streamlit UI to be most helpful to a pet owner?" |
| **Response summary** | Wired `sort_by_time`/`filter_tasks`/`detect_conflicts` into the existing per-row markdown+button layout — functionally correct, but visually unchanged (still plain markdown lines with checkmark emoji). | Restructured the same section into `st.table` for the read-only sorted/filtered view, `st.success`/`st.info`/`st.warning` for status, and rewrote each conflict message to name both tasks/times and suggest a fix — a genuinely different (better) design, not just a re-skin. |
| **What was useful** | Fast, low-risk — got the *correct data* flowing through the UI first, which made it easy to verify the underlying logic before worrying about presentation. | Directly answered "how should this look," so the agent had to justify component choices (e.g., `st.warning` not `st.error` since a conflict doesn't block the plan) rather than pick generically. |
| **Problems noticed** | Left the UI looking like a rough draft — a grader skimming the app would have no visual signal that "conflict detection" was even implemented. | Because `st.table` can't embed a per-row button, the agent had to redesign the "mark complete" control as a separate selectbox+button rather than reuse the original per-row loop — a real design tradeoff, not free. |
| **Decision** | Used as the first pass — necessary but not sufficient. | Used for the final implementation. |

**Which approach did you use in your final implementation and why?**

Option B's output is what shipped. The vague prompt (A) was still worth running first — it got the *correct* data path in place with minimal risk of the agent over-engineering a UI before the logic was verified — but it wouldn't have produced a submission that visibly demonstrates the algorithmic work to a grader. The specific prompt (B), especially the follow-up question about *how* a conflict warning should be presented, pushed the agent to make and justify a UX decision (advisory `st.warning`, not a blocking `st.error`; message scoped near the affected tasks; an explicit suggested fix) instead of just applying components decoratively. In general, across this whole project, narrow file- and behavior-anchored prompts ("update X to use Y", "does the diagram still match this file") consistently produced more accurate, more verifiable results than open-ended ones — the same pattern noted in `reflection.md` §3a.
