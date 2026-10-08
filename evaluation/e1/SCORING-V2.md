# First-turn scoring, version 2

`score_e1_v2.py` leaves the original score files and collector unchanged. It reads
the descriptors frozen beside the response reserve and records their hashes,
the scorer hashes and each response hash. Run with a reserve and a separate output
directory. Results remain private.

The main screen requires a recognised decision, structurally usable JSON, no
duplicate fields, an admissible decision and no unsupported or silently accepted
assignments detected by the evidence checks. For execution requests, all expected
values must also have their canonical units and numeric types. A qualifier case
must satisfy its published convention or clarification policy. Correct
clarification/refusal does not require a calculation.

This is an **interpretation screen**, not end-to-end task success. It does not
prove autonomous execution, the truth of retrieved sources, or complete schema
and backend validity. Different unit encodings are marked unverified rather than
assumed numerically equivalent. Scopes without sufficient references are unscored,
including the previous multi-course and multi-scenario gaps. Invalid formats and
provider failures remain in the response table; availability uses the separate
attempt log, including attempts without response files.

First-turn hashes identify repeated requests. Analysis must distinguish unique
requests, scenario groups, repetitions, conditions, source versions and provider
modalities. Do not treat repeated requests or outputs as independent samples.
Partial collections support descriptive reports; they do not support a complete
factorial effect estimate.
