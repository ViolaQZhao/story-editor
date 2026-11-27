"""Design exploration: the engine picks a species for every open plot, a shrub recipe and the management
choices, then meets each design with the same set of futures. Nothing here says which design is 'best':
it reports how each choice shifts the spread of outcomes, so the designer can lock what is settled and
run a narrower round."""
import json
import numpy as np
from .model import run, TESTS
from .species import TREES, NATIVE_SHRUBS

# shrub recipes: shares of each patch (J). Winter mahonia is a separate choice on top of any recipe.
RECIPES = {
    "even":    {s: 1 / 6 for s in NATIVE_SHRUBS},
    "berry":   dict(Salmonberry=0.25, Thimbleberry=0.20, Osoberry=0.20, Snowberry=0.15, Salal=0.15, Oceanspray=0.05),
    "nectar":  dict(Salmonberry=0.35, Osoberry=0.25, Salal=0.20, Oceanspray=0.10, Thimbleberry=0.05, Snowberry=0.05),
    "cover":   dict(Salal=0.40, Snowberry=0.20, Oceanspray=0.20, Osoberry=0.10, Salmonberry=0.05, Thimbleberry=0.05),
}
# management choices and their options; anything named in `locks` is held fixed
CHOICES = dict(nurse=[0, 1], thin=[0, 1], winter=[0, 1], water=[2, 5], recipe=list(RECIPES))
METRICS = ["jay", "hum", "survival", "canopy10", "canopy20", "canopy30", "canopy40", "canopy50", "structure50",
           "three50", "stressed50", "eco", "worst_drop", "est_survival", "first50", "occupied50", "annual_mort", "jay_n", "hum_n",
           *TESTS, "d_dry", "d_heat", "d_dry2", "d_age", "d_shade", "d_wind"]      # share of years 20-50 each condition is met; trees lost by cause
CATS = ["both birds", "jay only", "hummingbird only", "neither"]


def candidates(site, mode="round1"):
    """Candidate species per plot. round1: cedar or Douglas-fir at the cedar plots, the rest as drawn.
    open: every plot may change within its type (conifer / tall deciduous); vine maple stays (only small tree)."""
    out = {}
    for t in site["trees"]:
        s = t["species"]
        if s == "Western red cedar": c = ["Western red cedar", "Douglas-fir"]
        elif mode == "round1" or s == "Vine maple": c = [s]
        elif TREES[s]["conifer"]: c = ["Sitka spruce", "Grand fir", "Western red cedar", "Douglas-fir"]
        else: c = ["Bigleaf maple", "Red alder"]
        out[t["id"]] = c
    return out


def sample(site, cand, rng, locks=None, mgmt=None, events=None):
    """One design: {plot: species} for open plots plus the management choices. locks fixes plots or choices (anchoring).
    mgmt: management settings the designer fixed for this run; events: {event: False} for event modules switched off."""
    locks = locks or {}
    pick = {pid: locks.get(pid) or c[int(rng.integers(len(c)))] for pid, c in cand.items()}
    ch = {k: locks[k] if k in locks else v[int(rng.integers(len(v)))] for k, v in CHOICES.items()}
    return dict(plots=pick, **ch, mgmt=dict(mgmt or {}), events=dict(events or {}))


def to_run(site, d):
    design = dict(trees=[d["plots"][t["id"]] for t in site["trees"]], patch_mix=[RECIPES[d["recipe"]]] * len(site["patches"]))
    return design, dict(nurse=d["nurse"], thin=d["thin"], winter=d["winter"], water=d["water"], **d.get("mgmt", {}))


def run_d(site, d, seed, record=False):
    """Run one sampled design in one future, with its management settings and event switches."""
    design, dec = to_run(site, d)
    return run(site, design, dec, seed=seed, record=record, events=d.get("events") or True)


def measure(res, n_plots):
    """Answers to the designer's questions for one run. Bird scores are the share of years 20-50 in which
    all four habitat tests for that bird are met (the model tests habitat conditions, not bird numbers)."""
    s = res["series"]; y = slice(19, None)
    jay = np.all([s[k][y] for k in TESTS[:4]], 0).mean(); hum = np.all([s[k][y] for k in TESTS[4:]], 0).mean()
    e = s["eco"]; drop = float((np.maximum.accumulate(e) - e).max())
    return [jay, hum, 1 - s["died"].sum() / (n_plots + s["died"].sum()),      # share of all trees ever planted that did not die
            *[s["canopy"][i] for i in (9, 19, 29, 39, 49)], s["structure"][49], s["three_layers"][49],
            s["trees_stressed"][49] / max(s["trees_alive"][49], 1), e[y].mean(), drop,
            1 - s["died_young"].sum() / max(s["planted"].sum(), 1),             # plantings that got through their first five years
            s["first_alive"][49] / n_plots, s["trees_alive"][49] / n_plots,     # first-planted trees alive at 50; plots holding a living tree
            s["died"].sum() / max(s["trees_alive"].sum(), 1),
            float(np.sum([s[k][y] for k in TESTS[:4]], 0).mean()), float(np.sum([s[k][y] for k in TESTS[4:]], 0).mean()),
            *[float(s[k][y].mean()) for k in TESTS], *[float(s[k].sum()) for k in ("d_dry", "d_heat", "d_dry2", "d_age", "d_shade", "d_wind")]]   # conditions met per year, of four                   # deaths per tree per year: a result, not an input


