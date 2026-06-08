# Mnemosyne end-to-end smoke test.
# Run the server first (uvicorn app.main:app --port 8000), then:  .\smoke_test.ps1
$base = "http://localhost:8000"

function Chat($msg, $session) {
    $body = @{ message = $msg; session_id = $session } | ConvertTo-Json
    Invoke-RestMethod -Uri "$base/chat" -Method Post -ContentType "application/json" -Body $body
}

Write-Host "`n=== 0. Reset memory store (clean run) ===" -ForegroundColor Yellow
Invoke-RestMethod -Uri "$base/reset" -Method Post | Out-Null
Write-Host "Store cleared."

Write-Host "`n=== 1. Session s1: state facts ===" -ForegroundColor Cyan
$r1 = Chat "I live in New York and I prefer short answers" "s1"
Write-Host "Reply:" $r1.reply
Write-Host "New memories:" ($r1.new_memories | ForEach-Object { $_.content })

Write-Host "`n=== 2. Session s2 (new session): recall test ===" -ForegroundColor Cyan
$r2 = Chat "Where do I live?" "s2"
Write-Host "Reply:" $r2.reply
Write-Host "Recalled:" ($r2.recalled | ForEach-Object { $_.content })

Write-Host "`n=== 3. Contradiction: should supersede 'New York' ===" -ForegroundColor Cyan
$r3 = Chat "Actually I just moved to Berlin" "s2"
Write-Host "Reply:" $r3.reply

Write-Host "`n=== 4. All memories (watch for status=superseded) ===" -ForegroundColor Cyan
$mem = Invoke-RestMethod -Uri "$base/memories"
$mem.memories | ForEach-Object {
    Write-Host ("[{0}] ({1}) {2}" -f $_.status, $_.type, $_.content)
}
Write-Host "`nTotal memories:" $mem.count
