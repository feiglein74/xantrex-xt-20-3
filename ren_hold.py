#!/usr/bin/env python3
"""Halten REN auf einem festen State, bis Strg-C.

Aufruf:
  python3 ren_hold.py on
  python3 ren_hold.py off

REN bleibt im jeweiligen State, solange das Skript laeuft. Strg-C zum beenden;
beim Ende wird REN released damit der Bus sauber bleibt.
"""

import sys
import gpib

if len(sys.argv) != 2 or sys.argv[1] not in ("on", "off"):
    print("Usage: python3 ren_hold.py [on|off]")
    sys.exit(1)

bd = gpib.find("gpib0")
state = 1 if sys.argv[1] == "on" else 0
gpib.remote_enable(bd, state)
print(f"REN = {'ON' if state else 'OFF'}")
print("Strg-C zum beenden (REN wird beim beenden released).")

try:
    while True:
        import time
        time.sleep(60)
except KeyboardInterrupt:
    gpib.remote_enable(bd, 0)
    print("\nREN released, Skript beendet.")
