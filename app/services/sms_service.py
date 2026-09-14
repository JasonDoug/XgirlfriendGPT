import logging
from typing import Dict, Any, Optional, List
from apscheduler.schedulers.background import BackgroundScheduler
from app.config import settings
from app.services.storage_service import StorageService
from app.services.memory_service import MemoryService
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

class SMSService:
    """
    SMS & Outbound Texting Pipeline Service.
    Integrates Twilio Messaging API and an APScheduler background scheduler
    to trigger proactive contextual messages (e.g. 'Morning! Thinking about you').
    """

    _scheduler: Optional[BackgroundScheduler] = None

    @classmethod
    def start_proactive_scheduler(cls):
        """
        Initializes background scheduler for periodic companion engagement.
        """
        if cls._scheduler is None:
            cls._scheduler = BackgroundScheduler()
            cls._scheduler.add_job(
                cls._run_proactive_outbound_job, 
                'interval', 
                hours=12, 
                id='proactive_sms_job'
            )
            cls._scheduler.start()
            logger.info("Proactive SMS scheduler started successfully.")

    @classmethod
    def stop_scheduler(cls):
        if cls._scheduler and cls._scheduler.running:
            cls._scheduler.shutdown()
            cls._scheduler = None

    @classmethod
    def send_outbound_sms(cls, to_phone: str, message: str) -> Dict[str, Any]:
        """
        Sends SMS message using Twilio Messaging API.
        """
        if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN:
            try:
                import httpx
                url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.TWILIO_ACCOUNT_SID}/Messages.json"
                auth = (settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
                data = {
                    "From": settings.TWILIO_PHONE_NUMBER,
                    "To": to_phone,
                    "Body": message
                }
                resp = httpx.post(url, data=data, auth=auth, timeout=5.0)
                if resp.status_code in [200, 201]:
                    return {"status": "sent", "sid": resp.json().get("sid")}
            except Exception as e:
                logger.error(f"Twilio SMS send error: {e}")

        # Fallback simulation response when Twilio API credentials are not set
        return {
            "status": "simulated",
            "from": settings.TWILIO_PHONE_NUMBER or "+18005550199",
            "to": to_phone,
            "body": message
        }

    @classmethod
    def _run_proactive_outbound_job(cls):
        """
        Executed periodically by scheduler to trigger proactive text check-ins
        using stored companion personalities and recalled long-term user memories.
        """
        logger.info("Running scheduled proactive companion engagement pass...")
        companions = StorageService.list_companions_raw()
        if not companions:
            return

        mem_service = MemoryService()
        for comp in companions:
            comp_id = comp.get("companion_id")
            comp_name = comp.get("name", "Companion")
            sys_prompt = comp.get("system_prompt", "You are a caring friend.")

            # Retrieve user memories for companion
            memories = mem_service.retrieve_memories(
                companion_id=comp_id,
                user_id="default_user",
                query="hobbies interest day",
                limit=2
            )

            prompt = "Generate a short, warm, 1-sentence proactive check-in SMS text message for your user."
            reply, _ = LLMService.generate_chat_response(
                system_prompt=sys_prompt,
                user_message=prompt,
                memory_context=memories
            )

            logger.info(f"Generated proactive SMS for {comp_name}: '{reply}'")
