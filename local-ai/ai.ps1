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
# The model can be switched for every following task in config.txt (model = ...), without restarting the queue.
if (-not $PSBoundParameters.ContainsKey("Model")) {
    $cfgModel = Select-String -Path (Join-Path $PSScriptRoot "config.txt") -Pattern "^\s*model\s*=\s*(\S+)\s*$" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($cfgModel) { $Model = $cfgModel.Matches[0].Groups[1].Value }
}
if ($Item -match '^chain:([A-Za-z0-9-]+):(\d+)$') { $Chain = $Matches[1]; $Step = [int]$Matches[2] }
if ($Chain) { $Item = "$Chain-$Step" }
# "Continue": git prints harmless notes on stderr, which "Stop" would turn into crashes in
# Windows PowerShell 5.1. Every step checks its own result ($LASTEXITCODE / Fail) instead.
$ErrorActionPreference = "Continue"
$env:PYTHONUTF8 = "1"   # every python this starts reads files as UTF-8, like on a Mac (Tide and Grid tests read style.css without an encoding and crash under Windows' cp1252)
$root = Split-Path -Parent $PSScriptRoot
$aiDir = Join-Path $root "local-ai"
$reports = Join-Path $aiDir ".history\reports"
New-Item -ItemType Directory -Force $reports | Out-Null
$maxTokens = 17000   # biggest single file the model can hold next to the rules (see README)
# Long-context mode: the default Qwen model holds 64k tokens; a big game's game.py is 73k-146k, so tasks in
# those games switch to a long-context name of the same model (ollama cp, no extra disk). Each switch reloads
# the model for a minute or two, so the queue keeps a game's tasks together.
if ($Model -like "ollama_chat/qwen3.6*") {
    $biggest = 0
    # 3 characters per token, not 3.5: measured on SOL, real code packs tighter (Tide's 349 KB game.py is ~116k tokens)
    Get-ChildItem (Join-Path $root "games\$Game") -Filter *.py -File -ErrorAction SilentlyContinue |
        ForEach-Object { $biggest = [math]::Max($biggest, [math]::Round($_.Length / 3.0)) }
    # A page-only (view) task never sees the big game.py (it is hidden from the model below), so 128k is plenty.
    if ($biggest -gt 100000 -and $Task -match 'view idea') { $Model = "ollama_chat/qwen3.6-128k"; $maxTokens = 110000 }
    elseif ($biggest -gt 100000) { $Model = "ollama_chat/qwen3.6-192k"; $maxTokens = 165000 }
    elseif ($biggest -gt 40000) { $Model = "ollama_chat/qwen3.6-128k"; $maxTokens = 110000 }
    else { $maxTokens = 50000 }
}

function Fail($msg) { Write-Host "STOPPED: $msg" -ForegroundColor Red; exit 1 }

