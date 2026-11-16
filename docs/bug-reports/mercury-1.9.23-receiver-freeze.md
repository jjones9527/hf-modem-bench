# Mercury 1.9.23: receiving station stops processing audio mid-session

Filed 16 Nov 2026 as [Rhizomatica/mercury#579](https://github.com/Rhizomatica/mercury/issues/579). Text as posted:

---

**Version:** Mercury 1.9.23 (git 09f258f8), Windows 10 Pro 22H2 (x64), GUI `mercury-ui.exe`, `sound_system = wasapi`.

**Summary.** During long Winlink Express P2P sessions, the *receiving* station's Mercury stops processing received audio partway through a session. The engine log stops mid-reception, the process stays alive (Windows reports it as responding) and CPU drops to near zero. No error is logged. The waterfall stops updating. The link then dies because the receiver never answers. Seen three times so far, always on the receiving station.

**Setup.** Bench test, no radios:
- Two Mercury installs on one PC (`MercuryHF` on ports 8300/8301 and `MercuryHF 2` on 8310/8311), each with its own USB sound card (C-Media chips), through a Teensy IONOS HF channel simulator (WGN, 3 kHz).
- Winlink Express 1.8.6.0 on each station, "Vara HF P2P" session, one way: station 2 sends ten 42 KB (compressed) messages per session to station 1.
- `busy_detect = false`, `tx_gain_db` +3.5 / +3.0.
- The receiving station's Winlink connects to Mercury directly. The sending station's goes through a small logging TCP relay, so the frozen side has nothing between it and Winlink.

**The three freezes** (station 1 = receiver, VA3ZTF):

| # | Last log line (local, UTC−5) | Time into session | Mercury uptime | `rx_total` at the last line |
|---|---|---|---|---|
| 1 | 2026-11-15 19:10:57 | ~30 min | ~7.0 h | 200,976 |
| 2 | 2026-11-15 21:02:33 | ~37 min | ~1.8 h | 292,314 |
| 3 | 2026-11-16 07:24:23 | ~44 min | ~0.8 h | 286,164 |

All three happened at the same channel setting, where Mercury's measured data S:N was about 17.5 dB and one message takes about 5 minutes. Another 10-message session at the same setting completed normally, and so did one-hour sessions at 17.8 dB and 25.5 dB.

**The log just stops after a burst of received frames.** Freeze 3, last lines:

```
2026-11-16 07:24:14.994 [+2958.223s] [TMG] [arq-timing] turn frames=1 since_rx=1097ms since_tx_end=30090ms
2026-11-16 07:24:15.003 [+2958.231s] [INF] [radio] TX enabled (PTT ON)
2026-11-16 07:24:18.748 [+2961.976s] [INF] [radio] TX disabled (PTT OFF)
2026-11-16 07:24:23.186 [+2966.415s] [TMG] [arq-timing] car_rx bytes=1532 rx_total=281564
2026-11-16 07:24:23.187 [+2966.415s] [TMG] [arq-timing] car_rx bytes=2300 rx_total=283864
2026-11-16 07:24:23.187 [+2966.415s] [TMG] [arq-timing] car_rx bytes=2300 rx_total=286164
```

Freeze 1 ended the same way (`car_rx bytes=2300` ×6 at 19:10:57, then nothing), and so did freeze 2.

**Audio capture keeps running; the processing side has stopped.** When freeze 2 was left alone for several hours, the same process's log filled with:

```
2026-11-16 05:44:37.012 [+37759.255s] [WRN] [audio-cap] Buffer full in capture buffer!
```

about 100 lines per second, until it rotated the log past 20 MB (twice) and the process was stopped at 06:34:47. CPU while frozen was 0.2–0.27 s per 5 s, against about 2.5–3.0 s per 5 s for the healthy sending station. Killing the process and starting it again always recovered. The ini was unchanged, and the restarted copy logs no "Buffer full".

**Not related to:**
- running time (7.0 h, 1.8 h, 0.8 h after a fresh start);
- multiple instances on one card: we checked one `mercury-ui.exe` per station before each run, after finding duplicates earlier;
- the sending side: station 2 kept transmitting and logging normally each time.

**Not yet tried:** 1.9.24. Its changelog doesn't mention anything like this, but we'll retest on 1.9.24 if you think it might be fixed there. We can provide the full engine logs, Winlink logs and S:N recordings for the three sessions.
