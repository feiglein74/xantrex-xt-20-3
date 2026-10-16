#!/usr/bin/env python3
"""PAD-Scan: probiert alle GPIB-Adressen 1..30 durch und meldet,
auf welcher das XT (oder irgendein Listener) antwortet.

Methode: pro PAD ein kurzlebiges Device-Handle oeffnen, Serial Poll versuchen.
- Erfolg (ibrsp liefert Statusbyte) -> Geraet vorhanden
- Timeout / GpibError              -> kein Geraet auf dieser PAD

Timeout pro Versuch absichtlich kurz (T100ms), damit der Scan in ~3s durchlaeuft.
"""

import time
import Gpib
import gpib as _gpib


def main():
    print("=== GPIB PAD-Scan (1..30) ===\n")

    bd = _gpib.find("gpib0")
    print(f"Board-Descriptor: {bd}\n")

    # Bus zuerst saeubern
    _gpib.interface_clear(bd)
    time.sleep(0.2)

    found = []
    for pad in range(1, 31):
        # Adresse 0 = Controller, 31 = UNL -> uebersprungen
        try:
            dev = Gpib.Gpib(name="gpib0", pad=pad, sad=0,
                            timeout=_gpib.T100ms, send_eoi=1, eos_mode=0)
            sb = dev.serial_poll()
            print(f"  PAD {pad:2d}: ANTWORT  Statusbyte=0x{sb:02x} ({sb:08b})")
            found.append((pad, sb))
        except _gpib.GpibError:
            # Timeout = kein Geraet -> stumm weiter
            print(f"  PAD {pad:2d}: -")
        except Exception as e:
            print(f"  PAD {pad:2d}: {type(e).__name__}: {e}")

        # nach jedem Versuch IFC, damit ein TIMO-Hang nicht den naechsten verseucht
        _gpib.interface_clear(bd)
        time.sleep(0.05)

    print()
    if found:
        print(f"=== Gefunden auf {len(found)} Adresse(n): ===")
        for pad, sb in found:
            print(f"   PAD {pad}, Statusbyte 0x{sb:02x}")
        print()
        print("Naechster Schritt: /etc/gpib.conf auf die korrekte PAD aendern,")
        print("oder die DIPs auf die geplante PAD (5) umstellen.")
    else:
        print("=== KEIN Geraet auf 1..30 gefunden. ===")
        print("Hinweise:")
        print("  - GPIB-Kabel pruefen (beide Schrauben fest am Centronics-Stecker)")
        print("  - XT eingeschaltet?")
        print("  - GPIB-Option im Geraet vorhanden? (manche XT haben sie nicht)")
        print("  - DIPs 1-3 (REMOTE/PON/?) nochmal ablesen und beschreiben")


if __name__ == "__main__":
    main()
