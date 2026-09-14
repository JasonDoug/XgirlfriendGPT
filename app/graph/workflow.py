from langgraph.graph import StateGraph, END
from app.graph.state import CompanionState
from app.graph.agents.router_agent import RouterAgent
from app.graph.agents.persona_agent import PersonaAgent
from app.graph.agents.scene_agent import SceneAgent
from app.graph.agents.memory_agent import MemoryAgent

def router_node(state: CompanionState) -> CompanionState:
    return RouterAgent.select_speaker(state)

def persona_node(state: CompanionState) -> CompanionState:
    return PersonaAgent.generate_response(state)

def scene_node(state: CompanionState) -> CompanionState:
    return SceneAgent.execute_visual(state)

def memory_node(state: CompanionState) -> CompanionState:
    return MemoryAgent.extract_and_store(state)

def build_companion_graph():
    builder = StateGraph(CompanionState)

    builder.add_node("router", router_node)
    builder.add_node("persona", persona_node)
    builder.add_node("scene", scene_node)
    builder.add_node("memory", memory_node)

    builder.set_entry_point("router")

    builder.add_edge("router", "persona")
    builder.add_edge("persona", "scene")
    builder.add_edge("scene", "memory")
    builder.add_edge("memory", END)

    return builder.compile()

companion_graph = build_companion_graph()
