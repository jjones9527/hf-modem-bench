# Winlink Express P2P 5-minute inactivity timer (comment on Mercury #392)

Posted 16 Nov 2026 on [Rhizomatica/mercury#392](https://github.com/Rhizomatica/mercury/issues/392#issuecomment-6916600618). Background in [results-log.md](../results-log.md), "Relay trace". Text as posted:

---

This looks like a client-side timer in Winlink Express, as suggested above. We reproduced it on a bench (two Winlink Express 1.8.6.0 instances, "Vara HF P2P" sessions, IONOS simulator) with Mercury 1.9.23 and with VARA HF 4.09. We put a logging TCP relay between the sending Winlink and its modem to see both ports.

**What happens.** Winlink Express writes the whole message to the data port in one go (about 42 KB here). In a P2P session it then sends `DISCONNECT` exactly 5 minutes after that write, logging `P2P session inactivity timeout. Disconnecting.`, even though the modem is still sending. `BUFFER`, `PTT`, `BITRATE` and `SN` lines don't reset the timer. Excerpt from the relay log (Mercury 1.9.23, sender side, UTC):

```
13:58:29.196 DAT host>modem 42527 bytes
13:58:29.643 CTL modem>host BUFFER 42527
14:00:39.832 CTL modem>host BUFFER 31027
14:02:16.298 CTL modem>host BUFFER 19527
14:03:13.997 CTL modem>host BUFFER 12627
14:03:29.250 CTL host>modem DISCONNECT
14:03:29.250 CTL modem>host OK
14:03:29.365 CTL modem>host DISCONNECTED
```

1.9.23 answered `DISCONNECTED` straight away and then finished sending on the air. The receiver got the whole message, but the sender never saw the receipt, so the message stayed in its Outbox and the session ended.

**VARA HF does the same, just later.** With VARA 4.09, Winlink also wrote the whole message at once and sent `DISCONNECT` 5:00 later, then again every 5 minutes. VARA answered only `OK` and kept sending until its buffer was empty, then disconnected about 2 s after the last byte was acknowledged. The receiver stored the message and sent `FF`, which never reached the sender, so the result was the same: the message was delivered but stayed in the sender's Outbox, and the session ended. So any message that takes more than 5 minutes to send ends a Winlink Express P2P session, whichever VARA-protocol modem is used. ARDOP sessions in the same setup are not affected. 1.9.24's #493 (DISCONNECTED only when the session has closed) makes Mercury behave like VARA here, which delays the end but doesn't avoid it.

**Workaround we use on the bench.** The relay answers that one `DISCONNECT` with `OK` itself and doesn't pass it on, when the host hasn't written to the data port for 4 minutes. Winlink then carries on normally ("Completed send", next message), and a real end-of-session `DISCONNECT` (sent seconds after the host's last write) still goes through. With it, Mercury ran full one-hour sessions of 50 KB messages. The relay is a small Python script, if it's useful to anyone: https://github.com/jjones9527/hf-modem-bench/blob/phase1-scaffold/scripts/vara_relay.py

We didn't find a setting in Winlink Express for this timer.
