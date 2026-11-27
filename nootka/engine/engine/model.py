"""Nootka forest-section model: one run = one possible 50-year future of one design.

Uncertain knowledge (PARAMS, growth rates) is sampled once per run from stream 1 of the seed.
Year-to-year chance (events, which tree dies) comes from stream 2 and is drawn up front, so two
designs run with the same seed meet exactly the same events (common random numbers).
The model tracks habitat conditions, not birds. Competition is limited to shade from taller neighbouring trees."""
import numpy as np
from .species import TREES, SHRUBS, NATIVE_SHRUBS, WINTER_SHARE, PARAMS, H0, months
from .site import OUT

TN = list(TREES)
SN = list(SHRUBS)
SENS = {"high": 1.0, "med": 0.5, "low": 0.15}
TESTS = ["J1", "J2", "J3", "J4", "H1", "H2", "H3", "H4"]
SERIES = ["eco", "jay", "hum", "structure", "diversity", "canopy", "three_layers", "months", "nectar_early",
          "berry", "open", "conifers_alive", "nest_trees", "trees_alive", "trees_stressed", "died", "died_young", "planted", "first_alive", "shrub_cover", "invaded",
          "d_dry", "d_heat", "d_dry2", "d_age", "d_shade", "d_wind"] + TESTS
EVENTS = ["dry", "dry2", "heat", "wind", "wind_extreme", "snow", "budget_cut"]
CAUSES = ["dry summer", "heat wave", "second dry summer in a row", "end of lifespan", "shade", "wind storm"]
# management settings. The first four are the ones the engine explores in run 0; the rest are set by the designer.
DEFAULT_DEC = dict(winter=0, thin=0, water=2, nurse=0,
                   water_dry=0,                # emergency watering of established trees in dry summers
                   replant="same",             # same | tolerant (a conifer lost to drought comes back as Douglas-fir) | none
                   inv_every=1,                # invasive plants cleared every N years; 0 = never
                   thin_start=10, thin_every=5, thin_method="remove",     # glade: remove | lift (raise the crown, keep the tree) | small (only trees up to 8 m)
                   alder_out=0)                # year the red alders are taken out to release the conifers; 0 = left to their natural lifespan
SWITCHES = ["dry", "heat", "wind", "snow", "ivy", "trample", "budget"]   # event modules that can be switched off
# draft thresholds (Nootka parameters tab, mid-range)
TH = dict(nest_h=8.0, nest_n=3, cover10=0.5, cover_n=2, three=0.40, berry=0.10, months=9, nectar=0.05, open=0.30)


def default_design(site, swap=None):
    """Viola's plan as drawn. swap: {plot id: species} overrides."""
    sp = [(swap or {}).get(t["id"], t["species"]) for t in site["trees"]]
    return dict(trees=sp, patch_mix=None)


