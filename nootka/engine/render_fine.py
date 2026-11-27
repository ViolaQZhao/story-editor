"""Plan, section and block model with plants drawn in 0.2 m blocks. Style test for the front end.
Usage: python3 render_fine.py [year] [out_prefix]"""
import sys, math, numpy as np
from PIL import Image, ImageDraw
from engine.site import PATH, IMPERV, GREEN, SHRUB, PARCEL, OUT
from render_section import COLS, FORM, TRUNK_SHARE, SHRUB_TYPES
from render_views import GROUND, rgb, mixc, font, state

B = 0.5                                   # metres per block, same in all three views (Viola, 24 Nov)
KK = 3 if B < 0.3 else 7                  # screen pixels per block in plan and section
TRUNK = [rgb("#B08A66"), rgb("#6E5240")]
KINDS = list(SHRUB_TYPES)
def pal(sp, health=2):
    c = [rgb(x) for x in COLS[sp]]
    if health == 1: c = [mixc(x, "#C9B98A", 0.55) for x in c]          # stressed: faded toward straw
    return [None] + c + TRUNK + [rgb("#F2D06B")]
def trunk_h(kind, h): return h * TRUNK_SHARE[kind] * min(1, h / 10 + 0.3)


# ---------- side view of one tree: array of roles (0 empty, 1-3 crown light/mid/dark, 4-5 trunk) ----------
def side(kind, h, w, rng):
    Hn = max(3, round(h / B)); Wn = max(3, round(w / B)) | 1; Ht = min(Hn - 2, max(1, round(trunk_h(kind, h) / B))); Hc = Hn - Ht
    A = np.zeros((Hn, Wn + 4), int); cx = (Wn + 4) / 2; yy, xx = np.mgrid[0:Hn, 0:Wn + 4]; xx = xx + 0.5; yy = yy + 0.5
    tw = max(1, round(h * 0.035 / B)); noise = rng.random(A.shape)
    if kind == "conifer":
        t = np.clip(yy / Hc, 0, 1); tiers = max(3.0, Hc * B / 1.3); saw = (t * tiers) % 1
        hw = np.maximum(0.6, Wn / 2 * (0.05 + 0.95 * t) * (0.70 + 0.30 * saw)); q = (xx - cx) / hw
        m = (np.abs(q) <= 1) & (yy <= Hc)
        role = np.where(q < -0.3, 1, np.where(q > 0.3, 3, 2)); role = np.where(saw > 0.82, np.minimum(role + 1, 3), role)
        role = np.clip(role + (noise > 0.9).astype(int) - (noise < 0.08).astype(int), 1, 3); A[m] = role[m]
        tm = (np.abs(xx - cx) <= tw / 2 + 0.01) & (yy > Hc - 1) & (A == 0)
    else:
        flat = 0.75 if kind == "small" else 1.0; cy = Hc * (0.5 if kind != "small" else 0.55); rx, ry = Wn / 2 * 0.80, Hc / 2 * 0.86 * flat
        m = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 <= 1
        for _ in range(int(rng.integers(8, 13))):
            a = rng.uniform(0, 2 * math.pi); lr = rng.uniform(0.20, 0.34) * Wn / 2
            lx, ly = cx + math.cos(a) * rx * 0.86, cy + math.sin(a) * ry * 0.86
            m |= (xx - lx) ** 2 + ((yy - ly) * 1.15) ** 2 <= lr * lr
        m &= (yy <= Hc + 1) & (np.abs(xx - cx) <= Wn / 2 + 1.5)
        v = -(xx - cx) / rx * 0.55 - (yy - cy) / ry * 0.75 + (noise - 0.5) * 0.9
        role = np.where(v > 0.35, 1, np.where(v < -0.35, 3, 2)); A[m] = role[m]; A[m & (noise > 0.985)] = 0
        if kind == "small":
            tm = np.zeros_like(m)
            for off in (-0.28, 0.0, 0.28):
                tm |= (np.abs(xx - (cx + off * Wn * (Hn - yy) / Hn)) <= 0.6) & (yy > cy) & (A == 0)
        else:
            tm = (np.abs(xx - cx) <= tw / 2 + 0.01) & (yy > cy) & (A == 0)
            fork = (np.abs(np.abs(xx - cx) - (cy + ry * 0.7 - yy) * 0.5) <= 0.6) & (yy > cy) & (yy < cy + ry * 0.7)
            A[fork & m & (noise > 0.35)] = 5
    A[tm] = np.where(xx[tm] < cx, 4, 5)
    return A


