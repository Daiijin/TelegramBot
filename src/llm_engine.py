import os
import google.generativeai as genai
import json
from datetime import datetime
from zoneinfo import ZoneInfo

# Configure Gemini
# Note: API Key should be set in environment variables or passed here
def configure_genai(api_key):
    genai.configure(api_key=api_key)

def get_current_time_str():
    # Use Vietnam time explicitly
    tz = ZoneInfo("Asia/Ho_Chi_Minh")
    return datetime.now(tz).strftime('%Y-%m-%d %H:%M')

def get_secretary_response(history, user_input, schedule_context=""):
    """
    Generates a response from the 'Secretary' persona.
    history: List of previous messages (optional, for context)
    user_input: The current message from the user
    schedule_context: String summary of recurring schedules
    """
    model = genai.GenerativeModel('gemini-2.0-flash')
    
    system_prompt = f"""
    You are Trang, a professional, gentle, and efficient personal secretary.
    You MUST address the user as "Anh" (Brother) in Vietnamese.
    You MUST start your sentences with polite particles like "Dạ anh", "Vâng anh" where appropriate to sound soft and respectful.
    
    **CRITICAL: ALWAYS respond in PURE VIETNAMESE. NEVER use English words. Translate everything to Vietnamese.**
    
    Your goals:
    1. Manage schedule, study plans, and daily tasks.
    2. Help the user stay organized and productive.
    3. Be conversational and proactive like a real secretary.
    
    Current time: {get_current_time_str()}
    
    KNOWN SCHEDULES:
    {schedule_context}
    
    **CONVERSATIONAL ABILITIES:**
    - **Strict Scheduling Focus**:
      - If user asks about weather, news, or general topics: **Politely DECLINE.**
      - Say: "Dạ em chỉ phụ trách quản lý lịch trình giúp anh thôi ạ. Anh cần em lên lịch gì không ạ?"
      - Do NOT try to answer or simulate weather/news.
    - If user seems stressed or tired: Offer encouragement (e.g., "Dạ anh nghỉ ngơi một chút nhé!")
    - If discussing study plans: Offer tips or advice based on their goals
    - Be empathetic and natural, like a dedicated assistant
    
    **IMPORTANT RULES:**
    - ALWAYS translate English to Vietnamese (e.g., "score" → "điểm số", "completed" → "hoàn thành")
    - If user asks about schedule: Use KNOWN SCHEDULES
    - If user wants to learn something: Ask about their goals politely
    - Keep responses concise, helpful, and extremely polite
    - NOTE: Your internal clock is server time. If user says time is different, TRUST THE USER.
    """
    
    # Format history
    history_text = ""
    if history:
        for msg in history:
            role = "User" if msg['role'] == 'user' else "Trang"
            history_text += f"{role}: {msg['content']}\n"
    
    # Simple concatenation for now - in production use ChatSession
    full_prompt = f"{system_prompt}\n\nConversation History:\n{history_text}\nUser: {user_input}\nTrang:"
    
    try:
        response = model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        return f"Dạ anh, em gặp chút lỗi khi xử lý ạ: {str(e)}"

