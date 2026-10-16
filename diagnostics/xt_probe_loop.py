#!/usr/bin/env python3
"""Endlos-Probe alle 2s. Strg-C zum Beenden.

Sinn: User kann mit Oszi-Probe in einer Hand am 7210 messen, waehrend dieses
Skript automatisch Bus-Verkehr erzeugt. Pro Iteration: IFC + SDC an xt1 + REN.
Damit kommt regelmaessig ATN-Aktivitaet auf den Bus, und das XT (falls aktiv)
wuerde NDAC ziehen + INT signalisieren.
"""

import time
import Gpib
import gpib as _gpib

bd = _gpib.find("gpib0")
print("Loop-Probe alle 2s. Strg-C zum Beenden.\n")

i = 0
try:
    while True:
        i += 1
        try:
            _gpib.interface_clear(bd)
            time.sleep(0.05)
            _gpib.remote_enable(bd, 1)
            xt = Gpib.Gpib("xt1")
            xt.timeout(_gpib.T100ms)
            try:
                xt.clear()
                cs_ok = "ok"
            except _gpib.GpibError:
                cs_ok = "ERR"
            bits = _gpib.lines(bd)
            print(f"[{i:3d}] {time.strftime('%H:%M:%S')}  "
                  f"IFC+SDC -> {cs_ok}, "
                  f"NDAC={1 if bits & _gpib.BusNDAC else 0} "
                  f"ATN={1 if bits & _gpib.BusATN else 0} "
                  f"SRQ={1 if bits & _gpib.BusSRQ else 0}")
        except Exception as e:
            print(f"[{i:3d}] ERR: {type(e).__name__}: {e}")
        time.sleep(2.0)
except KeyboardInterrupt:
    print("\n[abgebrochen]")
