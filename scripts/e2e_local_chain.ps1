$ErrorActionPreference = 'Stop'
$base = 'http://127.0.0.1:8103'
$email = "e2elocal_$(Get-Date -Format 'yyyyMMddHHmmss')@example.com"
$pwd = 'E2ePass!123456'

Write-Host "[1] register/login local user: $email"
Invoke-RestMethod -Method Post -Uri "$base/v1/auth/register" -ContentType 'application/json' -Body (@{email=$email;password=$pwd} | ConvertTo-Json) | Out-Null
$login = Invoke-RestMethod -Method Post -Uri "$base/v1/auth/login" -ContentType 'application/json' -Body (@{email=$email;password=$pwd} | ConvertTo-Json)
$jwt = $login.access_token
$authHeader = @{ Authorization = "Bearer $jwt" }
$me = Invoke-RestMethod -Method Get -Uri "$base/v1/auth/me" -Headers $authHeader
$userId = $me.id

$walletBefore = Invoke-RestMethod -Method Get -Uri "$base/v1/billing/wallet" -Headers $authHeader

Write-Host '[2] create recharge code and redeem'
$redeemCode = "E2E-LOCAL-$(Get-Date -Format 'yyyyMMddHHmmss')"
$hash = [System.BitConverter]::ToString([System.Security.Cryptography.SHA256]::Create().ComputeHash([System.Text.Encoding]::UTF8.GetBytes($redeemCode))).Replace('-','').ToLowerInvariant()
$codeId = [guid]::NewGuid().ToString()
$sqlCode = "INSERT INTO recharge_codes (id, code_hash, amount_credits, status, created_at) VALUES ('$codeId', '$hash', 25.000000, 'unused', NOW());"
docker exec apicred-postgres-1 psql -U apicred -d apicred -c "$sqlCode" | Out-Null
$redeemResp = Invoke-RestMethod -Method Post -Uri "$base/v1/billing/redeem" -Headers $authHeader -ContentType 'application/json' -Body (@{code=$redeemCode} | ConvertTo-Json)

Write-Host '[3] create llm token and call chat once'
$tokenResp = Invoke-RestMethod -Method Post -Uri "$base/v1/tokens" -Headers $authHeader -ContentType 'application/json' -Body (@{name='e2e-local-token';scopes=@('llm')} | ConvertTo-Json)
$apiToken = $tokenResp.token
$models = Invoke-RestMethod -Method Get -Uri "$base/v1/models" -Headers $authHeader
$modelName = $models[0].name
$llmHeader = @{ Authorization = "Bearer $apiToken" }
$chatBody = @{ model=$modelName; stream=$false; messages=@(@{role='user';content='reply with: ok'}) } | ConvertTo-Json -Depth 8
$chatStatus = 'unknown'
try {
  $null = Invoke-RestMethod -Method Post -Uri "$base/v1/chat/completions" -Headers $llmHeader -ContentType 'application/json' -Body $chatBody
  $chatStatus = 'success'
} catch {
  $chatStatus = "failed: $($_.Exception.Message)"
}

$walletAfter = Invoke-RestMethod -Method Get -Uri "$base/v1/billing/wallet" -Headers $authHeader
$ledger = Invoke-RestMethod -Method Get -Uri "$base/v1/billing/ledger" -Headers $authHeader

[ordered]@{
  user = [ordered]@{ id=$userId; email=$email }
  wallet_before = $walletBefore
  redeem_response = $redeemResp
  wallet_after = $walletAfter
  model_used = $modelName
  chat_status = $chatStatus
  ledger_top5 = @($ledger | Select-Object -First 5)
} | ConvertTo-Json -Depth 10
