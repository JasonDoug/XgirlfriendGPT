from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from app.graph.state import CompanionState
from app.graph.agents.router_agent import RouterAgent
from app.graph.agents.persona_agent import PersonaAgent
from app.graph.agents.scene_agent import SceneAgent
from app.graph.agents.memory_agent import MemoryAgent

def router_node(state: CompanionState) -> CompanionState:
    return RouterAgent.select_speaker(state)

def scene_director_node(state: CompanionState) -> CompanionState:
    return SceneAgent.execute_visual(state)

async def persona_dialogue_node(state: CompanionState) -> CompanionState:
    return await PersonaAgent.generate_response_async(state)

def memory_extraction_node(state: CompanionState) -> CompanionState:
    return MemoryAgent.extract_and_store(state)

def route_decision(state: CompanionState) -> str:
    # If there are personas queued up to speak, continue speaking
    if state.pending_speakers:
        return "persona_speaker"
    # Once speaking turns finish, run background memory extraction
    return "memory_extractor"

def build_companion_graph(checkpointer=None):
    if checkpointer is None:
        checkpointer = MemorySaver()

    builder = StateGraph(CompanionState)

    builder.add_node("router", router_node)
    builder.add_node("scene_director", scene_director_node)
    builder.add_node("persona_speaker", persona_dialogue_node)
    builder.add_node("memory_extractor", memory_extraction_node)

    builder.set_entry_point("router")

    # Router checks intent / target speaker, then hands off to scene director
    builder.add_edge("router", "scene_director")

    builder.add_conditional_edges(
        "scene_director",
        route_decision,
        {
            "persona_speaker": "persona_speaker",
            "memory_extractor": "memory_extractor"
        }
    )

    # After a persona speaks, loop back to scene_director to check queue and visuals
    builder.add_edge("persona_speaker", "scene_director")
    builder.add_edge("memory_extractor", END)

    return builder.compile(checkpointer=checkpointer)

companion_graph = build_companion_graph()
