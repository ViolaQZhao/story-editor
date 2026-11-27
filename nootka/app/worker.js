// Runs the Python engine (the same files as on the desktop) inside the browser.
let py = null, api = null, base = "";
const getJSON = async u => { const r = await fetch(u); if (!r.ok) throw new Error("could not load " + u.split("/").pop() + " (" + r.status + ")"); return r.json(); };
const bytes = v => { if (typeof v === "string") return new TextEncoder().encode(v); const bin = atob(v[1]), u = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i); return u; };
// Python needs its standard library as one zip file: build it (stored, not compressed) from the file list.
const CRC = (() => { const t = new Uint32Array(256); for (let n = 0; n < 256; n++) { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1; t[n] = c >>> 0; } return t; })();
const crc32 = u => { let c = 0xFFFFFFFF; for (let i = 0; i < u.length; i++) c = CRC[(c ^ u[i]) & 255] ^ (c >>> 8); return (c ^ 0xFFFFFFFF) >>> 0; };
function zip(files) {
  const parts = [], central = []; let off = 0; const enc = new TextEncoder();
  for (const [name, v] of Object.entries(files)) { const data = bytes(v), nm = enc.encode(name), crc = crc32(data);
    const h = new DataView(new ArrayBuffer(30)); h.setUint32(0, 0x04034b50, true); h.setUint16(4, 20, true); h.setUint16(6, 0x800, true); h.setUint16(8, 0, true); h.setUint32(10, 0x00210000, true);
    h.setUint32(14, crc, true); h.setUint32(18, data.length, true); h.setUint32(22, data.length, true); h.setUint16(26, nm.length, true);
    const c = new DataView(new ArrayBuffer(46)); c.setUint32(0, 0x02014b50, true); c.setUint16(4, 20, true); c.setUint16(6, 20, true); c.setUint16(8, 0x800, true); c.setUint32(12, 0x00210000, true);
    c.setUint32(16, crc, true); c.setUint32(20, data.length, true); c.setUint32(24, data.length, true); c.setUint16(28, nm.length, true); c.setUint32(42, off, true);
    parts.push(new Uint8Array(h.buffer), nm, data); central.push(new Uint8Array(c.buffer), nm); off += 30 + nm.length + data.length; }
  const cs = central.reduce((a, b) => a + b.length, 0), e = new DataView(new ArrayBuffer(22)); e.setUint32(0, 0x06054b50, true);
  e.setUint16(8, central.length / 2, true); e.setUint16(10, central.length / 2, true); e.setUint32(12, cs, true); e.setUint32(16, off, true);
  return new Blob([...parts, ...central, new Uint8Array(e.buffer)]);
}
// A package is its Python files (JSON) plus its compiled modules (.wasm): write both into site-packages.
async function install(pyo, name) {
  const pk = await getJSON(pyo + name + ".json"), site = "/lib/python3.12/site-packages/";
  const put = (path, data) => { const dir = (site + path).slice(0, (site + path).lastIndexOf("/")); py.FS.mkdirTree(dir); py.FS.writeFile(site + path, data); };
  for (const [path, v] of Object.entries(pk.files)) put(path, bytes(v));
  await Promise.all(Object.entries(pk.so).map(async ([path, u]) => { const r = await fetch(pyo + u); if (!r.ok) throw new Error("could not load " + u); put(path, new Uint8Array(await r.arrayBuffer())); }));
  py.runPython("import importlib; importlib.invalidate_caches()");
}
const send = (m, tr) => postMessage(m, tr || []);
onmessage = async e => {
  const m = e.data;
  try {
    if (m.t === "init") {
      base = m.pyo; send({t: "step", s: "Loading the Python runtime (1 of 4)"});
      importScripts(m.pyo + "pyodide.js");
      const std = await getJSON(m.pyo + "stdlib.json");
      send({t: "step", s: "Starting Python (2 of 4)"});
      const stdURL = URL.createObjectURL(new Blob([zip(std.files)], {type: "application/zip"}));
      py = await loadPyodide({indexURL: m.pyo, stdLibURL: stdURL, lockFileURL: m.pyo + "pyodide-lock.json"});
      send({t: "step", s: "Loading the number library (3 of 4)"});
      await install(m.pyo, "numpy");
      send({t: "step", s: "Loading the engine and the site (4 of 4)"});
      py.FS.mkdirTree("/app/engine");
      for (const [path, src] of Object.entries(m.bundle.py)) py.FS.writeFile("/app/" + path, src);
      py.runPython("import sys; sys.path.insert(0, '/app')");
      api = py.pyimport("web_api"); api.init(m.bundle.site);
      send({t: "ready", meta: api.meta()});
    } else if (m.t === "designs") {
      send({t: "designs", v: api.designs(m.n, m.seed, m.setup || null)});
    } else if (m.t === "run") {
      send({t: "rows", di: m.di, rows: api.run_design(m.d, m.f0, m.f1)});
    } else if (m.t === "draw_ready") {
      await install(base, "pillow");
      const bin = atob(m.font), u8 = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
      py.FS.writeFile("/tmp/DejaVuSansMono.ttf", u8); send({t: "draw_ready"});
    } else if (m.t === "story") {
      send({t: "story", key: m.key, data: api.open_story(m.d, m.seed)});
    } else if (m.t === "draw") {
      const dir = api.draw(m.year, m.title), out = {}, tr = [];
      for (const n of ["plan", "section", "model", "plan_id", "section_id", "model_id"]) { const b = py.FS.readFile(dir + n + ".png"); out[n] = b.buffer; tr.push(b.buffer); }
      send({t: "drawn", key: m.key, year: m.year, files: out}, tr);
    }
  } catch (err) { send({t: "error", at: m.t, msg: String(err && err.message || err)}); }
};
