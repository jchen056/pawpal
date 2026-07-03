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

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

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
