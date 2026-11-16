#!/bin/bash
# Symulator ekranu Revo OS: zrzuty i mapa przycisków dla 4 wariantów (Belt / sztywny stół × gotowa / drukuje).
# Użycie: tools/symulator/generuj.sh <katalog wyjściowy>   (np. ../revotech-sites/content/revo3d-pl/media/symulator)
# Wymaga: xvfb-run, python3.12 z GTK, Pillow; FAKE_PY = python z pakietem websockets (fałszywy Moonraker).
set -e
ROOT=$(cd "$(dirname "$0")/../.." && pwd); OUT=${1:?katalog wyjściowy}; TMP=$(mktemp -d)
printf "[main]\ntheme: revo\nlanguage: pl\nuse_dpms: False\nscreen_blanking: off\n" > "$TMP/KlipperScreen.conf"
python3 - "$TMP" <<'PY' &
import json, sys
from http.server import BaseHTTPRequestHandler, HTTPServer
st = {"machine_id": "REVON-DEMO-0001", "hours": 150.0, "consent": {"alerts": True, "stats": True, "asked": True}, "service": False}
class H(BaseHTTPRequestHandler):
    def _s(s, c, d): s.send_response(c); s.send_header("Content-Type", "application/json"); s.end_headers(); s.wfile.write(json.dumps(d).encode())
    def do_GET(s): s._s(200, st)
    def do_POST(s): s._s(200, {"ok": True})
    def log_message(s, *a): pass
HTTPServer(("127.0.0.1", 7130), H).serve_forever()
PY
FA=$!
for V in belt:idle belt-druk:drukowanie stol:stol stol-druk:stol-drukowanie; do
  NAME=${V%%:*}; MODE=${V##*:}
  [ -n "$ONLY" ] && [ "$ONLY" != "$NAME" ] && continue
  ( cd "$ROOT" && ${FAKE_PY:-python3} tests_revo/fake_moonraker.py "$MODE" > "$TMP/fm-$NAME.log" 2>&1 ) & FM=$!
  sleep 1
  rm -rf "$OUT/$NAME"; mkdir -p "$OUT/$NAME"
  timeout ${SYM_TIMEOUT:-2400} xvfb-run -a -s "-screen 0 480x800x24" python3.12 "$ROOT/tools/symulator/generuj.py" "$TMP/KlipperScreen.conf" "$TMP/ks-$NAME.log" "$OUT/$NAME" "$NAME" | grep --line-buffered -E "^\[|DONE" || true
  kill $FM 2>/dev/null || true; sleep 1
  python3 - "$OUT/$NAME" <<'PY'
import glob, os, sys
from PIL import Image
d = sys.argv[1]
for p in glob.glob(os.path.join(d, "*.png")):
    Image.open(p).convert("RGB").save(p[:-4] + ".webp", "WEBP", quality=82, method=6); os.remove(p)
m = os.path.join(d, "manifest.json")
if os.path.exists(m):
    t = open(m).read().replace('.png"', '.webp"')
    open(m, "w").write(t)
PY
done
kill $FA 2>/dev/null || true
echo "Gotowe: $OUT"