def paste(img, A, colours, x_mid, y_base, dim=None, ids=None, oid=0):
    h, w = A.shape; x0 = int(round(x_mid - w / 2)); y0 = y_base - h
    for r in (1, 2, 3, 4, 5, 6):
        ys_, xs_ = np.where(A == r)
        if not len(ys_): continue
        Y, X = ys_ + y0, xs_ + x0; ok = (Y >= 0) & (Y < img.shape[0]) & (X >= 0) & (X < img.shape[1])
        c = np.array(colours[r], float)
        if dim is not None: c = c * 0.55 + np.array(dim) * 0.45
        img[Y[ok], X[ok]] = c
        if ids is not None: ids[Y[ok], X[ok]] = oid


def clump_side(kind, grow, rng):
    hm, wb, cols, acc = SHRUB_TYPES[kind]; h = max(2, round(hm * grow / B)); w = max(3, round(wb * 0.5 / B * rng.uniform(0.7, 1.1)))
    yy, xx = np.mgrid[0:h, 0:w]; q = (xx + .5 - w / 2) / (w / 2); t = 1 - (yy + .5) / h
    edge = np.sqrt(np.clip(1 - t ** 2, 0, 1)) if kind != "tall" else 0.55 + 0.45 * np.sin(math.pi * np.clip(t, 0, 1))
    n = rng.random((h, w)); m = (np.abs(q) <= edge * (0.85 + 0.3 * n))
    role = np.where(q + (n - .5) * 0.8 < -0.25, 1, np.where(q + (n - .5) * 0.8 > 0.35, 3, 2)); A = np.where(m, role, 0)
    A[m & (n > 0.94) & (t > 0.35)] = 6
    return A, [None] + [rgb(c) for c in cols] + TRUNK + [rgb(acc)]


def upscale(img, k): return Image.fromarray(np.repeat(np.repeat(img.astype(np.uint8), k, 0), k, 1))


def cut_line(S, rec, half=6.0):
    xs, cls = S["xs"], S["cls"]; tx = np.array([t["X"] for t in S["trees"]]); alive = np.array(rec["alive"])
    return max(range(len(xs)), key=lambda j: (alive & (abs(tx - xs[j]) <= half)).sum() + 0.1 * (cls[:, j] == SHRUB).sum())


