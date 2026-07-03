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

## ✨ Features

PawPal+ turns a list of pet-care tasks into a realistic daily plan. The scheduling
"brain" lives in `pawpal_system.py`; the Streamlit app in `app.py` is the interface.
Each feature maps to a method you can find in the code.

**Planning**

- **Priority-first budget packing** — fits the highest-priority tasks into the owner's
  available minutes (greedy first-fit); shorter tasks break ties so more gets done.
  (`Scheduler.sort_tasks`, `Scheduler.pack_into_budget`)
- **Skip tracking** — tasks that don't fit aren't dropped silently; they're reported, and
  skipped *high-priority* tasks are flagged loudly. (`Plan.skipped_high_priority`)

**Sorting**

- **Sorting by time** — arranges the day as a chronological timeline; untimed ("anytime")
  tasks fall to the end. (`Scheduler.sort_by_time`)
- **Sorting by priority** — high → medium → low, then shorter first. (`Scheduler.sort_tasks`)

**Filtering**

- **Filter by pet** — show just one pet's tasks. (`Scheduler.filter_by_pet`)
- **Filter by status** — show pending vs. completed tasks. (`Scheduler.filter_by_status`)
- **Due-today filter** — only tasks actually due today enter the plan.
  (`Scheduler.due_tasks`, `Task.due_today`)

**Conflict warnings**

- **Overlap detection** — flags any two timed tasks whose windows overlap, across the same
  *or* different pets. (`Scheduler.detect_conflicts`)
- **Human-readable, non-crashing warnings** — returns warning messages (with pet names)
  instead of erroring on a double-booking. (`Scheduler.conflict_warnings`)

**Recurring tasks**

- **Daily recurrence** — completing a daily task auto-creates the next one for tomorrow
  (today + 1 day). (`Task.complete`, `Task.next_occurrence`)
- **Weekly recurrence** — advances 7 days, preserving the weekday. (`Task.next_occurrence`)
- **One-off tasks** — complete once and don't repeat.

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

Running `python main.py` prints the generated schedule to the terminal. The plan is
shown in time order, with the time used vs. available, anything that didn't fit, and any
time conflicts:

```
             Today's Schedule — Jia
================================================
1. 09:00–09:10 [HIGH  ] Litter box (Milo) .. 10 min
2. 09:00–09:50 [HIGH  ] Vet visit (Rex) .. 50 min
------------------------------------------------
  Used 60 of 60 min   (0 min free)

  Didn't fit today (3):
    [MEDIUM] Feed (Milo) - 10 min
    [MEDIUM] Nail trim (Milo) - 15 min
    [LOW   ] Evening walk (Rex) - 20 min

  ⏱  Time conflicts (1):
    Litter box (09:00–09:10) overlaps Vet visit (09:00–09:50)
```

## 🧪 Testing PawPal+

Run the full test suite from the project root:

```bash
python -m pytest
```

The tests live in `tests/test_pawpal.py` and cover the logic layer end-to-end
(43 tests):

- **Task basics** — `is_recurring()`, `priority_rank()` ordering, unknown-priority
  fallback, and `mark_done()`.
- **Pet & Owner** — `add_task` sets the back-reference, `pending_tasks()` excludes
  completed tasks, `all_tasks()` gathers across pets, and `remove_pet()` removes a
  pet (and its tasks) while returning `False` for a pet that isn't registered.
- **Sorting** — `sort_tasks()` (priority, then shorter first) and `sort_by_time()`
  (chronological, untimed tasks last), plus `start_minutes()` / `end_minutes()`.
- **Filtering** — `filter_by_pet()` and `filter_by_status()`.
- **Recurring tasks** — `next_occurrence()` advances daily by 1 day and weekly by
  7 (same weekday), one-offs return `None`; `complete()` marks done and auto-attaches
  the follow-up; `due_today()` respects `due_date` so future occurrences stay off
  today's plan.
- **Conflict detection** — `detect_conflicts()` finds overlaps (and correctly treats
  adjacent/untimed tasks as non-conflicting); `conflict_warnings()` returns messages
  instead of crashing.
- **Budget & Plan** — `pack_into_budget()` splits scheduled vs. skipped, and
  `generate_plan()` prioritizes within budget, ignores completed/not-due tasks, honors
  an explicit budget, and reports conflicts.

Sample test output:

```
============================= test session starts ==============================
platform darwin -- Python 3.9.12, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/jchen056/pawpal
collected 43 items

tests/test_pawpal.py ...........................................         [100%]

============================== 43 passed in 0.04s ==============================
```

