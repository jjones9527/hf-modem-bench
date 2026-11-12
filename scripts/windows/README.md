# Bench-machine helper scripts

These are copies of the scripts in `%USERPROFILE%` on the Windows bench machine,
kept here so the procedure can be reproduced. Each script registers a scheduled
task with `-LogonType Interactive`, so the work runs in the logged-in desktop
session. An SSH session has no access to the audio devices or the Winlink
windows.

| script | what it does |
|---|---|
| `hfbench_run_task.ps1` + `audio_check.cmd` | Tone check at WGN 20 and 40. Writes `hfbench\levels.json` and `check.txt`. |
| `hfbench_start_listen.ps1 -Minutes N -Setting S` | Records the true per-direction S:N during runs and writes `hfbench\listen-<stamp>.json/.txt`. Each recording gets its own task, so starting one doesn't stop another. |
| `hfbench_start_campaign.ps1 -Campaign NAME -MaxRuns N [-AutoContinue]` | Runs `hfbench run --automate` for a campaign in `hfbench\runs\NAME`, tee'd to `console-<stamp>.txt`. `-AutoContinue` passes `--auto-continue 120`. `-Recover` passes `--recover`: after a failed run the runner clears both Outboxes, restarts both Winlink Express instances and their Ardop P2P sessions, and carries on. |

| `hfbench_ui_do.ps1 -Call CALL -Do ACTION [-Arg X]` | Runs one `hfbench.winlink_ui` step in the desktop session (`status`, `delete-outbox`, `close-session`, `close`, `open-session`, `launch "C:\RMS Express"`) and prints its log. Used to try the recovery step by step. |

Run one over SSH with `powershell -NoProfile -ExecutionPolicy Bypass -File %USERPROFILE%\<script>`.
