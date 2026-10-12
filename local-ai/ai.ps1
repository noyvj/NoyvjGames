# Run the local AI on one task with no chatting, on its own branch.
#   local-ai\ai lighthouse QI-52 "add the night-mode include to index.html" [-Files index.html] [-Pr]
#
# What happens:
#   1. A separate copy of the repo (a git worktree) is made in ..\bcm206-ai-work\<branch>,
#      on a new branch local-ai/<item>-<time> cut from main. Your own folder is never touched.
#   2. Aider does the task there, running this game's tests and flake8 after every edit.
#   3. Checks: only files inside games/<Game> changed, tests green, flake8 clean.
#   4. Pass: commit on the branch (explicit paths). Fail: nothing committed.
#   5. A report is written to local-ai\.history\reports\<branch>.md
#   6. With -Pr (and pr=on in local-ai\config.txt): push ONLY that branch and open a DRAFT pull
#      request for Claude to review. main is never pushed. The TODO item is never ticked here:
#      whoever merges the PR ticks it.
param(
    [Parameter(Mandatory = $true, Position = 0)][string]$Game,
    [Parameter(Mandatory = $true, Position = 1)][string]$Item,
    [Parameter(Mandatory = $true, Position = 2)][string]$Task,
    [string[]]$Files = @(),
    [switch]$Pr,
    [int]$Issue = 0,
    [string]$Model = "ollama_chat/devstral-small-2:24b",
    [string]$Base = "main",
    [int]$TimeoutMinutes = 90,
    # A chain is a feature built in steps: step N starts from step N-1's branch instead of main.
    # In queue.txt write the item as chain:NAME:N (for example chain:DR-SOUND:2).
    [string]$Chain = "",
    [int]$Step = 0
)
if ($Item -match '^chain:([A-Za-z0-9-]+):(\d+)$') { $Chain = $Matches[1]; $Step = [int]$Matches[2] }
if ($Chain) { $Item = "$Chain-$Step" }
# "Continue": git prints harmless notes on stderr, which "Stop" would turn into crashes in
# Windows PowerShell 5.1. Every step checks its own result ($LASTEXITCODE / Fail) instead.
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
$aiDir = Join-Path $root "local-ai"
$reports = Join-Path $aiDir ".history\reports"
New-Item -ItemType Directory -Force $reports | Out-Null
$maxTokens = 17000   # biggest single file the model can hold next to the rules (see README)

function Fail($msg) { Write-Host "STOPPED: $msg" -ForegroundColor Red; exit 1 }

