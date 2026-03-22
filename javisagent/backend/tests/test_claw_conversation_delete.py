import importlib.util
from pathlib import Path
import sys
import types

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

fake_claw_service = types.ModuleType("src.services.claw")
fake_claw_service.create_claw_agent = lambda **_: None
fake_claw_service.validate_working_directory = lambda path: (True, None)
fake_claw_service.__path__ = [str(BACKEND_ROOT / "src" / "services" / "claw")]
sys.modules["src.services.claw"] = fake_claw_service

from src.models.base import Base
from src.models.channels import ChannelSession
from src.models.claw import ClawConversation

CONVERSATIONS_MODULE_PATH = BACKEND_ROOT / "src" / "routes" / "claw" / "conversations.py"
CONVERSATIONS_MODULE_NAME = "test_claw_conversations_delete_route"
conversations_spec = importlib.util.spec_from_file_location(
    CONVERSATIONS_MODULE_NAME,
    CONVERSATIONS_MODULE_PATH,
)
conversations_route = importlib.util.module_from_spec(conversations_spec)
sys.modules[CONVERSATIONS_MODULE_NAME] = conversations_route
assert conversations_spec.loader is not None
conversations_spec.loader.exec_module(conversations_route)


def build_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return testing_session_local()


@pytest.mark.asyncio
async def test_delete_conversation_removes_channel_session_mapping():
    db = build_session()
    conversation = ClawConversation(
        title="QQ - test-user",
        working_directory=str(Path.cwd()),
        llm_model="deepseek-chat",
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    db.add(
        ChannelSession(
            channel_name="qq",
            chat_id="chat-1",
            sender_id="sender-1",
            conversation_id=conversation.id,
            extra_data={},
        )
    )
    db.commit()

    await conversations_route.delete_conversation(conversation.id, db=db)

    assert db.query(ClawConversation).filter_by(id=conversation.id).first() is None
    assert (
        db.query(ChannelSession).filter_by(conversation_id=conversation.id).first() is None
    )
