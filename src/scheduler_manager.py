from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from datetime import datetime, timedelta
import logging

import os

from zoneinfo import ZoneInfo

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

class SchedulerManager:
    def __init__(self, db_url=None):
        if db_url is None:
            BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(BASE_DIR, "data", "bot_data.db")
            db_url = f'sqlite:///{db_path}'
            
        jobstores = {
            'default': SQLAlchemyJobStore(url=db_url)
        }
        # Explicitly set timezone
        tz = ZoneInfo("Asia/Ho_Chi_Minh")
        self.scheduler = AsyncIOScheduler(jobstores=jobstores, timezone=tz)

    def start(self):
        self.scheduler.start()

    def add_reminder(self, chat_id, text, run_date):
        """
        Schedules a one-off reminder.
        run_date: datetime object
        """
        # Calculate 15 minutes before if needed, but for now let's assume the logic 
        # for "15 mins before" is handled before calling this, or we handle it here.
        # The user said: "remind me 15 mins before". 
        # So if the event is at T, we schedule at T - 15m.
        
        # We will assume the caller passes the ACTUAL time they want the notification.
        try:
            self.scheduler.add_job(
                self.send_message_callback, 
                'date', 
                run_date=run_date, 
                args=[chat_id, text],
                misfire_grace_time=60
            )
            logger.info(f"Scheduled reminder for {chat_id} at {run_date}")
            return True
        except Exception as e:
            logger.error(f"Error scheduling reminder: {e}")
            return False

    def add_recurring_reminder(self, chat_id, text, hour, minute, days_of_week, end_date=None):
        """
        Schedules a recurring reminder.
        days_of_week: string like 'mon,tue,wed,thu,fri'
        """
        try:
            self.scheduler.add_job(
                self.send_message_callback, 
                'cron', 
                day_of_week=days_of_week,
                hour=hour, 
                minute=minute,
                end_date=end_date,
                args=[chat_id, text]
            )
            logger.info(f"Scheduled recurring reminder for {chat_id} at {hour}:{minute} on {days_of_week}")
            return True
        except Exception as e:
            logger.error(f"Error scheduling recurring reminder: {e}")
            return False

    async def send_message_callback(self, chat_id, text):
        # This function needs to be injected or bound to the bot instance
        # For now, we'll define it here but it needs access to the bot application.
        # A better pattern is to pass the bot app to the scheduler or use a global.
        # We will handle this in main.py by passing the function or using a wrapper.
        pass

    def set_callback(self, callback_func):
        self.send_message_callback = callback_func

    def get_jobs(self):
        return self.scheduler.get_jobs()

    def add_daily_job(self, callback, hour, minute):
        """Schedules a daily system job (e.g., briefing)."""
        self.scheduler.add_job(
            callback,
            'cron',
            hour=hour,
            minute=minute,
            misfire_grace_time=60
        )
        logger.info(f"Scheduled daily job at {hour}:{minute}")
