"""Logic layer for PawPal+.

Classes: Task, Pet, Owner, Scheduler (plus DailyPlan, the Scheduler's output).
"""

import uuid
from dataclasses import dataclass, field
from datetime import date, timedelta
from itertools import combinations
from typing import Optional

PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}

# How far out the next occurrence of a recurring task is scheduled, once the
# current occurrence is marked complete.
RECURRENCE_INTERVALS = {
    "daily": timedelta(days=1),
    "weekly": timedelta(weeks=1),
}


def _time_to_minutes(hhmm: str) -> int:
    """Convert a "HH:MM" string into minutes since midnight."""
    hours, minutes = hhmm.split(":")
    return int(hours) * 60 + int(minutes)


def _minutes_to_time(total_minutes: int) -> str:
    """Convert minutes since midnight into a zero-padded "HH:MM" string."""
    hours, minutes = divmod(total_minutes, 60)
    return f"{hours:02d}:{minutes:02d}"


@dataclass
class Task:
    """A single care activity for a pet."""

    description: str
    duration_minutes: int
    priority: str  # "high" | "medium" | "low"
    category: str = "general"  # e.g., walk, feeding, meds, enrichment, grooming
    recurrence: str = "daily"  # "once" | "daily" | "weekly"
    preferred_time: Optional[str] = None  # e.g., "08:00"
    due_date: Optional[date] = None  # calendar date this occurrence is due; None = due immediately
    completed: bool = False
    last_completed_date: Optional[date] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    # Back-reference to the owning Pet, set by Pet.add_task(). Excluded from
    # repr/eq so printing/comparing a Task doesn't recurse into its Pet.
    pet: Optional["Pet"] = field(default=None, repr=False, compare=False)

    def mark_complete(self, on_date: Optional[date] = None) -> Optional["Task"]:
        """Mark this task completed as of on_date (defaults to today).

        For "daily"/"weekly" tasks, also creates and attaches (to the same
        pet, if any) a new Task instance for the next occurrence, due
        on_date + the recurrence interval. Returns that new Task, or None if
        this task doesn't recur.
        """
        completed_on = on_date or date.today()
        self.completed = True
        self.last_completed_date = completed_on

        interval = RECURRENCE_INTERVALS.get(self.recurrence)
        if interval is None:
            return None

        next_task = Task(
            description=self.description,
            duration_minutes=self.duration_minutes,
            priority=self.priority,
            category=self.category,
            recurrence=self.recurrence,
            preferred_time=self.preferred_time,
            due_date=completed_on + interval,
        )
        if self.pet is not None:
            self.pet.add_task(next_task)
        return next_task

    def mark_incomplete(self) -> None:
        """Mark this task as not completed and clear its last completion date."""
        self.completed = False
        self.last_completed_date = None

    def is_due(self, on_date: date) -> bool:
        """True if this task should appear in a plan for on_date."""
        if self.completed:
            return False
        if self.due_date is not None:
            return on_date >= self.due_date
        return True

    def conflicts_with(self, other: "Task") -> bool:
        """True if both tasks have a preferred_time and their durations overlap."""
        if self.preferred_time is None or other.preferred_time is None:
            return False
        start_a = _time_to_minutes(self.preferred_time)
        end_a = start_a + self.duration_minutes
        start_b = _time_to_minutes(other.preferred_time)
        end_b = start_b + other.duration_minutes
        return start_a < end_b and start_b < end_a


@dataclass
class Pet:
    """A pet and the list of care tasks assigned to it."""

    name: str
    species: str
    # compare=False avoids infinite recursion: Owner's default __eq__ compares
    # its pets list, which would compare each Pet's owner right back.
    owner: Optional["Owner"] = field(default=None, repr=False, compare=False)
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Attach a task to this pet and link the task back to it."""
        task.pet = self
        self.tasks.append(task)

    def edit_task(self, task_id: str, updates: dict) -> None:
        """Update fields on the task matching task_id."""
        task = self._find_task(task_id)
        for key, value in updates.items():
            setattr(task, key, value)

    def remove_task(self, task_id: str) -> None:
        """Remove the task matching task_id from this pet's task list."""
        self._find_task(task_id)  # raises if missing
        self.tasks = [task for task in self.tasks if task.id != task_id]

    def _find_task(self, task_id: str) -> Task:
        """Return the task matching task_id or raise ValueError if not found."""
        for task in self.tasks:
            if task.id == task_id:
                return task
        raise ValueError(f"No task with id {task_id!r} for pet {self.name!r}")


