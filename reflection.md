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

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

**b. Tradeoffs**

`Scheduler.build_plan()` fills the day's time budget **greedily by priority**: it sorts all due tasks (high → medium → low) and adds each one in that order as long as it still fits in the remaining time, rather than searching for the combination of tasks that uses the time budget most fully (a knapsack-style optimization).

Concretely, this means the scheduler can leave time on the table. For example, with a 40-minute budget and candidate tasks "Walk" (30 min, high), "Training" (25 min, medium), and "Feeding" (10 min, high): priority order tries Walk (30, high) first — fits, 10 min left — then Feeding (10, high) — fits exactly, 0 min left — then skips Training (25, medium) since it no longer fits. Total used: 40/40, which happens to be optimal here. But swap "Feeding" for a 15-minute high-priority task and the greedy approach schedules Walk (30) then skips the 15-minute task (only 10 min left), leaving 10 minutes unused, even though "Training" (25, medium) plus nothing else wouldn't fit either — a smarter packing could have found a better-fitting subset in some cases, but greedy-by-priority doesn't search for one.

I chose this tradeoff deliberately: a true optimal-packing scheduler (dynamic programming knapsack) would guarantee full use of the time budget, but it would also let a pile of low-priority tasks "win" a slot over a higher-priority task just because they pack more efficiently into the remaining minutes. For a pet owner, "did the important stuff happen" matters more than "was every minute of free time accounted for" — a few unused minutes is a minor cost, but bumping a medication task for two shorter enrichment tasks because they fit better is the wrong behavior. Greedy-by-priority also stays O(n log n) (just a sort) and is easy to explain in `DailyPlan.explanation()` ("skipped because not enough time was left"), whereas a knapsack-based explanation would be harder for an owner to reason about ("skipped because a different combination filled the day better").

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
