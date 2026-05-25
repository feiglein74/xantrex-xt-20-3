# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project goal

Control and monitoring software for two Xantrex XT 20-3 programmable DC bench power supplies, addressed over GPIB (IEEE-488) from a Linux host.

## Hardware setup

- **GPIB controller:** Keysight/Agilent 82357B USB-GPIB adapter (USB ID `0957:0718`).
- **Instruments:** 2× Xantrex XT 20-3 with GPIB option board. Rear-panel address/mode DIP block has 8 switches: DIPs 1–3 are mode bits (unlabeled — likely TON / LON / SRQ-enable, must be read off the unit), DIPs 4–8 are address bits with weights 1, 2, 4, 8, 16. Devices read DIPs only at power-on, so any change requires a power-cycle.
- **Planned PAD assignment:** XT #1 → PAD 5, XT #2 → PAD 6. Adapter (controller) sits at PAD 0.

## Software stack

**linux-gpib** (NOT pyvisa). This is a deliberate convention carried over from the sibling project `~/ngpv-40-5/` (R&S NGPV 40-5 lab supply) that uses the same 82357B adapter on this host.

- Kernel modules: `agilent_82357a` + `gpib_common` (already loaded on this host as of 2026-05-10).
- Device nodes: `/dev/gpib0`…`/dev/gpib15`, group `dialout`, mode 0660 via `/etc/udev/rules.d/55-gpib-perms.rules`.
- Config: `/etc/gpib.conf` defines one `interface { board_type = "agilent_82357a"; name = "gpib0"; pad = 0; … }` block plus one `device { name = "…"; pad = N; … }` per instrument. Python code addresses devices by these names, never by raw PAD.
- Python bindings: the `Gpib` (high-level) and `gpib` (low-level constants/functions) modules that ship with linux-gpib. Calls not exposed by the binding (e.g. `ibppc`, `ibrpp`) are reached via `ctypes.CDLL("/usr/lib/x86_64-linux-gnu/libgpib.so.0")`.
- **Do not introduce pyvisa, pyvisa-py, or any VISA layer.** The transport convention is fixed.

## Conventions adopted from the sibling NGPV project

The transport/adapter layer is reusable across instruments; the command-set layer is per-vendor and must be derived from the XT 20-3 manual, not guessed.

- Each script is single-purpose and short (one file = one job: probe, diagnose, set, monitor).
- Every script begins with `_gpib.find("gpib0")` to get the board descriptor and `_gpib.interface_clear(bd)` to release any hung ATN state from a prior failed write.
- German comments, terse style, no framework scaffolding.
- For recovery from a hung adapter (ATN stuck), the pattern in `~/ngpv-40-5/build/adapter_unhang.py` (toggle SC, IFC, send UNL+UNT) is the reference.

## What we have learned from the manuals

