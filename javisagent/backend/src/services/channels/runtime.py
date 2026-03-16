from __future__ import annotations

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from src.models.base import SessionLocal
from src.services.channels.registry import get_qq_channel_config

logger = logging.getLogger(__name__)

NANOBOT_ROOT = Path(__file__).resolve().parents[4] / "nanobot-main"
if NANOBOT_ROOT.exists():
    nanobot_root = str(NANOBOT_ROOT)
    if nanobot_root not in sys.path:
        sys.path.insert(0, nanobot_root)

try:
    from nanobot.bus.events import OutboundMessage
    from nanobot.bus.queue import MessageBus
    from nanobot.channels.qq import QQ_AVAILABLE, QQChannel
    from nanobot.config.schema import QQConfig

    NANOBOT_AVAILABLE = True
except Exception:
    OutboundMessage = None
    MessageBus = None
    QQ_AVAILABLE = False
    QQChannel = None
    QQConfig = None
    NANOBOT_AVAILABLE = False


class ChannelRuntimeManager:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._bus = None
        self._channel = None
        self._runner_task: asyncio.Task | None = None
        self._inbound_task: asyncio.Task | None = None
        self._outbound_task: asyncio.Task | None = None
        self._state = "disabled"
        self._message = "QQ 渠道尚未启用。"
        self._updated_at: datetime | None = None

    def _set_status(self, state: str, message: str, *, running: bool | None = None) -> None:
        self._state = state
        self._message = message
        self._updated_at = datetime.utcnow()
        if running is not None and self._channel is not None:
            self._channel._running = running

    def get_qq_runtime_status(self) -> dict[str, Any]:
        running = bool(self._channel and getattr(self._channel, "is_running", False))
        return {
            "installed": bool(QQ_AVAILABLE),
            "available": bool(NANOBOT_AVAILABLE and QQChannel and QQConfig and MessageBus),
            "running": running,
            "state": self._state,
            "message": self._message,
            "updated_at": self._updated_at.isoformat() if self._updated_at else None,
        }

    async def initialize(self) -> None:
        await self.refresh_from_db()

    async def shutdown(self) -> None:
        async with self._lock:
            await self._stop_qq_locked()
            self._set_status("stopped", "QQ 渠道已停止。", running=False)

    async def refresh_from_db(self) -> None:
        db = SessionLocal()
        try:
            qq_config = get_qq_channel_config(db)
        finally:
            db.close()

        async with self._lock:
            await self._apply_qq_config_locked(qq_config)

    async def _apply_qq_config_locked(self, qq_config: dict[str, Any]) -> None:
        await self._stop_qq_locked()

        if not qq_config["enabled"]:
            self._set_status("disabled", "QQ 渠道未启用。", running=False)
            return

        if not NANOBOT_AVAILABLE or QQChannel is None or QQConfig is None or MessageBus is None:
            self._set_status(
                "unavailable",
                "QQ 运行时依赖未加载，无法启动渠道。",
                running=False,
            )
            return

        if not QQ_AVAILABLE:
            self._set_status(
                "unavailable",
                "缺少 QQ SDK，请安装 qq-botpy 后再启动渠道。",
                running=False,
            )
            return

        if qq_config["validation_errors"]:
            self._set_status(
                "error",
                "QQ 渠道配置不完整，暂时无法启动。",
                running=False,
            )
            return

        config_payload = qq_config["config"]
        self._bus = MessageBus()
        self._channel = QQChannel(
            QQConfig(
                enabled=True,
                app_id=config_payload["app_id"],
                secret=config_payload["secret"],
                allow_from=config_payload["allow_from"],
            ),
            self._bus,
        )
        self._runner_task = asyncio.create_task(self._run_qq_channel(), name="javis-qq-runner")
        self._inbound_task = asyncio.create_task(self._consume_inbound(), name="javis-qq-inbound")
        self._outbound_task = asyncio.create_task(
            self._dispatch_outbound(),
            name="javis-qq-outbound",
        )
        self._set_status("running", "QQ 渠道运行中。", running=True)

    async def _run_qq_channel(self) -> None:
        try:
            if self._channel is None:
                return
            await self._channel.start()
            if self._state == "running":
                self._set_status("stopped", "QQ 渠道已停止。", running=False)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("QQ channel runner failed")
            self._set_status("error", f"QQ 渠道启动失败: {exc}", running=False)

    async def _consume_inbound(self) -> None:
        try:
            from src.services.channels.claw_bridge import process_inbound_message

            while self._bus is not None:
                inbound_message = await self._bus.consume_inbound()
                reply = await process_inbound_message(inbound_message)
                if not reply or self._bus is None or OutboundMessage is None:
                    continue
                await self._bus.publish_outbound(
                    OutboundMessage(
                        channel="qq",
                        chat_id=str(inbound_message.chat_id),
                        content=reply,
                    )
                )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("QQ inbound consumer failed")
            self._set_status("error", f"QQ 入站消息处理失败: {exc}", running=False)

    async def _dispatch_outbound(self) -> None:
        try:
            while self._bus is not None and self._channel is not None:
                outbound_message = await self._bus.consume_outbound()
                await self._channel.send(outbound_message)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("QQ outbound dispatcher failed")
            self._set_status("error", f"QQ 出站消息发送失败: {exc}", running=False)

    async def _stop_qq_locked(self) -> None:
        tasks = [self._inbound_task, self._outbound_task, self._runner_task]
        for task in tasks:
            if task is None:
                continue
            task.cancel()

        for task in tasks:
            if task is None:
                continue
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception:
                logger.exception("Error while stopping QQ task")

        if self._channel is not None:
            try:
                await self._channel.stop()
            except Exception:
                logger.exception("Error while stopping QQ channel")

        self._runner_task = None
        self._inbound_task = None
        self._outbound_task = None
        self._channel = None
        self._bus = None


channel_runtime = ChannelRuntimeManager()
