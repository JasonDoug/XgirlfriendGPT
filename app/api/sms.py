from fastapi import APIRouter, Form, HTTPException, status
from app.models.media import OutboundSMSRequest, SMSWebhook
from app.services.sms_service import SMSService
from app.services.llm_service import LLMService
from app.services.storage_service import StorageService

router = APIRouter(prefix="/sms", tags=["SMS & Outbound Texting Pipeline"])

@router.post("/webhook")
def inbound_sms_webhook(
    MessageSid: str = Form(...),
    From: str = Form(...),
    To: str = Form(...),
    Body: str = Form(...)
):
    """
    Twilio SMS Listener Webhook.
    Processes inbound user SMS and replies contextually.
    """
    reply, _ = LLMService.generate_chat_response(
        system_prompt="You are a companion texting over SMS. Keep answers brief.",
        user_message=Body,
        memory_context=[]
    )
    
    result = SMSService.send_outbound_sms(to_phone=From, message=reply)
    return {"status": "success", "inbound_body": Body, "reply": reply, "twilio_result": result}

@router.post("/send", status_code=status.HTTP_200_OK)
def trigger_outbound_sms(request: OutboundSMSRequest):
    """
    Manually or programmatically triggers outbound companion SMS.
    """
    profile_data = StorageService.get_companion_by_id(request.companion_id)
    sys_prompt = profile_data.get("system_prompt") if profile_data else "You are a companion sending a text."
    
    prompt = f"Send a casual outbound text message to the user based on context: {request.context_hint}"
    reply, _ = LLMService.generate_chat_response(system_prompt=sys_prompt, user_message=prompt, memory_context=[])
    
    result = SMSService.send_outbound_sms(to_phone=request.to_phone_number, message=reply)
    return {"status": "sent", "message": reply, "details": result}
