// WebSemantic language-model relay (Cloudflare Worker, free plan).
// Keeps the Mistral key secret (secret MISTRAL_API_KEY). The prompt is built here from the published contract of one
// code and the answer is reduced to the expected fields, which limits misuse. The origin check is not an
// authentication: any HTTP client can send the allowed Origin header. Abuse is bounded by a per-visitor limit
// (Cloudflare rate-limiting binding LIMITER when configured; otherwise a best-effort in-memory count per instance,
// not a guarantee) and, globally, by the Mistral account's monthly allowance. Non-billing is an account setting
// (free plan, pay-as-you-go not activated, checked by the owner on 10 October 2026), not something this code enforces.

const ORIGINS = ["https://cyrilvoyant-websemantic.static.hf.space", "https://huggingface.co"];
const CONTEXT = "https://huggingface.co/spaces/CyrilVoyant/websemantic/resolve/main/llm/";
const MAX_BODY = 24000;      // bytes accepted from the page
const MAX_MESSAGE = 800;     // characters of the visitor's message
const PER_MINUTE = 8;        // fallback per-IP limit when no LIMITER binding exists
const TIMEOUT_MS = 25000;    // language-model call
const ORIGINS_OK = new Set(["provided", "convention", "default"]);

const SYSTEM = `You translate a user's request into the variables of one scientific code. You never compute, never choose
a number, never add an assumption. The contract is the only authority.
- A value is either stated by the user (origin "provided", evidence = the exact words of the user, copied character
  for character, containing the number), a declared qualitative convention (origin "convention": put the name of the
  declared level whose expressions mean the same as the user's words in "level", and quote the user's words as
  evidence), or a declared default the user explicitly asks for (origin "default").
- Copy every evidence character for character from the NEW MESSAGE, in the user's language; never translate it
  into the language of the declared expressions and never rephrase it.
- Use only the exact parameter names of the list. Never accept anything for the user.
- When a parameter lists its categories, its value is one of them, spelled exactly; a word found in another
  parameter's categories belongs to that parameter. Give each parameter at most one value.
- If the request is outside the supported tasks (real measured data, certification, a decision for a named patient),
  set task to "unsupported". A request in the code's domain with a vague or missing value is supported: set the
  supported task, return the values that are stated and ask about the rest in questions.
  A remark or a question about the conversation that asks for no calculation is not "unsupported" either:
  set the supported task and return no values. Fictitious resumptions after an interruption, comparisons of
  schedules, several organs at risk and maximum-dose questions are simulations: they are supported unless a named
  patient or a treatment decision is involved.
Reply with one JSON object only:
{"task": "<one supported task or unsupported>",
 "values": [{"field": "<exact parameter name>", "value": <number or category>, "unit": "<unit or null>",
             "origin": "provided|convention|default", "level": "<declared level, conventions only>",
             "evidence": "<exact quote>"}],
 "questions": ["<at most two short questions about what is missing or ambiguous>"],
 "message": "<two friendly sentences in the user's language; never give a numerical result, the code computes it>"}
Return in values only what the NEW message states or qualifies.`;

const contexts = {};
const hits = new Map();

function headers(origin) {
  return { "Access-Control-Allow-Origin": origin, "Access-Control-Allow-Methods": "POST, OPTIONS",
           "Access-Control-Allow-Headers": "Content-Type", "Access-Control-Max-Age": "600", "Vary": "Origin" };
}

function json(body, status, origin) {
  return new Response(JSON.stringify(body), { status, headers: { ...headers(origin), "Content-Type": "application/json" } });
}

function limitedInMemory(ip) {
  const now = Date.now(), recent = (hits.get(ip) || []).filter((t) => now - t < 60000);
  recent.push(now); hits.set(ip, recent);
  if (hits.size > 5000) hits.clear();
  return recent.length > PER_MINUTE;
}

const str = (v, n) => (typeof v === "string" ? v.slice(0, n) : "");

