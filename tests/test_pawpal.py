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


def test_pack_into_budget_splits_scheduled_and_skipped():
    a = Task("a", 30)
    b = Task("b", 40)  # won't fit after a
    c = Task("c", 20)  # fits in the leftover
    scheduled, skipped = Scheduler().pack_into_budget([a, b, c], budget=50)
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


# --- Sorting by time -------------------------------------------------------

def test_start_and_end_minutes():
    task = Task("Vet", 50, start="09:00")
    assert task.start_minutes() == 540
    assert task.end_minutes() == 590


def test_untimed_task_has_no_minutes():
    task = Task("Feed", 10)
    assert task.start_minutes() is None
    assert task.end_minutes() is None


def test_sort_by_time_orders_timed_first_then_untimed():
    late = Task("late", 10, start="18:00")
    early = Task("early", 10, start="08:00")
    untimed = Task("untimed", 10)
    ordered = Scheduler().sort_by_time([untimed, late, early])
    assert ordered == [early, late, untimed]


# --- Filtering by pet / status ---------------------------------------------

def test_filter_by_pet():
    rex, milo = Pet("Rex"), Pet("Milo")
    walk = Task("Walk", 20)
    feed = Task("Feed", 10)
    rex.add_task(walk)
    milo.add_task(feed)
    assert Scheduler().filter_by_pet([walk, feed], "Rex") == [walk]


def test_filter_by_status_defaults_to_pending():
    done = Task("Brush", 15, completed=True)
    todo = Task("Walk", 20)
    assert Scheduler().filter_by_status([done, todo]) == [todo]
    assert Scheduler().filter_by_status([done, todo], completed=True) == [done]


# --- Recurring tasks -------------------------------------------------------

def test_daily_task_is_due_any_day():
    from datetime import date
    task = Task("Feed", 10, recurrence="daily")
    assert task.due_today(date(2026, 7, 3)) is True  # a Friday


def test_weekly_task_due_only_on_its_weekday():
    from datetime import date
    monday = date(2026, 7, 6)
    # weekday=0 is Monday; the task should fire on Monday, not on Friday.
    task = Task("Bath", 30, recurrence="weekly", weekday=0)
    assert task.due_today(monday) is True
    assert task.due_today(date(2026, 7, 3)) is False  # a Friday


def test_weekly_without_weekday_is_due_every_day():
    from datetime import date
    task = Task("Bath", 30, recurrence="weekly")
    assert task.due_today(date(2026, 7, 3)) is True


def test_generate_plan_skips_weekly_task_not_due_today():
    from datetime import date
    owner = Owner("Jia", available_time=60)
    pet = Pet("Rex")
    owner.add_pet(pet)
    pet.add_task(Task("Feed", 10, recurrence="daily"))
    pet.add_task(Task("Bath", 30, recurrence="weekly", weekday=0))  # Mondays only

    plan = Scheduler().generate_plan(owner, today=date(2026, 7, 3))  # Friday

    assert [t.description for t in plan.scheduled] == ["Feed"]
    assert plan.skipped == []  # Bath isn't skipped — it's simply not due


# --- Conflict detection ----------------------------------------------------

def test_detect_conflicts_finds_overlap():
    a = Task("Vet", 50, start="09:00")   # 09:00–09:50
    b = Task("Feed", 10, start="09:30")  # 09:30–09:40 (inside a)
    conflicts = Scheduler().detect_conflicts([a, b])
    assert conflicts == [(a, b)]


def test_adjacent_tasks_do_not_conflict():
    a = Task("Walk", 30, start="08:00")  # 08:00–08:30
    b = Task("Feed", 10, start="08:30")  # starts exactly when a ends
    assert Scheduler().detect_conflicts([a, b]) == []


def test_untimed_tasks_never_conflict():
    a = Task("Walk", 30)
    b = Task("Feed", 10)
    assert Scheduler().detect_conflicts([a, b]) == []


