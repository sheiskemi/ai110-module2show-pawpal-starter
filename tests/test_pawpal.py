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


def test_scheduler_excludes_tasks_already_completed_today():
    owner, biscuit, _ = make_owner_with_pets()
    plan_date = date(2026, 7, 7)
    done_task = Task("Morning walk", 30, "high", preferred_time="08:00")
    done_task.mark_complete(plan_date)
    biscuit.add_task(done_task)

    scheduler = Scheduler(available_time_minutes=60)
    plan = scheduler.build_plan(owner, plan_date)

    assert done_task not in plan.scheduled_tasks
    assert done_task not in plan.skipped_tasks


def test_mark_complete_on_daily_task_spawns_next_occurrence_due_tomorrow():
    pet = Pet("Biscuit", "Dog")
    task = Task("Morning walk", 30, "high", recurrence="daily", preferred_time="08:00")
    pet.add_task(task)
    completed_on = date(2026, 7, 7)

    next_task = task.mark_complete(completed_on)

    assert next_task is not None
    assert next_task is not task
    assert next_task in pet.tasks
    assert next_task.due_date == date(2026, 7, 8)
    assert task.is_due(completed_on) is False  # the completed instance is done for good
    assert next_task.is_due(completed_on) is False  # not due until tomorrow
    assert next_task.is_due(date(2026, 7, 8)) is True


def test_mark_complete_on_weekly_task_spawns_next_occurrence_due_in_a_week():
    pet = Pet("Biscuit", "Dog")
    task = Task("Nail trim", 20, "low", recurrence="weekly")
    pet.add_task(task)
    completed_on = date(2026, 7, 1)

    next_task = task.mark_complete(completed_on)

    assert next_task is not None
    assert next_task.due_date == date(2026, 7, 8)
    assert next_task.is_due(date(2026, 7, 5)) is False
    assert next_task.is_due(date(2026, 7, 8)) is True


def test_mark_complete_on_once_task_does_not_spawn_a_new_task():
    task = Task("Vet appointment", 60, "high", recurrence="once")

    next_task = task.mark_complete(date(2026, 7, 7))

    assert next_task is None
    assert task.is_due(date(2026, 7, 8)) is False


def test_scheduled_tasks_are_ordered_chronologically():
    owner, biscuit, _ = make_owner_with_pets()
    biscuit.add_task(Task("Feeding", 10, "high", preferred_time="08:30"))
    biscuit.add_task(Task("Morning walk", 30, "high", preferred_time="08:00"))

    scheduler = Scheduler(available_time_minutes=60)
    plan = scheduler.build_plan(owner, date(2026, 7, 7))

    scheduled_descriptions = [task.description for task in plan.scheduled_tasks]
    assert scheduled_descriptions == ["Morning walk", "Feeding"]


def test_scheduler_skips_conflicting_task_even_with_time_available():
    owner, biscuit, _ = make_owner_with_pets()
    biscuit.add_task(Task("Morning walk", 30, "high", preferred_time="08:00"))
    biscuit.add_task(Task("Vet call", 15, "high", preferred_time="08:15"))

    scheduler = Scheduler(available_time_minutes=120)
    plan = scheduler.build_plan(owner, date(2026, 7, 7))

    scheduled_descriptions = [task.description for task in plan.scheduled_tasks]
    skipped_descriptions = [task.description for task in plan.skipped_tasks]
    assert scheduled_descriptions == ["Morning walk"]
    assert skipped_descriptions == ["Vet call"]


def test_detect_conflicts_warns_about_overlapping_tasks_across_pets():
    owner, biscuit, whiskers = make_owner_with_pets()
    walk = Task("Morning walk", 30, "high", preferred_time="08:00")
    vet_call = Task("Vet call", 15, "medium", preferred_time="08:15")
    biscuit.add_task(walk)
    whiskers.add_task(vet_call)

    scheduler = Scheduler(available_time_minutes=120)
    warnings = scheduler.detect_conflicts(owner.get_all_tasks())

    assert len(warnings) == 1
    assert "Morning walk" in warnings[0]
    assert "Vet call" in warnings[0]


def test_detect_conflicts_returns_empty_list_when_nothing_overlaps():
    owner, biscuit, whiskers = make_owner_with_pets()
    biscuit.add_task(Task("Morning walk", 30, "high", preferred_time="08:00"))
    whiskers.add_task(Task("Litter box cleaning", 15, "medium", preferred_time="09:00"))

    scheduler = Scheduler(available_time_minutes=120)
    warnings = scheduler.detect_conflicts(owner.get_all_tasks())

    assert warnings == []


def test_owner_get_tasks_filters_by_pet_and_status():
    owner, biscuit, whiskers = make_owner_with_pets()
    walk = Task("Morning walk", 30, "high", preferred_time="08:00")
    walk.mark_complete(date(2026, 7, 7))
    litter = Task("Litter box cleaning", 15, "medium", preferred_time="09:00")
    biscuit.add_task(walk)
    whiskers.add_task(litter)

    assert owner.get_tasks(pet=biscuit) == [walk]
    assert owner.get_tasks(completed=True) == [walk]
    assert owner.get_tasks(completed=False) == [litter]


# --- Sorting correctness -----------------------------------------------


def test_sort_by_time_returns_chronological_order_regardless_of_input_order():
    tasks = [
        Task("Evening walk", 20, "medium", preferred_time="18:00"),
        Task("Breakfast", 10, "high", preferred_time="07:00"),
        Task("Lunch", 10, "medium", preferred_time="12:00"),
    ]

    scheduler = Scheduler(available_time_minutes=120)
    ordered = scheduler.sort_by_time(tasks)

    assert [task.description for task in ordered] == ["Breakfast", "Lunch", "Evening walk"]


