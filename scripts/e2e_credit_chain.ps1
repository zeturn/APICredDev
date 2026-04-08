$ErrorActionPreference = 'Stop'
$base = 'http://127.0.0.1:8103'
$email = "e2e_$(Get-Date -Format 'yyyyMMddHHmmss')@example.com"
$pwd = 'E2ePass!123456'
$basaltUserId = if ($env:E2E_BASALT_USER_ID) { $env:E2E_BASALT_USER_ID } else { '2' }
$basaltTenantId = if ($env:E2E_BASALT_TENANT_ID) { $env:E2E_BASALT_TENANT_ID } else { '4' }

Write-Host "[1] register/login user: $email"
try {
  Invoke-RestMethod -Method Post -Uri "$base/v1/auth/register" -ContentType 'application/json' -Body (@{email=$email;password=$pwd} | ConvertTo-Json) | Out-Null
} catch {
  Write-Host '[register skipped] maybe exists'
}
$login = Invoke-RestMethod -Method Post -Uri "$base/v1/auth/login" -ContentType 'application/json' -Body (@{email=$email;password=$pwd} | ConvertTo-Json)
$jwt = $login.access_token
$authHeader = @{ Authorization = "Bearer $jwt" }
$me = Invoke-RestMethod -Method Get -Uri "$base/v1/auth/me" -Headers $authHeader
$userId = $me.id
Write-Host "user_id=$userId"

Write-Host "[2] bind APICred user to Basalt user($basaltUserId/tenant $basaltTenantId)"
$sqlBind = "UPDATE users SET basalt_user_id='$basaltUserId', basalt_tenant_id='$basaltTenantId' WHERE id='$userId';"
docker exec apicred-postgres-1 psql -U apicred -d apicred -c "$sqlBind" | Out-Host

Write-Host '[3] verify wallet endpoints and permissions'
$walletBefore = Invoke-RestMethod -Method Get -Uri "$base/v1/billing/wallet" -Headers $authHeader
$basaltBefore = Invoke-RestMethod -Method Get -Uri "$base/v1/basalt/wallet/balance?currency=CREDIT&limit=20" -Headers $authHeader

Write-Host '[4] create recharge code in APICred DB and redeem'
$redeemCode = "E2E-CREDIT-$(Get-Date -Format 'yyyyMMddHHmmss')"
$hash = [System.BitConverter]::ToString([System.Security.Cryptography.SHA256]::Create().ComputeHash([System.Text.Encoding]::UTF8.GetBytes($redeemCode))).Replace('-','').ToLowerInvariant()
$codeId = [guid]::NewGuid().ToString()
$sqlCode = "INSERT INTO recharge_codes (id, code_hash, amount_credits, status, created_at) VALUES ('$codeId', '$hash', 30.000000, 'unused', NOW());"
docker exec apicred-postgres-1 psql -U apicred -d apicred -c "$sqlCode" | Out-Host
$redeemResp = Invoke-RestMethod -Method Post -Uri "$base/v1/billing/redeem" -Headers $authHeader -ContentType 'application/json' -Body (@{code=$redeemCode} | ConvertTo-Json)

Write-Host '[5] create API token and call chat/completions once'
$tokenResp = Invoke-RestMethod -Method Post -Uri "$base/v1/tokens" -Headers $authHeader -ContentType 'application/json' -Body (@{name='e2e-token';scopes=@('llm')} | ConvertTo-Json)
$apiToken = $tokenResp.token
$models = Invoke-RestMethod -Method Get -Uri "$base/v1/models" -Headers $authHeader
if (-not $models -or $models.Count -eq 0) { throw 'no models available' }
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

Write-Host '[6] collect after snapshots'
$walletAfter = Invoke-RestMethod -Method Get -Uri "$base/v1/billing/wallet" -Headers $authHeader
$ledgerAfter = Invoke-RestMethod -Method Get -Uri "$base/v1/billing/ledger" -Headers $authHeader
$basaltAfter = Invoke-RestMethod -Method Get -Uri "$base/v1/basalt/wallet/balance?currency=CREDIT&limit=20" -Headers $authHeader

$result = [ordered]@{
  user = [ordered]@{ id=$userId; email=$email; basalt_user_id=$basaltUserId; basalt_tenant_id=$basaltTenantId }
  wallet_before = $walletBefore
  redeem_response = $redeemResp
  wallet_after = $walletAfter
  basalt_before = $basaltBefore
  basalt_after = $basaltAfter
  model_used = $modelName
  chat_status = $chatStatus
  ledger_top5 = @($ledgerAfter | Select-Object -First 5)
}
$result | ConvertTo-Json -Depth 12