# A running tally after every task, in the Terminal and in its window title (visible from the taskbar).
# Counted from queue-done.txt plus this task, which the queue only writes there after this script ends.
function Show-Tally([bool]$passed) {
    try {
        $doneFile = Join-Path $PSScriptRoot "queue-done.txt"
        $rows = @(if (Test-Path $doneFile) { Get-Content $doneFile -Encoding utf8 | ForEach-Object { $_.TrimStart([char]0xFEFF) } |
            Where-Object { $_ -match '^(PASSED|FAILED)  ' } })
        $today = Get-Date -Format "yyyy-MM-dd"
        $isTodo = ($Item -notmatch '^(T|EDGE)-')
        $run = $rows.Count + 1
        $runToday = @($rows | Where-Object { $_ -match "^\S+  $today" }).Count + 1
        $built = @($rows | Where-Object { $_ -match '^PASSED ' -and $_ -notmatch '\| (T|EDGE)-' }).Count + $(if ($passed -and $isTodo) { 1 } else { 0 })
        $passedAll = @($rows | Where-Object { $_ -like "PASSED*" }).Count + $(if ($passed) { 1 } else { 0 })
        $mark = if ($passed) { [char]0x2713 } else { [char]0x00B7 }
        Write-Host ("{0} Tally: {1} tasks run ({2} passed) - {3} TODO items built - {4} today" -f $mark, $run, $passedAll, $built, $runToday) -ForegroundColor Cyan
        $Host.UI.RawUI.WindowTitle = "Local AI: $built TODO built - $run run - $runToday today"
    } catch { }
}

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
# Feature tasks for the same game build on each other through local-ai/stack-<game>: each starts from
# the last passed feature for that game, so two features never edit the same file from the same base and
# conflict (2026-10-12: six Signal pc.js branches could not be combined). Test-writing tasks (T-, EDGE-)
# only add new files and still start from main. A reviewer reviews the stack, one commit per TODO item.
$isFeature = -not $Chain -and $Item -notmatch '^(T|EDGE)-'
$stack = "local-ai/stack-$Game"
$haveStack = $isFeature -and ($null -ne (git -C $root rev-parse -q --verify "refs/heads/$stack" 2>$null))
# A stack that no longer merges with GitHub's main has been superseded there (2026-10-14: the audit rebuilt
# Lighthouse's seven stacked ideas on main, and every Lighthouse task then failed in seconds on the conflict).
# Keep the old stack under a dated name for the record and start this game's stack again from main.
if ($haveStack -and $haveRemote) {
    git -C $root merge-tree --write-tree $remoteBase $stack 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) {
        git -C $root branch -m $stack "$stack-superseded-$stamp"
        Write-Host "local-ai/stack-$Game conflicts with GitHub's $Base, so it was kept as $stack-superseded-$stamp and this task starts from $Base."
        $haveStack = $false
    }
}
if ($haveStack) { $start = $stack }
git -C $root worktree add -q -b $branch $work $start
if ($LASTEXITCODE -ne 0) { Fail "could not create the working copy" }
if (($start -eq $Base -or $haveStack) -and $haveRemote -and -not ($Chain -and $Step -gt 1)) {
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

Do only this. Change only files in games/$Game. Follow RULES.md. Write every path from the repo root: game files as games/$Game/<file> and new tests as games/$Game/tests/test_<name>.py. Do not add sys.path code to tests: the game's tests/conftest.py already makes its modules importable. Every feature must come with a test in games/$Game/tests/ that would fail without it (see RULES.md: a pytest test for Python, a browser test for page code), or the task fails. If you need a file that is not in the chat yet, name it: it will be added and you will be asked again, so then make the edits straight away.
"@ | Set-Content -Encoding utf8 $taskFile

# --- Run Aider with no chatting -----------------------------------------
$env:OLLAMA_API_BASE = "http://127.0.0.1:11434"
# The task goes in as the message itself (newest text, so it is never the part cut when the context fills up),
# through a file so Windows never mangles its quotes. RULES.md stays a read-only file.
$readArgs = @("--read", (Join-Path $aiDir "RULES.md"))
if (Test-Path (Join-Path $gameDir "CLAUDE.md")) { $readArgs += @("--read", (Join-Path $gameDir "CLAUDE.md")) }
# A game still being built has a plan (planning/<game>-plan.md) with the design each milestone follows.
$planFile = Join-Path $work "planning\$Game-plan.md"
if ($Item -match "^QI-\d+-\d+$" -and (Test-Path $planFile)) { $readArgs += @("--read", $planFile) }
$fileArgs = @(); foreach ($f in $Files) { $fileArgs += @("--file", $f) }
# Page-only (view) tasks, 2026-10-14: given no files, the model asked for game.py, pc.html, index.html and style.css
# at once. In Tide that is ~590 KB, far past its context, and Aider quit silently with no edits (5 failures in a row).
# So: start it with the page files already in the chat, and hide what it must not open. .aiderignore keeps a file
# out of the chat and the repo map; pc.html is generated (never edited) and a big game.py has no place in a view task.
$ignore = @("# written by ai.ps1 (this first line absorbs the byte-order mark Set-Content adds)", "games/$Game/pc.html")
if ($Task -match 'view idea') {
    Get-ChildItem $gameDir -Filter *.py -File | Where-Object { $_.Length -gt 120000 } | ForEach-Object { $ignore += "games/$Game/$($_.Name)" }
    if ($fileArgs.Count -eq 0) {
        $viewFiles = if ($Task -match 'PC \(Desktop\) view') { @("pc.js", "pc.css", "pc-config.json") } else { @("style.css", "ui.js", "app.js") }
        foreach ($f in $viewFiles) { if (Test-Path (Join-Path $gameDir $f)) { $fileArgs += @("--file", $f) } }
    }
}
Set-Content -Encoding utf8 (Join-Path $work ".aiderignore") ($ignore -join "`n")
$log = Join-Path $reports (($branch -replace '/', '_') + ".log")
$started = Get-Date
Write-Host "Working on $Item in $Game (branch $branch). This takes several minutes..."

$aiderArgs = @("--model", $Model,
    "--model-settings-file", (Join-Path $aiDir "aider.model.settings.yml"),
    "--subtree-only", "--map-tokens", "1024",
    "--no-auto-commits", "--no-dirty-commits", "--no-gitignore",
    "--test-cmd", "python ../../scripts/generate-pc-pages.py >NUL && python -m pytest -q -x --tb=line -p no:warnings --ignore-glob=*browser*", "--auto-test",   # browser tests only run in the final check: they are slow and Aider reruns tests after every edit
    "--lint-cmd", "python: python -m flake8 --select=E9,F63,F7,F82", "--auto-lint",   # only real errors here: layout is fixed automatically afterwards, so the model keeps its retries for failing tests
    "--yes-always", "--no-pretty", "--no-stream", "--analytics-disable", "--no-check-update", "--timeout", "1800",   # a big multi-file request can take a long time on this laptop: wait up to 30 min per reply
    "--chat-history-file", $log, "--input-history-file", "NUL") + $readArgs
# Thinking: the model's first reply was 6.5k-12k tokens of reasoning (3-5 minutes). config.txt: think = on | off | ab
# ("ab" alternates task by task so local-ai/ab_report.py can compare pass rates and times before choosing).
$thinkMode = "on"
$cfgThink = Select-String -Path (Join-Path $aiDir "config.txt") -Pattern "^\s*think\s*=\s*(on|off|ab)\s*$" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($cfgThink) { $thinkMode = $cfgThink.Matches[0].Groups[1].Value }
if ($thinkMode -eq "ab") {
    $doneRows = @(Get-Content (Join-Path $aiDir "queue-done.txt") -Encoding utf8 -ErrorAction SilentlyContinue | Where-Object { $_ -match '(PASSED|FAILED)  ' }).Count
    $thinkMode = if ($doneRows % 2 -eq 0) { "off" } else { "on" }
}
if ($thinkMode -eq "off") { $aiderArgs += @("--reasoning-effort", "none", "--no-check-model-accepts-settings") }

# Run Aider as a background job so a stuck run can be stopped when the task's time is up
# instead of blocking the whole queue for days. Returns $true if it was stopped for time.
function Invoke-Aider($messageFile, $extraFiles) {
    $left = $TimeoutMinutes * 60 - ((Get-Date) - $started).TotalSeconds
    if ($left -lt 60) { return $true }
    $argList = $aiderArgs + @($extraFiles | Where-Object { $_ }) + @("--message-file", $messageFile)
    $job = Start-Job -ScriptBlock {
        param($dir, $exe, $argList, $apiBase, $outFile)
        $env:OLLAMA_API_BASE = $apiBase
        $env:PYTHONUTF8 = "1"; $env:PYTHONIOENCODING = "utf-8"   # Aider crashed printing a model reply with symbols like a triangle under the cp1252 console
        Set-Location $dir
        & $exe @argList *>&1 | Out-File -Append -Encoding utf8 $outFile   # kept: Aider's own errors (context too full, crashes) never reach the chat log
    } -ArgumentList $gameDir, $aider, $argList, $env:OLLAMA_API_BASE, ($log -replace '\.log$', '.out')
    $stopped = -not (Wait-Job $job -Timeout ([int]$left))
    if ($stopped) {
        # aider.exe is a launcher with a python child: end the whole tree, then the job
        Get-CimInstance Win32_Process -Filter "Name='aider.exe'" | Where-Object { $_.CreationDate -ge $started } |
            ForEach-Object { taskkill /T /F /PID $_.ProcessId 2>$null | Out-Null }
        Stop-Job $job
    }
    Remove-Job $job -Force
    return $stopped
}

function Update-PcPages {
    # pc.html is generated from index.html and must never be hand-edited (the first trial run's
    # only failure). Regenerate it; the generator only rewrites pages whose content changed.
    if (Test-Path (Join-Path $gameDir "pc-config.json")) {
        Push-Location $work
        python scripts/generate-pc-pages.py | Out-Null
        Pop-Location
    }
}

$timedOut = Invoke-Aider $taskFile $fileArgs
Update-PcPages

# Repair rounds: real changes but failing tests (a feature task, not a test-writing one). The model gets a
# fresh session with the failing output and the files it changed, up to twice. This is the step that most
# often turns a near miss (for example one save-format test) into a pass.
# What the work looks like (each changed file and its content hash), so a full test pass can be reused when
# nothing changed afterwards instead of running the slow browser tests twice.
function Get-WorkState {
    $files = @(git -C $work status --porcelain --untracked-files=all | ForEach-Object { $_.Substring(3).Trim('"') } | Where-Object { $_ -notlike ".aider*" } | Sort-Object)
    ($files | ForEach-Object { $p = Join-Path $work $_; if (Test-Path $p -PathType Leaf) { $_ + ":" + (Get-FileHash $p -Algorithm MD5).Hash } else { $_ + ":gone" } }) -join "|"
}
$verifiedState = $null
$verifiedLine = ""
$repairs = 0
while (-not $timedOut -and $repairs -lt 2) {
    $touched = @(git -C $work status --porcelain --untracked-files=all | ForEach-Object { $_.Substring(3).Trim('"') } |
        Where-Object { $_ -like "games/$Game/*" -and $_ -notlike "*/pc.html" })
    if ($touched.Count -eq 0 -or ($touched | Where-Object { $_ -notmatch "/tests/test_ai_[^/]+\.py$" }).Count -eq 0) { break }
    # Tidy layout and the model's new test files first, so flake8 below only reports real mistakes.
    $chgPy = @($touched | Where-Object { $_ -like "*.py" } | ForEach-Object { Join-Path $work $_ } | Where-Object { Test-Path $_ })
    if ($chgPy.Count -gt 0) { python -m autopep8 --in-place --select=E1,E2,E3,W2,W3 @chgPy 2>$null | Out-Null }
    $freshTests = @(git -C $work status --porcelain --untracked-files=all | Where-Object { $_ -match '^(\?\?|A )' } |
        ForEach-Object { $_.Substring(3).Trim('"') } | Where-Object { $_ -match "^games/$([regex]::Escape($Game))/tests/[^/]+\.py$" } | ForEach-Object { Join-Path $work $_ })
    if ($freshTests.Count -gt 0) { python (Join-Path $aiDir "tidy_new_tests.py") @freshTests 2>$null | Out-Null }
    Push-Location $gameDir
    $firstTry = (python -m pytest -q -x --tb=short -p no:warnings --ignore-glob=*browser* 2>&1 | Out-String)
    $passing = ($LASTEXITCODE -eq 0)
    # flake8 counts as a failing check too (2026-10-14: two Lexis features passed every test and then failed the
    # final flake8 on an unused variable and a redefined fixture, with no round to fix them).
    if ($passing -and $chgPy.Count -gt 0) {
        $lintTry = (python -m flake8 --extend-ignore=E501 @chgPy 2>&1 | Out-String)
        if ($LASTEXITCODE -ne 0) { $passing = $false; $firstTry = "flake8 (fix each line; an unused import or variable: delete it):`n" + $lintTry }
    }
    $fastLine = ($firstTry.Trim() -split "`n")[-1]
    if ($passing -and -not $firstTry.StartsWith("flake8")) {
        # The edit loop skips the slow browser tests, so run them once here: if they fail, the model gets to
        # repair them (2026-10-13: two Dead Reckoning features broke browser tests the model never saw).
        $browserFiles = @(Get-ChildItem (Join-Path $gameDir "tests") -Filter "*browser*.py" -File -ErrorAction SilentlyContinue | ForEach-Object { "tests/" + $_.Name })
        $browserLine = "no browser tests"
        if ($browserFiles.Count -gt 0) {
            $browserTry = (python -m pytest -q -x --tb=short -p no:warnings @browserFiles 2>&1 | Out-String)
            $browserLine = ($browserTry.Trim() -split "`n")[-1]
            if ($LASTEXITCODE -ne 0) { $passing = $false; $firstTry = $browserTry }
        }
        if ($passing) { $verifiedState = Get-WorkState; $verifiedLine = "$fastLine; browser tests: $browserLine" }
    }
    Pop-Location
    # Tests pass, but a feature also needs its own test and none of the mistakes the 2026-10-14/15 audits kept
    # finding (local-ai/static_check.py: dead ids, lookups before the page exists, unknown engine actions, no
    # test). Until now a missing test failed the task at the very end and threw the work away; now the model
    # gets a repair round to add it, like a failing test.
    $checkLines = ""
    if ($passing -and $isFeature) {
        $env:NOYVJ_ROOT = $work
        $checkLines = ((python (Join-Path $aiDir "static_check.py") $Game --changed 2>&1) -join "`n")
        $checkFailed = ($LASTEXITCODE -ne 0)
        Remove-Item Env:NOYVJ_ROOT -ErrorAction SilentlyContinue
        if ($checkFailed) { $passing = $false; $verifiedState = $null } else { $checkLines = "" }
    }
    if ($passing) { break }
    $repairs++
    if ($checkLines) {
        $repairFile = Join-Path $work ".aider-repair.md"
        @"
# Finish the feature (repair round $repairs of 2)

You were building this in games/${Game}:

$Task

The tests pass, but the checker found the problems below. Fix each one with small edits.
- no-test: add a test file games/$Game/tests/test_<name>.py that would FAIL without your change and pass with
  it (RULES.md, Tests): a pytest unit test for Python, or a test that reads the changed page file and checks
  the new element, class or handler is there and wired up. Every assert checks a specific value.
- missing-id / data-never-set / unknown-action: the page code uses something nothing creates. Create it, or
  use the name the page or game.py really uses.
- head-lookup: move the lookup inside window.addEventListener("load", ...).

Checker output:
~~~
$checkLines
~~~
"@ | Set-Content -Encoding utf8 $repairFile
        $repairFiles = @(); foreach ($f in $touched) { $repairFiles += @("--file", $f.Substring("games/$Game/".Length)) }
        $timedOut = Invoke-Aider $repairFile $repairFiles
        Remove-Item $repairFile -ErrorAction SilentlyContinue
        Update-PcPages
        continue
    }
    $tail = (($firstTry.Trim() -split "`n") | Select-Object -Last 60) -join "`n"
    $repairFile = Join-Path $work ".aider-repair.md"
    @"
# Fix the failing checks (repair round $repairs of 2)

You were building this in games/${Game}:

$Task

Your changes are in the files listed below and already in this chat. The game's tests or flake8 now fail. Fix the
cause with small edits; do not delete or weaken existing tests. Remember the save rules in RULES.md: old
saves must load unchanged, and a new key appears in get_state() only when its value is not the default.

Test output (end):
~~~
$tail
~~~
"@ | Set-Content -Encoding utf8 $repairFile
    $repairFiles = @(); foreach ($f in $touched) { $repairFiles += @("--file", $f.Substring("games/$Game/".Length)) }
    $timedOut = Invoke-Aider $repairFile $repairFiles
    Remove-Item $repairFile -ErrorAction SilentlyContinue
    Update-PcPages
}
Remove-Item $taskFile -ErrorAction SilentlyContinue

# --- Check the result ----------------------------------------------------
# Aider writes chat paths relative to the repo root, so the model sometimes puts a NEW test file in the
# top-level tests/ folder (tests/test_goals.py, tests/lexis/test_x.py) instead of games/<game>/tests/.
# A brand-new one is moved where it belongs; anything else outside the game still fails below.
$gameTests = Join-Path $gameDir "tests"
foreach ($stray in @(git -C $work status --porcelain --untracked-files=all | Where-Object { $_.StartsWith("??") } |
        ForEach-Object { $_.Substring(3).Trim('"') } | Where-Object { $_ -match '^tests/(.+/)?[^/]+\.py$' })) {
    $target = Join-Path $gameTests (Split-Path $stray -Leaf)
    if (-not (Test-Path $target)) { Move-Item (Join-Path $work $stray) $target; Write-Host "Moved stray test file $stray into games/$Game/tests/" }
}
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
# Test-writing tasks make tests/test_ai_*.py files. Any brand-new test file the AI wrote, whatever its
# name, also loses unused imports and variables.
$newTests = @($inside | Where-Object { $_ -match "^games/$([regex]::Escape($Game))/tests/test_ai_[^/]+\.py$" })
$testOnly = ($inside.Count -gt 0 -and $newTests.Count -eq $inside.Count)
$untracked = @(git -C $work status --porcelain --untracked-files=all | Where-Object { $_.StartsWith("??") -or $_.StartsWith("A ") } |   # Aider stages the files it creates ("A "), so they count as new too
    ForEach-Object { $_.Substring(3).Trim('"') })
$newTestFiles = @($untracked | Where-Object { $_ -match "^games/$([regex]::Escape($Game))/tests/[^/]+\.py$" })
if ($newTestFiles.Count -gt 0) {
    $newPaths = @($newTestFiles | ForEach-Object { Join-Path $work $_ })
    python (Join-Path $aiDir "tidy_new_tests.py") @newPaths 2>$null | Out-Null   # one import per line, unused ones gone, late imports marked noqa E402
}

Push-Location $gameDir
if ($verifiedState -and $verifiedState -eq (Get-WorkState)) {
    # nothing changed since the repair check ran the whole suite (fast tests + browser tests): reuse it
    $testOut = "$verifiedLine (whole suite, before the final tidy-up changed nothing)"
    $testsOk = $true
} else {
    $testOut = (python -m pytest -q 2>&1 | Out-String)
    $testsOk = ($LASTEXITCODE -eq 0)
}
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
# A feature that changes the game's Python must come with a test (the pattern album shipped untested
# and lost its data on reload).
$gamePy = @($inside | Where-Object { $_ -like "*.py" -and $_ -notmatch "/tests/" })
$testFiles = @($inside | Where-Object { $_ -match "/tests/[^/]+\.py$" })
if ($isFeature -and -not $testOnly -and $inside.Count -gt 0 -and $testFiles.Count -eq 0) {
    # every TODO feature comes with a test (owner, 2026-10-14): Python or page code alike
    $what = if ($gamePy.Count -gt 0) { "changed the game's Python ($($gamePy -join ', '))" } else { "changed the page ($((@($inside | Where-Object { $_ -notlike '*/pc.html' }) | Select-Object -First 3) -join ', '))" }
    $problems += "it $what but added or changed no test in games/$Game/tests/"
}
$testLine = ($testOut.Trim() -split "`n")[-1]

$flakeOut = ""
if ($py.Count -gt 0) {
    $flakeOut = (python -m flake8 --extend-ignore=E501 @py 2>&1 | Out-String)
    if ($LASTEXITCODE -ne 0) { $problems += "flake8 found problems" }
}
# Load the game's pages in a real browser when the page code changed: tests never run pc.js or app.js,
# and on 2026-10-12 two Signal features passed every test but crashed or did nothing in the browser.
# Only NEW script errors fail the task (main's own errors are cached per main commit as a baseline).
$pageNote = ""
if (@($inside | Where-Object { $_ -match '\.(js|html|css)$' -and $_ -notlike "*/pc.html" }).Count -gt 0) {
    $mainHead = (git -C $root rev-parse --short HEAD).Trim()
    $baseFile = Join-Path $reports "pagecheck-$Game-$mainHead.json"
    if (-not (Test-Path $baseFile)) { python (Join-Path $aiDir "page_check.py") $root $Game | Set-Content -Encoding utf8 $baseFile }
    $base = Get-Content $baseFile -Raw | ConvertFrom-Json
    $now = python (Join-Path $aiDir "page_check.py") $work $Game | ConvertFrom-Json
    if ($now -is [System.Management.Automation.PSCustomObject] -and $now.unavailable) {
        $pageNote = "browser check skipped: $($now.unavailable)"
    } else {
        $known = @($base | Where-Object { $_ -is [string] })
        $new = @($now | Where-Object { $_ -is [string] -and $known -notcontains $_ })
        if ($new.Count -gt 0) { $problems += "the page shows a new script error in the browser: $($new[0])" }
        else { $pageNote = "browser check: no new script errors" }
    }
}
# The same checker as in the repair rounds, as a final gate (findings go in the report for the reviewer).
$staticOut = ""
if ($isFeature -and -not $testOnly -and $inside.Count -gt 0) {
    $env:NOYVJ_ROOT = $work
    $staticOut = ((python (Join-Path $aiDir "static_check.py") $Game --changed 2>&1) -join "`n")
    if ($LASTEXITCODE -ne 0) { $problems += "static_check.py found problems (see below)" } else { $staticOut = "" }
    Remove-Item Env:NOYVJ_ROOT -ErrorAction SilentlyContinue
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
    $commitOk = ($LASTEXITCODE -eq 0)
    Remove-Item $msgFile -ErrorAction SilentlyContinue
    if (-not $commitOk) { $ok = $false; $problems += "git commit failed" }
    elseif ($isFeature) {
        # the next feature task for this game starts from here (see local-ai/stack-<game> above)
        git -C $root branch -f $stack $branch 2>$null | Out-Null
    }
}

@"
# $(if ($ok) { "PASSED" } else { "FAILED" }): $Item in $Game

- Branch: ``$branch``
- Task: $Task
- Took: $minutes minutes
- Tests: $testLine
$(if ($salvageNote) { "- Salvage: $salvageNote" })
- Thinking: $thinkMode
$(if ($pageNote) { "- $pageNote" })
$(if ($repairs) { "- Repair rounds: $repairs (the model was shown failing tests or checker findings and asked to fix them)" })
$(if ($problems.Count) { "- Problems: " + ($problems -join "; ") })

## Changed files
$diffStat
$(if ($flakeOut) { "## flake8`n$flakeOut" })
$(if ($staticOut) { "## static_check.py`n~~~`n$staticOut`n~~~" })
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
    # One automatic second try for a TODO task (not test-writing tasks): back on the second list, which runs
    # after queue.txt. A second failure is not retried again.
    if ($Item -notmatch '^(T|EDGE)-') {
        $doneFile = Join-Path $aiDir "queue-done.txt"
        $failedBefore = @(Get-Content $doneFile -Encoding utf8 -ErrorAction SilentlyContinue | Where-Object { $_ -match "^\W*FAILED .*\| $([regex]::Escape($Item)) \|" }).Count
        if ($failedBefore -eq 0 -and -not $timedOut) {
            $retryLine = "$Game | $Item | $($Files -join ', ') | $($Task -replace '\|', '/')"
            $nextFile = Join-Path $aiDir "queue-next.txt"   # retries go to the top, ahead of the parked test-writing tasks
            $nextLines = @(Get-Content $nextFile -Encoding utf8 -ErrorAction SilentlyContinue)
            $head = @($nextLines | Select-Object -First 1)
            $rest = @($nextLines | Select-Object -Skip 1)
            Set-Content -Encoding utf8 $nextFile (@($head) + @($retryLine) + $rest)
            Write-Host "Queued one more try for $Item on the second list (queue-next.txt)."
        }
    }
    Write-Host "FAILED ($($problems -join '; ')). Nothing committed. Report: $report" -ForegroundColor Yellow
    Show-Tally $false
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
Show-Tally $true
