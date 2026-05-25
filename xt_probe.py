#!/usr/bin/env python3
"""Erstes Anklopfen am XT 20-3 ueber GPIB.

Schreibt KEIN Befehlsbyte (Befehlssatz noch unbekannt). Adressiert das Geraet
nur ueber Standard-IEEE-488-Mechanismen, bei denen die ADR-LED am XT angehen
muss, wenn PAD 5 + Bus stimmen:

  1) Serial Poll  -> adressiert XT als Talker, holt 1 Byte Statusbyte
  2) Selective Device Clear (SDC) -> adressiert XT als Listener, schickt SDC

Vor jedem Versuch: IFC, damit der Adapter nicht in einem haengenden ATN-State
aus einer vorigen Session sitzt (Pattern aus ngpv_diag.py).
"""

import time
import Gpib
import gpib as _gpib


LINES = [
    ("DAV",  _gpib.BusDAV),
    ("NDAC", _gpib.BusNDAC),
    ("NRFD", _gpib.BusNRFD),
    ("IFC",  _gpib.BusIFC),
    ("REN",  _gpib.BusREN),
    ("SRQ",  _gpib.BusSRQ),
    ("ATN",  _gpib.BusATN),
    ("EOI",  _gpib.BusEOI),
]


def show_lines(bd, label):
    bits = _gpib.lines(bd)
    s = " ".join(f"{n}={'1' if bits & m else '0'}" for n, m in LINES)
    print(f"  [{label:<22}] lines=0x{bits:04x}  {s}")


def main():
    print("=== XT 20-3 Probe (PAD 5) ===\n")

    bd = _gpib.find("gpib0")
    print(f"Board-Descriptor: {bd}")
    print(f"linux-gpib version: {_gpib.version()}\n")

    print("[Init] interface_clear()  (Adapter aus moeglichem Hang-Zustand holen)")
    _gpib.interface_clear(bd)
    time.sleep(0.2)
    show_lines(bd, "nach IFC")

    # --- Versuch 1: Serial Poll (adressiert als Talker, harmlos) ---
    print("\n[1] Serial Poll auf xt1")
    print("    Erwartung: ADR-LED am XT geht waehrend des Polls AN.")
    try:
        xt = Gpib.Gpib("xt1")
        xt.timeout(_gpib.T1s)
        sb = xt.serial_poll()
        print(f"    OK -> Statusbyte = 0x{sb:02x} ({sb:08b})")
        print(f"         ibsta=0x{xt.ibsta():04x}, ibcnt={xt.ibcnt()}")
    except _gpib.GpibError as e:
        print(f"    GpibError: {e}")
    except Exception as e:
        print(f"    {type(e).__name__}: {e}")
    show_lines(bd, "nach Serial Poll")

    _gpib.interface_clear(bd)
    time.sleep(0.2)

    # --- Versuch 2: Selective Device Clear (adressiert als Listener) ---
    # SDC ist IEEE-488-Standard und setzt ein konformes Geraet auf Defaults
    # zurueck. Da nur ein Multimeter (passiv) angeschlossen ist, kein DUT-Risiko.
    print("\n[2] Selective Device Clear (SDC) auf xt1")
    print("    Erwartung: ADR-LED geht kurz AN (Listener-Adressierung).")
    try:
        xt = Gpib.Gpib("xt1")
        xt.timeout(_gpib.T1s)
        xt.clear()
        print(f"    OK -> ibsta=0x{xt.ibsta():04x}")
    except _gpib.GpibError as e:
        print(f"    GpibError: {e}")
    except Exception as e:
        print(f"    {type(e).__name__}: {e}")
    show_lines(bd, "nach SDC")

    # --- Final: REN explizit setzen, damit das Geraet sicher in Remote ist ---
    # (DIP REMOTE haben wir auf OFF: Remote-Mode soll vom Controller kommen.)
    print("\n[3] remote_enable(1)  (Bus-REN aktivieren)")
    _gpib.remote_enable(bd, 1)
    time.sleep(0.1)
    show_lines(bd, "nach REN=1")

    print("\n=== fertig ===")
    print("Bitte beobachten am XT:")
    print("  - ADR-LED (gruen): muss waehrend Serial Poll und SDC AN gegangen sein.")
    print("  - ERR-LED (rot):   sollte AUS bleiben (wir haben keinen Befehl gesendet).")


if __name__ == "__main__":
    main()