# --- Preconditions -------------------------------------------------------
if (-not (Test-Path (Join-Path $root "games\$Game"))) { Fail "no game folder games\$Game" }
if ($Item -notmatch '^[A-Za-z0-9-]+$') { Fail "item id '$Item' should look like QI-52" }
try { Invoke-RestMethod http://127.0.0.1:11434/api/version | Out-Null }
catch { Fail "Ollama is not running. Start it from the Start menu." }
foreach ($f in $Files) {
    $p = Join-Path $root "games\$Game\$f"
    if (-not (Test-Path $p)) { if ($Chain) { continue }; Fail "games\$Game\$f does not exist" }   # a chain step's files may exist only on the previous step's branch
    $tokens = [math]::Round((Get-Item $p).Length / 3.5)
    if ($tokens -gt $maxTokens) { Fail "$f is about $tokens tokens, too big for the local model (limit ~$maxTokens)" }
}
$aider = (Get-Command aider -ErrorAction SilentlyContinue).Source
if (-not $aider) { $aider = Join-Path $HOME ".local\bin\aider.exe" }

# --- Separate working copy on a new branch -------------------------------
$stamp = Get-Date -Format "yyMMdd-HHmmss"
$branch = "local-ai/$Item-$Game-$stamp"
$workRoot = Join-Path (Split-Path -Parent $root) "bcm206-ai-work"
$work = Join-Path $workRoot ($branch -replace '/', '_')
New-Item -ItemType Directory -Force $workRoot | Out-Null
$config = Join-Path $aiDir "config.txt"
$prOn = (Test-Path $config) -and (Select-String -Path $config -Pattern '^\s*pr\s*=\s*on\s*$' -Quiet)

# Start from the newest shared work: fetch what other AIs/sessions pushed to GitHub.
# A PR run starts from origin/main exactly (so the PR shows only this task's change).
# A local run starts from your local main and merges in origin/main on top.
git -C $root fetch -q origin
if ($LASTEXITCODE -ne 0) { Write-Host "Warning: could not fetch from GitHub (offline?). Using local $Base only." -ForegroundColor Yellow }
$remoteBase = "origin/$Base"
$haveRemote = ($null -ne (git -C $root rev-parse -q --verify $remoteBase 2>$null))
$start = if ($Pr -and $prOn -and $haveRemote) { $remoteBase } else { $Base }
if ($Chain -and $Step -gt 1) {
    $prev = @(git -C $root for-each-ref --sort=-committerdate --format="%(refname:short)" "refs/heads/local-ai/$Chain-$($Step - 1)-*")
    if ($prev.Count -eq 0 -or -not $prev[0]) { Fail "step $($Step - 1) of $Chain has not passed, so step $Step cannot start" }
    $start = $prev[0]
}
git -C $root worktree add -q -b $branch $work $start
if ($LASTEXITCODE -ne 0) { Fail "could not create the working copy" }
if ($start -eq $Base -and $haveRemote -and -not ($Chain -and $Step -gt 1)) {
    git -C $work merge -q --no-edit $remoteBase 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) {
        git -C $work merge --abort 2>$null | Out-Null
        git -C $root worktree remove --force $work
        git -C $root branch -q -D $branch
        Fail "your local $Base and GitHub's $Base conflict; sort that out first (nothing was changed)"
    }
}
$behind = [int](git -C $root rev-list --count "$Base..$remoteBase" 2>$null)
if ($behind -gt 0) { Write-Host "Note: your own folder's $Base is $behind commit(s) behind GitHub. The AI used the newer code; run 'git pull' in your folder when convenient." }
$gameDir = Join-Path $work "games\$Game"
$report = Join-Path $reports (($branch -replace '/', '_') + ".md")

$itemText = python (Join-Path $aiDir "todo_item.py") show $Item 2>$null
if ($LASTEXITCODE -ne 0) { $itemText = "(not a TODO item id; free task)" }
$taskFile = Join-Path $work ".aider-task.md"
@"
# Task for the local AI

Game folder: games/$Game
TODO item: $Item
$($itemText -join "`n")

## What to do now
$Task

Do only this. Change only files in games/$Game. Follow RULES.md.
"@ | Set-Content -Encoding utf8 $taskFile

# --- Run Aider with no chatting -----------------------------------------
$env:OLLAMA_API_BASE = "http://127.0.0.1:11434"
$readArgs = @("--read", (Join-Path $aiDir "RULES.md"), "--read", $taskFile)
if (Test-Path (Join-Path $gameDir "CLAUDE.md")) { $readArgs += @("--read", (Join-Path $gameDir "CLAUDE.md")) }
$fileArgs = @(); foreach ($f in $Files) { $fileArgs += @("--file", $f) }
$log = Join-Path $reports (($branch -replace '/', '_') + ".log")
$started = Get-Date
Write-Host "Working on $Item in $Game (branch $branch). This takes several minutes..."

$aiderArgs = @("--model", $Model,
    "--model-settings-file", (Join-Path $aiDir "aider.model.settings.yml"),
    "--subtree-only", "--map-tokens", "1024",
    "--no-auto-commits", "--no-dirty-commits", "--no-gitignore",
    "--test-cmd", "python ../../scripts/generate-pc-pages.py >NUL && python -m pytest -q -x --tb=line -p no:warnings", "--auto-test",
    "--lint-cmd", "python: python -m flake8 --select=E9,F63,F7,F82", "--auto-lint",   # only real errors here: layout is fixed automatically afterwards, so the model keeps its retries for failing tests
    "--yes-always", "--no-pretty", "--no-stream", "--analytics-disable", "--no-check-update", "--timeout", "1800",   # a big multi-file request can take a long time on this laptop: wait up to 30 min per reply
    "--chat-history-file", $log, "--input-history-file", "NUL") + $readArgs + $fileArgs +
    @("--message", "Do the task in .aider-task.md now. Make the edits, keep them small.")

