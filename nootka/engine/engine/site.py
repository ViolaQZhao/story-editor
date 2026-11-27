"""Build the site grid from the Rhino export (zones, parcels, contours, plots)."""
import json
import numpy as np
try:                                     # only needed to build the grid from the Rhino export; a saved site loads without them
    import shapely
    from shapely.geometry import Polygon
    from scipy.interpolate import griddata
    from scipy.ndimage import distance_transform_edt
except ImportError:
    shapely = None

OUT, OTHER, PATH, IMPERV, GREEN, SHRUB, PARCEL = 0, 1, 2, 3, 4, 5, 6


OVERRIDES = [[0, 24, 13.5, 31.5, 3],      # A: paved road between the two lots on the west side
             [45, 41.5, 52.5, 65.8, 6]]   # B: part of a private parcel (City parcel line is open here)


def build_site(geom_path, contours_path, plots_path, cs=1.0, overrides=OVERRIDES):
    G = json.load(open(geom_path))
    polys = {}
    for layer, closed, pts in G["curves"]:
        if closed:
            polys.setdefault(layer, []).append(Polygon([tuple(q) for q in pts]).buffer(0))
    sb = polys["Site Boundary"][0]
    x0, y0, x1, y1 = sb.bounds
    xs = np.arange(x0 + cs / 2, x1, cs)
    ys = np.arange(y0 + cs / 2, y1, cs)
    X, Y = np.meshgrid(xs, ys)
    inside = shapely.contains_xy(sb, X, Y)
    cls = np.where(inside, OTHER, OUT)
    # drawn zones from large to small, so nested islands win; private parcels are painted last:
    # nothing inside a parcel counts as green space (Viola, 24 Nov)
    zones = ([(g, PATH) for g in polys.get("PATH", [])] + [(g, IMPERV) for g in polys.get("impervious", [])]
             + [(g, GREEN) for g in polys.get("Green Space", [])] + [(g, SHRUB) for g in polys.get("shrub patches", [])])
    zones.sort(key=lambda z: -z[0].area)
    for g, c in zones:
        cls[shapely.contains_xy(g, X, Y) & inside] = c
    parcel_id = np.full(cls.shape, -1)
    for n, g in enumerate(polys.get("PARCELS", [])):
        m = shapely.contains_xy(g, X, Y) & inside
        cls[m] = PARCEL; parcel_id[m] = n
    # areas with no zone drawn: boxes in metres from the SW corner, [x0, y0, x1, y1, class]
    for bx0, by0, bx1, by1, c in (overrides or []):
        box = (X - x0 >= bx0) & (X - x0 <= bx1) & (Y - y0 >= by0) & (Y - y0 <= by1)
        cls[box & (cls == OTHER)] = c

    P = json.load(open(plots_path))["plots"]
    trees = [p for p in P if p["kind"] == "Tree"]
    patches = [p for p in P if p["kind"] != "Tree"]
    patch_id = np.full(cls.shape, -1)
    for g in polys.get("shrub patches", []):
        k = int(np.argmin([(g.centroid.x - p["X"]) ** 2 + (g.centroid.y - p["Y"]) ** 2 for p in patches]))
        patch_id[shapely.contains_xy(g, X, Y) & (cls == SHRUB)] = k

    C = json.load(open(contours_path))["contours"]
    pts = np.array([[p[0], p[1]] for c in C for p in c])
    zz = np.array([p[2] for c in C for p in c])
    E = griddata(pts, zz, (X, Y), method="linear")
    En = griddata(pts, zz, (X, Y), method="nearest")
    E = np.where(np.isnan(E), En, E)
    dzdy, dzdx = np.gradient(E, cs, cs)
    slope = np.degrees(np.arctan(np.hypot(dzdx, dzdy)))
    aspect = (np.degrees(np.arctan2(-dzdx, -dzdy)) + 360) % 360

    green = (cls == GREEN) | (cls == SHRUB)
    dist_path = distance_transform_edt(cls != PATH) * cs
    dist_out = distance_transform_edt((cls != OUT) & (cls != PARCEL)) * cs
    dist_parcel = distance_transform_edt(cls != PARCEL) * cs if (cls == PARCEL).any() else np.full(cls.shape, 1e9)
    entry = green & (dist_parcel <= 1.5 * cs)          # where invasives arrive
    if not entry.any():
        entry = green & (dist_out <= 1.5 * cs)
    tx = np.array([t["X"] for t in trees]); ty = np.array([t["Y"] for t in trees])
    d2 = (X.ravel()[None, :] - tx[:, None]) ** 2 + (Y.ravel()[None, :] - ty[:, None]) ** 2
    ti = np.clip(((ty - ys[0]) / cs).round().astype(int), 0, len(ys) - 1)
    tj = np.clip(((tx - xs[0]) / cs).round().astype(int), 0, len(xs) - 1)
    # parcel cells added by an override box join the nearest drawn parcel
    lost = (cls == PARCEL) & (parcel_id < 0)
    if lost.any() and (parcel_id >= 0).any():
        idx = distance_transform_edt(parcel_id < 0, return_distances=False, return_indices=True)
        parcel_id[lost] = parcel_id[idx[0][lost], idx[1][lost]]
    parcel_id[cls != PARCEL] = -1
    # buildings (Viola, 24 Nov): the smallest parcel in the test area is a four-storey development, the others
    # two storeys. Size is the part inside the site boundary; slivers under 50 m2 are not counted as the smallest.
    areas = [g.area for g in polys.get("PARCELS", [])]
    parcels = [dict(id=n, area=round(a, 1), inside=float((parcel_id == n).sum() * cs * cs), storeys=2) for n, a in enumerate(areas)]
    parcels = [q for q in parcels if q["inside"] > 0]
    big = [q for q in parcels if q["inside"] >= 50]
    if big: min(big, key=lambda q: q["inside"])["storeys"] = 4
    return dict(cs=cs, xs=xs, ys=ys, cls=cls, green=green, patch_id=patch_id, parcel_id=parcel_id, parcels=parcels, E=E, slope=slope, aspect=aspect,
                dist_path=dist_path, dist_out=dist_out, entry=entry, trees=trees, patches=patches,
                d2=d2, tree_cell=(ti, tj), tree_edge=dist_out[ti, tj] < 6, tree_slope=slope[ti, tj],
                patch_cells=[(patch_id == k) for k in range(len(patches))],
                patch_area=np.array([(patch_id == k).sum() * cs * cs for k in range(len(patches))]))


