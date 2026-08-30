"""Checkpointer and memory persistence for Sentinel chat threads."""

from langgraph.checkpoint.memory import MemorySaver

# Shared checkpointer instance for stateful conversations
_shared_checkpointer = MemorySaver()


def get_checkpointer() -> MemorySaver:
    """Return the active checkpointer instance."""
    return _shared_checkpointer


def get_thread_config(conversation_id: str) -> dict:
    """Construct configuration dict for LangGraph thread persistence."""
    return {"configurable": {"thread_id": str(conversation_id)}}
