import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Literal, Any
from bson import ObjectId

app = FastAPI(title="AI Persona Builder API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Utilities
class ObjectIdEncoder:
    @staticmethod
    def encode(doc: Any):
        if isinstance(doc, list):
            return [ObjectIdEncoder.encode(d) for d in doc]
        if isinstance(doc, dict):
            new_doc = {}
            for k, v in doc.items():
                if isinstance(v, ObjectId):
                    new_doc[k] = str(v)
                elif isinstance(v, list) or isinstance(v, dict):
                    new_doc[k] = ObjectIdEncoder.encode(v)
                else:
                    new_doc[k] = v
            return new_doc
        return doc


# Request models
class ProfessionalCreate(BaseModel):
    name: str
    email: str
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    website: Optional[str] = None
    specialties: List[str] = []


class PersonaCreate(BaseModel):
    owner_email: str
    title: str
    description: Optional[str] = None
    tone: Optional[str] = "helpful, concise, expert"
    specialties: List[str] = []
    visibility: Literal["private", "unlisted", "public"] = "private"
    price_usd: Optional[float] = Field(None, ge=0)


class SourceCreate(BaseModel):
    persona_id: str
    type: Literal["text", "link", "file", "video", "image", "slides", "website"]
    title: Optional[str] = None
    url: Optional[str] = None
    content: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    metadata: dict = {}


class TrainRequest(BaseModel):
    persona_id: str
    notes: Optional[str] = None


class ChatRequest(BaseModel):
    persona_id: str
    message: str


@app.get("/")
def read_root():
    return {"message": "AI Persona Builder Backend Running"}


@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        from database import db

        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"

            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except ImportError:
        response["database"] = "❌ Database module not found (run enable-database first)"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    import os
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


@app.get("/schema")
def get_schema():
    """Expose schema metadata for viewer tools"""
    from schemas import Professional, Persona, Source, TrainingJob, Conversation
    def serialize(model):
        return {
            "name": model.__name__,
            "fields": list(model.model_fields.keys())
        }
    return {
        "models": [
            serialize(Professional),
            serialize(Persona),
            serialize(Source),
            serialize(TrainingJob),
            serialize(Conversation),
        ]
    }


@app.post("/api/professionals")
def create_professional(payload: ProfessionalCreate):
    from database import create_document
    from schemas import Professional
    prof = Professional(**payload.model_dump())
    inserted_id = create_document("professional", prof)
    return {"id": inserted_id, "status": "created"}


@app.post("/api/personas")
def create_persona(payload: PersonaCreate):
    from database import create_document
    from schemas import Persona
    persona = Persona(**payload.model_dump())
    inserted_id = create_document("persona", persona)
    return {"id": inserted_id, "status": "created"}


@app.get("/api/personas")
def list_personas(owner_email: Optional[str] = None, limit: int = 20):
    from database import get_documents
    filt = {"owner_email": owner_email} if owner_email else {}
    docs = get_documents("persona", filt, limit)
    return {"items": ObjectIdEncoder.encode(docs)}


@app.post("/api/sources")
def add_source(payload: SourceCreate):
    from database import create_document
    from schemas import Source
    # quick validation of persona_id format
    if not payload.persona_id:
        raise HTTPException(status_code=400, detail="persona_id required")
    source = Source(**payload.model_dump())
    inserted_id = create_document("source", source)
    return {"id": inserted_id, "status": "created"}


@app.post("/api/train")
def start_training(payload: TrainRequest):
    from database import create_document, db
    from schemas import TrainingJob
    job = TrainingJob(persona_id=payload.persona_id, status="queued", notes=payload.notes)
    job_id = create_document("trainingjob", job)
    # naive status update on persona
    try:
        db["persona"].update_one({"_id": ObjectId(payload.persona_id)}, {"$set": {"status": "training"}})
    except Exception:
        pass
    return {"job_id": job_id, "status": "queued"}


@app.post("/api/chat")
def chat(payload: ChatRequest):
    from database import db, create_document
    from schemas import Conversation
    # fetch persona
    persona = db["persona"].find_one({"_id": ObjectId(payload.persona_id)})
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")

    tone = persona.get("tone", "helpful, concise, expert")
    title = persona.get("title", "Your AI Coach")
    specialties = persona.get("specialties", [])

    style_hint = f"Tone: {tone}. "
    topic_hint = f"Expertise: {', '.join(specialties)}." if specialties else ""

    # Mock response generation: echo with persona style
    reply = (
        f"[{title}] {style_hint}{topic_hint} "
        f"Here's my take: {payload.message.strip()} -> "
        f"Consider breaking this down into steps, validate with examples, and iterate."
    )

    conv = Conversation(persona_id=payload.persona_id, user_message=payload.message, response=reply)
    _ = create_document("conversation", conv)

    return {"response": reply}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
