@echo off
rem Start the local AI's queue in its own window that stays open when the run ends (so its last lines can be read).
rem Start it by double-clicking this file, or with: explorer.exe "C:\Users\Esthe\Documents\bcm206\local-ai\start-ai.cmd"
rem Started that way, the runner belongs to Windows Explorer, not to the Claude app or a terminal tab, so an app
rem update or restart no longer closes it (on 2026-10-18 at 23:38 an automatic Claude app update did).
title Local AI queue
cd /d "%~dp0.."
powershell -NoExit -NoProfile -ExecutionPolicy Bypass -File "%~dp0ai-queue.ps1" %*
