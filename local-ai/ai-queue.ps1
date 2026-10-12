# Work through local-ai\queue.txt, one task per line, each on its own branch.
#   local-ai\ai-queue            run every waiting task
#   local-ai\ai-queue -Pr        also open a draft PR for each task that passes, and then run
#                                the GitHub issues labelled local-ai that Claude posted (needs pr = on)
#
# queue.txt format, one task per line (blank lines and # comments are ignored):
#   game | ITEM-ID | files (comma separated, or blank) | what to do
#   lighthouse | QI-52 | index.html | Add <script src="../../shared/night-mode.js"></script> right after the site-settings.js line.
# Finished lines move to queue-done.txt with PASSED or FAILED in front.
# When queue.txt runs out, everything in queue-next.txt (same format) is moved into it and the run carries on.
#
# Built to run unattended for days:
#   - waits (up to 6 hours) for Ollama instead of failing every task while it is down
#   - stops after 10 failures in a row, since that means something is broken, not one bad task
#   - every sync_every tasks (config.txt, default 50) and at the end: pushes the finished
#     local-ai/... branches to GitHub (push = on; never main) and catches your own main up with
#     GitHub when that is a plain fast-forward
param([switch]$Pr)
$aiDir = $PSScriptRoot
$root = Split-Path -Parent $aiDir
$queue = Join-Path $aiDir "queue.txt"
$done = Join-Path $aiDir "queue-done.txt"
$config = Join-Path $aiDir "config.txt"
if (-not (Test-Path $queue)) { Set-Content -Encoding utf8 $queue "# game | ITEM-ID | files | what to do   (see ai-queue.ps1)" }

function Setting($name, $default) {
    if (Test-Path $config) {
        $m = Select-String -Path $config -Pattern "^\s*$name\s*=\s*(\S+)\s*$" | Select-Object -First 1
        if ($m) { return $m.Matches[0].Groups[1].Value }
    }
    return $default
}

function Wait-ForOllama {
    for ($i = 0; $i -lt 360; $i++) {
        try { Invoke-RestMethod http://127.0.0.1:11434/api/version -TimeoutSec 10 | Out-Null; return $true } catch {}
        if ($i -eq 0) { Write-Host "Ollama is not answering. Waiting for it (checking every minute, up to 6 hours)..." -ForegroundColor Yellow }
        Start-Sleep 60
    }
    return $false
}

function Sync-WithGitHub {
    Write-Host ""
    Write-Host "--- Syncing with GitHub ---"
    git -C $root fetch -q origin
    if ($LASTEXITCODE -ne 0) { Write-Host "  Could not reach GitHub; will try again at the next sync."; return }
    # 1. Your own main: catch up only when it is a plain fast-forward and nothing is uncommitted.
    $branchNow = git -C $root rev-parse --abbrev-ref HEAD
    $behind = [int](git -C $root rev-list --count "HEAD..origin/$branchNow" 2>$null)
    $ahead = [int](git -C $root rev-list --count "origin/$branchNow..HEAD" 2>$null)
    if ($behind -gt 0) {
        $dirty = git -C $root status --porcelain --untracked-files=no
        if (-not $dirty -and $ahead -eq 0) {
            git -C $root merge -q --ff-only "origin/$branchNow"
            Write-Host "  Pulled $behind new commit(s) into your $branchNow."
        }
        else { Write-Host "  Your $branchNow is $ahead ahead and $behind behind GitHub: not pulled automatically (needs a merge)." }
    }
    # 2. Push finished local-ai branches (only ever local-ai/..., never main).
    if ((Setting "push" "off") -ne "on") { Write-Host "  Pushing is off (push = off in config.txt)."; return }
    $pushed = 0
    foreach ($b in @(git -C $root for-each-ref --format="%(refname:short)" refs/heads/local-ai/)) {
        if ($b -notlike "local-ai/*") { continue }
        $remote = git -C $root rev-parse -q --verify "refs/remotes/origin/$b" 2>$null
        $local = git -C $root rev-parse $b
        if ($remote -eq $local) { continue }
        git -C $root push -q origin "${b}:${b}" 2>$null
        if ($LASTEXITCODE -eq 0) { $pushed++ } else { Write-Host "  Could not push $b" }
    }
    Write-Host "  Pushed $pushed branch(es) to GitHub."
}

$syncEvery = [int](Setting "sync_every" "50")
$results = @()
$sinceSync = 0
$failStreak = 0
while ($true) {
    $lines = @(Get-Content $queue -Encoding utf8)
    $index = -1
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i].Trim() -and -not $lines[$i].Trim().StartsWith("#")) { $index = $i; break }
    }
    if ($index -lt 0) {
        # queue.txt is empty: carry on with the second list, if it has anything in it
        $nextFile = Join-Path $aiDir "queue-next.txt"
        $nextTasks = @()
        if (Test-Path $nextFile) {
            $nextTasks = @(Get-Content $nextFile -Encoding utf8 | Where-Object { $_.Trim() })
        }
        if (@($nextTasks | Where-Object { -not $_.Trim().StartsWith("#") }).Count -eq 0) { break }
        Set-Content -Encoding utf8 $queue (@($lines[0], "# Moved in from queue-next.txt on $(Get-Date -Format 'yyyy-MM-dd HH:mm')") + $nextTasks)
        Set-Content -Encoding utf8 $nextFile "# Second list: used when queue.txt runs out (same format as queue.txt)"
        Add-Content -Encoding utf8 $done "SWITCHED  $(Get-Date -Format 'yyyy-MM-dd HH:mm')  queue.txt was empty: moved $($nextTasks.Count) lines in from queue-next.txt"
        Write-Host ""
        Write-Host "queue.txt is done: carrying on with queue-next.txt ($($nextTasks.Count) lines)." -ForegroundColor Cyan
        continue
    }
    if (-not (Wait-ForOllama)) { Write-Host "Ollama never came back. Stopping; the remaining tasks are still in queue.txt." -ForegroundColor Red; break }

    $line = $lines[$index]
    $parts = $line -split '\|', 4 | ForEach-Object { $_.Trim() }
    # take the line off the queue first, so a crash never repeats it forever
    $rest = @()
    for ($i = 0; $i -lt $lines.Count; $i++) { if ($i -ne $index) { $rest += $lines[$i] } }
    Set-Content -Encoding utf8 $queue $rest

    if ($parts.Count -lt 4 -or -not $parts[0] -or -not $parts[1] -or -not $parts[3]) {
        Add-Content -Encoding utf8 $done "BAD LINE  $line"
        $results += "BAD LINE  $line"
        continue
    }
    $files = @($parts[2] -split ',' | ForEach-Object { $_.Trim() } | Where-Object { $_ })
    Write-Host ""
    Write-Host "=== $(Get-Date -Format 'ddd HH:mm')  $($parts[1]) in $($parts[0]): $($parts[3])"
    $aiArgs = @{ Game = $parts[0]; Item = $parts[1]; Task = $parts[3]; Files = $files }
    if ($Pr) { $aiArgs.Pr = $true }
    & (Join-Path $aiDir "ai.ps1") @aiArgs
    $status = if ($LASTEXITCODE -eq 0) { "PASSED" } else { "FAILED" }
    Add-Content -Encoding utf8 $done "$status  $(Get-Date -Format 'yyyy-MM-dd HH:mm')  $line"
    $results += "$status  $line"

    $failStreak = if ($status -eq "FAILED") { $failStreak + 1 } else { 0 }
    if ($failStreak -ge 10) {
        Write-Host "10 tasks failed in a row, so something is probably broken (Ollama, disk, git). Stopping; the rest stay in queue.txt." -ForegroundColor Red
        break
    }
    $sinceSync++
    if ($sinceSync -ge $syncEvery) { Sync-WithGitHub; $sinceSync = 0 }
}