GRIDS = ["cls", "green", "patch_id", "parcel_id", "E", "slope", "aspect", "dist_path", "dist_out", "entry"]


def save_site(site, path):
    """Write a built site as plain JSON, so the engine can run where shapely and scipy are not installed (the browser)."""
    out = {k: np.asarray(site[k]).tolist() for k in GRIDS}
    out.update(cs=site["cs"], xs=site["xs"].tolist(), ys=site["ys"].tolist(), trees=site["trees"], patches=site["patches"], parcels=site["parcels"],
               tree_cell=[np.asarray(a).tolist() for a in site["tree_cell"]], tree_edge=np.asarray(site["tree_edge"]).tolist(),
               tree_slope=np.round(site["tree_slope"], 3).tolist(), patch_area=site["patch_area"].tolist())
    for k in ("E", "slope", "aspect", "dist_path", "dist_out"): out[k] = np.round(np.asarray(site[k], float), 3).tolist()
    json.dump(out, open(path, "w"))


def load_site(src):
    d = json.load(open(src)) if isinstance(src, str) else src
    S = {k: np.array(d[k]) for k in GRIDS}; S["green"] = S["green"].astype(bool); S["entry"] = S["entry"].astype(bool)
    S.update(cs=d["cs"], xs=np.array(d["xs"]), ys=np.array(d["ys"]), trees=d["trees"], patches=d["patches"], parcels=d["parcels"],
             tree_cell=(np.array(d["tree_cell"][0]), np.array(d["tree_cell"][1])), tree_edge=np.array(d["tree_edge"]), tree_slope=np.array(d["tree_slope"]),
             patch_area=np.array(d["patch_area"]))
    X, Y = np.meshgrid(S["xs"], S["ys"]); tx = np.array([t["X"] for t in S["trees"]]); ty = np.array([t["Y"] for t in S["trees"]])
    S["d2"] = (X.ravel()[None, :] - tx[:, None]) ** 2 + (Y.ravel()[None, :] - ty[:, None]) ** 2
    S["patch_cells"] = [(S["patch_id"] == k) for k in range(len(S["patches"]))]
    return S
