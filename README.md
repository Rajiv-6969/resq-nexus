# Script Desk

An AI-assisted content script writer. Describe a topic, pick a content type, tone, and target length — get a ready-to-use script written for you.

Built as my first full-stack web application, from scratch, to learn how a real frontend and backend connect and work together.

## Features

- Generates scripts for multiple formats: YouTube videos, ads, podcasts, Instagram Reels, TikToks, and short film scenes
- Adjustable tone (conversational, energetic, authoritative, witty, calm)
- Optional target length control
- Clean, minimalist interface
- Powered by Google's Gemini API

## Tech stack

**Frontend:** React (Vite)
**Backend:** Python, FastAPI
**AI:** Google Gemini API

## How it works

1. The user fills in a topic, content type, tone, and optional length in the React frontend.
2. The frontend sends this as a request to a FastAPI backend.
3. The backend builds a tailored prompt based on the selected content type and sends it to the Gemini API.
4. The generated script is returned to the frontend and displayed on the page.

## Running it locally

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate       # Windows
pip install -r requirements.txt
```

Create a `.env` file inside `backend/` with your own Gemini API key: "your key here"

Then run:
```bash
uvicorn main:app --reload
```

### Frontend

In a separate terminal:
```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:5173`.

## What I learned building this

This was my first project, built completely from scratch with no prior coding experience. Along the way I learned:

- How frontend and backend applications communicate over HTTP
- Building a REST API with FastAPI, including request validation with Pydantic
- Managing state and handling asynchronous requests in React
- Integrating a third-party AI API and prompt design
- Debugging real errors: CORS issues, environment variables, mismatched names, and provider API changes
- Version control with Git and GitHub

## Possible future improvements

- Streaming responses so the script appears as it's generated, instead of all at once
- Save/history of previously generated scripts
- Support for additional AI providers (OpenAI, Claude)
