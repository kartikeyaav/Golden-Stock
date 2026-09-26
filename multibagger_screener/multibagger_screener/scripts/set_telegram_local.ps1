# set_telegram_local.ps1 - let the LAPTOP send Telegram messages.
#
# Why: the 3:10 PM breakout check (scripts/breakout_watch.py, Task Scheduler
# job MultibaggerBreakoutWatch) has to run on the laptop - GitHub's scheduler
# delivered this repository's cron runs a median 95 minutes late, and a 15:10
# decision that arrives at 16:45 is worthless. The bot token and chat id live
# only in the GitHub repository's secrets, which cannot be read back, so the
# laptop needs its own copy: the SAME two values you set as the repository
# secrets TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID.
#
# Usage:  powershell -ExecutionPolicy Bypass -File scripts\set_telegram_local.ps1
#
# Both values are read as secure strings (not echoed, not in shell history),
# TESTED with one real message before anything is saved, then stored as
# User-scope environment variables - the scheduled tasks run as this user, so
# they pick them up from their next run. Nothing is written to the repository.

function Read-Secret([string]$prompt) {
    $sec = Read-Host $prompt -AsSecureString
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec)
    try {
        return ([Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr) -replace '\s', '')
    } finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    }
}

$tok = Read-Secret "Paste the Telegram BOT TOKEN (same as the GitHub secret TELEGRAM_BOT_TOKEN)"
if ($tok -notmatch '^\d+:[A-Za-z0-9_-]{30,}$') {
    Write-Host "That does not look like a bot token (expected digits, a colon, then ~35 characters). Nothing was saved."
    exit 1
}
$chat = Read-Secret "Paste the CHAT ID (same as the GitHub secret TELEGRAM_CHAT_ID)"
if ($chat -notmatch '^-?\d+$') {
    Write-Host "A chat id is a number (it may start with a minus sign). Nothing was saved."
    exit 1
}

Write-Host "Sending one test message..."
try {
    $body = @{ chat_id = $chat; text = "GOLDEN STOCK - the laptop can now send the 3:10 PM breakout check." }
    $r = Invoke-RestMethod -Method Post -Uri "https://api.telegram.org/bot$tok/sendMessage" -Body $body -TimeoutSec 20
    if (-not $r.ok) { throw "Telegram answered ok=false" }
} catch {
    $msg = ($_.Exception.Message).Replace($tok, '<token>')
    Write-Host "Telegram rejected these values - nothing was saved."
    Write-Host "  $msg"
    exit 1
}

[Environment]::SetEnvironmentVariable('TELEGRAM_BOT_TOKEN', $tok, 'User')
[Environment]::SetEnvironmentVariable('TELEGRAM_CHAT_ID', $chat, 'User')
$tok = $null
Write-Host "Test message sent and both values saved for $env:USERNAME. The 3:10 PM check sends from its next run."
