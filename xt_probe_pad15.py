#!/usr/bin/env python3
"""Probe XT auf PAD 15 statt PAD 5 (Hypothese aus default14-Capture).

Kein /etc/gpib.conf Update notwendig — direkter pad-Parameter im Gpib() Aufruf.
"""
import time
import Gpib
import gpib as _gpib

bd = _gpib.find("gpib0")
print(f"Board: {bd}")

_gpib.interface_clear(bd)
time.sleep(0.2)

# Direkt PAD 15 ohne /etc/gpib.conf eintrag
print("\n[1] Versuche Gpib auf PAD 15 zu öffnen ...")
xt = Gpib.Gpib(name="gpib0", pad=15, sad=0, timeout=_gpib.T1s, send_eoi=1, eos_mode=0)

print("\n[2] Serial Poll auf PAD 15")
try:
    sb = xt.serial_poll()
    print(f"    OK Statusbyte = 0x{sb:02x} ({sb:08b})")
except _gpib.GpibError as e:
    print(f"    GpibError: {e}")

print("\n[3] SDC auf PAD 15")
try:
    xt.clear()
    print(f"    OK ibsta=0x{xt.ibsta():04x}")
except _gpib.GpibError as e:
    print(f"    ERR: {e}")

print("\n[4] Schreibversuch 'OUT OFF' auf PAD 15")
try:
    xt.write(b"OUT OFF\n")
    print(f"    OK ibsta=0x{xt.ibsta():04x}, {xt.ibcnt()} Bytes")
except _gpib.GpibError as e:
    print(f"    ERR: {e}")

print("\n[5] Query 'VOUT?' und Read")
try:
    xt.write(b"VOUT?\n")
    time.sleep(0.1)
    response = xt.read(64)
    print(f"    Read: {response!r}")
except _gpib.GpibError as e:
    print(f"    ERR: {e}")
