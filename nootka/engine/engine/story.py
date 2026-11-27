"""Everything the report needs about one storyline (one design in one future), and the drawings for one year."""
import math, numpy as np
from . import explore as ex
from .model import run, TESTS
from .species import WINTER_SHARE
from .site import OUT

YEARS = [1, 10, 20, 30, 40, 50]
FORM_CONIFER = {"Douglas-fir", "Western red cedar", "Sitka spruce", "Grand fir"}
TEST_LABEL = dict(J1="3 or more conifers of 8 m or taller (nest trees)", J2="dense canopy within 10 m of at least 2 nest trees",
                  J3="ground, shrub and tree layers together on 40% of the green area", J4="berry shrubs on 10% of the green area",
                  H1="something in flower in 9 or more months", H2="nectar shrubs in flower in late winter",
                  H3="perch and nest structure 2 m or taller near nectar", H4="30% or more of the green area open to the sky")


def build(S, d, seed, open_plots=("T04", "T08", "T13", "T14", "T15")):
    """Returns (data, R): data is plain JSON-ready, R is the full run with its yearly record."""
    R = ex.run_d(S, d, seed, record=True); s = R["series"]; rec = R["record"]; sp = rec[-1]["sp"]; ev = R["events"]
    T = len(S["trees"]); ids = [t["id"] for t in S["trees"]]; mine = dict(zip(ex.METRICS, ex.measure(R, T)))

    def decade(y):
        i = y - 1; a = max(0, y - 10); f = rec[i]
        con = [h for h, q, al in zip(f["h"], sp, f["alive"]) if al and q in FORM_CONIFER]
        return dict(year=y, alive=int(s["trees_alive"][i]), stressed=int(s["trees_stressed"][i]), died=int(s["died"][:y].sum()),
                    canopy=round(float(s["canopy"][i]) * 100), three=round(float(s["three_layers"][i]) * 100), structure=round(float(s["structure"][i]), 2),
                    shrub=round(float(s["shrub_cover"][i]) * 100), invaded=round(float(s["invaded"][i]) * 100, 1),
                    conifer_h=round(float(np.mean(con or [0])), 1), tallest=round(float(max(f["h"])), 1), tests={k: bool(s[k][i]) for k in TESTS},
                    events={k: int(ev[k][a:y].sum()) for k in ("dry", "heat", "wind", "snow", "budget_cut")})
    deaths = []; logs = {i: [] for i in ids}; removed = []
    for y, f in enumerate(rec, 1):
        prev = rec[y - 2] if y > 1 else None
        for k, why in zip(f["died"], f["cause"]): deaths.append(dict(year=y, id=ids[k], species=(prev or f)["sp"][k], why=why))
        for k in range(T):
            was = bool(prev and prev["alive"][k]); hb = round(prev["h"][k], 1) if prev else 0
            if k in f["glade"]: logs[ids[k]].append([y, f"removed by glade management at {hb} m, not replanted"]); removed.append(dict(year=y, id=ids[k], why="glade management", h=hb, species=f["sp"][k]))
            elif k in f["alder_out"]: logs[ids[k]].append([y, f"red alder taken out at {hb} m to release the conifers"]); removed.append(dict(year=y, id=ids[k], why="red alder removal", h=hb, species=f["sp"][k]))
            elif k in f["died"]: logs[ids[k]].append([y, "lost: " + f["cause"][f["died"].index(k)]])
            elif f["alive"][k] and not was:
                again = any("lost" in e[1] for e in logs[ids[k]])
                logs[ids[k]].append([y, ("replanted as " + f["sp"][k] if prev and prev["sp"][k] != f["sp"][k] else "replanted") if again else "planted"])
            if k in f["lifted"]: logs[ids[k]].append([y, "crown lifted by glade management"])
            if k in f["broken"]: logs[ids[k]].append([y, "top or branches broken by snow"])
    f50 = rec[-1]
    trees50 = [dict(id=ids[k], species=sp[k], h=round(f50["h"][k], 1), w=round(2 * f50["r"][k], 1), age=int(f50["age"][k]),
                    health=["not standing", "stressed", "good"][f50["health"][k]], removed=bool(f50["thinned"][k]),
                    shade=f50["shd"][k], shader=ids[f50["shader"][k]], fails=sum(1 for e in logs[ids[k]] if e[1].startswith("lost"))) for k in range(T)]
    by = {}
    for t in trees50:
        b = by.setdefault(t["species"], dict(n=0, good=0, stressed=0, gone=0, hs=[])); b["n"] += 1
        b["good" if t["health"] == "good" else ("stressed" if t["health"] == "stressed" else "gone")] += 1
        if t["health"] != "not standing": b["hs"].append(t["h"])
    by_sp = {k: dict(n=v["n"], good=v["good"], stressed=v["stressed"], gone=v["gone"], h=round(float(np.mean(v["hs"])), 1) if v["hs"] else None) for k, v in by.items()}
    frames = {y: dict(trees=[dict(sp=rec[y - 1]["sp"][k], h=round(rec[y - 1]["h"][k], 1), w=round(2 * rec[y - 1]["r"][k], 1), age=int(rec[y - 1]["age"][k]), health=int(rec[y - 1]["health"][k])) for k in range(T)],
                      patches=[dict(cover=round(c * 100), canopy=round(a * 100), inv=round(i * 100)) for c, a, i in zip(rec[y - 1]["cover"], rec[y - 1]["pcan"], rec[y - 1]["pinv"])]) for y in YEARS}
    mix = {k: v * (1 - WINTER_SHARE if d["winter"] else 1) for k, v in ex.RECIPES[d["recipe"]].items()}
    if d["winter"]: mix["Winter mahonia"] = WINTER_SHARE
    yr = slice(19, None)
    data = dict(design=dict(plots={p: v for p, v in d["plots"].items() if p in open_plots}, recipe=d["recipe"], nurse=d["nurse"], thin=d["thin"], winter=d["winter"], water=d["water"],
                            mgmt=d.get("mgmt", {}), events=d.get("events", {})),
                seed=seed, nurse_delay=int(R["nurse_delay"]), decades=[decade(y) for y in YEARS], deaths=deaths, broken=sum(len(f["broken"]) for f in rec), trees50=trees50, by_sp=by_sp,
                patches=[dict(id=p["id"], area=round(p["area"]), cover=round(c * 100)) for p, c in zip(S["patches"], f50["cover"])],
                jay=round(float(np.all([s[k][yr] for k in TESTS[:4]], 0).mean() * 100)), hum=round(float(np.all([s[k][yr] for k in TESTS[4:]], 0).mean() * 100)),
                fails={k: int((~s[k][yr].astype(bool)).sum()) for k in TESTS}, test_label=TEST_LABEL, est=round(mine["est_survival"] * 100), annual=round(mine["annual_mort"] * 100, 2),
                original=int(s["first_alive"][49]), timeline={k: [int(i) + 1 for i in np.where(ev[k])[0]] for k in ("dry", "heat", "wind", "wind_extreme", "snow", "budget_cut")},
                max_invaded=round(float(s["invaded"].max() * 100), 1), logs=logs, frames=frames, mix=[[k, round(v * 100)] for k, v in sorted(mix.items(), key=lambda q: -q[1])],
                removed=removed, tree_ids=ids, tree_species=sp, metrics={k: float(v) for k, v in mine.items()})
    return data, R


def frame_view(S, R):
    """Fix the section line and the drawing heights so every year of a storyline lines up."""
    import render_fine as rf
    if "cut" not in S:
        from .model import default_design
        S["cut"] = rf.cut_line(S, run(S, default_design(S), seed=0, record=True, events=False)["record"][24])
    hmax = max(max(f["h"]) for f in R["record"]); S["hmax_view"] = hmax + 1
    zmin = math.floor(np.nanmin(S["E"][S["cls"] != OUT])) - 1; S["zr_view"] = float(np.nanmax(S["E"][S["cls"] != OUT]) - zmin + max(hmax, 13) + 2)


def draw(S, R, year, prefix, title=""):
    import render_fine as rf
    f = R["record"][year - 1]; sp = f["sp"]
    rf.section(S, sp, f, year, f"{prefix}section.png", title=title); rf.plan(S, sp, f, year, f"{prefix}plan.png", title=title); rf.model(S, sp, f, year, f"{prefix}model.png", title=title)
