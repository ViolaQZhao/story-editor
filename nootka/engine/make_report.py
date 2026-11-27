"""Run round 1, pick one storyline at random, and build a report page: plan, section and block model every
ten years, with the numbers that answer the designer's questions. Usage: python3 make_report.py [pick_seed]"""
import sys, json, os, html, numpy as np
from engine.site import build_site
from engine import explore as ex
from engine.model import run, TESTS, default_design
import render_fine as rf

PICK = int(sys.argv[1]) if len(sys.argv) > 1 else 2026
ND, NF = 120, 25
YEARS = [1, 10, 20, 30, 40, 50]
OUT = "report"; os.makedirs(f"{OUT}/img", exist_ok=True)
S = build_site("inputs/nootka_geom.json", "inputs/contours.json", "inputs/plots.json", 1.0)
T = len(S["trees"])

print("round 1:", ND, "designs x", NF, "futures", flush=True)
D, X = ex.explore(S, n_designs=ND, n_futures=NF, seed=1, progress=30)
rng = np.random.default_rng(PICK); di, fi = int(rng.integers(ND)), int(rng.integers(NF)); d = D[di]
design, dec = ex.to_run(S, d); R = run(S, design, dec, seed=fi, record=True); s = R["series"]; rec = R["record"]; sp = R["species"]
cat = ex.category(X); mine = X[di, fi]; M = ex.METRICS

# fixed framing so the six years line up
base = run(S, default_design(S), seed=0, record=True, events=False)["record"][24]
S["cut"] = rf.cut_line(S, base); S["hmax_view"] = max(max(r["h"]) for r in rec) + 1
zr = None
for y in YEARS:
    f = rec[y - 1]; tag = f"storyline D{di:03d}-F{fi:02d}"
    rf.section(S, sp, f, y, f"{OUT}/img/section_{y}.png", title=tag); rf.plan(S, sp, f, y, f"{OUT}/img/plan_{y}.png", title=tag)
    if zr is None: S["zr_view"] = None; zr = rf.model(S, sp, rec[-1], 50, f"{OUT}/img/model_50.png", title=tag); S["zr_view"] = zr
    rf.model(S, sp, f, y, f"{OUT}/img/model_{y}.png", title=tag); print("  drew year", y, flush=True)

ids = [t["id"] for t in S["trees"]]; ev = R["events"]
TEST_LABEL = dict(J1="3 or more conifers of 8 m or taller (nest trees)", J2="dense canopy within 10 m of at least 2 nest trees",
                  J3="ground, shrub and tree layers together on 40% of the green area", J4="berry shrubs on 10% of the green area",
                  H1="something in flower in 9 or more months", H2="nectar shrubs in flower in late winter",
                  H3="perch and nest structure 2 m or taller near nectar", H4="30% or more of the green area open to the sky")
def decade(y):
    i = y - 1; a = max(0, y - 10); f = rec[i]
    return dict(year=y, alive=int(s["trees_alive"][i]), stressed=int(s["trees_stressed"][i]), died=int(s["died"][:y].sum()),
                canopy=round(float(s["canopy"][i]) * 100), three=round(float(s["three_layers"][i]) * 100), structure=round(float(s["structure"][i]), 2),
                shrub=round(float(s["shrub_cover"][i]) * 100), invaded=round(float(s["invaded"][i]) * 100, 1),
                conifer_h=round(float(np.mean([h for h, q, al in zip(f["h"], sp, f["alive"]) if al and rf.FORM[q] == "conifer"] or [0])), 1),
                tallest=round(float(max(f["h"])), 1), tests={k: bool(s[k][i]) for k in TESTS},
                events={k: int(ev[k][a:y].sum()) for k in ("dry", "heat", "wind", "snow", "budget_cut")})
decades = [decade(y) for y in YEARS]
deaths = []
for y, f in enumerate(rec, 1):
    for k, why in zip(f["died"], f["cause"]):
        deaths.append(dict(year=y, id=ids[k], species=sp[k], why=why))
