#!/bin/bash
# Wszystkie warianty symulatora naraz – każdy w osobnej przestrzeni sieciowej (fałszywy Moonraker ma stały port 7125).
# Wymaga roota (unshare -n). Użycie: FAKE_PY=<python z websockets> tools/symulator/wszystkie.sh <katalog wyjściowy>
set -e
DIR=$(cd "$(dirname "$0")" && pwd); OUT=${1:?katalog wyjściowy}; mkdir -p "$OUT"
for V in belt belt-druk belt-seq belt-plates belt-long belt-endless stol stol-druk; do
  unshare -n bash -c "python3 '$DIR/lo_up.py'; ONLY=$V '$DIR/generuj.sh' '$OUT' > '$OUT/$V.log' 2>&1" &
done
wait
grep -h DONE "$OUT"/*.log
