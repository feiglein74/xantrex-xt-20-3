#!/usr/bin/env python3
"""Probe nach exaktem Manual-Beispiel (TM-9BGP-6HSN, S. 2-4 / S. 2-7).

Manual-Sequenz vor jedem Geraetekontakt:
  1) ibfind GPIB0
  2) ibsic            (Interface Clear / IFC)
  3) ibsre 1          (Assert REN)
  4) ibcmd "?_@\\x11" (UNL=0x3F, UNT=0x5F, MTA0=0x40, LLO=0x11)
  5) ibfind "xt1"
  6) ibwrt "..."

Wir hatten Schritt 4 (UNL/UNT/MTA0/LLO als Vorlauf) bisher nicht gemacht.
Vielleicht braucht die XT-Karte den Local-Lockout-Vorlauf, bevor
Listener-Adressierung scharf geschaltet wird.
"""

import time, ctypes
import Gpib
import gpib as _gpib

libgpib = ctypes.CDLL("/usr/lib/x86_64-linux-gnu/libgpib.so.0")
libgpib.ibcmd.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_long]
libgpib.ibcmd.restype = ctypes.c_int


def show(bd, label):
    bits = _gpib.lines(bd)
    s = " ".join(f"{n}={1 if bits & m else 0}" for n, m in [
        ("DAV",_gpib.BusDAV),("NDAC",_gpib.BusNDAC),("NRFD",_gpib.BusNRFD),
        ("IFC",_gpib.BusIFC),("REN",_gpib.BusREN),("SRQ",_gpib.BusSRQ),
        ("ATN",_gpib.BusATN),("EOI",_gpib.BusEOI)])
    print(f"  [{label:<22}] {s}")


def main():
    bd = _gpib.find("gpib0")
    print(f"Board-Descriptor: {bd}")

    # Schritt 2: IFC
    print("\n[2] interface_clear()")
    _gpib.interface_clear(bd)
    time.sleep(0.2)
    show(bd, "nach IFC")

    # Schritt 3: REN assertieren
    print("\n[3] remote_enable(1)")
    _gpib.remote_enable(bd, 1)
    time.sleep(0.1)
    show(bd, "nach REN=1")

    # Schritt 4: ibcmd "?_@\x11" = UNL UNT MTA0 LLO
    print("\n[4] ibcmd UNL+UNT+MTA0+LLO  (Manual-Vorlauf)")
    cmd_bytes = bytes([0x3F, 0x5F, 0x40, 0x11])
    rc = libgpib.ibcmd(bd, cmd_bytes, len(cmd_bytes))
    print(f"    rc = 0x{rc:08x}")
    show(bd, "nach LLO-Vorlauf")

    # Schritt 5+6: device adressieren und schreiben
    print("\n[5/6] Schreibversuch 'X' an xt1")
    xt = Gpib.Gpib("xt1")
    xt.timeout(_gpib.T1s)
    try:
        xt.write(b"X\n")
        print(f"    OK   ibsta=0x{xt.ibsta():04x}, {xt.ibcnt()} Bytes")
    except _gpib.GpibError as e:
        print(f"    ERR  {e}")
    show(bd, "nach Write")


if __name__ == "__main__":
    main()