broken = sum(len(f["broken"]) for f in rec)
# what happened to each tree, year by year, and what each object looks like in the six drawn years
from engine.species import WINTER_SHARE
logs = {i: [] for i in ids}; removed = []
for y, f in enumerate(rec, 1):
    prev = rec[y - 2] if y > 1 else None
    for k in range(T):
        was = bool(prev and prev["alive"][k])
        if f["thinned"][k] and not (prev and prev["thinned"][k]): logs[ids[k]].append([y, "removed by glade management, not replanted"]); removed.append(dict(year=y, id=ids[k]))
        elif k in f["died"]: logs[ids[k]].append([y, "lost: " + f["cause"][f["died"].index(k)]])
        elif f["alive"][k] and not was: logs[ids[k]].append([y, "planted" if not any("lost" in e[1] for e in logs[ids[k]]) else "replanted"])
        if k in f["broken"]: logs[ids[k]].append([y, "top or branches broken by snow"])
frames = {y: dict(trees=[dict(h=round(rec[y - 1]["h"][k], 1), w=round(2 * rec[y - 1]["r"][k], 1), age=int(rec[y - 1]["age"][k]), health=int(rec[y - 1]["health"][k])) for k in range(T)],
                  patches=[dict(cover=round(c * 100), canopy=round(a * 100), inv=round(i * 100)) for c, a, i in zip(rec[y - 1]["cover"], rec[y - 1]["pcan"], rec[y - 1]["pinv"])]) for y in YEARS}
mix = {k: v * (1 - WINTER_SHARE if d["winter"] else 1) for k, v in ex.RECIPES[d["recipe"]].items()}
if d["winter"]: mix["Winter mahonia"] = WINTER_SHARE
mix = [[k, round(v * 100)] for k, v in sorted(mix.items(), key=lambda q: -q[1])]
f50 = rec[-1]
trees50 = [dict(id=ids[k], species=sp[k], h=round(f50["h"][k], 1), w=round(2 * f50["r"][k], 1), age=int(f50["age"][k]),
                health=["not standing", "stressed", "good"][f50["health"][k]], removed=bool(f50["thinned"][k])) for k in range(T)]
original = int(s["first_alive"][49])
by_sp = {}
for t in trees50:
    b = by_sp.setdefault(t["species"], dict(n=0, good=0, stressed=0, gone=0, hs=[])); b["n"] += 1
    b["good" if t["health"] == "good" else ("stressed" if t["health"] == "stressed" else "gone")] += 1
    if t["health"] != "not standing": b["hs"].append(t["h"])
patches = [dict(id=p["id"], area=round(p["area"]), cover=round(c * 100)) for p, c in zip(S["patches"], f50["cover"])]
yr = slice(19, None)
jay_years = np.all([s[k][yr] for k in TESTS[:4]], 0); hum_years = np.all([s[k][yr] for k in TESTS[4:]], 0)
fails = {k: int((~s[k][yr].astype(bool)).sum()) for k in TESTS}
open_plots = {p: v for p, v in d["plots"].items() if p in ("T04", "T08", "T13", "T14", "T15")}

def hist(values, me, title, pct=True, lo=None, hi=None):
    v = np.asarray(values) * (100 if pct else 1); me = me * (100 if pct else 1)
    small = v.max() < 5; fm = (lambda q: f"{q:.1f}") if small else (lambda q: f"{q:.0f}")
    lo = float(np.floor(v.min())) if lo is None else lo; hi = float(np.ceil(v.max())) if hi is None else hi; hi = max(hi, lo + 1)
    n, e = np.histogram(v, bins=24, range=(lo, hi)); W, H, L, Bm = 300, 120, 8, 22; bw = (W - 2 * L) / 24; mx = max(n.max(), 1)
    bars = "".join(f'<rect x="{L + i * bw:.1f}" y="{H - Bm - c / mx * (H - Bm - 14):.1f}" width="{bw - 1:.1f}" height="{c / mx * (H - Bm - 14):.1f}" class="bar"/>' for i, c in enumerate(n))
    xm = L + (me - lo) / (hi - lo) * (W - 2 * L); rank = float((v <= me).mean() * 100); u = "%" if pct else ""
    return (f'<figure><figcaption>{title}</figcaption><svg viewBox="0 0 {W} {H}" role="img" aria-label="{title}: this storyline {fm(me)}{u}, range {lo:.0f} to {fm(hi)}{u}">'
            f'{bars}<line x1="{L}" x2="{W - L}" y1="{H - Bm}" y2="{H - Bm}" class="axis"/><line x1="{xm:.1f}" x2="{xm:.1f}" y1="6" y2="{H - Bm}" class="me"/>'
            f'<text x="{L}" y="{H - 6}" class="t">{fm(lo)}{u}</text><text x="{W - L}" y="{H - 6}" class="t" text-anchor="end">{fm(hi)}{u}</text>'
            f'<text x="{min(max(xm, 40), W - 40):.1f}" y="{H - 6}" class="tm" text-anchor="middle">this one: {fm(me)}{u}</text></svg>'
            f'<p class="rank">Higher than {rank:.0f}% of the {v.size:,} runs.</p></figure>')
