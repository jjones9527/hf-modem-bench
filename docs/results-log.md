# Results log

A running record of every campaign: what was run, what happened, and what we
learned from it. Each entry is written when the run's logs have been checked.
This file is the lab notebook. The numbers in the final report are computed
again from the raw files.

**Raw data.** `scripts/archive-bench.sh` copies everything from the bench
machine into `logs/archive/` (gitignored). That covers each campaign's run sheet,
events, manifest and console output, the S:N recordings (`listen-*.json`), the
tone checks, and both stations' Winlink and ARDOP logs. Run it after every
campaign. All times are UTC.

**Stations.** Station 1 is VA3ZTF (`C:\RMS Express`) and station 2 is VE3XZQ
(`C:\RMS Express 2`). Station 2 always places the call. Adapters: until 11 Nov
station 1 used the Sabrent and station 2 the Syba; **from wgn25a (12 Nov) on they are
swapped** (station 1 Syba/C-Media, station 2 Sabrent), for every modem since.

**Workload.** Until 12 Nov: the Text_50KB set (sha256 `3ec10a0b…279f9`), 5 messages
from each station, each with one 51,200-byte attachment (about 42,100 bytes on the
wire). **From 13 Nov (oneway28 on): one way, 10 messages from station 2 to station 1,**
Text_50KB at 10 dB and above and Text_5KB (`85741279…384d4`) below, with a 60-min time
box per run.

**Goodput.** Compressed (FC EM) bytes × 8 divided by the message's transfer time.
Until 13 Nov from the sender's Winlink log; **from 13 Nov from the receiver's**, which
excludes the ~20 s handover and reads about 10% higher (test-plan.md).

**VARA-protocol modems** (Mercury from 15 Nov) run with station 2's Winlink behind the
bench relay, which holds Winlink Express's 5-min P2P inactivity DISCONNECT (D6).

## Where the entries are

Split by stage on 27 Nov 2026, so a session reads only the stage it needs. Section titles are unchanged: a reference such as *results-log.md, "Stage 1 summary"* is found by searching `docs/results/` for the quoted title.

| Stage | File | Sections |
| --- | --- | --- |
| Bench calibration and pilots (10–13 Nov 2026) | [0-calibration-and-pilots.md](results/0-calibration-and-pilots.md) | Bench calibration; pilot01; swap01; swap02; wgn25a; qam01; qam02; cal; cal6wgn14; cal7; cal7wgn22; cal7wgn28; oneway28; ARDOP 1.0.2.9 source; oneway28 0003 and oneway28r; Planned next |
| Stage 1: ARDOP 1.0.2.9, white noise | [1-ardop-wgn.md](results/1-ardop-wgn.md) | Stage 1 |
| Stage 2: Mercury 1.9.23 / 1.9.24 | [2-mercury.md](results/2-mercury.md) | Stage 2 |
| Stage 2b: Data2G 0.5.1, white noise | [2b-data2g-wgn.md](results/2b-data2g-wgn.md) | Stage 2b |
| Stage 3: VARA HF 4.9.1, white noise | [3-vara-hf-wgn.md](results/3-vara-hf-wgn.md) | Stage 3 |
| Stage 4: ARDOP 1.0.3.3 development build | [4-ardop-1.0.3.3.md](results/4-ardop-1.0.3.3.md) | Stage 4 |
| Stage 5: ULTRA 0.6.2 (paused) | [5-ultra.md](results/5-ultra.md) | Stage 5 |
| Stage 6: Aether HF; Modem73; white-noise stage complete | [6-aether-modem73-wgn-complete.md](results/6-aether-modem73-wgn-complete.md) | Stage 6; Modem73 2.5.0; White-noise stage complete |
| Stage 7: fading (MPG, MPM, MPP) | [7-fading.md](results/7-fading.md) | Stage 7 |

**Adding an entry:** append it to the file of the stage in progress (now [results/7-fading.md](results/7-fading.md)). When a new stage starts, create the next numbered file and add its row here.
