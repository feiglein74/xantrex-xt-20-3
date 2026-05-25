# Xantrex XT 20-3 GPIB Control

Linux control software for two Xantrex XT 20-3 programmable DC bench power
supplies via the M9B GPIB option board, addressed over a Keysight 82357B
USB-GPIB adapter.

## Hardware

- Adapter: Keysight 82357B (USB ID `0957:0718`)
- Instruments: 2× Xantrex XT 20-3 with M9B GPIB option (`XM-6H9B` board)
- Both XTs report `VMAX=20.000 V`, `IMAX=3.000 A`, `OVSET=22.000 V`

Single-adapter workflow: only one XT on the bus at a time (no GPIB cable
yet — adapter plugs directly onto the rear-panel Centronics connector).

## Software stack

- linux-gpib (kernel modules `agilent_82357a` + `gpib_common`)
- Python via `Gpib` (high-level) and `gpib` (low-level) bindings from
  the linux-gpib package
- NOT pyvisa — deliberate convention from sibling project `ngpv-40-5/`

## Addressing — the non-obvious part

The M9B/V1.14 firmware uses a **fixed primary address = 1**, regardless of
the rear-panel DIP switches. The DIPs configure secondary-address ranges
intended for multi-channel XT variants. On our single-output XT 20-3, the
device responds to **any secondary address in the range 3..30**.

```python
import gpib
bd = gpib.find("gpib0")
dev = gpib.dev(0, 1, 0x60 + 5, gpib.T1s, 1, 0)
#                  ^  ^^^^^^^^
#                  |  secondary 5 (0x60 + N for SAD N)
#                  primary = 1 (hardcoded in firmware)
```

## Quick start

After a fresh XT power-on the listener is in a disabled state and a single
`write()` will time out. The listener is woken up by an SAD burst:

```bash
sudo gpib_config                          # once after USB reset / boot
python3 xt_listener_hunt.py               # wakes the listener via SAD-sweep
python3 xt_diag.py                        # read all status registers
```

After `xt_listener_hunt.py` has run once per power-on, normal single-target
`dev() + write() + read()` cycles work.

## Setting outputs

```python
import time, gpib
bd = gpib.find("gpib0")
gpib.interface_clear(bd)
gpib.remote_enable(bd, 1)
dev = gpib.dev(0, 1, 0x60+5, gpib.T1s, 1, 0)

def send(c):
    gpib.write(dev, (c + "\n").encode())
    time.sleep(0.15)

send("VSET 5")        # 5.000 V setpoint
send("ISET 0.5")      # 0.500 A current limit
send("OUT ON")        # enable output

# Read back
def query(c):
    gpib.write(dev, (c + "\n").encode())
    time.sleep(0.08)
    return gpib.read(dev, 128).decode().strip()

print(query("VOUT?"))   # → 'VOUT 4.998'
print(query("ASTS?"))   # → 'ASTS 643'
```

## Verified commands

```
VSET <V>      ISET <A>       OUT ON / OUT OFF
VSET?         ISET?          OUT?
VOUT?         IOUT?          ASTS?      FAULT?
VMAX?         IMAX?          OVSET?
```

Other commands documented in the manual (untested in this session, see
`todo.md`): `VMAX <V>`, `IMAX <A>`, `OVSET <V>`, `DLY <s>`, `FOLD <mode>`,
`HOLD <ON/OFF>`, `TRG`, `MASK <list>`, `UNMASK <list>`, `SRQ <ON/OFF>`,
`RST`, `ERR?`, `AUXA <ON/OFF>`, `AUXB <ON/OFF>` (latter two drive the
open-collector outputs on rear-panel J7 pins 7 and 8 — see "User Signals
Connector" section below).

`VSET` and `ISET` accept decimal, unit suffixes (`5mA`), and scientific
notation (`1.5E-3`). Resolution: **1 mA on ISET** (sub-mA values round to
zero or the nearest 1 mA step). VSET resolution untested but presumably
1 mV.

## ASTS register bits

`ASTS?` returns a 16-bit decimal value. Verified bit meanings:

| Bit | Meaning |
|----:|---------|
|   0 | CV mode (Constant Voltage) |
|   1 | CC mode (Constant Current) |
|   8 | PON (Power-On flag, latched until cleared) |
|   9 | Remote Mode |

Bit 7 is sometimes set; meaning not yet identified. Other bits not observed.

## Voltage measurement offset

Internal `VOUT?` reads ~25 mV low compared to actual output:

| XT | `VOUT?` | Brymen at terminals | Δ |
|---:|--------:|---------------------:|--:|
|  1 | 4.998 V | 5.0227 V | −24.7 mV |
|  2 | 4.994 V | 5.0182 V | −24.2 mV |

A software wrapper can compensate: `V_true = VOUT_xt + 0.025`.

## Rear-panel RJ45 (J7) — User Signals Connector

The RJ45 jack on the GPIB subplate is **not** RS-232 and not a remote
console. It is a hardware-integration interface with open-collector
outputs (for status signaling to a PLC) and a TTL shutdown input.

| Pin | Function | Dir | Driven by |
|----:|----------|-----|-----------|
| 1 | TTL Shutdown input | In | external logic |
| 2 | Polarity signal (OC, active-low) | Out | `VSET -x` GPIB command |
| 3 | Isolation signal (OC) | Out | `OUT OFF` GPIB command |
| 4 | Fault signal (OC) | Out | any unmasked FAULT bit |
| 5 | External Vcc input, ≤18 V | In | user-supplied, for pull-ups |
| 6 | External GND / Shutdown return | — | — |
| 7 | AUXA (OC) | Out | `AUXA ON/OFF` GPIB command |
| 8 | AUXB (OC) | Out | `AUXB ON/OFF` GPIB command |

Open-collector outputs idle hi-Z. They only produce a usable HIGH level
if you supply an external pull-up via Pin 5; without it, a multimeter
sees nothing on those pins (this is normal, not a defect).

Typical uses: drive an external polarity-reversing relay (Pin 2),
signal Fault/Output-Off state to a SCADA system (Pins 3, 4), or use
AUXA/AUXB as software-controlled relay outputs for fans, contactors,
indicator lamps etc.

## Recovery from a hung listener

After many writes or extended idle periods the XT can lose its responsive
listener state. Full recovery sequence:

1. Unplug 82357B USB, wait ~2 s, plug back in
2. `sudo gpib_config`
3. Power-cycle the XT (front Netzschalter off → on)
4. Wait ~3 s, then run `xt_listener_hunt.py`

Adapter alone is insufficient; XT alone is insufficient — both must reset.

## Switching between XT #1 and XT #2

Before unplugging the adapter:

```python
gpib.write(dev, b"OUT OFF\n")           # safe shutdown of XT output
gpib.remote_enable(bd, 0)                # release REN
```

Power off the active XT, move the 82357B to the other XT, power it on, wait
3 s, then `xt_listener_hunt.py`.

## File index

- `xt_listener_hunt.py` — wake-up sequence after every XT power-on
- `xt_diag.py` — read all status/setpoint registers
- `xt_probe_extended.py` — demonstrate `pad=1, sad=N` addressing
- `master_v114.bin` — dump of the master EPROM (V1.14) for reference
- `default14.csv`, `default21.csv`, `default22.csv` — logic-analyzer captures
  proving DIPs influence the 7210 secondary-address writes
- `CLAUDE.md` — exhaustive diagnostic log (2026-05-10 through 2026-05-25);
  read this if you need the full story including the firmware reverse-
  engineering trail
