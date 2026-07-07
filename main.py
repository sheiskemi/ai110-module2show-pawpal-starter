"""Temporary testing ground for pawpal_system.py — run with: python main.py"""

from datetime import date

from pawpal_system import Owner, Pet, Scheduler, Task

owner = Owner("Sam")

biscuit = Pet("Biscuit", "Dog")
whiskers = Pet("Whiskers", "Cat")
owner.add_pet(biscuit)
owner.add_pet(whiskers)

biscuit.add_task(
    Task("Morning walk", 30, "high", category="walk", preferred_time="08:00")
)
biscuit.add_task(
    Task("Feeding", 10, "high", category="feeding", preferred_time="08:30")
)
whiskers.add_task(
    Task("Litter box cleaning", 15, "medium", category="grooming", preferred_time="09:00")
)

scheduler = Scheduler(available_time_minutes=60)
plan = scheduler.build_plan(owner, date.today())

print("=== Today's Schedule ===")
print(plan.summary())
print()
print(scheduler.explain(plan))