@dataclass
class Owner:
    """A pet owner who manages one or more pets."""

    name: str
    preferences: dict = field(default_factory=dict)
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to this owner and link the pet back to it."""
        pet.owner = self
        self.pets.append(pet)

    def get_all_tasks(self) -> list[Task]:
        """Flatten tasks across all of this owner's pets.

        Scheduler goes through this method rather than reading owner.pets
        directly, so Owner stays the single source of truth for how its
        pets' tasks are aggregated.
        """
        return [task for pet in self.pets for task in pet.tasks]

    def get_tasks(
        self,
        pet: Optional[Pet] = None,
        completed: Optional[bool] = None,
        category: Optional[str] = None,
    ) -> list[Task]:
        """Return tasks across all pets, optionally filtered by pet, status, or category."""
        tasks = self.get_all_tasks()
        if pet is not None:
            tasks = [task for task in tasks if task.pet is pet]
        if completed is not None:
            tasks = [task for task in tasks if task.completed == completed]
        if category is not None:
            tasks = [task for task in tasks if task.category == category]
        return tasks


@dataclass
class DailyPlan:
    """The result of running the Scheduler for an owner on a given date."""

    owner: Owner
    date: date
    scheduled_tasks: list[Task] = field(default_factory=list)
    skipped_tasks: list[Task] = field(default_factory=list)
    # Maps task.id -> "time" | "conflict", explaining why a task was skipped.
    skip_reasons: dict[str, str] = field(default_factory=dict)

    def total_time_used(self) -> int:
        """Return the total minutes used by all scheduled tasks."""
        return sum(task.duration_minutes for task in self.scheduled_tasks)

    def summary(self) -> str:
        """Return a human-readable, chronologically ordered listing of the day's scheduled tasks."""
        if not self.scheduled_tasks:
            return f"No tasks scheduled for {self.date}."
        lines = [f"Plan for {self.owner.name} on {self.date}:"]
        for task in self.scheduled_tasks:
            pet_name = task.pet.name if task.pet else "unknown pet"
            time_label = task.preferred_time or "anytime"
            lines.append(
                f"  {time_label} - {task.description} ({pet_name}, "
                f"{task.duration_minutes} min) [priority: {task.priority}]"
            )
        return "\n".join(lines)

    def explanation(self) -> str:
        """Return a human-readable explanation of what was scheduled or skipped, and why."""
        lines = [
            f"Scheduled {len(self.scheduled_tasks)} task(s) totaling "
            f"{self.total_time_used()} minutes."
        ]
        if self.skipped_tasks:
            lines.append(f"Skipped {len(self.skipped_tasks)} task(s):")
            for task in self.skipped_tasks:
                pet_name = task.pet.name if task.pet else "unknown pet"
                reason = self.skip_reasons.get(task.id, "time")
                reason_label = (
                    "not enough time left" if reason == "time" else "conflicts with another scheduled task"
                )
                lines.append(
                    f"  - {task.description} ({pet_name}, priority: {task.priority}) - {reason_label}"
                )
        return "\n".join(lines)


