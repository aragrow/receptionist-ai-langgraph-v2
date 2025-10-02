# ==================== src/api/webhook_router.py ====================

"""
Webhook Router

Handles incoming webhooks from external services like Twilio, Slack, etc.
"""

import logging
import hmac
import hashlib
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Form, Depends, Header
from fastapi.responses import Response
from pydantic import BaseModel, Field

logger = logging.getLogger("ai_receptionist.webhook_router")

router = APIRouter()


# ============ Request/Response Models ============

class TwilioWebhookData(BaseModel):
    """Data from Twilio webhook"""
    CallSid: str
    From: str
    To: Optional[str] = None
    CallStatus: Optional[str] = None
    Direction: Optional[str] = None
    SpeechResult: Optional[str] = None


class SlackWebhookData(BaseModel):
    """Data from Slack webhook"""
    type: str
    challenge: Optional[str] = None  # For URL verification
    event: Optional[dict] = None


class GenericWebhookData(BaseModel):
    """Generic webhook data"""
    event_type: str
    data: dict
    timestamp: Optional[str] = None


# ============ Utility Functions ============

def verify_twilio_signature(
    signature: str,
    url: str,
    params: dict,
    auth_token: str
) -> bool:
    """
    Verify Twilio webhook signature for security.
    
    See: https://www.twilio.com/docs/usage/security#validating-requests
    """
    try:
        # Create the signature string
        data = url
        for key in sorted(params.keys()):
            data += key + params[key]
        
        # Calculate expected signature
        expected_signature = hmac.new(
            auth_token.encode('utf-8'),
            data.encode('utf-8'),
            hashlib.sha1
        ).digest()
        
        # Compare signatures
        import base64
        expected_signature_b64 = base64.b64encode(expected_signature).decode()
        
        return hmac.compare_digest(signature, expected_signature_b64)
    
    except Exception as e:
        logger.error(f"Error verifying Twilio signature: {e}")
        return False