def test_generate_plan_reports_conflicts():
    owner = Owner("Jia", available_time=120)
    pet = Pet("Rex")
    owner.add_pet(pet)
    pet.add_task(Task("Vet", 50, priority="high", start="09:00"))
    pet.add_task(Task("Feed", 10, priority="medium", start="09:30"))

    plan = Scheduler().generate_plan(owner)

    assert plan.has_conflicts() is True
    assert len(plan.conflicts) == 1


def test_conflict_warnings_returns_messages_not_crash():
    rex, milo = Pet("Rex"), Pet("Milo")
    vet = Task("Vet", 50, start="09:00")
    litter = Task("Litter box", 10, start="09:00")  # same time, different pet
    rex.add_task(vet)
    milo.add_task(litter)
    warnings = Scheduler().conflict_warnings([vet, litter])
    assert len(warnings) == 1
    assert "Vet" in warnings[0] and "Litter box" in warnings[0]


def test_conflict_warnings_empty_when_clear():
    a = Task("Walk", 30, start="08:00")
    b = Task("Feed", 10, start="09:00")
    assert Scheduler().conflict_warnings([a, b]) == []


# --- Recurring auto-complete -----------------------------------------------

def test_next_occurrence_daily_advances_one_day():
    from datetime import date
    task = Task("Feed", 10, recurrence="daily", due_date=date(2026, 7, 3))
    nxt = task.next_occurrence()
    assert nxt is not None
    assert nxt.due_date == date(2026, 7, 4)
    assert nxt.completed is False


def test_next_occurrence_weekly_advances_seven_days_same_weekday():
    from datetime import date
    monday = date(2026, 7, 6)
    task = Task("Bath", 30, recurrence="weekly", due_date=monday)
    nxt = task.next_occurrence()
    assert nxt.due_date == date(2026, 7, 13)
    assert nxt.due_date.weekday() == monday.weekday()  # still a Monday


def test_next_occurrence_uses_today_when_no_due_date():
    from datetime import date
    task = Task("Feed", 10, recurrence="daily")
    nxt = task.next_occurrence(today=date(2026, 7, 3))
    assert nxt.due_date == date(2026, 7, 4)


def test_next_occurrence_one_off_returns_none():
    assert Task("Vet", 50).next_occurrence() is None


def test_complete_recurring_marks_done_and_attaches_follow_up():
    from datetime import date
    pet = Pet("Milo")
    feed = Task("Feed", 10, recurrence="daily", due_date=date(2026, 7, 3))
    pet.add_task(feed)

    follow_up = feed.complete()

    assert feed.completed is True
    assert follow_up is not None
    assert follow_up in pet.tasks          # auto-attached to the same pet
    assert follow_up.due_date == date(2026, 7, 4)
    assert len(pet.tasks) == 2


def test_complete_one_off_does_not_repeat():
    pet = Pet("Rex")
    vet = Task("Vet", 50)
    pet.add_task(vet)

    follow_up = vet.complete()

    assert vet.completed is True
    assert follow_up is None
    assert len(pet.tasks) == 1


# --- due_date drives due_today ---------------------------------------------

def test_future_due_date_is_not_due_today():
    from datetime import date
    task = Task("Feed", 10, recurrence="daily", due_date=date(2026, 7, 4))
    assert task.due_today(date(2026, 7, 3)) is False


def test_past_or_present_due_date_is_due_today():
    from datetime import date
    task = Task("Feed", 10, recurrence="daily", due_date=date(2026, 7, 3))
    assert task.due_today(date(2026, 7, 3)) is True   # today
    assert task.due_today(date(2026, 7, 5)) is True   # overdue


# --- Plan ------------------------------------------------------------------

def test_plan_skipped_high_priority():
    high = Task("Vet visit", 50, priority="high")
    low = Task("Walk", 20, priority="low")
    plan = Plan(scheduled=[], skipped=[high, low])
    assert plan.skipped_high_priority() == [high]


def test_plan_total_minutes():
    plan = Plan(scheduled=[Task("a", 15), Task("b", 25)])
    assert plan.total_minutes == 40
