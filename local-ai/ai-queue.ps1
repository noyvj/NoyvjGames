# Work through local-ai\queue.txt, one task per line, each on its own branch.
#   local-ai\ai-queue            run every waiting task
#   local-ai\ai-queue -Pr        also open a draft PR for each task that passes, and then run
#                                the GitHub issues labelled local-ai that Claude posted (needs pr = on)
#
# queue.txt format, one task per line (blank lines and # comments are ignored):
#   game | ITEM-ID | files (comma separated, or blank) | what to do
#   lighthouse | QI-52 | index.html | Add <script src="../../shared/night-mode.js"></script> right after the site-settings.js line.
# Finished lines move to queue-done.txt with PASSED or FAILED in front.
param([switch]$Pr)
$aiDir = $PSScriptRoot
$queue = Join-Path $aiDir "queue.txt"
$done = Join-Path $aiDir "queue-done.txt"
if (-not (Test-Path $queue)) { Set-Content -Encoding utf8 $queue "# game | ITEM-ID | files | what to do   (see ai-queue.ps1)" }

$results = @()
while ($true) {
    $lines = @(Get-Content $queue -Encoding utf8)
    $index = -1
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i].Trim() -and -not $lines[$i].Trim().StartsWith("#")) { $index = $i; break }
    }
    if ($index -lt 0) { break }
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
    Write-Host "=== $($parts[1]) in $($parts[0]): $($parts[3])"
    $aiArgs = @{ Game = $parts[0]; Item = $parts[1]; Task = $parts[3]; Files = $files }
    if ($Pr) { $aiArgs.Pr = $true }
    & (Join-Path $aiDir "ai.ps1") @aiArgs
    $status = if ($LASTEXITCODE -eq 0) { "PASSED" } else { "FAILED" }
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm"
    Add-Content -Encoding utf8 $done "$status  $stamp  $line"
    $results += "$status  $line"
}

# --- Then tasks Claude posted as GitHub issues labelled local-ai -----------
# Each is tried once: it gets the label local-ai-tried so the next run skips it.
$config = Join-Path $aiDir "config.txt"
$prOn = (Test-Path $config) -and (Select-String -Path $config -Pattern '^\s*pr\s*=\s*on\s*$' -Quiet)
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

Write-Host ""
Write-Host "Queue finished:"
if ($results.Count -eq 0) { Write-Host "  (nothing was waiting)" }
$results | ForEach-Object { Write-Host "  $_" }
Write-Host "Reports are in local-ai\.history\reports"
