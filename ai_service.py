import os
import json
import re
from dotenv import load_dotenv

load_dotenv()

# ----------------------------------------------------------------
#  Environment detection
#  If GEMINI_API_KEY is set (Railway) use Gemini
#  If not (local machine) fall back to Ollama
# ----------------------------------------------------------------

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
USE_GEMINI     = bool(GEMINI_API_KEY)
LOCAL_MODEL    = "aya-expanse"

if USE_GEMINI:
    from google import genai
    client = genai.Client(api_key = GEMINI_API_KEY)
else:
    import ollama




# ----------------------------------------------------------------
#  Shared prompt builder
# ----------------------------------------------------------------


def _build_prompt(language: str, issue_description: str) -> str:
    return f"""You are an expert software engineering mentor and code reviewer.

A developer has submitted a programming problem for analysis. Analyze it and respond ONLY with a valid JSON object — no markdown, no explanation, no extra text.

Programming Language: {language}
Problem Description:
{issue_description}

Respond with exactly this JSON structure:
{{
  "category": "<one of: Syntax Error | Logic Error | Runtime Exception | Type Error | Scope/Closure Issue | Async/Concurrency Bug | Memory/Resource Leak | API Misuse | Algorithm Issue | Configuration Error | Other>",
  "difficulty": "<one of: Beginner | Intermediate | Advanced>",
  "recommendation": "<a specific, actionable learning topic or documentation reference that would directly help this developer fix and prevent this issue>"
}}"""


# ----------------------------------------------------------------
#  Shared JSON parser
# ----------------------------------------------------------------

def _parse_response(raw_text: str) -> dict:
    raw_text = raw_text.strip()

    # Strip markdown code fences if the model wraps JSON anyway
    raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
    raw_text = re.sub(r"\s*```$", "", raw_text)
    raw_text = raw_text.strip()

    result = json.loads(raw_text)

    # Validate expected keys are present
    for key in ("category", "difficulty", "recommendation"):
        if key not in result:
            raise ValueError(f"AI response missing expected key: '{key}'")

    return result


# ----------------------------------------------------------------
#  Main entry point contains auto-routes to Gemini or Ollama
# ----------------------------------------------------------------

def analyze_issue(language: str, issue_description: str) -> dict:
    """
    Sends a programming problem to Gemini (Railway) or Ollama (local) and
    returns a structured analysis dict.

    Returns:
        {
            "category":       str  --> e.g. "Logic Error", "Syntax Error"
            "difficulty":     str  --> "Beginner" | "Intermediate" | "Advanced"
            "recommendation": str  --> targeted learning topic or doc reference
        }

    Raises:
        Exception (caller is responsible for catching and logging)
    """

    prompt = _build_prompt(language, issue_description)

    if USE_GEMINI:
        # Cloud: Gemini (Railway deployment) 
        response = client.models.generate_content(
            model = "gemini-2.5-flash",
            contents = prompt,
        )
        raw_text = response.text


    else:
        # Local: Ollama 
        response = ollama.generate(
            model   = LOCAL_MODEL,
            prompt  = prompt,
            format  = "json",
            options = {"temperature": 0.2},
        )
        raw_text = response.get("response", "")

    return _parse_response(raw_text)