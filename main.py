from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import os
import json
import requests
import openai
from pypdf import PdfReader

# ---------- Setup ----------

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
pushover_user = os.getenv("PUSHOVER_USER")
pushover_token = os.getenv("PUSHOVER_TOKEN")
pushover_url = "https://api.pushover.net/1/messages.json"

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with your frontend domain in production
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Push notification ----------
import os

def push(message: str):
    user_key = os.getenv("PUSHOVER_USER")
    app_token = os.getenv("PUSHOVER_TOKEN")
    conn = http.client.HTTPSConnection("api.pushover.net", 443)
    post_data = urllib.parse.urlencode({
        "token": app_token,
        "user": user_key,
        "message": message,
    })
    headers = { "Content-type": "application/x-www-form-urlencoded" }
    conn.request("POST", "/1/messages.json", post_data, headers)
    response = conn.getresponse()
    print("Pushover status:", response.status, response.reason)
    print(response.read().decode())
    conn.close()



# ---------- Tool functions ----------
def record_user_details(email, name="Name not provided", notes="not provided"):
    push(f"Recording interest from {name} with email {email} and notes {notes}")
    return {"recorded": "ok"}

def record_unknown_question(question):
    push(f"Recording '{question}' asked that I couldn't answer")
    return {"recorded": "ok"}

record_user_details_json = {
    "name": "record_user_details",
    "description": "Use this tool to record that a user is interested in being in touch and provided an email address",
    "parameters": {
        "type": "object",
        "properties": {
            "email": {"type": "string", "description": "The email address of this user"},
            "name": {"type": "string", "description": "The user's name, if they provided it"},
            "notes": {"type": "string", "description": "Any additional information"}
        },
        "required": ["email"],
        "additionalProperties": False
    }
}

record_unknown_question_json = {
    "name": "record_unknown_question",
    "description": "Always use this tool to record any question that couldn't be answered as you didn't know the answer",
    "parameters": {
        "type": "object",
        "properties": {
            "question": {"type": "string", "description": "The question that couldn't be answered"}
        },
        "required": ["question"],
        "additionalProperties": False
    }
}

tools = [
    {"type": "function", "function": record_user_details_json},
    {"type": "function", "function": record_unknown_question_json}
]

def handle_tool_calls(tool_calls):
    results = []
    for tool_call in tool_calls:
        tool_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)
        if tool_name == "record_user_details":
            result = record_user_details(**arguments)
        elif tool_name == "record_unknown_question":
            result = record_unknown_question(**arguments)
        else:
            result = {"error": "Unknown tool"}
        results.append({"role": "tool", "content": result})
    return results

# ---------- Load Profile Info on Startup ----------

LINKEDIN_PDF_PATH = "linkedin.pdf"
SUMMARY_TXT_PATH = "summary.txt"
PROFILE_NAME = "Shrweta Naik"

# Load LinkedIn PDF text
linkedin = ""
reader = PdfReader(LINKEDIN_PDF_PATH)
for page in reader.pages:
    text = page.extract_text()
    if text:
        linkedin += text

# Load summary
with open(SUMMARY_TXT_PATH, "r", encoding="utf-8") as f:
    summary = f.read()

system_prompt = f"""
You are acting as {PROFILE_NAME}.User greets you greet them back telling your information.

You are the friendly, approachable assistant on {PROFILE_NAME}'s website. Your main job is to answer questions about {PROFILE_NAME}'s career, background, skills, and experience. 
- Please always represent {PROFILE_NAME} in a warm, engaging, and professional manner—as if you were chatting with a potential client, employer, or collaborator. 
- You have access to a detailed summary and LinkedIn profile for reference, so use these to provide informative, genuine answers.
- If you are not sure about an answer or something is out of your expertise, politely let the user know and use your `record_unknown_question` tool to log it—even if it’s something unrelated to the career.
- If the conversation gets interesting, gently encourage the user to connect or share their email so you can follow up. Use your `record_user_details` tool to capture those details.

---

## Summary:
{summary}

---

## LinkedIn Profile:
{linkedin}

---

With this context, please chat with the user in the voice of {PROFILE_NAME}, always being helpful and personable.
"""

# ---------- Chat API ----------

class ChatRequest(BaseModel):
    message: str
    history: list  # List of {"role": "user"|"assistant", "content": str}

@app.post("/chat")
async def chat_endpoint(data: ChatRequest):
    try:
        messages = [{"role": "system", "content": system_prompt}] + data.history + [{"role": "user", "content": data.message}]
        done = False
        reply_content = None

        while not done:
            response = openai.chat.completions.create(
                model="gpt-4o",  # Or "gpt-4o-mini", etc.
                messages=messages,
                tools=tools
            )
            finish_reason = response.choices[0].finish_reason

            if finish_reason == "tool_calls":
                message = response.choices[0].message
                tool_calls = message.tool_calls
                results = handle_tool_calls(tool_calls)
                messages.append(message)
                messages.extend(results)
            else:
                done = True
                reply_content = response.choices[0].message.content

        return {"reply": reply_content}

    except Exception as e:
        return {"error": str(e)}
