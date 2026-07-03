# 05 Audit Privacy / Retention Report

## Scope

为 `audit_llm_messages` 增加脱敏、哈希模式与保留期清理。

## Implemented

- 新增配置：
  - `AUDIT_STORE_MESSAGE_CONTENT`
  - `AUDIT_REDACTION_ENABLED`
  - `AUDIT_RETENTION_DAYS`
  - `AUDIT_HASH_CONTENT`
- 写入前规则脱敏（第一版）：
  - OpenAI 风格 key (`sk-...`)
  - Anthropic key (`sk-ant-...`)
  - Bearer token
  - GitHub token
  - JWT-like token
  - email
  - card-like number
- Hash mode：
  - `content=null`
  - `content_hash=sha256(redacted_content)`
  - `content_preview`（前 120 字）
- 表结构增强（migration `0004`）：
  - `content_hash`
  - `content_preview`
  - `redaction_applied`
  - `retention_expires_at`
- Retention CLI：
  - `python -m app.cli audit purge-expired --dry-run`
  - `python -m app.cli audit purge-expired`

## Tests

- 新增：`backend/tests/test_audit_redaction_retention.py`
- 覆盖：
  - secret redaction before storage
  - hash mode stores hash not content
  - retention_expires_at set
  - purge dry-run / actual
  - user soft delete

## Result

- `audit_redaction_ready = true`
- `audit_hash_mode_ready = true`
- `audit_retention_ready = true`
