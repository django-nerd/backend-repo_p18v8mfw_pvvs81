"""
Database Schemas for Athlete Performance App

Each Pydantic model represents a collection in MongoDB. The collection name is the
lowercased class name (e.g., Athlete -> "athlete").
"""
from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional

class Athlete(BaseModel):
    name: str = Field(..., description="Athlete full name")
    email: Optional[str] = Field(None, description="Email address")
    primary_sport: Optional[str] = Field(None, description="Primary sport the athlete plays")
    age: Optional[int] = Field(None, ge=4, le=120)

class Exercise(BaseModel):
    name: str = Field(..., description="Exercise name")
    sport: str = Field(..., description="Associated sport")
    description: Optional[str] = None
    points_count: int = Field(4, ge=1, le=16, description="Number of laser touch points used in this drill")
    difficulty: Optional[str] = Field(None, description="Beginner, Intermediate, Advanced")
    focus: Optional[List[str]] = Field(None, description="What this drill focuses on: speed, agility, reaction, footwork")

class Session(BaseModel):
    athlete_id: str = Field(..., description="Reference to athlete _id as string")
    sport: str = Field(...)
    exercise_ids: List[str] = Field(..., description="List of exercise ids or names included in this session")
    status: str = Field("running", description="running | completed | cancelled")
    start_time: Optional[str] = Field(None, description="ISO start time - set by server")
    end_time: Optional[str] = Field(None, description="ISO end time - set by server")
    notes: Optional[str] = None

class Attempt(BaseModel):
    session_id: str = Field(...)
    exercise_id: str = Field(...)
    point_index: Optional[int] = Field(None, ge=0, le=32, description="Which touch point was hit")
    time_ms: int = Field(..., ge=0, description="Time in milliseconds for this touch or segment")
    ts: Optional[str] = Field(None, description="ISO timestamp - set by server")

class Plan(BaseModel):
    athlete_id: str = Field(...)
    sport: str = Field(...)
    video_url: Optional[HttpUrl] = None
    goals: Optional[List[str]] = Field(default=None, description="Skill goals extracted or provided")
    exercise_suggestions: List[str] = Field(default_factory=list)

# Note: The Flames database viewer can read these with GET /schema
