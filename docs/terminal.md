# Terminal dialogue

Open `WebSemantic.cmd` and choose TLS. Describe the study, refine the choices, then accept the assumptions. The
calculation starts when the checks are satisfied; an explicit change runs it again. The result folder is shown after
each calculation. The dialogue works in English or French.

Examples:

- "Propose the missing parameters."
- "Show the table: default, retained value, unit and origin."
- "Explain the formulas used."
- "Suggest five questions to refine the study."
- "I accept the assumptions, run the calculation."

A blocking question needs an answer about the choice concerned. The seed stays 42 unless explicitly requested; it is
recorded in the results.

## Optional shortcuts

| Command | Function |
|---|---|
| `/help` or `/a` | Help |
| `/s` | Five suggestions |
| `/show` | Summary |
| `/d` | Current table |
| `/details-all` | All parameters |
| `/e NAME` | Definition and unit |
| `/formulas` | Formulas and coefficients |
| `/p` | Propose the missing defaults |
| `/v` | Accept the assumptions and compute if admissible |
| `/web QUESTION` | Documentary search |
| `/set GROUP.NAME VALUE` | Change a value in the canonical unit (JSON value) |
| `/r` | Compute the current configuration |
| `/q` | Quit |

The long forms are `/suggest`, `/details`, `/profile`, `/accept`, `/run`, `/quit`. The prefix `\` is also accepted.

## Two scenarios

Name "scenario 1" and "scenario 2", the common values and their differences. "Same length" reuses a length already
defined. Accept the assumptions of both cases before the calculation.

Start, duration, time step, number of realisations and seed are common. The merged CSV files carry `scenario`; the
subfolders keep the individual calculations. The differences concern the complete configurations. Restart the
conversation to return to a single study.
