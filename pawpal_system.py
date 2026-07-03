"""PawPal+ logic layer.

Backend classes for planning a pet owner's daily care tasks.
Mirrors the UML design in diagrams/uml.mmd (Owner, Pet, Task, Scheduler).

Ownership model:
    Owner  --has-->  Pet  --has-->  Task
The Owner manages pets; each Pet owns its own tasks; the Scheduler reaches
across all of an owner's pets to build the day's plan.

This module has no Streamlit / UI dependencies so it can be tested in
isolation with pytest.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Priority ranking: higher number == more important (sorts first).
PRIORITY_ORDER = {"high": 3, "medium": 2, "low": 1}


@dataclass
class Task:
    """A single care activity (walk, feeding, meds, etc.).

    Attributes:
        description: What the task is.
        duration: How long it takes, in minutes ("time").
        recurrence: How often it repeats — e.g. "daily", "weekly", or ""
            for a one-off ("frequency").
        priority: One of "high", "medium", "low"; drives scheduling order.
        completed: Whether the task is already done today.
        pet: Back-reference to the owning pet, set by ``Pet.add_task``.
    """

    description: str
    duration: int
    recurrence: str = ""
    priority: str = "medium"
    completed: bool = False
    pet: Pet | None = None

    def is_recurring(self) -> bool:
        """True if this task repeats on a schedule."""
        return bool(self.recurrence)

    def priority_rank(self) -> int:
        """Numeric rank for sorting; unknown priorities rank lowest."""
        return PRIORITY_ORDER.get(self.priority.lower(), 0)

    def mark_done(self) -> None:
        """Mark this task as completed."""
        self.completed = True


@dataclass
class Pet:
    """A pet and the care tasks that belong to it."""

    name: str
    species: str = ""
    breed: str = ""
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Attach a care task to this pet and set its back-reference."""
        task.pet = self
        self.tasks.append(task)

    def pending_tasks(self) -> list[Task]:
        """Tasks for this pet that still need to be done."""
        return [t for t in self.tasks if not t.completed]


@dataclass
class Owner:
    """The pet owner. Manages the pets and exposes all their tasks."""

    name: str
    preferences: str = ""
    available_time: int = 0  # minutes available today
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Register a pet with the owner."""
        self.pets.append(pet)

    def all_tasks(self) -> list[Task]:
        """Every task across all of the owner's pets."""
        return [task for pet in self.pets for task in pet.tasks]

    def pending_tasks(self) -> list[Task]:
        """Every not-yet-completed task across all pets."""
        return [t for t in self.all_tasks() if not t.completed]


@dataclass
class Plan:
    """The outcome of scheduling: what fit today and what didn't.

    ``skipped`` is kept (rather than thrown away) so the UI can warn when a
    task — especially a high-priority one — could not fit in the budget.
    """

    scheduled: list[Task] = field(default_factory=list)
    skipped: list[Task] = field(default_factory=list)

    @property
    def total_minutes(self) -> int:
        """Total time the scheduled tasks will take."""
        return sum(t.duration for t in self.scheduled)

    def skipped_high_priority(self) -> list[Task]:
        """High-priority tasks that did not make it into the plan."""
        return [t for t in self.skipped if t.priority.lower() == "high"]


class Scheduler:
    """The "brain": retrieves, organizes, and manages tasks across pets.

    Kept separate from Owner so the scheduling logic (sorting, filtering)
    can be unit-tested on its own.
    """

    def __init__(self, time_budget: int | None = None) -> None:
        """Create a scheduler; if no budget is given, fall back to the owner's available_time."""
        self.time_budget = time_budget

    def sort_tasks(self, tasks: list[Task]) -> list[Task]:
        """Sort by priority (high first), then shorter duration first."""
        return sorted(
            tasks,
            key=lambda t: (-t.priority_rank(), t.duration),
        )

    def filter_tasks(self, tasks: list[Task], budget: int) -> tuple[list[Task], list[Task]]:
        """Split tasks (in the order given) into those that fit the budget and those that don't."""
        scheduled: list[Task] = []
        skipped: list[Task] = []
        remaining = budget
        for task in tasks:
            if task.duration <= remaining:
                scheduled.append(task)
                remaining -= task.duration
            else:
                skipped.append(task)
        return scheduled, skipped

    def generate_plan(self, owner: Owner) -> Plan:
        """Build a Plan of the highest-priority pending tasks (across all pets) that fit the budget."""
        budget = self.time_budget if self.time_budget is not None else owner.available_time
        ordered = self.sort_tasks(owner.pending_tasks())
        scheduled, skipped = self.filter_tasks(ordered, budget)
        return Plan(scheduled=scheduled, skipped=skipped)
