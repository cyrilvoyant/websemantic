// Loads Python (Pyodide) and the pinned scientific codes in the background, then runs glue.py functions on request.
importScripts("https://cdn.jsdelivr.net/pyodide/v0.27.2/full/pyodide.js");

let py = null;

async function sha256(data) {
  const digest = await crypto.subtle.digest("SHA-256", data);
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

async function init() {
  py = await loadPyodide();
  await py.loadPackage(["numpy", "pandas", "pyyaml", "micropip"]);
  await py.pyimport("micropip").install(["rdflib==7.6.0"]);
  const bundle = await (await fetch("bundle.zip", { cache: "no-cache" })).arrayBuffer();
  py.FS.mkdirTree("/home/pyodide/ws");
  py.unpackArchive(bundle, "zip", { extractDir: "/home/pyodide/ws" });
  const glue = await (await fetch("glue.py", { cache: "no-cache" })).text();
  py.FS.writeFile("/home/pyodide/glue.py", glue);
  py.runPython("import sys; sys.path[:0] = ['/home/pyodide/ws/src', '/home/pyodide']; import glue");
  // fingerprints of exactly what runs here, for the visitor's trace
  postMessage({ type: "ready", hashes: { "bundle.zip": await sha256(bundle), "glue.py": await sha256(new TextEncoder().encode(glue)) } });
}

const ready = init().catch((e) => postMessage({ type: "error", error: String(e) }));

// the ontology's SHACL shapes: pure-Python packages, pinned, loaded after the codes; every LQL-Equiv turn waits for them
const SHACL = ["pyshacl==0.40.1", "owlrl==7.6.2", "html5rdf==1.2.1", "prettytable==3.18.0", "wcwidth==0.9.1"];
const shacl = ready.then(async () => {
  const start = performance.now();
  await py.pyimport("micropip").install(SHACL);
  py.runPython("import pyshacl");
  postMessage({ type: "shacl", ok: true, packages: SHACL, seconds: Math.round(performance.now() - start) / 1000 });
}).catch((e) => postMessage({ type: "shacl", ok: false, error: String(e) }));

onmessage = async (event) => {
  const { id, fn, args } = event.data;
  try {
    await ready;
    if (args[0] === "lql" && (fn === "api_turn" || fn === "api_example")) await shacl;  // never compute unchecked
    const glue = py.pyimport("glue");
    postMessage({ id, result: glue[fn](...args) });
  } catch (e) {
    postMessage({ id, error: String(e) });
  }
};
