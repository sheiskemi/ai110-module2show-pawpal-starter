# PawPal+ Project Reflection

## 1. System Design

**Core user actions**

Based on the scenario in the README, a user of PawPal+ should be able to:

1. **Add a pet and owner profile** — enter basic owner and pet information (e.g., pet name, species/breed) so the app knows who it's planning care for.
2. **Add and edit care tasks** — create tasks like walks, feeding, meds, enrichment, or grooming, each with a duration and priority, and update them as needs change.
3. **Generate and view today's plan** — produce a daily schedule that fits the available time and respects task priorities/preferences, and see that plan along with an explanation of why tasks were included, excluded, or ordered the way they were.

**Building blocks (candidate objects)**

Brainstorming the main objects the system needs, based on the three core actions above:

- **Owner**
  - Attributes: `name`, `preferences` (e.g., preferred walk times, notes)
  - Methods: none of its own yet — mostly a data holder referenced by `Pet`

- **Pet**
  - Attributes: `name`, `species`/`breed`, `owner`, `tasks` (list of `Task` objects)
  - Methods: `add_task()`, `edit_task()`, `remove_task()` — manage the list of care tasks for this pet

- **Task**
  - Attributes: `title`, `duration_minutes`, `priority` (low/medium/high), `category` (walk, feeding, meds, enrichment, grooming), `recurrence` (e.g., daily/weekly), `preferred_time` (optional)
  - Methods: mostly attribute getters/setters; maybe `conflicts_with(other_task)` to detect overlapping preferred times

- **Scheduler** (or `PlanBuilder`)
  - Attributes: `available_time_minutes`, `tasks` (candidate tasks to consider)
  - Methods: `build_plan()` — sorts/filters tasks by priority and available time and returns a `DailyPlan`; `explain(plan)` — generates the reasoning text for why tasks were included/excluded/ordered

- **DailyPlan**
  - Attributes: `pet`, `scheduled_tasks` (ordered list with assigned times), `skipped_tasks`, `date`
  - Methods: `total_time_used()`, `summary()` — formats the plan for display, `explanation()` — returns the reasoning behind the schedule

**a. Initial design**

My initial UML (`diagrams/uml.mmd`) has five classes, each with a single clear responsibility:

- **Owner** is a simple data holder for the person caring for the pet — just a `name` and a `preferences` dict (e.g., preferred walk times). It has no behavior of its own; it exists so `Pet` has someone to belong to.
- **Pet** represents the animal being cared for (`name`, `species`, a reference to its `Owner`) and owns the list of `Task` objects associated with it. Its responsibility is managing that task list — `add_task()`, `edit_task()`, `remove_task()` — not scheduling.
- **Task** models a single care item (title, duration, priority, category, recurrence, optional preferred time). It's mostly a data object, with `conflicts_with(other)` as its one piece of behavior for detecting overlapping preferred times.
- **Scheduler** is the class responsible for turning a pet's tasks into a plan. It takes the available time and candidate tasks and is responsible for `build_plan()` (deciding what fits and in what order) and `explain()` (producing the reasoning). I split this out from `Pet` and `Task` on purpose so the scheduling algorithm isn't tangled up with data storage — `Pet` and `Task` shouldn't need to know *how* a plan gets built.
- **DailyPlan** is the output object: the result of running the scheduler for a given pet and date, holding `scheduled_tasks` and `skipped_tasks` plus display/reasoning helpers (`total_time_used()`, `summary()`, `explanation()`).

The relationships are intentionally shallow: `Owner` has many `Pet`s, `Pet` has many `Task`s, `Scheduler` creates a `DailyPlan`, and `DailyPlan` references the `Task`s it scheduled. I avoided adding extra classes (e.g., a separate `TimeSlot` or `Notification` class) since nothing in the current scenario requires them yet.

**b. Design changes**

While reviewing the `pawpal_system.py` skeleton against the UML, I caught a few gaps and made three changes:

