"""Pixel plan and block model of the site for one year of one run. Style test for the front end.
Usage: python3 render_views.py [year] [out_prefix]"""
import sys, math, numpy as np
from PIL import Image, ImageDraw, ImageFont
from engine.site import build_site, PATH, IMPERV, GREEN, SHRUB, PARCEL, OUT
from engine.model import run, default_design
from render_section import COLS, FORM, TRUNK_SHARE, SHRUB_TYPES, TYPE_OF

GROUND = {GREEN: "#A6CFC3", SHRUB: "#4A9E9B", PATH: "#00131E", IMPERV: "#074851", PARCEL: "#F5F2F7", 1: "#8FA3A8"}
rgb = lambda c: tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))
mixc = lambda a, b, k: tuple(int(x + (y - x) * k) for x, y in zip(rgb(a) if isinstance(a, str) else a, rgb(b) if isinstance(b, str) else b))
def font(n=10):
    for path in ("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", "/tmp/DejaVuSansMono.ttf"):
        try: return ImageFont.truetype(path, n)
        except Exception: pass
    return ImageFont.load_default()


def state(year):
    S = build_site("inputs/nootka_geom.json", "inputs/contours.json", "inputs/plots.json", 1.0)
    R = run(S, default_design(S), seed=0, record=True, events=False)
    return S, R, R["record"][year - 1]


def plan(S, R, rec, year, out, cut_x=31.0):
    B, PX = 0.5, 5; cls = S["cls"]; ny, nx = cls.shape; W, H = int(nx / B), int(ny / B); pad = 46
    im = Image.new("RGB", (W * PX + 2 * pad, H * PX + 2 * pad + 20), "#00131E"); d = ImageDraw.Draw(im); f = font()
    flip = S["ys"][0] < S["ys"][-1]                                    # put north at the top
    row = lambda j: (ny - 1 - j) if flip else j
    rng = np.random.default_rng(7)
    pid = S["patch_id"]; cover = rec["cover"]; kinds = list(SHRUB_TYPES)
    for j in range(ny):
        for i in range(nx):
            c = int(cls[j, i])
            if c == OUT: continue
            x0, y0 = pad + i * 2 * PX, pad + row(j) * 2 * PX
            for a in range(2):
                for b in range(2):
                    col = rgb(GROUND.get(c, "#8FA3A8"))
                    if c == GREEN and rng.random() < 0.10: col = mixc(col, "#4A9E9B", 0.25)       # groundcover speckle
                    if c == SHRUB and rng.random() < 0.75 * cover[pid[j, i]]:                    # shrub blocks by type
                        k = kinds[int(rng.integers(len(kinds)))]; col = rgb(SHRUB_TYPES[k][2][int(rng.integers(3))])
                        if rng.random() < 0.06: col = rgb(SHRUB_TYPES[k][3])
                    d.rectangle([x0 + a * PX, y0 + b * PX, x0 + (a + 1) * PX - 1, y0 + (b + 1) * PX - 1], fill=col)
    xs, ys = S["xs"], S["ys"]
    X = lambda x: pad + (x - xs[0] + 0.5) / B * PX
    Y = lambda y: pad + ((ys[-1] - y + 0.5) if flip else (y - ys[0] + 0.5)) / B * PX
    order = sorted([k for k in range(len(S["trees"])) if rec["alive"][k]], key=lambda k: rec["h"][k])
    for sh in (True, False):                                           # shadows first, then crowns, short trees first
        for k in order:
            t = S["trees"][k]; r = rec["r"][k] / B; cx, cy = X(t["X"]) / PX, Y(t["Y"]) / PX; sp = R["species"][k]
            off = min(3.0, rec["h"][k] / 6)
            for by in range(int(cy - r - 4), int(cy + r + 5)):
                for bx in range(int(cx - r - 4), int(cx + r + 5)):
                    dx, dy = bx + .5 - cx, by + .5 - cy
                    if sh:
                        if (dx - off) ** 2 + (dy - off) ** 2 <= r * r:
                            p = (bx * PX + 1, by * PX + 1)
                            if 0 <= p[0] < im.width and 0 <= p[1] < im.height:
                                d.rectangle([bx * PX, by * PX, bx * PX + PX - 1, by * PX + PX - 1], fill=mixc(im.getpixel(p), "#00131E", 0.35))
                    elif dx * dx + dy * dy <= r * r:
                        q = (dx + dy) / max(r, 1)                      # light from the north-west
                        col = COLS[sp][0 if q < -0.45 else (2 if q > 0.5 else 1)]
                        if FORM[sp] == "conifer" and dx * dx + dy * dy < 1.2: col = COLS[sp][0]
                        d.rectangle([bx * PX, by * PX, bx * PX + PX - 1, by * PX + PX - 1], fill=col)
    for k in order:
        t = S["trees"][k]; d.text((X(t["X"]) - 9, Y(t["Y"]) - 5), t["id"], fill="#00131E" if FORM[R["species"][k]] != "conifer" else "#F5F2F7", font=f)
    for q in S["parcels"]:
        jj, ii = np.where(S["parcel_id"] == q["id"])
        if len(ii) >= 50: d.text((pad + ii.mean() * 2 * PX - 8, pad + row(int(jj.mean())) * 2 * PX), f"{q['storeys']}F", fill="#074851", font=f)
    cx = pad + cut_x / B * PX; yb = pad + H * PX
    for y in range(pad - 12, yb + 12, 10): d.line([(cx, y), (cx, y + 5)], fill="#F2B766", width=1)
    d.text((cx - 22, pad - 26), "section", fill="#F2B766", font=f)
    d.text((pad, 12), f"Nootka plan, year {year}. Style test, no events. Not a result.", fill="#A6CFC3", font=f)
    d.text((im.width - pad - 8, pad - 28), "N", fill="#F5F2F7", font=f); d.line([(im.width - pad - 5, pad - 14), (im.width - pad - 5, pad - 4)], fill="#F5F2F7")
    d.rectangle([pad, yb + 22, pad + 10 / B * PX, yb + 25], fill="#F5F2F7"); d.text((pad, yb + 28), "10 m", fill="#F5F2F7", font=f)
    lx = pad + 130
    for name in ["Sitka spruce", "Western red cedar", "Bigleaf maple", "Red alder", "Vine maple"]:
        d.rectangle([lx, yb + 22, lx + 9, yb + 31], fill=COLS[name][1]); d.text((lx + 13, yb + 21), {"Sitka spruce":"spruce","Western red cedar":"cedar","Bigleaf maple":"bigleaf","Red alder":"alder","Vine maple":"vine maple"}[name], fill="#B9CFD0", font=f); lx += 74
    im.save(out); print(out, im.size)