# ---------- section ----------
def section(S, species, rec, year, out, K=KK, title=""):
    xs, ys, E, cls = S["xs"], S["ys"], S["E"], S["cls"]; best = S.get("cut", None) or cut_line(S, rec); x0 = xs[best]
    col = cls[:, best]; ins = np.where(col != OUT)[0]; sl = slice(ins.min(), ins.max() + 1)
    yy, zz, cc, pp = ys[sl], E[sl, best], col[sl], S["patch_id"][sl, best]
    if yy[0] > yy[-1]: yy, zz, cc, pp = yy[::-1], zz[::-1], cc[::-1], pp[::-1]
    tx = np.array([t["X"] for t in S["trees"]]); ty = np.array([t["Y"] for t in S["trees"]])
    near = [k for k in range(len(tx)) if rec["alive"][k] and abs(tx[k] - x0) <= 6 and yy[0] <= ty[k] <= yy[-1]]
    zmin = math.floor(zz.min()) - 2; zmax = zz.max() + S.get("hmax_view", max([rec["h"][k] for k in near] + [5])) + 3
    W = int((yy[-1] - yy[0] + 1) / B); H = int((zmax - zmin) / B); mg = max(4, round(2.8 / B))
    img = np.zeros((H + 30, W + 2 * mg, 3), float); kk = np.linspace(0, 1, img.shape[0])[:, None]; ids = np.zeros(img.shape[:2], np.uint8)
    img[:] = np.stack([7 + 10 * kk, 40 + 50 * kk, 52 + 55 * kk], -1)
    gy = lambda m: H - int(round((np.interp(m, yy, zz) - zmin) / B)); gx = lambda m: mg + int(round((m - yy[0]) / B))
    rng = np.random.default_rng(11); TOP = {GREEN: "#A6CFC3", SHRUB: "#4A9E9B", PATH: "#F5F2F7", IMPERV: "#8FA3A8", PARCEL: "#D9D2DD"}
    for b in range(W):
        m = yy[0] + b * B; i = min(len(cc) - 1, int(round(m - yy[0]))); y = gy(m); x = mg + b
        soil = rng.random(img.shape[0] - y); img[y:, x] = np.where(soil[:, None] > 0.5, (66, 53, 46), (58, 47, 42))
        img[y:y + max(1, round(0.4 / B)), x] = rgb(TOP.get(int(cc[i]), "#6E6A66"))
        if cc[i] == GREEN and rng.random() < 0.35: img[y - 1, x] = rgb("#7FB8A6")           # groundcover tufts
    for k in sorted(near, key=lambda k: -abs(tx[k] - x0)):
        if abs(tx[k] - x0) <= 3: continue
        sp = species[k]; paste(img, side(FORM[sp], rec["h"][k], 2 * rec["r"][k], np.random.default_rng(100 + k)), pal(sp, rec["health"][k]), gx(ty[k]), gy(ty[k]), dim=(14, 68, 80), ids=ids, oid=k + 1)
    m = yy[0]
    while m < yy[-1]:                                                                         # shrub clumps along the cut
        i = min(len(cc) - 1, int(round(m - yy[0])))
        if cc[i] == SHRUB and rng.random() < 0.85 * rec["cover"][pp[i]]:
            A, c = clump_side(KINDS[int(rng.integers(len(KINDS)))], min(1.0, year / 6), rng); paste(img, A, c, gx(m), gy(m), ids=ids, oid=101 + int(pp[i]))
        m += rng.uniform(0.5, 1.1)
    labels = []
    for k in sorted(near, key=lambda k: -abs(tx[k] - x0)):
        sp = species[k]
        if abs(tx[k] - x0) <= 3:
            paste(img, side(FORM[sp], rec["h"][k], 2 * rec["r"][k], np.random.default_rng(100 + k)), pal(sp, rec["health"][k]), gx(ty[k]), gy(ty[k]), ids=ids, oid=k + 1)
        labels.append((gx(ty[k]), gy(ty[k]) - round(rec["h"][k] / B), S["trees"][k]["id"]))
    Image.fromarray(ids).save(out.replace(".png", "_id.png"))
    px0 = gx(yy[0] + 3); img[gy(yy[0] + 3) - round(1.7 / B):gy(yy[0] + 3), px0:px0 + max(1, round(0.4 / B))] = (245, 242, 247)
    im = upscale(img, K); d = ImageDraw.Draw(im); f = font(11); used = []
    for x, y, t in sorted(labels, key=lambda l: l[1]):
        X, Y = x * K - 10, y * K - 14
        while any(abs(X - a) < 26 and abs(Y - b) < 12 for a, b in used): Y -= 12
        used.append((X, Y)); d.text((X, Y), t, fill="#F5F2F7", font=f)
    by = im.height - 22; d.rectangle([mg * K, by, mg * K + int(10 / B) * K, by + 3], fill="#F5F2F7"); d.text((mg * K, by + 6), "10 m", fill="#F5F2F7", font=f)
    d.text((mg * K, 8), f"Section, year {year}. {title}", fill="#A6CFC3", font=f)
    d.text((mg * K, 24), "S", fill="#F5F2F7", font=f); d.text((im.width - mg * K - 8, 24), "N", fill="#F5F2F7", font=f)
    d.text((mg * K + 180, by + 6), "bright = within 3 m of the cut, dim = 3-6 m behind", fill="#8FB3B4", font=f)
    im.save(out)


