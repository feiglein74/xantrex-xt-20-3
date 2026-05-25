#!/usr/bin/env python3
"""Sauberer XT-Diagnose-Lauf. Fragt VOUT, IOUT, OUT, ASTS und VMAX/IMAX ab.

Verwendet die bekannte funktionierende Adressierung:
  Primary = 1 (hardcoded in Firmware), Sekundär = beliebig in 3..30.
"""
import time
import gpib

PAD = 1
SAD = 0x60 + 5  # SAD 5, beliebig in 3..30

bd = gpib.find("gpib0")
gpib.interface_clear(bd)
time.sleep(0.1)
# REN OFF -> ON Edge, das aktiviert den Listener
gpib.remote_enable(bd, 0)
time.sleep(0.05)
gpib.remote_enable(bd, 1)
time.sleep(0.1)

dev = gpib.dev(0, PAD, SAD, gpib.T1s, 1, 0)

def query(cmd):
    gpib.write(dev, (cmd + "\n").encode())
    try:
        resp = gpib.read(dev, 128)
        return resp.decode(errors="replace").strip()
    except gpib.GpibError as e:
        return f"<err: {e}>"

print(f"XT auf PAD={PAD}, SAD={SAD-0x60}")
print()

for cmd in ["VOUT?", "IOUT?", "OUT?", "ASTS?", "VSET?", "ISET?", "VMAX?", "IMAX?", "OVSET?", "FAULT?"]:
    resp = query(cmd)
    print(f"  {cmd:8s} -> {resp}")

# Serial Poll am Ende
try:
    sb = gpib.serial_poll(dev)
    print(f"\nSerial Poll: 0x{sb:02x}")
except gpib.GpibError as e:
    print(f"\nSerial Poll err: {e}")

gpib.close(dev)