def model(S, R, rec, year, out):
    cls, E = S["cls"], S["E"]; ny, nx = cls.shape; TW, TH, ZH = 12, 6, 7                    # tile width/height, pixels per metre up
    flip = S["ys"][0] > S["ys"][-1]                                                        # b grows to the north
    zmin = math.floor(np.nanmin(E[cls != OUT])) - 1
    cubes = []                                                                             # (a, b, z, kind, colour, height)
    rng = np.random.default_rng(3); pid = S["patch_id"]; cover = rec["cover"]; kinds = list(SHRUB_TYPES); gz = {}
    for j in range(ny):
        for i in range(nx):
            c = int(cls[j, i])
            if c == OUT: continue
            b = (ny - 1 - j) if flip else j; z = round((E[j, i] - zmin) * 2) / 2; gz[(i, b)] = z
            col = "#C9C4CF" if c == PARCEL else GROUND.get(c, "#8FA3A8")
            cubes.append((i, b, 0, "ground", col, z))
            if c == SHRUB and rng.random() < 0.6 * cover[pid[j, i]]:
                k = kinds[int(rng.integers(len(kinds)))]; hgt = max(1, round(SHRUB_TYPES[k][0] * min(1, year / 6) * rng.uniform(0.6, 1.0)))
                for u in range(hgt): cubes.append((i, b, z + u, "leaf", SHRUB_TYPES[k][2][1] if rng.random() > 0.08 else SHRUB_TYPES[k][3], 1))
    xs, ys = S["xs"], S["ys"]
    for k, t in enumerate(S["trees"]):
        if not rec["alive"][k]: continue
        sp = R["species"][k]; kind = FORM[sp]; h = rec["h"][k]; r = rec["r"][k]
        i = int(round(t["X"] - xs[0])); j = int(round(abs(t["Y"] - ys[0]))); b = (ny - 1 - j) if flip else j
        z0 = gz.get((i, b), 0); Ht = max(1, round(h * TRUNK_SHARE[kind] * min(1, h / 10 + 0.3))); Hn = max(Ht + 1, round(h))
        for u in range(Ht): cubes.append((i, b, z0 + u, "trunk", "#8A6A4F", 1))
        n = Hn - Ht
        for u in range(n):
            tt = (u + 0.5) / n
            rr = r * (1 - 0.85 * tt) if kind == "conifer" else r * math.sqrt(max(0.05, 1 - (2 * tt - 0.75) ** 2 / 1.6))
            R2 = max(0.6, rr) ** 2; m = int(math.ceil(rr))
            for da in range(-m, m + 1):
                for db in range(-m, m + 1):
                    if da * da + db * db <= R2 and (da * da + db * db >= (max(0, rr - 1.6)) ** 2 or u >= n - 2 or u == 0):   # shell only
                        cubes.append((i + da, b + db, z0 + Ht + u, "leaf", COLS[sp][1], 1))
    # buildings: one flat-roofed, see-through volume per parcel (3 m per storey)
    par = S["parcel_id"]; pb = {}
    for j in range(ny):
        for i in range(nx):
            if par[j, i] >= 0: pb[(i, (ny - 1 - j) if flip else j)] = int(par[j, i])
    for q in S["parcels"]:
        cells = [k for k, v in pb.items() if v == q["id"]]
        roof = float(np.mean([gz[k] for k in cells])) + 3.0 * q["storeys"]
        for (a_, b_) in cells:
            cubes.append((a_, b_, gz[(a_, b_)], "bldg", (pb.get((a_, b_ + 1)) != q["id"], pb.get((a_ + 1, b_)) != q["id"]), max(1.0, roof - gz[(a_, b_)])))
    cubes.sort(key=lambda c: (c[0] + c[1], c[2]))
    na, nb = nx, ny; zr = max(c[2] + c[5] for c in cubes)
    Wp = (na + nb) * TW // 2 + 80; Hp = int((na + nb) * TH / 2 + zr * ZH + 110)
    im = Image.new("RGB", (Wp, Hp), "#00131E"); d = ImageDraw.Draw(im, "RGBA"); f = font()
    for rrow in range(Hp):
        kk = rrow / Hp; d.line([(0, rrow), (Wp, rrow)], fill=(int(4 + 8 * kk), int(28 + 46 * kk), int(40 + 50 * kk)))
    ox = 40 + nb * TW // 2; oy = int(zr * ZH) + 60
    for a, b, z, kind, col, hgt in cubes:
        sx = ox + (a - b) * TW // 2; top = oy + (a + b) * TH // 2 - int((z + hgt) * ZH); hh = int(hgt * ZH)
        if kind == "ground": hh = int((z - 0) * ZH) + 6
        if kind == "bldg":
            d.polygon([(sx, top), (sx + TW // 2, top + TH // 2), (sx, top + TH), (sx - TW // 2, top + TH // 2)], fill=(245, 242, 247, 120))
            if col[0]: d.polygon([(sx - TW // 2, top + TH // 2), (sx, top + TH), (sx, top + TH + hh), (sx - TW // 2, top + TH // 2 + hh)], fill=(200, 205, 215, 105))
            if col[1]: d.polygon([(sx + TW // 2, top + TH // 2), (sx, top + TH), (sx, top + TH + hh), (sx + TW // 2, top + TH // 2 + hh)], fill=(150, 160, 175, 105))
            continue
        cT = rgb(col); cL = mixc(col, "#00131E", 0.28); cR = mixc(col, "#00131E", 0.5)
        if kind == "ground": cL, cR = (66, 53, 46), (48, 39, 34)
        d.polygon([(sx, top), (sx + TW // 2, top + TH // 2), (sx, top + TH), (sx - TW // 2, top + TH // 2)], fill=cT)
        d.polygon([(sx - TW // 2, top + TH // 2), (sx, top + TH), (sx, top + TH + hh), (sx - TW // 2, top + TH // 2 + hh)], fill=cL)
        d.polygon([(sx + TW // 2, top + TH // 2), (sx, top + TH), (sx, top + TH + hh), (sx + TW // 2, top + TH // 2 + hh)], fill=cR)
    d.text((20, 14), f"Nootka block model, year {year}, seen from the north-east. Style test, no events. Not a result.", fill="#A6CFC3", font=f)
    d.text((20, 28), "1 block = 1 m", fill="#8FB3B4", font=f)
    im.save(out); print(out, im.size, len(cubes), "blocks")


if __name__ == "__main__":
    year = int(sys.argv[1]) if len(sys.argv) > 1 else 25; pre = sys.argv[2] if len(sys.argv) > 2 else "nootka"
    S, R, rec = state(year); plan(S, R, rec, year, f"{pre}_plan_y{year}.png"); model(S, R, rec, year, f"{pre}_model_y{year}.png")