g = lambda k: X[..., M.index(k)].ravel()
hists = (hist(g("jay"), mine[M.index("jay")], "Steller's jay: share of years 20 to 50 with all four conditions met", lo=0, hi=100)
         + hist(g("hum"), mine[M.index("hum")], "Anna's hummingbird: share of years 20 to 50 with all four conditions met", lo=0, hi=100)
         + hist(g("annual_mort"), mine[M.index("annual_mort")], "Yearly tree mortality that came out of the run (deaths per tree per year)")
         + hist(g("first50"), mine[M.index("first50")], "First-planted trees still alive at year 50")
         + hist(g("est_survival"), mine[M.index("est_survival")], "Plantings that got through their first five years")
         + hist(g("canopy50"), mine[M.index("canopy50")], "Canopy cover of the green area at year 50")
         + hist(g("three50"), mine[M.index("three50")], "Green area with all three layers at year 50"))
shares = [float((cat == i).mean() * 100) for i in range(4)]; mycat = int(cat[di, fi])
timeline = dict(dry=[int(i) + 1 for i in np.where(ev["dry"])[0]], heat=[int(i) + 1 for i in np.where(ev["heat"])[0]],
                wind=[int(i) + 1 for i in np.where(ev["wind"])[0]], wind_extreme=[int(i) + 1 for i in np.where(ev["wind_extreme"])[0]],
                snow=[int(i) + 1 for i in np.where(ev["snow"])[0]], budget_cut=[int(i) + 1 for i in np.where(ev["budget_cut"])[0]])
data = dict(id=f"D{di:03d}-F{fi:02d}", pick=PICK, nd=ND, nf=NF, design=dict(plots=open_plots, recipe=d["recipe"], nurse=d["nurse"], thin=d["thin"], winter=d["winter"], water=d["water"]),
            nurse_delay=int(R["nurse_delay"]), decades=decades, deaths=deaths, broken=broken, trees50=trees50,
            by_sp={k: dict(n=v["n"], good=v["good"], stressed=v["stressed"], gone=v["gone"], h=round(float(np.mean(v["hs"])), 1) if v["hs"] else None) for k, v in by_sp.items()},
            patches=patches, jay=round(float(jay_years.mean() * 100)), hum=round(float(hum_years.mean() * 100)), fails=fails, test_label=TEST_LABEL,
            est=round(float(mine[M.index("est_survival")] * 100)), annual=round(float(mine[M.index("annual_mort")] * 100), 2), shares=[round(x, 1) for x in shares], cats=ex.CATS, mycat=mycat, timeline=timeline,
            max_invaded=round(float(s["invaded"].max() * 100), 1), logs=logs, frames=frames, mix=mix, removed=removed, tree_ids=ids, tree_species=sp, original=original, worst_drop=round(float(mine[M.index("worst_drop")]), 2), species=sorted(set(sp)))
json.dump(data, open(f"{OUT}/data.json", "w"))
tpl = open("report_template.html").read()
open(f"{OUT}/index.html", "w").write(tpl.replace("/*DATA*/", json.dumps(data)).replace("<!--HISTS-->", hists))
print("picked", data["id"], "design:", data["design"], "category:", ex.CATS[mycat])
print("jay", data["jay"], "hum", data["hum"], "est", data["est"], "annual", data["annual"], "first", data["original"], "deaths", len(deaths), "broken", broken)
print(json.dumps(decades[-1]))
