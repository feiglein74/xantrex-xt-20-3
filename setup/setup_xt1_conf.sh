#!/usr/bin/env bash
# Trägt den xt1-Block (PAD 5) in /etc/gpib.conf ein und lädt die Conf in den
# linux-gpib Treiber. Idempotent: macht nichts, wenn xt1 schon drin ist.
#
# Aufruf:
#   bash setup/setup_xt1_conf.sh
# (sudo wird intern aufgerufen, du wirst nach dem Passwort gefragt)

set -euo pipefail

CONF=/etc/gpib.conf

if grep -q 'name[[:space:]]*=[[:space:]]*"xt1"' "$CONF"; then
    echo "[skip] xt1-Block ist bereits in $CONF eingetragen."
else
    BACKUP="$CONF.bak.$(date +%Y%m%d-%H%M%S)"
    echo "[backup] $CONF -> $BACKUP"
    sudo cp "$CONF" "$BACKUP"

    echo "[append] xt1-Block (PAD 5) -> $CONF"
    sudo tee -a "$CONF" >/dev/null <<'EOF'

/* Xantrex XT 20-3 #1 — PAD 5 */
device {
	minor       = 0
	name        = "xt1"
	pad         = 5
	sad         = 0

	eos         = 0x0a
	set-reos    = no
	set-bin     = no
}
EOF
fi

echo
echo "[verify] tail $CONF:"
tail -n 12 "$CONF"

echo
echo "[reload] sudo gpib_config"
sudo gpib_config

echo
echo "[ok] xt1 ist jetzt im Treiber registriert."
