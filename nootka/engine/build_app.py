"""Pack the engine, the site and the label font into one file the browser app loads.
Run from nootka/engine: python3 build_app.py (needs the DejaVu Sans Mono font installed)."""
import json, base64
files = ["engine/__init__.py", "engine/model.py", "engine/species.py", "engine/site.py", "engine/explore.py", "engine/story.py",
         "render_section.py", "render_views.py", "render_fine.py", "web_api.py"]
b = dict(py={f: open(f).read() for f in files}, site=open("inputs/site_full.json").read(),
         font=base64.b64encode(open("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", "rb").read()).decode())
json.dump(b, open("../app/bundle.json", "w")); import os; print(os.path.getsize("../app/bundle.json") // 1024, "KB")
