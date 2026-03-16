"""
测试 Claw 模型配置
"""
import sys
sys.path.insert(0, '.')

print("=" * 60)
print("Step 1: 导入 Base 和 engine")
from src.models import Base, engine

print("=" * 60)
print("Step 2: 导入 Claw 模型")
from src.models.claw import ClawConversation, ClawMessage, ClawToolCall

print("=" * 60)
print("Step 3: 检查模型列")
print("ClawConversation columns:", [c.name for c in ClawConversation.__table__.columns])
print("ClawMessage columns:", [c.name for c in ClawMessage.__table__.columns])

print("=" * 60)
print("Step 4: 检查关系")
print("ClawConversation.messages exists:", hasattr(ClawConversation, 'messages'))
print("ClawMessage.conversation exists:", hasattr(ClawMessage, 'conversation'))

print("=" * 60)
print("Step 5: 配置 mappers")
from sqlalchemy.orm import configure_mappers
try:
    configure_mappers()
    print("[OK] Mappers configured successfully")
except Exception as e:
    print("[FAIL] Mapper configuration failed:", e)
    import traceback
    traceback.print_exc()

print("=" * 60)
print("Step 6: 检查 mapper 的列映射")
from sqlalchemy import inspect
mapper = inspect(ClawConversation)
print("Mapped columns:", [c.key for c in mapper.columns])
print("Primary key:", [c.name for c in mapper.primary_key])

print("=" * 60)
print("Step 7: 测试创建对话")
from sqlalchemy.orm import Session
db = Session(bind=engine)

conv = ClawConversation(
    title='测试对话',
    working_directory='C:/test',
    llm_model='deepseek-chat'
)
db.add(conv)

try:
    db.commit()
    print("[OK] Conversation created successfully with id:", conv.id)
except Exception as e:
    print("[FAIL] Failed to create conversation:", e)
    import traceback
    traceback.print_exc()
finally:
    db.close()

print("=" * 60)
print("Test completed")
