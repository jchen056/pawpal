# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## 🖥️ Sample Output

Paste a sample of your app's CLI or Streamlit output here so a reader can see what a generated plan looks like:

```
 Today's Schedule — Jia
================================================
1. [HIGH  ] Vet visit (Rex) ............. 50 min
2. [MEDIUM] Feed (Milo) ................. 10 min
------------------------------------------------
  Used 60 of 60 min   (0 min free)

  Didn't fit today (1):
    [LOW   ] Evening walk (Rex) - 20 min
```

## 🧪 Testing PawPal+

```bash
# Run the full test suite:
pytest

# Run with coverage:
pytest --cov
```

Sample test output:

```
# Paste your pytest output here
```

## 📐 Smarter Scheduling

Beyond the basic "fit tasks into a time budget" plan, PawPal+ adds four pieces of
smarter scheduling logic. All of it lives in the UI-free logic layer
(`pawpal_system.py`) so it can be unit-tested on its own, and is exercised end-to-end
in `main.py`.

| Feature            | Method(s)                                                       | Notes                                                             |
| ------------------ | --------------------------------------------------------------- | ---------------------------------------------------------------- |
| Task sorting       | `Scheduler.sort_tasks()`, `Scheduler.sort_by_time()`            | Priority-first for planning; chronological for the timeline view |
| Filtering          | `Scheduler.filter_by_pet()`, `Scheduler.filter_by_status()`, `Scheduler.due_tasks()` | By pet, by completion status, or by "due today"    |
| Conflict detection | `Scheduler.detect_conflicts()`, `Scheduler.conflict_warnings()` | Flags overlapping time slots as warnings (never crashes)         |
| Recurring tasks    | `Task.complete()`, `Task.next_occurrence()`, `Task.due_today()` | Completing a daily/weekly task auto-creates its next occurrence  |

### Sorting behavior

Two different orderings for two different purposes:

- **`Scheduler.sort_tasks()`** orders tasks by `(-priority_rank, duration)` — highest
  priority first, and shorter tasks first within the same priority (a tie-breaker that
  lets more tasks fit the budget). This is the order the planner packs in.
- **`Scheduler.sort_by_time()`** orders tasks chronologically for a day-timeline view.
  It sorts on `(start is None, start)` so timed tasks come first (earliest → latest) and
  untimed ("anytime") tasks fall to the end. Time is compared via `Task.start_minutes()`,
  which parses `"HH:MM"` into minutes past midnight.

### Filtering behavior

Small, composable filters that each take a task list and return a new one:

- **`Scheduler.filter_by_pet(tasks, pet_name)`** — keep only one pet's tasks.
- **`Scheduler.filter_by_status(tasks, completed=False)`** — keep pending (or completed) tasks.
- **`Scheduler.due_tasks(tasks, today)`** — keep only what's due today, delegating to
  `Task.due_today()` (which honors recurrence and `due_date`).

`generate_plan()` chains these — `owner.pending_tasks()` → `due_tasks()` → sort → pack —
so only the tasks that are both pending and due today ever compete for the budget.

### Conflict detection logic

- **`Scheduler.detect_conflicts(tasks)`** compares every pair of *timed* tasks and returns
  the overlapping ones. Two tasks overlap when each starts before the other ends
  (`a.start < b.end and b.start < a.end`), computed from `Task.start_minutes()` /
  `Task.end_minutes()`. Untimed tasks can't conflict and are ignored. It catches
  conflicts across the same **or** different pets.
- **`Scheduler.conflict_warnings(tasks)`** formats those pairs into human-readable warning
  strings (including pet names). It's deliberately non-fatal: it *returns warnings* rather
  than raising, so a double-booking is surfaced to the owner instead of crashing the app.
- `generate_plan()` runs conflict detection on the scheduled tasks and stores the result on
  the `Plan` (see `Plan.has_conflicts()`); both `main.py` and `app.py` display the warnings.

### Recurring task logic

Recurrence is date-driven via the `Task.due_date` field and Python's `timedelta`:

- **`Task.complete(today)`** marks a task done and, if it recurs, auto-creates its next
  instance and attaches it to the same pet.
- **`Task.next_occurrence(today)`** builds that follow-up: daily tasks advance by
  `timedelta(days=1)`, weekly tasks by `timedelta(days=7)` (which preserves the weekday);
  one-off tasks return `None`. Using `timedelta` means month/year rollovers are handled
  correctly.
- **`Task.due_today(today)`** keeps a spawned occurrence off *today's* plan until its
  `due_date` arrives, so finishing today's "Feed" makes a fresh "Feed" appear for tomorrow.

## 📸 Demo Walkthrough

Describe your app in numbered steps so a reader can follow along without watching a video:

1. <!-- Describe this step -->
2. <!-- Describe this step -->
3. <!-- Describe this step -->
4. <!-- Describe this step -->
5. <!-- Add more steps as needed -->

**Screenshot or video** _(optional)_: <!-- Insert a screenshot or link to a demo video here -->
