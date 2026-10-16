#!/usr/bin/env python3
"""Passiver Bus-Beobachter.

Sampelt die GPIB-Steuerleitungen ueber 15s mit hoher Rate und meldet jede
Aenderung. Idee: waehrend das Skript laeuft, schaltet der Anwender das XT
aus und wieder ein. Wenn die GPIB-Karte aktiv ist und PON SRQ enabled
(PON-DIP=OFF), muss die SRQ-Linie kurz nach dem Power-On asserten.

Schreibt nichts auf den Bus. Setzt nur einmal IFC am Anfang, damit der
Adapter aus einem moeglichen Hang-Zustand startet, dann Read-only.
"""

import time
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


def state_of(bits):
    return tuple(bool(bits & m) for _, m in LINES)


def fmt_state(state):
    return " ".join(f"{n}={'1' if v else '0'}" for (n, _), v in zip(LINES, state))


def main():
    DURATION_S = 15.0

    bd = _gpib.find("gpib0")
    print(f"Board-Descriptor: {bd}")

    _gpib.interface_clear(bd)
    time.sleep(0.2)

    print(f"\nBeobachte Bus-Linien {DURATION_S:.0f}s lang.")
    print("=> JETZT das XT aus- und nach 2-3s wieder einschalten.\n")

    t0 = time.time()
    last = None
    last_t = t0
    samples = 0
    transitions = 0
    srq_seen = False

    while time.time() - t0 < DURATION_S:
        bits = _gpib.lines(bd)
        state = state_of(bits)
        samples += 1
        if state != last:
            t = time.time()
            dt = t - t0
            print(f"  t={dt:6.3f}s  {fmt_state(state)}")
            if last is not None:
                transitions += 1
            last = state
            last_t = t
        if any(v for (n, _), v in zip(LINES, state) if n == "SRQ"):
            srq_seen = True

    print(f"\n{samples} Samples, {transitions} Linien-Wechsel.")
    if srq_seen:
        print("=> SRQ wurde mind. einmal asserted -> XT lebt am Bus.")
    else:
        print("=> SRQ blieb durchgehend released.")
        print("   Wenn PON-DIP auf OFF (PON SRQ enabled) steht und das XT")
        print("   trotz Power-Cycle keinen SRQ asserted hat, antwortet die")
        print("   Karte nicht autonom. Wenn PON-DIP auf ON (disabled) steht,")
        print("   ist das normal und der Test ist unbrauchbar -> PON umlegen,")
        print("   nochmal versuchen.")


if __name__ == "__main__":
    main()
