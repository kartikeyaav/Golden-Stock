# set_ai_token.ps1 - store the long-lived Claude subscription token for the
# laptop AI jobs (nightly analyst, weekly committee, theme research).
#
# Why: the interactive `claude` -> /login session expires every couple of
# weeks (the 2026-09-16 outage). `claude setup-token` issues a long-lived
# token instead, and ai_analyst.py / ai_picks.py / theme_intel.py all keep
# CLAUDE_CODE_OAUTH_TOKEN through their env scrub. Same subscription, no API
# credits. The Task Scheduler jobs run as this user, so a User-scope variable
# reaches them from their next run.
#
# Usage:  1. claude setup-token        (browser sign-in; prints the token)
#         2. powershell -ExecutionPolicy Bypass -File scripts\set_ai_token.ps1
#
# The token is read as a secure string: it is not echoed to the screen and
# does not land in shell history. It is TESTED with one tiny headless call
# before it is saved (2026-09-22: a token one character short was saved,
# looked fine, and failed with "401 OAuth access token is invalid").

$sec = Read-Host "Paste the token printed by 'claude setup-token'" -AsSecureString
$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec)
try {
    $tok = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr) -replace '\s', ''
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
}

if (-not $tok.StartsWith('sk-ant-') -or $tok.Length -lt 40) {
    Write-Host "That does not look like a Claude token (expected it to start with sk-ant-). Nothing was saved."
    exit 1
}
Write-Host "Read $($tok.Length) characters. Testing it with one short call..."

# Test in THIS process only. Drop anything that could override the token
# (a host-injected proxy URL, an API key, other CLAUDE_CODE_* settings).
Get-ChildItem env: | Where-Object {
    ($_.Name -like 'ANTHROPIC_*') -or
    ($_.Name -like 'CLAUDE_CODE_*' -and $_.Name -ne 'CLAUDE_CODE_OAUTH_TOKEN')
} | ForEach-Object { Remove-Item "env:$($_.Name)" }
$env:CLAUDE_CODE_OAUTH_TOKEN = $tok

$reply = "Reply with the single word OK." | & claude -p --max-turns 1 2>&1 | Out-String
if ($LASTEXITCODE -ne 0) {
    $msg = $reply.Replace($tok, '<token>').Trim()
    Write-Host "Claude rejected this token - nothing was saved."
    Write-Host "  $msg"
    Write-Host "Run 'claude setup-token' again and copy the WHOLE token (one unbroken line)."
    $tok = $null
    exit 1
}

[Environment]::SetEnvironmentVariable('CLAUDE_CODE_OAUTH_TOKEN', $tok, 'User')
$tok = $null
Write-Host "Token works and is saved for $env:USERNAME. The scheduled AI tasks use it from their next run."
