import json
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Dict, List
from uuid import uuid4

from flask import Flask, redirect, render_template, request, url_for


app = Flask(__name__)
app.config["SECRET_KEY"] = "dev-secret"

# Exercise catalog (placeholder data – replace with DB/CMS later)
BODY_PARTS: Dict[str, Dict] = {
    "chest": {
        "label": "Chest",
        "color": "#2f855a",
        "exercises": [
            "Barbell Bench Press",
            "Dumbbell Bench Press",
            "Incline Dumbbell Press",
            "Decline Bench Press",
            "Machine Chest Press",
            "Dumbbell Fly",
            "Cable Crossover",
            "Push-up",
        ],
    },
    "shoulders": {
        "label": "Shoulders",
        "color": "#38a169",
        "exercises": [
            "Overhead Press",
            "Standing Military Press",
            "Seated Dumbbell Press",
            "Arnold Press",
            "Lateral Raise",
            "Rear Delt Fly",
            "Face Pull",
            "Upright Row",
        ],
    },
    "arms": {
        "label": "Arms",
        "color": "#277a49",
        "exercises": [
            "Barbell Curl",
            "Preacher Curl",
            "Hammer Curl",
            "Cable Curl",
            "Triceps Pushdown",
            "Overhead Triceps Extension",
            "Skull Crusher",
            "Bench Dip",
        ],
    },
    "back": {
        "label": "Back",
        "color": "#22543d",
        "exercises": [
            "Deadlift",
            "Romanian Deadlift",
            "Lat Pulldown",
            "Pull-up",
            "Bent Over Row",
            "T-Bar Row",
            "Single-Arm Dumbbell Row",
            "Seated Cable Row",
        ],
    },
    "legs": {
        "label": "Legs",
        "color": "#1b4332",
        "exercises": [
            "Back Squat",
            "Front Squat",
            "Leg Press",
            "Walking Lunge",
            "Romanian Deadlift",
            "Leg Extension",
            "Leg Curl",
            "Calf Raise",
        ],
    },
}

# Simple in-memory stores
WORKOUTS: List[Dict] = []
NUTRITION_LOGS: List[Dict] = []


# --------------------------------------------------------------------------- #
# Helper utilities
# --------------------------------------------------------------------------- #

def _has_exercise(body_part_key: str, exercise_name: str) -> bool:
    exercises = BODY_PARTS.get(body_part_key, {}).get("exercises", [])
    return exercise_name in exercises


def build_sessions() -> List[Dict]:
    """Collapse movement-level workouts into session-level containers."""
    sessions_map: Dict[str, Dict] = {}
    sorted_workouts = sorted(
        WORKOUTS,
        key=lambda item: (
            item["date"],
            item.get("session_id") or "",
            item.get("body_part"),
            item.get("name"),
        ),
    )

    for idx, entry in enumerate(sorted_workouts):
        sid = entry.get("session_id") or f"legacy-{entry['date'].strftime('%Y%m%d')}-{idx}"
        session = sessions_map.setdefault(
            sid,
            {
                "id": sid,
                "date": entry["date"],
                "session_note": entry.get("session_note", ""),
                "body_weight": entry.get("body_weight"),
                "calories_target": 0.0,
                "calories_burned": 0.0,
                "protein_g": 0.0,
                "fat_g": 0.0,
                "carb_g": 0.0,
                "duration_minutes": 0.0,
                "movements": [],
                "total_sets": 0,
                "total_reps": 0,
            },
        )

        if not session["movements"]:
            session["calories_target"] = entry.get("calories_target", 0.0)
            session["calories_burned"] = entry.get("calories_burned", 0.0)
            session["protein_g"] = entry.get("protein_g", 0.0)
            session["fat_g"] = entry.get("fat_g", 0.0)
            session["carb_g"] = entry.get("carb_g", 0.0)
            session["duration_minutes"] = entry.get("session_duration_minutes", 0.0)
            session["body_weight"] = entry.get("body_weight") or session["body_weight"]

        movement_total_reps = entry.get("total_reps")
        if movement_total_reps is None:
            movement_total_reps = entry.get("sets", 0) * entry.get("reps", 0)

        session["movements"].append(
            {
                "body_part": entry["body_part"],
                "body_part_label": entry["body_part_label"],
                "name": entry["name"],
                "weight": entry["weight"],
                "sets": entry["sets"],
                "reps": entry["reps"],
                "total_reps": movement_total_reps,
                "notes": entry.get("notes", ""),
            }
        )
        session["total_sets"] += entry.get("sets", 0)
        session["total_reps"] += movement_total_reps

    sessions = list(sessions_map.values())
    sessions.sort(key=lambda s: (s["date"], s["id"]), reverse=True)
    return sessions


