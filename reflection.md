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

AI was involved at essentially every stage — design, implementation, testing, refactoring, and documentation. My workflow was mostly: describe what I wanted at a high level, review what the AI produced, and course-correct. I came in with an initial UML sketch and the core ownership idea (Owner → Pet → Task), and the AI helped me develop it further — for example, splitting the scheduling result into its own `Plan` class and adding the family of `Scheduler` methods. It was especially strong at writing clean, well-documented code quickly and at generating thorough test cases, including edge cases I wouldn't have thought to check.

The prompts that worked best were the specific, goal-oriented ones — naming the feature I wanted ("sort by time," "filter by pet/status," "recurring tasks," "conflict detection") rather than making vague requests. Asking the AI to "walk me through the current logic" was also useful for understanding code it had written before I built on top of it.

Honestly, I ended up saying "yes" to a lot of the AI's ideas. The hardest part conceptually was the scheduling algorithm itself, and I didn't put a huge amount of my own thought into it — the AI proposed something functional (greedy, priority-first packing) and I accepted it. So at times I felt more like a director than an author.

**b. Judgment and verification**

Even though I accepted a lot, there were moments I steered or pushed back. When the AI offered a long list of possible improvements, I didn't take all of them — I chose the specific features I wanted, and when it suggested two code simplifications I applied only the rename (`filter_tasks` → `pack_into_budget`) and skipped the other. I also caught a gap the AI hadn't filled on its own: I could *add* a pet but there was no way to *remove* one, so I asked for that.

I verified the AI's work in two main ways: the automated test suite (which the AI wrote) had to pass, and I manually exercised the Streamlit app. One concrete moment stands out — after adding `remove_pet`, the app threw an `AttributeError` even though every test passed. That mismatch (green tests but a broken app) pushed me to find out *why* rather than assume it worked: it turned out to be a stale `Owner` object cached in Streamlit's session state, not a bug in the code. It was a good reminder that "the tests pass" isn't the same as "it works when you actually use it."

---

## 4. Testing and Verification

**a. What you tested**

Testing happened on two levels. First, the AI wrote a suite of automated tests for the logic layer — before I even asked for them — covering sorting, filtering, budget packing, recurrence (daily / weekly / one-off), and conflict detection, along with assertions on edge cases. These verified the underlying logic in isolation, independent of the UI. Second, I manually tested scenarios by playing with the Streamlit app: adding pets and tasks, marking tasks done, generating schedules, and watching for conflicts.

These tests mattered because the logic layer is the part that's easy to get subtly wrong (off-by-one budget math, a recurrence that spawns on the wrong day) and hard to eyeball. What I'd like to add next is an automated stress test that generates lots of random pets and tasks and checks that key invariants always hold — so a human doesn't have to click through the app by hand to feel confident.

**b. Confidence**

I'm not very confident the scheduler is fully correct — not because I've watched it fail, but because the logic we implemented is intentionally simple and I didn't stress it hard. It does handle the obvious edge cases: an owner with no pets, a pet with no tasks, a zero-minute budget, and it correctly flags tasks whose times conflict.

The main gap I can see is that it treats *every* time overlap as a conflict, when some overlaps are perfectly reasonable — for example, walking two dogs together, or feeding both pets at the same time. A smarter version would let the owner mark certain tasks as "can be done together" instead of warning about them. That's the first edge case I'd design and test for next.

---

## 5. Reflection

**a. What went well**

I'm most satisfied with the testing side. I was genuinely impressed that the AI could write so many test cases and assertion statements so quickly, and watching the suite grow — and stay green — as we added each feature was new to me. It gave the project a solid backbone and made me comfortable changing code without fear of quietly breaking something.

**b. What you would improve**

In another iteration I'd focus on two things. First, smarter scheduling: moving beyond greedy first-fit to handle tasks that can happen together, time windows, and maybe genuinely optimal packing. Second, adding a database to persist users and their pets and tasks between sessions, instead of losing everything when the app resets. I'd also start from a clear roadmap — this time I mostly went step by step, and I think having the AI help me lay out a plan *before* implementing would make the work more deliberate and less reactive.

**c. Key takeaway**

My biggest takeaway is the value of planning before executing — a roadmap up front, plus tests as a safety net throughout. Working with AI, I also learned that "the AI wrote it and the tests pass" isn't the same as "I understand it and it works in the real app." My real job in this collaboration was to direct, verify, and catch the gaps the AI won't necessarily surface on its own — like the missing remove button, or the tests-pass-but-app-breaks moment.
