# Check and commit the local AI's work on one TODO item. Never pushes.
#   .\local-ai\finish.ps1 -Game tide -Item GD-15 [-Message "GD-15: foam edge on flood flash"]
param(
    [Parameter(Mandatory = $true)][string]$Game,
    [Parameter(Mandatory = $true)][string]$Item,
    [string]$Message = ""
)
$root = Split-Path -Parent $PSScriptRoot
$gameDir = Join-Path $root "games\$Game"
Set-Location $root

# 1. Files changed in this game (edited or new). Anything outside it is a warning.
$changed = @(git status --porcelain --untracked-files=all -- "games/$Game" |
    ForEach-Object { $_.Substring(3).Trim('"') })
$outside = @(git status --porcelain --untracked-files=all |
    ForEach-Object { $_.Substring(3).Trim('"') } |
    Where-Object { $_ -notlike "games/$Game/*" -and $_ -ne "planning/TODO.md" })
if ($changed.Count -eq 0) { Write-Host "Nothing changed in games/$Game."; exit 1 }
if ($outside.Count -gt 0) {
    Write-Host "Warning: these changed files are outside games/$Game and will NOT be committed:"
    $outside | ForEach-Object { Write-Host "  $_" }
}

# 2. Tests must be green
Push-Location $gameDir
python -m pytest -q
$testsOk = ($LASTEXITCODE -eq 0)
Pop-Location
if (-not $testsOk) { Write-Host "Tests failed. Nothing committed."; exit 1 }

# 3. flake8 on changed Python files
$py = @($changed | Where-Object { $_ -like "*.py" -and (Test-Path $_) })
if ($py.Count -gt 0) {
    python -m flake8 --extend-ignore=E501 @py
    if ($LASTEXITCODE -ne 0) { Write-Host "flake8 found problems. Nothing committed."; exit 1 }
}

# 4. Show what will be committed and ask
Write-Host ""
Write-Host "Files to commit:"
$changed | ForEach-Object { Write-Host "  $_" }
git diff --stat -- @changed
$answer = Read-Host "Tick $Item in TODO.md and commit these? (y/n)"
if ($answer -ne "y") { Write-Host "Stopped. Nothing committed."; exit 0 }

# 5. Tick the item, refresh the progress chart, commit with explicit paths only
python local-ai/todo_item.py tick $Item
python scripts/todo-progress.py
if (-not $Message) { $Message = "${Item}: done with the local AI" }
$paths = $changed + "planning/TODO.md"
git add -- @paths
git commit -m $Message -- @paths
Write-Host "Committed. Not pushed."
