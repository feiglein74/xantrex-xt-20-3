#!/usr/bin/env python3
"""Test XT mit Extended Addressing via gpib.dev() Low-Level-API.

Hypothese: Primary=1 hardcoded in Firmware, Secondary = DIP + 3 oder + 5.
DIPs jetzt auf PAD 1 -> erwarte sad=4 oder sad=6.
"""
import time
import gpib

bd = gpib.find("gpib0")
gpib.interface_clear(bd)
time.sleep(0.2)
gpib.remote_enable(bd, 1)

# gpib.dev(board, pad, sad, timeout, send_eoi, eos)
# sad: 0 = no secondary, 0x60..0x7E = secondary 0..30
def try_pad_sad(pad, sad_val, label):
    print(f"\n=== {label}: PAD={pad}, SAD={sad_val} (raw=0x{sad_val:02x}) ===")
    try:
        dev = gpib.dev(0, pad, sad_val, gpib.T100ms, 1, 0)
        print(f"  dev handle: {dev}")
    except Exception as e:
        print(f"  dev() ERR: {e}")
        return

    # Serial Poll
    try:
        sb = gpib.serial_poll(dev)
        print(f"  Serial Poll: 0x{sb:02x}  <-- DEVICE ANTWORTET!")
    except gpib.GpibError as e:
        print(f"  Serial Poll: {e}")

    # SDC
    try:
        gpib.clear(dev)
        sta = gpib.ibsta()
        print(f"  SDC ok, ibsta=0x{sta:04x}")
        if sta & 0x0100:  # TIMO
            print(f"    -> TIMO bit set, kein Device-Response")
        else:
            print(f"    -> Kein TIMO, DEVICE ANTWORTET!")
    except gpib.GpibError as e:
        print(f"  SDC: {e}")

    # Bus-Status nach SDC
    bits = gpib.lines(bd)
    print(f"  Bus lines: 0x{bits:04x} (NDAC={1 if bits & gpib.BusNDAC else 0}, ATN={1 if bits & gpib.BusATN else 0})")

    gpib.close(dev)

# Erst PAD 1 ohne Secondary
try_pad_sad(1, 0, "Nur Primary")

# Dann Sekundär 0 (sad = 0x60)
try_pad_sad(1, 0x60, "PAD 1 + Sekundär 0")

# DIP=1: erwarte Sekundär 4 oder 6
for sad in [4, 5, 6]:
    try_pad_sad(1, 0x60 + sad, f"PAD 1 + Sekundär {sad}")

# Auch PAD=0 (was wir noch nie probiert haben)
try_pad_sad(0, 0, "PAD 0, kein Sekundär")
try_pad_sad(0, 0x60 + 4, "PAD 0 + Sekundär 4")

# Bus final
bits = gpib.lines(bd)
print(f"\n=== Final Bus: 0x{bits:04x} ===")
