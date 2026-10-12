# Start the local AI on one TODO item inside one game.
#   .\local-ai\work.ps1 -Game tide -Item GD-15
# It can only see and change files in games/<Game>, runs that game's tests and
# flake8 after every edit, and never commits. Run finish.ps1 when you are happy.
param(
    [Parameter(Mandatory = $true)][string]$Game,
    [Parameter(Mandatory = $true)][string]$Item,
    [string]$Model = "ollama_chat/devstral-small-2:24b"
)
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
$gameDir = Join-Path $root "games\$Game"
$aiDir = Join-Path $root "local-ai"
if (-not (Test-Path $gameDir)) { Write-Host "No game folder games\$Game"; exit 1 }

$itemText = python (Join-Path $aiDir "todo_item.py") show $Item
if ($LASTEXITCODE -ne 0) { Write-Host $itemText; exit 1 }

# The task file the model reads, kept out of git (see .git/info/exclude)
$histDir = Join-Path $aiDir ".history"
New-Item -ItemType Directory -Force $histDir | Out-Null
$task = Join-Path $histDir "TASK.md"
@"
# Your task: TODO item $Item in the game '$Game'

$($itemText -join "`n")

Work only in games/$Game. Follow RULES.md and this game's CLAUDE.md.
"@ | Set-Content -Encoding utf8 $task

# Bring your folder up to date with what other AIs/sessions pushed, but only when that is a
# plain fast-forward (never a merge, reset or stash). Otherwise just say so.
git -C $root fetch -q origin
$branchNow = git -C $root rev-parse --abbrev-ref HEAD
$behind = [int](git -C $root rev-list --count "HEAD..origin/$branchNow" 2>$null)
if ($behind -gt 0) {
    $dirty = git -C $root status --porcelain --untracked-files=no
    if (-not $dirty) {
        git -C $root merge -q --ff-only "origin/$branchNow"
        if ($LASTEXITCODE -eq 0) { Write-Host "Pulled $behind new commit(s) from GitHub." }
        else { Write-Host "Your $branchNow and GitHub's have both changed; pull and merge by hand when convenient." -ForegroundColor Yellow }
    }
    else { Write-Host "GitHub has $behind newer commit(s), but you have uncommitted changes, so nothing was pulled." -ForegroundColor Yellow }
}

try { Invoke-RestMethod http://127.0.0.1:11434/api/version | Out-Null }
catch { Write-Host "Ollama is not running. Start it from the Start menu, then try again."; exit 1 }

$env:OLLAMA_API_BASE = "http://127.0.0.1:11434"
$readArgs = @("--read", (Join-Path $aiDir "RULES.md"), "--read", $task)
$gameNotes = Join-Path $gameDir "CLAUDE.md"
if (Test-Path $gameNotes) { $readArgs += @("--read", $gameNotes) }

Write-Host ""
Write-Host $itemText
Write-Host ""
Write-Host "Tip: start by typing:  Do the task in TASK.md. First tell me your plan and which files you need."
Write-Host "Add files it needs with /add <file>. Type /exit when done, then run finish.ps1."
Write-Host ""

$aider = (Get-Command aider -ErrorAction SilentlyContinue).Source
if (-not $aider) { $aider = Join-Path $HOME ".local\bin\aider.exe" }

Push-Location $gameDir
try {
    & $aider --model $Model `
        --model-settings-file (Join-Path $aiDir "aider.model.settings.yml") `
        --subtree-only --map-tokens 1024 `
        --no-auto-commits --no-dirty-commits --no-gitignore `
        --test-cmd "python ../../scripts/generate-pc-pages.py >NUL && python -m pytest -q -x --tb=line -p no:warnings" --auto-test `
        --lint-cmd "python: python -m flake8 --extend-ignore=E501" --auto-lint `
        --chat-history-file (Join-Path $histDir "chat.md") `
        --input-history-file (Join-Path $histDir "input.txt") `
        --analytics-disable --no-check-update `
        @readArgs
}
finally { Pop-Location }
