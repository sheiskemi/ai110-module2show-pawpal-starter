# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## 🖥️ Sample Output

Output from running `python main.py`:

```
=== Today's Schedule ===
Plan for Sam on 2026-07-07:
  08:00 - Morning walk (Biscuit, 30 min) [priority: high]
  08:30 - Feeding (Biscuit, 10 min) [priority: high]
  09:00 - Litter box cleaning (Whiskers, 15 min) [priority: medium]

Scheduled 3 task(s) totaling 55 minutes.
```

## 🧪 Testing PawPal+

The automated suite in [`tests/test_pawpal.py`](tests/test_pawpal.py) covers the core scheduling behaviors, including:

- **Sorting correctness** — tasks are returned in chronological order by `preferred_time`, and tasks with no `preferred_time` sort last.
- **Recurrence logic** — completing a `"daily"`/`"weekly"` task spawns a new task due one interval later (and attaches it to the same pet); `"once"` tasks don't spawn a successor.
- **Conflict detection** — `Scheduler.detect_conflicts()` flags overlapping/duplicate-time tasks (including identical times across different pets), and `build_plan()` skips a lower-priority task rather than double-booking it.
- **Edge cases** — an owner with no pets, a pet with no tasks, a task that exactly fills the time budget, back-to-back (non-overlapping) tasks, and a task due exactly on the plan date.

Run the suite with:

```bash
python -m pytest
```

Sample successful test run:

```
============================================ test session starts =============================================
platform win32 -- Python 3.14.0, pytest-9.0.3, pluggy-1.6.0
rootdir: C:\Users\vicky\codepath\ai110-module2show-pawpal-starter
plugins: anyio-4.13.0
collected 34 items

tests\test_pawpal.py ..................................                                                 [100%]

============================================= 34 passed in 0.14s ==============================================
```

## ✨ Features

- **Chronological sorting** — `Scheduler.sort_by_time()` orders any task list by `preferred_time`, so plans and task lists always read top-to-bottom in the order they happen during the day.
- **Filtering** — `Owner.get_tasks()` and `Scheduler.filter_tasks()` narrow a task list by pet, completion status, and/or category, powering the "All / Pending / Completed" view in the UI.
- **Priority-driven daily planning** — `Scheduler.build_plan()` greedily fills the day's time budget with the highest-priority due tasks first, then re-sorts the result chronologically for display.
- **Conflict warnings** — `Scheduler.detect_conflicts()` flags any two tasks (even across different pets) whose preferred times overlap, and `build_plan()` skips a lower-priority task instead of double-booking it.
- **Daily/weekly recurrence** — `Task.mark_complete()` automatically spawns the next occurrence of a `"daily"` or `"weekly"` task, due one interval later; `"once"` tasks don't recur.
- **Plan explanations** — `DailyPlan.summary()` and `DailyPlan.explanation()` (surfaced via `Scheduler.explain()`) describe what was scheduled, what was skipped, and why.
- **Next-available-slot lookup** *(stretch)* — `Scheduler.find_next_available_slot(tasks, duration_minutes)` scans a day for the earliest open gap of a given length around existing preferred-time tasks, so a new task can be suggested a conflict-free time instead of only being checked for conflicts after the fact.

## 📐 Smarter Scheduling

| Feature | Method(s) | Notes |
|---------|-----------|-------|
| Task sorting | `Scheduler.sort_by_time()` | Sorts tasks chronologically by `preferred_time`. Since times are stored as zero-padded `"HH:MM"` strings, plain string comparison already matches chronological order, so no time-parsing is needed just to sort. Tasks with no `preferred_time` sort last. `build_plan()` calls this to order the final `scheduled_tasks` for display, after priority decided *which* tasks got included. |
| Filtering | `Owner.get_tasks(pet=, completed=, category=)`, `Scheduler.filter_tasks(tasks, completed=, pet_name=)` | `Owner.get_tasks()` filters across all of an owner's pets by pet object, completion status, and/or category. `Scheduler.filter_tasks()` filters an arbitrary task list by completion status and/or pet name — used for ad-hoc views (e.g., "show only Biscuit's incomplete tasks") independent of building a full plan. |
| Conflict handling | `Task.conflicts_with(other)`, `Scheduler.detect_conflicts(tasks)`, `Scheduler.build_plan()` | `Task.conflicts_with()` checks whether two tasks' preferred times overlap, based on `preferred_time` + `duration_minutes`. `build_plan()` calls it while assembling a plan and skips (rather than double-books) a task that conflicts with one already scheduled, recording the reason in `DailyPlan.skip_reasons`. `Scheduler.detect_conflicts()` is a separate, lightweight pairwise scan (`itertools.combinations`) that returns human-readable warning strings for every overlapping pair across all tasks — including across different pets — without raising an exception. |
| Recurring tasks | `Task.mark_complete()`, `Task.is_due()` | Each `Task` has a `recurrence` of `"once"`, `"daily"`, or `"weekly"`. Completing a `"daily"`/`"weekly"` task via `mark_complete()` retires that instance and automatically creates + attaches a new `Task` for the next occurrence, due `completed_on + timedelta(...)` (1 day or 1 week out). `is_due(on_date)` tells the scheduler whether a given task should appear in that day's plan based on its `due_date` and completion status. |
| Next-available-slot *(stretch)* | `Scheduler.find_next_available_slot(tasks, duration_minutes, day_start=, day_end=)` | Builds a sorted list of "busy" `(start, end)` windows from every task that has a `preferred_time`, then walks the day from `day_start` looking for the first gap — before the first busy window, between two busy windows, or after the last one — that's at least `duration_minutes` long. Returns `None` if the day has no gap that size. This flips conflict handling from reactive (detect an overlap after the fact) to proactive (suggest a time that won't overlap in the first place). |

