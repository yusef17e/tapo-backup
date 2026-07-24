"""Print clickable/labeled elements on the emulator's current screen.
Run after each manual step in the Tapo app (open camera, tap Playback, etc.)
to find the resourceId/text/description needed for backup/tapo_app.py TODOs.

Usage: python dump_ui.py [screenshot_name.png]
"""
import sys
import uiautomator2 as u2

d = u2.connect("127.0.0.1:5555")
d.screenshot(sys.argv[1] if len(sys.argv) > 1 else "screen.png")

for el in d.xpath("//*").all():
    info = el.info
    text = info.get("text") or info.get("contentDescription") or ""
    rid = info.get("resourceId") or ""
    if text or rid:
        print(f"{info['bounds']}  text={text!r}  resourceId={rid!r}")
