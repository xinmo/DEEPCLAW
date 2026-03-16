from .kb import router as kb_router
from .chat import router as chat_router
from .documents import router as documents_router
from .graph import router as graph_router

__all__ = ["kb_router", "chat_router", "documents_router", "graph_router"]
