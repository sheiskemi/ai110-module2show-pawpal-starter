"""Logic layer for PawPal+.

Class skeletons generated from diagrams/uml.mmd. No scheduling logic yet —
attributes and method stubs only.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class Owner:
    name: str
    preferences: dict = field(default_factory=dict)


@dataclass
class Task:
    title: str
    duration_minutes: int
    priority: str
    category: str
    recurrence: str = "daily"
    preferred_time: Optional[str] = None

    def conflicts_with(self, other: "Task") -> bool:
        raise NotImplementedError


@dataclass
class Pet:
    name: str
    species: str
    owner: Owner
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        raise NotImplementedError

    def edit_task(self, task_id: int, updates: dict) -> None:
        raise NotImplementedError

    def remove_task(self, task_id: int) -> None:
        raise NotImplementedError


@dataclass
class DailyPlan:
    pet: Pet
    date: date
    scheduled_tasks: list[Task] = field(default_factory=list)
    skipped_tasks: list[Task] = field(default_factory=list)

    def total_time_used(self) -> int:
        raise NotImplementedError

    def summary(self) -> str:
        raise NotImplementedError

    def explanation(self) -> str:
        raise NotImplementedError


class Scheduler:
    def __init__(self, available_time_minutes: int, tasks: list[Task]):
        self.available_time_minutes = available_time_minutes
        self.tasks = tasks

    def build_plan(self, pet: Pet, plan_date: date) -> DailyPlan:
        raise NotImplementedError

    def explain(self, plan: DailyPlan) -> str:
        raise NotImplementedError