class Scheduler:
    """Retrieves tasks across an owner's pets and organizes them into a plan.

    Stateless by design: it holds only the available time budget, and reads
    tasks fresh from the Owner on every build_plan() call rather than caching
    its own task list, so there is a single source of truth for "what tasks
    exist" (Owner/Pet) and Scheduler is purely responsible for "how they get
    ordered into a day."
    """

    def __init__(self, available_time_minutes: int):
        """Store the daily time budget used when building plans."""
        self.available_time_minutes = available_time_minutes

    def sort_by_time(self, tasks: list[Task]) -> list[Task]:
        """Return tasks sorted chronologically by preferred_time.

        "HH:MM" strings are zero-padded and fixed-width, so plain string
        comparison already matches chronological order (e.g. "08:00" <
        "09:05" lexicographically, same as it would numerically) - no need to
        parse into minutes just to sort. Tasks with no preferred_time sort last.
        """
        return sorted(tasks, key=lambda task: task.preferred_time or "99:99")

    def filter_tasks(
        self,
        tasks: list[Task],
        completed: Optional[bool] = None,
        pet_name: Optional[str] = None,
    ) -> list[Task]:
        """Return tasks filtered by completion status and/or owning pet's name."""
        filtered = tasks
        if completed is not None:
            filtered = [task for task in filtered if task.completed == completed]
        if pet_name is not None:
            filtered = [task for task in filtered if task.pet and task.pet.name == pet_name]
        return filtered

    def detect_conflicts(self, tasks: list[Task]) -> list[str]:
        """Scan tasks pairwise for overlapping preferred_times and return a warning
        message per conflicting pair, across the same pet or different pets.

        Lightweight by design: O(n^2) pairwise comparison, fine for the small
        number of tasks a single owner schedules in a day. Returns warning
        strings rather than raising, so a scheduling run can surface conflicts
        without crashing or blocking the rest of the plan.
        """
        warnings: list[str] = []
        for task_a, task_b in combinations(tasks, 2):
            if not task_a.conflicts_with(task_b):
                continue
            pet_a = task_a.pet.name if task_a.pet else "unknown pet"
            pet_b = task_b.pet.name if task_b.pet else "unknown pet"
            warnings.append(
                f"Warning: '{task_a.description}' ({pet_a}, {task_a.preferred_time}) "
                f"conflicts with '{task_b.description}' ({pet_b}, {task_b.preferred_time})"
            )
        return warnings

    def build_plan(self, owner: Owner, plan_date: date) -> DailyPlan:
        """Build a DailyPlan: due tasks, highest priority first, greedily fit into the
        time budget while skipping anything that conflicts with an already-scheduled task."""
        candidate_tasks = [task for task in owner.get_all_tasks() if task.is_due(plan_date)]
        candidate_tasks.sort(key=lambda task: PRIORITY_ORDER.get(task.priority, 99))

        scheduled: list[Task] = []
        skipped: list[Task] = []
        skip_reasons: dict[str, str] = {}
        time_used = 0
        for task in candidate_tasks:
            if any(task.conflicts_with(other) for other in scheduled):
                skipped.append(task)
                skip_reasons[task.id] = "conflict"
            elif time_used + task.duration_minutes <= self.available_time_minutes:
                scheduled.append(task)
                time_used += task.duration_minutes
            else:
                skipped.append(task)
                skip_reasons[task.id] = "time"

        # Selection order above is priority-driven; display order should read
        # chronologically.
        return DailyPlan(
            owner=owner,
            date=plan_date,
            scheduled_tasks=self.sort_by_time(scheduled),
            skipped_tasks=skipped,
            skip_reasons=skip_reasons,
        )

    def explain(self, plan: DailyPlan) -> str:
        """Return the reasoning behind a previously built DailyPlan."""
        return plan.explanation()

    def find_next_available_slot(
        self,
        tasks: list[Task],
        duration_minutes: int,
        day_start: str = "08:00",
        day_end: str = "20:00",
    ) -> Optional[str]:
        """Return the earliest "HH:MM" start time of at least duration_minutes
        that doesn't overlap any of the given tasks' preferred_time windows,
        searching within [day_start, day_end).

        Tasks without a preferred_time are ignored (they aren't "busy" time
        yet). Returns None if no gap of that size exists in the day. Useful
        for suggesting a preferred_time for a new task rather than only
        reacting to conflicts after the fact.
        """
        busy_windows = sorted(
            (
                _time_to_minutes(task.preferred_time),
                _time_to_minutes(task.preferred_time) + task.duration_minutes,
            )
            for task in tasks
            if task.preferred_time is not None
        )
        day_end_minutes = _time_to_minutes(day_end)

        cursor = _time_to_minutes(day_start)
        for busy_start, busy_end in busy_windows:
            if cursor + duration_minutes <= busy_start:
                return _minutes_to_time(cursor)
            cursor = max(cursor, busy_end)

        if cursor + duration_minutes <= day_end_minutes:
            return _minutes_to_time(cursor)
        return None
