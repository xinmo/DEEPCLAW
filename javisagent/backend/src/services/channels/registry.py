from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from src.models.channels import ChannelConfig

QQ_CHANNEL_NAME = "qq"
QQ_CHANNEL_LABEL = "QQ"
DEFAULT_QQ_CONFIG = {
    "app_id": "",
    "secret": "",
    "allow_from": [],
}


def _serialize_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _normalize_allow_from(values: list[Any] | str | None) -> list[str]:
    if values is None:
        return []

    items: list[str] = []
    raw_values: list[Any]
    if isinstance(values, str):
        raw_values = values.replace(",", "\n").splitlines()
    else:
        raw_values = list(values)

    for item in raw_values:
        text = str(item).strip()
        if not text:
            continue
        if text not in items:
            items.append(text)
    return items


def normalize_qq_config(raw_config: dict[str, Any] | None) -> dict[str, Any]:
    payload = dict(DEFAULT_QQ_CONFIG)
    if raw_config:
        payload.update(
            {
                "app_id": str(raw_config.get("app_id", "") or "").strip(),
                "secret": str(raw_config.get("secret", "") or "").strip(),
                "allow_from": _normalize_allow_from(raw_config.get("allow_from")),
            }
        )
    payload["allow_from"] = _normalize_allow_from(payload.get("allow_from"))
    return payload


def validate_qq_config(enabled: bool, config: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if enabled and not str(config.get("app_id", "")).strip():
        errors.append("启用 QQ 渠道前需要填写 App ID。")
    if enabled and not str(config.get("secret", "")).strip():
        errors.append("启用 QQ 渠道前需要填写 App Secret。")
    return errors


def is_qq_configured(config: dict[str, Any]) -> bool:
    return bool(str(config.get("app_id", "")).strip() and str(config.get("secret", "")).strip())


def get_or_create_channel_config(db: Session, name: str) -> ChannelConfig:
    record = db.query(ChannelConfig).filter_by(name=name).first()
    if record is not None:
        return record

    record = ChannelConfig(name=name, enabled=False, config_data=dict(DEFAULT_QQ_CONFIG))
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_qq_channel_config(db: Session) -> dict[str, Any]:
    record = get_or_create_channel_config(db, QQ_CHANNEL_NAME)
    config = normalize_qq_config(record.config_data)
    return {
        "name": QQ_CHANNEL_NAME,
        "label": QQ_CHANNEL_LABEL,
        "enabled": bool(record.enabled),
        "configured": is_qq_configured(config),
        "config": {
            "enabled": bool(record.enabled),
            "app_id": config["app_id"],
            "secret": config["secret"],
            "allow_from": config["allow_from"],
        },
        "validation_errors": validate_qq_config(bool(record.enabled), config),
        "created_at": _serialize_datetime(record.created_at),
        "updated_at": _serialize_datetime(record.updated_at),
    }


def save_qq_channel_config(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    record = get_or_create_channel_config(db, QQ_CHANNEL_NAME)
    normalized = normalize_qq_config(payload)
    record.enabled = bool(payload.get("enabled", False))
    record.config_data = normalized
    db.add(record)
    db.commit()
    db.refresh(record)
    return get_qq_channel_config(db)


def list_channel_summaries(
    db: Session,
    runtime_statuses: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    qq_config = get_qq_channel_config(db)
    runtime = (runtime_statuses or {}).get(QQ_CHANNEL_NAME, {})
    return [
        {
            "name": QQ_CHANNEL_NAME,
            "label": QQ_CHANNEL_LABEL,
            "enabled": qq_config["enabled"],
            "configured": qq_config["configured"],
            "status": str(runtime.get("state") or "stopped"),
            "status_message": str(
                runtime.get("message")
                or (
                    "QQ 渠道已配置完成。"
                    if qq_config["configured"]
                    else "请先填写 App ID 和 App Secret。"
                )
            ),
            "updated_at": qq_config["updated_at"],
        }
    ]
