# v0.6.0 — Independent channel stretch

Adds an optional reviewed final stretch for linear RGB or three registered mono FITS masters. R/G/B targets and amounts are independent, with individual channel and recombined previews. Shared starting target 0.23; sources are preserved and the full-resolution candidate requires explicit acceptance. Controls are saved in workflow presets; accepted reports record settings and selected master paths. Use this instead of an additional automatic stretch. Equal targets change relative emission balance; no alignment or physical color calibration is performed.

Validated October 22, 2026: 51 unit/Qt tests pass, including source preservation, targets, amount blending, cancellation, fixed preview/full-resolution plans, FITS loading, explicit acceptance and replay. Windows installer lifecycle checks are recorded separately.

# v0.5.0 — Optional Lighthouse finishing handoff

- Discover the separately installed Lighthouse for Siril script, with a custom-path Browse option.
- Prepare Lighthouse handoff saves accepted pixels as a new FITS and opens that copy in Siril, then closes CCDASTRO. Select Lighthouse from Siril's Scripts menu to start editing.
- This is an assisted handoff, not automatic launch or return. Nested automatic launches stalled in isolated Siril 1.4.4 checks and are not enabled.
- Requires an unchanged saved FITS source; accept/discard candidates first. Existing destination files are refused. Source disk files and personal data remain preserved.
- Save Lighthouse output separately, then reopen CCDASTRO to continue. No shared presets or bundled/imported Lighthouse code.
- Credits: Yannick Dutertre (Cuiv), Siril port; Neven Krčmarek, original Lighthouse.

Verification for v0.5.0: 42 automated tests and isolated installer lifecycle checks passed. An isolated Siril 1.4.4 check detected the installed Lighthouse script, opened a 40×32 RGB handoff copy, and confirmed the source file bytes were unchanged. Lighthouse editing itself remains a separately launched user action.
