import importlib.util, pathlib
spec = importlib.util.spec_from_file_location("f", pathlib.Path(__file__).parents[1] / "ks_includes/revo_flow.py")
f = importlib.util.module_from_spec(spec); spec.loader.exec_module(f)

def test_limit():
    assert f.flow_limit(0.4) == 25 and f.flow_limit("0.6") == 45 and f.flow_limit(None) == 25

def test_script_split_and_volume():
    s = f.extrude_script(25, 10).splitlines()
    total = sum(float(l.split()[1][1:]) for l in s)
    assert abs(total * f.FIL_AREA - 250) < 0.5 and all(float(l.split()[1][1:]) <= 45 for l in s)
    assert s[0].endswith("F624")
