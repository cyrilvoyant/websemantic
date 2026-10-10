// WebSemantic web app: chat on the left, qualified results on the right. Python runs in a background worker.
"use strict";
const APP_VERSION = "0.3.6";  // also in index.html (cache busting) and the footer

const params = new URLSearchParams(location.search);
const LOCAL = ["localhost", "127.0.0.1"].includes(location.hostname);
// The relay address is fixed; ?relay= is honoured only for local development.
const RELAY = (LOCAL && params.get("relay")) || "https://websemantic-relay.cyrilvoyant.workers.dev";

const T = {
  en: {
    tagline: "ask before you compute",
    intro: "Describe your case. The code asks for what is missing and computes only what you accept.",
    codes: { tls: "Road tunnel energy", lql: "Radiotherapy dose" },
    placeholder: { tls: "Describe your case… e.g. a long tunnel with a lot of traffic", lql: "Describe your case… e.g. 20 sessions of 3 Gy, prostate, rectum as organ at risk" },
    allCases: "All cases", details: "Technical details (versions, checks, options)", varsNote: "To work in the original application, open it and enter these values:", openApp: { lql: "Open the original LQL-Equiv", tls: "Open the original TLS (code and app)" }, examples: "Examples", more: "Other examples ↻", tags: { refuse: "refusal example", ask: "the code will ask" }, exampleBtn: "Example without language model", resetBtn: "New conversation",
    tabs: { results: "Results", about: "About" },
    loading: "Loading the scientific codes in your browser (about 15 s on the first visit)…",
    timeout: "The calculation took too long in this browser; nothing is shown.",
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
    prov: ["Code", "Nature", "Uncertainty covered", "not covered", "Download", "Model options", "Validity flags",
           "Source check"],
    vars: ["parameter", "value", "unit", "status", "source"],
    about: "<p><b>How it works.</b> Describe your case in your own words. A language model (Mistral) only turns your words into the parameters of the code; it never computes. The page shows what it understood, proposes the code's declared values for what you did not say, and computes only after your <b>yes</b>.</p><p><b>Who computes.</b> The original, unchanged codes (TLS for tunnels, LQL-Equiv for radiotherapy), run in your browser after their sources are checked.</p><p><b>Reading the results.</b> Every number comes from the code. The Variables tab shows each value and where it comes from: given by you, accepted convention or default. To keep a result, download its files: tables (CSV), manifest (versions and checks) and semantics.ttl (the same result described with the WebSemantic ontology).</p><p><b>Limits.</b> Fictitious scenarios for research and teaching: no real tunnel is certified, no treatment is decided.</p><p><b>Who.</b> Developed at the O.I.E. centre (Observation, Impacts, Énergie), Mines Paris – PSL, by Cyril Voyant.</p>",
    foot: "Fictitious scenarios only, no personal data · messages read by Mistral · voice recognised by your browser (it may use its vendor's online service)",
    voice: "Voice",
  },
  fr: {
    tagline: "demander avant de calculer",
    intro: "Décrivez votre cas. Le code demande ce qui manque et ne calcule que ce que vous acceptez.",
    codes: { tls: "Énergie d'un tunnel", lql: "Dose en radiothérapie" },
    placeholder: { tls: "Décrivez votre cas… par ex. un tunnel long avec beaucoup de trafic", lql: "Décrivez votre cas… par ex. 20 séances de 3 Gy, prostate, rectum comme organe à risque" },
    allCases: "Tous les cas", details: "Détails techniques (versions, vérifications, options)", varsNote: "Pour travailler dans l'application d'origine, ouvrez-la et saisissez ces valeurs :", openApp: { lql: "Ouvrir LQL-Equiv (application d'origine)", tls: "Ouvrir TLS d'origine (code et application)" }, examples: "Exemples", more: "Autres exemples ↻", tags: { refuse: "exemple de refus", ask: "le code demandera" }, exampleBtn: "Exemple sans modèle de langage", resetBtn: "Nouvelle conversation",
    tabs: { results: "Résultats", about: "À propos" },
    loading: "Chargement des codes scientifiques dans votre navigateur (environ 15 s à la première visite)…",
    timeout: "Le calcul a pris trop de temps dans ce navigateur ; rien n'est affiché.",
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
    prov: ["Code", "Nature", "Incertitude couverte", "non couverte", "Télécharger", "Options du modèle",
           "Indicateurs de validité", "Vérification des sources"],
    vars: ["paramètre", "valeur", "unité", "statut", "source"],
    about: "<p><b>Comment ça marche.</b> Décrivez votre cas avec vos mots. Un modèle de langage (Mistral) traduit seulement vos mots en paramètres du code ; il ne calcule jamais. La page montre ce qu'elle a compris, propose les valeurs déclarées par le code pour ce que vous n'avez pas dit, et ne calcule qu'après votre <b>oui</b>.</p><p><b>Qui calcule.</b> Les codes originaux, non modifiés (TLS pour les tunnels, LQL-Equiv pour la radiothérapie), dans votre navigateur, après vérification de leurs sources.</p><p><b>Lire les résultats.</b> Chaque nombre vient du code. L'onglet Variables montre chaque valeur et son origine : donnée par vous, convention acceptée ou valeur par défaut. Pour garder un résultat, téléchargez ses fichiers : tableaux (CSV), manifeste (versions et vérifications) et semantics.ttl (le même résultat décrit avec l'ontologie WebSemantic).</p><p><b>Limites.</b> Scénarios fictifs pour la recherche et l'enseignement : aucun tunnel réel n'est certifié, aucun traitement n'est décidé.</p><p><b>Qui.</b> Développé au centre O.I.E. (Observation, Impacts, Énergie), Mines Paris – PSL, par Cyril Voyant.</p>",
    foot: "Scénarios fictifs, aucune donnée personnelle · messages lus par Mistral · voix reconnue par votre navigateur (qui peut utiliser le service en ligne de son éditeur)",
    voice: "Voix",
  },
};