def build_schedule_map(sessions: List[Dict]) -> Dict[str, List[Dict]]:
    schedule = defaultdict(list)
    for session in sessions:
        date_key = session["date"].strftime("%Y-%m-%d")
        for movement in session["movements"]:
            payload = {
                **movement,
                "session_note": session["session_note"],
                "session_id": session["id"],
                "calories_burned": session["calories_burned"],
                "calories_target": session["calories_target"],
                "protein_g": session["protein_g"],
                "fat_g": session["fat_g"],
                "carb_g": session["carb_g"],
            }
            schedule[date_key].append(payload)
    return schedule


def build_sessions_by_date(sessions: List[Dict]) -> Dict[date, List[Dict]]:
    by_date: Dict[date, List[Dict]] = defaultdict(list)
    for session in sessions:
        by_date[session["date"]].append(session)
    return by_date


def build_nutrition_by_date() -> Dict[date, List[Dict]]:
    by_date: Dict[date, List[Dict]] = defaultdict(list)
    for entry in NUTRITION_LOGS:
        by_date[entry["date"]].append(entry)
    return by_date


def get_latest_body_weight(default: float = 70.0) -> float:
    sessions = build_sessions()
    for session in sessions:
        if session.get("body_weight"):
            return session["body_weight"]
    for entry in sorted(NUTRITION_LOGS, key=lambda item: item["date"], reverse=True):
        if entry.get("weight"):
            return entry["weight"]
    return default


def _baseline_macros(weight: float) -> Dict[str, float]:
    calories = round(weight * 30.0, 1)
    protein = round(weight * 1.6, 1)
    fat = round(weight * 0.8, 1)
    remaining = calories - (protein * 4 + fat * 9)
    carb = round(max(remaining / 4, 0), 1)
    return {
        "calories": calories,
        "protein": protein,
        "fat": fat,
        "carb": carb,
    }


def _sum_nutrition(entries: List[Dict]) -> Dict[str, float]:
    totals = {"calories": 0.0, "protein": 0.0, "fat": 0.0, "carb": 0.0}
    for entry in entries:
        totals["calories"] += entry.get("calories", 0.0)
        totals["protein"] += entry.get("protein", 0.0)
        totals["fat"] += entry.get("fat", 0.0)
        totals["carb"] += entry.get("carb", 0.0)
    for key in totals:
        totals[key] = round(totals[key], 1)
    return totals


