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

        lora_list = []
        if selected_lora:
            if isinstance(selected_lora, list):
                lora_list = [l for l in selected_lora if l]
            elif isinstance(selected_lora, str) and selected_lora.strip():
                lora_list = [selected_lora.strip()]

        trigger_word = cls.get_lora_trigger_word(selected_lora) if selected_lora and isinstance(selected_lora, str) else ""
        
        prompt_parts = []
        if trigger_word and trigger_word.lower() not in prompt.lower():
            prompt_parts.append(trigger_word)
        
        if not is_scene:
            prefix = ""
            if companion_gender.lower() == "male":
                prefix = f"photo of a handsome man{f' named {companion_name}' if companion_name else ''}"
            else:
                prefix = f"photo of a beautiful woman{f' named {companion_name}' if companion_name else ''}"
            if prefix.lower() not in prompt.lower():
                prompt_parts.append(prefix)
                
        prompt_parts.append(prompt)
        positive_prompt = ", ".join(prompt_parts)
        negative_prompt = "blurry, low quality, distorted, watermark, signature, bad anatomy, deformed"

        # Check if the model is registered under ComfyUI UNETLoader or CheckpointLoaderSimple
        use_unet_loader = False
        try:
            resp = httpx.get(f"{cls.COMFYUI_URL}/object_info/UNETLoader", timeout=2.0)
            if resp.status_code == 200:
                info = resp.json()
                unet_list = info.get("UNETLoader", {}).get("input", {}).get("required", {}).get("unet_name", [[]])[0]
                if checkpoint_name in unet_list:
                    use_unet_loader = True
        except Exception:
            pass

        ckpt_lower = checkpoint_name.lower()
        is_unet = use_unet_loader or any(kw in ckpt_lower for kw in [".gguf", "klein", "unet", "z-image", "fp8", "swarmui", "turbo", "flux"])

        is_flux2 = "flux-2" in ckpt_lower or "klein" in ckpt_lower or "z-image" in ckpt_lower or "lumina" in ckpt_lower
        is_flux1 = "flux" in ckpt_lower and not is_flux2
        is_flux = is_flux1 or is_flux2 or is_unet

        if "klein" in checkpoint_name.lower():
            klein_ckpt = checkpoint_name
            model_src = ["4", 0]
            clip_src = ["11", 0]

            workflow = {
                "4": {
                    "inputs": {"unet_name": klein_ckpt, "weight_dtype": "default"} if use_unet_loader else {"ckpt_name": klein_ckpt},
                    "class_type": "UNETLoader" if use_unet_loader else "CheckpointLoaderSimple"
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
            if use_unet_loader:
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
                clip_type_val = "lumina2" if ("z-image" in ckpt_lower or "lumina" in ckpt_lower) else "flux2"
                clip_node = {
                    "inputs": {
                        "clip_name": "qwen_3_4b.safetensors",
                        "type": clip_type_val
                    },
                    "class_type": "CLIPLoader"
                }
                vae_name = "ae.safetensors" if ("z-image" in ckpt_lower or "lumina" in ckpt_lower) else "flux2-vae.safetensors"
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
                    "class_type": "EmptyLatentImage"
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
        reference_face_url: Optional[str] = None,
        max_wait_seconds: float = 180.0
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

            appearance_text = companion_data.get("appearance_description") or (companion_data.get("traits") or {}).get("physical_appearance")
            if not appearance_text and companion_data.get("system_prompt"):
                from app.services.prompt_builder import PromptBuilderService
                appearance_text = PromptBuilderService.extract_physical_descriptors(companion_data.get("system_prompt"))
            if appearance_text and appearance_text.strip():
                clean_app = appearance_text.strip()
                if clean_app.lower() not in prompt.lower():
                    prompt = f"{clean_app}, {prompt}"

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
            resp = httpx.post(f"{cls.COMFYUI_URL}/prompt", json={"prompt": workflow}, timeout=5.0)
            if resp.status_code != 200:
                logger.error(f"ComfyUI prompt submission failed: {resp.text}")
                return cls._fallback_response(prompt, companion_id)

            prompt_data = resp.json()
            prompt_id = prompt_data.get("prompt_id")
            if not prompt_id:
                return cls._fallback_response(prompt, companion_id)

            # 2. Poll ComfyUI history endpoint until completed
            start_time = time.time()
            filename = None

            while time.time() - start_time < max_wait_seconds:
                try:
                    history_resp = httpx.get(f"{cls.COMFYUI_URL}/history/{prompt_id}", timeout=5.0)
                    if history_resp.status_code == 200:
                        history_data = history_resp.json()
                        if prompt_id in history_data:
                            outputs = history_data[prompt_id].get("outputs", {})
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
                time.sleep(2.0)

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
    async def generate_selfie_async(cls, prompt: str, companion_id: str, is_character_card: bool = False) -> Dict[str, Any]:
        """
        Asynchronously generates a selfie/image using ComfyUI with non-blocking event loop polling.
        """
        import asyncio
        output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "generated", companion_id)
        await asyncio.to_thread(os.makedirs, output_dir, exist_ok=True)

        comp_name = "Companion"
        comp_gender = "female"
        from app.services.storage_service import StorageService
        profile = await asyncio.to_thread(StorageService.get_companion_by_id, companion_id)
        if profile:
            comp_name = profile.get("name", comp_name)
            custom_desc = profile.get("system_prompt", "")
            if "male" in custom_desc.lower() and "female" not in custom_desc.lower():
                comp_gender = "male"

            appearance_text = profile.get("appearance_description") or (profile.get("traits") or {}).get("physical_appearance")
            if not appearance_text and custom_desc:
                from app.services.prompt_builder import PromptBuilderService
                appearance_text = PromptBuilderService.extract_physical_descriptors(custom_desc)
            if appearance_text and appearance_text.strip():
                clean_app = appearance_text.strip()
                if clean_app.lower() not in prompt.lower():
                    prompt = f"{clean_app}, {prompt}"

        from app.services.settings_service import SettingsService
        active_cfg = await asyncio.to_thread(SettingsService.get_settings)
        ckpt = active_cfg.get("image_model") or "flux1-dev-fp8.safetensors"
        width = int(active_cfg.get("image_width", 512))
        height = int(active_cfg.get("image_height", 768))
        steps = int(active_cfg.get("image_steps", 20))
        cfg_val = float(active_cfg.get("image_cfg", 1.0))

        workflow = await asyncio.to_thread(
            cls.prepare_comfy_workflow,
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
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(f"{cls.COMFYUI_URL}/prompt", json={"prompt": workflow})
                if resp.status_code != 200:
                    logger.error(f"ComfyUI prompt submission failed: {resp.text}")
                    return cls._fallback_response(prompt, companion_id)

                prompt_data = resp.json()
                prompt_id = prompt_data.get("prompt_id")
                if not prompt_id:
                    return cls._fallback_response(prompt, companion_id)

            start_time = time.time()
            filename = None

            async with httpx.AsyncClient(timeout=10.0) as client:
                while time.time() - start_time < 180.0:
                    try:
                        history_resp = await client.get(f"{cls.COMFYUI_URL}/history/{prompt_id}")
                        if history_resp.status_code == 200:
                            history_data = history_resp.json()
                            if prompt_id in history_data:
                                prompt_entry = history_data[prompt_id]
                                status_info = prompt_entry.get("status", {})
                                if status_info.get("status_str") == "error":
                                    messages = status_info.get("messages", [])
                                    err_msg = "ComfyUI execution error"
                                    for m in messages:
                                        if isinstance(m, list) and len(m) > 1 and m[0] == "execution_error":
                                            err_msg = m[1].get("exception_message") or err_msg
                                            break
                                    logger.error(f"ComfyUI prompt {prompt_id} failed: {err_msg}")
                                    break

                                outputs = prompt_entry.get("outputs", {})
                                for node_id, node_output in outputs.items():
                                    images = node_output.get("images", [])
                                    if images:
                                        img_info = images[0]
                                        filename = img_info.get("filename")
                                        break
                                if filename:
                                    break
                    except Exception as e:
                        logger.warning(f"Error checking ComfyUI history: {e}")
                    await asyncio.sleep(1.0)

            if filename:
                comfy_disk_path = f"/home/jason/AI-ImageGen/ComfyUI/output/{filename}"
                dest_file_path = os.path.join(output_dir, filename)

                exists_comfy = await asyncio.to_thread(os.path.exists, comfy_disk_path)
                if exists_comfy:
                    import shutil
                    await asyncio.to_thread(shutil.copyfile, comfy_disk_path, dest_file_path)
                else:
                    view_url = f"{cls.COMFYUI_URL}/view?filename={filename}&type=output"
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        img_bytes_resp = await client.get(view_url)
                        if img_bytes_resp.status_code == 200:
                            def write_bytes(path, data):
                                with open(path, "wb") as f:
                                    f.write(data)
                            await asyncio.to_thread(write_bytes, dest_file_path, img_bytes_resp.content)

                exists_dest = await asyncio.to_thread(os.path.exists, dest_file_path)
                if exists_dest:
                    relative_url = f"/static/generated/{companion_id}/{filename}"
                    return {
                        "status": "success",
                        "image_url": relative_url,
                        "prompt_used": prompt
                    }

        except Exception as e:
            logger.warning(f"Error during async ComfyUI generation: {e}")

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

