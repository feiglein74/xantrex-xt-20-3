#!/usr/bin/env python3
"""Versuche das XT aus dem Listener-disabled-Modus rauszubringen.

Bekannt:
- PAD=1, SAD=0 → Serial Poll antwortet mit 0x10 (Ready)
- SDC und Write timeoutten

Hypothesen die wir testen:
1. REN-Toggle (low/high) vor SDC könnte Listener aktivieren
2. *IDN? oder ein anderer Standard-Query als allererstes Schreiben
3. Verschiedene Sekundär-Adressen für write
4. Try sad=0 mit ASTS? (Address Status?) als minimalem Befehl
5. Try with explicit IFC + REN-puls direkt vor jedem Versuch
"""
import time
import gpib

bd = gpib.find("gpib0")

def fresh_bus():
    gpib.interface_clear(bd)
    time.sleep(0.05)

def open_dev(pad, sad):
    return gpib.dev(0, pad, sad, gpib.T100ms, 1, 0)

# === Test A: Status auslesen, dann *IDN? schreiben ===
print("=== A: REN ON, dann Serial Poll, dann VOUT? ===")
fresh_bus()
gpib.remote_enable(bd, 1)
time.sleep(0.1)
dev = open_dev(1, 0x60)
try:
    sb = gpib.serial_poll(dev)
    print(f"  Serial Poll: 0x{sb:02x}")
except Exception as e:
    print(f"  SP err: {e}")

for cmd in [b"VOUT?\n", b"VOUT?\r\n", b"VOUT?", b"*IDN?\n", b"ASTS?\n"]:
    try:
        gpib.write(dev, cmd)
        sta = gpib.ibsta()
        cnt = gpib.ibcnt()
        if sta & 0x4000:  # ERR
            print(f"  write {cmd!r}: ERR sta=0x{sta:04x}")
        else:
            print(f"  write {cmd!r}: OK sta=0x{sta:04x} cnt={cnt}")
            try:
                resp = gpib.read(dev, 80)
                print(f"    Read: {resp!r}")
            except Exception as e:
                print(f"    Read err: {e}")
    except Exception as e:
        print(f"  write {cmd!r}: {e}")
gpib.close(dev)

# === Test B: REN-Toggle vor write ===
print("\n=== B: REN OFF -> ON-Edge dann Serial Poll/Write ===")
fresh_bus()
gpib.remote_enable(bd, 0)
time.sleep(0.1)
gpib.remote_enable(bd, 1)
time.sleep(0.1)
dev = open_dev(1, 0x60)
try:
    sb = gpib.serial_poll(dev)
    print(f"  Serial Poll: 0x{sb:02x}")
except Exception as e:
    print(f"  SP err: {e}")
try:
    gpib.write(dev, b"VOUT?\n")
    sta = gpib.ibsta()
    print(f"  write VOUT?: sta=0x{sta:04x}, cnt={gpib.ibcnt()}")
except Exception as e:
    print(f"  write err: {e}")
gpib.close(dev)

# === Test C: alle Sekundär 0..30 mit write ===
print("\n=== C: SAD 0..30 mit write 'OUT?\\n' ===")
fresh_bus()
gpib.remote_enable(bd, 1)
time.sleep(0.05)
hits = []
for sad in range(0, 31):
    try:
        dev = gpib.dev(0, 1, 0x60 + sad, gpib.T30ms, 1, 0)
        try:
            gpib.write(dev, b"OUT?\n")
            sta = gpib.ibsta()
            cnt = gpib.ibcnt()
            if (sta & 0x4000) == 0 and cnt == 5:
                print(f"  SAD={sad:2d}: write OK ({cnt} bytes, sta=0x{sta:04x})")
                hits.append(("write", sad))
                try:
                    resp = gpib.read(dev, 80)
                    print(f"    Read: {resp!r}")
                except Exception as e:
                    print(f"    Read err: {e}")
            # else: silent (Timeout, normal für non-listener)
        except Exception as e:
            pass
        gpib.close(dev)
    except Exception:
        pass

if not hits:
    print("  Keine SAD-Adresse akzeptiert write")

# === Test D: nochmal Serial Poll auf alle SAD ===
print("\n=== D: Serial Poll auf SAD 0..30 ===")
fresh_bus()
gpib.remote_enable(bd, 1)
time.sleep(0.05)
for sad in range(0, 31):
    try:
        dev = gpib.dev(0, 1, 0x60 + sad, gpib.T30ms, 1, 0)
        try:
            sb = gpib.serial_poll(dev)
            if sb != 0:
                print(f"  SAD={sad:2d}: status=0x{sb:02x}")
        except Exception:
            pass
        gpib.close(dev)
    except Exception:
        pass

print("\n=== Final ===")
bits = gpib.lines(bd)
print(f"Bus: 0x{bits:04x}")
