"""Temporary testing ground for the PawPal+ logic layer.

Run it from the terminal to verify the scheduling logic without any UI:

    python main.py
"""

from datetime import date

from pawpal_system import Owner, Pet, Scheduler, Task

# 1. Create an Owner with some free time today.
owner = Owner(name="Jia", available_time=60)  # 60 minutes available

# 2. Create at least two Pets and register them with the owner.
rex = Pet(name="Rex", species="dog", breed="Labrador")
milo = Pet(name="Milo", species="cat")
owner.add_pet(rex)
owner.add_pet(milo)

# 3. Add Tasks deliberately OUT OF TIME ORDER so we can prove sort_by_time()
#    actually reorders them. Vet visit (09:00–09:50) and Feed (09:30–09:40)
#    overlap on purpose so conflict detection has something to catch.
#    "Morning brush" is already done, and "Nail trim" has no start time —
#    both are there to exercise the filtering methods.
rex.add_task(Task("Evening walk", duration=20, priority="low", recurrence="daily", start="18:00"))
rex.add_task(Task("Vet visit", duration=50, priority="high", start="09:00"))
rex.add_task(Task("Morning brush", duration=15, priority="low", start="07:30", completed=True))
milo.add_task(Task("Feed", duration=10, priority="medium", recurrence="daily", start="09:30"))
milo.add_task(Task("Nail trim", duration=15, priority="medium"))  # no start time
# Same start time as Rex's 09:00 vet visit → a cross-pet conflict to catch.
milo.add_task(Task("Litter box", duration=10, priority="high", start="09:00"))

# 4. Build today's plan and print it to the terminal.
plan = Scheduler().generate_plan(owner)

# Spell out the priority as a padded tag so the column stays aligned.
def priority_tag(priority: str) -> str:
    return f"[{priority.upper():<6}]"  # e.g. "[HIGH  ]", "[MEDIUM]", "[LOW   ]"


def clock(minutes: int) -> str:
    """Render minutes-past-midnight as HH:MM."""
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def when(task: Task) -> str:
    """A short 'HH:MM–HH:MM' window, or 'anytime' if the task has no start."""
    start = task.start_minutes()
    if start is None:
        return "anytime"
    return f"{clock(start)}–{clock(start + task.duration)}"


WIDTH = 48
print()
print(f"Today's Schedule — {owner.name}".center(WIDTH))
print("=" * WIDTH)

if plan.scheduled:
    # Show the day in chronological order (untimed tasks fall to the end).
    for i, task in enumerate(Scheduler().sort_by_time(plan.scheduled), start=1):
        tag = priority_tag(task.priority)
        pet_name = task.pet.name if task.pet else "household"
        # e.g. "1. 09:00–09:50 [HIGH  ] Vet visit (Rex) ...... 50 min"
        label = f"{i}. {when(task):>11} {tag} {task.description} ({pet_name})"
        print(f"{label} {'.' * max(2, WIDTH - len(label) - 8)} {task.duration:>2} min")
else:
    print("  (nothing fits today's time budget)")

print("-" * WIDTH)
remaining = owner.available_time - plan.total_minutes
print(f"  Used {plan.total_minutes} of {owner.available_time} min   ({remaining} min free)")

if plan.skipped:
    print(f"\n  Didn't fit today ({len(plan.skipped)}):")
    for task in plan.skipped:
        tag = priority_tag(task.priority)
        pet_name = task.pet.name if task.pet else "household"
        print(f"    {tag} {task.description} ({pet_name}) - {task.duration} min")

# Flag any scheduled tasks whose times overlap.
if plan.has_conflicts():
    print(f"\n  ⏱  Time conflicts ({len(plan.conflicts)}):")
    for a, b in plan.conflicts:
        print(f"    {a.description} ({when(a)}) overlaps {b.description} ({when(b)})")

# Loudly flag any important task that got pushed out.
for task in plan.skipped_high_priority():
    print(f"\n  ⚠️  High-priority task skipped: {task.description}")


# ---------------------------------------------------------------------------
# 5. Sorting & filtering demo — prove the utility methods work on their own,
#    independent of the budget-limited plan above. These operate on ALL tasks.
# ---------------------------------------------------------------------------
scheduler = Scheduler()
all_tasks = owner.all_tasks()


def line(task: Task) -> str:
    """One compact row: 'HH:MM–HH:MM  Description (Pet)  [done]'."""
    pet_name = task.pet.name if task.pet else "household"
    status = "  ✓ done" if task.completed else ""
    return f"{when(task):>11}  {task.description} ({pet_name}){status}"


print("\n" + "=" * WIDTH)
print("Sorting & filtering demo".center(WIDTH))
print("=" * WIDTH)

# --- Sort by time: note tasks were added out of order above ----------------
print("\nAll tasks, added out of order:")
for task in all_tasks:
    print("   " + line(task))

print("\nSame tasks, sort_by_time() (untimed 'anytime' last):")
for task in scheduler.sort_by_time(all_tasks):
    print("   " + line(task))

# --- Filter by pet ---------------------------------------------------------
print("\nfilter_by_pet('Rex'):")
for task in scheduler.filter_by_pet(all_tasks, "Rex"):
    print("   " + line(task))

# --- Filter by status ------------------------------------------------------
print("\nfilter_by_status(completed=False)  — still to do:")
for task in scheduler.filter_by_status(all_tasks, completed=False):
    print("   " + line(task))

print("\nfilter_by_status(completed=True)  — already done:")
for task in scheduler.filter_by_status(all_tasks, completed=True):
    print("   " + line(task))


# ---------------------------------------------------------------------------
# 6. Conflict detection — two tasks booked at the same time should produce a
#    warning message, not a crash. conflict_warnings() returns plain strings.
# ---------------------------------------------------------------------------
print("\n" + "=" * WIDTH)
print("Conflict detection".center(WIDTH))
print("=" * WIDTH)

warnings = scheduler.conflict_warnings(owner.all_tasks())
if warnings:
    print(f"\nFound {len(warnings)} conflict(s):")
    for message in warnings:
        print("   " + message)
else:
    print("\n  No time conflicts — the day is clear.")


# ---------------------------------------------------------------------------
# 7. Recurring tasks — completing a "daily"/"weekly" task auto-creates the
#    next occurrence (today + 1 day for daily, + 7 for weekly).
# ---------------------------------------------------------------------------
print("\n" + "=" * WIDTH)
print("Recurring auto-complete".center(WIDTH))
print("=" * WIDTH)

today = date.today()
feed = next(t for t in milo.tasks if t.description == "Feed" and not t.completed)

print(f"\nMilo has {len(milo.tasks)} tasks before completing '{feed.description}'.")
print(f"Completing '{feed.description}' ({feed.recurrence}) on {today} ...")

follow_up = feed.complete(today)  # marks done AND spawns the next instance

if follow_up is not None:
    print(f"  → auto-created next '{follow_up.description}', now due {follow_up.due_date}")
    print(f"    (that's {today} + 1 day)")
print(f"Milo now has {len(milo.tasks)} tasks; '{feed.description}' completed = {feed.completed}.")

# A one-off task, by contrast, does NOT repeat when completed.
nail_trim = next(t for t in milo.tasks if t.description == "Nail trim")
spawned = nail_trim.complete(today)
print(f"\nCompleting one-off '{nail_trim.description}' returns: {spawned} (nothing repeats).")