def get_daily_summary(
    target_date: date,
    sessions_by_date: Dict[date, List[Dict]],
    nutrition_by_date: Dict[date, List[Dict]],
) -> Dict:
    sessions_today = sessions_by_date.get(target_date, [])
    nutrition_today = nutrition_by_date.get(target_date, [])

    if sessions_today:
        calories_target = sum(session.get("calories_target", 0.0) for session in sessions_today)
        protein_target = sum(session.get("protein_g", 0.0) for session in sessions_today)
        fat_target = sum(session.get("fat_g", 0.0) for session in sessions_today)
        carb_target = sum(session.get("carb_g", 0.0) for session in sessions_today)
        if calories_target == 0:
            reference_weight = sessions_today[0].get("body_weight") or get_latest_body_weight()
            baseline = _baseline_macros(reference_weight)
            calories_target = baseline["calories"]
            protein_target = baseline["protein"]
            fat_target = baseline["fat"]
            carb_target = baseline["carb"]
    else:
        weight = get_latest_body_weight()
        baseline = _baseline_macros(weight)
        calories_target = baseline["calories"]
        protein_target = baseline["protein"]
        fat_target = baseline["fat"]
        carb_target = baseline["carb"]

    target = {
        "calories": round(calories_target, 1),
        "protein": round(protein_target, 1),
        "fat": round(fat_target, 1),
        "carb": round(carb_target, 1),
    }

    consumed = _sum_nutrition(nutrition_today)

    balance = {
        key: round(target[key] - consumed[key], 1)
        for key in target
    }

    burned = sum(session.get("calories_burned", 0.0) for session in sessions_today)
    duration = sum(session.get("duration_minutes", 0.0) for session in sessions_today)

    return {
        "date": target_date,
        "target": target,
        "consumed": consumed,
        "balance": balance,
        "sessions": sessions_today,
        "session_count": len(sessions_today),
        "calories_burned": round(burned, 1),
        "duration_minutes": round(duration, 1),
        "body_weight": get_latest_body_weight(),
    }


def get_recent_intake_series(
    days: int,
    sessions_by_date: Dict[date, List[Dict]],
    nutrition_by_date: Dict[date, List[Dict]],
) -> List[Dict]:
    today = date.today()
    series: List[Dict] = []
    for offset in range(days - 1, -1, -1):
        day = today - timedelta(days=offset)
        summary = get_daily_summary(day, sessions_by_date, nutrition_by_date)
        series.append(
            {
                "date": day,
                "calories_target": summary["target"]["calories"],
                "calories_consumed": summary["consumed"]["calories"],
                "calories_balance": summary["balance"]["calories"],
            }
        )
    return series


def get_grouped_workouts() -> Dict[str, Dict[str, List[Dict]]]:
    """Legacy helper for dashboard timeline grouped by date/body part."""
    grouped: Dict[str, Dict[str, List[Dict]]] = defaultdict(lambda: defaultdict(list))
    for entry in sorted(
        WORKOUTS,
        key=lambda item: (item["date"], item["body_part_label"], item["name"]),
    ):
        date_key = entry["date"].strftime("%Y-%m-%d")
        grouped[date_key][entry["body_part_label"]].append(entry)
    return grouped


def parse_date(value: str, default: date) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return default


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #

@app.route("/")
def home():
    sessions = build_sessions()
    sessions_by_date = build_sessions_by_date(sessions)
    nutrition_by_date = build_nutrition_by_date()

    today = date.today()
    summary = get_daily_summary(today, sessions_by_date, nutrition_by_date)
    recent_sessions = sessions[:4]
    schedule_map = build_schedule_map(sessions)
    intake_series = get_recent_intake_series(7, sessions_by_date, nutrition_by_date)

    return render_template(
        "home.html",
        summary=summary,
        recent_sessions=recent_sessions,
        schedule_json=json.dumps(schedule_map),
        intake_series=intake_series,
    )


@app.route("/dashboard")
def dashboard():
    grouped = get_grouped_workouts()
    return render_template(
        "index.html",
        grouped_workouts=grouped,
        has_workouts=bool(WORKOUTS),
        body_parts=BODY_PARTS,
    )