1. **Added `Owner.pets`.** The UML showed "Owner '1' --> 'many' Pet", but the code only had the reverse link (`Pet.owner`). There was no way to look up all of an owner's pets without scanning every `Pet` instance. Added `pets: list[Pet]` to `Owner` so the relationship is navigable in both directions, matching the diagram.

2. **Added `Task.id`.** `Pet.edit_task(task_id, ...)` and `Pet.remove_task(task_id)` both look up a task by id, but `Task` had no id field to match against — the methods were unimplementable as written. Added `id: str` (auto-generated via `uuid.uuid4()`) to `Task`.

3. **Made `Scheduler` stateless.** The original constructor took its own `tasks` list *and* `build_plan()` separately took a `pet` (which has its own `tasks`) — two possible sources of truth for what's being scheduled, risking a mismatch if someone built a `Scheduler` from one task list but called `build_plan()` on a different pet. Removed `tasks` from the constructor; `Scheduler` now only holds `available_time_minutes`, and `build_plan(pet, date)` reads `pet.tasks` directly.

These were caught by re-reading the skeleton against the UML relationships rather than during actual implementation, but the reasoning is the same: fix the data model before scheduling logic gets built on top of it and the gaps become harder to unwind.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

The scheduler considers three constraints when building a day's plan: **time** (`Scheduler.available_time_minutes` — the day's budget), **priority** (`Task.priority`, high/medium/low, which sets the order candidates are considered in), and **due date/completion** (`Task.is_due()` excludes anything already completed today or not yet due). A fourth constraint, **time-slot conflicts** (`Task.conflicts_with()`), acts as a filter on top of priority — a task can be next in priority order and still get skipped if its preferred time overlaps with something already scheduled.

I decided priority mattered most because it's the one constraint a pet owner explicitly sets to say "this matters more" — a missed medication task is a materially worse outcome than a missed enrichment activity, even if the enrichment task would have "fit" better. Time is a hard constraint (you can't schedule more minutes than exist in the day), so it acts as the ceiling rather than a ranking signal. Conflicts came last because they're rare in practice (most tasks don't specify a preferred time) but need to be checked before anything is locked in, otherwise the plan would double-book a pet.

**b. Tradeoffs**

`Scheduler.build_plan()` fills the day's time budget **greedily by priority**: it sorts all due tasks (high → medium → low) and adds each one in that order as long as it still fits in the remaining time, rather than searching for the combination of tasks that uses the time budget most fully (a knapsack-style optimization).

Concretely, this means the scheduler can leave time on the table. For example, with a 40-minute budget and candidate tasks "Walk" (30 min, high), "Training" (25 min, medium), and "Feeding" (10 min, high): priority order tries Walk (30, high) first — fits, 10 min left — then Feeding (10, high) — fits exactly, 0 min left — then skips Training (25, medium) since it no longer fits. Total used: 40/40, which happens to be optimal here. But swap "Feeding" for a 15-minute high-priority task and the greedy approach schedules Walk (30) then skips the 15-minute task (only 10 min left), leaving 10 minutes unused, even though "Training" (25, medium) plus nothing else wouldn't fit either — a smarter packing could have found a better-fitting subset in some cases, but greedy-by-priority doesn't search for one.

I chose this tradeoff deliberately: a true optimal-packing scheduler (dynamic programming knapsack) would guarantee full use of the time budget, but it would also let a pile of low-priority tasks "win" a slot over a higher-priority task just because they pack more efficiently into the remaining minutes. For a pet owner, "did the important stuff happen" matters more than "was every minute of free time accounted for" — a few unused minutes is a minor cost, but bumping a medication task for two shorter enrichment tasks because they fit better is the wrong behavior. Greedy-by-priority also stays O(n log n) (just a sort) and is easy to explain in `DailyPlan.explanation()` ("skipped because not enough time was left"), whereas a knapsack-based explanation would be harder for an owner to reason about ("skipped because a different combination filled the day better").

---

## 3. AI Collaboration

**a. How you used AI**

