# TODO

## GPIB-Befehle verifizieren

Aus dem TM-9BGP-6HSN Manual als verfügbar dokumentiert, aber in der
2026-05-25-Session noch nicht praktisch durchgespielt:

### Konfiguration
- [ ] `VMAX <V>` setzen (z.B. testweise auf 10 V begrenzen) und prüfen ob
      `VSET 15` dann mit `ERR?` zurückkommt mit "Number Out of Range"
- [ ] `IMAX <A>` analog
- [ ] `OVSET <V>` setzen (z.B. 6 V) und `VSET 8` auslösen → erwarte OV-Trip
- [ ] `RST` — komplettes Reset auf Defaults, prüfen ob VSET/ISET=0, OUT=ON,
      MASK auf Initial value
- [ ] `DLY <s>` setzen (z.B. 1s) und mit Logic Analyzer / scope den Delay
      zwischen `OUT ON` und der echten Spannungsregelung sehen

### Fault Handling
- [ ] `ERR?` provozieren mit absichtlich falschen Befehlen (`VSET 999`,
      Syntax-Fehler) und Fehler-Nummer auslesen
- [ ] `FAULT?` lesen und ASTS-Bits korrelieren
- [ ] `MASK CV,OV` setzen, dann `MASK?` lesen — verifiziert MASK-Round-Trip
- [ ] `UNMASK ALL` setzen und mit absichtlichen Fault-Events (OV-Trip)
      sehen wie SRQ und FAULT-Bits sich ändern
- [ ] `SRQ ON` aktivieren, einen Fault auslösen, prüfen ob SRQ-Linie am
      Bus asserted wird

### Foldback / Hold / Trigger
- [ ] `FOLD CV` setzen, Last erhöhen → erwarte dass das XT in
      Foldback geht (Output disabled bei CV-Mode-Erreichen)
- [ ] `FOLD CC` analog
- [ ] `HOLD ON; VSET 5; ISET 1; TRG` — verifizieren dass VSET/ISET erst
      bei TRG aktiviert werden
- [ ] `HOLD?` und `FOLD?` round-trip

### Polarität
- [ ] `VSET -5` senden, mit Multimeter an J7-2 (RJ45 Pin 2) prüfen ob
      die Polaritäts-Linie asserted wird (open-collector LOW). Output am
      XT bleibt positiv 5 V; nur die Steuerlinie für ein externes Relais.

### J7 User Signals
- [ ] `AUXA ON` → Multimeter an J7-7 sollte open-collector auf GND ziehen
      (mit external Vcc an J7-5 als Pull-up; sonst floating high-Z).
      `AUXA OFF` → J7-7 zurück hi-Z.
- [ ] `AUXB ON/OFF` analog an J7-8
- [ ] `OUT OFF` → J7-3 (Isolation Signal) sollte auf GND ziehen
- [ ] Fault provozieren (z.B. OV-Trip) → J7-4 sollte ziehen
- [ ] `VSET -5` → J7-2 (Polarity) sollte ziehen
- [ ] J7-1 (TTL Shutdown Input) testen: 0 V auf Pin 1 ziehen während
      OUT ON, Output sollte sofort hardware-abgeschaltet werden

### Sonstiges
- [ ] VSET-Auflösung empirisch messen (vermutlich 1 mV — wie ISET 1 mA)
- [ ] OVSET-Auflösung (vermutlich 1 mV)
- [ ] Mehrere Befehle in einer Zeile: `ISET 2.0A;VSET 5` — verifizieren

## ASTS-Bits identifizieren

| Bit | Status |
|----:|--------|
| 0 | CV — verifiziert |
| 1 | CC — verifiziert |
| 7 | ? — sehen wir oft, Bedeutung unklar |
| 8 | PON — vermutet |
| 9 | Remote — verifiziert |
| 2-6, 10-15 | ungetestet |

- [ ] Status-Bits durch absichtliche Faults (OV-Trip, SD, FOLD-Trigger)
      einzeln auslösen und ASTS-Wert beobachten

## Hardware-Setup

- [ ] **GPIB-Bus-Kabel** besorgen, damit beide XTs gleichzeitig am Bus
      sein können (aktuell adapter steckt direkt am Centronics-Stecker)
- [ ] **DIP-Stellungen festlegen** für unterschiedliche Adressen wenn
      beide gleichzeitig am Bus sind. Aus Captures: jedes XT antwortet
      aktuell auf **alle** SAD 3..30 — möglicherweise kollidieren sie
      trotz unterschiedlicher DIPs. Empirisch zu klären.
- [ ] Test mit beiden XTs gleichzeitig am Bus

## Software-Wrapper

- [ ] `xt.py` als Library mit `class XT`:
  - `XT(serial_or_id)` resolves to right SAD/DIPs
  - `xt.set_voltage(v)`, `xt.set_current(a)`, `xt.output(bool)`
  - `xt.voltage()` returns the Brymen-corrected voltage
    (`VOUT? + 0.025` based on measured XT 20-3 offset)
  - `xt.status()` returns named ASTS bits
