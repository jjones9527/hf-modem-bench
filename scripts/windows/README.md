# Bench-machine helper scripts

These are copies of the scripts in `%USERPROFILE%` on the Windows bench machine,
kept here so the procedure can be reproduced. Most of them register a scheduled
task with `-LogonType Interactive`, so the work runs in the logged-in desktop
session. An SSH session has no access to the audio devices or the Winlink
windows. Run one over SSH with
`powershell -NoProfile -ExecutionPolicy Bypass -File %USERPROFILE%\<script>`.

## Campaigns

| script | what it does |
|---|---|
| `hfbench_start_campaign.ps1 -Campaign NAME -MaxRuns N [-AutoContinue] [-Recover] [-Relay]` | Runs `hfbench run --automate` for `hfbench\runs\NAME` in the desktop session (task `hfbench_pilot`), tee'd to `runs\NAME\console-<stamp>.txt`. `-AutoContinue` passes `--auto-continue 120`. `-Recover` passes `--recover`: after a failed run the runner clears both Outboxes, restarts both Winlink Express instances, reopens the modem's P2P session (from the run sheet's modem profile) and carries on. `-Relay` (VARA-protocol modems) makes sure the bench relay is running and writes its state to `runs\NAME\relay.txt`. If any Mercury runs, the script refuses to start unless exactly one `mercury-ui.exe` runs per station. |
| `hfbench_start_listen.ps1 -Minutes N -Setting S [-Repeat R]` | Records the true per-direction S:N during runs: `hfbench\listen-<stamp>[-<n>].json/.txt`, R files of N minutes back to back. Each recording gets its own task, so starting one doesn't stop another. |
| `hfbench_start_relay.ps1 [-Extra ARGS] [-Restart]` | Starts `vara_relay.py` (task `hfbench_relay`): station 2's Winlink connects to 8320/8321, the relay passes everything to station 2's modem on 8310/8311 and logs it to `hfbench\relay-<stamp>.log`. By default it holds Winlink Express's 5-min P2P timer DISCONNECT (`--hold-timeout-disconnect`); `-Extra ""` logs only. A running relay is left alone (restarting it drops Winlink's connection to the modem) unless `-Restart`. |
| `hfbench_ui_do.ps1 -Call CALL -Do ACTION [-Arg X]` | Runs one `hfbench.winlink_ui` step in the desktop session (`status`, `delete-outbox`, `close-session`, `close`, `open-session`, `launch "C:\RMS Express"`) and prints its log. `status` shows the session window's state and folder counts. |

## Checks

| script | what it does |
|---|---|
| `hfbench_run_task.ps1` + `audio_check.cmd` | Tone check at WGN 20 and 40 (`hfbench audio check --snr 20 40`). Writes `hfbench\levels.json` and `check.txt`, ending with `EXIT n`. Reads the sound devices from the ARDOP_Win TNC ini files. |
| `hfbench_desktop.ps1 -HfArgs "..." -Out FILE` | Runs any `hfbench` command in the desktop session and waits, e.g. the 16QAM path check `-HfArgs "audio qam --snr 40 40 --json qam.json" -Out qam.txt`. |
| `hfbench_live_levels.ps1 [-Snr S]` | Opens a console on the bench desktop that repeats the tone check every few seconds, for trimming levels live. |
| `hfbench_fmt.ps1`, `hfbench_fx.ps1` | Show each active audio device's shared-mode format, and whether enhancements are disabled on the USB devices. |

## ARDOP settings

| script | what it does |
|---|---|
| `busydet_off.ps1` | Sets `BusyDet=0` in both `ARDOP_Win TNC.ini` files (keeps a backup). ARDOP must be closed: it rewrites its ini on exit. |
| `swap_ardop_devices.ps1` | Swaps the sound devices between the two ARDOP_Win instances (used for the swap01/02 campaigns). ARDOP must be closed. |