def run(site, design, dec=None, seed=0, years=50, record=False, events=True, weights=None):
    dec = {**DEFAULT_DEC, **(dec or {})}
    on = (lambda k: bool(events.get(k, True))) if isinstance(events, dict) else (lambda k: bool(events))
    ep = np.random.default_rng([seed, 1]); al = np.random.default_rng([seed, 2])
    par = {k: ep.uniform(*v) for k, v in PARAMS.items()}
    g_s = {s: ep.uniform(*TREES[s]["growth"]) for s in TN}
    hm_s = {s: ep.uniform(*TREES[s]["hmax"]) for s in TN}
    life_s = {s: (ep.uniform(*TREES[s]["life"]) if TREES[s]["life"] else 1e9) for s in TN}
    nurse_delay = int(ep.integers(5, 11)); cut_len = int(ep.integers(2, 6))

    nt, npch = len(site["trees"]), len(site["patches"]); shape = site["cls"].shape
    U = al.random((years, 6)); UT = al.random((years, nt, 4)); UG = al.random((years, 2) + shape)

    sp = list(design["trees"])
    tx = np.array([t["X"] for t in site["trees"]]); ty = np.array([t["Y"] for t in site["trees"]])
    DIST = np.hypot(tx[:, None] - tx[None, :], ty[:, None] - ty[None, :])
    r = np.zeros(nt)

    def traits():
        return dict(G=np.array([g_s[x] for x in sp]), HM=np.array([hm_s[x] for x in sp]), LIFE=np.array([life_s[x] for x in sp]),
                    CA=np.array([TREES[x]["crown"][0] for x in sp]), CB=np.array([TREES[x]["crown"][1] for x in sp]), CR=np.array([TREES[x]["crown"][2] for x in sp]),
                    CON=np.array([TREES[x]["conifer"] for x in sp], bool), DS=np.array([SENS[TREES[x]["drought"]] for x in sp]),
                    WIND=np.array([par["wind_" + TREES[x]["wind"]] for x in sp]),
                    SHADE=np.array([{"low": 1.0, "med": 0.5, "high": 0.1}[TREES[x]["shade"]] for x in sp]),      # sensitivity to shade
                    SNOWLOW=np.array([TREES[x]["snow"] == "low" for x in sp]), CEDAR=np.array([x == "Western red cedar" for x in sp]),
                    SPRUCE=np.array([x == "Sitka spruce" for x in sp]), MAPLE=np.array(["maple" in x for x in sp]), VINE=np.array([x == "Vine maple" for x in sp]),
                    ALDER=np.array([x == "Red alder" for x in sp]), SPI=np.array([TN.index(x) for x in sp]))
    T = traits(); G, HM, LIFE, CA, CB, CR, CON, DS, WIND, SHADE, SNOWLOW, CEDAR, SPRUCE, MAPLE, VINE, ALDER, SPI = T.values()
    plant_year = np.where(CON & bool(dec["nurse"]), nurse_delay, 0)
    alive = np.zeros(nt, bool); thinned = np.zeros(nt, bool); age = np.zeros(nt); h = np.zeros(nt)
    ever_died = np.zeros(nt, bool); planted_n = 0; lifted = np.zeros(nt, bool); last_cause = np.full(nt, -1)
    vig = np.ones(nt); hurt = np.zeros(nt)      # vigour: running share of potential growth achieved; hurt: years since breakage

    # shrub patches: shares by species
    mix = np.zeros((npch, len(SN)))
    for k in range(npch):
        m = (design.get("patch_mix") or [None] * npch)[k] or {s: 1 / len(NATIVE_SHRUBS) for s in NATIVE_SHRUBS}
        for s, v in m.items():
            mix[k, SN.index(s)] = v
        if dec["winter"]:
            mix[k] *= 1 - WINTER_SHARE; mix[k, SN.index("Winter mahonia")] += WINTER_SHARE
    BLOOM = np.array([[m in months(SHRUBS[s]["bloom"]) for m in range(1, 13)] for s in SN], float)   # species x month
    NECT = np.array([SHRUBS[s]["nectar"] for s in SN]); BERRY = np.array([SHRUBS[s]["berry"] for s in SN], float)
    SSENS = np.array([SENS[SHRUBS[s]["drought"]] for s in SN]); SHOK = np.array([SHRUBS[s]["shade_ok"] for s in SN])
    SHT = np.array([SHRUBS[s]["height"] for s in SN])
    cover = np.zeros(npch)

    green = site["green"]; gflat = green.ravel(); ng = gflat.sum(); garea = ng * site["cs"] ** 2
    inflat = (site["cls"] != OUT).ravel()
    near10 = (site["d2"] <= 100.0) & inflat[None, :]
    pcells = [c.ravel() for c in site["patch_cells"]]; anyp = (site["patch_id"] >= 0).ravel()
    parea = site["patch_area"]
    pathedge = green & (site["dist_path"] <= 2.0)
    inv = np.zeros(shape, bool); comp = np.zeros(shape)
    ti, tj = site["tree_cell"]
    w = weights or dict(structure=1, diversity=1, bloom=1, canopy=1, jay=1, hum=1)
    out = {k: np.zeros(years) for k in SERIES}; ev = {k: np.zeros(years, bool) for k in EVENTS}
    rec = [] if record else None
    prev_dry = False; cut_left = 0

    for t in range(years):
        f = t / max(years - 1, 1)
        dry = on("dry") and U[t, 0] < par["p_dry0"] + f * (par["p_dry50"] - par["p_dry0"])
        heat = on("heat") and U[t, 1] < par["p_heat0"] + f * (par["p_heat50"] - par["p_heat0"])
        wind = on("wind") and U[t, 2] < par["p_wind"]; windx = on("wind") and U[t, 2] < par["p_wind_x"]
        snow = on("snow") and U[t, 3] < par["p_snow"]
        if cut_left > 0: cut_left -= 1
        elif on("budget") and U[t, 4] < par["p_cut"]: cut_left = cut_len
        care = cut_left == 0
        dry2 = dry and prev_dry

        # planting and replacement of losses (only under active care)
        new = (~alive) & (~thinned) & (plant_year <= t) & ((plant_year == t) | (care & (dec["replant"] != "none")))
        if dec["replant"] == "tolerant":         # a conifer lost to drought is replaced with Douglas-fir
            swap = new & ever_died & CON & np.isin(last_cause, (0, 2))
            if swap.any():
                for k in np.where(swap)[0]: sp[k] = "Douglas-fir"
                T = traits(); G, HM, LIFE, CA, CB, CR, CON, DS, WIND, SHADE, SNOWLOW, CEDAR, SPRUCE, MAPLE, VINE, ALDER, SPI = T.values()
        alive[new] = True; age[new] = 0; h[new] = H0; vig[new] = 1.0; hurt[new] = 99; planted_n = int(new.sum())

        watered = (age < dec["water"]) & care
        stressed = dry & ~watered
        gf = np.where(age < 2, 0.3, 1.0) * np.where(stressed, 1 - (1 - par["dry_growth"]) * DS / 1.0, 1.0)
        # shade from taller neighbours (last year's crowns): 0 = open, 1 = stem fully under a taller crown
        taller = alive[None, :] & (h[None, :] > h[:, None] + 2.0)
        shm = np.where(taller, np.clip((r[None, :] + 1.0 - DIST) / 2.0, 0, 1), 0.0)
        shd = shm.max(1) * (h < 10); shader = shm.argmax(1)
        gf = gf * (1 - par["shade_growth"] * SHADE * shd)
        vig = 0.7 * vig + 0.3 * gf / np.where(age < 2, 0.3, 1.0)
        h = np.where(alive, h + G * gf * np.clip(1 - (h / HM) ** 2, 0, 1), 0.0)

        young = age < 5
        shelter = np.where(CON & bool(dec["nurse"]), par["shelter"], 1.0)
        # causes of death this year, each with its own chance; one draw per tree decides if it dies and of what
        steep = np.where(site["tree_slope"] > 20, 1.3, 1.0)
        rescue = par["rescue"] if (dec["water_dry"] and care) else 1.0      # emergency watering of established trees
        comps = [np.where(stressed, np.where(young, par["dry_young"] * shelter, par["dry_old"] * rescue) * DS / 0.5, 0.0) * steep,
                 np.where(young & (shelter == 1.0), par["heat_young"], 0.0) * (1.0 if heat else 0.0),
                 np.where(~young, par["cedar_dieback"] * rescue * (CEDAR + 0.5 * SPRUCE), 0.0) * (1.0 if dry2 else 0.0),
                 np.where(age > LIFE, 0.08, 0.0),
                 par["shade_mort"] * SHADE * shd]
        cum = np.cumsum(comps, 0); u = UT[t, :, 0]
        die = alive & (u < cum[-1]); cause = np.minimum((u[None, :] >= cum).sum(0), len(comps) - 1)
        blown = np.zeros(nt, bool); brk = np.zeros(nt, bool)
        if wind:
            pw = WIND * np.clip((h / 20.0) ** 2, 0, 2.5) * np.where(site["tree_edge"], 1.5, 1.0)
            pw = pw * np.where(inv[ti, tj], 1.3, 1.0) * (1.2 if thinned.any() else 1.0) * (4.0 if windx else 1.0)
            blown = alive & ~die & (h > 6) & (UT[t, :, 1] < pw); die |= blown; cause[blown] = 5
        if snow:
            brk = alive & SNOWLOW & (h > 3) & (UT[t, :, 2] < par["snow_dmg"])
            h[brk] *= 0.85; hurt[brk] = 0
        died_young = int((die & (age < 5)).sum()); ever_died |= die; last_cause[die] = cause[die]; lifted[die] = False
        by_cause = np.bincount(cause[die], minlength=6)
        alive &= ~die; h[~alive] = 0; age[~alive] = 0; age[alive] += 1; hurt += 1
        # health class per tree: 0 dead or not yet planted, 1 stressed, 2 good (J: thresholds)
        health = np.where(alive, np.where((vig < 0.75) | (hurt <= 3) | (age > LIFE), 1, 2), 0)

        r = np.where(alive, np.minimum(CA * h + CB, CR), 0.0)
        crown = site["d2"] <= (r ** 2)[:, None]
        crown &= alive[:, None]
        can = crown.any(0)

        # glade management: open the canopy over the shrub patches. The method is the designer's choice.
        gl = []; lf = []; al_out = []
        cano = crown[~lifted].any(0); canl = crown[lifted].any(0) & ~cano
        if dec["thin"] and t >= dec["thin_start"] and (t - dec["thin_start"]) % max(1, dec["thin_every"]) == 0 \
                and cano[anyp].mean() + par["lift_left"] * canl[anyp].mean() > 0.4:
            ok = alive & ~CON & ~lifted & ((h <= 8.0) if dec["thin_method"] == "small" else True)
            over = np.where(ok, (crown & anyp[None, :]).sum(1), 0)
            if over.max() > 0:
                k = int(over.argmax())
                if dec["thin_method"] == "lift": lifted[k] = True; lf.append(k)
                else:
                    alive[k] = False; thinned[k] = True; h[k] = 0; age[k] = 0; health[k] = 0; crown[k] = False; gl.append(k)
        # red alder taken out in a chosen year to release the conifers
        if dec["alder_out"] and t + 1 == dec["alder_out"]:
            for k in np.where(alive & ALDER)[0]:
                alive[k] = False; thinned[k] = True; h[k] = 0; age[k] = 0; health[k] = 0; crown[k] = False; al_out.append(int(k))
        r = np.where(alive, r, 0.0); can = crown.any(0)
        cano = crown[~lifted].any(0); canl = crown[lifted].any(0) & ~cano
        tall = crown[h > 6].any(0) if (h > 6).any() else np.zeros_like(can)
        sub = crown[(h >= 1.5) & (h <= 6)].any(0) if ((h >= 1.5) & (h <= 6)).any() else np.zeros_like(can)

        # invasive plants and trampling
        if on("ivy"):
            if U[t, 5] < par["p_ivy"]:
                e = np.where(site["entry"], UG[t, 0], -1.0); inv.flat[int(e.argmax())] = True
            nb = np.zeros(shape, bool)
            nb[1:] |= inv[:-1]; nb[:-1] |= inv[1:]; nb[:, 1:] |= inv[:, :-1]; nb[:, :-1] |= inv[:, 1:]
            inv |= nb & green & (UG[t, 0] < par["ivy_spread"])
            if care and dec["inv_every"] and t % dec["inv_every"] == 0: inv[:] = False      # cleared on the chosen cycle, while the site is under care
        if on("trample"):
            comp = np.minimum(1.0, comp + 0.1 * (pathedge & (UG[t, 1] < par["p_trample"])))
        invf = inv.ravel()

        # shrub patches
        cover = np.minimum(1.0, cover + 0.2)
        if dry and not (t < dec["water"] and care):
            cover *= 1 - par["shrub_dry"] * (mix * SSENS).sum(1)
        cc = np.array([cano[c].mean() + par["lift_left"] * canl[c].mean() if c.any() else 0.0 for c in pcells])            # canopy over each patch
        pinv = np.array([invf[c].mean() if c.any() else 0.0 for c in pcells])
        shade = np.clip(1 - (cc[:, None] - SHOK[None, :]) / 0.4, 0, 1)                # patch x species flowering factor
        eff = parea[:, None] * (cover * (1 - pinv))[:, None] * mix                      # m2 of each shrub species
        flower = (eff * shade * (0.7 if heat else 1.0)) @ BLOOM                        # patch x month, m2 in flower
        fl_m = flower.sum(0) / garea
        maple_bloom = bool((alive & MAPLE & (h > 3)).any())
        present = fl_m > 0.005
        if maple_bloom: present[2:6] = True
        nmonths = int(present.sum())
        nect = ((eff * shade * (NECT >= 0.6)[None, :]) @ BLOOM)[:, 1:4].sum(0).max() / garea
        berry = (eff * BERRY[None, :]).sum() / garea
        pheight = min(1.0, (t + 1) / 6) * (mix * SHT).sum(1)

        # layers per green cell
        ground = gflat & ~invf & (comp.ravel() <= 0.6)
        pc = np.zeros(gflat.shape, bool)
        for k, c in enumerate(pcells):
            if cover[k] >= 0.5: pc |= c
        shr = (pc | sub) & gflat
        layers = ground.astype(int) + shr + (tall & gflat)
        structure = layers[gflat].mean() / 3; three = (layers[gflat] == 3).mean()
        canopy = can[gflat].mean(); openshare = 1 - canopy

        nest = alive & CON & (h >= TH["nest_h"])
        J1 = nest.sum() >= TH["nest_n"]
        c10 = np.array([can[near10[i]].mean() for i in np.where(nest)[0]]) if nest.any() else np.array([])
        J2 = (c10 >= TH["cover10"]).sum() >= TH["cover_n"]
        J3 = three >= TH["three"]; J4 = berry >= TH["berry"]
        H1 = nmonths >= TH["months"]; H2 = nect >= TH["nectar"]
        H3 = bool(nect > 0 and ((alive & VINE & (h >= 2)).any() or (pheight >= 2).any()))
        H4 = openshare >= TH["open"]
        tests = [J1, J2, J3, J4, H1, H2, H3, H4]
        jay = sum(tests[:4]) / 4; hum = sum(tests[4:]) / 4
        areas = np.concatenate([np.bincount(SPI, weights=np.pi * r ** 2, minlength=len(TN)), eff.sum(0)])
        p = areas[areas > 0] / areas.sum() if areas.sum() > 0 else np.array([1.0])
        diversity = float(-(p * np.log(p)).sum() / np.log(len(TN) + len(SN)))
        parts = dict(structure=structure, diversity=diversity, bloom=nmonths / 12, canopy=min(canopy / 0.6, 1), jay=jay, hum=hum)
        eco = sum(w[k] * parts[k] for k in parts) / sum(w.values())

        vals = dict(eco=eco, jay=jay, hum=hum, structure=structure, diversity=diversity, canopy=canopy, three_layers=three,
                    months=nmonths, nectar_early=nect, berry=berry, open=openshare, conifers_alive=(alive & CON).sum(),
                    nest_trees=nest.sum(), trees_alive=alive.sum(), trees_stressed=(health == 1).sum(), died=die.sum(), died_young=died_young, d_dry=by_cause[0], d_heat=by_cause[1], d_dry2=by_cause[2], d_age=by_cause[3], d_shade=by_cause[4], d_wind=by_cause[5], planted=planted_n, first_alive=(alive & ~ever_died & ~thinned).sum(), shrub_cover=float((cover * parea).sum() / parea.sum()),
                    invaded=invf[gflat].mean(), **dict(zip(TESTS, tests)))
        for k, v in vals.items(): out[k][t] = v
        for k, v in zip(EVENTS, [dry, dry2, heat, wind, windx, snow, not care]): ev[k][t] = v
        if record:
            rec.append(dict(h=h.round(2).tolist(), r=r.round(2).tolist(), alive=alive.tolist(), health=health.tolist(), thinned=thinned.tolist(), sp=list(sp), glade=gl, lifted=lf, alder_out=al_out,
                            shd=shd.round(2).tolist(), shader=shader.tolist(),
                            died=np.where(die)[0].tolist(), cause=[CAUSES[c] for c in cause[die]], blown=np.where(blown)[0].tolist(), broken=np.where(brk)[0].tolist(), age=age.tolist(),
                            cover=cover.round(2).tolist(), pcan=cc.round(2).tolist(), pinv=pinv.round(2).tolist(), inv=np.packbits(inv).tolist(), comp=np.packbits(comp > 0.6).tolist()))
        prev_dry = dry
    return dict(series=out, events=ev, species=list(design["trees"]), dec=dec, seed=seed, record=rec, params=par, nurse_delay=nurse_delay)


def recovery(series, drop=0.05):
    """Largest fall of the eco index from its running peak, and years taken to get back within 2% of that peak
    (np.nan if it never does). A simple resilience read-out per run."""
    e = np.asarray(series); peak = np.maximum.accumulate(e); dd = peak - e
    if dd.max() < drop: return 0.0, 0.0
    i = int(dd.argmax()); back = np.where(e[i:] >= peak[i] - 0.02)[0]
    return float(dd.max()), (float(back[0]) if len(back) else float("nan"))
