"""Convert the Python-in-the-browser runtime into file types the page host serves: the standard library and the pure-Python
parts of numpy and Pillow become JSON (file name -> text), their compiled modules become .wasm files (which they are).
SRC is an unpacked Pyodide 0.26.4 release (github.com/pyodide/pyodide/releases). Only needed to rebuild app/py."""
import zipfile, json, base64, os, shutil
SRC = "/tmp/pyo/pyodide"; OUT = "../app/py"; shutil.rmtree(OUT, ignore_errors=True); os.makedirs(OUT + "/so")
for f in ("pyodide.js", "pyodide.asm.js", "pyodide.asm.wasm", "pyodide-lock.json"): shutil.copy(f"{SRC}/{f}", f"{OUT}/{f}")
def enc(b):
    try: return b.decode("utf-8")
    except UnicodeDecodeError: return ["b", base64.b64encode(b).decode()]
def conv(src, name, skip=()):
    z = zipfile.ZipFile(src); files = {}; so = {}
    for i in z.infolist():
        if i.is_dir() or i.filename.endswith(skip): continue
        if i.filename.endswith(".so"):
            n = f"so/{name}_{len(so):02d}.wasm"; open(f"{OUT}/{n}", "wb").write(z.read(i)); so[i.filename] = n
        else: files[i.filename] = enc(z.read(i))
    json.dump(dict(files=files, so=so), open(f"{OUT}/{name}.json", "w")); print(name, len(files), "files,", len(so), "modules,", os.path.getsize(f"{OUT}/{name}.json") // 1024, "KB")
conv(f"{SRC}/python_stdlib.zip", "stdlib")
conv(f"{SRC}/numpy-1.26.4-cp312-cp312-pyodide_2024_0_wasm32.whl", "numpy", skip=(".pyi", ".h", ".c", ".pxd", ".f90", ".f", ".pyf"))
conv(f"{SRC}/pillow-10.2.0-cp312-cp312-pyodide_2024_0_wasm32.whl", "pillow", skip=(".pyi",))
