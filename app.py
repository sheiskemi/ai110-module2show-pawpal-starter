from datetime import date

import streamlit as st

from pawpal_system import Owner, Pet, Scheduler, Task

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

st.markdown(
    """
**PawPal+** helps a pet owner plan daily care tasks (walks, feeding, meds, enrichment,
grooming) around a time budget, task priority, and preferred times — and explains why
each task was scheduled, skipped, or flagged as conflicting.
"""
)

st.divider()

st.subheader("Owner")
owner_name = st.text_input("Owner name", value="Jordan")

# Create the Owner once per session, then keep it updated in place on every
# rerun rather than re-creating it (which would wipe out any pets/tasks
# already added to session_state).
if "owner" not in st.session_state:
    st.session_state.owner = Owner(name=owner_name)
else:
    st.session_state.owner.name = owner_name

owner = st.session_state.owner

st.markdown("### Add a Pet")
col1, col2 = st.columns(2)
with col1:
    new_pet_name = st.text_input("Pet name", value="Mochi")
with col2:
    new_pet_species = st.selectbox("Species", ["dog", "cat", "other"])

if st.button("Add pet"):
    owner.add_pet(Pet(name=new_pet_name, species=new_pet_species))

if not owner.pets:
    st.info("No pets yet. Add one above.")
else:
    st.write("Pets:")
    st.table([{"name": p.name, "species": p.species, "tasks": len(p.tasks)} for p in owner.pets])

    st.markdown("### Add a Task")
    selected_pet_name = st.selectbox("Pet", [p.name for p in owner.pets])
    selected_pet = next(p for p in owner.pets if p.name == selected_pet_name)

    tcol1, tcol2, tcol3 = st.columns(3)
    with tcol1:
        task_title = st.text_input("Task title", value="Morning walk")
    with tcol2:
        duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
    with tcol3:
        priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)

    tcol4, tcol5, tcol6 = st.columns(3)
    with tcol4:
        category = st.selectbox(
            "Category", ["walk", "feeding", "meds", "enrichment", "grooming", "general"]
        )
    with tcol5:
        recurrence = st.selectbox("Recurrence", ["once", "daily", "weekly"])
    with tcol6:
        has_preferred_time = st.checkbox("Set a preferred time?", value=True)
        preferred_time = st.time_input("Preferred time", value=None) if has_preferred_time else None

    if st.button("Add task"):
        selected_pet.add_task(
            Task(
                description=task_title,
                duration_minutes=int(duration),
                priority=priority,
                category=category,
                recurrence=recurrence,
                preferred_time=preferred_time.strftime("%H:%M") if preferred_time else None,
            )
        )

    if selected_pet.tasks:
        show_filter = st.radio(
            "Show", ["All", "Pending", "Completed"], horizontal=True, key="task-filter"
        )
        display_scheduler = Scheduler(available_time_minutes=0)
        completed_filter = {"All": None, "Pending": False, "Completed": True}[show_filter]
        visible_tasks = display_scheduler.filter_tasks(
            selected_pet.tasks, completed=completed_filter
        )
        visible_tasks = display_scheduler.sort_by_time(visible_tasks)

        st.write(f"Tasks for {selected_pet.name} (sorted by time):")
        if not visible_tasks:
            st.info(f"No {show_filter.lower()} tasks for {selected_pet.name}.")
        else:
            st.table(
                [
                    {
                        "Time": task.preferred_time or "anytime",
                        "Task": task.description,
                        "Duration (min)": task.duration_minutes,
                        "Priority": task.priority,
                        "Category": task.category,
                        "Recurrence": task.recurrence,
                        "Status": "✅ Done" if task.completed else "⏳ Pending",
                    }
                    for task in visible_tasks
                ]
            )

            pending_tasks = [task for task in visible_tasks if not task.completed]
            if pending_tasks:
                mark_col1, mark_col2 = st.columns([3, 1])
                with mark_col1:
                    task_to_complete = st.selectbox(
                        "Mark a task complete",
                        pending_tasks,
                        format_func=lambda task: f"{task.preferred_time or 'anytime'} — {task.description}",
                        key="task-to-complete",
                    )
                with mark_col2:
                    if st.button("Mark done", key=f"done-{task_to_complete.id}"):
                        task_to_complete.mark_complete(date.today())
                        st.success(f"Marked '{task_to_complete.description}' complete.")
                        st.rerun()

        conflict_warnings = display_scheduler.detect_conflicts(selected_pet.tasks)
        if conflict_warnings:
            st.markdown("##### ⚠️ Scheduling conflicts")
            for warning in conflict_warnings:
                st.warning(f"{warning} — consider moving one of these to a different time.")
        elif visible_tasks:
            st.success(f"No scheduling conflicts for {selected_pet.name}.")
    else:
        st.info(f"No tasks yet for {selected_pet.name}. Add one above.")

st.divider()

st.subheader("Build Schedule")
available_minutes = st.number_input(
    "Available time today (minutes)", min_value=1, max_value=1440, value=120
)

if st.button("Generate schedule"):
    scheduler = Scheduler(available_time_minutes=int(available_minutes))
    plan = scheduler.build_plan(owner, date.today())

    st.markdown("#### Plan")
    if plan.scheduled_tasks:
        st.success(
            f"Scheduled {len(plan.scheduled_tasks)} task(s) using "
            f"{plan.total_time_used()} of {int(available_minutes)} available minutes."
        )
        st.table(
            [
                {
                    "Time": task.preferred_time or "anytime",
                    "Task": task.description,
                    "Pet": task.pet.name if task.pet else "unknown",
                    "Duration (min)": task.duration_minutes,
                    "Priority": task.priority,
                }
                for task in plan.scheduled_tasks
            ]
        )
    else:
        st.info(f"No tasks scheduled for {owner.name} today.")

    if plan.skipped_tasks:
        st.markdown("#### Skipped tasks")
        for task in plan.skipped_tasks:
            pet_name = task.pet.name if task.pet else "unknown pet"
            reason = plan.skip_reasons.get(task.id, "time")
            if reason == "conflict":
                st.warning(
                    f"'{task.description}' ({pet_name}) skipped — conflicts with an "
                    f"already-scheduled task at {task.preferred_time}. "
                    "Consider giving it a different preferred time."
                )
            else:
                st.info(
                    f"'{task.description}' ({pet_name}) skipped — not enough time left "
                    f"in today's {int(available_minutes)}-minute budget."
                )

    conflict_warnings = scheduler.detect_conflicts(owner.get_all_tasks())
    if conflict_warnings:
        st.markdown("#### ⚠️ Conflicts across all tasks")
        for warning in conflict_warnings:
            st.warning(f"{warning} — consider moving one of these to a different time.")

    with st.expander("Full explanation"):
        st.text(scheduler.explain(plan))
