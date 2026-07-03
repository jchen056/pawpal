# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

My initial UML had four classes, each with a single clear responsibility:

- **Owner** — the user of the app. Holds their `preferences` and `available_time` for the day, plus the lists of `pets` and `tasks`. Responsible for managing its own data (`add_task`, `edit_task`, `add_pet`).
- **Pet** — a simple data holder for a pet's `name`, `species`, and `breed`. It has no behavior; it exists so tasks and plans can refer to a specific animal.
- **Task** — one care activity (walk, feeding, meds). Knows its `duration`, `priority`, and `recurrence`, and can report `is_recurring()` and its numeric `priority_rank()` for sorting.
- **Scheduler** — the "brains." Deliberately kept separate from `Owner` so the scheduling logic could be unit-tested on its own. It sorts tasks by priority, filters them against a time budget, and produces the day's plan (`generate_plan`).

The core relationships were: an Owner *has* many Pets and many Tasks, and the Scheduler *uses* an Owner to produce a plan.

**b. Design changes**

Yes — two changes came out of reviewing the first implementation:

1. **Tasks now belong to a Pet.** Originally `Task` and `Pet` both lived under `Owner` but had no connection to each other, so in a multi-pet household there was no way to tell whose walk or feeding a task was. I moved the task list onto `Pet` (via `Pet.add_task`, which sets a back-reference on the task) and had `Owner` expose everything through `all_tasks()` / `pending_tasks()`. This makes the ownership chain Owner → Pet → Task explicit, and I also added a `completed` flag with `mark_done()` so finished tasks drop out of the plan.

2. **The scheduler no longer silently drops tasks.** My first `filter_tasks` returned only the tasks that fit the budget and threw the rest away, which meant an important task could disappear with no signal. I changed it to return both the *scheduled* and *skipped* tasks, and introduced a small **Plan** class to carry that result (plus helpers like `total_minutes()` and `skipped_high_priority()`). This keeps the "highest priority first" behavior while making it visible when a high-priority task can't fit, so the UI can warn the user instead of hiding the problem.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

The scheduler works within one hard constraint — the owner's **available time** for the day (`available_time`, or an explicit `time_budget`). Everything has to fit inside that budget, so the core question is *which* tasks make the cut.

To answer that, it considers three things, in order:

1. **Due today (recurrence).** Before anything else, `due_tasks` drops tasks that don't belong to today — completed tasks, and recurring tasks whose next occurrence is a future date. There's no point weighing a task that isn't even on the calendar.
2. **Priority.** `sort_tasks` orders what's left by `priority_rank` (high → medium → low), so the most important care happens first.
3. **Duration, as a tie-breaker.** Within the same priority, shorter tasks go first. This lets the budget absorb more tasks overall, so a busy day fits three quick medium tasks rather than one long one.

I decided time was the *most important* constraint because it's the real-world thing the owner can't change — a day only has so many minutes. Priority came second because when not everything fits, the owner cares most about *what* gets dropped, not just *how much*. I intentionally left `preferences` out of the scheduling math for now; it's stored on the `Owner` but isn't yet a factor, which keeps the logic simple and predictable.

Time conflicts (two tasks whose clock times overlap) are treated as a *separate concern* from budget. `detect_conflicts` and `conflict_warnings` run after the plan is built and surface overlaps as warnings — the scheduler reports them rather than trying to resolve them.

**b. Tradeoffs**

The main tradeoff is that the scheduler uses a **greedy first-fit** (`pack_into_budget`): it walks the priority-sorted list once and takes each task if it still fits, rather than searching for the mathematically optimal combination of tasks. This can be sub-optimal — for example, one long high-priority task can consume the whole budget and crowd out several smaller tasks that together would have delivered more overall value (the classic knapsack problem).

I think that tradeoff is reasonable here for two reasons. First, it matches how a person actually plans a day: you do the most important thing first and see what time is left, rather than solving an optimization problem in your head. Second, the scale is tiny — a pet owner has a handful of tasks, so the "wrong" greedy choice is rarely dramatic, and the code stays simple, fast, and easy to reason about. A full knapsack solver would add real complexity for a payoff most users would never notice.

A second, related tradeoff is treating conflicts as **warnings rather than hard blocks**. Two tasks can both be scheduled even if their times overlap; the app flags it and trusts the owner to sort it out. That keeps the tool a helpful assistant instead of a rigid gatekeeper — the owner might genuinely intend to feed both pets at 9:00, and it's not the app's place to forbid it.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
