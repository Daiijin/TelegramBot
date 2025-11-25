import os
import logging
import sqlite3
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from llm_engine import configure_genai, get_secretary_response, extract_schedule_intent
from scheduler_manager import SchedulerManager
from database import (
    init_db, add_user, update_user_goal, get_user_goals, add_task, get_tasks_for_date, 
    add_recurring_schedule, get_all_schedules, delete_task, delete_recurring_schedule,
    delete_all_tasks, delete_all_recurring_schedules, delete_tasks_by_date, DB_PATH,
    get_all_users, check_duplicate_recurring, check_duplicate_task
)

# ... (imports remain same)

# ... (rest of file)

async def send_daily_briefing(context: ContextTypes.DEFAULT_TYPE):
    """Sends a daily schedule summary to all users."""
    users = get_all_users()
    tz = ZoneInfo("Asia/Ho_Chi_Minh")
    now = datetime.now(tz)
    date_str = now.strftime('%Y-%m-%d')
    display_date = now.strftime('%d/%m')
    
    day_code_map = {0: "mon", 1: "tue", 2: "wed", 3: "thu", 4: "fri", 5: "sat", 6: "sun"}
    current_day_code = day_code_map[now.weekday()]

    for user in users:
        user_id = user[0]
        first_name = user[2] if user[2] else "Anh"
        
        # Get tasks
        tasks = get_tasks_for_date(user_id, date_str)
        
        # Get recurring
        recurring = get_all_schedules(user_id)
        todays_recurring = []
        for r in recurring:
            if current_day_code in r['days_of_week']:
                todays_recurring.append(r)
        
        if tasks or todays_recurring:
            msg = f"🌞 Chào buổi sáng {first_name}! Lịch trình hôm nay ({display_date}) của anh:\n"
            for t in tasks:
                t_time = datetime.fromisoformat(t['schedule_time']).strftime('%H:%M')
                fmt_desc = format_description(t['description'])
                msg += f"- {t_time}: {fmt_desc}\n"
            for r in todays_recurring:
                # Format time
                r_time = r['time']
                if ":" in r_time:
                    h, m = map(int, r_time.split(':'))
                    r_time = f"{h:02d}:{m:02d}"
                fmt_desc = format_description(r['description'])
                msg += f"- {r_time}: {fmt_desc} (Định kỳ)\n"
            
            msg += "\nChúc anh một ngày làm việc hiệu quả! 💪"
            try:
                await context.bot.send_message(chat_id=user_id, text=msg)
            except Exception as e:
                logging.error(f"Failed to send briefing to {user_id}: {e}")

async def post_init(application):
    scheduler.start()
    # Schedule Daily Briefing at 06:30
    scheduler.add_daily_job(lambda: application.create_task(send_daily_briefing(ContextTypes.DEFAULT_TYPE(application=application))), 6, 30)
    # Note: APScheduler async callback needs to be handled carefully. 
    # Better: Use application.job_queue if available, but we are using custom scheduler.
    # Let's use a wrapper that puts it on the event loop.
    # Actually, AsyncIOScheduler can run async functions directly.
    # But we need 'context'. 
    # Simpler: Just pass the callback that takes no args, and inside it use 'application.bot'.
    
    # Redefine for scheduler compatibility
    async def briefing_wrapper():
        await send_daily_briefing_internal(application)
        
    scheduler.add_daily_job(briefing_wrapper, 6, 30)

