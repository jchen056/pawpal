"""Tests for the PawPal+ logic layer.

Run from the project root with:

    pytest
"""

from pawpal_system import Owner, Pet, Plan, Scheduler, Task


# --- Task ------------------------------------------------------------------

def test_is_recurring():
    assert Task("Feed", 10, recurrence="daily").is_recurring() is True
    assert Task("Vet visit", 50).is_recurring() is False


def test_priority_rank_orders_high_above_low():
    assert Task("a", 5, priority="high").priority_rank() > Task("b", 5, priority="low").priority_rank()


def test_unknown_priority_ranks_lowest():
    assert Task("a", 5, priority="whatever").priority_rank() == 0


def test_mark_done():
    task = Task("Feed", 10)
    assert task.completed is False
    task.mark_done()
    assert task.completed is True


# --- Required simple tests -------------------------------------------------

def test_task_completion_changes_status():
    """Calling mark_done() flips the task from not-done to done."""
    task = Task("Feed", 10)
    assert task.completed is False  # before
    task.mark_done()
    assert task.completed is True   # after


def test_adding_task_increases_pet_task_count():
    """Adding a task to a Pet increases that pet's task count by one."""
    pet = Pet("Rex")
    before = len(pet.tasks)
    pet.add_task(Task("Walk", 20))
    assert len(pet.tasks) == before + 1


# --- Pet -------------------------------------------------------------------

def test_add_task_sets_back_reference():
    pet = Pet("Rex")
    task = Task("Walk", 20)
    pet.add_task(task)
    assert task.pet is pet
    assert pet.tasks == [task]


def test_pet_pending_tasks_excludes_completed():
    pet = Pet("Rex")
    pet.add_task(Task("Walk", 20))
    done = Task("Brush", 15, completed=True)
    pet.add_task(done)
    assert done not in pet.pending_tasks()
    assert len(pet.pending_tasks()) == 1


# --- Owner -----------------------------------------------------------------

def test_all_tasks_gathers_across_pets():
    owner = Owner("Jia")
    rex, milo = Pet("Rex"), Pet("Milo")
    owner.add_pet(rex)
    owner.add_pet(milo)
    rex.add_task(Task("Walk", 20))
    milo.add_task(Task("Feed", 10))
    assert len(owner.all_tasks()) == 2


def test_owner_pending_tasks_excludes_completed():
    owner = Owner("Jia")
    pet = Pet("Rex")
    owner.add_pet(pet)
    pet.add_task(Task("Walk", 20))
    pet.add_task(Task("Brush", 15, completed=True))
    assert len(owner.pending_tasks()) == 1


# --- Scheduler -------------------------------------------------------------

def test_sort_tasks_high_priority_then_shorter_first():
    low = Task("low", 5, priority="low")
    high_long = Task("high_long", 40, priority="high")
    high_short = Task("high_short", 10, priority="high")
    ordered = Scheduler().sort_tasks([low, high_long, high_short])
    assert ordered == [high_short, high_long, low]


def test_filter_tasks_splits_scheduled_and_skipped():
    a = Task("a", 30)
    b = Task("b", 40)  # won't fit after a
    c = Task("c", 20)  # fits in the leftover
    scheduled, skipped = Scheduler().filter_tasks([a, b, c], budget=50)
    assert scheduled == [a, c]
    assert skipped == [b]


def test_generate_plan_prioritizes_high_within_budget():
    owner = Owner("Jia", available_time=60)
    rex = Pet("Rex")
    owner.add_pet(rex)
    rex.add_task(Task("Vet visit", 50, priority="high"))
    rex.add_task(Task("Walk", 20, priority="low"))
    rex.add_task(Task("Feed", 10, priority="medium"))

    plan = Scheduler().generate_plan(owner)

    descriptions = [t.description for t in plan.scheduled]
    assert descriptions == ["Vet visit", "Feed"]
    assert [t.description for t in plan.skipped] == ["Walk"]
    assert plan.total_minutes == 60


def test_generate_plan_ignores_completed_tasks():
    owner = Owner("Jia", available_time=60)
    pet = Pet("Milo")
    owner.add_pet(pet)
    pet.add_task(Task("Brush", 15, completed=True))
    pet.add_task(Task("Feed", 10))

    plan = Scheduler().generate_plan(owner)

    assert [t.description for t in plan.scheduled] == ["Feed"]
    assert plan.skipped == []


def test_explicit_budget_overrides_available_time():
    owner = Owner("Jia", available_time=100)
    pet = Pet("Rex")
    owner.add_pet(pet)
    pet.add_task(Task("Long task", 60))

    plan = Scheduler(time_budget=30).generate_plan(owner)

    assert plan.scheduled == []
    assert len(plan.skipped) == 1


def test_zero_budget_schedules_nothing():
    owner = Owner("Jia", available_time=0)
    pet = Pet("Rex")
    owner.add_pet(pet)
    pet.add_task(Task("Walk", 20))

    plan = Scheduler().generate_plan(owner)

    assert plan.scheduled == []


# --- Plan ------------------------------------------------------------------

def test_plan_skipped_high_priority():
    high = Task("Vet visit", 50, priority="high")
    low = Task("Walk", 20, priority="low")
    plan = Plan(scheduled=[], skipped=[high, low])
    assert plan.skipped_high_priority() == [high]


def test_plan_total_minutes():
    plan = Plan(scheduled=[Task("a", 15), Task("b", 25)])
    assert plan.total_minutes == 40
