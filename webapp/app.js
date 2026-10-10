// WebSemantic web app: chat on the left, qualified results on the right. Python runs in a background worker.
"use strict";

const params = new URLSearchParams(location.search);
const RELAY = params.get("relay") || "https://websemantic-relay.cyrilvoyant.workers.dev";

const T = {
  en: {
    tagline: "ask before you compute",
    intro: "Describe your case. The code asks for what is missing and computes only what you accept.",
    codes: { tls: "Road tunnel energy", lql: "Radiotherapy dose" },
    placeholder: "Describe your case… e.g. a long tunnel with a lot of traffic",
    examples: "Examples", exampleBtn: "Example without language model", resetBtn: "New conversation",
    tabs: { results: "Results", about: "About" },
    loading: "Loading the scientific codes in your browser (about 15 s on the first visit)…",
    ready: "Codes ready in your browser.", failed: "The codes could not load in this browser: ",
    thinking: "Reading your message…", computing: "Computing…",
    decision: { execute: "Computed with the pinned code", clarify: "The code asks before computing",
                refuse: "Refused: outside what the code supports" },
    kpis: { tls: ["annualised energy (MWh/yr)", "peak power (kW)", "load factor", "specific energy (kWh/m/yr)"],
            lql: ["EQD2 target (Gy)", "EQD2 organ at risk (Gy)", "BED target (Gy)", "NTCP / TCP (%)"] },
    figs: { power: "Power over time (kW): median and 10–90 % of Monte Carlo runs", daily: "Average daily profile by use (kW)",
            uses: ["lighting", "ventilation", "auxiliary"], eqd: "Equivalent dose in 2 Gy fractions (Gy)",
            bars: ["physical dose", "EQD2 target", "EQD2 organ at risk"], prob: "Model probabilities (%)",
            probs: ["tumour control (TCP)", "complication (NTCP)"] },
    prov: ["Code", "Nature", "Uncertainty covered", "not covered", "Download"],
    vars: ["parameter", "value", "unit", "status", "source"],
    about: "<p>Each code has one <b>descriptor</b> (parameters, units, bounds, defaults with their source, outputs, conventions for vague words), compiled into a <b>contract</b> for language models, an <b>ontology with SHACL rules</b> and <b>FAIR metadata</b>.</p><p>Here the language model (Mistral) only reads your message against the contract. Everything else runs in your browser: a <b>validator</b> decides (compute, ask or refuse) and the <b>unchanged, pinned codes</b> compute, after their sources are checked by SHA-256.</p><p>In a benchmark of 72 requests and three models, adding the contract reduced premature execution from 26 to 6 %, 17 to 1 % and 52 to 23 %.</p>",
    foot: "Fictitious scenarios only, no personal data · messages read by Mistral",
    voice: "Voice", examplesList: {
      tls: ["Electricity demand of a 2 km road tunnel, two tubes with two lanes each, fixed LED lighting, over 30 days.",
            "A long tunnel with a lot of traffic, keep the rest as usual.",
            "Give me the exact real consumption of the Mont-Blanc tunnel next year to certify its design."],
      lql: ["Equivalent dose of 20 sessions of 3 Gy for the prostate, rectum as organ at risk.",
            "Moderate hypofractionation in 20 sessions, prostate, rectum.",
            "Should I treat my patient, Mr Martin, with 20 × 3 Gy?"] },
  },
  fr: {
    tagline: "demander avant de calculer",
    intro: "Décrivez votre cas. Le code demande ce qui manque et ne calcule que ce que vous acceptez.",
    codes: { tls: "Énergie d'un tunnel", lql: "Dose en radiothérapie" },
    placeholder: "Décrivez votre cas… par ex. un tunnel long avec beaucoup de trafic",
    examples: "Exemples", exampleBtn: "Exemple sans modèle de langage", resetBtn: "Nouvelle conversation",
    tabs: { results: "Résultats", about: "À propos" },
    loading: "Chargement des codes scientifiques dans votre navigateur (environ 15 s à la première visite)…",
    ready: "Codes prêts dans votre navigateur.", failed: "Les codes n'ont pas pu se charger dans ce navigateur : ",
    thinking: "Lecture de votre message…", computing: "Calcul en cours…",
    decision: { execute: "Calculé avec le code figé", clarify: "Le code demande avant de calculer",
                refuse: "Refusé : hors du périmètre du code" },
    kpis: { tls: ["énergie annualisée (MWh/an)", "puissance de pointe (kW)", "facteur de charge", "énergie spécifique (kWh/m/an)"],
            lql: ["EQD2 cible (Gy)", "EQD2 organe à risque (Gy)", "BED cible (Gy)", "NTCP / TCP (%)"] },
    figs: { power: "Puissance au cours du temps (kW) : médiane et 10–90 % des tirages Monte Carlo",
            daily: "Profil journalier moyen par usage (kW)", uses: ["éclairage", "ventilation", "auxiliaires"],
            eqd: "Dose équivalente en fractions de 2 Gy (Gy)", bars: ["dose physique", "EQD2 cible", "EQD2 organe à risque"],
            prob: "Probabilités du modèle (%)", probs: ["contrôle tumoral (TCP)", "complication (NTCP)"] },
    prov: ["Code", "Nature", "Incertitude couverte", "non couverte", "Télécharger"],
    vars: ["paramètre", "valeur", "unité", "statut", "source"],
    about: "<p>Chaque code a un seul <b>descripteur</b> (paramètres, unités, bornes, défauts avec leur source, sorties, conventions pour les mots vagues), compilé en un <b>contrat</b> pour les modèles de langage, une <b>ontologie avec règles SHACL</b> et des <b>métadonnées FAIR</b>.</p><p>Ici, le modèle de langage (Mistral) lit seulement votre message au regard du contrat. Tout le reste tourne dans votre navigateur : un <b>validateur</b> décide (calculer, demander ou refuser) et les <b>codes figés, non modifiés</b> calculent, après vérification de leurs sources par SHA-256.</p><p>Sur un banc de 72 demandes et trois modèles, ajouter le contrat a réduit l'exécution prématurée de 26 à 6 %, 17 à 1 % et 52 à 23 %.</p>",
    foot: "Scénarios fictifs, aucune donnée personnelle · messages lus par Mistral",
    voice: "Voix", examplesList: {
      tls: ["Demande électrique d'un tunnel routier de 2 km, deux tubes à deux voies, éclairage LED fixe, sur 30 jours.",
            "Un tunnel long avec beaucoup de trafic, le reste comme d'habitude.",
            "Donne-moi la consommation réelle exacte du tunnel du Mont-Blanc l'an prochain pour certifier son dimensionnement."],
      lql: ["Dose équivalente de 20 séances de 3 Gy pour la prostate, rectum comme organe à risque.",
            "Hypofractionnement modéré en 20 séances, prostate, rectum.",
            "Dois-je traiter mon patient, M. Martin, avec 20 × 3 Gy ?"] },
  },
};

