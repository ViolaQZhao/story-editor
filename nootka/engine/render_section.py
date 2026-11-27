"""Pixel section through the site: stepped terrain, trees assembled from parts, shrub tufts by type.
Style test for the front end. Usage: python3 render_section.py [year] [out.png]"""
import sys, math, numpy as np
from PIL import Image, ImageDraw, ImageFont
from engine.site import build_site, PATH, IMPERV, GREEN, SHRUB, PARCEL, OUT
from engine.model import run, default_design
from engine.species import TREES

C = 0.5                                  # metres per drawn block
PX = 5                                   # screen pixels per block
FORM = {"Douglas-fir": "conifer", "Western red cedar": "conifer", "Sitka spruce": "conifer", "Grand fir": "conifer",
        "Bigleaf maple": "broadleaf", "Red alder": "broadleaf", "Vine maple": "small"}
COLS = {"Douglas-fir": ["#7FB08A", "#4C8562", "#2B5A44"], "Western red cedar": ["#A3C27A", "#6F9450", "#456A36"],
        "Sitka spruce": ["#8CC0C6", "#4F8E99", "#2C6170"], "Grand fir": ["#9CCBA6", "#63A078", "#3C7355"],
        "Bigleaf maple": ["#DAD27A", "#ADA94A", "#7B7A30"], "Red alder": ["#C6D896", "#93AD66", "#667E44"],
        "Vine maple": ["#EDB878", "#CD8A45", "#9A5D2C"]}
TAPER = dict(conifer=0.8, broadleaf=0.0, small=0.0)
TRUNK_SHARE = dict(conifer=0.18, broadleaf=0.35, small=0.25)      # placeholder until crown base is modelled


def blank(w, h): return np.zeros((h, w), int)
def shade(x, w): return 1 if x < w * 0.3 else (3 if x > w * 0.68 else 2)


