from __future__ import annotations

import json
import os
import uuid
from datetime import date, datetime, time, timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

APP_DIR = Path(__file__).parent
DATA_FILE = APP_DIR / "studymate_data.json"
SAMPLE_FILE = APP_DIR / "sample_data.json"

st.set_page_config(page_title="StudyMate AI", page_icon="🎓", layout="wide", initial_sidebar_state="expanded")

from planner import DIFFICULTIES, generate_schedule, get_topic_rows

SUBJECT_COLORS = ["#5B6CFF", "#13B8A6", "#F59E0B", "#EC4899", "#8B5CF6", "#0EA5E9"]

def sample_data():
    today = date.today()
    return {
        "settings": {"daily_hours": 3.0, "start_time": "17:00", "end_time": "21:00"},
        "subjects": [
            {"id": "sub-math", "name": "Mathematics", "exam_date": (today + timedelta(days=5)).isoformat(), "difficulty": "Hard", "priority": 5, "topics": [
                {"id": "t-m1", "name": "Integration techniques", "difficulty": "Hard", "estimated_hours": 2.0, "completed": False},
                {"id": "t-m2", "name": "Differential equations", "difficulty": "Hard", "estimated_hours": 1.5, "completed": False},
                {"id": "t-m3", "name": "Applications of derivatives", "difficulty": "Medium", "estimated_hours": 1.0, "completed": True}]},
            {"id": "sub-dbms", "name": "Database Systems", "exam_date": (today + timedelta(days=9)).isoformat(), "difficulty": "Medium", "priority": 4, "topics": [
                {"id": "t-d1", "name": "Normalization and keys", "difficulty": "Medium", "estimated_hours": 1.0, "completed": False},
                {"id": "t-d2", "name": "SQL joins and subqueries", "difficulty": "Hard", "estimated_hours": 1.5, "completed": False},
                {"id": "t-d3", "name": "Transactions and ACID", "difficulty": "Easy", "estimated_hours": 1.0, "completed": False}]},
            {"id": "sub-ml", "name": "Machine Learning", "exam_date": (today + timedelta(days=14)).isoformat(), "difficulty": "Medium", "priority": 3, "topics": [
                {"id": "t-ml1", "name": "Supervised learning", "difficulty": "Medium", "estimated_hours": 1.5, "completed": False},
                {"id": "t-ml2", "name": "Model evaluation metrics", "difficulty": "Medium", "estimated_hours": 1.0, "completed": False}]}
        ]
    }


def normalize_data(data):
    data.setdefault("settings", {"daily_hours": 3.0, "start_time": "17:00", "end_time": "21:00"})
    data.setdefault("subjects", [])
    for s in data["subjects"]:
        s.setdefault("id", str(uuid.uuid4()))
        s.setdefault("priority", 3)
        s.setdefault("difficulty", "Medium")
        s.setdefault("topics", [])
        for t in s["topics"]:
            t.setdefault("id", str(uuid.uuid4()))
            t.setdefault("difficulty", s["difficulty"])
            t.setdefault("estimated_hours", 1.0)
            t.setdefault("completed", False)
    return data


def load_data():
    if "data" in st.session_state:
        return st.session_state.data
    if DATA_FILE.exists():
        try:
            data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = sample_data()
    else:
        data = sample_data()
    st.session_state.data = normalize_data(data)
    return st.session_state.data


def save_data():
    DATA_FILE.write_text(json.dumps(st.session_state.data, indent=2), encoding="utf-8")


def priority_table(data):
    rows = get_topic_rows(data)
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    return df.sort_values(["Completed", "Priority score"], ascending=[True, False])


