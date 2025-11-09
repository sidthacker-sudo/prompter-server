# score_server.py
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import re, uvicorn, os
from anthropic import Anthropic

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # local dev
    allow_methods=["*"],
    allow_headers=["*"],
)

# Environment API key is optional - we can receive it from request
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

class ScoreReq(BaseModel):
    text: str
    api_key: str = ""  # Optional API key from extension settings

class SuggestNextReq(BaseModel):
    last_prompt: str
    last_response: str
    api_key: str = ""

class InferMetadataReq(BaseModel):
    prompt: str
    api_key: str = ""

# --- GOAL DETECTOR -------------------------------------------------
def detect_goal(p: str) -> str:
    """Detect what the user is trying to accomplish."""
    p_low = p.lower()

    # Prioritize more specific patterns first
    if any(k in p_low for k in ["debug", "fix bug", "error", "not working"]):
        return "debug or fix code"
    if any(k in p_low for k in ["code", "python", "javascript", "function", "script"]):
        return "generate or write code"
    if any(k in p_low for k in ["summarize", "tl;dr", "summary", "condense"]):
        return "summarize text or content"
    if any(k in p_low for k in ["write", "compose", "draft"]):
        if any(k in p_low for k in ["email", "letter", "message"]):
            return "write an email or message"
        elif any(k in p_low for k in ["essay", "article", "blog", "post"]):
            return "write an article or essay"
        return "write or create content"
    if any(k in p_low for k in ["analyze", "interpret", "examine"]):
        return "analyze or interpret information"
    if any(k in p_low for k in ["explain", "what is", "how does", "why"]):
        return "learn or understand a concept"
    if any(k in p_low for k in ["compare", "versus", "vs", "difference between"]):
        return "compare ideas or options"
    if any(k in p_low for k in ["translate", "translation"]):
        return "translate text"
    if any(k in p_low for k in ["plan", "outline", "steps", "schedule", "roadmap"]):
        return "create a plan or outline"
    if any(k in p_low for k in ["brainstorm", "ideas", "suggest"]):
        return "brainstorm ideas"
    if any(k in p_low for k in ["review", "critique", "feedback"]):
        return "get feedback or review"

    return "general reasoning or assistance"

def score_prompt(p: str) -> int:
    """Score prompt quality from 0-100."""
    if not p.strip():
        return 10
    score = 50

    # Heuristics: add points for structure & constraints
    if any(k in p.lower() for k in ["role:", "you are", "as a "]):
        score += 10
    if any(k in p.lower() for k in ["output", "format", "json", "table"]):
        score += 10
    if len(p) > 80:
        score += 5
    if re.search(r"\b(audience|tone|length|deadline|examples?)\b", p, re.I):
        score += 10
    if "sources" in p.lower() or "cite" in p.lower():
        score += 5

    return max(0, min(100, score))

def rewrite_prompt_with_llm(p: str, goal: str, api_key: str = "") -> str:
    """Use Claude to intelligently rewrite the prompt."""
    # Use provided API key or fall back to environment variable
    key = api_key or ANTHROPIC_API_KEY

    if not key:
        # Fallback to template if no API key
        return rewrite_prompt_simple(p, goal)

    try:
        client = Anthropic(api_key=key)
        message = client.messages.create(
            model="claude-3-haiku-20240307",  # Much faster than Sonnet!
            max_tokens=500,  # Reduced from 1024 for speed
            messages=[{
                "role": "user",
                "content": f"""Rewrite this prompt to be more effective:

"{p}"

Goal: {goal}

Add role, output format, and constraints. Return the rewritten prompt directly with no preamble or explanation."""
            }]
        )
        result = message.content[0].text.strip()

        # Strip common preambles
        preambles = [
            "here is the rewritten prompt:",
            "here's the rewritten prompt:",
            "rewritten prompt:",
            "improved prompt:",
            "here is an improved version:",
            "here's an improved version:",
        ]

        result_lower = result.lower()
        for preamble in preambles:
            if result_lower.startswith(preamble):
                # Remove the preamble and any following whitespace/newlines
                result = result[len(preamble):].strip()
                break

        return result
    except Exception as e:
        print(f"LLM rewrite failed: {e}")
        return rewrite_prompt_simple(p, goal)

