"""Temporary testing ground for pawpal_system.py — run with: python main.py"""

from datetime import date

from pawpal_system import Owner, Pet, Scheduler, Task

owner = Owner("Sam")

biscuit = Pet("Biscuit", "Dog")
whiskers = Pet("Whiskers", "Cat")
owner.add_pet(biscuit)
owner.add_pet(whiskers)

# Tasks are added out of chronological order on purpose, to prove
# sort_by_time() actually reorders them rather than relying on insertion order.
litter = Task("Litter box cleaning", 15, "medium", category="grooming", preferred_time="09:00")
whiskers.add_task(litter)

feeding = Task("Feeding", 10, "high", category="feeding", preferred_time="08:30")
biscuit.add_task(feeding)

nail_trim = Task("Nail trim", 20, "low", category="grooming", preferred_time="17:00")
nail_trim.mark_complete(date.today())  # already done today
whiskers.add_task(nail_trim)

walk = Task("Morning walk", 30, "high", category="walk", preferred_time="08:00")
biscuit.add_task(walk)

# Deliberately overlaps with "Morning walk" (08:00-08:30) on a different pet,
# to demonstrate conflict detection across pets, not just within one pet's tasks.
vet_call = Task("Vet call", 15, "medium", category="meds", preferred_time="08:15")
whiskers.add_task(vet_call)

scheduler = Scheduler(available_time_minutes=60)
plan = scheduler.build_plan(owner, date.today())

print("=== Today's Schedule ===")
print(plan.summary())
print()
print(scheduler.explain(plan))

print()
print("=== Sorting demo: Scheduler.sort_by_time() ===")
all_tasks = owner.get_all_tasks()
print("Before sorting (insertion order):")
for task in all_tasks:
    print(f"  {task.preferred_time} - {task.description}")

print("After sorting:")
for task in scheduler.sort_by_time(all_tasks):
    print(f"  {task.preferred_time} - {task.description}")

print()
print("=== Filtering demo: Scheduler.filter_tasks() ===")
incomplete_tasks = scheduler.filter_tasks(all_tasks, completed=False)
print("Incomplete tasks:")
for task in incomplete_tasks:
    print(f"  {task.description}")

biscuit_tasks = scheduler.filter_tasks(all_tasks, pet_name="Biscuit")
print("Biscuit's tasks:")
for task in biscuit_tasks:
    print(f"  {task.description}")

print()
print("=== Conflict detection demo: Scheduler.detect_conflicts() ===")
conflict_warnings = scheduler.detect_conflicts(all_tasks)
if conflict_warnings:
    for warning in conflict_warnings:
        print(warning)
else:
    print("No conflicts found.")

print()
print("=== Recurring task demo: mark_complete() spawns the next occurrence ===")
print(f"Biscuit's tasks before completing the walk: {len(biscuit.tasks)}")
next_walk = walk.mark_complete(date.today())
print(f"Biscuit's tasks after completing the walk: {len(biscuit.tasks)}")
print(f"'{walk.description}' completed: {walk.completed}, due today: {walk.is_due(date.today())}")
print(f"Next occurrence due date: {next_walk.due_date} (today + 1 day, since recurrence='daily')")