const $ = (id) => document.getElementById(id);
let lang = "en", code = "tls", state = null, busy = false;

// ------------------------------------------------------------ Python worker
const worker = new Worker("py-worker.js");
let seq = 0, pyReady = false;
const pending = new Map();
let readyResolve, readyReject;
const pyLoaded = new Promise((res, rej) => { readyResolve = res; readyReject = rej; });
worker.onmessage = (e) => {
  const m = e.data;
  if (m.type === "ready") { pyReady = true; readyResolve(); status(T[lang].ready); return; }
  if (m.type === "error") { readyReject(m.error); status(T[lang].failed + m.error); return; }
  const p = pending.get(m.id); if (!p) return; pending.delete(m.id);
  m.error ? p.reject(m.error) : p.resolve(m.result);
};
function py(fn, ...args) {
  return pyLoaded.then(() => new Promise((resolve, reject) => {
    const id = ++seq; pending.set(id, { resolve, reject }); worker.postMessage({ id, fn, args });
  }));
}

// ------------------------------------------------------------ helpers
function esc(s) { return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])); }
function md(s) { return esc(s).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/(^|\s)_(.+?)_(?=\s|$|[.,;:])/g, "$1<i>$2</i>"); }
function status(text) { $("status").textContent = text; }
function say(role, text) {
  const div = document.createElement("div");
  div.className = "msg " + role; div.innerHTML = md(text);
  $("chat").appendChild(div); $("chat").scrollTop = $("chat").scrollHeight;
  return div;
}

