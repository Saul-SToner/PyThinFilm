# PyThinFilm Nature-style figure contract

## Core conclusions

- Main-result figures show the device response that directly supports the case claim.
- Validation figures show an external reference on the same axis and a signed residual below it.
- Robustness figures show intervals, thresholds or Pareto candidates rather than a single optimum.
- Approximation and placeholder outputs are visually and evidentially separated from external validation.

## Archetypes

| Figure family | Archetype | Hero evidence | Supporting evidence |
|---|---|---|---|
| R/T/A spectrum | quantitative hero | case-specific R, T or A curve | target wavelength and one feature |
| External validation | asymmetric quantitative | theory/reference spectrum | signed residual and maximum error |
| Parameter scan | asymmetric mixed-modality | response or objective landscape | constraint decomposition and robustness |
| Sensitivity | quantitative grid | stable interval / feature shift | MAE or diagnostic quantities |
| Material library | asymmetric quantitative | n/k dispersion | wavelength coverage |
| Roadmap / architecture | diagram profile | workflow hierarchy | status labels |

## Static export contract

- Backend: Python/Matplotlib only.
- Maximum journal width: 7.2 in (approximately 183 mm).
- White background; top and right spines removed; grids omitted unless numerically necessary.
- Final text is 7–9 pt; panel labels are bold lowercase letters.
- SVG is the editable primary output; PDF and 300 dpi PNG are generated beside it.
- SVG text remains editable (`svg.fonttype = none`); PDF uses TrueType (`pdf.fonttype = 42`).
- Every quantitative output retains its CSV/JSON source and figure-audit record.

## Reviewer-risk controls

- R/T/A bounds and energy conservation are audited automatically.
- COMSOL claims require a real, hash-recorded source CSV.
- Missing results remain NA and are never rendered as physical zero.
- Error and uncertainty definitions must be explicit.
- Placeholder and approximation figures cannot enter the report body.