- [ ] Auto-Wake auf jedem `__enter__`: SAD-Sweep wenn erster Write
      timeouted (statt manuell `xt_listener_hunt.py` aufrufen)
- [ ] `gpib.conf` Einträge für `xt1` (PAD 1, SAD 5) und `xt2` (?) sobald
      beide gleichzeitig am Bus

## Reverse-Engineering — EPROM-Patch für Multi-XT-Bus

**Konkretes Ziel:** Primary-Address pro XT konfigurierbar machen (statt
hardcoded 1), damit beide XTs gleichzeitig am Bus mit eindeutigen
Adressen laufen können. Nötig falls der empirische Multi-XT-Test
zeigt dass beide auf alle SADs antworten (siehe Hardware-Setup-Block).

**Voraussetzung:** GPIB-Bus-Kabel + empirischer Test der zeigt dass die
Geräte auf gleicher Primary kollidieren.

### Bekannte Code-Stellen aus der 2026-05-25-Suche

- **@7b5c**: `ADDB #$05` — einzige relevante Stelle dieses Opcodes
  im Code. Pattern davor: `TSX; LDAB $43,X` → liest Stack-Variable
  bei SP+43, addiert 5, speichert. Sehr wahrscheinlich die
  Sekundär-Adress-Berechnung `DIP+5`.
- **6× `ORAB #$80`** (sets ARS bit = secondary register select):
  @2525, @272e, @37e8, @3938, @658a, @f4ca.
  Drei davon haben Pattern `ANDB #$7F; ORAB #$80; STAB direct` —
  klassisch "ARS auf 1 zwingen vor Secondary-Schreibvorgang".
- **131× `LDAB #$01`** im Code — die hardcoded Primary=1 ist eine davon,
  aber zu viele um direkt zu filtern. Über Cross-Reference rückwärts
  vom 7210-Schreibvorgang einkreisbar.

### Konkreter Plan in Ghidra (geschätzt 1–2 h)

1. Funktion bei @7b5c öffnen, Stack-Layout analysieren — welche
   Variable wird bei SP+43 erwartet, woher kommt der DIP-Wert?
2. Cross-Reference rückwärts: welche Funktion ruft diese auf?
3. Cross-Reference vorwärts: wer schreibt das +5-Ergebnis (Stack[SP+0])
   ins 7210?
4. Einer der 6 `ORAB #$80`-Spots steht direkt vor einem 7210-ADR-Write.
   Den finden → ist die Stelle die ADR1 (secondary) programmiert.
5. Symmetrisch für die Primary-Address: ein Cross-Ref-Pfad endet
   bei einem `LDAB #$01 / STAB ...7210-pointer...`. Das ist der Patch-
   Punkt für eine eindeutige Primary pro XT.

### Patch-Strategie

- **Variante A — Primary aus DIPs ableiten** (sauber, aber komplex):
  ersetzt den `LDAB #$01` durch eine Sequenz die den DIP-Wert direkt
  als Primary nutzt. Nur möglich wenn das LDAB-Pattern lang genug ist
  um die Sequenz zu fassen, oder via NOP-padded subroutine call.
- **Variante B — Primary über JSR zu Patch-Block** (einfacher, langsamer):
  das `LDAB #$01` durch einen `JSR <freier_speicher>` ersetzen,
  dort den DIP-Wert lesen, B mit korrektem Wert füllen, RTS.
- **Variante C — Pauschal-Patch** (am einfachsten):
  ein Byte ändern (`01` → `02`) damit XT #1 mit Patch auf Primary 2
  läuft, XT #2 mit Original-EPROM auf Primary 1. Bei zwei Geräten
  reicht das. Risiko: nur ein Byte ändern und alle abhängigen
  Berechnungen in der Firmware müssen das tolerieren.

### Workflow für Patch + Re-Burn

1. Patch in Hex-Editor an identifizierter Adresse
2. Checksumme (falls die Firmware eine prüft — wir wissen es noch nicht)
3. TL866II+ mit `minipro -p M27C512@DIP28 -w master_v114_patched.bin`
4. Original-EPROM aufbewahren als Backup
5. Patched EPROM in einen XT-Sockel, testen

### Nebensächliche RE-Aufgaben (low priority)

- [ ] Listener-Wake-Mystery: warum aktiviert ein SAD-Sweep den Listener
      während ein einzelner Write nicht? — Auf der Bus-Seite vermutlich
      braucht der 7210 zuerst eine "Untalk" oder "Listen" zu seiner
      konfigurierten Adresse, bevor er als Listener wirklich reagiert.
- [ ] DIP-Read-Mystery: ADC ist abgeschaltet (`OPTION=0x3F`), aber DIPs
      werden gelesen (Capture-Vergleich bestätigt). Über welchen Weg?
      Key-Wakeup-Interrupt auf PE-Pins? Slave-µP-IPC?
- [ ] Slave-EPROM (V1.11) dumpen für IPC-Protokoll-Verständnis
