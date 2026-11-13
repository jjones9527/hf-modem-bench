"""Winlink Express window automation (Windows desktop session only).

Needs the `uiautomation` package. Verified against Winlink Express 1.8.6.0 on
10-11 Nov 2026 (folders, export, import, P2P session window).

Notes from the bench:
- Menus are opened with the LegacyIAccessible default action; WinForms
  MenuStrip items don't support Expand.
- An action that opens a modal dialog blocks its UIA call until the dialog
  closes (about 60 s, then a harmless COMError), so such calls run in a thread.
- Selecting a folder needs LegacyIAccessible Select + DoDefaultAction;
  SelectionItem.Select alone doesn't refresh the message list.
- The session window's channel bar: the first edit box holds the callsign to
  call. The status bar reads 'In: a/b  Out: c/d  BPM: n' and
  'Connected - In sending state' / 'Disconnected/Listening'.

Run as a script for one-off actions:
  python -m hfbench.winlink_ui LOG CALL folders | select-folder NAME | import PATH | status
                                 | delete-outbox | close-session | close | open-session [TYPE] | launch INSTALL
"""

from __future__ import annotations

import re
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path


def _auto():
    import uiautomation as auto  # imported lazily: Windows only
    return auto


@dataclass
class SessionStatus:
    connected: bool
    state: str          # e.g. 'Connected - In sending state', 'Disconnected/Listening'
    counters: str       # 'In: a/b  Out: c/d  BPM: n'
    can_start: bool
    can_abort: bool
    target: str


