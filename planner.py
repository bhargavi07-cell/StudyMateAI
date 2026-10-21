from datetime import date, datetime, timedelta
import pandas as pd

DIFFICULTIES = {"Easy": 1, "Medium": 2, "Hard": 3}


def get_topic_rows(data, today=None):
    today = today or date.today()
    rows = []
    for subject in data.get("subjects", []):
        due = date.fromisoformat(subject["exam_date"])
        days_left = (due - today).days
        for topic in subject.get("topics", []):
            difficulty = DIFFICULTIES.get(topic.get("difficulty", "Medium"), 2)
            remaining = max(0.0, float(topic.get("estimated_hours", 1.0)))
            completed = bool(topic.get("completed", False))
            urgency = 0 if days_left < 0 else max(0, 14 - days_left) / 14
            remaining_factor = min(1.0, remaining / 2.0)
            score = round((urgency * 40) + (difficulty / 3 * 30) + (remaining_factor * 20) + (int(subject.get("priority", 3)) / 5 * 10), 1)
            if not completed:
                if days_left < 0:
                    reason = "Exam date has passed; review the date before planning."
                else:
                    parts = []
                    if days_left <= 3:
                        parts.append(f"exam is in {days_left} day(s)")
                    elif days_left <= 7:
                        parts.append(f"exam is approaching ({days_left} days)")
                    if difficulty == 3:
                        parts.append("high difficulty")
                    if remaining >= 1.5:
                        parts.append(f"{remaining:g} hours remain")
                    if int(subject.get("priority", 3)) >= 4:
                        parts.append("subject priority is high")
                    reason = "Prioritized because " + (", ".join(parts) if parts else "it has remaining work and a future exam") + "."
            else:
                score = 0.0
                reason = "Already marked complete."
            rows.append({
                "topic_id": topic["id"], "subject_id": subject["id"], "Subject": subject["name"],
                "Topic": topic["name"], "Exam date": due, "Days left": days_left,
                "Difficulty": topic.get("difficulty", "Medium"), "Hours left": remaining,
                "Completed": completed, "Priority score": score, "Why this rank": reason
            })
    return rows


def generate_schedule(data, start_day=None, horizon=7):
    """Greedy priority scheduler. Sequential sessions fit configured daily window and cap."""
    start_day = start_day or date.today()
    settings = data.get("settings", {})
    daily_hours = float(settings.get("daily_hours", 3))
    start_t = datetime.strptime(settings.get("start_time", "17:00"), "%H:%M").time()
    end_t = datetime.strptime(settings.get("end_time", "21:00"), "%H:%M").time()
    start_minutes = start_t.hour * 60 + start_t.minute
    end_minutes = end_t.hour * 60 + end_t.minute
    window_hours = (end_minutes - start_minutes) / 60
    capacity = min(daily_hours, window_hours)
    columns = ["Date", "Start", "End", "Subject", "Topic", "Hours", "Priority score", "Status", "topic_id"]
    if capacity <= 0 or horizon <= 0:
        return pd.DataFrame(columns=columns)
    pending = [r.copy() for r in get_topic_rows(data, today=start_day)
               if not r["Completed"] and r["Days left"] >= 0 and r["Hours left"] > 0]
    pending.sort(key=lambda r: (-r["Priority score"], r["Exam date"], r["Topic"]))
    output = []
    for offset in range(horizon):
        day = start_day + timedelta(days=offset)
        remaining = capacity
        cursor = start_minutes
        for task in pending:
            if remaining <= 1e-6:
                break
            if task["Hours left"] <= 1e-6 or day > task["Exam date"]:
                continue
            take = min(float(task["Hours left"]), remaining, 1.0)
            if take <= 0:
                continue
            end_cursor = cursor + int(round(take * 60))
            output.append({
                "Date": day, "Start": f"{cursor//60:02d}:{cursor%60:02d}",
                "End": f"{end_cursor//60:02d}:{end_cursor%60:02d}",
                "Subject": task["Subject"], "Topic": task["Topic"], "Hours": round(take, 2),
                "Priority score": task["Priority score"], "Status": "Pending", "topic_id": task["topic_id"]
            })
            cursor = end_cursor
            remaining -= take
            task["Hours left"] = round(float(task["Hours left"]) - take, 3)
    return pd.DataFrame(output, columns=columns)
