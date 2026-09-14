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
    "selected_lora": ""
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
                "image_cfg": 3.5,
                "image_width": 896,
                "image_height": 1152
            }
        elif "flux" in m_lower:
            return {
                "image_steps": 4 if "schnell" in m_lower else 20,
                "image_cfg": 1.0 if "schnell" in m_lower else 3.5,
                "image_width": 896,
                "image_height": 1152
            }
        elif "turbo" in m_lower or "lightning" in m_lower:
            return {
                "image_steps": 6,
                "image_cfg": 2.0,
                "image_width": 896,
                "image_height": 1152
            }
        elif "dreamshaper" in m_lower or "v1-5" in m_lower or "v1.5" in m_lower:
            return {
                "image_steps": 20,
                "image_cfg": 7.0,
                "image_width": 512,
                "image_height": 768
            }
        else: # Standard SDXL
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
            new_settings["image_steps"] = new_settings.get("image_steps", defaults["image_steps"])
            new_settings["image_cfg"] = new_settings.get("image_cfg", defaults["image_cfg"])
            new_settings["image_width"] = new_settings.get("image_width", defaults["image_width"])
            new_settings["image_height"] = new_settings.get("image_height", defaults["image_height"])

        current.update(new_settings)
        try:
            with open(SETTINGS_FILE, "w") as f:
                json.dump(current, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
        return current

    @classmethod
    def discover_models(cls) -> Dict[str, List[Dict[str, Any]]]:
        models_root = "/home/jason/models"
        
        # 1. Discover LLM Models (Ollama API + local GGUFs in /home/jason/models/LLMs)
        llm_models = []
        try:
            resp = httpx.get("http://localhost:11434/api/tags", timeout=3.0)
            if resp.status_code == 200:
                data = resp.json()
                for m in data.get("models", []):
                    name = m.get("name")
                    if name and not any(l["id"] == name for l in llm_models):
                        llm_models.append({"id": name, "label": f"🤖 Ollama: {name}", "source": "ollama"})
        except Exception:
            pass

        # Scan local GGUF models in /home/jason/models/LLMs
        llm_dir = os.path.join(models_root, "LLMs")
        if os.path.exists(llm_dir):
            for root, _, files in os.walk(llm_dir):
                for file in files:
                    if file.endswith(".gguf") and not file.startswith("ggml-vocab"):
                        full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_path, llm_dir)
                        if not any(l["id"] == rel_path for l in llm_models):
                            llm_models.append({"id": rel_path, "label": f"📁 Local GGUF: {file}", "source": "gguf", "path": full_path})

        # Ensure default model is included
        if not any(l["id"] == settings.DEFAULT_MODEL for l in llm_models):
            llm_models.insert(0, {"id": settings.DEFAULT_MODEL, "label": f"🤖 Ollama: {settings.DEFAULT_MODEL}", "source": "ollama"})

        # 2. Discover Image Generation Models (Checkpoints + Diffusion models)
        image_models = []
        checkpoints_dir = os.path.join(models_root, "Checkpoints", "checkpoints")
        diffusion_dir = os.path.join(models_root, "Diffusion", "diffusion_models")
        other_sd_dir = os.path.join(models_root, "Other", "Stable-Diffusion")

        scan_dirs = [(checkpoints_dir, "Checkpoint"), (diffusion_dir, "Diffusion Model"), (other_sd_dir, "SD Model")]
        for s_dir, category in scan_dirs:
            if os.path.exists(s_dir):
                for root, _, files in os.walk(s_dir):
                    for file in files:
                        if file.endswith((".safetensors", ".gguf", ".ckpt")) and not file.startswith("put_") and not file.startswith("README"):
                            if not any(img["id"] == file for img in image_models):
                                image_models.append({
                                    "id": file,
                                    "label": f"🎨 {category}: {file}",
                                    "category": category
                                })

        # 3. Discover LoRAs with Architecture Tagging
        loras = [{"id": "", "label": "None (Base Model Only)"}]
        lora_scan_dirs = [
            os.path.join(models_root, "LoRAs"),
            "/home/jason/AI-ImageGen/ComfyUI/models/loras"
        ]
        for l_dir in lora_scan_dirs:
            if os.path.exists(l_dir):
                for root, _, files in os.walk(l_dir):
                    for file in files:
                        if file.endswith((".safetensors", ".ckpt")) and not file.startswith("put_"):
                            if not any(l["id"] == file for l in loras):
                                f_lower = file.lower()
                                arch = "FLUX" if "flux" in f_lower else ("SDXL" if "sdxl" in f_lower else "SD1.5/SDXL")
                                loras.append({"id": file, "label": f"✨ [{arch}] {file}"})


        return {
            "llm_models": llm_models,
            "image_models": image_models,
            "loras": loras
        }