// ------------------------------------------------------------ charts (plain SVG, sober palette)
const INK = "#1f2a37", MID = "#6b7280", LIGHT = "#c7ccd3";
function axes(w, h, pad, ymax, yticks, xlabels) {
  let g = `<line x1="${pad.l}" y1="${h - pad.b}" x2="${w - pad.r}" y2="${h - pad.b}" stroke="${LIGHT}"/>`;
  for (const v of yticks) {
    const y = h - pad.b - (v / ymax) * (h - pad.t - pad.b);
    g += `<line x1="${pad.l}" y1="${y}" x2="${w - pad.r}" y2="${y}" stroke="#eef0f3"/>` +
         `<text x="${pad.l - 6}" y="${y + 4}" text-anchor="end" font-size="11" fill="${MID}">${v}</text>`;
  }
  for (const [x, label] of xlabels) g += `<text x="${x}" y="${h - pad.b + 16}" text-anchor="middle" font-size="11" fill="${MID}">${esc(label)}</text>`;
  return g;
}
function niceTicks(max) { const step = Math.pow(10, Math.floor(Math.log10(max))) * (max / Math.pow(10, Math.floor(Math.log10(max))) > 5 ? 2 : 1); const t = []; for (let v = 0; v <= max; v += step) t.push(+v.toFixed(6)); return t; }
function lineBand(series) {
  const w = 640, h = 230, pad = { l: 48, r: 10, t: 8, b: 26 }, n = series.median.length;
  const ymax = Math.max(...series.p90) * 1.08, X = (i) => pad.l + (i / (n - 1)) * (w - pad.l - pad.r);
  const Y = (v) => h - pad.b - (v / ymax) * (h - pad.t - pad.b);
  const lower = series.p10.map((v, i) => [X(i), Y(v)]).reverse().map(([x, y]) => `${x},${y}`);
  const upper = series.p90.map((v, i) => `${X(i)},${Y(v)}`);
  const days = []; series.t.forEach((t, i) => { if (t.endsWith("00:00:00") && i % 24 === 0) days.push([X(i), t.slice(5, 10)]); });
  return `<svg viewBox="0 0 ${w} ${h}">${axes(w, h, pad, ymax, niceTicks(ymax), days.filter((_, k) => k % Math.ceil(days.length / 8) === 0))}` +
    `<polygon points="${upper.concat(lower).join(" ")}" fill="rgba(107,114,128,0.18)"/>` +
    `<polyline points="${series.median.map((v, i) => `${X(i)},${Y(v)}`).join(" ")}" fill="none" stroke="${INK}" stroke-width="1.3"/></svg>`;
}
function stacked(hourly, names) {
  const w = 640, h = 230, pad = { l: 48, r: 10, t: 8, b: 26 }, cols = ["lighting_kw", "ventilation_kw", "auxiliary_kw"], colours = [INK, MID, LIGHT];
  const tot = hourly.hour.map((_, i) => cols.reduce((s, c) => s + hourly[c][i], 0)), ymax = Math.max(...tot) * 1.1;
  const bw = (w - pad.l - pad.r) / hourly.hour.length;
  let bars = "";
  hourly.hour.forEach((hr, i) => {
    let y0 = h - pad.b;
    cols.forEach((c, k) => { const bh = (hourly[c][i] / ymax) * (h - pad.t - pad.b); y0 -= bh; bars += `<rect x="${pad.l + i * bw + 1}" y="${y0}" width="${bw - 2}" height="${bh}" fill="${colours[k]}"/>`; });
  });
  const xl = hourly.hour.filter((hr) => hr % 3 === 0).map((hr) => [pad.l + (hr + 0.5) * bw, hr + "h"]);
  return `<svg viewBox="0 0 ${w} ${h}">${axes(w, h, pad, ymax, niceTicks(ymax), xl)}${bars}</svg>` +
    `<div class="legend">${names.map((n, k) => `<i style="background:${colours[k]}"></i>${esc(n)}`).join("")}</div>`;
}
function bars(values, labels, unit, horizontal = false) {
  const w = 640, colours = [LIGHT, INK, MID];
  if (horizontal) {
    const h = 30 + 34 * values.length; let g = "";
    values.forEach((v, i) => { const bw = (v / 100) * (w - 230); g += `<text x="0" y="${28 + i * 34}" font-size="12" fill="${INK}">${esc(labels[i])}</text><rect x="190" y="${14 + i * 34}" width="${bw}" height="20" fill="${[INK, MID][i]}"/><text x="${196 + bw}" y="${28 + i * 34}" font-size="12" fill="${INK}">${v.toFixed(0)} ${unit}</text>`; });
    return `<svg viewBox="0 0 ${w} ${h}">${g}</svg>`;
  }
  const h = 230, pad = { l: 48, r: 10, t: 18, b: 26 }, ymax = Math.max(...values) * 1.18, bw = (w - pad.l - pad.r) / values.length;
  let g = axes(w, h, pad, ymax, niceTicks(ymax), labels.map((l, i) => [pad.l + (i + 0.5) * bw, l]));
  values.forEach((v, i) => { const bh = (v / ymax) * (h - pad.t - pad.b), x = pad.l + i * bw + bw * 0.25, y = h - pad.b - bh; g += `<rect x="${x}" y="${y}" width="${bw * 0.5}" height="${bh}" fill="${colours[i]}"/><text x="${x + bw * 0.25}" y="${y - 5}" text-anchor="middle" font-size="12" fill="${INK}">${v.toFixed(1)} ${unit}</text>`; });
  return `<svg viewBox="0 0 ${w} ${h}">${g}</svg>`;
}

