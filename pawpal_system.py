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
from datetime import date, timedelta

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
        start: Optional preferred start time as "HH:MM" (24-hour). Empty
            means "any time" — such tasks are packed by priority only and
            can never raise a time conflict.
        weekday: For "weekly" tasks, which day it lands on (0=Mon .. 6=Sun).
            None means "any day" (a weekly task with no weekday still shows
            up every day, so nothing silently disappears).
        due_date: The calendar day this task is scheduled for. Optional —
            tasks without one fall back to recurrence-based "due today" logic.
            When a recurring task is completed, the next instance is created
            with this advanced to the next occurrence.
        completed: Whether the task is already done today.
        pet: Back-reference to the owning pet, set by ``Pet.add_task``.
    """

    description: str
    duration: int
    recurrence: str = ""
    priority: str = "medium"
    start: str = ""
    weekday: int | None = None
    due_date: date | None = None
    completed: bool = False
    pet: Pet | None = None

    def is_recurring(self) -> bool:
        """True if this task repeats on a schedule."""
        return bool(self.recurrence)

    def priority_rank(self) -> int:
        """Numeric rank for sorting; unknown priorities rank lowest."""
        return PRIORITY_ORDER.get(self.priority.lower(), 0)

    def start_minutes(self) -> int | None:
        """Convert the ``start`` time to minutes past midnight.

        Parsing time into an integer lets the scheduler sort and compare
        times with plain arithmetic instead of string juggling.

        Returns:
            Minutes since 00:00 (e.g. "09:30" -> 570), or None if the task
            has no start time set.
        """
        if not self.start:
            return None
        hours, minutes = self.start.split(":")
        return int(hours) * 60 + int(minutes)

    def end_minutes(self) -> int | None:
        """The moment the task finishes, in minutes past midnight.

        Returns:
            ``start_minutes() + duration``, or None if the task has no start
            time (an untimed task has no end either).
        """
        start = self.start_minutes()
        return None if start is None else start + self.duration

    def due_today(self, today: date | None = None) -> bool:
        """Whether this task belongs on today's plan.

        If the task has an explicit ``due_date``, it is due once today has
        reached (or passed) that date. Otherwise we fall back to recurrence:
        daily and one-off tasks are always in play, and a "weekly" task only
        surfaces on its ``weekday`` (no weekday set → due every day, so
        nothing is accidentally hidden).

        Args:
            today: The day to test against; defaults to ``date.today()``.

        Returns:
            True if the task should appear on ``today``'s plan.
        """
        if today is None:
            today = date.today()
        if self.due_date is not None:
            return self.due_date <= today
        if self.recurrence.lower() == "weekly" and self.weekday is not None:
            return today.weekday() == self.weekday
        return True

    def next_occurrence(self, today: date | None = None) -> Task | None:
        """Build the next instance of a recurring task, or None for one-offs.

        Daily tasks advance by one day, weekly tasks by seven (which keeps
        the same weekday). Date math uses ``timedelta`` so month/year
        rollovers are handled correctly. The new task starts uncompleted.

        Args:
            today: Fallback "current day", used only when this task has no
                ``due_date`` yet; defaults to ``date.today()``.

        Returns:
            A new uncompleted ``Task`` whose ``due_date`` is this task's
            due_date (or ``today``) plus the recurrence step, or None if the
            task is a one-off (no recurrence, nothing to repeat).
        """
        step_days = {"daily": 1, "weekly": 7}.get(self.recurrence.lower())
        if step_days is None:
            return None  # one-off tasks don't repeat
        base = self.due_date or today or date.today()
        return Task(
            description=self.description,
            duration=self.duration,
            recurrence=self.recurrence,
            priority=self.priority,
            start=self.start,
            weekday=self.weekday,
            due_date=base + timedelta(days=step_days),
        )

    def mark_done(self) -> None:
        """Mark this task as completed (just flips the flag)."""
        self.completed = True

    def complete(self, today: date | None = None) -> Task | None:
        """Mark done and, for recurring tasks, auto-create the next instance.

        The follow-up task is attached to the same pet (via ``next_occurrence``)
        so it shows up on a future day's plan.

        Args:
            today: Passed through to ``next_occurrence`` for the date math;
                defaults to ``date.today()``.

        Returns:
            The newly created follow-up ``Task``, or None if this was a
            one-off (nothing to repeat).
        """
        self.mark_done()
        follow_up = self.next_occurrence(today)
        if follow_up is not None and self.pet is not None:
            self.pet.add_task(follow_up)
        return follow_up


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

    def remove_pet(self, pet: Pet) -> bool:
        """Unregister a pet (and, with it, all of its tasks).

        Args:
            pet: The pet to remove.

        Returns:
            True if the pet was found and removed, False if it wasn't
            registered with this owner.
        """
        if pet in self.pets:
            self.pets.remove(pet)
            return True
        return False

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
    conflicts: list[tuple[Task, Task]] = field(default_factory=list)

    @property
    def total_minutes(self) -> int:
        """Total time the scheduled tasks will take."""
        return sum(t.duration for t in self.scheduled)

    def skipped_high_priority(self) -> list[Task]:
        """High-priority tasks that did not make it into the plan."""
        return [t for t in self.skipped if t.priority.lower() == "high"]

    def has_conflicts(self) -> bool:
        """True if any two scheduled tasks overlap in time."""
        return bool(self.conflicts)


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

    def sort_by_time(self, tasks: list[Task]) -> list[Task]:
        """Order tasks chronologically for a day-timeline view.

        The sort key ``(start is None, start)`` places timed tasks first
        (earliest → latest); because ``False`` sorts before ``True``, untimed
        tasks fall to the end while keeping their original relative order.

        Args:
            tasks: Tasks to order (not mutated).

        Returns:
            A new list sorted by start time, untimed tasks last.
        """
        return sorted(
            tasks,
            key=lambda t: (t.start_minutes() is None, t.start_minutes() or 0),
        )

    def filter_by_pet(self, tasks: list[Task], pet_name: str) -> list[Task]:
        """Keep only the tasks belonging to a given pet.

        Args:
            tasks: Tasks to filter.
            pet_name: Name of the pet whose tasks to keep.

        Returns:
            A new list of tasks whose owning pet is named ``pet_name``.
        """
        return [t for t in tasks if t.pet is not None and t.pet.name == pet_name]

    def filter_by_status(self, tasks: list[Task], completed: bool = False) -> list[Task]:
        """Keep only the tasks matching a completion status.

        Args:
            tasks: Tasks to filter.
            completed: Status to match; default False keeps not-yet-done tasks.

        Returns:
            A new list of tasks whose ``completed`` flag equals ``completed``.
        """
        return [t for t in tasks if t.completed == completed]

    def due_tasks(self, tasks: list[Task], today: date | None = None) -> list[Task]:
        """Keep only the tasks that are due today (honours recurrence).

        Args:
            tasks: Tasks to filter.
            today: Day to test against; defaults to ``date.today()``.

        Returns:
            A new list of the tasks for which ``Task.due_today(today)`` is True.
        """
        return [t for t in tasks if t.due_today(today)]

    def detect_conflicts(self, tasks: list[Task]) -> list[tuple[Task, Task]]:
        """Find pairs of timed tasks whose start–end intervals overlap.

        Only tasks with a ``start`` time can conflict; untimed tasks are
        ignored. Tasks are sorted by start time, then every pair is compared:
        two overlap when each starts before the other ends
        (``a.start < b.end and b.start < a.end``). Comparing all pairs keeps
        the check correct even when one long task overlaps several others.

        Args:
            tasks: Tasks to check; those without a start time are skipped.

        Returns:
            A list of overlapping ``(earlier, later)`` task pairs, each pair
            reported once and ordered by start time. Empty if none overlap.
        """
        timed = self.sort_by_time([t for t in tasks if t.start_minutes() is not None])
        conflicts: list[tuple[Task, Task]] = []
        for i in range(len(timed)):
            for j in range(i + 1, len(timed)):
                a, b = timed[i], timed[j]
                if a.start_minutes() < b.end_minutes() and b.start_minutes() < a.end_minutes():
                    conflicts.append((a, b))
        return conflicts

    def conflict_warnings(self, tasks: list[Task]) -> list[str]:
        """Human-readable warnings for overlapping tasks (same or different pets).

        Lightweight and non-fatal: it formats the pairs from
        ``detect_conflicts`` into strings so the caller can print warnings
        instead of the program crashing on a double-booking.

        Args:
            tasks: Tasks to check for overlaps.

        Returns:
            A list of formatted warning strings naming each conflicting pair
            and their pets; empty when there are no conflicts.
        """
        messages: list[str] = []
        for a, b in self.detect_conflicts(tasks):
            pet_a = a.pet.name if a.pet else "household"
            pet_b = b.pet.name if b.pet else "household"
            messages.append(
                f"⚠️  Conflict: '{a.description}' ({pet_a}, {a.start}) overlaps "
                f"'{b.description}' ({pet_b}, {b.start})"
            )
        return messages

    def pack_into_budget(self, tasks: list[Task], budget: int) -> tuple[list[Task], list[Task]]:
        """Pack tasks (in the order given) into the time budget.

        Walks the list once (greedy first-fit), keeping a running remaining
        budget: each task is scheduled if it still fits, otherwise skipped.
        Named to distinguish it from the ``filter_by_*`` methods, which only
        keep matching tasks — this one actually allocates the budget.

        Args:
            tasks: Tasks in the order they should be considered (usually
                priority-sorted by ``sort_tasks`` first).
            budget: Total minutes available.

        Returns:
            A ``(scheduled, skipped)`` tuple: tasks kept because they fit the
            remaining minutes, and those set aside because they did not.
        """
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

    def generate_plan(self, owner: Owner, today: date | None = None) -> Plan:
        """Build a Plan of the highest-priority tasks that fit today's budget.

        Pipeline: gather pending tasks across all pets → drop the ones not
        due today (recurrence) → sort by priority → pack into the time budget
        → flag any time overlaps among the scheduled tasks.

        Args:
            owner: The owner whose pets' tasks are scheduled. The budget is
                ``self.time_budget`` if set, else ``owner.available_time``.
            today: Day to schedule for; defaults to ``date.today()``. Drives
                the recurrence (due-today) filtering.

        Returns:
            A ``Plan`` holding the scheduled tasks, the skipped tasks, and any
            detected time conflicts among the scheduled ones.
        """
        budget = self.time_budget if self.time_budget is not None else owner.available_time
        due = self.due_tasks(owner.pending_tasks(), today)
        ordered = self.sort_tasks(due)
        scheduled, skipped = self.pack_into_budget(ordered, budget)
        conflicts = self.detect_conflicts(scheduled)
        return Plan(scheduled=scheduled, skipped=skipped, conflicts=conflicts)
