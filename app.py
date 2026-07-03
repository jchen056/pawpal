import streamlit as st

from pawpal_system import Owner, Pet, Scheduler, Task

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")
st.caption("A pet-care planning assistant: add your pets and tasks, then build today's schedule.")

with st.expander("What is this?"):
    st.markdown(
        """
**PawPal+** helps a pet owner plan care tasks for the day. You add pets and their
tasks (each with a duration and priority), set how much time you have, and the
scheduler fits the highest-priority tasks into your time budget.
"""
    )

# --- Persistent state ------------------------------------------------------
# The Owner object (with its pets and tasks) lives in session_state so it
# survives Streamlit's reruns.
if "owner" not in st.session_state:
    st.session_state.owner = Owner(name="Jordan")

owner: Owner = st.session_state.owner

# --- Owner settings --------------------------------------------------------
st.subheader("1. Owner")
owner.name = st.text_input("Owner name", value=owner.name)
owner.available_time = st.number_input(
    "Time available today (minutes)", min_value=0, max_value=600,
    value=owner.available_time or 60, step=5,
)

# --- Add a pet -------------------------------------------------------------
st.subheader("2. Pets")
with st.form("add_pet", clear_on_submit=True):
    c1, c2, c3 = st.columns(3)
    pet_name = c1.text_input("Pet name", value="Mochi")
    species = c2.selectbox("Species", ["dog", "cat", "other"])
    breed = c3.text_input("Breed (optional)")
    if st.form_submit_button("Add pet") and pet_name.strip():
        owner.add_pet(Pet(name=pet_name.strip(), species=species, breed=breed.strip()))
        st.success(f"Added {pet_name}.")

# List the current pets, each with a Remove button. Removing a pet also
# removes its tasks (they live on the pet), so we rerun to refresh the page.
for p_idx, pet in enumerate(owner.pets):
    label = pet.name + (f" ({pet.species})" if pet.species else "")
    name_col, remove_col = st.columns([5, 1])
    name_col.write(f"🐾 {label} — {len(pet.tasks)} task(s)")
    if remove_col.button("Remove", key=f"remove_pet_{p_idx}"):
        owner.remove_pet(pet)
        st.rerun()

if not owner.pets:
    st.info("No pets yet. Add one above to get started.")

# --- Add a task to a pet ---------------------------------------------------
if owner.pets:
    st.subheader("3. Tasks")
    with st.form("add_task", clear_on_submit=True):
        pet_names = [p.name for p in owner.pets]
        c1, c2 = st.columns([2, 1])
        task_desc = c1.text_input("Task", value="Morning walk")
        which_pet = c2.selectbox("For which pet?", pet_names)

        c3, c4, c5 = st.columns(3)
        duration = c3.number_input("Minutes", min_value=1, max_value=240, value=20)
        priority = c4.selectbox("Priority", ["high", "medium", "low"], index=1)
        recurrence = c5.selectbox("Repeats", ["", "daily", "weekly"])

        c6, c7 = st.columns(2)
        start = c6.text_input("Start time (HH:MM, optional)", value="")
        WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        weekday_label = c7.selectbox("If weekly, which day?", ["(any day)"] + WEEKDAYS)

        if st.form_submit_button("Add task") and task_desc.strip():
            pet = owner.pets[pet_names.index(which_pet)]
            weekday = None if weekday_label == "(any day)" else WEEKDAYS.index(weekday_label)
            pet.add_task(
                Task(
                    description=task_desc.strip(),
                    duration=int(duration),
                    priority=priority,
                    recurrence=recurrence,
                    start=start.strip(),
                    weekday=weekday,
                )
            )
            st.success(f"Added '{task_desc}' for {which_pet}.")

    # If completing a recurring task just spawned its next occurrence, say so.
    if st.session_state.get("last_spawn"):
        st.success("🔁 " + st.session_state.pop("last_spawn"))

    # --- Filter controls (backed by the Scheduler's filter methods) --------
    scheduler = Scheduler()
    f1, f2 = st.columns(2)
    pet_filter = f1.selectbox("Filter by pet", ["All pets"] + [p.name for p in owner.pets])
    status_filter = f2.selectbox("Show", ["All", "Pending", "Completed"])

    def task_label(task: Task) -> str:
        return (
            f"[{task.priority.upper()}] {task.description} — {task.duration} min"
            + (f" @ {task.start}" if task.start else "")
            + (f" · {task.recurrence}" if task.recurrence else "")
            + (f" · due {task.due_date}" if task.due_date else "")
        )

    # Show each pet's tasks (filtered by status, sorted chronologically), each
    # with a "Done" button. Task objects live in session_state, so id(task) is
    # a stable button key across reruns. Completing a daily/weekly task
    # auto-creates its next occurrence, so we rerun to pick up the new task.
    for pet in owner.pets:
        if pet_filter != "All pets" and pet.name != pet_filter:
            continue

        tasks = pet.tasks
        if status_filter == "Pending":
            tasks = scheduler.filter_by_status(tasks, completed=False)
        elif status_filter == "Completed":
            tasks = scheduler.filter_by_status(tasks, completed=True)
        tasks = scheduler.sort_by_time(tasks)  # chronological order

        label = pet.name + (f" ({pet.species})" if pet.species else "")
        st.markdown(f"**{label}**")
        if not tasks:
            st.caption("No tasks match this filter.")
            continue

        for task in tasks:
            text_col, button_col = st.columns([6, 1])
            if task.completed:
                text_col.markdown(f"~~{task_label(task)}~~ ✓")
            else:
                text_col.write(task_label(task))
                if button_col.button("Done", key=f"done_{id(task)}"):
                    follow_up = task.complete()  # marks done + spawns next if recurring
                    if follow_up is not None:
                        msg = f"'{follow_up.description}' recurs — next one added"
                        if follow_up.due_date:
                            msg += f", due {follow_up.due_date}"
                        st.session_state["last_spawn"] = msg
                    st.rerun()  # refresh so any spawned task shows up