def rewrite_prompt_simple(p: str, goal: str) -> str:
    """Fallback template-based rewrite."""
    return (
        f"Role: You are a helpful assistant.\n"
        f"Goal: {goal}\n"
        f"Task: {p.strip()}\n"
        "Constraints: Be clear, concise, and step-by-step.\n"
        "Output format: Bulleted outline plus a one-sentence summary."
    )

@app.post("/score")
def score(req: ScoreReq):
    """Score a prompt and return LLM-powered improvement suggestions."""
    goal = detect_goal(req.text)
    s = score_prompt(req.text)
    rw = rewrite_prompt_with_llm(req.text, goal, req.api_key)
    return {"score": s, "rewrite": rw, "goal": goal}

@app.post("/suggest-next")
def suggest_next(req: SuggestNextReq):
    """Suggest the next logical prompts based on conversation context."""
    key = req.api_key or ANTHROPIC_API_KEY

    if not key:
        return {
            "suggestions": [
                "Continue exploring this topic in more depth.",
                "Can you provide a practical example?"
            ]
        }

    try:
        client = Anthropic(api_key=key)
        message = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=400,
            messages=[{
                "role": "user",
                "content": f"""Based on this conversation, suggest TWO different follow-up prompts:

User's last prompt: "{req.last_prompt}"

AI's response: "{req.last_response[:1500]}"

Suggest 2 distinct follow-up prompts that:
1. Build on the conversation naturally
2. Take different angles or directions
3. Are specific and actionable

Format as:
1. [first prompt]
2. [second prompt]

Return ONLY these two numbered prompts, no preamble."""
            }]
        )
        result = message.content[0].text.strip()
        print(f"LLM raw response: {result}")

        # Parse numbered list
        suggestions = []
        for line in result.split('\n'):
            line = line.strip()
            # Remove numbering (1., 2., 1), 2), etc.)
            if line and (line[0].isdigit() or line.startswith('-')):
                # Strip number and punctuation
                cleaned = line.lstrip('0123456789.-) ').strip()
                if cleaned:
                    suggestions.append(cleaned)

        print(f"Parsed suggestions: {suggestions}")

        # Ensure we have exactly 2 suggestions
        if len(suggestions) < 2:
            print("Not enough suggestions, using fallback")
            suggestions = [
                "Can you elaborate on the key points you mentioned?",
                "What are some practical applications of this?"
            ]
        elif len(suggestions) > 2:
            suggestions = suggestions[:2]

        print(f"Final suggestions: {suggestions}")
        return {"suggestions": suggestions}
    except Exception as e:
        print(f"Suggestion failed: {e}")
        return {
            "suggestions": [
                "Can you elaborate on the key points you mentioned?",
                "What are some practical applications of this?"
            ]
        }

@app.post("/infer-metadata")
def infer_metadata(req: InferMetadataReq):
    """Infer title and category for a prompt."""
    key = req.api_key or ANTHROPIC_API_KEY

    if not key:
        # Fallback to simple heuristics
        return {
            "title": req.prompt[:50] + "..." if len(req.prompt) > 50 else req.prompt,
            "category": "other"
        }

    try:
        client = Anthropic(api_key=key)
        message = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=150,
            messages=[{
                "role": "user",
                "content": f"""Analyze this prompt and provide a title and category.

Prompt: "{req.prompt}"

Categories: coding, writing, analysis, creative, other

Respond in this exact format:
TITLE: [short descriptive title, max 5 words]
CATEGORY: [one of: coding, writing, analysis, creative, other]"""
            }]
        )
        result = message.content[0].text.strip()
        print(f"Metadata inference result: {result}")

        # Parse the response
        title = "Untitled Prompt"
        category = "other"

        for line in result.split('\n'):
            line = line.strip()
            if line.startswith("TITLE:"):
                title = line.replace("TITLE:", "").strip()
            elif line.startswith("CATEGORY:"):
                cat = line.replace("CATEGORY:", "").strip().lower()
                if cat in ["coding", "writing", "analysis", "creative", "other"]:
                    category = cat

        return {"title": title, "category": category}
    except Exception as e:
        print(f"Metadata inference failed: {e}")
        # Fallback
        return {
            "title": req.prompt[:50] + "..." if len(req.prompt) > 50 else req.prompt,
            "category": "other"
        }

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001)