I used my AI coding assistant across every phase: brainstorming the initial UML, converting it into class skeletons, implementing the `Task`/`Pet`/`Owner`/`Scheduler` logic, adding the sorting/filtering/conflict-detection layer, writing the automated test suite, and finally wiring the algorithmic layer into the Streamlit UI. The most effective feature by far was **giving it the actual source files (`pawpal_system.py`, `app.py`) instead of describing them from memory** — asking "based on my final implementation, what should change in the UML?" produced a genuinely accurate diff (e.g., catching that `build_plan(pet, date)` had actually become `build_plan(owner, plan_date)`, and that `DailyPlan.pet` had become `DailyPlan.owner`) instead of a generic guess. The second most useful feature was its ability to **run code and read the output back** (`python -m py_compile`, `python main.py`, `pytest`) rather than just writing code and trusting it — every UI or logic change in this project was verified against a real run before I considered it done.

The most helpful prompts were narrow and file-anchored: "update the display logic in app.py to use the Scheduler methods" or "does the UML still match pawpal_system.py" gave it a concrete artifact to check against, rather than open-ended asks like "make the scheduler smarter," which tend to produce plausible-sounding but unverified suggestions.

**b. Judgment and verification**

One suggestion I rejected outright: an earlier pass at `app.py` had left in debug instrumentation (`st.write("DEBUG mark_complete signature:", ...)`, `st.code(inspect.getsource(...))`) at the top of the file — clearly leftover from diagnosing something during development, but it had no place in a "professional manual"-grade UI. I had it stripped out entirely rather than commented out, since keeping dead debug code around "just in case" is exactly the kind of clutter that makes a codebase harder to trust later.

I also pushed back on the shape of a couple of UI suggestions rather than accepting them verbatim — for example, when asked to make the task list "look professional" with `st.table`, the first instinct was to keep the existing per-row markdown+button loop and just restyle it. I rejected that because `st.table` can't embed a button inline, so I had the assistant restructure it: a read-only `st.table` for the sorted/filtered view, with task completion handled separately via a selectbox + button. Every change was checked either by running `python -m py_compile app.py` to confirm it wasn't syntactically broken, or by manually running `python main.py` and diffing the printed output against what the README claimed it would show — I didn't accept a "sample output" block without having actually produced that output myself.

**c. Separate chat sessions for different phases**

The git history (`chore: add class skeletons` → `feat: implement Task/Pet/Owner/Scheduler logic` → `feat: implement sorting, filtering, and conflict detection` → `test: add automated test suite` → UI/UML/README polish) reflects that each phase was its own focused session rather than one long, sprawling conversation. That mattered because each phase had a different unit of truth to check against: the skeleton phase was checked against the UML, the logic phase against the skeleton's method signatures, the algorithm phase against the tests I was about to write, and this final polish phase against the actual behavior of `pawpal_system.py` and `main.py`. Keeping them separate meant each session's context stayed small and relevant — the assistant wasn't dragging along irrelevant history from the UML-drafting phase while I was debugging a conflict-detection edge case, and I could re-anchor a new session on the current state of the code rather than on what I'd said three phases earlier (which might already be stale).

**d. Being the "lead architect"**

The biggest lesson was that the AI is very good at *filling in* a design once the shape is decided, but the decisions that keep the system clean — where a responsibility lives, whether a class should be stateful, what a method's real signature should be — still need a human holding the whole picture. The `Scheduler` becoming stateless (removing its own `tasks` list so `Owner`/`Pet` stayed the single source of truth) and the UML corrections in this session are both cases where the AI could execute the change quickly and correctly once I'd identified *what* was wrong, but it took someone reading the code end-to-end against the diagram to notice the mismatch in the first place. Treating the AI as a fast, capable pair of hands — rather than the one deciding the architecture — kept the design coherent instead of drifting toward whatever the most recent prompt happened to produce.

---

## 4. Testing and Verification

**a. What you tested**

The 30 tests in `tests/test_pawpal.py` cover five groups of behavior:

- **Data-model wiring** — adding a pet sets the `Pet.owner` back-reference, adding a task sets `Task.pet`, `Owner.get_all_tasks()` aggregates across pets, and `Pet.edit_task()`/`remove_task()` work (including raising `ValueError` for an unknown id). These matter because every scheduling behavior downstream depends on these references being correct — a broken back-reference would silently make conflict detection or "which pet is this for" display wrong without an obvious error.
- **Conflict detection** — `Task.conflicts_with()` for overlapping, non-overlapping, and exactly-back-to-back times; `Scheduler.detect_conflicts()` across pets and for exact-same-time duplicates; and `build_plan()` skipping a conflicting task even when time is available. This is the behavior most likely to have an off-by-one bug (is the boundary `<` or `<=`?), so it needed direct coverage rather than just trusting the logic looked right.
- **Priority + time-budget scheduling** — tasks fit within budget, lower-priority tasks get skipped when time runs out, an already-completed task is excluded entirely (not scheduled *or* skipped), and a task that exactly fills the remaining budget is still scheduled. Important because these are the core promise of the app ("respects priority and time"), and boundary conditions (`==` budget, `0` remaining) are exactly where greedy-fill logic tends to break.
- **Recurrence** — completing a `"daily"`/`"weekly"` task spawns a next occurrence due one interval later and attached to the same pet; a `"once"` task does not spawn a successor. Important because recurrence is stateful (it mutates and creates objects), so it's easy to get subtly wrong (e.g., spawning from the wrong date, or not attaching to the pet).
- **Sorting and edge cases** — chronological ordering regardless of insertion order, tasks with no `preferred_time` sorting last, an owner with no pets, a pet with no tasks, and a task due exactly on the plan date.

**b. Confidence**

I'm fairly confident in the core scheduling behaviors (priority ordering, time-budget fitting, conflict skipping, recurrence) since each has direct, boundary-aware test coverage and I re-ran `main.py` manually to visually confirm the same behaviors end-to-end, not just through assertions. I'm less confident in things the tests don't touch: multi-day recurrence chains (does completing three "daily" occurrences in a row keep producing correct due dates without drift?), and what happens if a task's `preferred_time` is malformed rather than absent — `conflicts_with()` assumes well-formed `"HH:MM"` strings and would raise on garbage input rather than failing gracefully.

If I had more time, I'd add tests for: multi-day recurrence chains (three consecutive completions), a task whose duration pushes past midnight (`preferred_time="23:30"`, `duration_minutes=60`), three-or-more-way conflicts (does every pair get reported, or just the first?), and `Owner.get_tasks()` combined with multiple filters at once (pet + completed + category together) rather than one filter at a time.

---

## 5. Reflection

**a. What went well**

I'm most satisfied with the conflict-detection and recurrence logic together — they're the two features that turn PawPal+ from "a to-do list with a sort function" into something that actually reasons about a pet owner's day. Skipping a conflicting task instead of silently double-booking it, and explaining *why* in `DailyPlan.skip_reasons`, means the plan is trustworthy without the owner having to manually cross-check times. And because both were built with tests alongside the logic (not after), I never had to go back and guess whether an edge case worked — I already knew.

**b. What you would improve**

If I had another iteration, I'd redesign the greedy-by-priority scheduler to at least *try* a same-priority-tier reordering before giving up on a task that doesn't fit — right now, if a high-priority task doesn't fit in the remaining budget, it's skipped even if a same-priority task later in the list would have fit in that space. I'd also promote `preferred_time` validation into the `Task` constructor (or a small parser) instead of letting `conflicts_with()` assume well-formed `"HH:MM"` strings, since right now a malformed time would raise deep inside scheduling logic instead of failing clearly at the point where the bad data was entered.

**c. Key takeaway**

The main thing I learned is that AI collaboration works best as a tight loop between a clear architectural decision and a fast, verifiable implementation of it — not as a way to skip making the decision. Every time I let the assistant infer the design (e.g., what `Scheduler` should hold state for, whether `build_plan` should take a `Pet` or an `Owner`), I ended up correcting it later against the actual requirements. Every time I made the call first and had the assistant implement and verify it, the result matched what I actually needed on the first pass.
