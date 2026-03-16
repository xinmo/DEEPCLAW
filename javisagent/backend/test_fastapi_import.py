"""
模拟 FastAPI 应用的导入顺序
"""
import sys
sys.path.insert(0, '.')

print("=" * 60)
print("Simulating FastAPI app.py import order")
print("=" * 60)

print("\n1. Import Base and engine")
from src.models import Base, engine

print("\n2. Import Claw models (as in app.py)")
from src.models.claw import ClawConversation, ClawMessage, ClawToolCall

print("\n3. Import Task model")
from src.models.task import Task

print("\n4. Import Knowledge models")
from src.models.knowledge import KnowledgeBase, KBDocument, Conversation, Message

print("\n5. Create all tables")
Base.metadata.create_all(bind=engine)

print("\n6. Import routes (this triggers model usage)")
from src.routes.claw import conversations_router

print("\n7. Test creating conversation via route logic")
from sqlalchemy.orm import Session

db = Session(bind=engine)
conv = ClawConversation(
    title='Test via FastAPI flow',
    working_directory='C:/test',
    llm_model='deepseek-chat'
)
db.add(conv)

try:
    db.commit()
    print("[OK] Conversation created with id:", conv.id)
except Exception as e:
    print("[FAIL] Error:", e)
    import traceback
    traceback.print_exc()
finally:
    db.close()

print("\n" + "=" * 60)
print("Test completed")