**The XT-specific GPIB manual exists** and supersedes the XHR/XFR variant:
- **TM-9BGP-6HSN** — "Internal GPIB Interface for XT and HPD Series", Sorensen/AMETEK, Release 2.1 (2001). Local cache: `/tmp/xt_gpib_manual.pdf` (download from <https://xdevs.com/doc/SORENSEN/Sorensen%20HPD-XTS_%20M9(GPIB)_Manual_TM-9BGP-6HSN_Rev2_1.pdf> if missing).
- The XHR/XFR variant **TM-GPRF-01XN** still has more depth on some bus mechanics (cached too) and is largely interchangeable since the cards share family.

## GPIB option board (M9B / XM-6H9B) layout

The board actually installed in our XT 20-3s. Identifier on the PCB silk: `XM-6H9B`. Subplate part number `SM-6H9B-GPIB`. Manual ref: TM-9BGP-6HSN §5.3.

**ICs of interest:**
- **U25 = TLC 7210** (40-pin DIP) — IEEE-488 talker/listener controller. Receives its primary address by being programmed by the master µP after power-on; it is *not* hardwired from the DIPs.
- **U22 = SN75160** (DIO octal transceiver), **U20 = SN75161** (control-line octal transceiver) — bus drivers.
- **U57, U90 = MC68HC11F1** (68-pin PLCC) — Master and Slave microcontrollers. Each has its own EPROM in a 28-pin DIP socket.
- **U18 = Master EPROM** "M9B V1.14" (P/N UM-6H5C-M114), socketed.
- **U95 = Slave EPROM** "M9B V1.11" (P/N UM-6H8B-S111), socketed.
- **R96 = 10 kΩ SIP** — pull-down/pull-up array for the SW1 DIP block (10-pin isolated SIP).

**Diagnostic LEDs on the PCB** (manual §5.2.1):
- CR13 (green): Master µP recovered from illegal opcode (COP event).
- CR14 (red): Master µP restart due to noise.
- CR141 (red): Slave µP restart due to noise.
- All three off in normal operation. If a red one lights or flickers, suspect µP / EPROM / power rail issues.

**Documented PCB jumpers** (manual §2.3):
- **J95** (Local Mode Disable): Closed = remote OR local possible. Open = remote only.
- **J217** (OVP Control): Closed = software OVP control allowed.
- Both Closed is the factory default and is what we have.

**SW1 DIP block** — 8-position "piano" DIP, P/N SW-8156-KA3, on the rear-panel subplate:
- DIP 1 = REMOTE Mode Selection
- DIP 2 = PON SRQ (Power-On Service Request) Selection
- DIP 3 = **Not Used** (per manual; confirmed)
- DIPs 4–8 = A1, A2, A3, A4, A5 (primary address bits, weights 1, 2, 4, 8, 16)

**Note on DIP electrical convention for our specific units:** physical position **ON = +5 V**, **OFF = 0 V** (verified empirically with multimeter). The XHR/XFR manual prose uses inverted wording ("Switch right = 1 (ON, CLOSED)") that initially misled this troubleshooting session — trust the physical level you measure on the unit, not the manual's verbal convention.

**Rear panel / subplate layout** (manual Fig 2.2-2):
- **J8** — IEEE-488 connector (24-pin Centronics, the GPIB cable plugs in here).
- **J7** — RJ45 (8-position modular phone jack), labeled `M9B` on the silk. **NOT RS-232.** This is the User Signals Connector, with open-collector outputs and a TTL shutdown input. Pinout (manual §2.4):
  - J7-1: External TTL shutdown input
  - J7-2: Polarity signal, open collector (asserted by `VSET -x`)
  - J7-3: Isolation signal, open collector (asserted by `OUT OFF`)
  - J7-4: Fault signal, open collector (asserted on FAULT register bit)
  - J7-5: External Vcc input, 18 V max (user-supplied; nothing if not driven)
  - J7-6: External GND / shutdown return
  - J7-7: AUXA open collector (asserted by `AUXA ON`)
  - J7-8: AUXB open collector (asserted by `AUXB ON`)
- **Front panel LEDs (when GPIB option is installed):** REM (Remote Mode), SRQ, OVP. SRQ-LED here mirrors the GPIB SRQ line; lights when `PON SRQ Enabled` and the unit just powered up, until cleared by serial poll.
- **Rear panel LEDs on the subplate:** ADR (green, addressed as listener or talker) and ERR (red, command rejected).

If you measure **no signal** on the J7 RJ45 pins with a multimeter, that is normal: open-collector outputs idle hi-Z, the Vcc pin is only live if you feed external 5–18 V into it. So J7 stillness is not a defect indicator.

**Important consequence for diagnosis:** RS-232 cannot be used as a cross-check on these specific units, because RS-232 is a separate optional subplate (with 9-pin D-sub) that is *not* installed here. Only the GPIB subplate is fitted. If the GPIB path is broken there is no software-level alternative remote interface on these units.

## Earlier troubleshooting notes (XHR/XFR manual, kept for reference)

The closest *external* official documentation is the **Xantrex "Internal GPIB Interface for XHR/XFR Series"** manual (TM-GPRF-01XN, Release 3.1) — same Xantrex GPIB-card family as the XT, very likely the same firmware/command set. Local copy cached under `/home/feig/.claude/projects/-home-feig-xantrex-xt-20-3/ca615389-6e24-4137-8d5c-e4378c544181/tool-results/`.

**DIP block on the GPIB subplate (per XHR/XFR manual; XT layout matches):**

- DIP 1 = **REMOTE**: Power-On default mode. Switch position **0 (OFF) → unit boots in remote mode**, REM-LED on, output active with safe defaults (VSET=0, ISET=0, OUT ON). Position 1 (ON) → boots in local mode, front-panel control. Per the XHR/XFR manual this is a *startup-default* switch, NOT a hardware master-enable for the GPIB buffers — but on the actual XT 20-3 unit in this project, empirical testing suggested it may behave as a master-enable. Confirm per-unit before relying on the manual's wording.
- DIP 2 = **PON** (= "Power On Service Request", PON SRQ): not "output on at power-up". Position **0 (OFF) → PON SRQ enabled** (unit asserts SRQ when it powers on). Position 1 (ON) → disabled. Inverse logic.
- DIP 3 = unlabeled, function not documented. Leave OFF.
- DIPs 4–8 = **A1…A5**, primary GPIB address bits. A1 = LSB (weight 1), A5 = MSB (weight 16). Switch ON = bit set. Address 0 and 31 are special (controller / UNL command); valid device range is 1–30.

**Status byte (8-bit, returned by Serial Poll):** bit 7 = PON, bit 6 = SRQ asserted, bit 5 = ERR, bit 4 = Ready, bit 0 = Fault. Bits 1–3 unused.

**Command set: NOT SCPI**, Xantrex-proprietary "device-dependent commands". Token-based, ASCII, case-insensitive, space-separated, terminated by LF. Confirmed commands from the XHR/XFR manual that should map directly to the XT (verify each before relying on it):

```
VSET <volts>     ISET <amps>      OUT ON / OUT OFF
VOUT?            IOUT?            FAULT?     ASTS?
VMAX <volts>     IMAX <amps>      OVSET <volts>
DLY <seconds>    FOLD ON/OFF      HOLD ON/OFF
SRQ ON/OFF       MASK <flags>     UNMASK <flags>
```

Floating-point parameters: 4 significant figures, optional unit suffix (`V`, `mV`, `A`, `mA`, `s`, `ms`), scientific notation with `E`/`e`.

## Still open

- **Whether REMOTE-DIP on the XT is a hardware master-enable.** The XHR/XFR manual says no; the XT might differ. Empirical test pending.
- **Exact XT command set.** Likely a subset/superset of the XHR/XFR list above. Each command has to be verified against the actual XT — best feedback channel is the ERR-LED (red) on the front panel: lit = command rejected.

## 2026-05-10 session conclusion: firmware deactivates the 7210 at end of init

After a full day of bus-level diagnosis with an Analog Discovery 2 logic analyzer hooked into the 7210 µP-side bus pins (CS, RD, WR, RS0–2, D0–D7) — culminating in a clean 217 ms post-power-on capture (default14.csv at 25 MHz):

**The Master µP runs a real, multi-stage init sequence (47 distinct writes), but the *final* write to the primary Address Register sets DT=1 and DL=1, which disables the 7210 as both talker and listener.** From default14:

```
+135.410ms  RS=6  D=0xff  →  ARS=1, DT=1, DL=1, ADR=31 (writes Address 1, disabled)
+137.538ms  RS=6  D=0x0f  →  ARS=0, DT=0, DL=0, ADR=15 (Address 0 = 15, enabled)
+149.433ms  RS=6  D=0xec  →  ARS=1, DT=1, DL=1, ADR=12
+155.875ms  RS=6  D=0xec  →  ARS=1, DT=1, DL=1, ADR=12
+196.463ms  RS=6  D=0x6c  →  ARS=0, DT=1, DL=1, ADR=12  ← FINAL, primary address disabled
```

After +196.463 ms the µP enters a polling loop reading Serial Poll Status (RS=3). With both DT=1 and DL=1 on the primary address register, the 7210 will not respond to any MLA from the controller — exactly the symptom we chased all day. A full PAD-scan over addresses 1–30 from the controller side returns nothing.

The intermediate state at +137.538 ms (ADR=15, fully enabled) would have been a working configuration — but it gets overwritten with the disabled value. So this is not "no init" but "init runs, then deactivates the chip again."

Both XT 20-3 units behave identically, so this is a *systemic* firmware behaviour, not a single-unit fault. The most plausible interpretations:
1. **The firmware enters a self-test-failed code path** that intentionally disables the 7210 — there might be an internal check (RAM, EEPROM checksum, voltage rail, slave-µP handshake) that fails and triggers the safe-default disable.
2. **A bug in the final init step** that flips DT/DL to 1 unintentionally.
3. **A magic wake-up command** is expected from the controller before the µP fully enables the 7210, and we never sent it.

Without disassembly of the master EPROM (U18, "M9B V1.14") or knowledge of the expected wake-up handshake, this is not solvable from the bus side alone. Fixing it would require: (a) reverse engineering the master code path, (b) finding original Sorensen/AMETEK service docs that describe a wake-up sequence, or (c) replacing the EPROM with a known-good image.

Notes on capture quality:
- Decoder is reliable at 25 MHz sample rate (default10 and default14). At 6.25 MHz (default11, 12, 13) WR/CS edges can fall inside the same sample, giving false-negative write counts. Trust 25 MHz captures.
- DIP-encoded PAD = 5 on both units (verified by user with multimeter and per the manual table); the firmware ignores this DIP value and writes hardcoded ADR=15 then ADR=12 to the address register. So either the µP doesn't read the DIPs, the bit ordering is reversed in firmware, or both.

The XT-GPIB hardware (75160/75161 transceivers, 7210 controller, ICs in general) is intact. The blocker is the firmware behaviour.

Consequences:
- The 7210 stays in the indeterminate post-power-on state, has no primary address loaded, and ignores all MLA commands from the controller.
- The XT visibly handshakes universal commands (NDAC during ATN-true command phase) because that's done by I/O glue independent of 7210 internal state, but selective listener addressing fails — exactly the symptom we chased all day.
- Both XT 20-3 units in this project show identical behaviour, ruling out single-unit hardware failure and pointing at a *systemic* issue with the firmware path on this specific GPIB option board (M9B / XM-6H9B).

Possible underlying causes (not yet narrowed):
1. **Master-EPROM (U18, "M9B V1.14") code is defective** for the units we have — perhaps a different revision than what the assembled hardware expects.
2. **Master µP is taking a self-test-failed branch** — some other peripheral check fails and the firmware skips 7210 init as a result.
3. **Hardware issue between µP and 7210's chip-select path** that prevents writes from reaching the chip — though we did see CS pulses at the 7210 on the scope, so this is unlikely.

The next escalation if this matters enough to keep going: dump U18 + U95 EPROMs from both units, compare them against each other, and (if non-trivial) reverse-engineer the init-path in the master code. Hardware-stack: RS-232 option subplate as alternative, or sourcing a known-working M9B card.

## Reusable assets from the session

- `/home/feig/xantrex-xt-20-3/xt_probe.py` — single SDC + Serial Poll + REN test for xt1 (PAD 5).
- `/home/feig/xantrex-xt-20-3/xt_pad_scan.py` — sweeps PAD 1..30 with SDC.
- `/home/feig/xantrex-xt-20-3/xt_bus_watch.py` — passive bus-line sampler.
- `/home/feig/xantrex-xt-20-3/xt_probe_loop.py` — periodic IFC+SDC bursts (for scope observation).
- `/home/feig/xantrex-xt-20-3/xt_probe_slow_t1.py` — same probe with T1=2 µs bus timing (no measurable effect on this card).
- `/home/feig/xantrex-xt-20-3/xt_probe_manual_seq.py` — manual UNL+UNT+MTA0+LLO prelude before write (no effect here either).
- `/home/feig/xantrex-xt-20-3/ren_hold.py` — keep REN asserted/released until Ctrl-C, useful for scope work.
- `/home/feig/xantrex-xt-20-3/setup_xt1_conf.sh` — append `xt1` device block to `/etc/gpib.conf` and reload.
- `/home/feig/xantrex-xt-20-3/sn75161b.pdf` — local copy of TI bus-transceiver datasheet.
- `/home/feig/xantrex-xt-20-3/7210.pdf` — local copy of NAT7210 datasheet.
- `/home/feig/xantrex-xt-20-3/master_v114.bin` — 64 KB EPROM dump of the master µP (V1.14), MD5 `21903b193c458d74f11a97f69038d38f`. Read with TL866II+ as M27C512@DIP28.

Logic-analyzer captures (default1.csv … default16.csv) sit in the project dir and document the diagnostic trail. `default14.csv` (5.4 M samples, 217 ms, 25 MHz, 16 channels) is the definitive **complete init-sequence capture** showing 47 distinct 7210 bus events.

## Reverse-engineering the master EPROM (M27C512, V1.14)

Key infrastructure for any future RE work:

- **Ghidra 12.0.4** with the **M68HC11 SLEIGH plugin** from <https://github.com/GaryOderNichts/ghidra-hc11-lang> placed at `/usr/share/ghidra/Ghidra/Processors/HC11/`. The plugin needs write access to its own folder for first-load `.sla` compilation (`sudo chmod -R a+w` after install).
- Reset vector at `$FFFE-FFFF` = `$18DC`. Code there is `LDY #0` then `JMP $1800`.
- `$1800` is the standard HC11 init: `LDAA #$10 → STAA INIT($103D)`, then `OPTION($0039)`, `HPRIO($0035)`, then a CONFIG-register check at `$003F` with conditional EEPROM reprogramming.

What we did **not** find in a few hours of static analysis:
- The values written to the 7210 (0x6C, 0x0F, 0xEC, 0xFF) **do not appear as immediate constants** in the code (no `LDAB #$6C` / `LDAA #$6C` etc.). They must come from a runtime-built table or a calculation.
- Top STAA/STAB targets in extended addressing are `$ad30` (53×), `$1218` (23×), `$1837` (7×), `$1830` (5×) — but no obvious 8-address cluster for the 7210 register file. So the chip is accessed via `STAB n,X` (indexed) with X as a runtime pointer, plausibly stored in a RAM variable around `$10df` (where Ghidra showed an indirect-load `LDX [$10df]`).
- 58× `LDAB 3,X` in the binary (possibly the Serial-Poll-Status polling we saw in the captures, but not specifically attributable without context).

Concrete next-session entry points if RE is to be continued:
1. Run **Auto-Analysis with the M68HC11 plugin in Ghidra** on `master_v114.bin` and let it find functions and cross-references.
2. Open the function at `$1800` and follow the call graph until you hit a function that writes to a runtime pointer pattern (`LDX [some RAM]`, `STAB n,X` with `n=0..7`).
3. Identify the runtime RAM variable that holds the 7210 base address, then trace where it's initialised — that gives the 7210 base address in the HC11 memory map.
4. Once the base is known, all 7210 register accesses (init, polling, etc.) can be enumerated and the question "why does the firmware end with DT=1, DL=1?" can be answered from the code path.

Without this RE work, the practical conclusion stands: **the M9B GPIB cards we have don't expose the XT to a controller, even though the firmware runs and the chip does init-like writes**. Whether this is a self-test-failed branch, a buggy final write, or expected behaviour requiring a wake-up command is undetermined.

## 2026-05-25 session: Ghidra reverse engineering of master_v114.bin

Ghidra 12.0.4 with the HC11 plugin successfully auto-analysed the master EPROM image. Reset vector at $FFFE points to $18DC, which is the start of the entry function.

### `UndefinedFunction_18dc` (the entry / reset code)

Standard HC11 boot sequence, no 7210 access yet:

1. `DAT_103d = 0x10` — sets INIT register, memory map: RAM at $0000-$03FF, registers at $1000-$107F.
2. `DAT_0039 = 0x3f` — OPTION register.
3. CONFIG ($003F) check: if not `0x0B`, reprograms it via PPROG ($003B), with two embedded delay loops of $0D05 iterations each.
4. `DAT_003a = 0xaa` — COPRST watchdog refresh.
5. `DAT_0035 = 0x10` — HPRIO register.
6. `DAT_0038 = 0x20` — possibly KWIB or similar key wakeup register.
7. `DAT_005c..005f` — four RAM variables set with initial values (0xa0, 0x8c, 0x00, 0xcc).
8. Stack pointer set to $13FF via `LoadStack(0x13FF)`.
9. **External RAM zeroing**: bytes $1184..$12CE cleared to zero (≈330 bytes — likely external RAM, since HC11F1 internal RAM only reaches $03FF).
10. **External RAM init from ROM**: bytes $1000..$1184 are filled from $1400..$1584 (this is the .data-section init pattern, copying initialized variables from ROM to RAM).
11. Pushes $18AA as return address, then JSRs to `SUB_18f1` (the main routine).
12. Falls into an infinite loop if SUB_18f1 ever returns (it doesn't — it has its own infinite loop).

**Memory-map inference from this:** HC11 internal RAM at $0000-$03FF and internal registers at $1000-$107F leave $1080-$FFFF for external resources. The address `$10DF`, used heavily later, is on the cusp — possibly external RAM rather than HC11-internal.

### `UndefinedFunction_18f1` (the main routine)

The "real" application. Layout:

- **Early init calls**: `SUB_2505(param_1)`, `SUB_254e()`, `SUB_2c58()`, `SUB_29b3()`, `SUB_26f1()`. Several `SUB_3684(...)` checks are interleaved — these are **validation routines** (see below). Some `DAT_106c`/`DAT_106e` writes (extended HC11 registers).
- **DAT_10df is treated as a struct pointer** — initialised to `auStack_1d` (a 27-byte stack buffer). The struct is then accessed as `DAT_10df[6]`, `DAT_10df[4]`, `DAT_10df[0xb]`, etc. This holds the "current command" data.
- **Main loop** (`do { ... } while(true)`):
  - Watchdog refresh `DAT_003a = 0xaa` every iteration.
  - `SUB_259a()`, `SUB_2cd4()` housekeeping.
  - Receive byte via `SUB_2a5b()` → stored in `DAT_10dd`. **`SUB_2a5b` is the prime candidate for the GPIB byte-receive routine.**
  - If a byte arrived, enters an inner do-while loop that dispatches via a huge **`switch(DAT_10df[4]) { case 1..0x47: ... }`** — a 71-entry table of command handlers. Each case calls a specific FUN_/SUB_ — these are the **XT command implementations** (VSET, ISET, OUT ON/OFF, FAULT?, etc.). Mapping every case to its XT command would be the next step to build a working driver against this firmware.
  - Periodic LED-blink-like updates of `DAT_10e3`, `DAT_10e5`, `DAT_10e6`, `DAT_10e1`.
  - `SUB_36b8(0x37, 0x10, 0x37)` and `SUB_36b8(0x9d, 0xd8)` called each iteration — parameters 0x37 and 0x10 match values seen in the bus-capture writes to AUXMR/ADMR, so these are probably the **7210 register-write routines**.

### Subroutines understood so far

- **`SUB_3684(param_1, param_2)`**: a validation check. Reads two 16-bit values; returns 1 only if `*param_2` is the one's-complement of `*param_1`. Classic value+inverse data-integrity pattern, used for RAM/EEPROM self-test. The "many arguments" view in Ghidra is misleading — extra parameters pass via stack but aren't read; only the first two pointers matter.
- **`SUB_36b8`** (similar in role): not yet inspected directly, but called with the same kind of arguments and probably the actual **7210-register writer** (the values 0x37, 0x10, 0xd8 from the capture match call arguments).

### What's still to find

- **The 7210 base address in the HC11 memory map.** Pattern to look for: a function that does `LDX [some_RAM_pointer]; STAB n,X` with `n` in 0..7. The RAM pointer is presumably set up in `SUB_2505` (first call) or one of the early init subs.
- **Why the address-register write ends with `DT=1, DL=1`**: which case in the dispatcher (if any), or which init step, writes the final `0x6c` to the address register? Once the 7210-write routine is identified, cross-references will lead back to all callers.
- **Mapping the 71 dispatcher cases to XT commands** — by correlating with the published XT/XHR command set (VSET, ISET, OUT, VOUT?, IOUT?, FAULT?, ASTS?, …).

### Concrete next steps in Ghidra

1. **`SUB_2505`** (first call in main) — likely the 7210 hardware init.
2. **`SUB_36b8`** — almost certainly the 7210 register-write routine; once read, the 7210 base address falls out.
3. **`SUB_2a5b`** — probably the GPIB byte-receive; will confirm where received bytes are stashed.
4. After `SUB_36b8` is understood, cross-reference all call sites: each call is a 7210 register access with concrete (register, value) → the entire init sequence and the polling loop can be reconstructed.

### Investigation continued 2026-05-25: still no smoking gun

Walked through several subroutine candidates and verified each is NOT the 7210 driver:

- **`SUB_2505`** — only initialises zero-page RAM variables ($0001-$0028), no I/O.
- **`SUB_3684`** — data-integrity check (value + one's-complement) used for RAM/EEPROM tests. The arguments like `0x37, 0x10, 0x37` look 7210-related but are just test patterns.
- **`SUB_36b8`** — the write-counterpart of SUB_3684 (writes value + complement to two memory cells). Also a test/integrity helper, NOT 7210.
- **`SUB_2a5b`** — ring-buffer line reader (reads from buffer at `$1134-$1160` until newline `\n`, copies to `$10e9`). This is the **output/send** queue, not GPIB receive — there are 35 sequential JSRs to `FUN_2caf` (the buffer writer) in the address block $2B01-$2C36, which is a long string-emit routine. So `$1134-$1160` is the *output buffer for response strings*.
- **`FUN_2caf`** — ring-buffer producer: takes a byte, stores at `$1163` (write pointer), wraps around between `$1134-$1160`.
- **`SUB_18c3`** (one of the interrupt vector targets at `$FFF8-FFF9`) — just sets flag bit 7 in `$0001`, clears bit 7 in `$0000`. Generic "interrupt happened" stub; real work is presumably done in main loop.
- **`SUB_259a`** (which `$18E3` was incorrectly merged into) — a sanity-check / reboot function: verifies that SUB_2505's init values still match in RAM, and if not, does a full hardware re-init and jumps back to main. So `$18E3` as a vector entry is a "recovery reset", not 7210 I/O.

**Indexed `STAB 6,X` search (would catch 7210 address-register writes via runtime pointer):**
8 hits in the binary; all 6 indeterminate ones turned out to be:
- 0x1969: HC11 Timer Output Compare 1
- 0x23d7: SUB_229e (uppercase + whitespace normaliser for the command string)
- 0x3423: SUB_338e (per-channel status aggregator over the two `$103B + N*0xa1`-byte channel structures)
- 0x3b4a: local stack variable
- 0x4a0c & 0x4a24: SUB_48ae (a VSET-like command handler — stack-buffer accesses for DAC math)
- 0x7153: not inspected, but pattern likely same

So `STAB 6,X` in this firmware is mostly Timer / struct access, not 7210.

**Extended addressing analysis (would catch 7210 writes via fixed memory address):**
- Top STAA/STAB extended targets in external memory ($1080-$7FFF) — no 8-address cluster anywhere.
- The only ≥4-address cluster is `$11dc..$11df` (4 addresses, mixed R/W). Probably a multi-byte status variable, not the 7210.

**`LDAB #imm / STAB n,X` pattern search (immediate-then-write, would catch hardcoded init values):**
32 hits total. None of them have the values `0x0F, 0x6C, 0xFF, 0xEC` from the bus capture. So the values written to the 7210 are *not* hardcoded immediates anywhere in the code — they come from runtime-computed RAM variables.

### Implication

The 7210 driver is one of these:
- Accessed via `LDAB DAT_xxxx / STAB n,X` (value from RAM) — would need data-flow tracing in Ghidra to find which RAM variable feeds the address register and how it's computed.
- Accessed via 16-bit instructions (`LDD`, `STD`, `LDX`, `STX`) and a different addressing scheme.
- Wrapped in an indirect-call-through-pointer table (some firmwares dispatch I/O through a vtable).

To progress further requires either:
- **Multi-hour Ghidra session with manual function annotation**, especially data-flow tracing of `DAT_10df`, `DAT_1163`, `DAT_1161`, and the four `DAT_005c..005f` "magic" RAM init values.
- **Or a different angle entirely** — e.g. dumping the slave EPROM (V1.11) for symbol cross-checks, or running the firmware in a 68HC11 simulator (sim68hc11, e-puck simulator) with the bus traffic stubbed in, watching when register writes happen.

For now the practical conclusion stays: **firmware runs, writes some values to *something*, but we can't yet identify the 7210 driver path statically**. The Ghidra database is saved and can be extended in a future session — Ghidra's project file in `~/ghidra_projects/` (or wherever the project was created) keeps all the symbol naming and annotations.

## 2026-05-25 session continuation: discovered hardware-level RS-bit inversion

Major correction to everything we deduced from logic-analyzer captures so far.

### CSIO1 is the 7210's chip-select source

Empirical test: oscilloscope on HC11F1 pin 22 (PG5/CSIO1) shows pulses **synchronous** with the 7210-CS pin (pin 8). Tests of CSGEN (pin 21), CSIO2 (pin 23), and CSPROG (pin 20) showed no such synchrony. So the 7210 lives in the CSIO1 default range `$1100-$11FF`.

The firmware never writes to CSCTL/CSSTRH/CSSTRL/CSGADR/CSGSIZ, so default chip-select settings are in effect. The exact 8-byte location within `$1100-$11FF` isn't statically identifiable because all 7210 access goes through indirect-pointer addressing (`LDX [RAM_var]; STAB n,X`), not extended addressing.

### RS-pin wiring is INVERTED between HC11 and 7210

Decisive empirical test: scope channel 1 on HC11 pin 58 (PF0/ADDR0), channel 2 on 7210 pin 21 (RS0). The two signals are **inverse polarity** — when one is high, the other is low. Confirmed with a 2-channel comparison, the inversion is consistent throughout a CS-active cycle.

Cross-check on D-pins: HC11 pin 9 (PC0/DATA0) vs 7210 pin 12 (D0) → **synchronous, same polarity**. So **only the RS-lines are inverted**, the D-lines are not.

This means there's an inverter chip (74HC04 or similar) on the M9B card between the HC11 address bus and the 7210 RS-inputs. Possibly intentional to map the 7210 register layout to a specific memory-address scheme, possibly just board design.

### Consequence — the entire capture-decode of register IDs needs to flip

| What our captures read | What 7210 actually sees | Register |
|------------------------|-------------------------|----------|
| RS=0 (`b000`) | RS=7 (`b111`) | EOSR |
| RS=1 (`b001`) | RS=6 (`b110`) | **ADR0/ADR1 (Address Register)** |
| RS=2 (`b010`) | RS=5 (`b101`) | AUXMR |
| RS=3 (`b011`) | RS=4 (`b100`) | ADMR (Address Mode) |
| RS=4 (`b100`) | RS=3 (`b011`) | SPMR (Serial Poll Mode) |
| RS=5 (`b101`) | RS=2 (`b010`) | IMR2 |
| RS=6 (`b110`) | RS=1 (`b001`) | IMR1 |
| RS=7 (`b111`) | RS=0 (`b000`) | CDOR (Data Out) |

### Re-interpreting default14.csv with the corrected mapping

The "smoking gun" we had identified yesterday — `RS=6, D=0x6c` final write that we read as "Address Register, DT=1, DL=1, ADR=12 → disabled" — was actually a write to **IMR1 (Interrupt Mask 1)** with value 0x6c. That's an interrupt mask configuration, not a chip-disable. The 7210 wasn't being disabled at all; we were decoding the register address wrong.

The ACTUAL Address-Register write (RS=6 in 7210 terms) occurred at t=+147.747ms in our capture, where we had read RS=1, D=0x02. Decoded properly:
- D=0x02 = `0b00000010`
- ARS=0 (primary address register)
- DT=0 (talker enabled)
- DL=0 (listener enabled)
- ADR = `0b00010` = **2**

So the firmware **programs the 7210 with primary address 2**, both talker and listener enabled. NOT disabled, NOT address 12, NOT address 15.

### But PAD-scan still fails

Tested xt1 reconfigured to PAD 2 in `/etc/gpib.conf` — no response. Full PAD scan over 1-30 with clean adapter — no response from any address.

Possible reasons why PAD 2 still doesn't respond despite the correct address being programmed:
- **Later writes to other registers might disable the chip.** E.g. ADMR=0xff (which we saw multiple times) puts the 7210 into "mode 3" (dual primary addressing with secondary), which has different behavior than the default mode 1. Plus AUXMR=0xf2 is an auxiliary command we haven't decoded.
- **PAD-bus inversion** — if the GPIB DIO lines themselves are inverted between the 7210 and the actual bus connector (not just inside the chip's logic, but on the external pins), then what the 7210 sees as "address 2" appears on the bus as `~2 & 0x1F = 0x1D = 29`. But our earlier scan tested PAD 29 too.
- **Higher-order disable mechanism** that we don't see in the visible init sequence — perhaps a configuration that requires a specific bus command from the controller first.

### Practical state

- Statically we've found the architecture (7210 at CSIO1 / `$1100-$11FF`, accessed via indirect pointers), the bit-inversion on RS lines, and the actual programmed address (PAD 2).
- We still don't see the 7210 respond to controller addressing on any PAD.
- Continuing would mean either:
  - More logic-analyzer captures with the *corrected* understanding (filter writes by 7210-RS, not our capture-RS) to find late disables
  - Or hardware-level investigation of why the GPIB bus doesn't see the listener-ready state

EPROM file `master_v114.bin` is unchanged. Ghidra project preserved with all the work so far. The bit-inversion finding is a major new piece of information — any future capture analysis must apply the bit-flip before decoding RS values.

## 2026-05-25 session continuation 2: definitive root cause found

### Correction to the RS-inversion interpretation

The RS-pin inversion exists between HC11 and 7210 as a hardware fact (PF0 high when RS0 low), but **our logic-analyzer captures probe the 7210-side of the inverter directly**. So the RS values we read in the captures are already the "7210's view" — they don't need bit-flipping. The previous decode (RS=6 → ADR register) was correct all along; the RS-inversion is just a hardware property of how the µP's address bus is wired to the 7210's RS pins on the M9B card, and is transparent to our analysis.

### Where the DIPs connect — and why they're ignored

Continuity test from the rear-panel DIP block to the HC11F1 PLCC socket revealed the surprising wiring:

| DIP (weight) | HC11 Pin | Signal |
|--------------|----------|--------|
| DIP 16 (A5)  | 59       | PE0/AN0 |
| DIP 8 (A4)   | 61       | PE1/AN1 |
| DIP 4 (A3)   | 63       | PE2/AN2 |
| DIP 2 (A2)   | 65       | PE3/AN3 |
| DIP 1 (A1)   | 60       | PE4/AN4 |

**The DIPs are wired to the A/D converter inputs**, not to digital I/O pins! The µP would have to read them through the ADC subsystem (set ADCTL, wait for conversion, read ADR1-ADR4).

But the firmware reveals:

- **OPTION ($1039) is written exactly ONCE, in the boot init: `STAA #$3F → $0039`** — bit 7 (ADPU, A/D Power Up) is **0**, so the **ADC subsystem is left powered off** for the entire run.
- **ADR1-ADR4 ($1031-$1034) are read zero times** in the entire 64 KB firmware. The ADC result registers are never accessed.
- ADCTL ($1030) is written once at $EF20, but with no subsequent ADRx read it can't be for DIP-decoding.

**Conclusion: the master firmware never reads the DIPs.** No matter where you set the rear-panel switches, the firmware ignores them. The primary-address value written to the 7210's ADR0 register comes from a hardcoded path, not from any DIP-decoding logic.

### Why the 7210 is permanently disabled

Both XT 20-3 units write the same hardcoded sequence to the 7210, ending with `ADR0 = 0x6c` = (ARS=0, DT=1, DL=1, ADR=12). With both DT and DL set, the 7210 ignores all listener and talker addressing — exactly the symptom we've been chasing for two days.

The firmware appears to be deliberately keeping the GPIB chip in a disabled state. This could mean:
- The firmware is a **self-test or factory-test build** that intentionally disables GPIB until an unknown trigger condition is met (no such trigger has been found from bus side).
- The firmware was meant for a **different hardware configuration** (e.g. expecting digital inputs at PE0-PE4 rather than ADC reads) and is mis-matched with the M9B board we have.
- The firmware contains a **bug** where the init sequence completes but never re-enables the chip via a subsequent ADR0 write with DT=0, DL=0.

### Final diagnosis (2026-05-25)

**The M9B GPIB option boards in these XT 20-3 units have:**
1. Hardware: present and intact (75160/75161 transceivers, 7210 controller, dual 68HC11F1 µPs, all socketed EPROMs intact).
2. Firmware: master-V1.14 EPROM runs to completion but: (a) does not read the rear-panel DIPs, (b) configures the 7210 with ADR0=0x6c which disables both talker and listener functions.
3. Net effect: the cards never respond to any GPIB controller addressing.

This is **not** a defect in our particular units — it is a firmware behavior that affects all M9B/V1.14 boards. Without a different (working) version of the master EPROM, or extensive patching of the existing code, these cards cannot be brought into a state where a host controller can talk to them.

### What would be needed to actually make these work

Three paths in increasing difficulty:

1. **Find and burn a different master EPROM image** — e.g. M9B V1.13 or V1.15 from a known-working XT 20-3 with the same M9B board. Sources: Sorensen/AMETEK support, second-hand instrument forums, working units to dump from.
2. **Patch the existing V1.14 image** to either (a) replace the hardcoded 0x6c ADR0 write with a value that enables the chip with a useful address, or (b) add DIP-reading via ADC and use the DIP value. Requires careful 6811 disassembly, identifying the responsible code location, and re-burning the EPROM.
3. **Replace the M9B card** entirely with an equivalent that has working firmware — practically equivalent to buying a working XT 20-3 with GPIB.

The Ghidra project, master_v114.bin dump, all the logic-analyzer captures (default1-default15.csv), and the bit-level mapping documentation are preserved here for any future continuation.

## 2026-05-25 evening: BREAKTHROUGH — XT actually answers GPIB

The "final diagnosis" above is **wrong on the conclusion** (the cards are not
dead). It is correct on the static-code observations (ADC off, ADR0=0x6c
written), but the *interpretation* that this means "the cards never respond"
was disproven by empirical test.

### Capture comparison with different DIP settings proved firmware reads DIPs

| DIP setting | Capture | ADR1=DIP+3 hits | ADR1=DIP+5 hits |
|-------------|---------|-----------------|------------------|
| all OFF (PAD 0) | default21 | D=0x83 → 47× | D=0x85 → 14× |
| DIP 1 only (PAD 1) | default22 | D=0x84 → 60× | D=0x86 → 8× |
| DIP 1+4 (PAD 5) | default14 | D=0x88 → 5× | D=0x8a → 6× |

Same pattern with offsets +12 and +24 at PAD 5. The firmware programs the
7210's **secondary** address register with `DIP_value + 3, +5, +12, +24` —
clearly a **multi-channel listener configuration**. So the firmware was
written for a multi-output XT variant (e.g. XT 250-0.25 quad-channel),
not the single-output XT 20-3 we have. The DIPs ARE consulted; we just
couldn't find the read path in static analysis (presumably via key-wakeup
on Port E, since ADRx registers are never read).

### Talker works — Primary 1, Secondary 0 returns Serial Poll status

`xt_probe_extended.py` with `gpib.dev(0, pad=1, sad=0x60, ...)` returns:
- Serial Poll: **status byte 0x10** (Bit 4 = Ready) — the XT answers GPIB!
- Other secondary addresses (4, 5, 6) also return without TIMO but with 0x00.

### Listener is disabled — SDC and writes still time out

The capture shows hundreds of `DT=0 DL=1` writes (talker enabled, listener
disabled — e.g. D=0x3b = ADR0 listener-disabled, ADR=27). So the firmware
deliberately keeps the listener function off. That is why every previous
SDC/write/clear timed out, even though serial polls succeed.

### Practical state of the XT 20-3 GPIB interface

- ✅ Hardware: intact
- ✅ Firmware: runs, reads DIPs, programs the 7210
- ✅ Talker: works on `PAD=1, SAD=0`, status 0x10 returned
- ❌ Listener: not enabled in current firmware state — root cause unclear
  (firmware bug, intentional, or missing trigger condition)

### Practical addressing

- **Primary = 1** always (independent of DIPs)
- **Secondary ranges = DIP_value + 3, +5, +12, +24** depending on the channel
- Test in linux-gpib: `gpib.dev(board, 1, 0x60+N, T100ms, 1, 0)`

### FULL bidirectional communication achieved

`xt_listener_hunt.py` with the same `pad=1, sad=N` addressing also did a
REN-toggle (OFF→ON edge) before write — that triggered the listener.
After that, all standard XHR/XFR commands work:

```
ASTS? → ASTS 641
VOUT? → VOUT -0.001
OUT?  → OUT 1
```

`ASTS = 641 = 0x281` = bits 0 (Constant Voltage), 7, 9 (Remote Mode).

**Every secondary address 3..30 accepts the write and returns the same
response** — the XT either has a single internal handler that ignores
the SAD entirely, or treats all secondary as aliases for one channel.
This matches the firmware-being-multichannel hypothesis: in our single-
output XT 20-3 the channel structure collapses.

### Working addressing (verified 2026-05-25)

- Primary = **1** (always, independent of DIPs)
- Secondary = **0..30** all work, but **3..30** are reliable for write
- REN must be asserted, and a REN OFF→ON edge before the first write
  unsticks the listener

### Listener can desync after many writes — full reset procedure

After many successful read/write cycles the XT can drop back into the
listener-disabled state (bus reads `0x10ff`, NDAC released, no SAD
accepts write). Recovery sequence that reliably restores comms:

1. **USB-reset the 82357B** (unplug, wait ~2s, plug back in)
2. `sudo gpib_config`
3. **Power-cycle the XT** (front Netzschalter off, wait a few seconds, on)
4. Wait ~500ms after the XT is back on, then `xt_diag.py` or any
   `gpib.dev(0, 1, 0x60+N, T1s, 1, 0)` + write cycle works again

The order matters: GPIB adapter clean first (so the XT sees a quiescent
bus on its first read), then XT cold-boot. Adapter alone is not enough;
XT alone is not enough — both must be reset together.

### Reusable assets

- `/home/feig/xantrex-xt-20-3/xt_probe_extended.py` — extended addressing
  probe. Confirmed `pad=1, sad=0x60` returns status 0x10 via Serial Poll.
- `/home/feig/xantrex-xt-20-3/xt_listener_hunt.py` — REN-toggle + SAD-sweep.
  Found full bidirectional comms on every SAD 3..30.
- `/home/feig/xantrex-xt-20-3/xt_diag.py` — clean read-back of all XT
  status registers (VOUT, IOUT, OUT, ASTS, VSET, ISET, VMAX, IMAX, OVSET,
  FAULT). Returns valid XT 20-3 values (VMAX=20.000, IMAX=3.000).
- `/home/feig/xantrex-xt-20-3/default21.csv` (all DIPs OFF) and
  `/home/feig/xantrex-xt-20-3/default22.csv` (DIP 1 ON) — capture pair used
  to confirm DIPs are read by the firmware (secondary address depends on
  DIP value with offsets +3, +5, +12, +24).

### Verified measurements and behaviour (2026-05-25)

Confirmed by direct test on XT #1 with electronic load:

**Setpoint resolution**
- `ISET`: 1 mA steps (3 decimal places); values < 0.5 mA round to 0
- Unit suffixes accepted: `5mA` → 0.005, `1.5E-3` → 0.002 (still 1 mA grid)

**ASTS register bit decoding** (Accumulated Status, 16-bit)
- Bit 0 = CV Mode (Constant Voltage)
- Bit 1 = CC Mode (Constant Current) — exclusive with CV in steady state;
  during fast transitions both bits can briefly read 1
- Bit 8 = PON (Power-On flag, latched until cleared)
- Bit 9 = Remote Mode

**Internal-vs-true voltage offset**
- Brymen multimeter: 5.0227 V at the output terminals
- `VOUT?`: 4.998 V (intern)
- Offset = −25 mV constant across multiple readings.
  Software wrapper could correct: `V_true = VOUT? + 0.025`.

**Working command set verified**
```
VSET <V>     ISET <A>     OUT ON / OUT OFF
VSET?        ISET?        OUT?
VOUT?        IOUT?        ASTS?     FAULT?
VMAX?        IMAX?        OVSET?
```
All confirmed responding correctly on `pad=1, sad=0x65` (SAD 5) of XT #1.

**Static device parameters reported by XT #1**
- VMAX = 20.000 V (matches XT 20-3 spec)
- IMAX = 3.000 A (matches XT 20-3 spec)
- OVSET = 22.000 V (OVP threshold)

### XT #2 also confirmed working (2026-05-25 evening)

After successful XT #1 session, plugged the adapter onto XT #2 and ran
`xt_listener_hunt.py` for the wake-up. XT #2 responds identically:
VMAX=20.000, IMAX=3.000, OVSET=22.000 — two physically identical XT 20-3
units with identical firmware behaviour.

**Single-adapter workflow** (no GPIB cable yet): only one XT can be on
the bus at a time. Sequence when switching:
1. Set `OUT OFF` on the active XT
2. `gpib.remote_enable(bd, 0)` (REN release)
3. Power off the active XT (front Netzschalter)
4. Mechanically move the 82357B from one XT's GPIB connector to the other
5. Power on the new XT, wait ~3 s
6. Run `xt_listener_hunt.py` to wake the listener
7. Use `xt_diag.py` or your own commands

The 82357B is robust against mechanical re-seating during operation
(REN released to be on the safe side, but not strictly required).

### Listener wake-up is not optional

A single `gpib.dev() + gpib.write()` after fresh power-on does NOT
activate the listener — the write times out. The `xt_listener_hunt.py`
script's burst over SAD 0..30 *does* — somewhere in that sequence the
firmware flips the listener into the responding state. After that,
any single-SAD write/read cycle works normally. So the standard
incantation after each XT power-on is:

```
python3 xt_listener_hunt.py   # wake-up via SAD-sweep
python3 xt_diag.py            # or any single-target use
```

## Working notes for future Claude sessions

- The sibling project at `/home/feig/ngpv-40-5/build/` is the reference for adapter handling. Read `gpib.conf`, `adapter_check.py`, `adapter_unhang.py`, `ngpv_diag.py` before writing anything new — they encode hard-won bus-recovery patterns.
- User communicates in German interactively; code, comments in source, and this file stay German/English as established by the sibling project (German comments are fine).
- Do not invent build commands, test commands, or directory layout in this file until they actually exist in the repo.

## 82357B adapter hangs (lessons learned)

**Symptom:** all data-byte writes time out, NDAC/NRFD stay released, but REN and IFC work normally and `_gpib.find("gpib0")` succeeds. Looks like every device on the bus is dead simultaneously.

**Cause:** the Keysight 82357B firmware/state-machine drifts after a series of failed bus operations (typical: many timeouts in a row from probing a misconfigured device). REN and IFC ride a different code path than the data handshake, so the adapter stays half-alive.

**Fix:** unplug the 82357B USB cable, wait a couple of seconds, plug it back in, then `sudo gpib_config`. After that the bus is clean again. This burned ~30 minutes on 2026-05-10 — debugging XT cards that turned out to be perfectly fine.

**Diagnostic order when a previously-working bus goes stumm:**
1. USB-reset the 82357B and re-test against a known-good device (e.g. NGPV via `~/ngpv-40-5/build/ngpv_diag.py`).
2. Only after step 1 confirms the toolchain is fine, suspect the device-under-test, the cable, or DIP/jumper settings.
