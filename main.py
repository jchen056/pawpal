"""Temporary testing ground for the PawPal+ logic layer.

Run it from the terminal to verify the scheduling logic without any UI:

    python main.py
"""

from pawpal_system import Owner, Pet, Scheduler, Task

# 1. Create an Owner with some free time today.
owner = Owner(name="Jia", available_time=60)  # 60 minutes available

# 2. Create at least two Pets and register them with the owner.
rex = Pet(name="Rex", species="dog", breed="Labrador")
milo = Pet(name="Milo", species="cat")
owner.add_pet(rex)
owner.add_pet(milo)

# 3. Add at least three Tasks with different times to the pets.
rex.add_task(Task("Vet visit", duration=50, priority="high"))
rex.add_task(Task("Evening walk", duration=20, priority="low", recurrence="daily"))
milo.add_task(Task("Feed", duration=10, priority="medium", recurrence="daily"))

# 4. Build today's plan and print it to the terminal.
plan = Scheduler().generate_plan(owner)

# Spell out the priority as a padded tag so the column stays aligned.
def priority_tag(priority: str) -> str:
    return f"[{priority.upper():<6}]"  # e.g. "[HIGH  ]", "[MEDIUM]", "[LOW   ]"


WIDTH = 48
print()
print(f"Today's Schedule — {owner.name}".center(WIDTH))
print("=" * WIDTH)

if plan.scheduled:
    for i, task in enumerate(plan.scheduled, start=1):
        tag = priority_tag(task.priority)
        pet_name = task.pet.name if task.pet else "household"
        # e.g. "1. [HIGH  ] Vet visit (Rex) ........ 50 min"
        label = f"{i}. {tag} {task.description} ({pet_name})"
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

# Loudly flag any important task that got pushed out.
for task in plan.skipped_high_priority():
    print(f"\n  ⚠️  High-priority task skipped: {task.description}")
