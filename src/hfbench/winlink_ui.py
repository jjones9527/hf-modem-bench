"""Winlink Express window automation (Windows desktop session only; needs
the `uiautomation` package). Verified on Winlink Express 1.8.6.0, 11 Nov 2026.
Menu actions that open a modal dialog block for about 60 s before returning a
harmless COMError; they run in a thread. Usage (run as a script):
  ui_tool.py LOG CALL select-folder "Sent Items"
  ui_tool.py LOG CALL export PATH          (exports the selected row 0)
  ui_tool.py LOG CALL import PATH
  ui_tool.py LOG CALL folders              (folder names + counts)
"""
import os, sys, threading, time
import uiautomation as auto

log = open(sys.argv[1], "a", encoding="utf-8")
def say(*a):
    log.write(" ".join(str(x) for x in a) + "\n"); log.flush()

CALL, ACTION, ARGS = sys.argv[2], sys.argv[3], sys.argv[4:]

def find_main():
    for w in auto.GetRootControl().GetChildren():
        n = w.Name or ""
        if w.ControlTypeName == "WindowControl" and "Winlink Express" in n and f"- {CALL}" in n:
            return w
    raise SystemExit(f"main window for {CALL} not found")

def folders(main):
    out = []
    for lst in ("lstFixedFolders",):
        for it in main.ListControl(AutomationId=lst).GetChildren():
            out.append(it.Name)
    return out

def grid_rows(main, n=6):
    rows = []
    grid = main.TableControl(AutomationId="grdMessageList")
    for r in grid.GetChildren():
        if not (r.Name or "").startswith("Row "):
            continue
        cells = {}
        for c in r.GetChildren():
            key = (c.Name or "").rsplit(" Row ", 1)[0]
            try:
                cells[key] = c.GetValuePattern().Value
            except Exception:
                pass
        rows.append({k: cells.get(k) for k in ("Date/Time", "Message ID", "Size", "Sender", "Recipient", "Subject")})
        if len(rows) >= n:
            break
    return rows

def select_folder(main, name):
    item = next(i for i in main.ListControl(AutomationId="lstFixedFolders").GetChildren() if (i.Name or "").startswith(name))
    acc = item.GetLegacyIAccessiblePattern()
    acc.Select(1 | 2)          # SELFLAG_TAKEFOCUS | SELFLAG_TAKESELECTION
    time.sleep(0.3)
    try:
        acc.DoDefaultAction()
    except Exception as e:
        say("default action:", type(e).__name__)
    time.sleep(1.5)
    say("grid after selecting", repr(name), ":", grid_rows(main, 3))

def in_thread(fn):
    def run():
        with auto.UIAutomationInitializerInThread():
            try:
                fn()
            except Exception as e:
                say("threaded call returned:", type(e).__name__, str(e)[:80])
    t = threading.Thread(target=run, daemon=True); t.start(); return t

def menu(main, top, item_name):
    m = main.MenuItemControl(Name=top, searchDepth=3)
    m.GetLegacyIAccessiblePattern().DoDefaultAction()
    time.sleep(1.0)
    for w in [main] + [x for x in auto.GetRootControl().GetChildren() if x.ProcessId == main.ProcessId]:
        c = w.MenuItemControl(Name=item_name, searchDepth=6)
        if c.Exists(0.5):
            return in_thread(lambda: c.GetLegacyIAccessiblePattern().DoDefaultAction())
    raise SystemExit(f"menu item {item_name!r} not found")

def other_windows(main):
    return [w for w in auto.GetRootControl().GetChildren()
            if w.ProcessId == main.ProcessId and "Winlink Express" not in (w.Name or "")
            and "Peer-to-Peer" not in (w.Name or "")]

def texts(w):
    return [c.Name for c, d in auto.WalkControl(w, maxDepth=4) if c.ControlTypeName == "TextControl" and c.Name]

def press_ok_boxes(main, wait=4):
    time.sleep(wait)
    for w in other_windows(main):
        say("dialog:", repr(w.Name), "texts:", texts(w))
        for b in ("OK", "Yes"):
            btn = w.ButtonControl(Name=b, searchDepth=3)
            if btn.Exists(0.3):
                in_thread(lambda: btn.GetInvokePattern().Invoke()); say("pressed", b); time.sleep(1); break

main = find_main()
say(f"== {ACTION} {ARGS} on {main.Name!r}")
if ACTION == "folders":
    say(folders(main))
elif ACTION == "select-folder":
    select_folder(main, ARGS[0])
elif ACTION == "export":
    path = ARGS[0]
    grid = main.TableControl(AutomationId="grdMessageList")
    row0 = next(r for r in grid.GetChildren() if r.Name == "Row 0")
    row0.GetLegacyIAccessiblePattern().Select(2)
    time.sleep(0.8)
    t = menu(main, "Message", "Export selected messages")
    dlg = auto.WindowControl(AutomationId="DialogExportMessagesFileName", searchDepth=1)
    if not dlg.Exists(10):
        raise SystemExit("export dialog did not appear")
    say("dialog:", texts(dlg))
    dlg.EditControl(AutomationId="txtFileName").GetValuePattern().SetValue(path)
    in_thread(lambda: dlg.ButtonControl(AutomationId="btnExport").GetInvokePattern().Invoke())
    press_ok_boxes(main)
elif ACTION == "import":
    path = ARGS[0]
    dlg = auto.WindowControl(AutomationId="DialogImportMessagesFileName", searchDepth=1)
    if not dlg.Exists(1):
        menu(main, "Message", "Import messages")
        if not dlg.Exists(90):
            raise SystemExit("import dialog did not appear")
    dlg.EditControl(AutomationId="txtFileName").GetValuePattern().SetValue(path)
    say("path set:", dlg.EditControl(AutomationId="txtFileName").GetValuePattern().Value)
    in_thread(lambda: dlg.ButtonControl(AutomationId="btnImport").GetInvokePattern().Invoke())
    press_ok_boxes(main)
    press_ok_boxes(main, wait=1)
    select_folder(main, "Outbox")
say("folders now:", folders(main))
log.close()
