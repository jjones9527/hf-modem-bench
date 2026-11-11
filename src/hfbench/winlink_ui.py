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
  python -m hfbench.winlink_ui LOG CALL folders | select-folder NAME | export PATH | import PATH
"""

from __future__ import annotations

import re
import sys
import threading
import time
from dataclasses import dataclass


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
    def main(self):
        for w in self.auto.GetRootControl().GetChildren():
            n = w.Name or ""
            if w.ControlTypeName == "WindowControl" and "Winlink Express" in n and f"- {self.call}" in n:
                return w
        raise RuntimeError(f"Winlink Express main window for {self.call} not found")

    def session_window(self):
        for w in self.auto.GetRootControl().GetChildren():
            n = w.Name or ""
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

    def _dialogs(self, main):
        return [w for w in self.auto.GetRootControl().GetChildren()
                if w.ProcessId == main.ProcessId and "Winlink Express" not in (w.Name or "")
                and "Peer-to-Peer" not in (w.Name or "")]

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

    # -- import --------------------------------------------------------------------
    def import_xml(self, path: str) -> str:
        """Import messages via Message > Import messages; returns the summary text."""
        main = self.main()
        dlg = self.auto.WindowControl(AutomationId="DialogImportMessagesFileName", searchDepth=1)
        if not dlg.Exists(0.5):
            self._menu(main, "Message", "Import messages")
            if not dlg.Exists(30):
                raise RuntimeError("import dialog did not appear")
        dlg.EditControl(AutomationId="txtFileName").GetValuePattern().SetValue(path)
        self._thread(lambda: dlg.ButtonControl(AutomationId="btnImport").GetInvokePattern().Invoke())
        texts = self._close_info_boxes(main) + self._close_info_boxes(main, wait=0.5)
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
    else:
        raise SystemExit(f"unknown action {action}")
    say("folders:", ui.folder_counts())


if __name__ == "__main__":
    _main(sys.argv[1:])