# --- Then tasks Claude posted as GitHub issues labelled local-ai -----------
# Each is tried once: it gets the label local-ai-tried so the next run skips it.
$prOn = (Setting "pr" "off") -eq "on"
if ($Pr -and $prOn -and (Get-Command gh -ErrorAction SilentlyContinue)) {
    gh label create local-ai-tried --color BFD4F2 --description "The local AI has run this task" 2>$null | Out-Null
    $issues = @(gh issue list --label local-ai --state open --search "-label:local-ai-tried" --limit 50 --json number,title,body | ConvertFrom-Json)
    foreach ($issue in ($issues | Sort-Object number)) {
        $fields = @{}
        $key = $null
        foreach ($l in ($issue.body -split "`r?`n")) {
            if ($l -match '^\s*(game|item|files|task)\s*:\s*(.*)$') { $key = $Matches[1]; $fields[$key] = $Matches[2].Trim() }
            elseif ($key -eq "task" -and $l.Trim()) { $fields.task += " " + $l.Trim() }
        }
        gh issue edit $issue.number --add-label local-ai-tried | Out-Null
        if (-not $fields.game -or -not $fields.item -or -not $fields.task) {
            gh issue comment $issue.number --body "The local AI skipped this: the body needs game:, item: and task: lines (see local-ai/FOR-CLAUDE.md)." | Out-Null
            $results += "BAD ISSUE #$($issue.number) $($issue.title)"
            continue
        }
        $files = @("$($fields.files)" -split ',' | ForEach-Object { $_.Trim() } | Where-Object { $_ })
        Write-Host ""
        Write-Host "=== Issue #$($issue.number): $($issue.title)"
        & (Join-Path $aiDir "ai.ps1") -Game $fields.game -Item $fields.item -Task $fields.task -Files $files -Pr -Issue $issue.number
        $status = if ($LASTEXITCODE -eq 0) { "PASSED" } else { "FAILED" }
        Add-Content -Encoding utf8 $done "$status  $(Get-Date -Format 'yyyy-MM-dd HH:mm')  issue #$($issue.number) $($issue.title)"
        $results += "$status  issue #$($issue.number) $($issue.title)"
    }
}

Sync-WithGitHub
$passed = @($results | Where-Object { $_ -like "PASSED*" }).Count
Write-Host ""
Write-Host "Queue finished: $passed passed out of $($results.Count)."
$results | Where-Object { $_ -notlike "PASSED*" } | ForEach-Object { Write-Host "  $_" }
Write-Host "Full list: local-ai\queue-done.txt   Reports: local-ai\.history\reports"