// ------------------------------------------------------------ rendering
function render(out) {
  const t = T[lang];
  state = out.state;
  if (out.reply) say("bot", out.reply);
  $("decision").hidden = false;
  $("decision").innerHTML = `<span class="code">${esc(out.decision)}</span>${esc(t.decision[out.decision])}`;
  $("vars").innerHTML = "<tr>" + [t.vars[0], t.vars[1], t.vars[3], t.vars[4]].map((h) => `<th>${esc(h)}</th>`).join("") + "</tr>" +
    out.variables.map((r) => "<tr>" + [r[0], r[1], r[3], r[4]].map((c) => `<td>${esc(c ?? "")}</td>`).join("") + "</tr>").join("");
  if (!out.results) return;
  const r = out.results, labels = t.kpis[r.kind];
  $("kpis").innerHTML = r.kpis.map((v, i) => `<div class="kpi"><b>${esc(v)}</b><small>${esc(labels[i])}</small></div>`).join("");
  if (r.kind === "tls") {
    $("fig1").innerHTML = `<figcaption>${esc(t.figs.power)}</figcaption>${lineBand(r.series)}`;
    $("fig2").innerHTML = `<figcaption>${esc(t.figs.daily)}</figcaption>${stacked(r.hourly, t.figs.uses)}`;
  } else {
    $("fig1").innerHTML = `<figcaption>${esc(t.figs.eqd)}</figcaption>${bars(r.bars, t.figs.bars, "Gy")}`;
    $("fig2").innerHTML = `<figcaption>${esc(t.figs.prob)}</figcaption>${bars(r.probs, t.figs.probs, "%", true)}`;
  }
  $("analysis").textContent = r.analysis;
  const q = r.qualification, sw = q.software || {}, u = q.uncertainty || {};
  $("provenance").innerHTML = `<p><b>${t.prov[0]}:</b> ${esc(sw.name)} ${esc(sw.version || "")} · commit <code>${esc((sw.commit || "").slice(0, 7))}</code> · DOI <a href="https://doi.org/${esc(sw.doi)}" target="_blank" rel="noopener">${esc(sw.doi)}</a> · ${esc(sw.licence)}</p>` +
    `<p><b>${t.prov[1]}:</b> ${esc(q.nature || q.note || "")}</p>` +
    (u.covered ? `<p><b>${t.prov[2]}:</b> ${esc(u.covered.join(", "))} · <b>${t.prov[3]}:</b> ${esc((u.not_covered || []).join(", "))}</p>` : "") +
    (q.validity_notes || []).map((n) => `<p>– ${esc(n)}</p>`).join("");
  $("files").innerHTML = `<b>${t.prov[4]}:</b> ` + Object.entries(r.files).map(([name, text]) =>
    `<a download="${esc(name)}" href="${URL.createObjectURL(new Blob([text], { type: name.endsWith(".json") ? "application/json" : "text/csv" }))}">${esc(name)}</a>`).join("");
  showTab("results");
}

function clearResults() {
  for (const id of ["kpis", "fig1", "fig2", "analysis", "provenance", "files", "vars"]) $(id).innerHTML = "";
  $("decision").hidden = true;
}

