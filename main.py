import os
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from database import db, create_document, get_documents
from schemas import Athlete, Exercise, Session, Attempt, Plan

app = FastAPI(title="Athlete Speed & Agility API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Athlete Speed & Agility Backend running"}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    return response

# Simple helper to get collection name from class name

def coll(model_cls):
    return model_cls.__name__.lower()

# Athletes

@app.post("/athletes")
def create_athlete(athlete: Athlete):
    new_id = create_document(coll(Athlete), athlete)
    return {"id": new_id}

@app.get("/athletes")
def list_athletes():
    docs = get_documents(coll(Athlete))
    return docs

# Exercises

@app.post("/exercises")
def create_exercise(exercise: Exercise):
    new_id = create_document(coll(Exercise), exercise)
    return {"id": new_id}

@app.get("/exercises")
def list_exercises(sport: Optional[str] = None):
    flt = {"sport": sport} if sport else {}
    docs = get_documents(coll(Exercise), flt)
    return docs

# Sessions

@app.post("/sessions")
def create_session(session: Session):
    data = session.model_dump()
    data["start_time"] = datetime.now(timezone.utc).isoformat()
    new_id = create_document(coll(Session), data)
    return {"id": new_id}

@app.get("/sessions")
def list_sessions(athlete_id: Optional[str] = None):
    flt = {"athlete_id": athlete_id} if athlete_id else {}
    return get_documents(coll(Session), flt)

@app.post("/sessions/{session_id}/complete")
def complete_session(session_id: str):
    if db is None:
        raise HTTPException(500, "Database not available")
    updated = db[coll(Session)].update_one({"_id": {"$eq": db[coll(Session)]._Document__codec_options.uuid_representation and None}}, {})
    # Simpler approach: set by filter on _id string matching
    try:
        from bson import ObjectId
        result = db[coll(Session)].update_one({"_id": ObjectId(session_id)}, {"$set": {"status": "completed", "end_time": datetime.now(timezone.utc).isoformat(), "updated_at": datetime.now(timezone.utc)}})
        if result.matched_count == 0:
            raise HTTPException(404, "Session not found")
    except Exception:
        # Fallback for string ids if any were inserted as strings
        result = db[coll(Session)].update_one({"_id": session_id}, {"$set": {"status": "completed", "end_time": datetime.now(timezone.utc).isoformat(), "updated_at": datetime.now(timezone.utc)}})
        if result.matched_count == 0:
            raise HTTPException(404, "Session not found")
    return {"status": "ok"}

# Attempts (real-time touch/laser hits)

@app.post("/attempts")
def record_attempt(attempt: Attempt):
    data = attempt.model_dump()
    data["ts"] = datetime.now(timezone.utc).isoformat()
    new_id = create_document(coll(Attempt), data)
    return {"id": new_id}

@app.get("/attempts")
def list_attempts(session_id: Optional[str] = None, exercise_id: Optional[str] = None, limit: int = 100):
    flt = {}
    if session_id:
        flt["session_id"] = session_id
    if exercise_id:
        flt["exercise_id"] = exercise_id
    return get_documents(coll(Attempt), flt, limit)

# Plans: upload favorite player video URL and get suggested drills

class PlanRequest(BaseModel):
    athlete_id: str
    sport: str
    video_url: Optional[str] = None
    goals: Optional[List[str]] = None

@app.post("/plans")
def create_plan(req: PlanRequest):
    # Very simple suggestion engine: map goals to exercise focus keywords
    goal_to_focus = {
        "speed": ["speed", "acceleration"],
        "agility": ["agility", "change of direction"],
        "reaction": ["reaction", "decision"],
        "footwork": ["footwork", "ladder"],
        "stamina": ["conditioning", "repeat sprint"]
    }
    # Build search terms
    focuses = []
    if req.goals:
        for g in req.goals:
            focuses.extend(goal_to_focus.get(g.lower(), [g.lower()]))
    # Find matching exercises for sport
    flt = {"sport": req.sport}
    exercises = get_documents(coll(Exercise), flt)
    suggestions = []
    if focuses:
        for ex in exercises:
            ex_focus = [f.lower() for f in (ex.get("focus") or [])]
            if any(f in ex_focus for f in focuses):
                suggestions.append(ex.get("name"))
    else:
        suggestions = [ex.get("name") for ex in exercises[:5]]

    plan_doc = {
        "athlete_id": req.athlete_id,
        "sport": req.sport,
        "video_url": req.video_url,
        "goals": req.goals or [],
        "exercise_suggestions": suggestions,
    }
    new_id = create_document(coll(Plan), plan_doc)
    return {"id": new_id, "exercise_suggestions": suggestions}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
