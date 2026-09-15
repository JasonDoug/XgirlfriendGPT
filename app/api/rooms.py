from fastapi import APIRouter, HTTPException, status
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

from app.models.room import (
    Room, 
    RoomParticipant, 
    RoomCreateRequest, 
    RoomMessageRequest, 
    RoomMessageResponse
)
from app.services.storage_service import StorageService
from app.services.memory_service import MemoryService
from app.graph.workflow import companion_graph
from app.graph.state import CompanionState

router = APIRouter(prefix="/api/v1/rooms", tags=["rooms"])

@router.post("/create", response_model=Room, status_code=status.HTTP_201_CREATED)
def create_room(request: RoomCreateRequest):
    """
    Creates a new multi-persona group chat room.
    """
    participants: List[RoomParticipant] = []
    for comp_id in request.companion_ids:
        comp_data = StorageService.get_companion_by_id(comp_id)
        if not comp_data:
            raise HTTPException(
                status_code=404, 
                detail=f"Companion ID '{comp_id}' not found."
            )
        participants.append(
            RoomParticipant(
                companion_id=comp_id,
                name=comp_data.get("name", "Companion")
            )
        )

    room_id = f"room_{uuid.uuid4().hex[:10]}"
    room = Room(
        room_id=room_id,
        name=request.name,
        description=request.description,
        user_id=request.user_id,
        participants=participants
    )

    StorageService.save_room(room.model_dump(mode="json"))
    return room


@router.get("", response_model=List[Room])
def list_rooms(user_id: Optional[str] = None):
    """
    Lists group chat rooms, optionally filtered by user_id.
    """
    raw_rooms = StorageService.list_rooms(user_id=user_id)
    return [Room(**r) for r in raw_rooms]

@router.get("/{room_id}", response_model=Room)
def get_room(room_id: str):
    """
    Retrieves a room by ID.
    """
    raw_room = StorageService.get_room_by_id(room_id)
    if not raw_room:
        raise HTTPException(status_code=404, detail="Room not found.")
    return Room(**raw_room)

@router.post("/message", response_model=RoomMessageResponse)
async def send_room_message(request: RoomMessageRequest):
    """
    Executes a multi-persona group chat turn using the LangGraph multi-agent orchestrator.
    """
    raw_room = StorageService.get_room_by_id(request.room_id)
    if not raw_room:
        raise HTTPException(status_code=404, detail="Room not found.")

    room = Room(**raw_room)
    active_ids = [p.companion_id for p in room.participants]
    
    # Load companion profiles
    companion_profiles: Dict[str, Any] = {}
    for comp_id in active_ids:
        c_data = StorageService.get_companion_by_id(comp_id)
        if c_data:
            companion_profiles[comp_id] = c_data

    if not companion_profiles:
        raise HTTPException(status_code=400, detail="No valid companions found in this room.")

    # Load history
    history = StorageService.get_room_history(request.room_id, limit=10)

    # Retrieve memories if enabled
    recalled_memories: List[str] = []
    if request.enable_memory:
        mem_service = MemoryService()
        for comp_id in active_ids:
            m_list = mem_service.retrieve_memories(
                companion_id=comp_id,
                user_id=request.user_id,
                query=request.message,
                limit=3
            )
            recalled_memories.extend(m_list)

    # Build Initial State
    initial_state = CompanionState(
        room_id=request.room_id,
        user_id=request.user_id,
        user_message=request.message,
        active_companion_ids=active_ids,
        companion_profiles=companion_profiles,
        message_history=history,
        recalled_memories=recalled_memories,
        current_speaker_id=request.target_companion_id
    )

    # Invoke LangGraph Workflow
    final_state_dict = await companion_graph.ainvoke(initial_state)

    speaker_id = final_state_dict.get("current_speaker_id") or active_ids[0]
    speaker_name = final_state_dict.get("current_speaker_name") or companion_profiles[speaker_id].get("name", "Companion")
    reply_text = final_state_dict.get("reply") or "Hey!"
    image_url = final_state_dict.get("image_url")

    # Persist turns in history
    StorageService.append_room_message(
        room_id=request.room_id,
        role="user",
        speaker_id=request.user_id,
        speaker_name="User",
        content=request.message
    )
    
    StorageService.append_room_message(
        room_id=request.room_id,
        role="assistant",
        speaker_id=speaker_id,
        speaker_name=speaker_name,
        content=reply_text,
        image_url=image_url
    )

    return RoomMessageResponse(
        room_id=request.room_id,
        speaker_id=speaker_id,
        speaker_name=speaker_name,
        reply=reply_text,
        image_url=image_url
    )
