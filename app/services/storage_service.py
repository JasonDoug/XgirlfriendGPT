import os
import json
import logging
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

    @classmethod
    def _ensure_dirs(cls):
        os.makedirs(DATA_DIR, exist_ok=True)
        os.makedirs(CHATS_DIR, exist_ok=True)
        os.makedirs(ROOM_CHATS_DIR, exist_ok=True)

    @classmethod
    def save_companion(cls, profile: CompanionProfile):
        cls._ensure_dirs()
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

        with open(COMPANIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(companions, f, indent=2)


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
        companions = cls.list_companions_raw()
        filtered = [c for c in companions if c["companion_id"] != companion_id]
        
        if len(filtered) < len(companions):
            with open(COMPANIONS_FILE, "w", encoding="utf-8") as f:
                json.dump(filtered, f, indent=2)
            
            # Remove chat history file if exists
            chat_file = os.path.join(CHATS_DIR, f"{companion_id}.json")
            if os.path.exists(chat_file):
                os.remove(chat_file)
            return True
        return False

    @classmethod
    def save_chat_history(cls, companion_id: str, history: List[Dict[str, str]]):
        cls._ensure_dirs()
        chat_file = os.path.join(CHATS_DIR, f"{companion_id}.json")
        with open(chat_file, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)

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
        rooms = cls.list_rooms()
        updated = False
        for i, r in enumerate(rooms):
            if r["room_id"] == room_dict["room_id"]:
                rooms[i] = room_dict
                updated = True
                break
        if not updated:
            rooms.append(room_dict)
        with open(ROOMS_FILE, "w", encoding="utf-8") as f:
            json.dump(rooms, f, indent=2)

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
        
        with open(room_chat_file, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)