st.divider()

# --- Build the schedule ----------------------------------------------------
st.subheader("4. Today's Schedule")

if st.button("Generate schedule", type="primary", disabled=not owner.pets):
    plan = Scheduler().generate_plan(owner)

    m1, m2, m3 = st.columns(3)
    m1.metric("Scheduled", f"{len(plan.scheduled)} tasks")
    m2.metric("Time used", f"{plan.total_minutes} min")
    m3.metric("Time free", f"{owner.available_time - plan.total_minutes} min")

    if plan.scheduled:
        st.markdown("#### 📋 Plan (in time order)")
        # Present the plan as a clean table, sorted chronologically.
        timeline = Scheduler().sort_by_time(plan.scheduled)
        st.table([
            {
                "Time": task.start or "anytime",
                "Priority": task.priority.upper(),
                "Task": task.description,
                "Pet": task.pet.name if task.pet else "household",
                "Min": task.duration,
            }
            for task in timeline
        ])
    else:
        st.warning("Nothing fits today's time budget. Add more time in step 1.")

    # --- Conflict warnings -------------------------------------------------
    # A time overlap is advice, not an error: we still show the full plan and
    # flag each clash as a non-blocking warning that names both tasks and
    # pets, the exact overlap window, and a concrete next step.
    if plan.has_conflicts():
        def _hhmm(minutes: int) -> str:
            return f"{minutes // 60:02d}:{minutes % 60:02d}"

        st.warning(f"⏱ {len(plan.conflicts)} time conflict(s) — some tasks overlap:")
        for a, b in plan.conflicts:
            pet_a = a.pet.name if a.pet else "household"
            pet_b = b.pet.name if b.pet else "household"
            overlap = f"{_hhmm(max(a.start_minutes(), b.start_minutes()))}" \
                      f"–{_hhmm(min(a.end_minutes(), b.end_minutes()))}"
            with st.container(border=True):
                st.markdown(
                    f"**{a.description}** ({pet_a}) and **{b.description}** ({pet_b}) "
                    f"both need **{overlap}**."
                )
                st.caption("You can't be in two places at once — move one to a "
                           "different time so both pets are covered.")

    # Flag anything that didn't fit — loudly for high-priority tasks.
    for task in plan.skipped_high_priority():
        st.error(f"⚠️ High-priority task skipped: {task.description} ({task.duration} min)")

    if plan.skipped:
        with st.expander(f"Didn't fit today ({len(plan.skipped)})"):
            st.table([
                {
                    "Priority": task.priority.upper(),
                    "Task": task.description,
                    "Pet": task.pet.name if task.pet else "household",
                    "Min": task.duration,
                }
                for task in plan.skipped
            ])


# --- Debug: peek inside st.session_state -----------------------------------
# Watch this panel while you add pets/tasks and mark them done — it shows
# exactly what Streamlit is remembering between reruns.
with st.sidebar:
    st.header("🔍 session_state")
    st.caption("Live contents of the session 'vault'. Updates on every rerun.")

    # 1. The keys currently stored.
    st.write("**Keys in the vault:**", list(st.session_state.keys()))

    # 2. A readable summary of the Owner object we stashed.
    if "owner" in st.session_state:
        owner = st.session_state.owner
        st.write(f"**owner.name:** {owner.name}")
        st.write(f"**available_time:** {owner.available_time} min")
        st.write(f"**pets:** {len(owner.pets)}")
        for pet in owner.pets:
            done = sum(1 for t in pet.tasks if t.completed)
            st.write(f"- {pet.name}: {len(pet.tasks)} task(s), {done} done")

    # 3. The raw dump of everything (including each widget's stored key).
    with st.expander("Raw st.session_state"):
        st.write(st.session_state)

    # 4. A reset button: deleting the key forces re-creation next rerun.
    if st.button("Clear session_state"):
        st.session_state.clear()
        st.rerun()
