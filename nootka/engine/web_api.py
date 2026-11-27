"""Entry points the browser calls. The same engine files run here as on the desktop."""
import json, os, numpy as np
from engine.site import load_site
from engine import explore as ex, story

S = None; R = None
MODE = "open"          # run 0 leaves every tree plot open within its type (conifer / tall deciduous); vine maple is the only small tree


def init(site_json):
    global S
    S = load_site(json.loads(site_json)); return len(S["trees"])


def designs(n, seed=1, setup=None):
    """setup: {"locks": {plot or choice: value}, "mgmt": {...}, "events": {event: False}} as assembled by the designer."""
    rng = np.random.default_rng([seed, 9]); cand = ex.candidates(S, MODE); st = json.loads(setup) if setup else {}
    return json.dumps([ex.sample(S, cand, rng, st.get("locks"), st.get("mgmt"), st.get("events")) for _ in range(n)])


def run_design(d_json, f0, f1):
    """All futures f0..f1-1 for one design: one row of metrics per future."""
    d = json.loads(d_json)
    return json.dumps([[round(float(v), 4) for v in ex.measure(ex.run_d(S, d, f), len(S["trees"]))] for f in range(f0, f1)])


def open_story(d_json, seed):
    global R
    data, R = story.build(S, json.loads(d_json), int(seed), open_plots=[k for k, v in ex.candidates(S, MODE).items() if len(v) > 1]); story.frame_view(S, R); return json.dumps(data)


def draw(year, title=""):
    os.makedirs("/tmp/v", exist_ok=True); story.draw(S, R, int(year), "/tmp/v/", title); return "/tmp/v/"


def meta():
    from engine.model import DEFAULT_DEC, SWITCHES
    return json.dumps(dict(metrics=ex.METRICS, cats=ex.CATS, trees=len(S["trees"]), patches=len(S["patches"]), candidates={k: v for k, v in ex.candidates(S, MODE).items() if len(v) > 1},
                           recipes=list(ex.RECIPES), choices=ex.CHOICES, defaults=DEFAULT_DEC, switches=SWITCHES, tree_ids=[t["id"] for t in S["trees"]]))
