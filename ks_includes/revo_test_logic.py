# Revo OS – logika ekranu testu maszyny (bez GTK, testowalna).
# Stan pochodzi ze zmiennych makra _REVO_TEST (revo-config/revo/revo.cfg).

REASONS = ["Nie rusza", "Zły kierunek", "Hałas / drgania", "Inne"]
ACTIVE = ("run", "ask", "reason", "repeat")


def fmt_eta(sec):
    sec = max(0, int(sec))
    if sec < 60:
        return "< 1 min"
    return f"~ {round(sec / 60)} min"


def eta(plan, step, elapsed=0.0):
    """Szacowany czas do końca: reszta bieżącego kroku + suma czasów kolejnych."""
    if step < 0 or step >= len(plan):
        return 0
    cur = max(5, plan[step][5] - elapsed)
    return cur + sum(s[5] for s in plan[step + 1:])


def view(t, elapsed=0.0):
    t = t or {}
    faza = t.get("faza") or "idle"
    plan = t.get("plan") or []
    step = t.get("step", -1)
    if not isinstance(step, int):
        step = -1
    v = {"faza": faza, "total": len(plan), "num": step + 1, "progress": 0.0,
         "name": "", "desc": "", "img": "", "title": "", "note": "", "buttons": [],
         "left": "", "eta": "", "problems": [], "skipped": []}
    if faza in ACTIVE and 0 <= step < len(plan):
        s = plan[step]
        v.update(name=s[0], desc=s[7], img=s[4],
                 progress=step / max(1, len(plan)),
                 left=f"Remaining: {len(plan) - step - 1} steps",
                 eta=fmt_eta(eta(plan, step, elapsed)))
        crit = bool(s[6])
        stop = ("PRZERWIJ", "REVO_SELFTEST_ANULUJ", "danger")
        skip = ("POMIŃ", "REVO_TEST_POMIN", "skip")
        if faza == "run":
            v["title"] = t.get("info") or "Maszyna wykonuje krok…"
            v["buttons"] = [stop, skip] if s[1] == "heat" else [stop]
            if s[1] == "heat":
                v["note"] = "Możesz pominąć grzanie – krok dostanie żółtą flagę, ale test nie zostanie przez to oblany."
        elif faza == "ask":
            a = t.get("ask") or {}
            v["title"] = a.get("t", "Czy działa?")
            v["buttons"] = [stop, ("PROBLEM", "REVO_TEST_ODP WYNIK=problem", "warn"),
                            (a.get("ok", "DZIAŁA"), a.get("cmd", "REVO_TEST_ODP WYNIK=ok"), "ok")]
        elif faza == "reason":
            v["title"] = "Co jest nie tak?"
            v["buttons"] = [(r.upper(), f'REVO_TEST_PRZYCZYNA P="{r.lower()}"', "warn") for r in REASONS]
        elif faza == "repeat":
            v["title"] = "Problem: " + (t.get("last") or "?")
            v["note"] = ("Krok krytyczny – bez niego test się zakończy." if crit
                         else "Problem trafi do raportu, test pójdzie dalej.")
            v["buttons"] = [("POWTÓRZ", "REVO_TEST_POWTORZ", "ok"),
                            ("ZAKOŃCZ TEST" if crit else "DALEJ", "REVO_TEST_DALEJ", "warn" if crit else "plain")]
            if s[1] == "heat":
                v["buttons"].insert(1, skip)
    elif faza in ("done", "stop"):
        sm = t.get("summary") or {}
        ok, total = sm.get("ok", 0), sm.get("total", len(plan))
        v["progress"] = 1.0 if faza == "done" else (sm.get("done", 0) / max(1, total))
        v["img"] = "intro"
        v["name"] = "TEST ZAKOŃCZONY" if faza == "done" else "TEST PRZERWANY"
        sk = sm.get("skipped", 0)
        v["title"] = f"Wynik: {ok}/{total} OK" + (f" · {sk} skipped" if sk else "")
        v["desc"] = (("Powód: " + sm["stopped"] + ". ") if sm.get("stopped") else "") + \
            "Wynik został zapisany i trafi do Revotech."
        v["problems"] = [f"{k}: {r.split(' · ', 1)[1] if ' · ' in r else 'problem'}"
                         for k, r in (sm.get("results") or {}).items() if not str(r).startswith(("ok", "pominiety"))]
        v["skipped"] = [k for k, r in (sm.get("results") or {}).items() if str(r).startswith("pominiety")]
        v["buttons"] = [("ZAMKNIJ", "REVO_TEST_ZAMKNIJ", "plain"), ("TESTUJ PONOWNIE", "REVO_SELFTEST", "ok")]
    else:
        v["faza"] = "idle"
        v["name"] = "TEST MASZYNY"
        v["title"] = "Pełny test, ok. 15–25 min"
        v["desc"] = ("Maszyna sprawdzi po kolei elektronikę, każdy silnik, krańcówki, osie, pas, "
                     "grzanie, wentylatory i oświetlenie. Przy każdym kroku potwierdzasz, czy działa. "
                     "Zdejmij wydruki z pasa i załaduj filament.")
        v["img"] = "intro"
        v["buttons"] = [("ROZPOCZNIJ TEST", "REVO_SELFTEST", "ok")]
    return v
