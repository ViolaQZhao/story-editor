"""Self-checks for the Nootka engine. Run: python3 tests_check.py"""
import numpy as np
from engine.site import build_site
from engine.model import run, default_design
S=build_site('inputs/nootka_geom.json','inputs/contours.json','inputs/plots.json',1.0)
D=default_design(S); spruce=[t['id'] for t in S['trees'] if t['species']=='Sitka spruce']
F=default_design(S,{i:'Grand fir' for i in spruce})
N=200
def alive_con(R): return R['series']['conifers_alive']
# 1 reproducible
assert np.array_equal(run(S,D,seed=3)['series']['eco'],run(S,D,seed=3)['series']['eco'])
# 2 common random numbers
a,b=run(S,D,seed=3),run(S,F,seed=3); assert all(np.array_equal(a['events'][k],b['events'][k]) for k in a['events'])
# 3 no events -> never worse on average than with events for trees alive
ne=np.mean([run(S,D,seed=s,events=False)['series']['trees_alive'].mean() for s in range(60)])
we=np.mean([run(S,D,seed=s)['series']['trees_alive'].mean() for s in range(60)])
print('trees alive, no events vs events',round(ne,2),round(we,2)); assert ne>=we
# 4 dry summers in the first five unwatered years cost more young trees than wet ones
loss={True:[],False:[]}
for s in range(N):
    R=run(S,D,seed=s); 
    for t in range(2,5): loss[bool(R['events']['dry'][t])].append(R['series']['trees_alive'][t-1]-R['series']['trees_alive'][t])
print('trees lost per year, years 3-5: dry',round(np.mean(loss[True]),2),'not dry',round(np.mean(loss[False]),2)); assert np.mean(loss[True])>np.mean(loss[False])
# 5 5-year watering protects young trees in dry years
w2=np.mean([run(S,D,dict(water=2),seed=s)['series']['trees_alive'][:6].mean() for s in range(N)])
w5=np.mean([run(S,D,dict(water=5),seed=s)['series']['trees_alive'][:6].mean() for s in range(N)])
print('trees alive years 1-6: water 2 yr',round(w2,2),'5 yr',round(w5,2)); assert w5>=w2
# 6 storms take more conifers when the seven plots are Sitka spruce than grand fir (storm years after year 25)
ds,df=[],[]
for s in range(N):
    a,b=run(S,D,seed=s),run(S,F,seed=s)
    for t in range(25,50):
        if a['events']['wind'][t]: ds.append(alive_con(a)[t-1]-alive_con(a)[t]); df.append(alive_con(b)[t-1]-alive_con(b)[t])
print('conifers lost in a storm year: spruce design',round(np.mean(ds),2),'fir design',round(np.mean(df),2)); assert np.mean(ds)>np.mean(df)
# 7 grid size: 1 m against 0.5 m
S5=build_site('inputs/nootka_geom.json','inputs/contours.json','inputs/plots.json',0.5); D5=default_design(S5)
e1=np.array([run(S,D,seed=s)['series']['eco'][[9,24,49]] for s in range(40)]); e5=np.array([run(S5,D5,seed=s)['series']['eco'][[9,24,49]] for s in range(40)])
print('eco index mean abs difference 1 m vs 0.5 m:',np.abs(e1-e5).mean().round(3),' correlation across runs:',np.corrcoef(e1.ravel(),e5.ravel())[0,1].round(3))
# 8 shade: Douglas-fir at the five cedar plots grows more slowly where taller neighbours stand close
CED=[t['id'] for t in S['trees'] if t['species']=='Western red cedar']; DF=default_design(S,{i:'Douglas-fir' for i in CED})
hh=np.zeros((2,len(CED)))
for s in range(60):
    for k,ev in enumerate([run(S,DF,seed=s,events=False,record=True)]):
        h=np.array(ev['record'][29]['h']); hh[0]+=[h[[t['id'] for t in S['trees']].index(i)] for i in CED]
print('Douglas-fir height at year 30 at the cedar plots (no events):',dict(zip(CED,(hh[0]/60).round(1))))
print('all checks passed')

# 9. exploration: sampling respects candidates and locks, results repeat exactly, storyline frames export
from engine import explore as ex
import json as _json, time as _time
site = S
cand = ex.candidates(site); opened = [p for p, c in cand.items() if len(c) > 1]
assert opened == ["T04", "T08", "T13", "T14", "T15"], opened
t0 = _time.time(); D, X = ex.explore(site, n_designs=12, n_futures=6, seed=1, locks={"T04": "Douglas-fir", "water": 5})
assert all(d["plots"]["T04"] == "Douglas-fir" and d["water"] == 5 for d in D)
D2, X2 = ex.explore(site, n_designs=12, n_futures=6, seed=1, locks={"T04": "Douglas-fir", "water": 5})
assert np.array_equal(X, X2) and np.isfinite(X).all() and (X[..., :11] >= 0).all() and (X[..., :11] <= 1.0001).all()
co = ex.candidates(site, "open"); assert sum(len(c) > 1 for c in co.values()) == 24
fr = ex.frames(site, D[0], seed=3); assert [f["year"] for f in fr["frames"]] == [1, 10, 20, 30, 40, 50]
assert set(t["health"] for f in fr["frames"] for t in f["trees"]) <= {0, 1, 2}
assert len(ex.leverage(D, X)) >= 5 and set(np.unique(ex.category(X))) <= {0, 1, 2, 3}
print(f"9. exploration ok: 72 runs in {_time.time() - t0:.1f} s; one storyline = {len(_json.dumps(fr)) / 1024:.0f} KB")
print("all checks passed (incl. exploration)")

# 10. management modules and event switches behave as intended
D0 = default_design(S)
def tot(dec=None, events=True, key="died", n=25): return float(np.mean([run(S, D0, dec, seed=q, events=events)["series"][key].sum() for q in range(n)]))
base = tot(); assert tot(dict(water=5)) <= base and tot(dict(water_dry=1)) <= base, "watering should not raise losses"
assert tot(events=dict(dry=False)) < base and tot(events=dict(dry=False), key="d_dry") == 0 and tot(events=dict(wind=False), key="d_wind") == 0
assert tot(dict(replant="none"), key="planted") == 32 and tot(dict(replant="none"), key="trees_alive") < tot(key="trees_alive")
inv = lambda dec: float(np.mean([run(S, D0, dec, seed=q)["series"]["invaded"].mean() for q in range(25)])); assert inv(dict(inv_every=0)) > inv(dict(inv_every=5)) >= inv(None)
for meth in ("remove", "lift", "small"):
    Rm = run(S, D0, dict(thin=1, thin_method=meth), seed=3, record=True); gl = sum(len(f["glade"]) for f in Rm["record"]); lf = sum(len(f["lifted"]) for f in Rm["record"])
    assert (meth == "lift") == (lf > 0 and gl == 0), (meth, gl, lf)
Ra = run(S, D0, dict(alder_out=20), seed=3, record=True); assert len(Ra["record"][19]["alder_out"]) > 0 and "Red alder" not in [x for x, a_ in zip(Ra["record"][25]["sp"], Ra["record"][25]["alive"]) if a_]
Rt = [run(S, D0, dict(replant="tolerant"), seed=q, record=True)["record"][-1]["sp"].count("Douglas-fir") for q in range(25)]; assert max(Rt) > 0
print("10. management and switches ok: losses per run", round(base, 1), "| water 5:", round(tot(dict(water=5)), 1), "| emergency watering:", round(tot(dict(water_dry=1)), 1), "| no dry summers:", round(tot(events=dict(dry=False)), 1))
print("all checks passed (incl. management)")