def explore(site, cand=None, n_designs=200, n_futures=30, seed=0, locks=None, designs=None, progress=None, mgmt=None, events=None):
    """Returns designs (list of dicts) and X[design, future, metric]. Futures 0..n_futures-1 are shared by all designs."""
    cand = cand or candidates(site); rng = np.random.default_rng([seed, 9])
    designs = designs or [sample(site, cand, rng, locks, mgmt, events) for _ in range(n_designs)]
    X = np.zeros((len(designs), n_futures, len(METRICS)))
    for i, d in enumerate(designs):
        for f in range(n_futures):
            X[i, f] = measure(run_d(site, d, f), len(site["trees"]))
        if progress and (i + 1) % progress == 0: print(f"  {i + 1}/{len(designs)} designs", flush=True)
    return designs, X


def category(X, bar=0.7):
    """Class of each run: which birds have their habitat conditions met in at least `bar` of years 20-50 (J)."""
    j = X[..., METRICS.index("jay")] >= bar; h = X[..., METRICS.index("hum")] >= bar
    return np.where(j & h, 0, np.where(j, 1, np.where(h, 2, 3)))


def leverage(designs, X, metric="eco"):
    """For every open plot and every choice: mean outcome under each option, and the gap between the best and
    worst option. A large gap means this choice matters; a small one means it can be left to taste.
    Neighbour effects are averaged out here: lock the large-gap choices and run again to see them."""
    m = X[..., METRICS.index(metric)].mean(1); rows = []
    keys = [("plot", p) for p in designs[0]["plots"]] + [("choice", k) for k in CHOICES]
    for kind, k in keys:
        val = [d["plots"][k] if kind == "plot" else d[k] for d in designs]
        opts = sorted(set(val), key=str)
        if len(opts) < 2: continue
        means = {str(o): float(m[[v == o for v in val]].mean()) for o in opts}
        rows.append(dict(kind=kind, name=k, means=means, gap=max(means.values()) - min(means.values()),
                         best=max(means, key=means.get)))
    return sorted(rows, key=lambda r: -r["gap"])


def frames(site, d, seed, every=10):
    """What the front end draws for one storyline: tree and shrub state at year 0 marks, then every `every` years.
    Only the design and the seed need storing; this is recomputed when the storyline is opened."""
    res = run_d(site, d, seed, record=True); s = res["series"]; out = []
    for y in [0] + list(range(every - 1, len(res["record"]), every)):
        r = res["record"][y]
        out.append(dict(year=y + 1, trees=[dict(id=t["id"], species=sp, h=h, r=rr, health=hl)
                                           for t, sp, h, rr, hl in zip(site["trees"], res["species"], r["h"], r["r"], r["health"])],
                        patches=[dict(id=p["id"], cover=c) for p, c in zip(site["patches"], r["cover"])],
                        canopy=float(s["canopy"][y]), structure=float(s["structure"][y]), three_layers=float(s["three_layers"][y]),
                        alive=int(s["trees_alive"][y]), stressed=int(s["trees_stressed"][y]),
                        tests={k: bool(s[k][y]) for k in TESTS}))
    ev = {k: [int(i) + 1 for i in np.where(v)[0]] for k, v in res["events"].items()}
    return dict(design=d, seed=seed, frames=out, events=ev)


def site_json(site, path):
    """Static base for the front end: class and elevation of every cell, plot positions. Written once."""
    json.dump(dict(cs=site["cs"], xs=[float(site["xs"][0]), float(site["xs"][-1])], ys=[float(site["ys"][0]), float(site["ys"][-1])],
                   cls=site["cls"].tolist(), z=np.round(site["E"], 2).tolist(), patch_id=site["patch_id"].tolist(),
                   trees=[dict(id=t["id"], x=t["x"], y=t["y"], X=t["X"], Y=t["Y"]) for t in site["trees"]],
                   patches=[dict(id=q["id"], area=q["area"]) for q in site["patches"]]), open(path, "w"))