def ai_assistant_reply(question, context):
    """Optional OpenAI-compatible API; local fallback is transparent and rule-based."""
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if api_key:
        try:
            import urllib.request
            payload = {
                "model": os.getenv("STUDYMATE_AI_MODEL", "gpt-4o-mini"),
                "messages": [
                    {"role": "system", "content": "You are StudyMate AI, a practical academic study coach. Be accurate, concise, and never claim to know course material not provided. Give actionable study guidance."},
                    {"role": "user", "content": f"Student context: {context}\nQuestion: {question}"}
                ],
                "temperature": 0.4
            }
            req = urllib.request.Request(
                "https://api.openai.com/v1/chat/completions",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=20) as response:
                result = json.loads(response.read().decode("utf-8"))
            return result["choices"][0]["message"]["content"], "API"
        except Exception as exc:
            return f"I couldn't reach the optional AI service ({type(exc).__name__}). Here's an offline study method instead:\n\n1. Split the topic into 25-minute blocks.\n2. Recall key ideas without notes, then check gaps.\n3. Solve 3–5 practice questions and log mistakes.", "Offline fallback"
    q = question.lower()
    if any(word in q for word in ["explain", "what is", "meaning", "define"]):
        answer = ("I’m running in **offline assistant mode**, so I won’t invent a textbook explanation without the exact topic material. "
                  "Try this structure for your topic:\n\n1. Write a one-sentence definition in your own words.\n2. Identify the key steps or components.\n3. Work through one simple example.\n4. Explain when the concept is useful.\n5. Test yourself without looking at notes.\n\nPaste your notes or a specific passage and I can help you break it down.")
    elif any(word in q for word in ["plan", "revision", "revise", "schedule"]):
        answer = ("**A practical revision cycle**\n\n- **First pass (40%)**: understand the concept and make a one-page summary.\n- **Active recall (30%)**: close your notes and write what you remember.\n- **Practice (20%)**: solve questions under exam-like conditions.\n- **Error review (10%)**: record mistakes and revisit them tomorrow.\n\nPrioritize topics with the highest score in the Priority page, and keep each session focused on one outcome.")
    else:
        answer = ("**Study coach suggestion**\n\n1. Define one measurable outcome for this session.\n2. Study for 25 minutes, then take a 5-minute break.\n3. Use active recall rather than rereading.\n4. Finish with 3 practice questions and note what remains unclear.\n\nFor a personalized plan, mention the subject, exam date, and how much time you have.")
    return answer, "Offline fallback"


def add_topic(subject, name, difficulty, hours):
    subject["topics"].append({"id": str(uuid.uuid4()), "name": name.strip(), "difficulty": difficulty, "estimated_hours": float(hours), "completed": False})


data = load_data()
subjects = data["subjects"]

# Sidebar navigation and settings
with st.sidebar:
    st.markdown("# 🎓 StudyMate AI")
    st.caption("Intelligent Student Study Planner")
    page = st.radio("Navigate", ["Dashboard", "Study Planner", "Smart Timetable", "Priority Engine", "Tasks & Progress", "AI Study Assistant"], label_visibility="collapsed")
    st.divider()
    st.markdown("**Your study settings**")
    new_daily = st.number_input("Available study hours/day", min_value=0.5, max_value=16.0, step=0.5, value=float(data["settings"].get("daily_hours", 3.0)))
    new_start = st.time_input("Study window starts", value=datetime.strptime(data["settings"].get("start_time", "17:00"), "%H:%M").time())
    new_end = st.time_input("Study window ends", value=datetime.strptime(data["settings"].get("end_time", "21:00"), "%H:%M").time())
    if st.button("Save study settings", use_container_width=True):
        if new_end <= new_start:
            st.error("End time must be later than start time on the same day.")
        else:
            data["settings"] = {"daily_hours": float(new_daily), "start_time": new_start.strftime("%H:%M"), "end_time": new_end.strftime("%H:%M")}
            save_data()
            st.success("Settings saved.")
            st.rerun()
    st.divider()
    if st.button("↻ Reset demo data", use_container_width=True):
        st.session_state.data = normalize_data(sample_data())
        save_data()
        st.session_state.pop("task_editor", None)
        st.success("Demo data restored.")
        st.rerun()
    st.caption("Data is stored locally in studymate_data.json.")

