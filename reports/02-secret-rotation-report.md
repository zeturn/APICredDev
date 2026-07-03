# 02 Secret Rotation Report

## Scope

为 provider credential 加密引入显式密钥与版本化轮换机制，新增 CLI 轮换命令与测试。

## Implemented

- 新增配置：
  - `APICRED_ENCRYPTION_KEY`
  - `APICRED_ENCRYPTION_KEY_ID`
  - `APICRED_PREVIOUS_ENCRYPTION_KEYS`
- 加密行为：
  - 新写入使用 `<key_id>:<fernet-token>`（默认 `v3:`）。
  - 读取时按前缀选择 key。
  - `v2:` 旧格式仍保留 legacy fallback 解密兼容。
- 新增轮换服务与 CLI：
  - `python -m app.cli secrets rotate-provider-credentials --dry-run`
  - `python -m app.cli secrets rotate-provider-credentials`
- 轮换报告字段仅输出：
  - `credential_id`
  - `old_version`
  - `new_version`
  - `status`
- 轮换幂等：当前版本密文不重复轮换。

## Tests

- 新增：`backend/tests/test_secret_encryption_rotation.py`
- 覆盖：
  - current key encrypt/decrypt
  - previous key decrypt
  - legacy `v2` fallback
  - dry-run / actual / idempotency
  - bad key fails safely
  - report 不泄露 secret 明文

## Result

- `explicit_encryption_key_ready = true`
- `rotation_command_ready = true`
- `legacy_decrypt_supported = true`
- `secret_not_leaked = true`
