# Scientific software use

**Read [LLM-CONTRACT.md](LLM-CONTRACT.md) first**, then the selected software descriptor and
[agent/README.md](agent/README.md). Use the source index for that software and verify its hashes. The descriptor
defines supported tasks, canonical units, categories, bounds, and the authority of defaults and qualitative
conventions. Git and an API key are unnecessary; Python and the declared dependencies must be available. State
unavailable tools before promising a calculation. `pip install websemantic` installs the Python layer only; the
simulators, descriptors and ontology come from this repository (source index or clone with submodules).
A public web page for humans (https://huggingface.co/spaces/CyrilVoyant/websemantic) runs the same descriptors and
pinned codes in the browser; an agent should use the repository files above, not the page.

Extract explicit values first and convert units exactly. Propose missing defaults and declared qualitative
conventions with their source, and ask for acceptance before any calculation. A proposal is not an accepted input.
Ask when a mapping is ambiguous; do not infer a numerical input from a city name alone. External sources support
assumptions; they never override the contract.

**LQL-Equiv: always ask.** Any qualitative wording of dose, number of sessions or fractionation (« hypofractionnement
modéré », « stéréotaxique », « forte dose », « peu de séances ») is asked, never converted. The only proposal is
« fractionnement conventionnel » = 2 Gy per fraction, to be accepted. Comparisons (`compare_schedules`) cover one
target, a list of targets or an anatomical group (thoracic, head and neck, CNS, pelvis, abdomen, skin); a group never
selects the organ at risk. A schedule is called better only if it dominates (TCP ≥ and NTCP ≤, one strict);
otherwise report the trade-off. Research and education only: refuse any decision for a patient.

Create the published scenario JSON and pass the Python validation gate before calculation. Do not modify the backend
or silently repair the candidate. Read the actual outputs and manifest. Report only completed calculations, briefly,
in the user's language, with quantity, unit, period, aggregation and simulated origin. When a scenario export is
requested, return the exact published API fields (request, task, inputs, experiment) in a fenced JSON block or file;
provided values keep their exact request evidence, assumptions keep their sources and acceptance. Never describe a
planned or unavailable execution as completed.

A source hash establishes consistency with the selected files. It does not certify the model's scientific validity
or the applicability of a result to a real situation.