### Confidence Level: ★★★★☆ (4 / 5)

All 43 tests pass and cover every scheduling behavior — sorting, filtering, budget
packing, recurrence, and conflict detection — including edge cases like unknown
priorities, adjacent (non-overlapping) times, and untimed tasks. I'm confident the
**logic layer** is reliable.

I held back the fifth star because the tests exercise `pawpal_system.py` directly, not
the Streamlit UI in `app.py`; UI behavior (session-state persistence, the Done/Remove
buttons) is currently verified by hand. I'd also want to add tests for malformed input
(e.g. a bad `"HH:MM"` start time) before claiming full reliability.

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

## 🎬 Demo Walkthrough

### The interface

Launch the web app with `streamlit run app.py`. The page is organized top-to-bottom as a
four-step workflow, plus a debug sidebar:

1. **Owner** — set your name and how many minutes you have available today.
2. **Pets** — add a pet (name, species, optional breed); each pet is listed with a
   **Remove** button and its task count.
3. **Tasks** — add tasks for a pet (duration, priority, optional start time, and
   recurrence: none / daily / weekly). Below the form you can **filter by pet** and
   **filter by status** (All / Pending / Completed), and mark any task **Done**. Marking a
   recurring task done strikes it through and automatically schedules its next occurrence.
4. **Today's Schedule** — click **Generate schedule** to build the plan, shown as a table
   in time order alongside how much time was used, any conflicts, and what didn't fit.

**Actions a user can perform:** set available time · add / remove pets · add tasks with
priority, time, and recurrence · filter the task list by pet or status · mark tasks done
(auto-spawning the next recurring instance) · generate and read the daily schedule ·
reset everything from the sidebar.

### An example workflow

1. In **Owner**, set available time to `60` minutes.
2. In **Pets**, add `Rex` (dog) and `Milo` (cat).
3. In **Tasks**, add `Vet visit` for Rex — 50 min, **high** priority, start `09:00`. Then
   add `Litter box` for Milo — 10 min, **high**, start `09:00`, and `Feed` for Milo — 10
   min, **medium**, **daily**.
4. Click **Generate schedule**. PawPal+ packs the two high-priority tasks into the 60-minute
   budget, lays them out in time order, warns that the two `09:00` tasks overlap, and lists
   `Feed` under "Didn't fit today."
5. Mark `Feed` **Done** — it strikes through and a fresh `Feed` appears dated tomorrow.

### Key Scheduler behaviors shown

- **Priority-first packing** — `Vet visit` and `Litter box` (both high) are scheduled;
  the medium `Feed` is skipped when time runs out.
- **Sorting by time** — the plan is displayed chronologically, not in entry order.
- **Conflict warnings** — the two tasks that both start at `09:00` are flagged, with the
  exact overlap window, rather than silently double-booked.
- **Daily recurrence** — completing `Feed` auto-creates tomorrow's `Feed` (today + 1 day).

### Sample CLI output (behaviors)

Running `python main.py` also demonstrates the scheduler behaviors directly in the
terminal. Beyond the schedule (see **Sample Output** above), it prints the sorting /
filtering, conflict, and recurrence demos:

```
================================================
            Sorting & filtering demo
================================================

Same tasks, sort_by_time() (untimed 'anytime' last):
   07:30–07:45  Morning brush (Rex)  ✓ done
   09:00–09:50  Vet visit (Rex)
   09:00–09:10  Litter box (Milo)
   09:30–09:40  Feed (Milo)
   18:00–18:20  Evening walk (Rex)
       anytime  Nail trim (Milo)

filter_by_status(completed=False)  — still to do:
   18:00–18:20  Evening walk (Rex)
   09:00–09:50  Vet visit (Rex)
   09:30–09:40  Feed (Milo)
       anytime  Nail trim (Milo)
   09:00–09:10  Litter box (Milo)

================================================
               Conflict detection
================================================

Found 2 conflict(s):
   ⚠️  Conflict: 'Vet visit' (Rex, 09:00) overlaps 'Litter box' (Milo, 09:00)
   ⚠️  Conflict: 'Vet visit' (Rex, 09:00) overlaps 'Feed' (Milo, 09:30)

================================================
            Recurring auto-complete
================================================

Completing 'Feed' (daily) on 2026-07-03 ...
  → auto-created next 'Feed', now due 2026-07-04
    (that's 2026-07-03 + 1 day)

Completing one-off 'Nail trim' returns: None (nothing repeats).
```

**Screenshot or video** _(optional)_: <!-- Insert a screenshot or link to a demo video here -->
