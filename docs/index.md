# Xantrex XT 20-3 over GPIB — working addressing for the M9B option

Scripts and notes for controlling **Xantrex (Sorensen / AMETEK) XT 20-3**
programmable DC power supplies over **GPIB / IEEE-488** from Linux, using the
internal **M9B GPIB option board** (`XM-6H9B`, manual TM-9BGP-6HSN) and a
**Keysight / Agilent 82357B** USB-GPIB adapter with
[linux-gpib](https://linux-gpib.sourceforge.io/).

Source code: **[github.com/feiglein74/xantrex-xt-20-3](https://github.com/feiglein74/xantrex-xt-20-3)**

## Symptom

- The XT is set to a GPIB address with the rear-panel DIP switches.
- A PAD scan over addresses 1–30 finds nothing, every write times out.
- The front-panel and option-board LEDs look normal, hardware tests fine.

## What is actually going on

Found by logic-analyzer captures of the TLC7210 GPIB controller and
reverse-engineering of the master firmware (M9B V1.14, MC68HC11F1):

| Finding | Detail |
|---|---|
| Primary address | Always **1**, regardless of the DIP switches |
| Secondary address | The DIPs set secondary-address ranges (DIP value + 3, +5, +12, +24) meant for multi-channel XT variants; a single-output XT 20-3 answers on **any SAD 3–30** |
| Listener wake-up | After power-on only the talker works (serial poll returns `0x10`). A REN off→on edge plus a write sweep over the secondary addresses enables the listener |
| Command set | Xantrex proprietary, **not SCPI**: `VSET`, `ISET`, `OUT ON/OFF`, `VOUT?`, `IOUT?`, `ASTS?`, `FAULT?`, `VMAX?`, `IMAX?`, `OVSET?` verified |

## Minimal example

```python
import gpib
dev = gpib.dev(0, 1, 0x60 + 5, gpib.T1s, 1, 0)   # PAD 1, SAD 5
gpib.write(dev, b"VSET 5\n")
gpib.write(dev, b"VOUT?\n")
print(gpib.read(dev, 128))                        # b'VOUT 4.998\n'
```

Run `xt_listener_hunt.py` once after every power-on first — see the
[README](https://github.com/feiglein74/xantrex-xt-20-3#readme) for the full
quick start, ASTS bit table, rear-panel J7 pinout and recovery procedure.

## Further reading

- [README](https://github.com/feiglein74/xantrex-xt-20-3#readme) — usage, verified commands, pinouts
- [Diagnostic and reverse-engineering log](https://github.com/feiglein74/xantrex-xt-20-3/blob/master/CLAUDE.md) — full trail, partly German
- [Open items](https://github.com/feiglein74/xantrex-xt-20-3/blob/master/todo.md) — commands not yet verified (German)