## 📸 Demo Walkthrough

### UI features

The Streamlit app (`app.py`) lets a user:

- Enter an owner name and add one or more pets (name + species).
- Add tasks to a selected pet: title, duration, priority, category (walk / feeding / meds / enrichment / grooming / general), recurrence (once / daily / weekly), and an optional preferred time.
- Filter a pet's task list to **All / Pending / Completed**, displayed in a sorted table with time, duration, priority, category, recurrence, and status columns.
- Mark a pending task complete from a dropdown, which (for daily/weekly tasks) silently queues up the next occurrence.
- See per-pet conflict warnings the moment two of that pet's tasks overlap in time.
- Set a daily time budget and click **Generate schedule** to build a plan across *all* pets, showing which tasks were scheduled (with total minutes used), which were skipped (and why — time budget vs. conflict), and any remaining time conflicts across the whole household.

### Example workflow

1. Enter owner name "Sam" and add a pet, "Biscuit" (dog).
2. Add a task: "Morning walk", 30 min, high priority, category "walk", recurs daily, preferred time 08:00.
3. Add a second task: "Feeding", 10 min, high priority, category "feeding", recurs daily, preferred time 08:30.
4. Add a pet "Whiskers" (cat) and a task "Vet call", 15 min, medium priority, preferred time 08:15 — overlaps with "Morning walk", so a conflict warning appears immediately under Whiskers' task list.
5. Set the available time budget (e.g., 60 minutes) and click **Generate schedule** — the plan shows "Morning walk" and "Feeding" scheduled (55 minutes used), "Vet call" skipped as a conflict, and an explanation of why.

### Key Scheduler behaviors demonstrated

- **Sorting** — tasks entered out of order are displayed chronologically by `preferred_time`.
- **Conflict warnings** — overlapping preferred times across different pets are flagged with an actionable message, and the lower-priority task is skipped rather than double-booked.
- **Recurrence** — completing a daily/weekly task creates its next occurrence automatically.

### Sample CLI output (`python main.py`)

```
=== Today's Schedule ===
Plan for Sam on 2026-07-07:
  08:00 - Morning walk (Biscuit, 30 min) [priority: high]
  08:30 - Feeding (Biscuit, 10 min) [priority: high]
  09:00 - Litter box cleaning (Whiskers, 15 min) [priority: medium]

Scheduled 3 task(s) totaling 55 minutes.
Skipped 1 task(s):
  - Vet call (Whiskers, priority: medium) - conflicts with another scheduled task

=== Sorting demo: Scheduler.sort_by_time() ===
Before sorting (insertion order):
  08:30 - Feeding
  08:00 - Morning walk
  09:00 - Litter box cleaning
  17:00 - Nail trim
  08:15 - Vet call
After sorting:
  08:00 - Morning walk
  08:15 - Vet call
  08:30 - Feeding
  09:00 - Litter box cleaning
  17:00 - Nail trim

=== Filtering demo: Scheduler.filter_tasks() ===
Incomplete tasks:
  Feeding
  Morning walk
  Litter box cleaning
  Vet call
Biscuit's tasks:
  Feeding
  Morning walk

=== Conflict detection demo: Scheduler.detect_conflicts() ===
Warning: 'Morning walk' (Biscuit, 08:00) conflicts with 'Vet call' (Whiskers, 08:15)

=== Recurring task demo: mark_complete() spawns the next occurrence ===
Biscuit's tasks before completing the walk: 2
Biscuit's tasks after completing the walk: 3
'Morning walk' completed: True, due today: False
Next occurrence due date: 2026-07-08 (today + 1 day, since recurrence='daily')

=== Next-available-slot demo: Scheduler.find_next_available_slot() ===
Earliest 20-min opening today, given current tasks: 08:40
```

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->

## 🎨 Professional UI Formatting *(stretch)*

The Streamlit UI in `app.py` uses Streamlit's built-in components rather than raw text to make output easy to scan at a glance:

- **`st.table`** renders the sorted/filtered per-pet task list and the generated daily plan as structured tables (Time, Task, Duration, Priority, Category, Recurrence, Status columns) instead of plain markdown lines.
- **`st.success`** confirms positive outcomes — a task marked complete, a plan built with total minutes used, or "no scheduling conflicts" for a pet.
- **`st.warning`** flags every conflict with an actionable suggestion ("consider moving one of these to a different time"), visually distinct from informational skips.
- **`st.info`** is reserved for neutral/expected states (no tasks yet, a task skipped only because the time budget ran out).
- **Emoji status indicators** (✅ done / ⏳ pending, ⚠️ for conflicts, 🐾 branding) give an at-a-glance read of task and plan state without reading full sentences.
