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
    Supports multi-turn conversation history and unconstrained roleplay inference with async and sync interfaces.
    """

    @classmethod
    async def generate_chat_response_async(
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

        # Check if user message explicitly requests a selfie, photo, or picture
        user_msg_lower = user_message.lower() if user_message else ""
        photo_keywords = [
            "selfie", "photo", "picture", "pic", "take a pic", 
            "snap a pic", "send pic", "send photo", "send selfie", 
            "show me a photo", "take a photo", "take a picture", "show photo", "camera"
        ]
        is_photo_request = any(kw in user_msg_lower for kw in photo_keywords)

        history_list = list(history or [])
        current_user_message = user_message
        last_error_detail = ""

        # Retry loop for LLM inference (up to 2 attempts for explicit photo requests)
        max_attempts = 2 if is_photo_request else 1
        for attempt in range(max_attempts):
            raw_output = await cls._call_inference_engine_async(
                user_message=current_user_message, 
                system_prompt=augmented_system_prompt,
                history=history_list
            )
            
            cleaned_output = cls._strip_thinking_tags(raw_output)
            reply_text, image_command = cls._extract_image_tool_call(cleaned_output)

            # If an image command was generated, return it
            if image_command and image_command.prompt and image_command.prompt.strip():
                return reply_text, image_command

            # If user explicitly requested a photo/selfie but no valid tool call was generated, retry once
            if is_photo_request and attempt < max_attempts - 1:
                last_error_detail = f"Attempt {attempt + 1}/{max_attempts}: LLM did not include a valid JSON image tool call."
                logger.warning(last_error_detail)
                current_user_message = (
                    f"{user_message}\n\n"
                    f"[SYSTEM REMINDER: The user requested a photo/selfie. "
                    f"You MUST append a JSON tool call at the end of your message describing what you look like or where you are AT THIS EXACT MOMENT based on the current chat context: "
                    f"{{\"generate_image\": true, \"prompt\": \"<detailed description based on current chat context>\"}}]"
                )

        # Fallback handling if no JSON tool call was returned: return text reply gracefully
        cleaned_text = re.sub(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```|\{[\s\S]*?\}', '', cleaned_output).strip()
        cleaned_text = re.sub(r'```(?:json)?\s*```', '', cleaned_text).strip()
        final_reply = cleaned_text if cleaned_text else cleaned_output.strip()

        if is_photo_request:
            # Construct a graceful fallback image command using the reply text context
            fallback_cmd = ImageGenCommand(
                generate_image=True, 
                prompt=f"A photorealistic selfie matching the situation: {final_reply[:120]}"
            )
            return final_reply, fallback_cmd

        return final_reply, None

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

        user_msg_lower = user_message.lower() if user_message else ""
        photo_keywords = [
            "selfie", "photo", "picture", "pic", "take a pic", 
            "snap a pic", "send pic", "send photo", "send selfie", 
            "show me a photo", "take a photo", "take a picture", "show photo", "camera"
        ]
        is_photo_request = any(kw in user_msg_lower for kw in photo_keywords)

        history_list = list(history or [])
        current_user_message = user_message
        last_error_detail = ""

        max_attempts = 2 if is_photo_request else 1
        for attempt in range(max_attempts):
            raw_output = cls._call_inference_engine(
                user_message=current_user_message, 
                system_prompt=augmented_system_prompt,
                history=history_list
            )
            
            cleaned_output = cls._strip_thinking_tags(raw_output)
            reply_text, image_command = cls._extract_image_tool_call(cleaned_output)

            if image_command and image_command.prompt and image_command.prompt.strip():
                return reply_text, image_command

            if is_photo_request and attempt < max_attempts - 1:
                last_error_detail = f"Attempt {attempt + 1}/{max_attempts}: LLM did not include a valid JSON image tool call."
                logger.warning(last_error_detail)
                current_user_message = (
                    f"{user_message}\n\n"
                    f"[SYSTEM REMINDER: The user requested a photo/selfie. "
                    f"You MUST append a JSON tool call at the end of your message describing what you look like or where you are AT THIS EXACT MOMENT based on the current chat context: "
                    f"{{\"generate_image\": true, \"prompt\": \"<detailed description based on current chat context>\"}}]"
                )

        cleaned_text = re.sub(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```|\{[\s\S]*?\}', '', cleaned_output).strip()
        cleaned_text = re.sub(r'```(?:json)?\s*```', '', cleaned_text).strip()
        final_reply = cleaned_text if cleaned_text else cleaned_output.strip()

        if is_photo_request:
            fallback_cmd = ImageGenCommand(
                generate_image=True, 
                prompt=f"A photorealistic selfie matching the situation: {final_reply[:120]}"
            )
            return final_reply, fallback_cmd

        return final_reply, None

    @classmethod
    def _strip_thinking_tags(cls, text: str) -> str:
        """
        Strips internal reasoning blocks like <think>...</think> produced by thinking models.
        """
        if not text:
            return ""
        # 1. Remove complete <think>...</think> blocks
        cleaned = re.sub(r'<think>[\s\S]*?</think>', '', text, flags=re.IGNORECASE).strip()
        # 2. Remove any remaining unclosed <think>... blocks to end of text
        cleaned = re.sub(r'<think>[\s\S]*$', '', cleaned, flags=re.IGNORECASE).strip()
        # 3. Remove orphaned </think> closing tags
        cleaned = re.sub(r'^[\s\S]*?</think>', '', cleaned, flags=re.IGNORECASE).strip()
        return cleaned

    @classmethod
    def _build_headers(cls) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if settings.LLM_API_KEY:
            url_lower = settings.LLM_BASE_URL.lower()
            is_https = url_lower.startswith("https://")
            is_loopback = any(h in url_lower for h in ["localhost", "127.0.0.1", "::1", "0.0.0.0"])
            if is_https or is_loopback:
                headers["Authorization"] = f"Bearer {settings.LLM_API_KEY}"
            else:
                logger.warning("LLM_API_KEY set but target LLM_BASE_URL is unencrypted non-loopback HTTP; omitting Authorization header.")
        return headers

    @classmethod
    async def _ensure_ollama_adapter_model(cls, base_model: str, lora_path: str) -> str:
        if not lora_path or not os.path.exists(lora_path):
            return base_model
        safe_name = f"{base_model.replace('/', '-').replace(':', '-')}-adapter"
        try:
            import httpx
            modelfile_content = f"FROM {base_model}\nADAPTER {lora_path}\n"
            create_payload = {"name": safe_name, "modelfile": modelfile_content, "stream": False}
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post("http://127.0.0.1:11434/api/create", json=create_payload)
                if resp.status_code == 200:
                    logger.info(f"Ollama dynamic LoRA model '{safe_name}' created successfully with adapter '{lora_path}'")
                    return safe_name
        except Exception as e:
            logger.warning(f"Could not create dynamic Ollama LoRA model: {e}")
        return base_model

    @classmethod
    def _ensure_ollama_adapter_model_sync(cls, base_model: str, lora_path: str) -> str:
        if not lora_path or not os.path.exists(lora_path):
            return base_model
        safe_name = f"{base_model.replace('/', '-').replace(':', '-')}-adapter"
        try:
            import httpx
            modelfile_content = f"FROM {base_model}\nADAPTER {lora_path}\n"
            create_payload = {"name": safe_name, "modelfile": modelfile_content, "stream": False}
            resp = httpx.post("http://127.0.0.1:11434/api/create", json=create_payload, timeout=30.0)
            if resp.status_code == 200:
                logger.info(f"Ollama dynamic LoRA model '{safe_name}' created successfully with adapter '{lora_path}'")
                return safe_name
        except Exception as e:
            logger.warning(f"Could not create dynamic Ollama LoRA model: {e}")
        return base_model

    @classmethod
    async def _call_inference_engine_async(cls, user_message: str, system_prompt: str, history: List[Dict[str, str]]) -> str:
        """
        Calls live LLM server asynchronously using httpx.AsyncClient.
        """
        import httpx
        import asyncio

        headers = cls._build_headers()

        messages = [{"role": "system", "content": system_prompt}]
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
        selected_llm_lora = active_settings.get("selected_llm_lora", "")

        if selected_llm_lora:
            selected_model = await cls._ensure_ollama_adapter_model(selected_model, selected_llm_lora)

        sys_lower = system_prompt.lower()
        if "strictly concise" in sys_lower or "short" in sys_lower or "concise" in sys_lower:
            max_tokens = 300
        elif "medium" in sys_lower or "balanced" in sys_lower:
            max_tokens = 500
        elif "long" in sys_lower or "verbose" in sys_lower:
            max_tokens = 800
        else:
            max_tokens = 400

        payload = {
            "model": selected_model,
            "messages": messages,
            "temperature": 0.7,
            "top_p": 0.9,
            "max_tokens": max_tokens,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9,
                "repeat_penalty": 1.1,
                "num_ctx": 4096
            }
        }

        import time
        logger.info(f"Sending async prompt turn to LLM model '{selected_model}' at {settings.LLM_BASE_URL}...")
        start_t = time.time()
        last_exception = None

        candidate_base_urls = [settings.LLM_BASE_URL]
        for alt in [
            "http://172.17.0.1:11434/v1",
            "http://127.0.0.1:11434/v1",
            "http://host.docker.internal:11434/v1",
            "http://localhost:11434/v1"
        ]:
            if alt not in candidate_base_urls:
                candidate_base_urls.append(alt)

        async with httpx.AsyncClient(timeout=300.0) as client:
            for base_url in candidate_base_urls:
                for attempt in range(2):
                    try:
                        url = f"{base_url.rstrip('/')}/chat/completions"
                        resp = await client.post(url, json=payload, headers=headers)
                        if resp.status_code == 200:
                            data = resp.json()
                            content = data["choices"][0]["message"]["content"]
                            elapsed = time.time() - start_t
                            logger.info(f"LLM model '{selected_model}' responded asynchronously in {elapsed:.2f}s via {base_url}")
                            if content and content.strip():
                                return content.strip()
                        else:
                            last_exception = f"LLM API returned status {resp.status_code}: {resp.text}"
                            logger.error(last_exception)
                    except Exception as e:
                        last_exception = str(e)
                        logger.warning(f"LLM async endpoint connection error at {base_url} (attempt {attempt+1}): {e}")
                        if attempt == 0:
                            await asyncio.sleep(0.5)

        raise RuntimeError(f"LLM Endpoint Unreachable or Failed: {last_exception}")

    @classmethod
    def _call_inference_engine(cls, user_message: str, system_prompt: str, history: List[Dict[str, str]]) -> str:
        """
        Calls live LLM server synchronously.
        """
        import httpx
        
        headers = cls._build_headers()

        messages = [{"role": "system", "content": system_prompt}]
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
        selected_llm_lora = active_settings.get("selected_llm_lora", "")

        if selected_llm_lora:
            selected_model = cls._ensure_ollama_adapter_model_sync(selected_model, selected_llm_lora)

        sys_lower = system_prompt.lower()
        if "strictly concise" in sys_lower or "short" in sys_lower or "concise" in sys_lower:
            max_tokens = 300
        elif "medium" in sys_lower or "balanced" in sys_lower:
            max_tokens = 500
        elif "long" in sys_lower or "verbose" in sys_lower:
            max_tokens = 800
        else:
            max_tokens = 400

        payload = {
            "model": selected_model,
            "messages": messages,
            "temperature": 0.7,
            "top_p": 0.9,
            "max_tokens": max_tokens,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9,
                "repeat_penalty": 1.1,
                "num_ctx": 4096
            }
        }

        import time
        logger.info(f"Sending prompt turn to LLM model '{selected_model}' at {settings.LLM_BASE_URL}...")
        start_t = time.time()
        last_exception = None

        candidate_base_urls = [settings.LLM_BASE_URL]
        for alt in [
            "http://172.17.0.1:11434/v1",
            "http://127.0.0.1:11434/v1",
            "http://host.docker.internal:11434/v1",
            "http://localhost:11434/v1"
        ]:
            if alt not in candidate_base_urls:
                candidate_base_urls.append(alt)

        for base_url in candidate_base_urls:
            for attempt in range(2):
                try:
                    url = f"{base_url.rstrip('/')}/chat/completions"
                    resp = httpx.post(url, json=payload, headers=headers, timeout=300.0)
                    if resp.status_code == 200:
                        data = resp.json()
                        content = data["choices"][0]["message"]["content"]
                        elapsed = time.time() - start_t
                        logger.info(f"LLM model '{selected_model}' responded in {elapsed:.2f}s via {base_url}")
                        if content and content.strip():
                            return content.strip()
                    else:
                        last_exception = f"LLM API returned status {resp.status_code}: {resp.text}"
                        logger.error(last_exception)
                except Exception as e:
                    last_exception = str(e)
                    logger.warning(f"LLM endpoint connection error at {base_url} (attempt {attempt+1}): {e}")
                    if attempt == 0:
                        time.sleep(0.5)

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
