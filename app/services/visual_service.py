import os
import re
import json
import random
import time
import logging
import httpx
from typing import Dict, Any, Optional
from app.config import settings

logger = logging.getLogger(__name__)

class VisualPipelineService:
    """
    Visual Pipeline Service (Consistent Selfie & Image Generator).
    Generates realistic selfies and scene images using local models in /home/jason/models
    via local ComfyUI API runner (http://127.0.0.1:8188).
    """

    COMFYUI_URL = "http://127.0.0.1:8188"
    MODELS_DIR = "/home/jason/models"

    @classmethod
    def get_lora_trigger_word(cls, lora_filename: str) -> str:
        """
        Maps LoRA filenames to their specific required trigger words.
        """
        l_lower = lora_filename.lower()
        if "krea2" in l_lower or "krea_v1" in l_lower or "krea" in l_lower:
            return "krea style"
        elif "classic_painting" in l_lower or "classic painting" in l_lower:
            return "classic painting style, oil painting"
        elif "renaissance" in l_lower:
            return "renaissance art style"
        elif "pov" in l_lower:
            return "pov perspective"
        elif "cheating" in l_lower:
            return "caught cheating style"
        else:
            clean_name = os.path.splitext(lora_filename)[0].replace("_", " ").replace("-", " ")
            clean_name = re.sub(r'\b(v\d+|\d+)\b', '', clean_name, flags=re.IGNORECASE).strip()
            return f"{clean_name} style" if clean_name else ""

    @classmethod
    def prepare_comfy_workflow(
        cls, 
        prompt: str, 
        checkpoint_name: str = "juggernautXL_ragnarok.safetensors",
        width: int = 896,
        height: int = 1152,
        steps: int = 20,
        cfg: float = 7.0,
        companion_gender: str = "female",
        companion_name: Optional[str] = None,
        selected_lora: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Builds a ComfyUI prompt API workflow node graph.
        Dynamically adapts between FLUX UNet models and standard SD/SDXL Checkpoints,
        supporting single or multi-LoRA chaining and automatic trigger word injection.
        """
        seed = random.randint(1, 2147483647)
        
        # Determine if prompt is a scene/location photo or a person/selfie photo
        p_lower = prompt.lower()
        scene_keywords = ["view of", "room", "surroundings", "environment", "scenic", "landscape", "location", "interior", "living room", "bedroom", "kitchen", "cafe", "street", "building", "place"]
        person_keywords = ["selfie", "portrait", "person", "woman", "man", "girl", "guy", "face", "wearing", "looking at camera", "smiling"]
        
        is_scene = any(kw in p_lower for kw in scene_keywords) and not any(kw in p_lower for kw in person_keywords)

        is_flux2 = "flux-2" in checkpoint_name.lower() or "klein" in checkpoint_name.lower()
        is_flux1 = "flux" in checkpoint_name.lower() and not is_flux2
        is_flux = is_flux1 or is_flux2

        # Clean out any proper character names from prompt (e.g. "Cherry Rose", "Cherry") to prevent model confusion
        clean_prompt = prompt
        if companion_name:
            for name_variant in [companion_name, companion_name.split()[0]]:
                if name_variant and len(name_variant) > 1:
                    clean_prompt = re.sub(rf'\b{re.escape(name_variant)}\b', '', clean_prompt, flags=re.IGNORECASE).strip()

        # Clean extra commas or trailing whitespace left behind by name removal
        clean_prompt = re.sub(r'\s*,\s*,', ',', clean_prompt).strip(" ,")

        # Process multi-LoRA selection and auto-inject trigger words into positive prompt
        lora_list = [l.strip() for l in (selected_lora or "").split(",") if l.strip() and l.strip().lower() != "none"]
        trigger_words = []
        for l_file in lora_list:
            tw = cls.get_lora_trigger_word(l_file)
            if tw and tw.lower() not in clean_prompt.lower():
                trigger_words.append(tw)

        if trigger_words:
            clean_prompt = f"{clean_prompt}, {', '.join(trigger_words)}"

        if companion_gender.lower() == "male":
            gender_desc = "man"
            subject_tag = "1man, male"
            negative_tag = ", 1woman, female, feminine features, girl, dress"
        else:
            gender_desc = "woman"
            subject_tag = "1woman, female"
            negative_tag = ", 1man, male, masculine features, boy, guy, mustache, beard"

        if is_scene:
            if is_flux:
                positive_prompt = f"A detailed photorealistic photo of {clean_prompt}"
                negative_prompt = ""
            else:
                positive_prompt = f"masterpiece, best quality, photorealistic photo of {clean_prompt}, 8k, sharp focus, natural lighting"
                negative_prompt = f"blurry, low quality, distorted, bad architecture, deformed, 3d render{negative_tag}"
        else: # Selfie / Person request
            if is_flux:
                positive_prompt = f"A casual photorealistic selfie of a {gender_desc}, {clean_prompt}"
                negative_prompt = f"blurry, low quality, distorted, deformed{negative_tag}"
            else:
                positive_prompt = f"masterpiece, best quality, photorealistic selfie of {subject_tag}, {clean_prompt}, 8k, detailed skin texture, sharp focus, natural lighting"
                negative_prompt = f"blurry, low quality, distorted, extra limbs, bad face, deformed, bad hands, cartoon, 3d render{negative_tag}"

        # Check if the model is registered under ComfyUI UNETLoader or CheckpointLoaderSimple
        is_unet = False
        try:
            resp = httpx.get(f"{cls.COMFYUI_URL}/object_info/UNETLoader", timeout=2.0)
            if resp.status_code == 200:
                info = resp.json()
                unet_list = info.get("UNETLoader", {}).get("input", {}).get("required", {}).get("unet_name", [[]])[0]
                if checkpoint_name in unet_list:
                    is_unet = True
        except Exception:
            is_unet = checkpoint_name.lower() == "flux-2-klein-4b.safetensors"

        if "klein" in checkpoint_name.lower():
            klein_ckpt = "flux-2-klein-4b.safetensors"
            model_src = ["4", 0]
            clip_src = ["11", 0]

            workflow = {
                "4": {
                    "inputs": {"unet_name": klein_ckpt, "weight_dtype": "default"},
                    "class_type": "UNETLoader"
                },
                "10": {
                    "inputs": {"vae_name": "flux2-vae.safetensors"},
                    "class_type": "VAELoader"
                },
                "11": {
                    "inputs": {"clip_name": "qwen_3_4b.safetensors", "type": "flux2"},
                    "class_type": "CLIPLoader"
                },
                "5": {
                    "inputs": {"width": width, "height": height, "batch_size": 1},
                    "class_type": "EmptyLatentImage"
                }
            }

            # Chain LoRAs sequentially
            current_model = model_src
            current_clip = clip_src
            for idx, lora_file in enumerate(lora_list):
                lora_id = f"10_{idx + 1}"
                workflow[lora_id] = {
                    "inputs": {
                        "lora_name": lora_file,
                        "strength_model": 1.0,
                        "strength_clip": 1.0,
                        "model": current_model,
                        "clip": current_clip
                    },
                    "class_type": "LoraLoader"
                }
                current_model = [lora_id, 0]
                current_clip = [lora_id, 1]

            workflow["6"] = {
                "inputs": {"text": positive_prompt, "clip": current_clip},
                "class_type": "CLIPTextEncode"
            }
            workflow["7"] = {
                "inputs": {"text": "", "clip": current_clip},
                "class_type": "CLIPTextEncode"
            }
            workflow["3"] = {
                "inputs": {
                    "seed": seed,
                    "steps": steps if steps <= 8 else 4,
                    "cfg": 1.0,
                    "sampler_name": "euler",
                    "scheduler": "simple",
                    "denoise": 1.0,
                    "model": current_model,
                    "positive": ["6", 0],
                    "negative": ["7", 0],
                    "latent_image": ["5", 0]
                },
                "class_type": "KSampler"
            }
            workflow["8"] = {
                "inputs": {"samples": ["3", 0], "vae": ["10", 0]},
                "class_type": "VAEDecode"
            }
            workflow["9"] = {
                "inputs": {"filename_prefix": "XgirlfriendGPT", "images": ["8", 0]},
                "class_type": "SaveImage"
            }
            return workflow

        if is_flux:
            # Build loader node 4 dynamically based on whether model is registered in UNETLoader or CheckpointLoaderSimple
            if is_unet:
                model_node = {
                    "inputs": {
                        "unet_name": checkpoint_name,
                        "weight_dtype": "default"
                    },
                    "class_type": "UNETLoader"
                }
            else:
                model_node = {
                    "inputs": {
                        "ckpt_name": checkpoint_name
                    },
                    "class_type": "CheckpointLoaderSimple"
                }

            if is_flux2:
                clip_node = {
                    "inputs": {
                        "clip_name": "qwen_3_4b.safetensors",
                        "type": "flux2"
                    },
                    "class_type": "CLIPLoader"
                }
                vae_name = "flux2-vae.safetensors"
            else:
                clip_node = {
                    "inputs": {
                        "clip_name1": "t5xxl_fp8_e4m3fn.safetensors",
                        "clip_name2": "clip_l.safetensors",
                        "type": "flux"
                    },
                    "class_type": "DualCLIPLoader"
                }
                vae_name = "ae.safetensors"

            flux_guidance_val = 3.5 if cfg <= 1.0 else cfg
            return {
                "3": {
                    "inputs": {
                        "seed": seed,
                        "steps": steps,
                        "cfg": 1.0,
                        "sampler_name": "euler",
                        "scheduler": "simple" if is_flux else "normal",
                        "denoise": 1.0,
                        "model": ["4", 0],
                        "positive": ["12", 0],
                        "negative": ["7", 0],
                        "latent_image": ["5", 0]
                    },
                    "class_type": "KSampler"
                },
                "4": model_node,
                "5": {
                    "inputs": {
                        "width": width,
                        "height": height,
                        "batch_size": 1
                    },
                    "class_type": "EmptyFlux2LatentImage" if is_flux2 else "EmptyLatentImage"
                },
                "6": {
                    "inputs": {
                        "text": positive_prompt,
                        "clip": ["11", 0]
                    },
                    "class_type": "CLIPTextEncode"
                },
                "7": {
                    "inputs": {
                        "text": negative_prompt,
                        "clip": ["11", 0]
                    },
                    "class_type": "CLIPTextEncode"
                },
                "8": {
                    "inputs": {
                        "samples": ["3", 0],
                        "vae": ["10", 0]
                    },
                    "class_type": "VAEDecode"
                },
                "9": {
                    "inputs": {
                        "filename_prefix": "XgirlfriendGPT",
                        "images": ["8", 0]
                    },
                    "class_type": "SaveImage"
                },
                "10": {
                    "inputs": {
                        "vae_name": vae_name
                    },
                    "class_type": "VAELoader"
                },
                "11": clip_node,
                "12": {
                    "inputs": {
                        "conditioning": ["6", 0],
                        "guidance": flux_guidance_val
                    },
                    "class_type": "FluxGuidance"
                }
            }

        return {
            "3": {
                "inputs": {
                    "seed": seed,
                    "steps": steps,
                    "cfg": cfg,
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "denoise": 1.0,
                    "model": ["4", 0],
                    "positive": ["6", 0],
                    "negative": ["7", 0],
                    "latent_image": ["5", 0]
                },
                "class_type": "KSampler"
            },
            "4": {
                "inputs": {
                    "ckpt_name": checkpoint_name
                },
                "class_type": "CheckpointLoaderSimple"
            },
            "5": {
                "inputs": {
                    "width": width,
                    "height": height,
                    "batch_size": 1
                },
                "class_type": "EmptyLatentImage"
            },
            "6": {
                "inputs": {
                    "text": positive_prompt,
                    "clip": ["4", 1]
                },
                "class_type": "CLIPTextEncode"
            },
            "7": {
                "inputs": {
                    "text": negative_prompt,
                    "clip": ["4", 1]
                },
                "class_type": "CLIPTextEncode"
            },
            "8": {
                "inputs": {
                    "samples": ["3", 0],
                    "vae": ["4", 2]
                },
                "class_type": "VAEDecode"
            },
            "9": {
                "inputs": {
                    "filename_prefix": "XgirlfriendGPT",
                    "images": ["8", 0]
                },
                "class_type": "SaveImage"
            }
        }

    @classmethod
    def generate_selfie(
        cls, 
        prompt: str, 
        companion_id: str, 
        reference_face_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Submits image generation request to local ComfyUI API, waits for completion,
        and saves generated image locally to be served at /static/generated/{companion_id}/{filename}.
        """
        # Ensure static output directory exists
        output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static", "generated", companion_id))
        os.makedirs(output_dir, exist_ok=True)

        from app.services.settings_service import SettingsService
        from app.services.storage_service import StorageService

        active_cfg = SettingsService.get_settings()
        ckpt = active_cfg.get("image_model") or "juggernautXL_ragnarok.safetensors"
        width = int(active_cfg.get("image_width", 896))
        height = int(active_cfg.get("image_height", 1152))
        steps = int(active_cfg.get("image_steps", 20))
        cfg_val = float(active_cfg.get("image_cfg", 7.0))

        companion_data = StorageService.get_companion_by_id(companion_id)
        comp_name = None
        comp_gender = "female"
        if companion_data:
            comp_name = companion_data.get("name")
            desc = (companion_data.get("custom_description") or companion_data.get("system_prompt") or "").lower()
            if (" man " in f" {desc} " or " male " in f" {desc} ") and not ("woman" in desc or "female" in desc):
                comp_gender = "male"

        workflow = cls.prepare_comfy_workflow(
            prompt=prompt,
            checkpoint_name=ckpt,
            width=width,
            height=height,
            steps=steps,
            cfg=cfg_val,
            companion_gender=comp_gender,
            companion_name=comp_name,
            selected_lora=active_cfg.get("selected_lora", "")
        )

        try:
            # 1. Post prompt to ComfyUI
            resp = httpx.post(f"{cls.COMFYUI_URL}/prompt", json={"prompt": workflow}, timeout=10.0)
            if resp.status_code != 200:
                logger.error(f"ComfyUI prompt submission failed: {resp.text}")
                return cls._fallback_response(prompt, companion_id)

            prompt_data = resp.json()
            prompt_id = prompt_data.get("prompt_id")
            if not prompt_id:
                return cls._fallback_response(prompt, companion_id)

            # 2. Poll ComfyUI history endpoint until completed (up to 180s for cold model loading and VAE decode)
            start_time = time.time()
            filename = None

            while time.time() - start_time < 180.0:
                try:
                    history_resp = httpx.get(f"{cls.COMFYUI_URL}/history/{prompt_id}", timeout=5.0)
                    if history_resp.status_code == 200:
                        history_data = history_resp.json()
                        if prompt_id in history_data:
                            outputs = history_data[prompt_id].get("outputs", {})
                            # Search for SaveImage node outputs (Node "9")
                            for node_id, node_output in outputs.items():
                                images = node_output.get("images", [])
                                if images:
                                    img_info = images[0]
                                    filename = img_info.get("filename")
                                    break
                            if filename:
                                break
                except Exception:
                    pass
                time.sleep(1.5)

            # 3. Retrieve image bytes from local disk or ComfyUI view endpoint
            if filename:
                comfy_disk_path = f"/home/jason/AI-ImageGen/ComfyUI/output/{filename}"
                dest_file_path = os.path.join(output_dir, filename)

                if os.path.exists(comfy_disk_path):
                    import shutil
                    shutil.copyfile(comfy_disk_path, dest_file_path)
                else:
                    view_url = f"{cls.COMFYUI_URL}/view?filename={filename}&type=output"
                    img_bytes_resp = httpx.get(view_url, timeout=10.0)
                    if img_bytes_resp.status_code == 200:
                        with open(dest_file_path, "wb") as f:
                            f.write(img_bytes_resp.content)

                if os.path.exists(dest_file_path):
                    relative_url = f"/static/generated/{companion_id}/{filename}"
                    return {
                        "status": "success",
                        "image_url": relative_url,
                        "prompt_used": prompt
                    }

        except Exception as e:
            logger.warning(f"Error during ComfyUI generation: {e}")

        return cls._fallback_response(prompt, companion_id)

    @classmethod
    def _fallback_response(cls, prompt: str, companion_id: str) -> Dict[str, Any]:
        """
        Fallback response when ComfyUI is offline or generation timed out.
        """
        return {
            "status": "pending",
            "image_url": None,
            "prompt_used": prompt
        }

# Alias for backward compatibility and clean agent imports
VisualService = VisualPipelineService