async def send_daily_briefing_internal(app):
    users = get_all_users()
    tz = ZoneInfo("Asia/Ho_Chi_Minh")
    now = datetime.now(tz)
    date_str = now.strftime('%Y-%m-%d')
    display_date = now.strftime('%d/%m')
    day_code_map = {0: "mon", 1: "tue", 2: "wed", 3: "thu", 4: "fri", 5: "sat", 6: "sun"}
    current_day_code = day_code_map[now.weekday()]

    for user in users:
        user_id = user[0]
        first_name = user[2] if user[2] else "Anh"
        tasks = get_tasks_for_date(user_id, date_str)
        recurring = get_all_schedules(user_id)
        todays_recurring = [r for r in recurring if current_day_code in r['days_of_week']]
        
        if tasks or todays_recurring:
            msg = f"🌞 Chào buổi sáng {first_name}! Lịch trình hôm nay ({display_date}) của anh:\n"
            for t in tasks:
                t_time = datetime.fromisoformat(t['schedule_time']).strftime('%H:%M')
                fmt_desc = format_description(t['description'])
                msg += f"- {t_time}: {fmt_desc}\n"
            for r in todays_recurring:
                r_time = r['time']
                if ":" in r_time:
                    h, m = map(int, r_time.split(':'))
                    r_time = f"{h:02d}:{m:02d}"
                fmt_desc = format_description(r['description'])
                msg += f"- {r_time}: {fmt_desc} (Định kỳ)\n"
            msg += "\nChúc anh một ngày làm việc hiệu quả! 💪"
            try:
                await app.bot.send_message(chat_id=user_id, text=msg)
            except Exception as e:
                logging.error(f"Failed to send briefing to {user_id}: {e}")

# Load environment variables
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Initialize modules
init_db()
configure_genai(GEMINI_API_KEY)
scheduler = SchedulerManager()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user.id, user.username)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Dạ em chào anh {user.first_name} ạ! Em là Trang, thư ký riêng của anh. Em có thể giúp anh quản lý lịch trình, kế hoạch học tập và tài chính. Anh cần em giúp gì không ạ?"
    )

