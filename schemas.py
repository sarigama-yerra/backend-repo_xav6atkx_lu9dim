"""
Database Schemas for AI Persona Builder

Each Pydantic model represents a MongoDB collection. The collection name is the
lowercase of the class name (e.g., Persona -> "persona").

These models are used by the database viewer and for validation in the app.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Literal


class Professional(BaseModel):
    """Professionals who build and sell their AI personas"""
    name: str = Field(..., description="Full name of the professional")
    email: str = Field(..., description="Unique email address")
    bio: Optional[str] = Field(None, description="Short bio")
    avatar_url: Optional[str] = Field(None, description="Profile image URL")
    website: Optional[str] = Field(None, description="Personal or business site")
    specialties: List[str] = Field(default_factory=list, description="Domains of expertise")
    is_active: bool = Field(True, description="Whether this account is active")


class Source(BaseModel):
    """Knowledge sources uploaded or linked to a persona"""
    persona_id: str = Field(..., description="Related persona id")
    type: Literal["text", "link", "file", "video", "image", "slides", "website"]
    title: Optional[str] = Field(None, description="Display title for the source")
    url: Optional[str] = Field(None, description="URL for link/video/website sources")
    content: Optional[str] = Field(None, description="Raw text content for text sources")
    file_name: Optional[str] = Field(None, description="Original file name if uploaded")
    file_size: Optional[int] = Field(None, description="File size in bytes if uploaded")
    metadata: dict = Field(default_factory=dict, description="Arbitrary metadata like tags, notes")


class Persona(BaseModel):
    """An AI coach persona owned by a professional"""
    owner_email: str = Field(..., description="Owner email (references Professional.email)")
    title: str = Field(..., description="Public name of the persona")
    description: Optional[str] = Field(None, description="What this AI coach does")
    tone: Optional[str] = Field("helpful, concise, expert", description="Speaking style to emulate")
    specialties: List[str] = Field(default_factory=list, description="Topics this persona covers")
    status: Literal["draft", "training", "trained", "error"] = Field("draft", description="Training state")
    price_usd: Optional[float] = Field(None, ge=0, description="Optional price to access this persona")
    visibility: Literal["private", "unlisted", "public"] = Field("private")


class TrainingJob(BaseModel):
    """Represents a training request for a persona"""
    persona_id: str = Field(..., description="Target persona id")
    status: Literal["queued", "running", "completed", "failed"] = Field("queued")
    notes: Optional[str] = Field(None, description="Optional status notes")


class Conversation(BaseModel):
    """Simple conversation log with a persona"""
    persona_id: str = Field(...)
    user_message: str = Field(...)
    response: str = Field(...)

