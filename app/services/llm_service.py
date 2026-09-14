import json
import re
import logging
from typing import List, Dict, Tuple, Optional
from app.config import settings
from app.models.chat import ImageGenCommand

logger = logging.getLogger(__name__)

class LLMService:
    """
    Text & Personality Engine LLM Service.
    Connects to local Ollama (http://localhost:11434/v1), vLLM, Together AI, or OpenAI.
    Supports multi-turn conversation history and unconstrained roleplay inference.
    """

    @classmethod
    def generate_chat_response(
        cls, 
        system_prompt: str, 
        user_message: str, 
        memory_context: List[str],
        history: Optional[List[Dict[str, str]]] = None
    ) -> Tuple[str, Optional[ImageGenCommand]]:
        
        # Inject long-term memory facts if available
        context_str = ""
        if memory_context:
            context_str = "\n### RECALLED LONG-TERM FACTS & MEMORIES:\n" + "\n".join([f"- {m}" for m in memory_context]) + "\n"

        augmented_system_prompt = f"{system_prompt}\n{context_str}".strip()

        # Check if user message explicitly requests a selfie, photo, or location image
        user_msg_lower = user_message.lower() if user_message else ""
        photo_keywords = [
            "selfie", "photo", "picture", "pic", "image", "show where", "show me where", "where you are", 
            "where are you", "your room", "your surroundings", "your location", "take a pic", 
            "snap a pic", "snap", "camera", "look like", "send pic", "send photo", "send selfie", "show me", "let me see"
        ]
        is_photo_request = any(kw in user_msg_lower for kw in photo_keywords)

        history_list = list(history or [])
        current_user_message = user_message
        last_error_detail = ""

        # Retry loop for LLM inference (up to 3 attempts total for photo requests)
        max_attempts = 3 if is_photo_request else 1
        for attempt in range(max_attempts):
            raw_output = cls._call_inference_engine(
                user_message=current_user_message, 
                system_prompt=augmented_system_prompt,
                history=history_list
            )
            
            cleaned_output = cls._strip_thinking_tags(raw_output)
            reply_text, image_command = cls._extract_image_tool_call(cleaned_output)

            # If an image command was generated, return it
            if image_command and image_command.prompt and image_command.prompt.strip():
                return reply_text, image_command

            # If user explicitly requested a photo/selfie but no valid tool call was generated, retry
            if is_photo_request:
                last_error_detail = f"Attempt {attempt + 1}/{max_attempts}: LLM did not include a valid JSON image tool call. Model output: '{cleaned_output}'"
                logger.warning(last_error_detail)
                if attempt < max_attempts - 1:
                    current_user_message = (
                        f"{user_message}\n\n"
                        f"[SYSTEM REMINDER: The user requested a photo/selfie/location picture. "
                        f"You MUST append a JSON tool call at the end of your message describing what you look like or where you are AT THIS EXACT MOMENT based on the current chat context: "
                        f"{{\"generate_image\": true, \"prompt\": \"<detailed description based on current chat context>\"}}]"
                    )
            else:
                cleaned_text = re.sub(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```|\{[\s\S]*?\}', '', cleaned_output).strip()
                cleaned_text = re.sub(r'```(?:json)?\s*```', '', cleaned_text).strip()
                return cleaned_text if cleaned_text else cleaned_output.strip(), None


        # If photo request retries failed completely, raise an explicit error for clean debugging
        raise RuntimeError(f"Image Tool Call Generation Failed: {last_error_detail}")

    @classmethod
    def _strip_thinking_tags(cls, text: str) -> str:
        """
        Strips internal reasoning blocks like <think>...</think> produced by thinking models.
        """
        cleaned = re.sub(r'<think>[\s\S]*?</think>', '', text, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r'^<think>[\s\S]*', '', cleaned, flags=re.IGNORECASE).strip()
        return cleaned if cleaned else text.strip()

    @classmethod
    def _call_inference_engine(cls, user_message: str, system_prompt: str, history: List[Dict[str, str]]) -> str:
        """
        Calls live LLM server with multi-turn chat history matching direct Ollama sampling defaults.
        """
        import httpx
        
        headers = {"Content-Type": "application/json"}
        if settings.LLM_API_KEY:
            headers["Authorization"] = f"Bearer {settings.LLM_API_KEY}"

        # Construct OpenAI-standard multi-turn message sequence
        messages = [{"role": "system", "content": system_prompt}]
        
        # Append recent conversation turns (sanitized to prevent context explosion)
        if history:
            for turn in history[-8:]:
                role = turn.get("role", "user")
                content = turn.get("content", "")
                if role in ["user", "assistant"] and content:
                    clean_content = content[:1000].strip()
                    messages.append({"role": role, "content": clean_content})
                    
        messages.append({"role": "user", "content": user_message})

        from app.services.settings_service import SettingsService
        active_settings = SettingsService.get_settings()
        selected_model = active_settings.get("llm_model") or settings.DEFAULT_MODEL

        # Match natural Ollama sampling parameters
        payload = {
            "model": selected_model,
            "messages": messages,
            "temperature": 0.85,
            "top_p": 0.9,
            "max_tokens": 1024
        }

        import time
        logger.info(f"Sending prompt turn to Ollama model '{selected_model}' at {settings.LLM_BASE_URL}...")
        start_t = time.time()
        last_exception = None
        for attempt in range(2):
            try:
                url = f"{settings.LLM_BASE_URL.rstrip('/')}/chat/completions"
                resp = httpx.post(url, json=payload, headers=headers, timeout=120.0)
                if resp.status_code == 200:
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"]
                    elapsed = time.time() - start_t
                    logger.info(f"Ollama model '{selected_model}' responded in {elapsed:.2f}s")
                    if content and content.strip():
                        return content.strip()
                else:
                    last_exception = f"LLM API returned status {resp.status_code}: {resp.text}"
                    logger.error(last_exception)
            except Exception as e:
                last_exception = str(e)
                logger.warning(f"LLM endpoint connection error (attempt {attempt+1}): {e}")
                if attempt == 0:
                    time.sleep(1.0)

        raise RuntimeError(f"LLM Endpoint Unreachable or Failed: {last_exception}")


    @classmethod
    def _extract_image_tool_call(cls, text: str) -> Tuple[str, Optional[ImageGenCommand]]:
        """
        Strictly parses JSON tool outputs like {"generate_image": true, "prompt": "..."}.
        Returns cleaned text reply and ImageGenCommand if present; otherwise returns (text, None).
        No artificial fallbacks.
        """
        json_matches = re.finditer(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```|\{[\s\S]*?\}', text)
        for match in json_matches:
            raw_json = match.group(1) if match.group(1) else match.group(0)
            try:
                data = json.loads(raw_json)
                if isinstance(data, dict) and (data.get("generate_image") or "prompt" in data or data.get("action") == "generate_image"):
                    prompt = data.get("prompt", "")
                    if prompt:
                        # Clean out the JSON block and codeblock backticks from response text
                        cleaned = text.replace(match.group(0), "").strip()
                        cleaned = re.sub(r'```(?:json)?\s*```', '', cleaned).strip()
                        return cleaned if cleaned else "Here is a picture for you!", ImageGenCommand(generate_image=True, prompt=prompt)
            except Exception:
                continue

        return text.strip(), None
