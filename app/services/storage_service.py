import os
import json
import logging
import threading
import tempfile
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.models.personality import CompanionProfile

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
COMPANIONS_FILE = os.path.join(DATA_DIR, "companions.json")
ROOMS_FILE = os.path.join(DATA_DIR, "rooms.json")
CHATS_DIR = os.path.join(DATA_DIR, "chats")
ROOM_CHATS_DIR = os.path.join(DATA_DIR, "room_chats")

class StorageService:
    """
    Persistent Disk Storage Service for Companion Profiles, Rooms, & Multi-Turn Chat Histories.
    Saves characters & multi-persona rooms permanently.
    """
    _file_lock = threading.Lock()

    @classmethod
    def _ensure_dirs(cls):
        os.makedirs(DATA_DIR, exist_ok=True)
        os.makedirs(CHATS_DIR, exist_ok=True)
        os.makedirs(ROOM_CHATS_DIR, exist_ok=True)
        try:
            os.chmod(DATA_DIR, 0o777)
            os.chmod(CHATS_DIR, 0o777)
            os.chmod(ROOM_CHATS_DIR, 0o777)
        except Exception:
            pass

    @classmethod
    def _atomic_write_json(cls, file_path: str, data: Any):
        dir_name = os.path.dirname(file_path)
        os.makedirs(dir_name, exist_ok=True)
        temp_fd, temp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
        try:
            with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            try:
                os.chmod(temp_path, 0o666)
            except Exception:
                pass
            os.replace(temp_path, file_path)
            try:
                os.chmod(file_path, 0o666)
            except Exception:
                pass
        except Exception:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
            raise

    @classmethod
    def save_companion(cls, profile: CompanionProfile):
        cls._ensure_dirs()
        with cls._file_lock:
            companions = cls.list_companions_raw()
            
            # Update existing profile matching companion_id or character name
            updated = False
            for i, c in enumerate(companions):
                if c["companion_id"] == profile.companion_id or c.get("name", "").lower() == profile.name.lower():
                    companions[i] = profile.model_dump(mode="json")
                    updated = True
                    break
            
            if not updated:
                companions.append(profile.model_dump(mode="json"))

            cls._atomic_write_json(COMPANIONS_FILE, companions)

    @classmethod
    def list_companions_raw(cls) -> List[Dict[str, Any]]:
        cls._ensure_dirs()
        if not os.path.exists(COMPANIONS_FILE):
            return []
        try:
            with open(COMPANIONS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading companions file: {e}")
            return []

    @classmethod
    def get_companion_by_id(cls, companion_id: str) -> Optional[Dict[str, Any]]:
        companions = cls.list_companions_raw()
        for c in companions:
            if c["companion_id"] == companion_id:
                return c
        return None

    @classmethod
    def delete_companion(cls, companion_id: str) -> bool:
        cls._ensure_dirs()
        with cls._file_lock:
            companions = cls.list_companions_raw()
            filtered = [c for c in companions if c["companion_id"] != companion_id]
            
            if len(filtered) < len(companions):
                cls._atomic_write_json(COMPANIONS_FILE, filtered)
                
                # Remove chat history file if exists
                chat_file = os.path.join(CHATS_DIR, f"{companion_id}.json")
                if os.path.exists(chat_file):
                    os.remove(chat_file)
                return True
            return False

    @classmethod
    def save_chat_history(cls, companion_id: str, history: List[Dict[str, str]]):
        cls._ensure_dirs()
        with cls._file_lock:
            chat_file = os.path.join(CHATS_DIR, f"{companion_id}.json")
            cls._atomic_write_json(chat_file, history)

    @classmethod
    def get_chat_history(cls, companion_id: str) -> List[Dict[str, str]]:
        cls._ensure_dirs()
        chat_file = os.path.join(CHATS_DIR, f"{companion_id}.json")
        if not os.path.exists(chat_file):
            return []
        try:
            with open(chat_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading chat history for {companion_id}: {e}")
            return []

    # Room Management Methods
    @classmethod
    def save_room(cls, room_dict: Dict[str, Any]):
        cls._ensure_dirs()
        with cls._file_lock:
            rooms = cls.list_rooms()
            updated = False
            for i, r in enumerate(rooms):
                if r["room_id"] == room_dict["room_id"]:
                    rooms[i] = room_dict
                    updated = True
                    break
            if not updated:
                rooms.append(room_dict)
            cls._atomic_write_json(ROOMS_FILE, rooms)

    @classmethod
    def delete_room(cls, room_id: str) -> bool:
        cls._ensure_dirs()
        with cls._file_lock:
            rooms = cls.list_rooms()
            filtered = [r for r in rooms if r["room_id"] != room_id]
            if len(filtered) == len(rooms):
                return False
            cls._atomic_write_json(ROOMS_FILE, filtered)
            room_chat_file = os.path.join(ROOM_CHATS_DIR, f"{room_id}.json")
            if os.path.exists(room_chat_file):
                try:
                    os.remove(room_chat_file)
                except Exception:
                    pass
            return True

    @classmethod
    def list_rooms(cls, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        cls._ensure_dirs()
        if not os.path.exists(ROOMS_FILE):
            return []
        try:
            with open(ROOMS_FILE, "r", encoding="utf-8") as f:
                rooms = json.load(f)
                if user_id:
                    rooms = [r for r in rooms if r.get("user_id") == user_id]
                return rooms
        except Exception as e:
            logger.error(f"Error loading rooms file: {e}")
            return []

    @classmethod
    def get_room_by_id(cls, room_id: str) -> Optional[Dict[str, Any]]:
        rooms = cls.list_rooms()
        for r in rooms:
            if r["room_id"] == room_id:
                return r
        return None

    @classmethod
    def get_room_history(cls, room_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        cls._ensure_dirs()
        room_chat_file = os.path.join(ROOM_CHATS_DIR, f"{room_id}.json")
        if not os.path.exists(room_chat_file):
            return []
        try:
            with open(room_chat_file, "r", encoding="utf-8") as f:
                history = json.load(f)
                return history[-limit:]
        except Exception as e:
            logger.error(f"Error loading room chat history for {room_id}: {e}")
            return []

    @classmethod
    def append_room_message(
        cls, 
        room_id: str, 
        role: str, 
        speaker_id: str, 
        speaker_name: str, 
        content: str, 
        image_url: Optional[str] = None
    ):
        cls._ensure_dirs()
        with cls._file_lock:
            room_chat_file = os.path.join(ROOM_CHATS_DIR, f"{room_id}.json")
            history = cls.get_room_history(room_id, limit=500)
            
            msg_entry = {
                "role": role,
                "speaker_id": speaker_id,
                "speaker_name": speaker_name,
                "content": content,
                "image_url": image_url,
                "timestamp": datetime.utcnow().isoformat()
            }
            history.append(msg_entry)
            
            cls._atomic_write_json(room_chat_file, history)
