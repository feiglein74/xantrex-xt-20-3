#!/usr/bin/env python3
"""Probe mit verlangsamtem T1-Bus-Timing.

Default-T1 (Acceptor-Settle-Time) am 82357B ist 350ns. Manche aelteren
GPIB-Geraete brauchen 2us bis sie sicher sampeln. Wir setzen T1 hier auf
1 (= 2us) und versuchen Listener-Adressierung + Schreibversuch.
"""

import time
import Gpib
import gpib as _gpib

T1_DELAY_2000ns = 1
T1_DELAY_500ns  = 2
T1_DELAY_350ns  = 3


def main():
    bd = _gpib.find("gpib0")
    print(f"Board-Descriptor: {bd}")

    print("\nSetze T1-Delay auf 2us (langsamstes Timing, max. Kompatibilitaet)...")
    _gpib.config(bd, _gpib.IbcTIMING, T1_DELAY_2000ns)

    _gpib.interface_clear(bd)
    time.sleep(0.3)

    bits = _gpib.lines(bd)
    print(f"\nBus initial: lines=0x{bits:04x}  NDAC={1 if bits & _gpib.BusNDAC else 0}  ATN={1 if bits & _gpib.BusATN else 0}")

    xt = Gpib.Gpib("xt1")
    xt.timeout(_gpib.T1s)

    print("\n[1] SDC auf xt1")
    try:
        xt.clear()
        print(f"    OK   ibsta=0x{xt.ibsta():04x}")
    except _gpib.GpibError as e:
        print(f"    ERR  {e}")

    bits = _gpib.lines(bd)
    print(f"    Bus: lines=0x{bits:04x}")

    print("\n[2] Schreibversuch 'X' an xt1")
    try:
        xt.write(b"X\n")
        print(f"    OK   ibsta=0x{xt.ibsta():04x}, {xt.ibcnt()} Bytes")
    except _gpib.GpibError as e:
        print(f"    ERR  {e}")

    bits = _gpib.lines(bd)
    print(f"    Bus: lines=0x{bits:04x}")

    print("\nBeobachte ADR-LED am XT-Heck (waehrend SDC und Write).")
    print("Wenn jetzt was reagiert: T1-Timing war's.")


if __name__ == "__main__":
    main()
