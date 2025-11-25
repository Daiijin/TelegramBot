import os
import json
import logging
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def get_current_time_str():
    # Use Vietnam time explicitly
    tz = ZoneInfo("Asia/Ho_Chi_Minh")
    return datetime.now(tz).strftime('%Y-%m-%d %H:%M')

def get_secretary_response(history, user_input, schedule_context=""):
    """
    Sends the user input to Gemini API (via REST) and returns the response.
    """
    current_time_str = get_current_time_str()
    
    system_prompt = f"""You are Trang, a professional and empathetic personal secretary.
Current time: {current_time_str}.

Your goal is to help the user manage their schedule and tasks.
You MUST reply in pure, natural Vietnamese.

RULES:
1.  **Pure Vietnamese**: Never use English words like "schedule", "remind", "task". Use "lịch", "nhắc nhở", "công việc".
2.  **Empathetic**: Be polite, caring, and helpful. (e.g., "Dạ vâng", "Em hiểu rồi ạ", "Anh nhớ giữ gìn sức khỏe nhé").
3.  **Proactive**: If information is missing, ask for it politely.
4.  **Strict Scope**: You ONLY handle scheduling, reminders, and goal setting.
    - If the user asks about weather, news, or general knowledge, politely decline: "Dạ em chỉ là thư ký hỗ trợ lịch trình thôi ạ, em chưa biết về vấn đề này."
    - Do NOT simulate weather or news reports.

CONVERSATION HISTORY:
{history}

USER INPUT:
{user_input}

RESPONSE:
"""

    payload = {
        "contents": [{
            "parts": [{"text": system_prompt}]
        }]
    }

    try:
        response = requests.post(
            GEMINI_API_URL,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        
        data = response.json()
        if "candidates" in data and data["candidates"]:
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        else:
            logger.error(f"Gemini API returned no candidates: {data}")
            return "Dạ em đang gặp chút trục trặc, anh thử lại sau nhé ạ."
            
    except Exception as e:
        logger.error(f"Error calling Gemini API: {e}")
        return "Dạ mạng đang hơi yếu, em chưa nghe rõ ạ."

def extract_schedule_intent(user_input, history=None):
    """
    Uses Gemini (via REST) to extract schedule intent from user input.
    Returns a JSON object.
    """
    current_time_str = get_current_time_str()
    
    prompt = f"""
Current Time: {current_time_str}
User Input: "{user_input}"

Analyze the user's input and extract the scheduling intent into a JSON object.

INTENT TYPES:
1. `schedule_reminder`: User wants to set a reminder or schedule.
2. `check_schedule`: User wants to check existing schedules.
3. `delete_schedule`: User wants to cancel/delete a schedule.
4. `set_goal`: User wants to set a long-term goal.
5. `chat`: General conversation, greeting, or questions NOT related to scheduling.
6. `clarify_schedule`: User input is vague about time (e.g., "sáng mai", "chiều nay") WITHOUT a specific hour/minute.

RULES FOR `schedule_reminder`:
- `run_date`: ISO 8601 format (YYYY-MM-DDTHH:MM:SS).
- **CRITICAL**: If the user says vague times like "sáng mai", "chiều nay", "tối nay" WITHOUT a specific number, set intent to `clarify_schedule`. DO NOT GUESS 08:00 or 00:00.
- `remind_before_minutes`: Integer. If user says "nhắc trước 30p", value is 30. Default 0.
- `type`: "one_off" or "recurring".
- `days_of_week`: Array of strings ["mon", "tue", "wed", "thu", "fri", "sat", "sun"] for recurring.
- **DATE LOGIC**: If user says "9h tối" (21:00) and current time is 19:00, assume TODAY. If current time is 22:00, assume TOMORROW.

JSON OUTPUT FORMAT:
{{
  "intent": "schedule_reminder" | "check_schedule" | "delete_schedule" | "set_goal" | "chat" | "clarify_schedule",
  "description": "string (content of the task)",
  "run_date": "string (ISO 8601) or null",
  "remind_before_minutes": int,
  "type": "one_off" | "recurring",
  "days_of_week": [],
  "conversational_response": "string (A natural, polite Vietnamese response confirming the action or asking for details)"
}}

EXAMPLES:
Input: "Nhắc tôi họp lúc 9h sáng mai"
Output: {{
  "intent": "schedule_reminder",
  "description": "Họp",
  "run_date": "2025-11-26T09:00:00",
  "remind_before_minutes": 0,
  "type": "one_off",
  "conversational_response": "Dạ vâng, em sẽ nhắc anh họp lúc 9 giờ sáng mai ạ."
}}

Input: "Sáng mai nhắc tôi đi họp" (VAGUE TIME)
Output: {{
  "intent": "clarify_schedule",
  "conversational_response": "Dạ sáng mai mấy giờ anh muốn đi họp ạ?"
}}

Input: "Chào em"
Output: {{
  "intent": "chat",
  "conversational_response": "Dạ em chào anh ạ. Anh cần em giúp gì về lịch trình không ạ?"
}}

Input: "Thời tiết hôm nay thế nào?"
Output: {{
  "intent": "chat",
  "conversational_response": "Dạ em chỉ là thư ký lịch trình nên không rõ về thời tiết ạ. Anh hỏi em về lịch họp nhé!"
}}

Input: "Nhắc tôi lúc 8h tối nay trước 15p"
Output: {{
  "intent": "schedule_reminder",
  "run_date": "2025-11-25T20:00:00",
  "remind_before_minutes": 15,
  "conversational_response": "Dạ em sẽ nhắc anh lúc 8h tối nay và báo trước 15 phút ạ."
}}

RETURN ONLY THE JSON OBJECT.
"""
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "response_mime_type": "application/json"
        }
    }

    try:
        response = requests.post(
            GEMINI_API_URL,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        
        data = response.json()
        if "candidates" in data and data["candidates"]:
            text_response = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            # Clean up markdown code blocks if present
            if text_response.startswith("```json"):
                text_response = text_response[7:-3]
            elif text_response.startswith("```"):
                text_response = text_response[3:-3]
            return json.loads(text_response)
        else:
            logger.error(f"Gemini API returned no candidates: {data}")
            return {"intent": "chat", "conversational_response": "Dạ em đang gặp lỗi hệ thống, anh thử lại sau nhé."}
            
    except Exception as e:
        logger.error(f"Error calling Gemini API: {e}")
        return {"intent": "chat", "conversational_response": "Dạ mạng đang yếu, em chưa xử lý được ạ."}