def format_description(text):
    """Capitalizes the first letter of the description."""
    if not text: return ""
    # Remove "lịch" prefix if it exists to be concise
    cleaned = text.strip()
    if cleaned.lower().startswith("lịch "):
        cleaned = cleaned[5:].strip()
    return cleaned[0].upper() + cleaned[1:] if cleaned else ""

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    chat_id = update.effective_chat.id
    
    # 1. Get Intent from LLM
    try:
        history = context.user_data.get('history', [])
        intent_data = extract_schedule_intent(user_input, history)
    except Exception as e:
        logging.error(f"LLM Error: {e}")
        await context.bot.send_message(chat_id=chat_id, text="Dạ em đang gặp chút trục trặc, anh thử lại sau nhé.")
        return

    intents = intent_data.get("intents", [])
    
    # If no specific intent found (or just 'chat'), use the Chat Persona
    if not intents or (len(intents) == 1 and intents[0].get("intent") == "chat"):
        # Get context (recurring schedules)
        schedules = get_all_schedules(update.effective_user.id)
        schedule_context = "\n".join([f"- {s['description']} ({s['days_of_week']} {s['time']})" for s in schedules])
        
        # Get history (last 10 messages)
        if 'history' not in context.user_data:
            context.user_data['history'] = []
        history = context.user_data['history'][-10:]
        
        # Get user goals
        user_goals = get_user_goals(chat_id)
        context_input = user_input
        if user_goals:
            context_input = f"[User Goal: {user_goals}] {user_input}"
            
        response = get_secretary_response(history, context_input, schedule_context)
        
        # Update history
        context.user_data['history'].append({'role': 'user', 'content': user_input})
        context.user_data['history'].append({'role': 'assistant', 'content': response})
        
        await context.bot.send_message(chat_id=chat_id, text=response)
        return

    # Process each intent
    for intent_obj in intents:
        intent_type = intent_obj.get("intent")
        conversational_resp = intent_obj.get("conversational_response")
        
        # Helper to send response (Conversational + Technical)
        async def send_response(technical_msg=None):
            final_msg = ""
            if conversational_resp:
                final_msg += conversational_resp + "\n\n"
            if technical_msg:
                final_msg += technical_msg
            
            if final_msg.strip():
                await context.bot.send_message(chat_id=chat_id, text=final_msg.strip())
            
            # Update history with the full response
            if 'history' not in context.user_data:
                context.user_data['history'] = []
            context.user_data['history'].append({'role': 'user', 'content': user_input})
            context.user_data['history'].append({'role': 'assistant', 'content': final_msg.strip()})

        if intent_type == "schedule_reminder":
            description = intent_obj.get("description")
            fmt_desc = format_description(description)
            reminder_msg = intent_obj.get("reminder_message", f"Thưa anh, đã đến giờ {fmt_desc} rồi ạ.")
            
            if "thưa anh" in reminder_msg.lower() and description in reminder_msg:
                reminder_msg = reminder_msg.replace(description, fmt_desc)

            schedule_type = intent_obj.get("type")
            
            if schedule_type == "recurring":
                days = intent_obj.get("days_of_week")
                hour = intent_obj.get("hour")
                minute = intent_obj.get("minute")
                end_date = intent_obj.get("end_date")
                remind_before = intent_obj.get("remind_before_minutes", 0)
                
                if not days:
                    await context.bot.send_message(chat_id=chat_id, text="❌ Dạ em chưa rõ anh muốn nhắc vào thứ mấy ạ?")
                    return

                # Convert days to string if it's a list
                if isinstance(days, list):
                    days = ",".join(days)

                day_map = {"mon": "Thứ 2", "tue": "Thứ 3", "wed": "Thứ 4", "thu": "Thứ 5", "fri": "Thứ 6", "sat": "Thứ 7", "sun": "Chủ Nhật"}
                display_days = ", ".join([day_map.get(d, d) for d in days.split(',')])

                # Check for duplicates (using ORIGINAL time)
                if check_duplicate_recurring(update.effective_user.id, description, days, f"{hour:02d}:{minute:02d}"):
                    await send_response(f"⚠️ Dạ lịch '{fmt_desc}' vào {hour:02d}:{minute:02d} các ngày {display_days} đã có rồi ạ.")
                    return

                # Add to DB (ORIGINAL time)
                add_recurring_schedule(update.effective_user.id, description, days, f"{hour:02d}:{minute:02d}", end_date)
                
                # Calculate Reminder Time
                sched_hour = hour
                sched_minute = minute
                sched_days = days
                
                if remind_before > 0:
                    # Logic to shift time and days
                    # Create a dummy date to subtract time
                    dummy_now = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
                    reminder_time = dummy_now - timedelta(minutes=remind_before)
                    sched_hour = reminder_time.hour
                    sched_minute = reminder_time.minute
                    
                    # Check if day shifted (e.g. 00:05 - 10m -> 23:55 prev day)
                    if reminder_time.date() < dummy_now.date():
                        # Shift days back by 1
                        day_list = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
                        new_days = []
                        for d in days.split(','):
                            if d in day_list:
                                idx = day_list.index(d)
                                new_idx = (idx - 1) % 7
                                new_days.append(day_list[new_idx])
                        sched_days = ",".join(new_days)
                    
                    # Schedule Early Reminder
                    early_msg = f"⏰ Thưa anh, còn {remind_before} phút nữa là đến giờ {fmt_desc} rồi ạ."
                    scheduler.add_recurring_reminder(chat_id, early_msg, sched_hour, sched_minute, sched_days, end_date)

                # Schedule Main Reminder (On-time)
                scheduler.add_recurring_reminder(chat_id, reminder_msg, hour, minute, days, end_date)
                
                msg = f"✅ Dạ em đã lên lịch: {fmt_desc} vào {hour:02d}:{minute:02d} các ngày {display_days}"
                if remind_before > 0:
                    msg += f" (nhắc trước {remind_before} phút và đúng giờ)"
                msg += " rồi ạ."
                await send_response(msg)
                
            else:
                run_date_str = intent_obj.get("run_date")
                remind_before = intent_obj.get("remind_before_minutes", 0)
                
                if run_date_str:
                    run_date = datetime.fromisoformat(run_date_str)
                    
                    # CRITICAL CHECK: Reject 00:00 default unless explicitly requested
                    if run_date.hour == 0 and run_date.minute == 0:
                        # Check if user actually said "midnight" or similar
                        explicit_midnight = any(k in user_input.lower() for k in ["00:00", "0h", "12h đêm", "nửa đêm", "midnight", "khuya"])
                        if not explicit_midnight:
                            await send_response("Dạ anh muốn nhắc vào lúc mấy giờ ạ?")
                            return

                    # AMBIGUOUS TIME HEURISTIC:
                    # If time is AM (0-11), and user didn't say "sáng", and it's in the past,
                    # but PM version is in the future -> Assume PM.
                    if run_date.hour < 12:
                        is_explicit_am = any(k in user_input.lower() for k in ["sáng", "am", "a.m", "khuya", "rạng sáng"])
                        if not is_explicit_am:
                            now = datetime.now()
                            # Check if AM time is past
                            if run_date < now:
                                # Check if PM time would be future
                                run_date_pm = run_date + timedelta(hours=12)
                                if run_date_pm > now:
                                    run_date = run_date_pm
                                    run_date_str = run_date.isoformat()

                    # SMART DATE SHIFT: If time has passed, move to tomorrow
                    now = datetime.now()
                    is_shifted = False
                    if run_date < now:
                        run_date += timedelta(days=1)
                        run_date_str = run_date.isoformat() # Update str for DB
                        is_shifted = True

                    # Check for duplicates (ORIGINAL time - wait, should check NEW time)
                    if check_duplicate_task(update.effective_user.id, description, run_date_str):
                        await send_response(f"⚠️ Dạ lịch '{fmt_desc}' vào lúc {run_date.strftime('%H:%M %d/%m/%Y')} đã có rồi ạ.")
                        return

                    # Schedule Reminders
                    if remind_before > 0:
                        reminder_time = run_date - timedelta(minutes=remind_before)
                        early_msg = f"⏰ Thưa anh, còn {remind_before} phút nữa là đến giờ {fmt_desc} rồi ạ."
                        scheduler.add_reminder(chat_id, early_msg, reminder_time)
                    
                    # Always schedule the main on-time reminder
                    scheduler.add_reminder(chat_id, reminder_msg, run_date)
                    
                    add_task(update.effective_user.id, description, run_date_str)
                    
                    if is_shifted:
                        msg = f"⚠️ Dạ giờ đó hôm nay đã qua, nên em chuyển sang ngày mai.\n✅ Đã lên lịch: {fmt_desc} vào lúc {run_date.strftime('%H:%M %d/%m/%Y')}"
                    else:
                        msg = f"✅ Dạ em đã lên lịch: {fmt_desc} vào lúc {run_date.strftime('%H:%M %d/%m/%Y')}"
                    
                    if remind_before > 0:
                        msg += f" (nhắc trước {remind_before} phút và đúng giờ)"
                    msg += " rồi ạ."
                    await send_response(msg)

        elif intent_type == "log_event":
            description = intent_obj.get("description")
            start_time = intent_obj.get("start_time")
            add_task(update.effective_user.id, description, start_time)
            fmt_desc = format_description(description)
            await send_response(f"✅ Dạ em đã ghi lại: {fmt_desc}.")

        elif intent_type == "clarify_schedule":
            # Bot needs more information about the schedule
            clarify_msg = intent_obj.get("message", "Dạ em chưa rõ anh muốn lên lịch như thế nào ạ?")
            await send_response(clarify_msg)

        elif intent_type == "check_schedule":
            time_range = intent_obj.get("time_range")
            keyword = intent_obj.get("keyword")
            user_id = update.effective_user.id
            
            def format_time_display(time_str):
                try:
                    h, m = map(int, time_str.split(':'))
                    return f"{h:02d}:{m:02d}"
                except:
                    return time_str

            if keyword:
                recurring = get_all_schedules(user_id)
                found_schedules = []
                for r in recurring:
                    if keyword.lower() in r['description'].lower():
                        found_schedules.append(r)
                
                if not found_schedules:
                    await send_response(f"❌ Dạ em không tìm thấy lịch nào có tên '{keyword}' ạ.")
                else:
                    msg = f"📅 Dạ lịch '{keyword}' của anh đây ạ:\n"
                    day_map = {"mon": "Thứ 2", "tue": "Thứ 3", "wed": "Thứ 4", "thu": "Thứ 5", "fri": "Thứ 6", "sat": "Thứ 7", "sun": "Chủ Nhật"}
                    
                    for r in found_schedules:
                        r_time = format_time_display(r['time'])
                        fmt_desc = format_description(r['description'])
                        days_display = []
                        if r['days_of_week']:
                            days_display = [day_map.get(d, d) for d in r['days_of_week'].split(',')]
                        days_str = ", ".join(days_display)
                        end_date_str = f" (đến {r['end_date']})" if r.get('end_date') else ""
                        msg += f"- {fmt_desc}: {r_time} các ngày {days_str}{end_date_str}\n"
                    
                    await send_response(msg)

            elif time_range in ["week", "next_week"]:
                tz = ZoneInfo("Asia/Ho_Chi_Minh")
                today = datetime.now(tz)
                response_lines = ["📅 Dạ lịch trình tuần tới của anh đây ạ:\n"]
                
                has_events = False
                for i in range(7):
                    current_day = today + timedelta(days=i)
                    date_str = current_day.strftime('%Y-%m-%d')
                    display_date = current_day.strftime('%d/%m')
                    weekday_map = {0: "Thứ 2", 1: "Thứ 3", 2: "Thứ 4", 3: "Thứ 5", 4: "Thứ 6", 5: "Thứ 7", 6: "Chủ Nhật"}
                    weekday_name = weekday_map[current_day.weekday()]
                    
                    tasks = get_tasks_for_date(user_id, date_str)
                    recurring = get_all_schedules(user_id)
                    todays_recurring = []
                    day_code_map = {0: "mon", 1: "tue", 2: "wed", 3: "thu", 4: "fri", 5: "sat", 6: "sun"}
                    current_day_code = day_code_map[current_day.weekday()]
                    
                    for r in recurring:
                        if current_day_code in r['days_of_week']:
                            todays_recurring.append(r)
                    
                    if tasks or todays_recurring:
                        has_events = True
                        response_lines.append(f"📌 {weekday_name} ({display_date}):")
                        for t in tasks:
                            t_time = datetime.fromisoformat(t['schedule_time']).strftime('%H:%M')
                            fmt_desc = format_description(t['description'])
                            response_lines.append(f" - {t_time}: {fmt_desc}")
                        for r in todays_recurring:
                            r_time = format_time_display(r['time'])
                            fmt_desc = format_description(r['description'])
                            response_lines.append(f" - {r_time}: {fmt_desc} (Định kỳ)")
                        response_lines.append("")
                
                if not has_events:
                    await send_response("Dạ tuần tới anh chưa có lịch trình nào ạ.")
                else:
                    await send_response("\n".join(response_lines))

            elif time_range == "specific_date":
                # Handle specific date queries like "lịch ngày 24/12"
                specific_date_str = intent_obj.get("specific_date")
                if not specific_date_str:
                    await send_response("Dạ em chưa rõ anh muốn xem lịch ngày nào ạ?")
                    continue
                
                try:
                    target_date = datetime.fromisoformat(specific_date_str + "T00:00:00")
                except:
                    await send_response("Dạ em không hiểu định dạng ngày này ạ. Anh có thể nói rõ hơn không ạ?")
                    continue
                
                date_str = specific_date_str
                tasks = get_tasks_for_date(user_id, date_str)
                
                recurring = get_all_schedules(user_id)
                todays_recurring = []
                day_code_map = {0: "mon", 1: "tue", 2: "wed", 3: "thu", 4: "fri", 5: "sat", 6: "sun"}
                target_day_code = day_code_map[target_date.weekday()]
                
                for r in recurring:
                    if target_day_code in r['days_of_week']:
                        todays_recurring.append(r)
                
                if not tasks and not todays_recurring:
                    day_map = {0: "Thứ 2", 1: "Thứ 3", 2: "Thứ 4", 3: "Thứ 5", 4: "Thứ 6", 5: "Thứ 7", 6: "Chủ Nhật"}
                    day_name = day_map[target_date.weekday()]
                    await send_response(f"Dạ ngày {target_date.strftime('%d/%m/%Y')} ({day_name}) anh chưa có lịch nào ạ.")
                else:
                    day_map = {0: "Thứ 2", 1: "Thứ 3", 2: "Thứ 4", 3: "Thứ 5", 4: "Thứ 6", 5: "Thứ 7", 6: "Chủ Nhật"}
                    day_name = day_map[target_date.weekday()]
                    msg = f"📅 Dạ lịch trình ngày {target_date.strftime('%d/%m/%Y')} ({day_name}) của anh:\n"
                    for t in tasks:
                        t_time = datetime.fromisoformat(t['schedule_time']).strftime('%H:%M')
                        fmt_desc = format_description(t['description'])
                        msg += f"- {t_time}: {fmt_desc}\n"
                    for r in todays_recurring:
                        r_time = format_time_display(r['time'])
                        fmt_desc = format_description(r['description'])
                        msg += f"- {r_time}: {fmt_desc} (Định kỳ)\n"
                    await send_response(msg)

            else:
                tz = ZoneInfo("Asia/Ho_Chi_Minh")
                now = datetime.now(tz)
                target_date = now
                
                if time_range == "tomorrow":
                    target_date = now + timedelta(days=1)
                elif time_range in ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]:
                    days_map = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}
                    target_day_num = days_map[time_range]
                    current_day_num = now.weekday()
                    days_ahead = target_day_num - current_day_num
                    if days_ahead <= 0: 
                        days_ahead += 7
                    target_date = now + timedelta(days=days_ahead)
                
                date_str = target_date.strftime('%Y-%m-%d')
                tasks = get_tasks_for_date(user_id, date_str)
                
                recurring = get_all_schedules(user_id)
                todays_recurring = []
                day_code_map = {0: "mon", 1: "tue", 2: "wed", 3: "thu", 4: "fri", 5: "sat", 6: "sun"}
                target_day_code = day_code_map[target_date.weekday()]
                
                for r in recurring:
                    if target_day_code in r['days_of_week']:
                        todays_recurring.append(r)
                
                if not tasks and not todays_recurring:
                    await send_response(f"Dạ ngày {target_date.strftime('%d/%m')} anh chưa có lịch nào ạ.")
                else:
                    msg = f"📅 Dạ lịch trình ngày {target_date.strftime('%d/%m')} của anh:\n"
                    for t in tasks:
                        t_time = datetime.fromisoformat(t['schedule_time']).strftime('%H:%M')
                        fmt_desc = format_description(t['description'])
                        msg += f"- {t_time}: {fmt_desc}\n"
                    for r in todays_recurring:
                        r_time = format_time_display(r['time'])
                        fmt_desc = format_description(r['description'])
                        msg += f"- {r_time}: {fmt_desc} (Định kỳ)\n"
                    await send_response(msg)

        elif intent_type == "set_goal":
            goal = intent_obj.get("goal")
            if goal:
                update_user_goal(update.effective_user.id, goal)
                
                if 'history' not in context.user_data:
                    context.user_data['history'] = []
                history = context.user_data['history']
                
                advice_prompt = f"Người dùng vừa nói: '{user_input}'. Họ đang muốn đặt mục tiêu: '{goal}'. Hãy đóng vai thư ký Trang. **QUAN TRỌNG: HÃY TRẢ LỜI HOÀN TOÀN BẰNG TIẾNG VIỆT. TUYỆT ĐỐI KHÔNG DÙNG TỪ TIẾNG ANH.** Dựa vào toàn bộ câu nói của người dùng VÀ LỊCH SỬ TRÒ CHUYỆN (để biết chủ đề, ví dụ TOEIC), hãy TỰ NHẬN ĐỊNH xem thông tin đã đủ để lập kế hoạch chưa (Mục tiêu, Thời gian hoàn thành, Thời gian học mỗi ngày). \n- Nếu THIẾU thông tin: CHỈ ĐẶT CÂU HỎI để làm rõ.\n- Nếu ĐỦ thông tin: Hãy xác nhận '🎯 Dạ em đã lưu mục tiêu: {goal}' và NGAY LẬP TỨC hỏi về lịch học: 'Anh muốn sắp xếp lịch học vào những ngày nào và khung giờ nào ạ?' để em lên lịch nhắc nhở.\n\nHãy trả lời tự nhiên, ngắn gọn."
                response = get_secretary_response(history, advice_prompt, "")
                
                # Update history
                context.user_data['history'].append({'role': 'user', 'content': user_input})
                context.user_data['history'].append({'role': 'assistant', 'content': response})
                
                await context.bot.send_message(chat_id=chat_id, text=response)

        elif intent_type == "delete_schedule":
            delete_all = intent_obj.get("delete_all", False)
            description = intent_obj.get("description")
            time_range = intent_obj.get("time_range")
            
            if delete_all:
                t_rows = delete_all_tasks(update.effective_user.id)
                r_rows = delete_all_recurring_schedules(update.effective_user.id)
                jobs_removed = 0
                for job in scheduler.get_jobs():
                    if job.args and job.args[0] == chat_id:
                        job.remove()
                        jobs_removed += 1
                await send_response(f"✅ Dạ em đã xóa toàn bộ lịch trình của anh rồi ạ ({t_rows} việc, {r_rows} lịch định kỳ).")
            
            elif description:
                deleted_one_off = delete_task(update.effective_user.id, description)
                deleted_recurring = delete_recurring_schedule(update.effective_user.id, description)
                jobs_removed = 0
                for job in scheduler.get_jobs():
                    if job.args and job.args[0] == chat_id:
                        msg = job.args[1]
                        if description.lower() in msg.lower():
                            job.remove()
                            jobs_removed += 1
                
                fmt_desc = format_description(description)
                if deleted_one_off or deleted_recurring or jobs_removed > 0:
                    await send_response(f"✅ Dạ em đã xóa lịch '{fmt_desc}' rồi ạ.")
                else:
                    await send_response(f"❌ Dạ em tìm không thấy lịch nào tên là '{fmt_desc}' để xóa ạ.")

            elif time_range:
                tz = ZoneInfo("Asia/Ho_Chi_Minh")
                now = datetime.now(tz)
                target_date = now
                if time_range == "tomorrow":
                    target_date = now + timedelta(days=1)
                elif time_range in ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]:
                    days_map = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}
                    target_day_num = days_map[time_range]
                    current_day_num = now.weekday()
                    days_ahead = target_day_num - current_day_num
                    if days_ahead <= 0: 
                        days_ahead += 7
                    target_date = now + timedelta(days=days_ahead)
                
                target_date_str = target_date.strftime('%Y-%m-%d')
                deleted_rows = delete_tasks_by_date(update.effective_user.id, target_date_str)
                
                recurring = get_all_schedules(update.effective_user.id)
                day_code_map = {0: "mon", 1: "tue", 2: "wed", 3: "thu", 4: "fri", 5: "sat", 6: "sun"}
                target_day_code = day_code_map[target_date.weekday()]
                
                deleted_recurring_count = 0
                for r in recurring:
                    if target_day_code in r['days_of_week']:
                        delete_recurring_schedule(update.effective_user.id, r['description'])
                        for job in scheduler.get_jobs():
                            if job.args and job.args[0] == chat_id and r['description'] in job.args[1]:
                                job.remove()
                        deleted_recurring_count += 1
                
                msg = f"✅ Dạ em đã xóa các công việc trong ngày {target_date.strftime('%d/%m')} ({deleted_rows} việc)."
                if deleted_recurring_count > 0:
                    msg += f"\nĐồng thời em cũng đã xóa {deleted_recurring_count} lịch định kỳ trùng vào ngày này."
                await send_response(msg)
            else:
                await send_response("❌ Dạ anh muốn xóa lịch nào ạ? Anh nói rõ hơn giúp em nhé.")

        elif intent_type == "clarify_schedule":
            message = intent_obj.get("message", "Dạ anh có thể nói rõ hơn được không ạ?")
            await send_response(message)
async def post_init(application):
    scheduler.start()

if __name__ == '__main__':
    if not TELEGRAM_TOKEN:
        print("Error: TELEGRAM_TOKEN not found in .env")
        exit(1)

    application = ApplicationBuilder().token(TELEGRAM_TOKEN).post_init(post_init).build()
    
    # Connect scheduler callback
    async def actual_callback(chat_id, text):
        await application.bot.send_message(chat_id=chat_id, text=text)
    
    scheduler.set_callback(actual_callback)
    
    start_handler = CommandHandler('start', start)
    msg_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
    
    application.add_handler(start_handler)
    application.add_handler(msg_handler)
    
    print("Bot is running...")
    application.run_polling()