def test_sort_by_time_places_tasks_without_preferred_time_last():
    tasks = [
        Task("Play session", 15, "low"),  # no preferred_time
        Task("Breakfast", 10, "high", preferred_time="07:00"),
    ]

    scheduler = Scheduler(available_time_minutes=120)
    ordered = scheduler.sort_by_time(tasks)

    assert [task.description for task in ordered] == ["Breakfast", "Play session"]


# --- Recurrence logic ----------------------------------------------------


def test_completing_daily_task_creates_task_due_the_next_day():
    pet = Pet("Biscuit", "Dog")
    task = Task("Morning walk", 30, "high", recurrence="daily", preferred_time="08:00")
    pet.add_task(task)

    next_task = task.mark_complete(date(2026, 7, 7))

    assert next_task.due_date == date(2026, 7, 8)
    assert next_task.completed is False
    assert next_task.id != task.id
    assert len(pet.tasks) == 2  # original + newly spawned occurrence


# --- Conflict detection ---------------------------------------------------


def test_scheduler_flags_tasks_at_the_exact_same_preferred_time():
    owner, biscuit, whiskers = make_owner_with_pets()
    walk = Task("Morning walk", 30, "high", preferred_time="08:00")
    feeding = Task("Feeding", 15, "medium", preferred_time="08:00")
    biscuit.add_task(walk)
    whiskers.add_task(feeding)

    scheduler = Scheduler(available_time_minutes=120)
    warnings = scheduler.detect_conflicts(owner.get_all_tasks())
    plan = scheduler.build_plan(owner, date(2026, 7, 7))

    assert len(warnings) == 1
    assert "Morning walk" in warnings[0] and "Feeding" in warnings[0]
    # Higher priority ("high") wins the slot; the duplicate-time task is skipped.
    assert [task.description for task in plan.scheduled_tasks] == ["Morning walk"]
    assert [task.description for task in plan.skipped_tasks] == ["Feeding"]


def test_back_to_back_tasks_do_not_conflict():
    # Walk runs 08:00-08:30, feeding starts exactly when it ends.
    walk = Task("Morning walk", 30, "high", preferred_time="08:00")
    feeding = Task("Feeding", 10, "medium", preferred_time="08:30")

    assert not walk.conflicts_with(feeding)


# --- Edge cases: empty input ------------------------------------------------


def test_build_plan_for_owner_with_no_pets_returns_empty_plan():
    owner = Owner("Sam")
    scheduler = Scheduler(available_time_minutes=60)

    plan = scheduler.build_plan(owner, date(2026, 7, 7))

    assert plan.scheduled_tasks == []
    assert plan.skipped_tasks == []
    assert plan.summary() == "No tasks scheduled for 2026-07-07."


def test_build_plan_for_pet_with_no_tasks_returns_empty_plan():
    owner, biscuit, whiskers = make_owner_with_pets()
    scheduler = Scheduler(available_time_minutes=60)

    plan = scheduler.build_plan(owner, date(2026, 7, 7))

    assert plan.scheduled_tasks == []
    assert plan.skipped_tasks == []


# --- Edge cases: time-budget boundary ---------------------------------------


def test_task_that_exactly_fills_time_budget_is_scheduled():
    owner, biscuit, _ = make_owner_with_pets()
    biscuit.add_task(Task("Long walk", 60, "high", preferred_time="08:00"))

    scheduler = Scheduler(available_time_minutes=60)
    plan = scheduler.build_plan(owner, date(2026, 7, 7))

    assert len(plan.scheduled_tasks) == 1
    assert plan.skipped_tasks == []


# --- Edge cases: due-date boundary -------------------------------------------


def test_task_due_exactly_on_plan_date_is_included():
    task = Task("Vet appointment", 30, "high", due_date=date(2026, 7, 7))

    assert task.is_due(date(2026, 7, 7)) is True
    assert task.is_due(date(2026, 7, 6)) is False


# --- Next available slot ----------------------------------------------------


def test_find_next_available_slot_before_first_busy_task():
    tasks = [Task("Morning walk", 30, "high", preferred_time="09:00")]
    scheduler = Scheduler(available_time_minutes=120)

    slot = scheduler.find_next_available_slot(tasks, duration_minutes=20)

    assert slot == "08:00"  # fits before the 09:00 task, starting at day_start


def test_find_next_available_slot_fits_in_a_gap_between_tasks():
    tasks = [
        Task("Morning walk", 30, "high", preferred_time="08:00"),
        Task("Lunch", 15, "medium", preferred_time="09:00"),
    ]
    scheduler = Scheduler(available_time_minutes=120)

    slot = scheduler.find_next_available_slot(tasks, duration_minutes=20)

    assert slot == "08:30"  # right after the walk ends, before lunch starts


def test_find_next_available_slot_returns_none_when_day_is_full():
    tasks = [Task("All day training", 720, "high", preferred_time="08:00")]
    scheduler = Scheduler(available_time_minutes=720)

    slot = scheduler.find_next_available_slot(
        tasks, duration_minutes=30, day_start="08:00", day_end="20:00"
    )

    assert slot is None


def test_find_next_available_slot_ignores_tasks_without_preferred_time():
    tasks = [Task("Playtime", 15, "low")]  # no preferred_time
    scheduler = Scheduler(available_time_minutes=120)

    slot = scheduler.find_next_available_slot(tasks, duration_minutes=20)

    assert slot == "08:00"