# Global data snapshots
data = st.session_state.data
subjects = data["subjects"]
tasks_df = priority_table(data)
schedule_df = generate_schedule(data)
all_topics = [t for s in subjects for t in s["topics"]]
completed_count = sum(bool(t["completed"]) for t in all_topics)
topic_count = len(all_topics)
completion = completed_count / topic_count if topic_count else 0
pending_hours = sum(float(t.get("estimated_hours", 1)) for t in all_topics if not t["completed"])
today_tasks = schedule_df[schedule_df["Date"] == date.today()] if not schedule_df.empty else pd.DataFrame()
upcoming = sorted([s for s in subjects if date.fromisoformat(s["exam_date"]) >= date.today()], key=lambda s: s["exam_date"])

def page_header(title, subtitle):
    st.markdown(f"<div class='page-head'><div><div class='eyebrow'>STUDYMATE WORKSPACE</div><h1>{title}</h1><p>{subtitle}</p></div></div>", unsafe_allow_html=True)

st.markdown("""
<style>
:root { --sm-ink:#182230; --sm-muted:#667085; --sm-line:#e8ebf2; }
.block-container { padding-top: 1.6rem; max-width: 1450px; }
.page-head { padding: 4px 0 18px; }
.page-head h1 { margin: 2px 0 4px; font-size: 2.1rem; letter-spacing: -.04em; color: var(--sm-ink); }
.page-head p { margin:0; color:var(--sm-muted); font-size:1rem; }
.eyebrow { font-size:.72rem; letter-spacing:.15em; font-weight:800; color:#5b6cff; }
.metric-card { background:linear-gradient(145deg,#fff,#fafbff); border:1px solid #e7eaf3; border-radius:16px; padding:18px 20px; min-height:116px; box-shadow:0 4px 16px rgba(20,30,60,.035); }
.metric-label { color:#667085; font-size:.86rem; font-weight:600; }
.metric-value { color:#182230; font-size:1.8rem; font-weight:750; letter-spacing:-.04em; margin-top:7px; }
.metric-note { color:#7c8798; font-size:.78rem; margin-top:2px; }
.section-title { font-size:1.1rem; font-weight:750; margin:8px 0 10px; color:#182230; }
div[data-testid="stMetric"] { background:#fff; border:1px solid #e7eaf3; padding:15px 17px; border-radius:14px; }
.stButton>button { border-radius:10px; font-weight:600; }
[data-testid="stSidebar"] { border-right:1px solid #edf0f6; }
</style>
""", unsafe_allow_html=True)

