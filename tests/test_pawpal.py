from datetime import date

import pytest

from pawpal_system import Owner, Pet, Scheduler, Task


def make_owner_with_pets():
    owner = Owner("Sam")
    biscuit = Pet("Biscuit", "Dog")
    whiskers = Pet("Whiskers", "Cat")
    owner.add_pet(biscuit)
    owner.add_pet(whiskers)
    return owner, biscuit, whiskers


def test_add_pet_sets_back_reference():
    owner = Owner("Sam")
    pet = Pet("Biscuit", "Dog")

    owner.add_pet(pet)

    assert pet in owner.pets
    assert pet.owner is owner


def test_mark_complete_changes_task_status():
    task = Task("Morning walk", 30, "high", preferred_time="08:00")
    assert task.completed is False

    task.mark_complete()

    assert task.completed is True


def test_add_task_increases_pet_task_count():
    pet = Pet("Biscuit", "Dog")
    assert len(pet.tasks) == 0

    pet.add_task(Task("Morning walk", 30, "high", preferred_time="08:00"))

    assert len(pet.tasks) == 1


def test_add_task_sets_pet_back_reference():
    pet = Pet("Biscuit", "Dog")
    task = Task("Morning walk", 30, "high", preferred_time="08:00")

    pet.add_task(task)

    assert task in pet.tasks
    assert task.pet is pet


def test_owner_get_all_tasks_aggregates_across_pets():
    owner, biscuit, whiskers = make_owner_with_pets()
    walk = Task("Morning walk", 30, "high", preferred_time="08:00")
    litter = Task("Litter box cleaning", 15, "medium", preferred_time="09:00")
    biscuit.add_task(walk)
    whiskers.add_task(litter)

    all_tasks = owner.get_all_tasks()

    assert walk in all_tasks
    assert litter in all_tasks
    assert len(all_tasks) == 2


def test_edit_task_updates_fields():
    pet = Pet("Biscuit", "Dog")
    task = Task("Morning walk", 30, "high", preferred_time="08:00")
    pet.add_task(task)

    pet.edit_task(task.id, {"duration_minutes": 45, "priority": "medium"})

    assert task.duration_minutes == 45
    assert task.priority == "medium"


def test_edit_task_raises_for_unknown_id():
    pet = Pet("Biscuit", "Dog")

    with pytest.raises(ValueError):
        pet.edit_task("nonexistent-id", {"priority": "low"})


def test_remove_task_removes_it():
    pet = Pet("Biscuit", "Dog")
    task = Task("Morning walk", 30, "high", preferred_time="08:00")
    pet.add_task(task)

    pet.remove_task(task.id)

    assert task not in pet.tasks


def test_conflicts_with_overlapping_times():
    task_a = Task("Morning walk", 30, "high", preferred_time="08:00")
    task_b = Task("Feeding", 10, "high", preferred_time="08:15")

    assert task_a.conflicts_with(task_b)


def test_conflicts_with_non_overlapping_times():
    task_a = Task("Morning walk", 30, "high", preferred_time="08:00")
    task_b = Task("Feeding", 10, "high", preferred_time="09:00")

    assert not task_a.conflicts_with(task_b)


def test_scheduler_fits_tasks_within_time_budget():
    owner, biscuit, whiskers = make_owner_with_pets()
    biscuit.add_task(Task("Morning walk", 30, "high", preferred_time="08:00"))
    biscuit.add_task(Task("Feeding", 10, "high", preferred_time="08:30"))
    whiskers.add_task(Task("Litter box cleaning", 15, "medium", preferred_time="09:00"))

    scheduler = Scheduler(available_time_minutes=60)
    plan = scheduler.build_plan(owner, date(2026, 7, 7))

    assert len(plan.scheduled_tasks) == 3
    assert plan.skipped_tasks == []
    assert plan.total_time_used() == 55


def test_scheduler_skips_lower_priority_tasks_when_time_runs_out():
    owner, biscuit, whiskers = make_owner_with_pets()
    biscuit.add_task(Task("Morning walk", 30, "high", preferred_time="08:00"))
    whiskers.add_task(Task("Nail trim", 20, "low", preferred_time="10:00"))

    scheduler = Scheduler(available_time_minutes=30)
    plan = scheduler.build_plan(owner, date(2026, 7, 7))

    scheduled_descriptions = [task.description for task in plan.scheduled_tasks]
    skipped_descriptions = [task.description for task in plan.skipped_tasks]

    assert "Morning walk" in scheduled_descriptions
    assert "Nail trim" in skipped_descriptions


def test_scheduler_excludes_completed_tasks():
    owner, biscuit, _ = make_owner_with_pets()
    done_task = Task("Morning walk", 30, "high", preferred_time="08:00", completed=True)
    biscuit.add_task(done_task)

    scheduler = Scheduler(available_time_minutes=60)
    plan = scheduler.build_plan(owner, date(2026, 7, 7))

    assert done_task not in plan.scheduled_tasks
    assert done_task not in plan.skipped_tasks
