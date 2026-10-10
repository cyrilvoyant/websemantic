// WebSemantic language-model relay (Cloudflare Worker, free plan).
// Keeps the Mistral key secret (environment secret MISTRAL_API_KEY) and accepts only WebSemantic requests: the prompt
// is built here from the published contract of one code, so the key cannot be used as a general-purpose chatbot.

const ORIGINS = ["https://cyrilvoyant-websemantic.static.hf.space", "https://huggingface.co"];
const CONTEXT = "https://huggingface.co/spaces/CyrilVoyant/websemantic/resolve/main/llm/";
const PER_MINUTE = 8; // per visitor IP, best effort (per Worker instance)

const SYSTEM = `You help a user prepare a scenario for one scientific code. The contract is the only authority.
- Never invent a value. A value is either stated by the user (origin "provided", evidence = the exact words of the
  user, copied character for character), a declared qualitative convention (origin "convention": put the name of
  the declared level whose expressions mean the same as the user's words in "level", and quote the user's vague
  words as evidence), or a declared default (origin "default").
- Never accept anything for the user. Use the canonical units of the parameter list.
- If the request is outside the supported tasks (real measured data, certification, a decision for a named patient),
  set task to "unsupported".
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

function reply(body, status, origin) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": origin,
               "Access-Control-Allow-Methods": "POST, OPTIONS", "Access-Control-Allow-Headers": "Content-Type",
               "Vary": "Origin" },
  });
}

function limited(ip) {
  const now = Date.now(), recent = (hits.get(ip) || []).filter((t) => now - t < 60000);
  recent.push(now); hits.set(ip, recent);
  return recent.length > PER_MINUTE;
}

export default {
  async fetch(request, env) {
    const origin = request.headers.get("Origin") || "";
    const allowed = ORIGINS.includes(origin) ? origin : ORIGINS[0];
    if (request.method === "OPTIONS") return reply({}, 204, allowed);
    if (request.method !== "POST" || !ORIGINS.includes(origin)) return reply({ error: "forbidden" }, 403, allowed);
    if (limited(request.headers.get("CF-Connecting-IP") || "?")) return reply({ error: "busy" }, 429, allowed);

    let body;
    try { body = await request.json(); } catch { return reply({ error: "bad request" }, 400, allowed); }
    const { code, lang, message, state } = body || {};
    if (!["tls", "lql"].includes(code) || typeof message !== "string" || !message.trim() || message.length > 800
        || JSON.stringify(state || {}).length > 20000) return reply({ error: "bad request" }, 400, allowed);

    if (!contexts[code]) {
      const r = await fetch(CONTEXT + code + ".json");
      if (!r.ok) return reply({ error: "context" }, 502, allowed);
      contexts[code] = await r.json();
    }
    const c = contexts[code];
    const prompt = `SUPPORTED TASKS: ${JSON.stringify(c.tasks)}\nCONTRACT:\n${c.contract}\n` +
      `PARAMETERS:\n${JSON.stringify(c.params)}\nCURRENT SCENARIO:\n${JSON.stringify(state || {})}\n` +
      `REPLY LANGUAGE for message and questions: ${lang === "fr" ? "French" : "English"}\nNEW MESSAGE:\n${message}`;

    const r = await fetch("https://api.mistral.ai/v1/chat/completions", {
      method: "POST",
      headers: { "Content-Type": "application/json", "Authorization": "Bearer " + env.MISTRAL_API_KEY },
      body: JSON.stringify({ model: env.MISTRAL_MODEL || "mistral-small-latest", temperature: 0,
                             response_format: { type: "json_object" },
                             messages: [{ role: "system", content: SYSTEM }, { role: "user", content: prompt }] }),
    });
    if (!r.ok) return reply({ error: r.status === 429 ? "busy" : "llm" }, 503, allowed);
    try {
      const data = await r.json();
      return reply({ parsed: JSON.parse(data.choices[0].message.content) }, 200, allowed);
    } catch {
      return reply({ error: "llm" }, 502, allowed);
    }
  },
};
