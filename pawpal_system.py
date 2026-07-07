"""Logic layer for PawPal+.

Classes: Task, Pet, Owner, Scheduler (plus DailyPlan, the Scheduler's output).
"""

import uuid
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


@dataclass
class Task:
    """A single care activity for a pet."""

    description: str
    duration_minutes: int
    priority: str  # "high" | "medium" | "low"
    category: str = "general"  # e.g., walk, feeding, meds, enrichment, grooming
    recurrence: str = "daily"  # e.g., daily, weekly
    preferred_time: Optional[str] = None  # e.g., "08:00"
    completed: bool = False
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    # Back-reference to the owning Pet, set by Pet.add_task(). Excluded from
    # repr/eq so printing/comparing a Task doesn't recurse into its Pet.
    pet: Optional["Pet"] = field(default=None, repr=False, compare=False)

    def mark_complete(self) -> None:
        """Mark this task as completed."""
        self.completed = True

    def mark_incomplete(self) -> None:
        """Mark this task as not completed."""
        self.completed = False

    def conflicts_with(self, other: "Task") -> bool:
        """True if both tasks have a preferred_time and their durations overlap."""
        if self.preferred_time is None or other.preferred_time is None:
            return False

        def to_minutes(hhmm: str) -> int:
            hours, minutes = hhmm.split(":")
            return int(hours) * 60 + int(minutes)

        start_a = to_minutes(self.preferred_time)
        end_a = start_a + self.duration_minutes
        start_b = to_minutes(other.preferred_time)
        end_b = start_b + other.duration_minutes
        return start_a < end_b and start_b < end_a


@dataclass
class Pet:
    """A pet and the list of care tasks assigned to it."""

    name: str
    species: str
    owner: Optional["Owner"] = None
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


@dataclass
class DailyPlan:
    """The result of running the Scheduler for an owner on a given date."""

    owner: Owner
    date: date
    scheduled_tasks: list[Task] = field(default_factory=list)
    skipped_tasks: list[Task] = field(default_factory=list)

    def total_time_used(self) -> int:
        """Return the total minutes used by all scheduled tasks."""
        return sum(task.duration_minutes for task in self.scheduled_tasks)

    def summary(self) -> str:
        """Return a human-readable, ordered listing of the day's scheduled tasks."""
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
            lines.append(f"Skipped {len(self.skipped_tasks)} task(s) due to time constraints:")
            for task in self.skipped_tasks:
                pet_name = task.pet.name if task.pet else "unknown pet"
                lines.append(
                    f"  - {task.description} ({pet_name}, priority: {task.priority})"
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

    def build_plan(self, owner: Owner, plan_date: date) -> DailyPlan:
        """Build a DailyPlan by greedily fitting the owner's tasks, highest priority first, into the time budget."""
        candidate_tasks = [task for task in owner.get_all_tasks() if not task.completed]
        candidate_tasks.sort(key=lambda task: PRIORITY_ORDER.get(task.priority, 99))

        scheduled: list[Task] = []
        skipped: list[Task] = []
        time_used = 0
        for task in candidate_tasks:
            if time_used + task.duration_minutes <= self.available_time_minutes:
                scheduled.append(task)
                time_used += task.duration_minutes
            else:
                skipped.append(task)

        return DailyPlan(
            owner=owner,
            date=plan_date,
            scheduled_tasks=scheduled,
            skipped_tasks=skipped,
        )

    def explain(self, plan: DailyPlan) -> str:
        """Return the reasoning behind a previously built DailyPlan."""
        return plan.explanation()