# ---------- plan ----------
def plan(S, species, rec, year, out, K=KK, title=""):
    cls = S["cls"]; ny, nx = cls.shape; f5 = int(round(1 / B)); xs, ys = S["xs"], S["ys"]; north_up = ys[0] < ys[-1]
    C = np.repeat(np.repeat(cls, f5, 0), f5, 1); P = np.repeat(np.repeat(S["patch_id"], f5, 0), f5, 1)
    if north_up: C, P = C[::-1], P[::-1]
    H, W = C.shape; img = np.zeros((H, W, 3), float); rng = np.random.default_rng(7)
    ids = np.where((C == SHRUB) & (P >= 0), P + 101, 0).astype(np.uint8)
    for c, colr in GROUND.items(): img[C == c] = rgb(colr)
    img[C == OUT] = rgb("#00131E"); n = rng.random((H, W))
    g = C == GREEN; img[g & (n < 0.10)] = mixc("#A6CFC3", "#4A9E9B", 0.3); img[g & (n > 0.96)] = mixc("#A6CFC3", "#F5F2F7", 0.5)
    hatch = (C == PARCEL) & (((np.add.outer(np.arange(H), np.arange(W))) % max(4, round(1.6 / B))) == 0); img[hatch] = rgb("#DDD6E2")
    yy, xx = np.mgrid[0:H, 0:W]
    if rec.get("inv"):                                                                         # invasive plants on green cells
        inv = np.unpackbits(np.array(rec["inv"], np.uint8))[:ny * nx].reshape(ny, nx).astype(bool)
        I = np.repeat(np.repeat(inv, f5, 0), f5, 1); I = I[::-1] if north_up else I
        img[I & (n < 0.75)] = rgb("#5B4B7A"); img[I & (n >= 0.75)] = rgb("#3D3257")
    sy, sx = np.where((C == SHRUB) & (rng.random((H, W)) < 0.55 * B * B))                             # shrub clumps
    for y, x in zip(sy, sx):
        if rng.random() > rec["cover"][P[y, x]]: continue
        kind = KINDS[int(rng.integers(len(KINDS)))]; cols = [rgb(c) for c in SHRUB_TYPES[kind][2]]; r = rng.uniform(0.44, 1.0) / B
        y0, y1, x0, x1 = max(0, int(y - r - 1)), min(H, int(y + r + 2)), max(0, int(x - r - 1)), min(W, int(x + r + 2))
        dy, dx = yy[y0:y1, x0:x1] - y, xx[y0:y1, x0:x1] - x; nn = rng.random(dy.shape)
        m = (dx * dx + dy * dy <= (r * (0.8 + 0.35 * nn)) ** 2) & (C[y0:y1, x0:x1] == SHRUB); q = (dx + dy) / r + (nn - .5)
        sub = img[y0:y1, x0:x1]; sub[m & (q < -0.4)] = cols[0]; sub[m & (q >= -0.4) & (q <= 0.5)] = cols[1]; sub[m & (q > 0.5)] = cols[2]
        sub[m & (nn > 0.965)] = rgb(SHRUB_TYPES[kind][3])
    X = lambda x: (x - xs[0] + 0.5) / B; Y = lambda y: ((ys[-1] - y + 0.5) if north_up else (y - ys[0] + 0.5)) / B
    order = sorted([k for k in range(len(S["trees"])) if rec["alive"][k]], key=lambda k: rec["h"][k]); shape = {}
    for k in order:
        r = max(rec["r"][k] / B, 0.8); cx, cy = X(S["trees"][k]["X"]), Y(S["trees"][k]["Y"]); rg = np.random.default_rng(300 + k)
        ph = rg.uniform(0, 6.28, 3); y0, y1, x0, x1 = max(0, int(cy - r - 12)), min(H, int(cy + r + 13)), max(0, int(cx - r - 12)), min(W, int(cx + r + 13))
        shape[k] = (r, cx, cy, ph, (y0, y1, x0, x1))
    def mask(k, ox=0.0):
        r, cx, cy, ph, (y0, y1, x0, x1) = shape[k]; dy, dx = yy[y0:y1, x0:x1] + .5 - cy - ox, xx[y0:y1, x0:x1] + .5 - cx - ox
        th = np.arctan2(dy, dx); lob = 5 if FORM[species[k]] != "conifer" else 9
        rr = r * (1 + 0.07 * np.sin(lob * th + ph[0]) + 0.05 * np.sin((lob + 3) * th + ph[1]))
        return np.hypot(dx, dy), rr, th, dx, dy
    for k in order:                                                                             # shadows
        d_, rr, *_ = mask(k, ox=min(1.6, rec["h"][k] * 0.08) / B); y0, y1, x0, x1 = shape[k][4]; sub = img[y0:y1, x0:x1]; m = d_ <= rr
        sub[m] = sub[m] * 0.72 + np.array(rgb("#00131E")) * 0.28
    for k in order:                                                                             # crowns, short trees first
        sp = species[k]; cols = pal(sp, rec["health"][k])[1:4]; d_, rr, th, dx, dy = mask(k); y0, y1, x0, x1 = shape[k][4]; sub = img[y0:y1, x0:x1]
        nn = np.random.default_rng(500 + k).random(d_.shape); m = d_ <= rr; r = shape[k][0]
        if FORM[sp] == "conifer":
            spoke = np.sin(9 * th + shape[k][3][2]) + (nn - .5) * 1.2; role = np.where(spoke > 0.5, 0, np.where(spoke < -0.5, 2, 1)); role[d_ < max(1.2, r * 0.12)] = 0
        else:
            q = (dx + dy) / max(r, 1) + (nn - .5) * 1.1; role = np.where(q < -0.45, 0, np.where(q > 0.5, 2, 1))
        for i in range(3): sub[m & (role == i)] = cols[i]
        ids[y0:y1, x0:x1][m] = k + 1
        sub[m & (d_ > rr - 1.0) & (r > 2)] = mixc(COLS[sp][2], "#00131E", 0.45)                            # rim so overlapping crowns stay readable
    mg = max(5, round(3.2 / B)); canvas = np.zeros((H + 2 * mg + 14, W + 2 * mg, 3), float); canvas[:] = rgb("#00131E"); canvas[mg:mg + H, mg:mg + W] = img
    idc = np.zeros(canvas.shape[:2], np.uint8); idc[mg:mg + H, mg:mg + W] = ids; Image.fromarray(idc).save(out.replace(".png", "_id.png"))
    im = upscale(canvas, K); d = ImageDraw.Draw(im); f = font(11); o = mg * K
    for k in order:
        sp = species[k]; d.text((o + shape[k][1] * K - 10, o + shape[k][2] * K - 6), S["trees"][k]["id"], fill="#00131E" if FORM[sp] != "conifer" else "#F5F2F7", font=f)
    pid = S["parcel_id"][::-1] if north_up else S["parcel_id"]
    for q in S["parcels"]:
        jj, ii = np.where(pid == q["id"])
        if len(ii) >= 50: d.text((o + ii.mean() * f5 * K - 34, o + jj.mean() * f5 * K), f"{q['storeys']} storeys", fill="#074851", font=f)
    cx = o + (xs[S.get("cut", None) or cut_line(S, rec)] - xs[0] + 0.5) / B * K; yb = o + H * K
    for y in range(o - 12, yb + 12, 12): d.line([(cx, y), (cx, y + 6)], fill="#F2B766", width=2)
    d.text((cx - 24, o - 30), "section", fill="#F2B766", font=f)
    d.text((o, 10), f"Plan, year {year}. {title}", fill="#A6CFC3", font=f)
    d.text((im.width - o - 8, o - 30), "N", fill="#F5F2F7", font=f)
    d.rectangle([o, yb + 16, o + 10 / B * K, yb + 19], fill="#F5F2F7"); d.text((o, yb + 23), "10 m", fill="#F5F2F7", font=f); lx = o + 190
    for name, lab in [(n_, n_.replace("Western red ", "").replace("Sitka ", "").lower()) for n_ in dict.fromkeys(species)]:
        d.rectangle([lx, yb + 18, lx + 10, yb + 28], fill=COLS[name][1]); d.text((lx + 15, yb + 17), lab, fill="#B9CFD0", font=f); lx += 28 + 7 * len(lab)
    im.save(out)


