# Your local AI

Everything here runs on this laptop. No internet is needed once it's set up,
and nothing leaves the machine.

| Piece | What it is |
|---|---|
| Ollama | Runs the model on your graphics card. Starts with Windows (tray icon). |
| devstral-small-2:24b | The model (the "brain"), 15 GB, stored by Ollama. |
| Aider | The agent (the "hands"): reads and edits files, runs tests. |
| `RULES.md` | Your standing rules. The model reads them every time. |
| `work.ps1` | Starts the AI on one TODO item in one game. |
| `finish.ps1` | Tests, ticks the item, and commits. Never pushes. |

## Doing one TODO item

1. Open a terminal in the project folder (`Documents\bcm206`).
2. Start it, naming the game folder and the item:
   ```
   .\local-ai\work.cmd -Game lighthouse -Item QI-52
   ```
3. Type: `Do the task in TASK.md. First tell me your plan and which files you need.`
4. Add the files it asks for with `/add <file>`, then say `go`.
   It runs the game's tests and flake8 after each edit and fixes failures.
5. Check the game in a browser if you like, then type `/exit`.
6. Commit it:
   ```
   .\local-ai\finish.cmd -Game lighthouse -Item QI-52
   ```
   This stops if tests fail, shows the files, and asks before committing.

## Useful Aider commands
- `/undo` — undo the AI's last edit
- `/diff` — show what it changed
- `/ask <question>` — ask without letting it edit
- `/drop <file>` — stop showing it a file

## If it is slow
Run `ollama ps`. Normal is about `17%/83% CPU/GPU`. If the CPU share is much
higher, close other GPU programs (games, video), or lower `num_ctx` in
`aider.model.settings.yml`, or use the smaller model:
`ollama pull qwen2.5-coder:14b`, then add `-Model ollama_chat/qwen2.5-coder:14b`
to the work.ps1 line.

Two Windows settings (on your account, read only by Ollama) make it fit
better: `OLLAMA_FLASH_ATTENTION=1` and `OLLAMA_KV_CACHE_TYPE=q8_0`. Delete
them under "Edit environment variables for your account" to undo.
Some of the model always runs on the CPU (about 17%): it is 15 GB on a 16 GB card.

## Which games it can work on
To edit a file the model must read all of it, and it holds about 24,000 tokens.
- **Yes:** every game whose `game.py` is under ~1,700 lines (Lighthouse, Rule Finder,
  Hull Repair, Lexis, Mirror Lab, Teach the Machine, Stranded, Station Medic,
  Reaction Bench, Picture Grid, Robot Script, Pocket Bazaar, Constellations,
  Logic Gates, Evidence Hunt, Dead Reckoning, Heist Committee, Signal).
- **Only CSS/HTML changes:** the big games (Tide, Grid, Herd, Thaw, Loop, Drift,
  Aftermath, SOL, Canopy, Continuum, Trade Empire, Le Champ de Mots, Chronicle).
  Their `game.py` is far too big for any model this laptop can run.

## Expectations
This model is much weaker than Claude. Keep tasks small and in one game.
If it gets confused, `/undo` and give it a smaller piece of the item.
