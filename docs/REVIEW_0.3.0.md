# Review fixes in 0.3.0

## Recorder and event loop

Live budget and plan attributes stay available to dashboards/templates but are excluded from Recorder (`_unrecorded_attributes` is a class-level frozenset). Identical entity snapshots are not written. Power sensors publish at most once per second; other changing detail at most once per five seconds, on the next manager update. Status/availability transitions publish immediately. This changes presentation frequency, not the internal control frequency. Recorder still records meaningful numeric/state changes; existing database records are not removed.

Requests arriving during a running control cycle set a coalescing rerun flag. The manager evaluates fresh inputs immediately after the current cycle, even after a cycle error. Unloading stops scheduling and waits for the active cycle before saving state.

All actuator service calls have a ten-second timeout. Failures start a 30-second retry cooldown; their pending reservation remains allocated because a timed-out command might have reached the hardware. Commands remain ordered: parallel actuation was optional and is deliberately not enabled, so the priority budget is not spent twice. A hardware/cloud action already submitted cannot necessarily be cancelled by a timeout.

Every device type checks explicitly configured actuator states before controlling them. Missing, unknown or unavailable switches/numbers/selects block commands. An existing, never-pressed button with `unknown` state is valid; a missing/unavailable button is not. Unavailable actors also pause program observation, avoiding false completion caused by lost state.

## Status and compatibility

Status sensors use HA's ENUM device class and fixed English state codes with German/English translations. Entity IDs and unique IDs are unchanged. **Templates and automations that compare raw status values need the following migration.** The `legacy_status` attribute retains the previous code, and the diagnostic `phase` sensor retains the existing household state-machine values. Existing German attribute keys (`grund`, `aktuell_w`, etc.) stay available.

| Previous state | New state |
| --- | --- |
| init | initializing |
| bereit | ready |
| erkannt | detected |
| wartet | waiting |
| laeuft | running |
| fertig | finished |
| aus | off |
| manuell | manual |
| beobachten | observing |
| inaktiv | inactive |
| sperrzeit | locked |
| max_erreicht | limit_reached |
| nicht_verbunden | disconnected |
| voll | full |
| laedt_sofort | charging_now |
| laedt_pflicht | charging_required |
| laedt_pv | charging_pv |
| boost | boost |

Additional states: `actuator_unavailable`, `actuator_error`. New `status_code` is the stable machine-readable status; new `reason` localizes diagnostic explanations to the HA server language (German or English). Legacy `grund` is retained in German. Client-specific ENUM labels use the user's HA language. The custom card retains its existing German interface labels; it understands the new and old status codes. Card nodes are patched in place, with delegated listeners and preserved input/dropdown focus and scroll position.

## Configuration, diagnostics and CI

- Complete matching `strings.json`, German and English translation keys, including dryer and data descriptions. A dedicated parity/type check supplements hassfest (hassfest alone is not a complete translation coverage check).
- Battery forecast strategy uses the end of today's last strictly positive forecast hour, never a fixed 21:00 cut-off. No remaining positive forecast means no future production window.
- Explicit per-device entity field lists and a cached fast-input set replace domain-prefix guessing. All values in those fields are watched regardless of domain; the supported form domains are unchanged.
- Priority-service validation raises translated `ServiceValidationError`; service metadata included.
- Config-entry diagnostics include parameters, last decisions, per-device budget, up to 240 recent budget samples and forecast health. Device names/IDs, configured entity IDs, raw config, error text and free-form reason text are omitted.
- One idempotent release workflow reacts to manifest changes, `v*` tags or manual dispatch. It verifies tag/version consistency and changelog coverage and publishes only after all checks pass. Old per-version workflows removed; the separate existing release-note synchronization job is retained.
- Manifest is the only version source; HA's integration loader supplies runtime/device/card versions.
- Required checks: hassfest, HACS metadata validation (external brands-catalog listing is excluded), Ruff, isolated regression tests, actual HA manager/config-flow/platform/service tests, translation parity and DOM-update tests. Local tests do not exercise real hardware/cloud devices.
- Minimum HA: 2025.7.0; this version and HA 2026.2.3 are exercised separately (20 actual HA tests per version, 96 isolated regression tests and 2 DOM tests).
- Duplicate battery-budget calculation consolidated. Ruff imports/zip checks addressed.

Update through HACS and restart Home Assistant. Reload dashboard browser cache if necessary. Review raw status comparisons before enabling automations using those states.