# ---------- block model: terrain and buildings in 1 m blocks, plants in 0.2 m blocks ----------
def crown_voxels(kind, h, w, rng):
    """Occupancy of one tree at 0.2 m, returned as visible voxels (da, db, dz, role) seen from +a, +b and above."""
    Hn = max(3, round(h / B)); R = max(1.5, w / 2 / B); Ht = min(Hn - 2, max(1, round(trunk_h(kind, h) / B))); Hc = Hn - Ht; m = int(R + 4)
    zz, bb, aa = np.mgrid[0:Hn, -m:m + 1, -m:m + 1]; d = np.hypot(aa, bb); t = np.clip((Hn - zz - .5) / Hc, 0, 1)        # t: 0 top, 1 crown base
    if kind == "conifer":
        tiers = max(3.0, Hc * B / 1.3); saw = (t * tiers) % 1; occ = (d <= np.maximum(0.6, R * (0.05 + 0.95 * t) * (0.70 + 0.30 * saw))) & (zz >= Ht)
    else:
        flat = 0.75 if kind == "small" else 1.0; cz = Ht + Hc * 0.5; rz = Hc / 2 * 0.86 * flat; rx = R * 0.80
        occ = (d / rx) ** 2 + ((zz - cz) / rz) ** 2 <= 1
        for _ in range(int(rng.integers(10, 16))):
            a = rng.uniform(0, 2 * math.pi); e = rng.uniform(-0.6, 0.9); lr = rng.uniform(0.22, 0.36) * R; ce = math.cos(e)
            occ |= (aa - math.cos(a) * rx * 0.85 * ce) ** 2 + (bb - math.sin(a) * rx * 0.85 * ce) ** 2 + (zz - cz - math.sin(e) * rz * 0.85) ** 2 <= lr * lr
        occ &= zz >= Ht - 1
    tw = max(1, round(h * 0.035 / B)); trunk = (np.abs(aa) <= tw / 2) & (np.abs(bb) <= tw / 2) & (zz < (Ht + (Hc * 0.5 if kind != "conifer" else 1))) & ~occ
    full = occ | trunk; hid = np.zeros_like(full)
    hid[:-1, :-1, :-1] = full[1:, :-1, :-1] & full[:-1, 1:, :-1] & full[:-1, :-1, 1:]                                      # covered above, toward +b and toward +a
    vis = full & ~hid; z, b, a = np.where(vis); n = rng.random(len(z))
    up = np.ones(len(z), bool); ok = z + 1 < Hn; up[ok] = ~full[z[ok] + 1, b[ok], a[ok]]
    role = np.where(trunk[z, b, a], 4, np.where(n > 0.86, 3, np.where(up & (n < 0.5), 1, 2)))
    return a - m, b - m, z, role