@app.route("/workouts/new", methods=["GET", "POST"])
def new_workouts():
    if request.method == "POST":
        raw_date = request.form.get("workout_date", "").strip()
        payload_raw = request.form.get("session_payload", "").strip()
        session_note = request.form.get("session_note", "").strip()
        body_weight_raw = request.form.get("body_weight", "").strip()

        form_state = {
            "workout_date": raw_date,
            "session_note": session_note,
            "body_weight": body_weight_raw,
        }

        if not raw_date or not payload_raw:
            return render_template(
                "workouts_new.html",
                error="Date and at least one movement are required.",
                body_parts=BODY_PARTS,
                form=form_state,
                form_payload=payload_raw,
            )

        if not body_weight_raw:
            return render_template(
                "workouts_new.html",
                error="Please provide your body weight to estimate energy and macro needs.",
                body_parts=BODY_PARTS,
                form=form_state,
                form_payload=payload_raw,
            )

        workout_date = parse_date(raw_date, default=date.today())

        try:
            body_weight = float(body_weight_raw)
            if body_weight <= 0:
                raise ValueError
        except ValueError:
            return render_template(
                "workouts_new.html",
                error="Body weight must be a positive number.",
                body_parts=BODY_PARTS,
                form=form_state,
                form_payload=payload_raw,
            )

        try:
            parsed_payload = json.loads(payload_raw)
        except json.JSONDecodeError:
            return render_template(
                "workouts_new.html",
                error="The submitted movements could not be read. Try adding them again.",
                body_parts=BODY_PARTS,
                form=form_state,
                form_payload=payload_raw,
            )

        if not isinstance(parsed_payload, list) or len(parsed_payload) == 0:
            return render_template(
                "workouts_new.html",
                error="Please add at least one movement before saving.",
                body_parts=BODY_PARTS,
                form=form_state,
                form_payload=payload_raw,
            )

        session_id = str(uuid4())
        entries_to_store: List[Dict] = []
        total_sets = 0

        for idx, entry in enumerate(parsed_payload, start=1):
            body_part = str(entry.get("body_part", "")).strip()
            exercise = str(entry.get("exercise", "")).strip()
            sets_raw = entry.get("sets", "")
            reps_raw = entry.get("reps", "")
            weight_raw = entry.get("weight", "")
            note = str(entry.get("note", "") or "").strip()

            if not body_part or not exercise:
                return render_template(
                    "workouts_new.html",
                    error=f"Movement #{idx} is missing a body part or exercise.",
                    body_parts=BODY_PARTS,
                    form=form_state,
                    form_payload=payload_raw,
                )

            if body_part not in BODY_PARTS or not _has_exercise(body_part, exercise):
                return render_template(
                    "workouts_new.html",
                    error=f"Movement #{idx} references an invalid body part / exercise combination.",
                    body_parts=BODY_PARTS,
                    form=form_state,
                    form_payload=payload_raw,
                )

            try:
                sets_value = int(sets_raw) if str(sets_raw).strip() else 0
                reps_value = int(reps_raw) if str(reps_raw).strip() else 0
                weight_value = float(weight_raw) if str(weight_raw).strip() else 0.0
            except (TypeError, ValueError):
                return render_template(
                    "workouts_new.html",
                    error=f"Movement #{idx} contains a numeric field with an invalid format.",
                    body_parts=BODY_PARTS,
                    form=form_state,
                    form_payload=payload_raw,
                )

            total_sets += sets_value
            total_reps = sets_value * reps_value
            notes_combined = note or session_note

            entries_to_store.append(
                {
                    "date": workout_date,
                    "body_part": body_part,
                    "body_part_label": BODY_PARTS[body_part]["label"],
                    "name": exercise,
                    "weight": weight_value,
                    "sets": sets_value,
                    "reps": reps_value,
                    "notes": notes_combined,
                    "entry_note": note,
                    "session_note": session_note,
                    "session_id": session_id,
                    "total_reps": total_reps,
                }
            )

        duration_hours = max((total_sets * 3) / 60.0, 0.25)
        calories_burned = round(body_weight * 6.0 * duration_hours, 1)
        caloric_surplus = body_weight * 5  # ~300 kcal surplus target
        calories_target = round(calories_burned + caloric_surplus, 1)
        protein_g = round(body_weight * 2.0, 1)
        fat_g = round(body_weight * 0.9, 1)
        remaining_calories = calories_target - (protein_g * 4 + fat_g * 9)
        carb_g = round(max(remaining_calories / 4, 0), 1)

        for stored in entries_to_store:
            stored.update(
                {
                    "body_weight": body_weight,
                    "session_duration_minutes": round(duration_hours * 60, 1),
                    "calories_burned": calories_burned,
                    "calories_target": calories_target,
                    "protein_g": protein_g,
                    "fat_g": fat_g,
                    "carb_g": carb_g,
                }
            )

        WORKOUTS.extend(entries_to_store)
        return redirect(url_for("home"))

    return render_template("workouts_new.html", body_parts=BODY_PARTS, form=None, form_payload="")


