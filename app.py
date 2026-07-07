from datetime import date

import streamlit as st

from pawpal_system import Owner, Pet, Scheduler, Task

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

st.markdown(
    """
Welcome to the PawPal+ starter app.

This file is intentionally thin. It gives you a working Streamlit app so you can start quickly,
but **it does not implement the project logic**. Your job is to design the system and build it.

Use this app as your interactive demo once your backend classes/functions exist.
"""
)

with st.expander("Scenario", expanded=True):
    st.markdown(
        """
**PawPal+** is a pet care planning assistant. It helps a pet owner plan care tasks
for their pet(s) based on constraints like time, priority, and preferences.

You will design and implement the scheduling logic and connect it to this Streamlit UI.
"""
    )

with st.expander("What you need to build", expanded=True):
    st.markdown(
        """
At minimum, your system should:
- Represent pet care tasks (what needs to happen, how long it takes, priority)
- Represent the pet and the owner (basic info and preferences)
- Build a plan/schedule for a day that chooses and orders tasks based on constraints
- Explain the plan (why each task was chosen and when it happens)
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

    if st.button("Add task"):
        selected_pet.add_task(
            Task(description=task_title, duration_minutes=int(duration), priority=priority)
        )

    if selected_pet.tasks:
        st.write(f"Tasks for {selected_pet.name}:")
        st.table(
            [
                {"title": task.description, "duration_minutes": task.duration_minutes, "priority": task.priority}
                for task in selected_pet.tasks
            ]
        )
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
    st.markdown(f"```\n{plan.summary()}\n```")
    st.markdown(f"```\n{scheduler.explain(plan)}\n```")
