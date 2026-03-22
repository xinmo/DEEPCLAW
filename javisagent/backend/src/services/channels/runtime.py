from __future__ import annotations

import asyncio
import logging
import sys
from collections import deque
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.models.base import SessionLocal
from src.services.channels.registry import (
    get_qq_channel_config,
    normalize_qq_config,
    validate_qq_config,
)

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
        self._logs: deque[dict[str, str]] = deque(maxlen=200)
        self._record_log("info", "QQ 渠道运行时已初始化。", source="javis.channels.qq.runtime")

    def _now(self) -> datetime:
        return datetime.now(UTC)

    def _isoformat(self, value: datetime | None = None) -> str:
        return (value or self._now()).isoformat()

    def _append_log(self, *, level: str, source: str, message: str) -> None:
        self._logs.append(
            {
                "timestamp": self._isoformat(),
                "level": level.upper(),
                "source": source,
                "message": message,
            }
        )

    def _record_log(self, level: str, message: str, *, source: str) -> None:
        level_name = level.upper()
        log_method = {
            "DEBUG": logger.debug,
            "INFO": logger.info,
            "WARNING": logger.warning,
            "ERROR": logger.error,
        }.get(level_name, logger.info)
        log_method("%s: %s", source, message)
        self._append_log(level=level_name, source=source, message=message)

    def _set_status(self, state: str, message: str, *, running: bool | None = None) -> None:
        changed = state != self._state or message != self._message
        self._state = state
        self._message = message
        self._updated_at = self._now()
        if running is not None and self._channel is not None:
            self._channel._running = running
        if changed:
            log_level = "error" if state == "error" else "warning" if state == "unavailable" else "info"
            self._record_log(log_level, message, source="javis.channels.qq.runtime")

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

    def get_qq_logs(self, *, limit: int = 100) -> list[dict[str, str]]:
        safe_limit = max(1, min(limit, self._logs.maxlen or limit))
        return list(reversed(list(self._logs)[-safe_limit:]))

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
            self._record_log("info", "开始启动 QQ 渠道。", source="javis.channels.qq.runner")
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

            self._record_log("info", "QQ 入站消息消费者已启动。", source="javis.channels.qq.inbound")
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
            self._record_log("info", "QQ 出站消息发送器已启动。", source="javis.channels.qq.outbound")
            while self._bus is not None and self._channel is not None:
                outbound_message = await self._bus.consume_outbound()
                await self._channel.send(outbound_message)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("QQ outbound dispatcher failed")
            self._set_status("error", f"QQ 出站消息发送失败: {exc}", running=False)

    async def test_qq_connection(self, payload: dict[str, Any]) -> dict[str, Any]:
        normalized = normalize_qq_config(payload)
        checks: list[dict[str, str]] = []
        tested_at = self._isoformat()
        runtime = self.get_qq_runtime_status()

        validation_errors = validate_qq_config(True, normalized)
        if validation_errors:
            checks.append(
                {
                    "key": "configuration",
                    "label": "参数检查",
                    "status": "error",
                    "message": "；".join(validation_errors),
                }
            )
            self._record_log("warning", "QQ 测试连接失败：参数不完整。", source="javis.channels.qq.test")
            return {
                "success": False,
                "state": "error",
                "message": "测试连接前需要先填写完整的 App ID 和 App Secret。",
                "tested_at": tested_at,
                "checks": checks,
                "runtime": runtime,
            }

        checks.append(
            {
                "key": "configuration",
                "label": "参数检查",
                "status": "success",
                "message": "App ID、App Secret 和白名单参数格式检查通过。",
            }
        )

        runtime_available = bool(NANOBOT_AVAILABLE and QQChannel and QQConfig and MessageBus)
        checks.append(
            {
                "key": "runtime",
                "label": "运行时依赖",
                "status": "success" if runtime_available else "error",
                "message": (
                    "nanobot QQ 运行时可用。"
                    if runtime_available
                    else "nanobot QQ 运行时未加载，当前环境无法发起连接测试。"
                ),
            }
        )
        if not runtime_available:
            self._record_log("error", "QQ 测试连接失败：nanobot 运行时不可用。", source="javis.channels.qq.test")
            return {
                "success": False,
                "state": "error",
                "message": "当前环境缺少 nanobot QQ 运行时，无法执行测试连接。",
                "tested_at": tested_at,
                "checks": checks,
                "runtime": runtime,
            }

        checks.append(
            {
                "key": "sdk",
                "label": "SDK 检查",
                "status": "success" if QQ_AVAILABLE else "error",
                "message": (
                    "qq-botpy 已安装，可以执行实际握手测试。"
                    if QQ_AVAILABLE
                    else "缺少 qq-botpy，暂时无法执行实际握手测试。"
                ),
            }
        )
        if not QQ_AVAILABLE:
            self._record_log("error", "QQ 测试连接失败：缺少 qq-botpy。", source="javis.channels.qq.test")
            return {
                "success": False,
                "state": "error",
                "message": "当前环境缺少 qq-botpy，无法执行测试连接。",
                "tested_at": tested_at,
                "checks": checks,
                "runtime": runtime,
            }

        if runtime["running"]:
            db = SessionLocal()
            try:
                saved_detail = get_qq_channel_config(db)
            finally:
                db.close()

            saved_config = normalize_qq_config(saved_detail["config"])
            if saved_config == normalized:
                checks.append(
                    {
                        "key": "live_probe",
                        "label": "实际连接",
                        "status": "success",
                        "message": "当前 QQ 渠道已经使用同一份配置运行中，跳过额外握手测试。",
                    }
                )
                self._record_log(
                    "info",
                    "QQ 测试连接复用了当前运行中的正式实例结果。",
                    source="javis.channels.qq.test",
                )
                return {
                    "success": True,
                    "state": "success",
                    "message": "当前 QQ 渠道已在运行，连接状态正常。",
                    "tested_at": tested_at,
                    "checks": checks,
                    "runtime": runtime,
                }

            checks.append(
                {
                    "key": "live_probe",
                    "label": "实际连接",
                    "status": "warning",
                    "message": "检测到正式 QQ 渠道正在运行。为避免打断正式实例，本次未对当前表单参数发起真实握手测试。",
                }
            )
            self._record_log(
                "warning",
                "QQ 测试连接跳过了真实握手，因为正式实例正在运行。",
                source="javis.channels.qq.test",
            )
            return {
                "success": False,
                "state": "warning",
                "message": "当前 QQ 渠道正在运行，本次只完成了基础诊断。",
                "tested_at": tested_at,
                "checks": checks,
                "runtime": runtime,
            }

        self._record_log("info", "开始执行 QQ 真实握手测试。", source="javis.channels.qq.test")
        probe_success, probe_message = await self._probe_qq_connection(normalized)
        checks.append(
            {
                "key": "live_probe",
                "label": "实际连接",
                "status": "success" if probe_success else "error",
                "message": probe_message,
            }
        )
        self._record_log(
            "info" if probe_success else "error",
            probe_message,
            source="javis.channels.qq.test",
        )
        return {
            "success": probe_success,
            "state": "success" if probe_success else "error",
            "message": probe_message,
            "tested_at": tested_at,
            "checks": checks,
            "runtime": runtime,
        }

    async def _probe_qq_connection(self, config: dict[str, Any], timeout_seconds: int = 8) -> tuple[bool, str]:
        try:
            import botpy
        except Exception as exc:
            return False, f"QQ SDK 导入失败：{exc}"

        intents = botpy.Intents(public_messages=True, direct_message=True)
        ready_event = asyncio.Event()

        class ProbeClient(botpy.Client):
            def __init__(self):
                super().__init__(intents=intents)

            async def on_ready(self):
                ready_event.set()

        client = ProbeClient()

        async def run_client() -> None:
            await client.start(appid=config["app_id"], secret=config["secret"])

        client_task = asyncio.create_task(run_client(), name="javis-qq-probe-client")
        ready_task = asyncio.create_task(ready_event.wait(), name="javis-qq-probe-ready")

        try:
            done, _pending = await asyncio.wait(
                {client_task, ready_task},
                timeout=timeout_seconds,
                return_when=asyncio.FIRST_COMPLETED,
            )

            if ready_task in done and ready_event.is_set():
                return True, "QQ 连接握手成功。"

            if client_task in done:
                exc = client_task.exception()
                if exc is not None:
                    return False, f"QQ 连接失败：{exc}"
                return False, "QQ 连接已结束，但没有进入 ready 状态。"

            return False, f"QQ 连接超时，{timeout_seconds} 秒内未完成握手。"
        finally:
            ready_task.cancel()
            try:
                await ready_task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass

            try:
                await client.close()
            except Exception:
                pass

            if not client_task.done():
                client_task.cancel()
            try:
                await client_task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass

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
