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

    # Show each pet's tasks, each with a "Done" button.
    # Completing a daily/weekly task auto-creates its next occurrence
    # (via Task.complete), so we rerun to pick up the newly added task.
    def task_label(task: Task) -> str:
        return (
            f"[{task.priority.upper()}] {task.description} — {task.duration} min"
            + (f" @ {task.start}" if task.start else "")
            + (f" · {task.recurrence}" if task.recurrence else "")
            + (f" · due {task.due_date}" if task.due_date else "")
        )

    for p_idx, pet in enumerate(owner.pets):
        label = pet.name + (f" ({pet.species})" if pet.species else "")
        st.markdown(f"**{label}**")
        if not pet.tasks:
            st.caption("No tasks yet.")
        for t_idx, task in enumerate(pet.tasks):
            text_col, button_col = st.columns([6, 1])
            if task.completed:
                text_col.markdown(f"~~{task_label(task)}~~ ✓")
            else:
                text_col.write(task_label(task))
                if button_col.button("Done", key=f"done_{p_idx}_{t_idx}"):
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
        st.markdown("#### Plan")
        # Lay the plan out as a chronological timeline (untimed tasks last).
        for i, task in enumerate(Scheduler().sort_by_time(plan.scheduled), start=1):
            pet_name = task.pet.name if task.pet else "household"
            when = f"{task.start} · " if task.start else ""
            st.write(f"{i}. {when}**[{task.priority.upper()}]** {task.description} "
                     f"— {pet_name} ({task.duration} min)")
    else:
        st.warning("Nothing fits today's time budget.")

    # Warn about any scheduled tasks whose times overlap. Reuse the same
    # conflict_warnings() messages the terminal (main.py) prints, so both
    # entry points report conflicts identically — pet names included.
    if plan.has_conflicts():
        st.warning(f"⏱ {len(plan.conflicts)} time conflict(s) detected:")
        for message in Scheduler().conflict_warnings(plan.scheduled):
            st.write("- " + message)

    # Flag anything that didn't fit — loudly for high-priority tasks.
    for task in plan.skipped_high_priority():
        st.error(f"⚠️ High-priority task skipped: {task.description} ({task.duration} min)")

    if plan.skipped:
        with st.expander(f"Didn't fit today ({len(plan.skipped)})"):
            for task in plan.skipped:
                pet_name = task.pet.name if task.pet else "household"
                st.write(f"[{task.priority.upper()}] {task.description} "
                         f"— {pet_name} ({task.duration} min)")


# --- Debug: peek inside st.session_state -----------------------------------
# Watch this panel while you add pets/tasks and tick checkboxes — it shows
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
