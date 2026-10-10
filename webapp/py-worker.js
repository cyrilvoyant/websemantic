// Loads Python (Pyodide) and the pinned scientific codes in the background, then runs glue.py functions on request.
importScripts("https://cdn.jsdelivr.net/pyodide/v0.27.2/full/pyodide.js");

let py = null;

async function init() {
  py = await loadPyodide();
  await py.loadPackage(["numpy", "pandas", "pyyaml", "micropip"]);
  await py.pyimport("micropip").install(["rdflib==7.1.1"]);
  const bundle = await (await fetch("bundle.zip", { cache: "no-cache" })).arrayBuffer();
  py.FS.mkdirTree("/home/pyodide/ws");
  py.unpackArchive(bundle, "zip", { extractDir: "/home/pyodide/ws" });
  py.FS.writeFile("/home/pyodide/glue.py", await (await fetch("glue.py", { cache: "no-cache" })).text());
  py.runPython("import sys; sys.path[:0] = ['/home/pyodide/ws/src', '/home/pyodide']; import glue");
  postMessage({ type: "ready" });
}

const ready = init().catch((e) => postMessage({ type: "error", error: String(e) }));

onmessage = async (event) => {
  const { id, fn, args } = event.data;
  try {
    await ready;
    const glue = py.pyimport("glue");
    postMessage({ id, result: glue[fn](...args) });
  } catch (e) {
    postMessage({ id, error: String(e) });
  }
};