class WinlinkUI:
    """Controls one Winlink Express instance, identified by its callsign."""

    def __init__(self, call: str, log=print):
        self.call = call
        self.log = log
        self.auto = _auto()

    # -- windows -----------------------------------------------------------------
    def _top_windows(self):
        """(window, name, control type) for every readable top-level window. A window
        that is closing can refuse access (COMError 'Access is denied'); skip it."""
        out = []
        for w in self.auto.GetRootControl().GetChildren():
            try:
                out.append((w, w.Name or "", w.ControlTypeName))
            except Exception:
                continue
        return out

    def main(self):
        for w, n, kind in self._top_windows():
            if kind == "WindowControl" and "Winlink Express" in n and f"- {self.call}" in n:
                return w
        raise RuntimeError(f"Winlink Express main window for {self.call} not found")

    def session_window(self):
        for w, n, _ in self._top_windows():
            if "Peer-to-Peer Session" in n and n.rstrip().endswith(f"- {self.call}"):
                return w
        raise RuntimeError(f"no Peer-to-Peer Session window open for {self.call}")

    def _thread(self, fn):
        auto = self.auto

        def run():
            with auto.UIAutomationInitializerInThread():
                try:
                    fn()
                except Exception as e:  # blocked-modal COMError is expected
                    self.log(f"  (ui call returned {type(e).__name__})")
        t = threading.Thread(target=run, daemon=True)
        t.start()
        return t

    def _menu(self, main, top: str, item: str):
        main.MenuItemControl(Name=top, searchDepth=3).GetLegacyIAccessiblePattern().DoDefaultAction()
        time.sleep(1.0)
        for w in [main] + [x for x in self.auto.GetRootControl().GetChildren() if x.ProcessId == main.ProcessId]:
            c = w.MenuItemControl(Name=item, searchDepth=6)
            if c.Exists(0.5):
                return self._thread(lambda: c.GetLegacyIAccessiblePattern().DoDefaultAction())
        raise RuntimeError(f"menu item {item!r} not found")

    def _child_windows(self, main):
        """Dialogs owned by the main window can appear as its children (seen in an
        instance started by the recovery) rather than as top-level windows."""
        out = []
        try:
            for c in main.GetChildren():
                try:
                    if c.ControlTypeName == "WindowControl":
                        out.append(c)
                except Exception:
                    continue
        except Exception:
            pass
        return out

    def _dialogs(self, main):
        out = []
        for w in list(self.auto.GetRootControl().GetChildren()) + self._child_windows(main):
            try:
                n = w.Name or ""
                if w.ProcessId == main.ProcessId and "Winlink Express" not in n and "Peer-to-Peer" not in n:
                    out.append(w)
            except Exception:
                continue
        return out

    def _texts(self, w):
        return [c.Name for c, d in self.auto.WalkControl(w, maxDepth=4)
                if c.ControlTypeName == "TextControl" and c.Name]

    def _close_info_boxes(self, main, wait: float = 3.0) -> list[str]:
        """Press OK on any message boxes; return their texts."""
        time.sleep(wait)
        seen = []
        for w in self._dialogs(main):
            seen += self._texts(w)
            ok = w.ButtonControl(Name="OK", searchDepth=3)
            if ok.Exists(0.3):
                self._thread(lambda: ok.GetInvokePattern().Invoke())
                time.sleep(1)
        return seen

    # -- folders -----------------------------------------------------------------
    def folder_counts(self) -> dict[str, int]:
        out = {}
        for it in self.main().ListControl(AutomationId="lstFixedFolders").GetChildren():
            m = re.match(r"(.+?)\s+\((\d+)", it.Name or "")
            if m:
                out[m.group(1).strip()] = int(m.group(2))
        return out

    def select_folder(self, name: str) -> None:
        main = self.main()
        item = next(i for i in main.ListControl(AutomationId="lstFixedFolders").GetChildren()
                    if (i.Name or "").startswith(name))
        acc = item.GetLegacyIAccessiblePattern()
        acc.Select(1 | 2)
        time.sleep(0.3)
        try:
            acc.DoDefaultAction()
        except Exception:
            pass
        time.sleep(1.0)

    def folder_mids(self, name: str) -> list[str]:
        """Message IDs listed in a folder (selects the folder)."""
        self.select_folder(name)
        mids = []
        grid = self.main().TableControl(AutomationId="grdMessageList")
        for r in grid.GetChildren():
            if not (r.Name or "").startswith("Row "):
                continue
            for c in r.GetChildren():
                if (c.Name or "").startswith("Message ID"):
                    try:
                        v = c.GetValuePattern().Value
                    except Exception:
                        v = ""
                    if v:
                        mids.append(v)
        return mids

    # -- import --------------------------------------------------------------------
    def _own_dialog(self, automation_id: str):
        """A dialog with this AutomationId belonging to *this* instance's process."""
        main = self.main()
        pid = main.ProcessId
        # A dialog is usually a top-level window, but in an instance started by the
        # recovery (via a scheduled task) it appears as a child of the main window.
        for w in list(self.auto.GetRootControl().GetChildren()) + list(main.GetChildren()):
            try:
                if w.AutomationId == automation_id and w.ProcessId == pid:
                    return w
            except Exception:
                continue
        return None

    def import_xml(self, path: str) -> str:
        """Import messages via Message > Import messages; returns the summary text.
        Waits for the menu call to finish: a blocked call (about 60 s) delays
        any later UI call, even in the other Winlink instance."""
        main = self.main()
        menu_thread = None
        dlg = self._own_dialog("DialogImportMessagesFileName")
        if dlg is None:
            menu_thread = self._menu(main, "Message", "Import messages")
            t0 = time.time()
            while dlg is None and time.time() - t0 < 120:
                time.sleep(1)
                dlg = self._own_dialog("DialogImportMessagesFileName")
            if dlg is None:
                raise RuntimeError("import dialog did not appear within 120 s")
        dlg.EditControl(AutomationId="txtFileName").GetValuePattern().SetValue(path)
        self._thread(lambda: dlg.ButtonControl(AutomationId="btnImport").GetInvokePattern().Invoke())
        texts = self._close_info_boxes(main) + self._close_info_boxes(main, wait=0.5)
        if menu_thread is not None:
            menu_thread.join(90)
        summary = " ".join(texts)
        m = re.search(r"Number of messages imported = (\d+)", summary)
        if not m:
            raise RuntimeError(f"import result not recognised: {summary[:200]!r}")
        return summary

    # -- P2P session -----------------------------------------------------------------
    def status(self) -> SessionStatus:
        w = self.session_window()
        bar_texts = [c.Name for c in w.StatusBarControl(AutomationId="barStatus").GetChildren()
                     if c.ControlTypeName == "TextControl" and c.Name]
        counters = next((t for t in bar_texts if t.startswith("In:")), "")
        state = next((t for t in bar_texts if "Connected" in t or "Disconnected" in t or "Listening" in t), "")
        edits = [c for c in w.MenuBarControl(AutomationId="mnuChannel").GetChildren()
                 if c.ControlTypeName == "EditControl"]
        edits.sort(key=lambda c: c.BoundingRectangle.left)
        target = edits[0].GetValuePattern().Value if edits else ""
        mi = lambda n: w.MenuItemControl(Name=n, searchDepth=3)
        return SessionStatus(state.startswith("Connected"), state, counters,
                             mi("Start").IsEnabled, mi("Abort").IsEnabled, target)

    def start(self, expect_target: str) -> None:
        st = self.status()
        if st.target.strip().upper() != expect_target.upper():
            raise RuntimeError(f"session window for {self.call} would call {st.target!r}, expected {expect_target!r}")
        if not st.can_start:
            raise RuntimeError(f"Start is not enabled in {self.call}'s session window ({st.state!r})")
        w = self.session_window()
        self._thread(lambda: w.MenuItemControl(Name="Start", searchDepth=3).GetLegacyIAccessiblePattern().DoDefaultAction())
        self.log(f"Start pressed in {self.call}'s session window (calling {expect_target})")

    def abort(self) -> None:
        w = self.session_window()
        item = w.MenuItemControl(Name="Abort", searchDepth=3)
        if item.IsEnabled:
            self._thread(lambda: item.GetLegacyIAccessiblePattern().DoDefaultAction())
            self.log(f"Abort pressed in {self.call}'s session window")

    # -- recovery: the operator's reset, step by step ---------------------------------
    # The operator's procedure (12 Nov 2026): select every Outbox message, press
    # Delete, close the session window, close Winlink Express, start it again and open
    # the Ardop P2P session (the ARDOP TNC starts with it). Control names come from
    # the UI survey of 11 Nov 2026 and still need a live trial (see docs).

    def has_session_window(self) -> bool:
        try:
            self.session_window()
            return True
        except RuntimeError:
            return False

    def has_main_window(self) -> bool:
        try:
            self.main()
            return True
        except RuntimeError:
            return False

    def _press_confirmations(self, pid: int, wait: float = 2.0, names=("Yes", "OK")) -> list[str]:
        """Answer confirmation boxes of this instance with Yes/OK; return their texts."""
        time.sleep(wait)
        seen = []
        extra = []
        if self.has_main_window():
            extra = [(c, c.Name or "", "WindowControl") for c in self._child_windows(self.main())]
        for w, n, _ in self._top_windows() + extra:
            try:
                if w.ProcessId != pid or "Winlink Express" in n or "Peer-to-Peer" in n:
                    continue
            except Exception:
                continue
            seen += self._texts(w)
            for b in names:
                btn = w.ButtonControl(Name=b, searchDepth=3)
                if btn.Exists(0.3):
                    self._thread(lambda btn=btn: btn.GetInvokePattern().Invoke())
                    time.sleep(1)
                    break
        return seen

    def delete_folder_messages(self, name: str = "Outbox", attempts: int = 3) -> list[str]:
        """Select every message in a folder and press Delete (they go to Deleted
        Items, as when the operator does it). Returns the MIDs that were there."""
        before = self.folder_mids(name)
        if not before:
            return []
        for _ in range(attempts):
            main = self.main()
            rows = [r for r in main.TableControl(AutomationId="grdMessageList").GetChildren()
                    if (r.Name or "").startswith("Row ")]
            for i, r in enumerate(rows):
                # SELFLAG_TAKEFOCUS|TAKESELECTION for the first row, ADDSELECTION for the rest
                r.GetLegacyIAccessiblePattern().Select(3 if i == 0 else 8)
                time.sleep(0.1)
            t = self._thread(lambda: main.MenuItemControl(Name="Delete", searchDepth=3)
                             .GetLegacyIAccessiblePattern().DoDefaultAction())
            texts = self._press_confirmations(main.ProcessId)
            t.join(90)
            if texts:
                self.log(f"  {self.call}: Delete asked: {' '.join(texts)[:120]!r}")
            left = self.folder_mids(name)
            if not left:
                self.log(f"{self.call}: deleted {len(before)} message(s) from {name}")
                return before
        raise RuntimeError(f"{self.call}: {name} still has {len(left)} message(s) after Delete")

    def close_session_window(self, timeout: float = 30) -> None:
        if not self.has_session_window():
            return
        w = self.session_window()
        self._thread(lambda: w.MenuItemControl(Name="Exit", searchDepth=3).GetLegacyIAccessiblePattern().DoDefaultAction())
        t0 = time.time()
        while self.has_session_window():
            if time.time() - t0 > timeout:
                raise RuntimeError(f"{self.call}: session window did not close within {timeout:.0f} s")
            self._press_confirmations(w.ProcessId, wait=1.0)
        self.log(f"{self.call}: session window closed")

    def close_main(self, timeout: float = 60) -> bool:
        """Close Winlink Express normally. False if it is still open after timeout."""
        if not self.has_main_window():
            return True
        main = self.main()
        pid = main.ProcessId
        self._thread(lambda: main.GetWindowPattern().Close())
        t0 = time.time()
        while self.has_main_window():
            if time.time() - t0 > timeout:
                return False
            self._press_confirmations(pid, wait=1.0)
        self.log(f"{self.call}: Winlink Express closed")
        return True

    def wait_main(self, timeout: float = 120) -> None:
        t0 = time.time()
        while not self.has_main_window():
            if time.time() - t0 > timeout:
                raise RuntimeError(f"{self.call}: Winlink Express window did not appear within {timeout:.0f} s")
            time.sleep(2)
        time.sleep(5)   # let it finish loading folders

    def open_session(self, session_type: str = "Ardop P2P", timeout: float = 90) -> SessionStatus:
        """Open a P2P session from the main window ('Open Session:' with
        `session_type` selected next to it) and wait until Start is enabled.
        Verified for 'Ardop P2P' (12 Nov 2026). For VARA-type modems the session
        type is expected to be 'Vara HF P2P'; confirm at each modem's bring-up.
        The session type is not changed here: select it once by hand per install."""
        if not self.has_session_window():
            main = self.main()
            if not main.MenuItemControl(Name=session_type, searchDepth=3).Exists(1):
                raise RuntimeError(f"{self.call}: session type {session_type!r} is not selected in the main window")
            self._thread(lambda: main.MenuItemControl(Name="Open Session:", searchDepth=3)
                         .GetLegacyIAccessiblePattern().DoDefaultAction())
        t0 = time.time()
        while True:
            if time.time() - t0 > timeout:
                raise RuntimeError(f"{self.call}: {session_type} session not ready within {timeout:.0f} s")
            time.sleep(2)
            if not self.has_session_window():
                continue
            try:
                st = self.status()
            except Exception:
                continue
            if st.can_start and not st.connected:
                self.log(f"{self.call}: {session_type} session open ({st.state or 'ready'})")
                return st

    def open_ardop_p2p(self, timeout: float = 90) -> SessionStatus:
        return self.open_session("Ardop P2P", timeout)


