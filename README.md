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

```bash
# Run the full test suite:
pytest

# Run with coverage:
pytest --cov
```

Sample test output:

```
# Paste your pytest output here
```

## 📐 Smarter Scheduling

| Feature | Method(s) | Notes |
|---------|-----------|-------|
| Task sorting | `Scheduler.sort_by_time()` | Sorts tasks chronologically by `preferred_time`. Since times are stored as zero-padded `"HH:MM"` strings, plain string comparison already matches chronological order, so no time-parsing is needed just to sort. Tasks with no `preferred_time` sort last. `build_plan()` calls this to order the final `scheduled_tasks` for display, after priority decided *which* tasks got included. |
| Filtering | `Owner.get_tasks(pet=, completed=, category=)`, `Scheduler.filter_tasks(tasks, completed=, pet_name=)` | `Owner.get_tasks()` filters across all of an owner's pets by pet object, completion status, and/or category. `Scheduler.filter_tasks()` filters an arbitrary task list by completion status and/or pet name — used for ad-hoc views (e.g., "show only Biscuit's incomplete tasks") independent of building a full plan. |
| Conflict handling | `Task.conflicts_with(other)`, `Scheduler.detect_conflicts(tasks)`, `Scheduler.build_plan()` | `Task.conflicts_with()` checks whether two tasks' preferred times overlap, based on `preferred_time` + `duration_minutes`. `build_plan()` calls it while assembling a plan and skips (rather than double-books) a task that conflicts with one already scheduled, recording the reason in `DailyPlan.skip_reasons`. `Scheduler.detect_conflicts()` is a separate, lightweight pairwise scan (`itertools.combinations`) that returns human-readable warning strings for every overlapping pair across all tasks — including across different pets — without raising an exception. |
| Recurring tasks | `Task.mark_complete()`, `Task.is_due()` | Each `Task` has a `recurrence` of `"once"`, `"daily"`, or `"weekly"`. Completing a `"daily"`/`"weekly"` task via `mark_complete()` retires that instance and automatically creates + attaches a new `Task` for the next occurrence, due `completed_on + timedelta(...)` (1 day or 1 week out). `is_due(on_date)` tells the scheduler whether a given task should appear in that day's plan based on its `due_date` and completion status. |

## 📸 Demo Walkthrough

Describe your app in numbered steps so a reader can follow along without watching a video:

1. <!-- Describe this step -->
2. <!-- Describe this step -->
3. <!-- Describe this step -->
4. <!-- Describe this step -->
5. <!-- Add more steps as needed -->

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->