# Run Aider as a background job so a stuck run can be stopped after $TimeoutMinutes
# instead of blocking the whole queue for days.
$job = Start-Job -ScriptBlock {
    param($dir, $exe, $argList, $apiBase)
    $env:OLLAMA_API_BASE = $apiBase
    Set-Location $dir
    & $exe @argList *>&1 | Out-Null
} -ArgumentList $gameDir, $aider, $aiderArgs, $env:OLLAMA_API_BASE
$timedOut = -not (Wait-Job $job -Timeout ($TimeoutMinutes * 60))
if ($timedOut) {
    # aider.exe is a launcher with a python child: end the whole tree, then the job
    Get-CimInstance Win32_Process -Filter "Name='aider.exe'" | Where-Object { $_.CreationDate -ge $started } |
        ForEach-Object { taskkill /T /F /PID $_.ProcessId 2>$null | Out-Null }
    Stop-Job $job
}
Remove-Job $job -Force
Remove-Item $taskFile -ErrorAction SilentlyContinue

# pc.html is generated from index.html and must never be hand-edited (the first trial run's
# only failure). Regenerate it here; the generator only rewrites pages whose content changed.
if (Test-Path (Join-Path $gameDir "pc-config.json")) {
    Push-Location $work
    python scripts/generate-pc-pages.py | Out-Null
    Pop-Location
}

# --- Check the result ----------------------------------------------------
$changed = @(git -C $work status --porcelain --untracked-files=all | ForEach-Object { $_.Substring(3).Trim('"') } |
    Where-Object { $_ -notlike ".aider*" })
$outside = @($changed | Where-Object { $_ -notlike "games/$Game/*" })
$inside = @($changed | Where-Object { $_ -like "games/$Game/*" })
$problems = @()
if ($timedOut) { $problems += "timed out after $TimeoutMinutes minutes" }
if ($inside.Count -eq 0) { $problems += "the AI made no changes in games/$Game" }
if ($outside.Count -gt 0) { $problems += "it changed files outside games/${Game}: $($outside -join ', ')" }

$py = @($inside | Where-Object { $_ -like "*.py" } | ForEach-Object { Join-Path $work $_ } | Where-Object { Test-Path $_ })
# Layout (spacing, blank lines, trailing spaces) is fixed mechanically rather than failing correct work over it.
if ($py.Count -gt 0) { python -m autopep8 --in-place --select=E1,E2,E3,W2,W3 @py 2>$null | Out-Null }
# New test files the AI wrote (tests/test_ai_*.py) also lose unused imports and variables.
$newTests = @($inside | Where-Object { $_ -match "^games/$([regex]::Escape($Game))/tests/test_ai_[^/]+\.py$" })
$testOnly = ($inside.Count -gt 0 -and $newTests.Count -eq $inside.Count)
if ($newTests.Count -gt 0) {
    $newPaths = @($newTests | ForEach-Object { Join-Path $work $_ })
    python -m autoflake --in-place --remove-all-unused-imports --remove-unused-variables @newPaths 2>$null | Out-Null
}

Push-Location $gameDir
$testOut = (python -m pytest -q 2>&1 | Out-String)
$testsOk = ($LASTEXITCODE -eq 0)
$salvageNote = ""
# A test-writing task with some wrong guesses: keep its passing tests rather than throw the whole file away.
if (-not $testsOk -and $testOnly) {
    $rels = @($newTests | ForEach-Object { $_.Substring("games/$Game/".Length) })
    $salvageNote = ((python (Join-Path $aiDir "salvage_tests.py") $gameDir @rels 2>&1) -join " ")
    if ($LASTEXITCODE -eq 0) {
        $testOut = (python -m pytest -q 2>&1 | Out-String)
        $testsOk = ($LASTEXITCODE -eq 0)
    }
}
Pop-Location
if (-not $testsOk) { $problems += "tests failed" }
$testLine = ($testOut.Trim() -split "`n")[-1]