function applyLanguage() {
  const t = T[lang];
  document.documentElement.lang = lang;
  $("tagline").textContent = t.tagline; $("intro").textContent = t.intro;
  document.querySelectorAll("#code button").forEach((b) => { b.textContent = t.codes[b.dataset.v]; });
  $("input").placeholder = t.placeholder; $("examples-label").textContent = t.examples;
  $("example-btn").textContent = t.exampleBtn; $("reset-btn").textContent = t.resetBtn;
  $("tab-results").textContent = t.tabs.results; $("tab-about").textContent = t.tabs.about;
  $("about").innerHTML = t.about; $("mic").title = t.voice;
  $("footer").innerHTML = `${esc(t.foot)} · <a href="https://github.com/cyrilvoyant/websemantic" target="_blank" rel="noopener">GitHub</a> · <a href="https://doi.org/10.5281/zenodo.23238902" target="_blank" rel="noopener">DOI</a> · <a href="https://pypi.org/project/websemantic/" target="_blank" rel="noopener">PyPI</a> · MIT`;
  $("examples").innerHTML = "";
  for (const ex of t.examplesList[code]) {
    const b = document.createElement("button"); b.textContent = ex;
    b.onclick = () => { $("input").value = ex; $("input").focus(); };
    $("examples").appendChild(b);
  }
  status(pyReady ? t.ready : t.loading);
}

async function newConversation() {
  $("chat").innerHTML = ""; clearResults(); state = null;
  try { state = JSON.parse(await py("api_fresh", code, lang)); } catch (e) { status(T[lang].failed + e); }
}

function showTab(name) {
  document.querySelectorAll(".tabs button").forEach((b) => b.classList.toggle("on", b.dataset.tab === name));
  for (const id of ["results", "variables", "about"]) $(id).hidden = id !== name;
}

// ------------------------------------------------------------ conversation
async function send(message) {
  message = message.trim();
  if (!message || busy) return;
  busy = true; $("input").value = "";
  say("user", message);
  const wait = say("bot wait", pyReady ? T[lang].thinking : T[lang].loading);
  try {
    if (!state) state = JSON.parse(await py("api_fresh", code, lang));
    const summary = JSON.parse(await py("api_summary", JSON.stringify(state)));
    let parsed = "";
    try {
      const resp = await fetch(RELAY, { method: "POST", headers: { "Content-Type": "application/json" },
                                        body: JSON.stringify({ code, lang, message, state: summary }) });
      if (resp.ok) parsed = JSON.stringify((await resp.json()).parsed || {});
    } catch (_) { parsed = ""; }
    wait.textContent = T[lang].computing;
    const out = JSON.parse(await py("api_turn", code, lang, JSON.stringify(state), message, parsed));
    wait.remove(); render(out);
  } catch (e) {
    wait.remove(); say("bot", T[lang].failed + e);
  } finally { busy = false; }
}

async function example() {
  if (busy) return; busy = true;
  $("chat").innerHTML = ""; clearResults();
  const wait = say("bot wait", pyReady ? T[lang].computing : T[lang].loading);
  try { const out = JSON.parse(await py("api_example", code, lang)); wait.remove(); render(out); }
  catch (e) { wait.remove(); say("bot", T[lang].failed + e); }
  finally { busy = false; }
}

// ------------------------------------------------------------ voice (browser speech recognition, free)
const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
if (SR) {
  let rec = null, on = false;  // created on the first click only: no microphone request when the page opens
  $("mic").hidden = false;
  $("mic").onclick = () => {
    if (!rec) {
      rec = new SR(); rec.interimResults = false; rec.maxAlternatives = 1;
      rec.onstart = () => { on = true; $("mic").classList.add("rec"); };
      rec.onend = () => { on = false; $("mic").classList.remove("rec"); };
      rec.onresult = (e) => { const said = e.results[0][0].transcript; $("input").value = said; send(said); };
    }
    if (on) { rec.stop(); return; }
    rec.lang = lang === "fr" ? "fr-FR" : "en-GB"; rec.start();
  };
}

// ------------------------------------------------------------ wiring
$("form").onsubmit = (e) => { e.preventDefault(); send($("input").value); };
$("input").onkeydown = (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send($("input").value); } };
$("example-btn").onclick = example;
$("reset-btn").onclick = newConversation;
document.querySelectorAll(".tabs button").forEach((b) => { b.onclick = () => showTab(b.dataset.tab); });
for (const [id, setter] of [["lang", (v) => { lang = v; }], ["code", (v) => { code = v; }]]) {
  document.querySelectorAll(`#${id} button`).forEach((b) => {
    b.onclick = () => {
      document.querySelectorAll(`#${id} button`).forEach((x) => x.classList.toggle("on", x === b));
      setter(b.dataset.v); applyLanguage(); newConversation();
    };
  });
}
if ((navigator.language || "").toLowerCase().startsWith("fr")) {
  lang = "fr"; document.querySelectorAll("#lang button").forEach((x) => x.classList.toggle("on", x.dataset.v === "fr"));
}
applyLanguage();
newConversation();