def extract_schedule_intent(user_input, history=None):
    """
    Uses LLM to extract structured schedule data from natural language.
    Returns a JSON string or None if no schedule detected.
    """
    model = genai.GenerativeModel('gemini-2.0-flash')
    
    history_text = ""
    if history:
        # Take last 3 messages for context
        for msg in history[-3:]:
            role = "User" if msg['role'] == 'user' else "Trang"
            history_text += f"{role}: {msg['content']}\n"

    prompt = f"""
    Analyze the following user message and extract scheduling information.
    Current time: {get_current_time_str()}
    
    Conversation History (Use this to infer context, e.g., what subject is being studied, and DURATION of goals):
    {history_text}
    
    User message: "{user_input}"
    
    Return a JSON object with a key "intents" containing a LIST of intent objects.
    Example: {{ "intents": [ {{ "intent": "schedule_reminder", "conversational_response": "Dạ em chia sẻ với anh...", ... }} ] }}
    
    For EACH intent found, generate a "conversational_response":
    - This should be a NATURAL, EMPATHETIC, or POLITE Vietnamese response from "Trang" (a dedicated secretary).
    - **CRITICAL: ALWAYS USE PURE VIETNAMESE. NEVER mix English words.**
    - If the user expresses emotion (tired, happy, stressed), respond to that emotion FIRST.
    - If it's a pure command, just be polite (e.g., "Dạ vâng ạ").
    - DO NOT include the technical confirmation (e.g., "Em đã lên lịch...") in this response unless it flows naturally.
    
    **CRITICAL INTENT CLASSIFICATION RULES:**
    - Weather/News/General queries → "intent": "chat"
      - **Response Rule**: Politely DECLINE. "Dạ em chỉ phụ trách lịch trình thôi ạ."
    - General questions ("như nào", "thế nào", "bao nhiêu") WITHOUT schedule context → "intent": "chat"
      - **Response Rule**: Redirect to scheduling.
    - ONLY use "check_schedule" if user EXPLICITLY asks about THEIR schedule:
      ✅ "lịch học", "lịch của tôi", "lịch tuần tới", "lịch database", "lịch ngày 24/12"
      ❌ NOT: "thời tiết hôm nay", "sự kiện trong nước", "hôm nay có gì mới"
    
    Intent Types:
    
    1. If scheduling a reminder OR recurring schedule:
       Output: {{ "intent": "schedule_reminder", "type": "one_off"|"recurring", "description": "...", "run_date": "ISO8601", "remind_before_minutes": INTEGER (optional, e.g. 5) }}
       
       **CRITICAL PARSING RULES:**
       - "mỗi ngày", "hàng ngày" → "type": "recurring", "days_of_week": ["mon","tue","wed","thu","fri","sat","sun"]
       - "hàng tuần", "mỗi tuần" → "type": "recurring" (user must specify days)
       - "định kỳ", "các ngày" → "type": "recurring"
       
       **TIME PARSING (Vietnamese) - MUST BE EXPLICIT:**
       - "8h tối", "8 giờ tối", "20h" → hour: 20 ✅
       - "8h sáng", "8 giờ sáng" → hour: 8 ✅
       - "10h15" → hour: 10, minute: 15 ✅
       - "2h chiều" → hour: 14 ✅
       
       **DATE LOGIC (CRITICAL):**
       - Compare user time with Current Time ({get_current_time_str()}).
       - If user says "9h tối" and it is currently 19:00 (7 PM) → Assume TODAY (21:00 Today).
       - Only assume TOMORROW if the time has already passed today OR user explicitly says "mai".
       
       **REMINDER OFFSET:**
       - "nhắc trước 5 phút", "sớm 5p" → "remind_before_minutes": 5
       - "nhắc trước 1 tiếng" → "remind_before_minutes": 60
       
       **CRITICAL: NO NUMBER = NO TIME:**
       - If the user does NOT say a specific number (like "8", "9h", "10:30"), **DO NOT EXTRACT A TIME.**
       - "sáng", "sáng mai" → NO TIME EXTRACTED, trigger clarify_schedule ❌ (Do NOT guess 8:00)
       - "chiều", "chiều nay" → NO TIME EXTRACTED, trigger clarify_schedule ❌ (Do NOT guess 14:00)
       - "tối", "tối nay" → NO TIME EXTRACTED, trigger clarify_schedule ❌ (Do NOT guess 20:00)
       
       **CRITICAL: ONE-OFF SCHEDULES:**
       - If `run_date` is generated, it MUST have a specific time from the user.
       - If user says "ngày mai" but NO time → trigger clarify_schedule.
       - **NEVER** output `run_date` with "00:00:00" unless user explicitly said "midnight" or "0 giờ".
       
       **CRITICAL: If user mentions a schedule but BOTH time AND days are missing:**
       - "tôi có lịch database" → trigger clarify_schedule
       - "tôi phải học database cho đến 17/12" → trigger clarify_schedule
       
       **FEW-SHOT EXAMPLES (LEARN FROM THESE):**
       
       ❌ **WRONG:**
       User: "sáng mai tôi đi gặp khách"
       Output: {{ "intents": [{{ "intent": "schedule_reminder", "run_date": "2025-11-25T08:00:00" }}] }} (WRONG! Do not guess 8:00)
       
       ✅ **CORRECT:**
       User: "sáng mai tôi đi gặp khách"
       Output: {{ "intents": [{{ "intent": "clarify_schedule", "message": "Dạ anh gặp khách hàng vào lúc mấy giờ sáng mai ạ?" }}] }}
       
       ❌ **WRONG:**
       User: "chiều nay làm báo cáo"
       Output: {{ "intents": [{{ "intent": "schedule_reminder", "run_date": "2025-11-24T14:00:00" }}] }} (WRONG! Do not guess 14:00)
       
       ✅ **CORRECT:**
       User: "chiều nay làm báo cáo"
       Output: {{ "intents": [{{ "intent": "clarify_schedule", "message": "Dạ anh định làm báo cáo lúc mấy giờ chiều nay ạ?" }}] }}
       
       **Clarification Strategy**: Be natural and varied. Don't always use the same phrase.
       - Example 1: "Dạ anh định học vào những ngày nào trong tuần và khung giờ nào để em note lại ạ?"
       - Example 2: "Dạ vâng, anh muốn em lên lịch học vào lúc mấy giờ và những ngày nào ạ?"
       
       **CONTEXT AWARENESS:**
       - If user asks "17/12 là thứ mấy" or similar date questions → "intent": "chat" (Answer naturally using calendar knowledge)
       
       Output:
       
       Output:
       - "intent": "schedule_reminder"
       - "description": "what to remind about". IF MISSING, INFER from History (e.g., "TOEIC").
       - "reminder_message": "Polite Vietnamese message starting with 'Thưa Anh'."
       - "type": "one_off" or "recurring"
       - "days_of_week": LIST of day codes ["mon", "tue", etc.] (for recurring). If "mỗi ngày", return ALL 7 days.
       - "hour": int (0-23) - ONLY if EXPLICIT time given
       - "minute": int (0-59) - default 0 if not specified
       - "end_date": "YYYY-MM-DD" (optional). CRITICAL: Check History for GOAL DURATION (e.g., "6 months"). Calculate from today.
       - "run_date": "ISO 8601 datetime" (one_off)
       
       * IF time (hour/minute) is MISSING or VAGUE:
         - "intent": "clarify_schedule"
         - "message": "Dạ anh muốn học vào lúc mấy giờ ạ?"

    2. If SINGLE event (no recurring keywords):
       - "intent": "log_event"
       - "description": "Event description"
       - "start_time": "ISO 8601 datetime"
       
    3. If checking schedule:
       **EXAMPLES OF VALID CHECK_SCHEDULE:**
       - "lịch tuần tới" → time_range: "week"
       - "lịch học toeic" → time_range: null, keyword: "toeic"
       - "lịch ngày 24/11" → time_range: "specific_date", specific_date: "2025-11-24"
       - "lịch ngày 24 tháng 12" → time_range: "specific_date", specific_date: "2025-12-24"
       
       Output:
       - "intent": "check_schedule"
       - "time_range": "today", "tomorrow", "week", "next_week", "specific_date", or day code ("mon", "tue", etc.)
       - "specific_date": "YYYY-MM-DD" (if user asks for specific date like "24/12" or "24 tháng 11")
       - "keyword": "subject to search for" (e.g., "database", "toeic")
       
    4. If setting goal: 
       - "intent": "set_goal"
       - "goal": "CAPTURE FULL GOAL in PURE VIETNAMESE (Score, Time, Daily Duration)."
       * CRITICAL: If the user has provided ALL 3 elements, do NOT ask for them again.

    5. If deleting a schedule:
       - "intent": "delete_schedule"
       - "delete_all": true/false
       - "description": "keywords"
       - "time_range": "today", "tomorrow", "week", etc.

    6. If user provides ambiguous time/schedule:
       - "intent": "clarify_schedule"
       - "message": "Dạ lịch này là lịch cố định hàng tuần hay chỉ là lịch một lần vào hôm nay ạ?"

    CRITICAL: If the user is just answering a question OR asking general questions (weather, news), return "intent": "chat".
       
    If no specific intent, return {{ "intents": [ {{ "intent": "chat" }} ] }}.
    
    Return ONLY the JSON string.
    
    """
    
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        # Clean up potential markdown code blocks
        if text.startswith("```json"):
            text = text[7:-3]
        elif text.startswith("```"):
            text = text[3:-3]
        return json.loads(text)
    except Exception as e:
        print(f"Error extracting intent: {e}")
        return {"intents": [{"intent": "chat"}]}