class WinlinkProcesses:
    """Start, find and (last resort) stop one station's processes: its Winlink
    Express and the modem TNC that Winlink started (ARDOP_Win.exe in the install,
    or a VARA-type program elsewhere), each identified by its full executable path."""

    def __init__(self, run=None, tnc_exes: dict[str, str] | None = None):
        """tnc_exes maps an install folder to its TNC's full path; default
        <install>\\ARDOP_Win.exe."""
        import subprocess
        self._run = run or (lambda args: subprocess.run(args, capture_output=True, text=True, timeout=60).stdout)
        self.tnc_exes = tnc_exes or {}

    def _ps(self, script: str) -> str:
        return self._run(["powershell", "-NoProfile", "-Command", script])

    def paths(self, install: str) -> list[str]:
        return [str(Path(install) / "RMS Express.exe"),
                self.tnc_exes.get(str(install), str(Path(install) / "ARDOP_Win.exe"))]

    def pids(self, install: str) -> dict[str, list[int]]:
        out = {}
        for path in self.paths(install):
            exe = Path(path).name.replace("'", "''")
            q = path.replace("'", "''")
            txt = self._ps(f"Get-CimInstance Win32_Process -Filter \"Name='{exe}'\" | "
                           f"Where-Object {{ $_.ExecutablePath -eq '{q}' }} | ForEach-Object {{ $_.ProcessId }}")
            out[path] = [int(x) for x in txt.split() if x.strip().isdigit()]
        return out

    def running(self, install: str) -> bool:
        return any(self.pids(install).values())

    def kill(self, install: str) -> list[int]:
        killed = [p for v in self.pids(install).values() for p in v]
        for p in killed:
            self._run(["taskkill", "/PID", str(p), "/F"])
        return killed

    def launch(self, install: str) -> None:
        """Start Winlink Express through its own scheduled task in the desktop session,
        so it isn't a child of the runner: Task Scheduler can kill a task's child
        processes when that task ends or is stopped."""
        exe = str(Path(install) / "RMS Express.exe").replace("'", "''")
        wd = str(install).replace("'", "''")
        name = "hfbench_winlink_" + "".join(c for c in Path(install).name if c.isalnum())
        self._ps(
            f"$a = New-ScheduledTaskAction -Execute '{exe}' -WorkingDirectory '{wd}'; "
            "$p = New-ScheduledTaskPrincipal -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) "
            "-LogonType Interactive; "
            "$s = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -AllowStartIfOnBatteries "
            "-DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew; "
            f"Register-ScheduledTask -TaskName '{name}' -Action $a -Principal $p -Settings $s -Force | Out-Null; "
            f"Start-ScheduledTask -TaskName '{name}'")


def _main(argv: list[str]) -> None:
    logf = open(argv[0], "a", encoding="utf-8")
    say = lambda *a: (logf.write(" ".join(str(x) for x in a) + "\n"), logf.flush())
    ui = WinlinkUI(argv[1], log=say)
    action, args = argv[2], argv[3:]
    if action == "folders":
        say(ui.folder_counts())
    elif action == "select-folder":
        ui.select_folder(args[0])
    elif action == "import":
        say(ui.import_xml(args[0]))
    elif action == "status":
        say(ui.status())
    elif action == "delete-outbox":
        say("deleted:", ui.delete_folder_messages("Outbox"))
    elif action == "close-session":
        ui.close_session_window()
    elif action == "close":
        ui.close_session_window()
        say("closed:", ui.close_main())
        return
    elif action == "open-session":             # optional arg: session type (default Ardop P2P)
        say(ui.open_session(args[0] if args else "Ardop P2P"))
    elif action == "launch":                  # args: install folder
        WinlinkProcesses().launch(args[0])
        ui.wait_main()
        say(f"{ui.call}: Winlink Express started")
    else:
        raise SystemExit(f"unknown action {action}")
    say("folders:", ui.folder_counts())


if __name__ == "__main__":
    _main(sys.argv[1:])
