import os
import json
import logging
import httpx
from typing import Dict, Any, List
from app.config import settings

logger = logging.getLogger(__name__)

SETTINGS_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "settings.json"))

DEFAULT_SETTINGS = {
    "llm_model": settings.DEFAULT_MODEL,
    "image_model": "juggernautXL_ragnarok.safetensors",
    "image_width": 896,
    "image_height": 1152,
    "image_steps": 20,
    "image_cfg": 7.0,
    "selected_lora": "",
    "selected_llm_lora": ""
}

class SettingsService:
    @classmethod
    def get_recommended_model_defaults(cls, image_model: str) -> Dict[str, Any]:
        """
        Returns tailored recommended parameters (steps, CFG, resolution) for each image model type.
        """
        m_lower = image_model.lower()
        if "flux-2" in m_lower or "klein" in m_lower:
            return {
                "image_steps": 4,
                "image_cfg": 1.0,
                "image_width": 896,
                "image_height": 1152
            }
        elif "flux" in m_lower:
            is_schnell = any(kw in m_lower for kw in ["schnell", "turbo", "hyper", "4step", "4-step"])
            return {
                "image_steps": 4 if is_schnell else 20,
                "image_cfg": 1.0,
                "image_width": 896,
                "image_height": 1152
            }
        elif "turbo" in m_lower or "lightning" in m_lower or "hyper" in m_lower:
            return {
                "image_steps": 6,
                "image_cfg": 2.0,
                "image_width": 896,
                "image_height": 1152
            }
        elif "z-image" in m_lower or "z_image" in m_lower:
            return {
                "image_steps": 8,
                "image_cfg": 3.0,
                "image_width": 896,
                "image_height": 1152
            }
        elif "dreamshaper" in m_lower or "v1-5" in m_lower or "v1.5" in m_lower or "sd1" in m_lower:
            return {
                "image_steps": 20,
                "image_cfg": 7.0,
                "image_width": 512,
                "image_height": 768
            }
        elif any(kw in m_lower for kw in ["pony", "sdxl", "xl", "juggernaut", "babes"]):
            return {
                "image_steps": 25,
                "image_cfg": 7.0,
                "image_width": 896,
                "image_height": 1152
            }
        else: # Standard SD Checkpoint
            return {
                "image_steps": 20,
                "image_cfg": 7.0,
                "image_width": 896,
                "image_height": 1152
            }

    @classmethod
    def get_settings(cls) -> Dict[str, Any]:
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f:
                    data = json.load(f)
                    return {**DEFAULT_SETTINGS, **data}
            except Exception as e:
                logger.error(f"Failed to read settings file: {e}")
        return DEFAULT_SETTINGS.copy()

    @classmethod
    def update_settings(cls, new_settings: Dict[str, Any]) -> Dict[str, Any]:
        current = cls.get_settings()
        
        # If image model changed, auto-tailor steps, CFG, and resolution for the selected model
        new_model = new_settings.get("image_model")
        if new_model and new_model != current.get("image_model"):
            defaults = cls.get_recommended_model_defaults(new_model)
            # Apply recommended defaults when model selection changes
            new_settings["image_steps"] = defaults["image_steps"]
            new_settings["image_cfg"] = defaults["image_cfg"]
            new_settings["image_width"] = defaults["image_width"]
            new_settings["image_height"] = defaults["image_height"]

        current.update(new_settings)
        try:
            with open(SETTINGS_FILE, "w") as f:
                json.dump(current, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
        return current

    @classmethod
    def detect_image_arch(cls, filename: str, filepath: str = "") -> str:
        f_lower = (filename + " " + filepath).lower()
        if "flux-2" in f_lower or "klein" in f_lower:
            return "FLUX2"
        elif "flux" in f_lower:
            return "FLUX"
        elif "pony" in f_lower:
            return "Pony / SDXL"
        elif "sd_xl" in f_lower or "sdxl" in f_lower or "juggernaut" in f_lower or "babes" in f_lower:
            return "SDXL"
        elif "dreamshaper" in f_lower or "1.5" in f_lower or "sd1" in f_lower or "v1-5" in f_lower:
            return "SD1.5"
        elif "z-image" in f_lower:
            return "Z-Image"
        else:
            return "SD Checkpoint"

    @classmethod
    def detect_lora_arch(cls, filename: str, filepath: str = "") -> str:
        f_lower = (filename + " " + filepath).lower()
        if "flux-2" in f_lower or "klein" in f_lower:
            return "FLUX2"
        elif "flux" in f_lower or "krea" in f_lower or "renaissance" in f_lower:
            return "FLUX"
        elif "pony" in f_lower:
            return "Pony"
        elif "sdxl" in f_lower or "pov" in f_lower or "cheating" in f_lower:
            return "SDXL"
        elif "1.5" in f_lower or "sd1" in f_lower:
            return "SD1.5"
        else:
            return "SDXL / SD1.5"

    @classmethod
    def discover_models(cls) -> Dict[str, List[Dict[str, Any]]]:
        """
        Scans /home/jason/models and ComfyUI model directories recursively several levels deep
        to discover all available LLMs, image generation models (with architecture tags), and LoRAs.
        """
        models_root = "/home/jason/models"
        
        # 1. Discover LLMs (Live Ollama API + recursive GGUF scan)
        llm_models = []
        try:
            resp = httpx.get("http://localhost:11434/api/tags", timeout=2.0)
            if resp.status_code == 200:
                for m in resp.json().get("models", []):
                    name = m.get("name")
                    if name and not any(l["id"] == name for l in llm_models):
                        llm_models.append({"id": name, "label": f"🤖 Ollama: {name}", "source": "ollama"})
        except Exception:
            pass

        non_llm_keywords = ["audio", "tts", "wavtokenizer", "dia_q5", "kokoro", "embed", "vocab", "speech", "whisper", "flux", "sdxl"]
        if os.path.exists(models_root):
            for root, _, files in os.walk(models_root):
                for file in files:
                    f_lower = file.lower()
                    if file.endswith(".gguf") and not any(kw in f_lower for kw in non_llm_keywords):
                        full_path = os.path.join(root, file)
                        if os.path.isfile(full_path):
                            rel_path = os.path.relpath(full_path, models_root)
                            if not any(l["id"] == rel_path or l["id"] == file for l in llm_models):
                                llm_models.append({"id": rel_path, "label": f"📁 Local GGUF: {file}", "source": "gguf", "path": full_path})

        # Ensure default model is included
        if not any(l["id"] == settings.DEFAULT_MODEL for l in llm_models):
            llm_models.insert(0, {"id": settings.DEFAULT_MODEL, "label": f"🤖 Ollama: {settings.DEFAULT_MODEL}", "source": "ollama"})

        # 2. Discover LLM Text Generation LoRAs (Adapters)
        llm_lora_dirs = [
            os.path.join(models_root, "LLMs", "loras"),
            os.path.join(models_root, "LLMs", "adapters"),
            os.path.join(models_root, "LoRAs", "llm"),
            os.path.join(models_root, "PEFT")
        ]
        llm_loras = [{"id": "", "label": "None (Base Model Only)"}]
        for l_dir in llm_lora_dirs:
            if os.path.exists(l_dir):
                for root, _, files in os.walk(l_dir):
                    for file in files:
                        if file.endswith((".bin", ".gguf", ".safetensors", ".pt")) and not file.startswith("put_"):
                            full_path = os.path.join(root, file)
                            if os.path.isfile(full_path) and not any(l["id"] == full_path for l in llm_loras):
                                rel_name = os.path.relpath(full_path, models_root)
                                llm_loras.append({
                                    "id": full_path,
                                    "label": f"🧠 [LLM LoRA] {file}",
                                    "filename": file,
                                    "path": full_path,
                                    "rel_path": rel_name
                                })

        # 3. Discover Image LoRAs first (to identify LoRA filenames)
        lora_scan_dirs = [
            os.path.join(models_root, "LoRAs"),
            os.path.join(models_root, "Lora"),
            "/home/jason/AI-ImageGen/ComfyUI/models/loras"
        ]
        lora_files = set()
        loras = [{"id": "", "label": "None (Base Model Only)"}]
        for l_dir in lora_scan_dirs:
            if os.path.exists(l_dir):
                for root, _, files in os.walk(l_dir):
                    for file in files:
                        if file.endswith((".safetensors", ".ckpt")) and not file.startswith("put_"):
                            full_path = os.path.join(root, file)
                            if os.path.isfile(full_path):
                                lora_files.add(file.lower())
                                if not any(l["id"] == file for l in loras):
                                    arch = cls.detect_lora_arch(file, full_path)
                                    loras.append({"id": file, "label": f"✨ [{arch}] {file}", "arch": arch})

        # 4. Discover Image Generation Models (Deep recursive scan)
        image_scan_dirs = [
            os.path.join(models_root, "Checkpoints"),
            os.path.join(models_root, "Diffusion"),
            os.path.join(models_root, "Other", "Stable-Diffusion"),
            os.path.join(models_root, "huggingface"),
            "/home/jason/AI-ImageGen/ComfyUI/models/checkpoints",
            "/home/jason/AI-ImageGen/ComfyUI/models/unet"
        ]

        non_image_keywords = ["music", "audio", "demucs", "tts", "embedding", "whisper", "voice", "omnivoice", "minimax", "acestep", "ocr", "kokoro", "applio", "realesrgan", "vae"]

        image_models = []
        for s_dir in image_scan_dirs:
            if os.path.exists(s_dir):
                for root, _, files in os.walk(s_dir):
                    r_lower = root.lower()
                    if any(ign in r_lower for ign in ["lora", "loras", "tts", "audio", "whisper", "qwen-tts", "voices", "upscale"]):
                        continue
                    for file in files:
                        f_lower = file.lower()
                        if f_lower in lora_files:
                            continue
                        if any(kw in f_lower for kw in non_image_keywords):
                            continue
                        if file.endswith((".safetensors", ".gguf", ".ckpt")) and not file.startswith("put_") and not file.startswith("README"):
                            full_path = os.path.join(root, file)
                            if not os.path.isfile(full_path):
                                continue
                            try:
                                size_mb = os.path.getsize(full_path) / (1024 * 1024)
                                if size_mb >= 500.0 and not any(img["id"] == file for img in image_models):
                                    arch = cls.detect_image_arch(file, full_path)
                                    recs = cls.get_recommended_model_defaults(file)
                                    image_models.append({
                                        "id": file,
                                        "label": f"🎨 [{arch}] {file}",
                                        "arch": arch,
                                        "size_mb": round(size_mb, 1),
                                        "recommended": recs
                                    })
                            except Exception:
                                pass

        return {
            "llm_models": llm_models,
            "llm_loras": llm_loras,
            "image_models": image_models,
            "loras": loras
        }