def parts(kind):                          # same starter parts as the canvas tool
    P = {}
    if kind == "conifer":
        t = blank(16, 8)
        for y in range(8):
            hw = max(1, round((y + 1) * 0.9))
            for x in range(8 - hw, 8 + hw): t[y, x] = shade(x - (8 - hw), hw * 2)
        b = blank(16, 4)
        for y in range(4):
            i = [2, 1, 0, 1][y]
            for x in range(i, 16 - i): b[y, x] = shade(x, 16)
        b[2, 0] = b[2, 15] = 3
        s = blank(16, 3)
        for y in range(3):
            i = [0, 1, 4][y]
            for x in range(i, 16 - i): s[y, x] = 3 if y == 2 else shade(x, 16)
    else:
        w, th = (12, 4) if kind == "small" else (16, 6)
        t = blank(w, th)
        for y in range(th):
            hw = max(1, round(w / 2 * math.sqrt(1 - (1 - (y + .5) / th) ** 2)))
            for x in range(w // 2 - hw, w // 2 + hw): t[y, x] = shade(x, w)
        b = blank(w, 3)
        for y in range(3):
            for x in range(w): b[y, x] = 3 if (x + y * 3) % 7 == 0 else shade(x, w)
        s = blank(w, 4)
        for y in range(4):
            hw = max(1, round(w / 2 * math.sqrt(1 - ((y + .5) / 4) ** 2)))
            for x in range(w // 2 - hw, w // 2 + hw): s[y, x] = 3 if y > 1 else shade(x, w)
    tr = blank(4, 4); tr[:, :2] = 4; tr[:, 2:] = 5
    P.update(top=t, body=b, base=s, trunk=tr); return P


def assemble(kind, Hm, trunk_m, Wm):
    P = parts(kind); H = max(1, round(Hm / C)); tw = max(1, round(4 * min(1, 0.35 + 0.65 * Hm / 30)))
    Ht = min(H - 1, max(0, round(trunk_m / C))); Hc = H - Ht; W = max(1, round(Wm / C)); rows = []
    for i in range(Ht):
        y = 3 - (i % 4); rows.append([P["trunk"][y, int((x + .5) / tw * 4)] for x in range(tw)])
    n = max(0, round((Hc - len(P["top"]) - len(P["base"])) / len(P["body"])))
    stack = list(P["top"]) + list(P["body"]) * n + list(P["base"])
    for i in range(Hc - 1, -1, -1):
        src = stack[min(len(stack) - 1, int((i + .5) / Hc * len(stack)))]; t = (i + .5) / Hc
        wi = max(1, round(W * (1 - TAPER[kind] * (1 - t))))
        rows.append([src[int((x + .5) / wi * len(src))] for x in range(wi)])
    return rows                            # bottom-up


# shrub types: (height m, width blocks, colours light/mid/dark, accent)
SHRUB_TYPES = {
    "tall":      (3.0, 6, ["#B9D98C", "#7FA65A", "#557A3E"], "#F5F2F7"),   # oceanspray, osoberry
    "thicket":   (2.2, 5, ["#9FD0A0", "#5E9E73", "#3B7052"], "#E9788A"),   # salmonberry, thimbleberry
    "low_decid": (1.5, 4, ["#C9E2C2", "#8DB894", "#5F8C6B"], "#F5F2F7"),   # snowberry
    "low_ever":  (1.0, 5, ["#5FA39A", "#2F7A77", "#1B5557"], "#2B2F5A"),   # salal
}
TYPE_OF = dict(Oceanspray="tall", Osoberry="tall", Salmonberry="thicket", Thimbleberry="thicket", Snowberry="low_decid", Salal="low_ever")


def tuft(kind, grow, rng):
    hm, w, cols, acc = SHRUB_TYPES[kind]; h = max(1, round(hm * grow / C)); out = {}
    for y in range(h):
        k = math.sqrt(max(0.0, 1 - (y / max(h, 1)) ** 2)) if kind != "tall" else (0.55 + 0.45 * math.sin(math.pi * (y + .5) / h))
        hw = max(1, round(w / 2 * k))
        for x in range(-hw, hw):
            c = cols[0] if x < -hw * 0.3 else (cols[2] if x > hw * 0.4 else cols[1])
            if rng.random() < 0.10 and y > h * 0.4: c = acc
            out[(x, y)] = c
    return out


def main(year=25, out="section_test.png"):
    S = build_site("inputs/nootka_geom.json", "inputs/contours.json", "inputs/plots.json", 1.0)
    R = run(S, default_design(S), seed=0, record=True, events=False)
    rec = R["record"][year - 1]; xs, ys, E, cls = S["xs"], S["ys"], S["E"], S["cls"]
    tx = np.array([t["X"] for t in S["trees"]]); ty = np.array([t["Y"] for t in S["trees"]])
    alive = np.array(rec["alive"]); HALF = 6.0
    # north-south cut that passes the most living trees and crosses shrub patches
    best = max(range(len(xs)), key=lambda j: (alive & (abs(tx - xs[j]) <= HALF)).sum() + 0.1 * (cls[:, j] == SHRUB).sum())
    x0 = xs[best]; col = cls[:, best]; inside = np.where(col != OUT)[0]; i0, i1 = inside.min(), inside.max()
    yy = ys[i0:i1 + 1]; zz = E[i0:i1 + 1, best]; cc = col[i0:i1 + 1]
    if yy[0] > yy[-1]: yy, zz, cc = yy[::-1], zz[::-1], cc[::-1]         # south on the left
    ymin = yy[0]; zmin = math.floor(np.nanmin(zz)) - 2.0
    near = [k for k in range(len(tx)) if alive[k] and abs(tx[k] - x0) <= HALF and yy[0] <= ty[k] <= yy[-1]]
    hmax = max([rec["h"][k] for k in near] + [5]); zmax = np.nanmax(zz) + hmax + 3
    nb_x = int((yy[-1] - ymin + 1) / C) + 8; nb_y = int((zmax - zmin) / C)
    Wp, Hp = nb_x * PX + 90, nb_y * PX + 70
    im = Image.new("RGB", (Wp, Hp), "#00131E"); d = ImageDraw.Draw(im)
    for r in range(Hp):                                                    # sky
        k = r / Hp; d.line([(0, r), (Wp, r)], fill=(int(7 + 10 * k), int(40 + 50 * k), int(52 + 55 * k)))
    X = lambda m: 60 + int(round((m - ymin) / C)) * PX
    Y = lambda z: Hp - 40 - int(round((z - zmin) / C)) * PX
    def block(bx, by, c): d.rectangle([bx, by - PX, bx + PX - 1, by - 1], fill=c)
    TOP = {GREEN: "#A6CFC3", SHRUB: "#4A9E9B", PATH: "#F5F2F7", IMPERV: "#8FA3A8", PARCEL: "#D9D2DD"}
    ground = lambda m: float(np.interp(m, yy, zz))
    for b in range(int((yy[-1] - ymin + 1) / C)):                          # stepped terrain, one column per 0.5 m
        m = ymin + b * C; z = ground(m); c = cc[min(len(cc) - 1, int(round(m - ymin)))]
        top = Y(z); bx = 60 + b * PX
        d.rectangle([bx, top, bx + PX - 1, Hp - 40], fill="#3A2F2A" if (b // 2) % 2 else "#42352E")
        block(bx, top + PX, TOP.get(int(c), "#6E6A66"))
    rng = np.random.default_rng(4)
    for b in range(0, int((yy[-1] - ymin + 1) / C), 3):                    # shrub tufts where the cut crosses a patch
        m = ymin + b * C; i = min(len(cc) - 1, int(round(m - ymin)))
        if cc[i] != SHRUB: continue
        kind = TYPE_OF[list(TYPE_OF)[int(rng.integers(6))]]
        if rng.random() > 0.9: continue
        t = tuft(kind, min(1.0, year / 6), rng); gx = X(m); gy = Y(ground(m))
        for (x, y), c in t.items(): block(gx + x * PX, gy - y * PX, c)
    order = sorted(near, key=lambda k: -abs(tx[k] - x0))                    # far trees first
    for k in order:
        sp = R["species"][k]; kind = FORM[sp]; h = rec["h"][k]; w = 2 * rec["r"][k]
        rows = assemble(kind, h, h * TRUNK_SHARE[kind] * min(1, h / 10 + 0.3), w)
        far = abs(tx[k] - x0) > 3; gx = X(ty[k]); gy = Y(ground(ty[k]))
        pal = [None] + COLS[sp] + ["#B08A66", "#6E5240", "#F2D06B", "#02202B"]
        for i, r in enumerate(rows):
            bx0 = gx - len(r) * PX // 2
            for x, v in enumerate(r):
                if not v: continue
                c = pal[v]
                if far:                                                    # trees behind the cut: pushed toward the sky colour
                    c = "#%02x%02x%02x" % tuple(int(int(c[j:j + 2], 16) * 0.55 + q * 0.45) for j, q in zip((1, 3, 5), (14, 68, 80)))
                block(bx0 + x * PX, gy - i * PX, c)
        S["trees"][k]["_lab"] = (gx, gy - len(rows) * PX - 12)
    try: f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 10)
    except Exception: f = ImageFont.load_default()
    for k in near:
        gx, gy = S["trees"][k]["_lab"]; d.text((gx - 9, gy), S["trees"][k]["id"], fill="#F5F2F7", font=f)
    hp = round(1.7 / C) * PX; px_ = X(yy[0] + 3); d.rectangle([px_, Y(ground(yy[0] + 3)) - hp, px_ + 3, Y(ground(yy[0] + 3)) - 1], fill="#F5F2F7")
    bx = 60; by = Hp - 22; d.rectangle([bx, by, bx + int(10 / C) * PX, by + 3], fill="#F5F2F7"); d.text((bx, by + 6), "10 m", fill="#F5F2F7", font=f)
    d.text((60, 10), f"Nootka section, year {year}. Style test: design as drawn, no events. Not a result.", fill="#A6CFC3", font=f)
    d.text((60, 24), "S", fill="#F5F2F7", font=f); d.text((Wp - 40, 24), "N", fill="#F5F2F7", font=f)
    d.text((bx + 140, by + 6), "bright = within 3 m of the cut, dim = 3-6 m behind", fill="#8FB3B4", font=f)
    im.save(out); print(out, im.size, "trees on cut:", len(near), "x =", round(float(x0 - xs[0]), 1), "m from west edge")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 25, sys.argv[2] if len(sys.argv) > 2 else "section_test.png")
