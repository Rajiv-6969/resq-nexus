from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
from dotenv import load_dotenv
import os

load_dotenv()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

class ScriptRequest(BaseModel):
    topic: str
    content_type: str = "youtube"
    tone: str = "conversational"
    length_minutes: float | None = None

CONTENT_TYPE_GUIDANCE = {
    "youtube": "a YouTube video script with a strong hook and clear sections",
    "ad": "a short, punchy advertisement script with a clear call to action",
    "podcast": "a podcast segment script or detailed talking-point outline",
    "social": "a fast-paced short-form social video script (Reels/TikTok style), one core idea, punchy",
    "reel": "a 15-30 second Instagram Reel / TikTok script — fast hook in the first line, quick pacing, on-screen text suggestions in brackets",
    "short_film": "a short film scene, written in proper screenplay format with scene headings (INT./EXT.), character names, and dialogue",
}

@app.post("/api/generate")
def generate_script(request: ScriptRequest):
    guidance = CONTENT_TYPE_GUIDANCE.get(request.content_type, "a script")
    prompt = f"Write {guidance} about: {request.topic}\n"
    prompt += f"Tone: {request.tone}\n"

    if request.length_minutes:
        prompt += f"Target length: about {request.length_minutes} minute(s) when spoken aloud.\n"

    prompt += "Return only the finished script, no extra commentary."

    response = client.models.generate_content(
        model="gemini-flash-latest",
        contents=prompt,
    )
    return {"script": response.text}