def verify_slack_signature(
    signature: str,
    timestamp: str,
    body: bytes,
    signing_secret: str
) -> bool:
    """
    Verify Slack webhook signature for security.
    
    See: https://api.slack.com/authentication/verifying-requests-from-slack
    """
    try:
        # Check timestamp is recent (within 5 minutes)
        import time
        current_timestamp = int(time.time())
        if abs(current_timestamp - int(timestamp)) > 60 * 5:
            return False
        
        # Create signature base string
        sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
        
        # Calculate expected signature
        expected_signature = 'v0=' + hmac.new(
            signing_secret.encode('utf-8'),
            sig_basestring.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
    
    except Exception as e:
        logger.error(f"Error verifying Slack signature: {e}")
        return False


# ============ Dependency Injection ============

def get_services():
    """Get services from main.py"""
    from main import services
    return services


# ============ Twilio Webhooks ============

@router.post("/twilio/voice")
async def handle_twilio_voice_webhook(
    request: Request,
    CallSid: str = Form(...),
    From: str = Form(...),
    To: Optional[str] = Form(None),
    CallStatus: Optional[str] = Form(None),
    Direction: Optional[str] = Form(None),
    x_twilio_signature: Optional[str] = Header(None),
    services=Depends(get_services)
):
    """
    Handle incoming Twilio voice call webhook.
    
    This endpoint receives call events from Twilio and processes them
    through the AI Receptionist workflow.
    
    TwiML Response: https://www.twilio.com/docs/voice/twiml
    """
    logger.info(f"📞 Twilio webhook received: CallSid={CallSid}, From={From}, Status={CallStatus}")
    
    try:
        # Verify Twilio signature (optional but recommended for production)
        # TODO: Enable in production with real auth token
        # TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
        # if x_twilio_signature and TWILIO_AUTH_TOKEN:
        #     form_data = await request.form()
        #     if not verify_twilio_signature(
        #         x_twilio_signature,
        #         str(request.url),
        #         dict(form_data),
        #         TWILIO_AUTH_TOKEN
        #     ):
        #         raise HTTPException(status_code=403, detail="Invalid signature")
        
        # Handle different call statuses
        if CallStatus == "ringing":
            # Call is incoming, return TwiML to gather speech
            twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Gather input="speech" action="/webhooks/twilio/voice/gather" method="POST" timeout="5" speechTimeout="auto">
        <Say voice="alice">Hello! Welcome to our AI receptionist. How can I help you today?</Say>
    </Gather>
    <Say>I didn't catch that. Please call back and try again.</Say>
</Response>"""
            return Response(content=twiml, media_type="application/xml")
        
        elif CallStatus == "in-progress":
            # Call is active
            return Response(
                content='<?xml version="1.0" encoding="UTF-8"?><Response><Say>Processing your request...</Say></Response>',
                media_type="application/xml"
            )
        
        elif CallStatus == "completed":
            # Call ended, log it
            logger.info(f"✅ Call completed: {CallSid}")
            return Response(content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>', media_type="application/xml")
        
        else:
            # Default response
            return Response(
                content='<?xml version="1.0" encoding="UTF-8"?><Response><Say>Thank you for calling.</Say></Response>',
                media_type="application/xml"
            )
    
    except Exception as e:
        logger.error(f"❌ Twilio webhook error: {e}", exc_info=True)
        return Response(
            content='<?xml version="1.0" encoding="UTF-8"?><Response><Say>Sorry, an error occurred.</Say></Response>',
            media_type="application/xml"
        )


@router.post("/twilio/voice/gather")
async def handle_twilio_voice_gather(
    CallSid: str = Form(...),
    From: str = Form(...),
    SpeechResult: Optional[str] = Form(None),
    services=Depends(get_services)
):
    """
    Handle speech input from Twilio call.
    
    This endpoint receives the transcribed speech and processes it
    through the AI Receptionist workflow.
    """
    logger.info(f"🎤 Speech received: CallSid={CallSid}, Speech={SpeechResult}")
    
    try:
        if not SpeechResult:
            # No speech detected
            twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>I didn't hear anything. Please try again.</Say>
    <Gather input="speech" action="/webhooks/twilio/voice/gather" method="POST" timeout="5">
        <Say>How can I help you?</Say>
    </Gather>
</Response>"""
            return Response(content=twiml, media_type="application/xml")
        
        # Process through AI Receptionist
        result = await services.workflow_runner.process_call(
            call_data={
                "call_sid": CallSid,
                "caller_phone": From,
                "speech_text": SpeechResult,
                "session_id": CallSid  # Use CallSid as session ID
            }
        )
        
        # Generate TwiML response
        response_text = result.response_text or "I'm processing your request."
        
        if result.requires_human_escalation:
            # Escalate to human
            twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>{response_text} Please hold while I transfer you to a representative.</Say>
    <Dial>+1234567890</Dial>
</Response>"""
        else:
            # Continue conversation
            twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>{response_text}</Say>
    <Gather input="speech" action="/webhooks/twilio/voice/gather" method="POST" timeout="5">
        <Say>Is there anything else I can help you with?</Say>
    </Gather>
    <Say>Thank you for calling. Goodbye!</Say>
</Response>"""
        
        return Response(content=twiml, media_type="application/xml")
    
    except Exception as e:
        logger.error(f"❌ Error processing speech: {e}", exc_info=True)
        return Response(
            content='<?xml version="1.0" encoding="UTF-8"?><Response><Say>Sorry, I encountered an error. Please try again.</Say></Response>',
            media_type="application/xml"
        )


@router.post("/twilio/sms")
async def handle_twilio_sms_webhook(
    MessageSid: str = Form(...),
    From: str = Form(...),
    Body: str = Form(...),
    services=Depends(get_services)
):
    """
    Handle incoming SMS messages from Twilio.
    
    Processes text messages through the AI Receptionist.
    """
    logger.info(f"📱 SMS received: From={From}, Body={Body}")
    
    try:
        # Process through AI Receptionist
        result = await services.workflow_runner.process_call(
            call_data={
                "call_sid": MessageSid,
                "caller_phone": From,
                "speech_text": Body,
                "session_id": f"sms_{MessageSid}"
            }
        )
        
        # Generate TwiML SMS response
        response_text = result.response_text or "Thank you for your message."
        
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>{response_text}</Message>
</Response>"""
        
        return Response(content=twiml, media_type="application/xml")
    
    except Exception as e:
        logger.error(f"❌ Error processing SMS: {e}", exc_info=True)
        return Response(
            content='<?xml version="1.0" encoding="UTF-8"?><Response><Message>Sorry, an error occurred.</Message></Response>',
            media_type="application/xml"
        )


# ============ Slack Webhooks ============

@router.post("/slack/events")
async def handle_slack_events(
    request: Request,
    x_slack_signature: Optional[str] = Header(None),
    x_slack_request_timestamp: Optional[str] = Header(None),
    services=Depends(get_services)
):
    """
    Handle Slack Events API webhooks.
    
    Responds to events like mentions, direct messages, etc.
    """
    logger.info("💬 Slack event received")
    
    try:
        # Get request body
        body = await request.body()
        data = await request.json()
        
        # Verify Slack signature (optional but recommended for production)
        # TODO: Enable in production with real signing secret
        # SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")
        # if x_slack_signature and x_slack_request_timestamp and SLACK_SIGNING_SECRET:
        #     if not verify_slack_signature(
        #         x_slack_signature,
        #         x_slack_request_timestamp,
        #         body,
        #         SLACK_SIGNING_SECRET
        #     ):
        #         raise HTTPException(status_code=403, detail="Invalid signature")
        
        # Handle URL verification challenge
        if data.get("type") == "url_verification":
            return {"challenge": data["challenge"]}
        
        # Handle events
        event = data.get("event", {})
        event_type = event.get("type")
        
        if event_type == "app_mention":
            # Bot was mentioned
            text = event.get("text", "")
            user = event.get("user")
            channel = event.get("channel")
            
            logger.info(f"Bot mentioned by {user}: {text}")
            
            # Process through AI (simplified)
            # In production, integrate with your Slack client to post responses
            return {"ok": True}
        
        elif event_type == "message":
            # Direct message received
            text = event.get("text", "")
            user = event.get("user")
            
            logger.info(f"DM from {user}: {text}")
            
            # Process and respond
            return {"ok": True}
        
        else:
            logger.info(f"Unhandled event type: {event_type}")
            return {"ok": True}
    
    except Exception as e:
        logger.error(f"❌ Slack webhook error: {e}", exc_info=True)
        return {"ok": False, "error": str(e)}


@router.post("/slack/interactions")
async def handle_slack_interactions(
    request: Request,
    services=Depends(get_services)
):
    """
    Handle Slack interactive components (buttons, menus, etc.)
    """
    logger.info("🎛️ Slack interaction received")
    
    try:
        # Slack sends interactions as form data with a "payload" field
        form_data = await request.form()
        import json
        payload = json.loads(form_data.get("payload", "{}"))
        
        interaction_type = payload.get("type")
        user = payload.get("user", {})
        
        if interaction_type == "block_actions":
            # Button clicked
            actions = payload.get("actions", [])
            for action in actions:
                action_id = action.get("action_id")
                value = action.get("value")
                
                logger.info(f"Action: {action_id} = {value}")
                
                # Handle action
                # Return updated message or acknowledge
        
        return {"ok": True}
    
    except Exception as e:
        logger.error(f"❌ Slack interaction error: {e}", exc_info=True)
        return {"ok": False, "error": str(e)}


# ============ Generic Webhook ============

@router.post("/generic")
async def handle_generic_webhook(
    data: GenericWebhookData,
    x_webhook_secret: Optional[str] = Header(None),
    services=Depends(get_services)
):
    """
    Generic webhook handler for custom integrations.
    
    Accepts any event type and processes accordingly.
    """
    logger.info(f"🔗 Generic webhook: {data.event_type}")
    
    try:
        # Verify webhook secret (optional)
        # WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
        # if WEBHOOK_SECRET and x_webhook_secret != WEBHOOK_SECRET:
        #     raise HTTPException(status_code=403, detail="Invalid webhook secret")
        
        # Process based on event type
        if data.event_type == "call.incoming":
            # Handle incoming call
            caller_phone = data.data.get("caller_phone")
            logger.info(f"Incoming call from {caller_phone}")
            
        elif data.event_type == "feedback.received":
            # Handle feedback
            session_id = data.data.get("session_id")
            rating = data.data.get("rating")
            logger.info(f"Feedback received for {session_id}: {rating}")
            
        else:
            logger.warning(f"Unknown event type: {data.event_type}")
        
        return {
            "success": True,
            "event_type": data.event_type,
            "message": "Webhook processed successfully"
        }
    
    except Exception as e:
        logger.error(f"❌ Generic webhook error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Webhook processing failed: {str(e)}"
        )


# ============ Webhook Testing ============

@router.get("/test")
async def test_webhook():
    """
    Test endpoint to verify webhooks are working.
    """
    return {
        "status": "operational",
        "message": "Webhook endpoint is working",
        "available_webhooks": [
            "/webhooks/twilio/voice",
            "/webhooks/twilio/sms",
            "/webhooks/slack/events",
            "/webhooks/slack/interactions",
            "/webhooks/generic"
        ]
    }