def model(S, species, rec, year, out, title=""):
    cls, E = S["cls"], S["E"]; ny, nx = cls.shape; M = 12                                      # pixels per metre across; a 0.2 m block is 4 x 4 px
    flip = S["ys"][0] > S["ys"][-1]; zmin = math.floor(np.nanmin(E[cls != OUT])) - 1; gz = {}; items = []
    rng = np.random.default_rng(3); pid = S["patch_id"]; par = S["parcel_id"]; pb = {}
    for j in range(ny):
        for i in range(nx):
            c = int(cls[j, i])
            if c == OUT: continue
            b = (ny - 1 - j) if flip else j; z = round((E[j, i] - zmin) / B) * B; gz[(i, b)] = z
            items.append((i + b, 0.0, "ground", (i, b, z, "#C9C4CF" if c == PARCEL else GROUND.get(c, "#8FA3A8"), 101 + int(pid[j, i]) if c == SHRUB and pid[j, i] >= 0 else 0)))
            if par[j, i] >= 0: pb[(i, b)] = int(par[j, i])
            if c == SHRUB and rng.random() < 0.5 * rec["cover"][pid[j, i]]:
                kind = KINDS[int(rng.integers(len(KINDS)))]; hm = SHRUB_TYPES[kind][0] * min(1, year / 6) * rng.uniform(0.6, 1.0)
                Hn = max(1, round(hm / B)); r = rng.uniform(0.4, 0.72) / B; mm = int(r) + 2; zz, bb, aa = np.mgrid[0:Hn, -mm:mm + 1, -mm:mm + 1]
                occ = (np.hypot(aa, bb) / r) ** 2 + (zz / Hn) ** 2 <= 1 + (rng.random(zz.shape) - .5) * 0.5; hid = np.zeros_like(occ)
                hid[:-1, :-1, :-1] = occ[1:, :-1, :-1] & occ[:-1, 1:, :-1] & occ[:-1, :-1, 1:]
                zv, bv, av = np.where(occ & ~hid); av = av - mm; bv = bv - mm; cols = [rgb(x) for x in SHRUB_TYPES[kind][2]]; acc = rgb(SHRUB_TYPES[kind][3]); nn = rng.random(len(zv))
                ca, cb = i + rng.uniform(0.3, 0.7), b + rng.uniform(0.3, 0.7)
                for a_, b_, z_, n_ in zip(av, bv, zv, nn):
                    A_, B_ = ca + a_ * B, cb + b_ * B
                    items.append((A_ + B_, z + z_ * B, "vox", (A_, B_, z + z_ * B, acc if n_ > 0.95 else cols[0 if n_ < 0.3 else 1], cols[1], cols[2], 101 + int(pid[j, i]))))
    for q in S["parcels"]:
        cells = [k for k, v in pb.items() if v == q["id"]]; roof = float(np.mean([gz[k] for k in cells])) + 3.0 * q["storeys"]
        for (a_, b_) in cells:
            items.append((a_ + b_, gz[(a_, b_)] + 0.01, "bldg", (a_, b_, gz[(a_, b_)], max(1.0, roof - gz[(a_, b_)]), pb.get((a_, b_ + 1)) != q["id"], pb.get((a_ + 1, b_)) != q["id"])))
    xs, ys = S["xs"], S["ys"]; nvox = 0
    for k, t in enumerate(S["trees"]):
        if not rec["alive"][k]: continue
        sp = species[k]; a0 = t["X"] - xs[0] + 0.5; jf = abs(t["Y"] - ys[0]) + 0.5; b0 = (ny - jf) if flip else jf
        z0 = gz.get((int(a0), int(b0)), 0.0); c = pal(sp, rec["health"][k]); av, bv, zv, role = crown_voxels(FORM[sp], rec["h"][k], 2 * rec["r"][k], np.random.default_rng(700 + k)); nvox += len(av)
        for a_, b_, z_, r_ in zip(av, bv, zv, role):
            A_, B_, Z_ = a0 + a_ * B, b0 + b_ * B, z0 + z_ * B
            col = (c[4], c[4], c[5]) if r_ == 4 else (c[1] if r_ == 1 else (c[3] if r_ == 3 else c[2]), c[2], c[3])
            items.append((A_ + B_, Z_, "vox", (A_, B_, Z_, *col, k + 1)))
    items.sort(key=lambda it: (it[0], it[1]))
    zr = S.get("zr_view") or max(it[3][2] + (it[3][3] if it[2] == "bldg" else 0) for it in items) + 1
    Wp = (nx + ny) * M + 80; Hp = int((nx + ny) * M / 2 + zr * M + 90)
    im = Image.new("RGB", (Wp, Hp), "#00131E"); d = ImageDraw.Draw(im, "RGBA"); f = font(12)
    imid = Image.new("L", (Wp // 2, Hp // 2), 0); di = ImageDraw.Draw(imid)                 # pick map at half size
    for r in range(Hp):
        kk = r / Hp; d.line([(0, r), (Wp, r)], fill=(int(4 + 8 * kk), int(28 + 46 * kk), int(40 + 50 * kk)))
    ox = 40 + ny * M; oy = int(zr * M) + 50; h2 = M // 2; vh = max(1, int(B * M) // 2)
    def faces(a, b, ztop, hh, cT, cL, cR, left=True, right=True):
        sx = ox + (a - b) * M; top = oy + (a + b) * h2 - int(ztop * M)
        d.polygon([(sx, top), (sx + M, top + h2), (sx, top + M), (sx - M, top + h2)], fill=cT)
        if left: d.polygon([(sx - M, top + h2), (sx, top + M), (sx, top + M + hh), (sx - M, top + h2 + hh)], fill=cL)
        if right: d.polygon([(sx + M, top + h2), (sx, top + M), (sx, top + M + hh), (sx + M, top + h2 + hh)], fill=cR)
    for key, z, kind, v in items:
        if kind == "vox":
            a, b, zz_, cT, cL, cR, oid = v; sx = int(ox + (a - b) * M); top = int(oy + (a + b) * h2 - (zz_ + B) * M)
            di.rectangle([(sx - vh) // 2, top // 2, (sx + vh - 1) // 2, (top + 2 * vh - 1) // 2], fill=oid)
            d.rectangle([sx - vh, top, sx + vh - 1, top + vh - 1], fill=cT); d.rectangle([sx - vh, top + vh, sx - 1, top + 2 * vh - 1], fill=cL); d.rectangle([sx, top + vh, sx + vh - 1, top + 2 * vh - 1], fill=cR)
        elif kind == "ground":
            a, b, zz_, col, oid = v; faces(a, b, zz_, int(zz_ * M) + 8, rgb(col), (66, 53, 46), (48, 39, 34))
            sx = ox + (a - b) * M; top = oy + (a + b) * h2 - int(zz_ * M); hh = int(zz_ * M) + 8
            di.polygon([(sx // 2, top // 2), ((sx + M) // 2, (top + h2) // 2), ((sx + M) // 2, (top + h2 + hh) // 2), (sx // 2, (top + M + hh) // 2), ((sx - M) // 2, (top + h2 + hh) // 2), ((sx - M) // 2, (top + h2) // 2)], fill=oid)
        else:
            a, b, zg, hgt, L, Rr = v; faces(a, b, zg + hgt, int(hgt * M), (245, 242, 247, 105), (200, 205, 215, 95), (150, 160, 175, 95), L, Rr)
    d.text((20, 14), f"Block model, year {year}, seen from the north-east. {title}", fill="#A6CFC3", font=f)
    imid.save(out.replace(".png", "_id.png")); im.save(out); return max(it[3][2] + (it[3][3] if it[2] == "bldg" else 0) for it in items) + 1


if __name__ == "__main__":
    year = int(sys.argv[1]) if len(sys.argv) > 1 else 25; pre = sys.argv[2] if len(sys.argv) > 2 else "nootka"
    S, R, rec = state(year); sp = R["species"]
    section(S, sp, rec, year, f"{pre}_section_y{year}.png"); plan(S, sp, rec, year, f"{pre}_plan_y{year}.png"); model(S, sp, rec, year, f"{pre}_model_y{year}.png")