$flakeOut = ""
if ($py.Count -gt 0) {
    $flakeOut = (python -m flake8 --extend-ignore=E501 @py 2>&1 | Out-String)
    if ($LASTEXITCODE -ne 0) { $problems += "flake8 found problems" }
}
$diffStat = ($changed | ForEach-Object { "- $_" }) -join "`n"
# keep the change itself in the report: a failed run's working copy is deleted below
git -C $work add -N -- @inside 2>$null | Out-Null
$diffText = (git -C $work diff -- @inside 2>&1 | Select-Object -First 300 | Out-String)
$minutes = [math]::Round(((Get-Date) - $started).TotalMinutes, 1)

# --- Commit or not -------------------------------------------------------
$ok = ($problems.Count -eq 0)
if ($ok) {
    git -C $work add -- @inside
    # The message goes through a file: Windows PowerShell mangles double quotes in native arguments,
    # which stripped them from messages and broke the commit outright when a task quoted code.
    $msgFile = Join-Path $work ".aider-commit-msg.txt"
    [IO.File]::WriteAllText($msgFile, "local-ai: ${Item}: $Task`n`nMade by the local model ($Model), not yet reviewed by Claude.`n", (New-Object System.Text.UTF8Encoding $false))
    git -C $work commit -q -F $msgFile -- @inside
    Remove-Item $msgFile -ErrorAction SilentlyContinue
    if ($LASTEXITCODE -ne 0) { $ok = $false; $problems += "git commit failed" }
}

@"
# $(if ($ok) { "PASSED" } else { "FAILED" }): $Item in $Game

- Branch: ``$branch``
- Task: $Task
- Took: $minutes minutes
- Tests: $testLine
$(if ($salvageNote) { "- Salvage: $salvageNote" })
$(if ($problems.Count) { "- Problems: " + ($problems -join "; ") })

## Changed files
$diffStat
$(if ($flakeOut) { "## flake8`n$flakeOut" })
$(if (-not $ok -and $diffText.Trim()) { "## The change it tried (first 300 lines)`n~~~diff`n$diffText~~~" })
$(if (-not $ok -and $testsOk -eq $false) { "## Test output (end)`n~~~`n" + (($testOut -split "`n" | Select-Object -Last 40) -join "`n") + "`n~~~" })
Full AI conversation: $log
"@ | Set-Content -Encoding utf8 $report

if (-not $ok) {
    if ($Issue -gt 0 -and $prOn) {
        gh issue comment $Issue --body ("The local AI could not finish this.`n`n" + (Get-Content $report -Raw)) | Out-Null
    }
    # The report keeps the attempted change; drop the working copy and its empty branch so days of
    # failures never pile up on disk.
    git -C $root worktree remove --force $work 2>$null | Out-Null
    git -C $root branch -q -D $branch 2>$null | Out-Null
    Write-Host "FAILED ($($problems -join '; ')). Nothing committed. Report: $report" -ForegroundColor Yellow
    exit 1
}

# --- Optional draft PR ---------------------------------------------------
if ($Pr -and -not $prOn) { Write-Host "Not opening a PR: pull requests are switched off in local-ai\config.txt (pr = off)." }
if ($Pr -and $prOn) {
    if ($branch -notlike "local-ai/*") { Fail "refusing to push a branch not under local-ai/" }
    git -C $work push -q origin "${branch}:${branch}"
    if ($LASTEXITCODE -ne 0) { Fail "push failed; the commit is safe on the local branch $branch" }
    $closes = if ($Issue -gt 0) { "Closes #$Issue`n`n" } else { "" }
    $body = $closes + (Get-Content $report -Raw) + "`n`nFor Claude (see local-ai/FOR-CLAUDE.md): please review. Check the diff against games/$Game/CLAUDE.md and the standing rules, run that game's tests, then merge, fix or close. Tick $Item in planning/TODO.md only if the whole item is now done."
    gh pr create --draft --base $Base --head $branch --title "local-ai: ${Item} ${Game}: $Task" --body $body
}

git -C $root worktree remove --force $work
Write-Host "PASSED in $minutes min. Committed on branch $branch. Report: $report" -ForegroundColor Green