const $ = (id) => document.getElementById(id);
let lang = "en", code = "tls", state = null, busy = false, conversation = 0, blobs = [];

// ------------------------------------------------------------ Python worker
const worker = new Worker("py-worker.js?v=" + APP_VERSION);
let seq = 0, pyReady = false;
const pending = new Map();
let readyResolve, readyReject;
const pyLoaded = new Promise((res, rej) => { readyResolve = res; readyReject = rej; });
worker.onerror = (e) => { readyReject(String(e.message || e)); status(T[lang].failed + (e.message || e)); };
worker.onmessage = (e) => {
  const m = e.data;
  if (m.type === "ready") { pyReady = true; readyResolve(); status(T[lang].ready); return; }
  if (m.type === "error") { readyReject(m.error); status(T[lang].failed + m.error); return; }
  const p = pending.get(m.id); if (!p) return; pending.delete(m.id);
  m.error ? p.reject(m.error) : p.resolve(m.result);
};
function py(fn, ...args) {
  return pyLoaded.then(() => new Promise((resolve, reject) => {
    const id = ++seq;
    const timer = setTimeout(() => { pending.delete(id); reject(T[lang].timeout); }, 120000);
    pending.set(id, { resolve: (v) => { clearTimeout(timer); resolve(v); }, reject: (e) => { clearTimeout(timer); reject(e); } });
    worker.postMessage({ id, fn, args });
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
const INK = "#1c2836", MID = "#5f6b7a", LIGHT = "#b8c2cf", NAVY = "#1f3a5f", BLUE = "#3b7dd8", TEAL = "#2a9d8f", ORANGE = "#e07b3f";
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
function niceTicks(max) { if (!(max > 0) || !isFinite(max)) return [0]; const step = Math.pow(10, Math.floor(Math.log10(max))) * (max / Math.pow(10, Math.floor(Math.log10(max))) > 5 ? 2 : 1); const t = []; for (let v = 0; v <= max; v += step) t.push(+v.toFixed(6)); return t; }
function lineBand(series) {
  const w = 640, h = 230, pad = { l: 48, r: 10, t: 8, b: 26 }, n = series.median.length;
  const ymax = Math.max(...series.p90.filter(Number.isFinite), 1) * 1.08, X = (i) => pad.l + (i / (n - 1)) * (w - pad.l - pad.r);
  const Y = (v) => h - pad.b - (v / ymax) * (h - pad.t - pad.b);
  const lower = series.p10.map((v, i) => [X(i), Y(v)]).reverse().map(([x, y]) => `${x},${y}`);
  const upper = series.p90.map((v, i) => `${X(i)},${Y(v)}`);
  const days = []; series.t.forEach((t, i) => { if (t.endsWith("00:00:00") && i % 24 === 0) days.push([X(i), t.slice(5, 10)]); });
  return `<svg viewBox="0 0 ${w} ${h}">${axes(w, h, pad, ymax, niceTicks(ymax), days.filter((_, k) => k % Math.ceil(days.length / 8) === 0))}` +
    `<polygon points="${upper.concat(lower).join(" ")}" fill="rgba(59,125,216,0.16)"/>` +
    `<polyline points="${series.median.map((v, i) => `${X(i)},${Y(v)}`).join(" ")}" fill="none" stroke="${NAVY}" stroke-width="1.4"/></svg>`;
}
function stacked(hourly, names) {
  const w = 640, h = 230, pad = { l: 48, r: 10, t: 8, b: 26 }, cols = ["lighting_kw", "ventilation_kw", "auxiliary_kw"], colours = [BLUE, TEAL, ORANGE];
  const tot = hourly.hour.map((_, i) => cols.reduce((s, c) => s + (hourly[c][i] || 0), 0)), ymax = Math.max(...tot, 1) * 1.1;
  const bw = (w - pad.l - pad.r) / hourly.hour.length;
  let bars = "";
  hourly.hour.forEach((hr, i) => {
    let y0 = h - pad.b;
    cols.forEach((c, k) => { const bh = ((hourly[c][i] || 0) / ymax) * (h - pad.t - pad.b); y0 -= bh; bars += `<rect x="${pad.l + i * bw + 1}" y="${y0}" width="${bw - 2}" height="${bh}" fill="${colours[k]}" fill-opacity="0.82"/>`; });
  });
  const xl = hourly.hour.filter((hr) => hr % 3 === 0).map((hr) => [pad.l + (hr + 0.5) * bw, hr + "h"]);
  return `<svg viewBox="0 0 ${w} ${h}">${axes(w, h, pad, ymax, niceTicks(ymax), xl)}${bars}</svg>` +
    `<div class="legend">${names.map((n, k) => `<i style="background:${colours[k]}"></i>${esc(n)}`).join("")}</div>`;
}
function bars(values, labels, unit, horizontal = false) {
  const w = 640, colours = [LIGHT, TEAL, ORANGE];
  if (horizontal) {
    const h = 30 + 34 * values.length; let g = "";
    values.forEach((v, i) => { const ok = Number.isFinite(v), bw = ok ? (v / 100) * (w - 230) : 0; g += `<text x="0" y="${28 + i * 34}" font-size="12" fill="${INK}">${esc(labels[i])}</text><rect x="190" y="${14 + i * 34}" width="${bw}" height="20" fill="${[TEAL, ORANGE][i]}"/><text x="${196 + bw}" y="${28 + i * 34}" font-size="12" fill="${INK}">${ok ? v.toFixed(0) + " " + unit : "—"}</text>`; });
    return `<svg viewBox="0 0 ${w} ${h}">${g}</svg>`;
  }
  const h = 230, pad = { l: 48, r: 10, t: 18, b: 26 }, ymax = Math.max(...values.filter(Number.isFinite), 1) * 1.18, bw = (w - pad.l - pad.r) / values.length;
  let g = axes(w, h, pad, ymax, niceTicks(ymax), labels.map((l, i) => [pad.l + (i + 0.5) * bw, l]));
  values.forEach((v, i) => { const ok = Number.isFinite(v), bh = ok ? (v / ymax) * (h - pad.t - pad.b) : 0, x = pad.l + i * bw + bw * 0.25, y = h - pad.b - bh; g += `<rect x="${x}" y="${y}" width="${bw * 0.5}" height="${bh}" fill="${colours[i]}"/><text x="${x + bw * 0.25}" y="${y - 5}" text-anchor="middle" font-size="12" fill="${INK}">${ok ? v.toFixed(1) + " " + unit : "—"}</text>`; });
  return `<svg viewBox="0 0 ${w} ${h}">${g}</svg>`;
}

const APPS = { lql: "https://cyrilvoyant.github.io/LQL-Equiv-web/", tls: "https://github.com/cyrilvoyant/tunnel-load-simulator" };
function openApp() {
  return `<a class="app-link" href="${APPS[code]}" target="_blank" rel="noopener">${esc(T[lang].openApp[code])} ↗</a>`;
}
function table(tbl) {
  return `<div class="table-wrap"><table class="cases"><tr>${tbl.head.map((h) => `<th>${esc(h)}</th>`).join("")}</tr>` +
    tbl.rows.map((row) => `<tr>${row.map((c, i) => i ? `<td>${esc(c)}</td>` : `<th>${esc(c)}</th>`).join("")}</tr>`).join("") +
    "</table></div>";
}
function grouped(chart) {
  // grouped bars from a zero line (values may be negative: differences in %), with an optional reference line
  const w = 640, h = 260, pad = { l: 48, r: 10, t: 22, b: 40 }, cats = chart.categories, series = chart.series;
  const all = series.flatMap((s) => s.values).concat(chart.line ? [chart.line.value] : []).filter(Number.isFinite);
  const hi = Math.max(...all, 0), lo = Math.min(...all, 0), span = (hi - lo) || 1;
  // doses per session lie close together: the axis is zoomed around them (ticks shown), not started at 0
  const zoom = chart.zoom && all.length > 0 && Math.min(...all) > 0, pos = all.filter((v) => v > 0);
  const zlo = zoom ? Math.min(...pos) : lo, zspan = zoom ? (hi - zlo) || hi * 0.05 : span;
  const top = hi + zspan * (zoom ? 0.6 : 0.15), bottom = zoom ? Math.max(0, zlo - zspan * 1.2) : (lo < 0 ? lo - span * 0.12 : 0);
  const Y = (v) => pad.t + ((top - v) / (top - bottom)) * (h - pad.t - pad.b);
  const cw = (w - pad.l - pad.r) / cats.length, bw = Math.min(46, (cw * 0.8) / series.length);
  const palette = series.length === 1 ? null : [TEAL, BLUE, ORANGE, NAVY, LIGHT];
  const digits = Math.max(Math.abs(hi), Math.abs(lo)) < 20 ? (chart.unit === "%" ? 1 : 2) : 1;
  const step = niceTicks(zoom ? top - bottom : Math.max(Math.abs(top), Math.abs(bottom)))[1] || 1;
  let g = "";
  for (let v = Math.ceil(bottom / step) * step; v <= top + 1e-9; v += step) {
    g += `<line x1="${pad.l}" y1="${Y(v)}" x2="${w - pad.r}" y2="${Y(v)}" stroke="${Math.abs(v) < 1e-9 ? LIGHT : "#eef0f3"}"/>` +
         `<text x="${pad.l - 6}" y="${Y(v) + 4}" text-anchor="end" font-size="11" fill="${MID}">${+v.toFixed(6)}</text>`;
  }
  cats.forEach((c, i) => {
    const x0 = pad.l + i * cw + (cw - bw * series.length) / 2;
    series.forEach((s, k) => {
      const v = s.values[i], ok = Number.isFinite(v), y0 = Y(Math.max(0, bottom)), y = ok ? Y(v) : y0;
      const colour = palette ? palette[k % 5] : (i === 0 ? TEAL : BLUE), label = ok ? v.toFixed(digits) : "—";
      g += `<rect x="${x0 + k * bw}" y="${Math.min(y, y0)}" width="${bw - 3}" height="${Math.abs(y0 - y)}" fill="${colour}" fill-opacity="0.85"/>` +
           `<text x="${x0 + k * bw + bw / 2 - 1.5}" y="${ok && v < 0 ? y + 13 : y - 4}" text-anchor="middle" font-size="10" fill="${INK}">${label}</text>`;
    });
    g += `<text x="${pad.l + (i + 0.5) * cw}" y="${h - pad.b + 16}" text-anchor="middle" font-size="10.5" fill="${MID}">${esc(c)}</text>`;
  });
  if (chart.line && Number.isFinite(chart.line.value)) {
    const y = Y(chart.line.value);
    g += `<line x1="${pad.l}" y1="${y}" x2="${w - pad.r}" y2="${y}" stroke="${ORANGE}" stroke-width="1.5" stroke-dasharray="5 4"/>`;
  }
  const items = (palette ? series.map((s, k) => `<i style="background:${palette[k % 5]}"></i>${esc(s.name)}`) : []).concat(
    chart.line && Number.isFinite(chart.line.value) ? [`<i style="background:none;border-top:2px dashed ${ORANGE};height:0"></i>${esc(chart.line.label)} : ${chart.line.value.toFixed(2)}`] : []);
  const legend = items.length ? `<div class="legend">${items.join("")}</div>` : "";
  return `<svg viewBox="0 0 ${w} ${h}">${g}</svg>${legend}`;
}

// ------------------------------------------------------------ rendering
function render(out) {
  const t = T[lang];
  state = out.state;
  if (out.reply) say("bot", out.reply);
  $("decision").hidden = false; $("decision").className = "decision " + out.decision;
  $("decision").innerHTML = `<span class="code">${esc(out.decision)}</span>${esc(t.decision[out.decision])}`;
  $("vars").innerHTML = `<caption>${esc(t.varsNote)} ${openApp()}</caption>` + "<tr>" + [t.vars[0], t.vars[1], t.vars[3], t.vars[4]].map((h) => `<th>${esc(h)}</th>`).join("") + "</tr>" +
    out.variables.map((r) => "<tr>" + [r[0], r[1], r[3], r[4]].map((c) => `<td>${esc(c ?? "")}</td>`).join("") + "</tr>").join("");
  clearResults(false);
  if (!out.results) return;  // never leave the figures of an earlier scenario next to new parameters
  const r = out.results, labels = r.kpi_labels || t.kpis[r.kind];
  $("kpis").innerHTML = r.kpis.map((v, i) => `<div class="kpi"><b>${esc(v)}</b><small>${esc(labels[i])}</small></div>`).join("");
  if (r.kind === "tls") {
    $("fig1").innerHTML = `<figcaption>${esc(t.figs.power)}</figcaption>${lineBand(r.series)}`;
    $("fig2").innerHTML = `<figcaption>${esc(t.figs.daily)}</figcaption>${stacked(r.hourly, t.figs.uses)}`;
  } else if (r.kind === "lql_table") {
    $("fig1").innerHTML = `<figcaption>${esc(r.chart.title)}</figcaption>${grouped(r.chart)}`;
    $("fig2").innerHTML = `<figcaption>${esc(t.allCases)}</figcaption>${table(r.table)}`;
  } else {
    $("fig1").innerHTML = `<figcaption>${esc(t.figs.eqd)}</figcaption>${bars(r.bars, t.figs.bars, "Gy")}`;
    $("fig2").innerHTML = `<figcaption>${esc(t.figs.prob)}</figcaption>${bars(r.probs, t.figs.probs, "%", true)}`;
  }
  $("analysis").textContent = r.analysis;
  const q = r.qualification, sw = q.software || {}, u = q.uncertainty || {};
  const doi = sw.doi ? ` · DOI <a href="https://doi.org/${esc(sw.doi)}" target="_blank" rel="noopener">${esc(sw.doi)}</a>` : "";
  const kv = (o) => Object.entries(o || {}).map(([k, v]) => `${esc(k)} = ${esc(v)}`).join(", ");
  $("provenance").innerHTML = `<details><summary>${esc(t.details)}</summary><p><b>${t.prov[0]}:</b> ${esc(sw.name)} ${esc(sw.version || "")} · commit <code>${esc((sw.commit || "").slice(0, 7))}</code>${doi} · ${esc(sw.licence || "")}</p>` +
    (q.verification ? `<p><b>${t.prov[7]}:</b> ${esc(q.verification)}</p>` : "") +
    (q.options && Object.keys(q.options).length ? `<p><b>${t.prov[5]}:</b> ${kv(q.options)}</p>` : "") +
    (q.flags ? `<p><b>${t.prov[6]}:</b> ${kv(q.flags)}</p>` : "") +
    `<p><b>${t.prov[1]}:</b> ${esc(q.nature || q.note || "")}</p>` +
    (u.covered ? `<p><b>${t.prov[2]}:</b> ${esc(u.covered.join(", "))} · <b>${t.prov[3]}:</b> ${esc((u.not_covered || []).join(", "))}</p>` : "") +
    (q.validity_notes || []).map((n) => `<p>– ${esc(n)}</p>`).join("") + "</details>";
  $("files").innerHTML = `<b>${t.prov[4]}:</b> ` + Object.entries(r.files).map(([name, text]) => {
    const url = URL.createObjectURL(new Blob([text], { type: name.endsWith(".json") ? "application/json" : name.endsWith(".ttl") ? "text/turtle" : "text/csv" }));
    blobs.push(url);
    return `<a download="${esc(name)}" href="${url}">${esc(name)}</a>`;
  }).join("") + `<p class="open">${openApp()}</p>`;
  showTab("results");
  // on a phone the results sit below the chat: bring them into view
  if (window.matchMedia("(max-width:900px)").matches) $("decision").scrollIntoView({ behavior: "smooth", block: "start" });
}

function clearResults(all = true) {
  for (const id of ["kpis", "fig1", "fig2", "analysis", "provenance", "files"]) $(id).innerHTML = "";
  blobs.forEach((u) => URL.revokeObjectURL(u)); blobs = [];
  if (all) { $("vars").innerHTML = ""; $("decision").hidden = true; }
}

function applyLanguage() {
  const t = T[lang];
  document.documentElement.lang = lang;
  $("tagline").textContent = t.tagline; $("intro").textContent = t.intro;
  document.querySelectorAll("#code button").forEach((b) => { b.textContent = t.codes[b.dataset.v]; });
  $("input").placeholder = t.placeholder[code]; $("examples-label").textContent = t.examples;
  $("example-btn").textContent = t.exampleBtn; $("reset-btn").textContent = t.resetBtn;
  $("tab-results").textContent = t.tabs.results; $("tab-about").textContent = t.tabs.about;
  $("about").innerHTML = t.about; $("mic").title = t.voice;
  $("footer").innerHTML = `${esc(t.foot)} · <a href="https://github.com/cyrilvoyant/websemantic" target="_blank" rel="noopener">GitHub</a> · <a href="https://doi.org/10.5281/zenodo.23238902" target="_blank" rel="noopener">DOI</a> · <a href="https://pypi.org/project/websemantic/" target="_blank" rel="noopener">PyPI</a> · MIT · app ${APP_VERSION}`;
  $("more-examples").textContent = t.more;
  renderExamples();
  status(pyReady ? t.ready : t.loading);
}

// ------------------------------------------------------------ examples: a few at a time, a new set at each visit
let EXAMPLES = { tls: [], lql: [] }, exampleOffset = 0;
try {  // per-visitor convenience only; the page works without storage
  const visits = Number(localStorage.getItem("ws-visits") || 0) + 1;
  localStorage.setItem("ws-visits", String(visits));
  exampleOffset = visits * 3;
} catch (_) { exampleOffset = Math.floor(Math.random() * 10) * 3; }
fetch("examples.json", { cache: "no-cache" }).then((r) => r.json()).then((e) => { EXAMPLES = e; renderExamples(); }).catch(() => {});
function renderExamples() {
  const pool = EXAMPLES[code] || [], t = T[lang], shown = [];
  for (let k = 0; k < Math.min(3, pool.length); k++) shown.push(pool[(exampleOffset + k) % pool.length]);
  $("examples").innerHTML = "";
  for (const ex of shown) {
    const b = document.createElement("button"), text = ex[lang] || ex.en;
    b.className = ex.kind; b.textContent = text;
    if (t.tags[ex.kind]) { const tag = document.createElement("span"); tag.className = "tag"; tag.textContent = t.tags[ex.kind]; b.appendChild(tag); }
    b.onclick = async () => {  // an example is a complete case: it starts a new conversation
      if (state && $("chat").children.length) await newConversation();
      $("input").value = text; $("input").focus();
    };
    $("examples").appendChild(b);
  }
}

async function newConversation() {
  conversation++; busy = false;  // replies of an earlier conversation are ignored
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
  const mine = conversation, m = code, l = lang;
  busy = true; $("input").value = "";
  say("user", message);
  const wait = say("bot wait", pyReady ? T[l].thinking : T[l].loading);
  try {
    if (!state) state = JSON.parse(await py("api_fresh", m, l));
    let parsed = "";
    if (JSON.parse(await py("api_needs_reading", message))) {  // a pure "yes" needs no language model
      const summary = JSON.parse(await py("api_summary", JSON.stringify(state)));
      try {
        const ctrl = new AbortController(), timer = setTimeout(() => ctrl.abort(), 30000);
        const resp = await fetch(RELAY, { method: "POST", headers: { "Content-Type": "application/json" }, signal: ctrl.signal,
                                          body: JSON.stringify({ code: m, lang: l, message, state: summary }) });
        clearTimeout(timer);
        const data = resp.ok ? await resp.json() : null;
        if (data && data.parsed && typeof data.parsed === "object") parsed = JSON.stringify(data.parsed);
      } catch (_) { parsed = ""; }
    }
    if (mine !== conversation) return;  // the visitor reset or switched meanwhile
    wait.textContent = T[l].computing;
    const out = JSON.parse(await py("api_turn", m, l, JSON.stringify(state), message, parsed));
    if (mine !== conversation) return;
    wait.remove(); render(out);
  } catch (e) {
    if (mine === conversation) { wait.remove(); say("bot", T[l].failed + e); }
  } finally { if (mine === conversation) busy = false; }
}

async function example() {
  if (busy) return;
  conversation++; const mine = conversation, m = code, l = lang;
  busy = true; $("chat").innerHTML = ""; clearResults();
  const wait = say("bot wait", pyReady ? T[l].computing : T[l].loading);
  try { const out = JSON.parse(await py("api_example", m, l)); if (mine === conversation) { wait.remove(); render(out); } }
  catch (e) { if (mine === conversation) { wait.remove(); say("bot", T[l].failed + e); } }
  finally { if (mine === conversation) busy = false; }
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
      rec.onresult = (e) => { $("input").value = e.results[0][0].transcript; $("input").focus(); };  // read it, then send
    }
    if (on) { rec.stop(); return; }
    rec.lang = lang === "fr" ? "fr-FR" : "en-GB"; rec.start();
  };
}

// ------------------------------------------------------------ wiring
$("form").onsubmit = (e) => { e.preventDefault(); send($("input").value); };
$("input").onkeydown = (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send($("input").value); } };
$("example-btn").onclick = example;
$("more-examples").onclick = () => { exampleOffset += 3; renderExamples(); };
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