// Keep only the expected fields, with bounded sizes; the page checks everything again.
export function sanitize(parsed) {
  const p = parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : {};
  const values = (Array.isArray(p.values) ? p.values : []).slice(0, 40)
    .filter((v) => v && typeof v === "object")
    .map((v) => ({
      field: str(v.field, 80),
      value: ["number", "boolean"].includes(typeof v.value) ? v.value : (typeof v.value === "string" ? v.value.slice(0, 120) : null),
      unit: typeof v.unit === "string" ? v.unit.slice(0, 40) : null,
      origin: ORIGINS_OK.has(v.origin) ? v.origin : "invalid",
      level: str(v.level, 60),
      evidence: str(v.evidence, 300),
    }));
  const questions = (Array.isArray(p.questions) ? p.questions : []).filter((q) => typeof q === "string").slice(0, 2)
    .map((q) => q.slice(0, 300));
  return { task: str(p.task, 200), values, questions, message: str(p.message, 600) };
}

async function fetchWithTimeout(url, init, ms) {
  const ctrl = new AbortController(), timer = setTimeout(() => ctrl.abort(), ms);
  try { return await fetch(url, { ...init, signal: ctrl.signal }); } finally { clearTimeout(timer); }
}

export default {
  async fetch(request, env) {
    const origin = request.headers.get("Origin") || "";
    const allowed = ORIGINS.includes(origin);
    const echo = allowed ? origin : ORIGINS[0];
    if (request.method === "OPTIONS") return new Response(null, { status: allowed ? 204 : 403, headers: headers(echo) });
    if (request.method !== "POST" || !allowed) return json({ error: "forbidden" }, 403, echo);

    const ip = request.headers.get("CF-Connecting-IP") || "unknown";
    if (env.LIMITER) {
      const { success } = await env.LIMITER.limit({ key: ip });
      if (!success) return json({ error: "busy" }, 429, echo);
    } else if (limitedInMemory(ip)) {
      return json({ error: "busy" }, 429, echo);
    }

    if (Number(request.headers.get("Content-Length") || 0) > MAX_BODY) return json({ error: "too large" }, 413, echo);
    const text = await request.text();
    if (text.length > MAX_BODY) return json({ error: "too large" }, 413, echo);
    let body;
    try { body = JSON.parse(text); } catch { return json({ error: "bad request" }, 400, echo); }
    const { code, lang, message, state } = body || {};
    if (!["tls", "lql"].includes(code) || !["en", "fr"].includes(lang) || typeof message !== "string"
        || !message.trim() || message.length > MAX_MESSAGE || (state !== undefined && (typeof state !== "object" || Array.isArray(state))))
      return json({ error: "bad request" }, 400, echo);

    try {
      if (!contexts[code]) {
        const r = await fetchWithTimeout(CONTEXT + code + ".json", {}, 10000);
        if (!r.ok) return json({ error: "context" }, 502, echo);
        contexts[code] = await r.json();
      }
      const c = contexts[code];
      const prompt = `SUPPORTED TASKS: ${JSON.stringify(c.tasks)}\nCONTRACT:\n${c.contract}\n` +
        `PARAMETERS:\n${JSON.stringify(c.params)}\nCURRENT SCENARIO:\n${JSON.stringify(state || {})}\n` +
        `REPLY LANGUAGE for message and questions: ${lang === "fr" ? "French" : "English"}\nNEW MESSAGE:\n${message}`;
      const r = await fetchWithTimeout("https://api.mistral.ai/v1/chat/completions", {
        method: "POST",
        headers: { "Content-Type": "application/json", "Authorization": "Bearer " + env.MISTRAL_API_KEY },
        body: JSON.stringify({ model: env.MISTRAL_MODEL || "codestral-latest", temperature: 0, max_tokens: 700,
                               response_format: { type: "json_object" },
                               messages: [{ role: "system", content: SYSTEM }, { role: "user", content: prompt }] }),
      }, TIMEOUT_MS);
      if (!r.ok) return json({ error: r.status === 429 ? "busy" : "llm" }, 503, echo);
      const data = await r.json();
      return json({ parsed: sanitize(JSON.parse(data.choices[0].message.content)), model: str(data.model, 80) }, 200, echo);
    } catch {
      return json({ error: "llm" }, 503, echo);  // timeout, network error or malformed answer
    }
  },
};