@app.route("/analytics")
def analytics():
    serialized_workouts = [
        {
            "date": entry["date"].strftime("%Y-%m-%d"),
            "body_part": entry["body_part"],
            "body_part_label": entry["body_part_label"],
            "name": entry["name"],
            "weight": entry["weight"],
            "sets": entry["sets"],
            "reps": entry["reps"],
        }
        for entry in WORKOUTS
    ]
    return render_template(
        "analytics.html",
        body_parts=BODY_PARTS,
        workouts_json=json.dumps(serialized_workouts),
    )


@app.route("/schedule")
def schedule():
    sessions = build_sessions()
    calendar_payload = build_schedule_map(sessions)
    return render_template(
        "schedule.html",
        schedule_json=json.dumps(calendar_payload),
        body_parts=BODY_PARTS,
    )


@app.route("/nutrition", methods=["GET", "POST"])
def nutrition():
    if request.method == "POST":
        raw_date = request.form.get("log_date") or date.today().isoformat()
        log_date = parse_date(raw_date, default=date.today())

        weight_raw = request.form.get("log_weight", "").strip()
        calories_raw = request.form.get("log_calories", "").strip()
        protein_raw = request.form.get("log_protein", "").strip()
        fat_raw = request.form.get("log_fat", "").strip()
        carb_raw = request.form.get("log_carb", "").strip()
        notes = request.form.get("log_notes", "").strip()

        try:
            weight = float(weight_raw) if weight_raw else None
        except ValueError:
            weight = None
        try:
            calories = float(calories_raw) if calories_raw else 0.0
        except ValueError:
            calories = 0.0
        try:
            protein = float(protein_raw) if protein_raw else 0.0
        except ValueError:
            protein = 0.0
        try:
            fat = float(fat_raw) if fat_raw else 0.0
        except ValueError:
            fat = 0.0
        try:
            carb = float(carb_raw) if carb_raw else 0.0
        except ValueError:
            carb = 0.0

        NUTRITION_LOGS.append(
            {
                "date": log_date,
                "weight": weight,
                "calories": calories,
                "protein": protein,
                "fat": fat,
                "carb": carb,
                "notes": notes,
            }
        )
        return redirect(url_for("nutrition"))

    logs_sorted = sorted(NUTRITION_LOGS, key=lambda item: item["date"], reverse=True)
    daily_totals = defaultdict(lambda: {"calories": 0.0, "protein": 0.0, "fat": 0.0, "carb": 0.0, "weight": None})
    for entry in logs_sorted:
        key = entry["date"].strftime("%Y-%m-%d")
        totals = daily_totals[key]
        totals["calories"] += entry.get("calories", 0.0)
        totals["protein"] += entry.get("protein", 0.0)
        totals["fat"] += entry.get("fat", 0.0)
        totals["carb"] += entry.get("carb", 0.0)
        totals["weight"] = entry.get("weight") or totals["weight"]

    for totals in daily_totals.values():
        for macro in ("calories", "protein", "fat", "carb"):
            totals[macro] = round(totals[macro], 1)

    daily_history = sorted(daily_totals.items(), key=lambda item: item[0], reverse=True)

    return render_template(
        "nutrition.html",
        logs=logs_sorted,
        daily_history=daily_history,
        latest_weight=get_latest_body_weight(),
        date=date,
    )


if __name__ == "__main__":
    app.run(debug=True, port=5050)