if page == "Dashboard":
    page_header("Good to see you 👋", "A clear view of what to study next, and how close you are to exam-ready.")
    st.caption(f"Today is {date.today().strftime('%A, %d %B %Y')} · Demo data is ready to explore.")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Today's study hours", f"{today_tasks['Hours'].sum() if not today_tasks.empty else 0:.1f} h", "Planned for today")
    c2.metric("Tasks completed", f"{completed_count}/{topic_count}", f"{completion:.0%} overall progress")
    c3.metric("Study hours remaining", f"{pending_hours:.1f} h", "Across unfinished topics")
    c4.metric("Upcoming exams", len(upcoming), "Future exam dates")
    st.progress(completion, text=f"Overall topic completion · {completion:.0%}")
    left, right = st.columns([1.35, 1])
    with left:
        st.markdown('<div class="section-title">Today’s plan</div>', unsafe_allow_html=True)
        if today_tasks.empty:
            st.info("No sessions were generated for today. Add topics, check exam dates, or increase your available study time.")
        else:
            show = today_tasks[["Start", "End", "Subject", "Topic", "Hours", "Priority score"]].copy()
            show["Hours"] = show["Hours"].map(lambda x: f"{x:.1f} h")
            st.dataframe(show, hide_index=True, use_container_width=True)
            if st.button("Open task manager →", key="dash_tasks"):
                st.session_state.page_jump = "Tasks & Progress"
                st.rerun()
    with right:
        st.markdown('<div class="section-title">Upcoming exams</div>', unsafe_allow_html=True)
        if upcoming:
            for s in upcoming[:4]:
                days = (date.fromisoformat(s["exam_date"]) - date.today()).days
                st.markdown(f"**{s['name']}**  \n`{date.fromisoformat(s['exam_date']).strftime('%d %b')}` · {days} day(s) left")
                st.progress(max(0, min(1, 1 - days/30)), text=f"{s['difficulty']} · subject priority {s['priority']}/5")
        else:
            st.info("No upcoming exams. Add an exam date in Study Planner.")
    st.markdown('<div class="section-title">Study load by subject</div>', unsafe_allow_html=True)
    if subjects:
        subject_hours = []
        for s in subjects:
            hrs = sum(float(t.get("estimated_hours", 1)) for t in s["topics"] if not t["completed"])
            subject_hours.append({"Subject": s["name"], "Hours remaining": hrs})
        fig = px.bar(pd.DataFrame(subject_hours), x="Subject", y="Hours remaining", color="Subject", color_discrete_sequence=SUBJECT_COLORS)
        fig.update_layout(showlegend=False, margin=dict(l=8,r=8,t=15,b=8), height=280, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", yaxis_title="Hours", xaxis_title="")
        st.plotly_chart(fig, use_container_width=True)

elif page == "Study Planner":
    page_header("Personalized study planner", "Add subjects and topics. StudyMate will recalculate priorities and schedule from your data.")
    with st.expander("＋ Add a subject", expanded=not bool(subjects)):
        with st.form("add_subject_form", clear_on_submit=True):
            col1, col2, col3 = st.columns([1.4, 1, 1])
            name = col1.text_input("Subject name *", placeholder="e.g. Operating Systems")
            exam = col2.date_input("Exam date *", value=date.today() + timedelta(days=7), min_value=date(2000,1,1))
            diff = col3.selectbox("Overall difficulty", list(DIFFICULTIES.keys()), index=1)
            priority = st.slider("Subject importance", 1, 5, 3, help="Higher value means this subject matters more to your current plan.")
            submitted = st.form_submit_button("Add subject", type="primary")
            if submitted:
                if not name.strip():
                    st.error("Enter a subject name.")
                elif any(s["name"].strip().lower() == name.strip().lower() for s in subjects):
                    st.error("A subject with this name already exists.")
                else:
                    subjects.append({"id": str(uuid.uuid4()), "name": name.strip(), "exam_date": exam.isoformat(), "difficulty": diff, "priority": priority, "topics": []})
                    save_data(); st.success("Subject added."); st.rerun()
    if subjects:
        st.markdown("### Your subjects")
        for s in subjects:
            with st.container(border=True):
                top = st.columns([2, 1.2, 1, .6])
                top[0].markdown(f"**{s['name']}**")
                top[1].caption(f"Exam: {date.fromisoformat(s['exam_date']).strftime('%d %b %Y')}")
                top[2].caption(f"{s['difficulty']} · priority {s['priority']}/5")
                if top[3].button("Delete", key=f"del_{s['id']}"):
                    data["subjects"] = [x for x in subjects if x["id"] != s["id"]]
                    save_data(); st.rerun()
                with st.form(f"topic_form_{s['id']}", clear_on_submit=True):
                    a,b,c = st.columns([2,1,1])
                    topic_name = a.text_input("Topic name *", key=f"topic_name_{s['id']}")
                    topic_diff = b.selectbox("Difficulty", list(DIFFICULTIES.keys()), index=list(DIFFICULTIES.keys()).index(s["difficulty"]), key=f"topic_diff_{s['id']}")
                    hours = c.number_input("Estimated hours", min_value=.25, max_value=40.0, value=1.0, step=.25, key=f"hours_{s['id']}")
                    if st.form_submit_button("＋ Add topic"):
                        if not topic_name.strip():
                            st.error("Enter a topic name.")
                        elif any(t["name"].lower() == topic_name.strip().lower() for t in s["topics"]):
                            st.error("That topic already exists in this subject.")
                        else:
                            add_topic(s, topic_name, topic_diff, hours); save_data(); st.rerun()
                if s["topics"]:
                    st.caption(f"{sum(t['completed'] for t in s['topics'])}/{len(s['topics'])} topics complete")
                    st.write(" · ".join([f"{'✓ ' if t['completed'] else ''}{t['name']} ({t['estimated_hours']:g}h)" for t in s["topics"]]))
    else:
        st.info("Add your first subject to start building a personalized plan.")

elif page == "Smart Timetable":
    page_header("Smart timetable", "A conflict-free schedule generated from your topics, deadlines, difficulty, and available hours.")
    st.info(f"Planning window: {data['settings']['start_time']}–{data['settings']['end_time']} · daily cap {data['settings']['daily_hours']:g} h. Sessions are capped at 1 hour and placed sequentially.")
    horizon = st.slider("Plan next how many days?", 1, 14, 7)
    sched = generate_schedule(data, horizon=horizon)
    if sched.empty:
        st.warning("No eligible study sessions found. Add unfinished topics with future exam dates and check your study window.")
    else:
        sched["Date"] = pd.to_datetime(sched["Date"])
        sched["Day"] = sched["Date"].dt.strftime("%a, %d %b")
        st.metric("Scheduled study time", f"{sched['Hours'].sum():.1f} hours", f"{sched['Date'].nunique()} days with sessions")
        st.dataframe(sched[["Day","Start","End","Subject","Topic","Hours","Priority score"]], hide_index=True, use_container_width=True)
        sched["StartDT"] = pd.to_datetime(sched["Date"].dt.strftime("%Y-%m-%d") + " " + sched["Start"])
        sched["EndDT"] = pd.to_datetime(sched["Date"].dt.strftime("%Y-%m-%d") + " " + sched["End"])
        fig = px.timeline(sched, x_start="StartDT", x_end="EndDT", y="Day", color="Subject", hover_name="Topic", color_discrete_sequence=SUBJECT_COLORS)
        fig.update_yaxes(autorange="reversed", title="")
        fig.update_layout(height=max(300, 65 * sched["Day"].nunique()), margin=dict(l=8,r=8,t=20,b=8), xaxis_title="Study window", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
        csv = sched[["Date","Start","End","Subject","Topic","Hours","Priority score"]].to_csv(index=False).encode("utf-8")
        st.download_button("Download timetable CSV", csv, "studymate_timetable.csv", "text/csv")
        st.caption("The generator uses a transparent rule-based priority score, not a trained machine-learning model. It schedules each session once, in sequence, within the daily window and daily hour cap.")
    if st.button("Recalculate timetable", type="primary"):
        st.rerun()

elif page == "Priority Engine":
    page_header("Priority recommendation engine", "Understand what deserves attention first, with an explainable score for every topic.")
    st.caption("Score combines exam urgency (40%), difficulty (30%), remaining workload (20%), and subject importance (10%). Completed topics score zero.")
    if tasks_df.empty:
        st.info("Add subjects and topics to see recommendations.")
    else:
        display = tasks_df[["Subject","Topic","Exam date","Days left","Difficulty","Hours left","Completed","Priority score","Why this rank"]].copy()
        display["Exam date"] = pd.to_datetime(display["Exam date"]).dt.strftime("%d %b %Y")
        st.dataframe(display, hide_index=True, use_container_width=True)
        active = tasks_df[(~tasks_df["Completed"]) & (tasks_df["Days left"] >= 0)].sort_values("Priority score", ascending=False).head(3)
        st.markdown("### Focus next")
        if active.empty:
            st.success("No eligible unfinished topics with upcoming exams. Add new topics or update past exam dates.")
        else:
            for _, r in active.iterrows():
                st.markdown(f"**{r['Subject']} · {r['Topic']}** — score **{r['Priority score']}/100**  \n{r['Why this rank']}")

elif page == "Tasks & Progress":
    page_header("Tasks & progress", "Mark topics complete, adjust estimates, and see how your work is adding up.")
    if not all_topics:
        st.info("No topics yet. Add some in Study Planner.")
    else:
        for s in subjects:
            if not s["topics"]:
                continue
            st.markdown(f"### {s['name']}")
            for t in s["topics"]:
                with st.container(border=True):
                    c1,c2,c3,c4 = st.columns([2.3, .8, .8, .8])
                    checked = c1.checkbox(t["name"], value=bool(t["completed"]), key=f"done_{t['id']}")
                    hours_val = c2.number_input("Hours", min_value=.25, max_value=40.0, value=float(t["estimated_hours"]), step=.25, key=f"edit_hours_{t['id']}")
                    diff_val = c3.selectbox("Difficulty", list(DIFFICULTIES.keys()), index=list(DIFFICULTIES.keys()).index(t["difficulty"]), key=f"edit_diff_{t['id']}")
                    if c4.button("Save", key=f"save_topic_{t['id']}"):
                        t["completed"] = checked
                        t["estimated_hours"] = float(hours_val)
                        t["difficulty"] = diff_val
                        save_data(); st.success("Topic updated."); st.rerun()
                    if checked != bool(t["completed"]):
                        t["completed"] = checked
                        save_data()
        st.divider()
        c1,c2 = st.columns(2)
        c1.metric("Completed topics", f"{completed_count}/{topic_count}")
        c2.metric("Completion rate", f"{completion:.0%}")
        if topic_count:
            status = pd.DataFrame([{"Status":"Completed" if t["completed"] else "Pending","Count":1} for t in all_topics]).groupby("Status", as_index=False).sum()
            fig = px.pie(status, values="Count", names="Status", hole=.65, color_discrete_sequence=["#13B8A6","#E4E7EC"])
            fig.update_layout(height=280, margin=dict(l=5,r=5,t=15,b=5), legend_title="")
            st.plotly_chart(fig, use_container_width=True)
        subject_progress = []
        for s in subjects:
            total = len(s["topics"])
            done = sum(t["completed"] for t in s["topics"])
            subject_progress.append({"Subject":s["name"],"Completed":done,"Pending":total-done,"Progress":done/total if total else 0})
        st.markdown("### Subject-wise progress")
        for r in subject_progress:
            st.write(f"**{r['Subject']}** · {r['Completed']}/{r['Completed']+r['Pending']} topics")
            st.progress(r["Progress"])

elif page == "AI Study Assistant":
    page_header("AI study assistant", "Get practical revision strategies and topic-study guidance, with an offline fallback.")
    has_key = bool(os.getenv("OPENAI_API_KEY", "").strip())
    st.caption("Assistant mode: optional API connected" if has_key else "Assistant mode: offline study coach · no API key required")
    context = f"Subjects: {', '.join(s['name'] for s in subjects) or 'none yet'}. Upcoming exams: {', '.join(s['name'] + ' on ' + s['exam_date'] for s in upcoming) or 'none'}."
    with st.form("assistant_form", clear_on_submit=False):
        question = st.text_area("What would you like help with?", placeholder="e.g. Make a 3-day revision plan for Database Systems...", height=120)
        ask = st.form_submit_button("Get study guidance", type="primary")
    if ask:
        if not question.strip():
            st.warning("Enter a question or topic first.")
        else:
            answer, mode = ai_assistant_reply(question.strip(), context)
            st.session_state.last_assistant_answer = answer
            st.session_state.last_assistant_mode = mode
    if st.session_state.get("last_assistant_answer"):
        st.markdown("### Study guidance")
        st.caption(st.session_state.get("last_assistant_mode", "Offline fallback"))
        st.markdown(st.session_state.last_assistant_answer)
    st.markdown("### Quick prompts")
    quick_cols = st.columns(3)
    prompts = ["Build a revision plan for my nearest exam", "How should I use active recall?", "Give me a focused 60-minute study routine"]
    for i, prompt in enumerate(prompts):
        if quick_cols[i].button(prompt, key=f"quick_{i}"):
            answer, mode = ai_assistant_reply(prompt, context)
            st.session_state.last_assistant_answer = answer
            st.session_state.last_assistant_mode = mode
            st.rerun()

# Footer
st.divider()
st.caption("StudyMate AI · Hackathon prototype · Priority recommendations are explainable rules, not a trained ML model.")
