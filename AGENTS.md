## PV-Vergleich feste Skala und Tageswechsel (0.3.70)
- Vergleichsgrafik nutzt **fixe Gesamt-PV-Peakleistung**, niemals das historische Maximum. `pv_vergleich.gesamt_peak_kwp` ist der explizit konfigurierbare Gesamtwert inkl. nicht modellierter/Balkon-PV, sonst die Summe der gezeichneten `solar_surfaces`. Eine fehlende Gesamtleistung nicht heimlich mit Messwerten auffüllen.
- Die Skala ist installierte kWp × 1h (kWh) plus 10 % Textreserve; mit halben kWh aufrunden. `PVComparison`-Stundenwerte bleiben Wh. Prozentwerte befinden sich innerhalb ihrer Stunde direkt über dem höchsten Ist-/Prognosebalken, nicht in einer separaten Zeile.
- Y-Achse/Gitternetz beziehen sich ausschließlich auf die tatsächliche Balkenfläche (Datum und Stundenlabel außerhalb). Jede lokale Tagesgrenze wird durch eine zusammenhängende kontrastreiche Linie über Datum, Plot und Zeitleiste markiert; scrollt mit den Daten, während die Y-Achse feststeht.
- Die bestehenden UI-Tests mit Peak, Nachtfilter, Tageslinien und Fehlwerten behalten. Weder Prognose, Regelung noch HA-Kartenregistrierung ändern.

## ⚠️ VERBINDLICH: Laden der Dashboard-Karte (Stand 11.11.2026) – nicht zurückbauen

An den smartify-Repos wird parallel gearbeitet. Diese Regel gilt identisch in `smartify-energy-pro`, `smartify-flow-card`, `smartify-row-card` und `my-weather` und darf von keinem Agenten und keiner Person ohne ausdrückliche Freigabe des Repository-Eigentümers geändert oder „wiederhergestellt“ werden – auch nicht beim Mergen/Rebasen älterer Branches.

1. **Die Karte wird ausschließlich als Lovelace-Ressource geladen** (Storage-Modus, `type: module`, automatisch angelegt/aktualisiert, eigene Duplikate entfernt, Ressourcen-Storage vorher laden).
2. **Kein `add_extra_js_url` (und kein `extra_module_url`) als regulärer Ladeweg.** Grund: Extra-JS steht im `<head>` der index.html und läuft im Wettlauf mit dem Scoped-Custom-Element-Registry-Polyfill des HA-Frontends. Definiert die Karte ihre Elemente vor dem Polyfill, liefert `customElements.get()` danach nichts mehr und `whenDefined()` löst nie auf → dauerhaft **„Konfigurationsfehler / Custom element doesn't exist“** bis zum Reload. Auf HA 2026.10.4 nachgestellt. Auch eine zusätzliche Ressource mit identischer URL behebt das nicht (Modul wird nicht erneut ausgeführt). Zulässig ist Extra-JS nur als letzter Ersatz, wenn nachweislich keine Storage-Ressource angelegt werden kann (Lovelace-YAML-Modus), mit Log-Hinweis auf den manuellen Eintrag.
3. **Ressourcen-URL immer versioniert** (`?v=<Version>` bzw. Version+Hash). Wird die Datei mit Cache-Headern ausgeliefert, braucht jede veröffentlichte JS-Änderung eine neue Version.
4. **Registrierung nur im Event-Loop** (`@callback`/`async def`), bei spät startendem Lovelace wiederholen; fremde Ressourcen nie verändern oder löschen.
5. `customElements.define` bleibt durch `customElements.get` abgesichert; der `hass`-Setter der Karte darf keine Exception werfen (HA ersetzt die Karte sonst durch „Konfigurationsfehler“).
6. Vor jedem Push/Merge prüfen: `grep -rn "add_extra_js_url\|extra_module_url" custom_components/` zeigt höchstens den dokumentierten YAML-Fallback. Die zugehörigen Tests dürfen nicht entfernt oder abgeschwächt werden: `tests/ha/test_card_resource.py`.

## PV-Flächen-Editor (0.3.64)
- PV-Flächen werden NUR noch über die Karte `custom:smartify-energy-pv-card` (in `smartify-energy-plan-card.js`, gleiche Lovelace-Ressource – keinen zweiten Ladeweg einführen) gepflegt, nicht im Optionsdialog. Speicherung in `options["solar_surfaces"]` (`pv_layout.normalize_surfaces`), WebSocket `smartify_energy/pv_layout`, `/pv_layout/save` (admin), `/pv_map/reload` (admin) in `pv_websocket.py`.
- Ausrichtung wird im Backend aus der Geometrie berechnet (Fläche: Außennormale der Traufkante `edge`, `flip` dreht; Linie: Normale, Standard die südlichere). Vom Client geschickte Azimutwerte bei gezeichneten Flächen ignorieren. Die JS-Vorschau (`pvSurfaceAzimuth`) muss dieselben Ergebnisse liefern – Tests `tests/test_pv_layout.py` und `tests/ui/pv-card.test.cjs` mit denselben Fällen.
- Luftbild (basemap.at) nur auf ausdrückliche Anforderung bzw. einmalig beim ersten Öffnen laden, in `.storage/smartify_energy_map/<entry_id>` speichern; `pv_layout`-Abfrage kontaktiert den Kachelserver nie. Fehlgeschlagenes Nachladen behält das alte Bild. Attribution „basemap.at (CC BY 4.0)“ anzeigen.
- Kacheln mit `await resp.read()` vollständig lesen und nur vollständige JPEGs (FFD8…FFD9) speichern. NICHT `resp.content.read(n)`: liefert nur den gepufferten Teil → abgeschnittene Kacheln, graue Flecken (0.3.64–0.3.66). Höchstens `TILE_PARALLEL` gleichzeitige Abrufe (Rücksicht auf den öffentlichen Server). Test: `test_truncated_tile_is_rejected_and_old_photo_kept`.
- Karte zeichnet in LOKALEN Pixelkoordinaten (`_lx/_ly/_lon/_lat`, Ursprung = linke obere Luftbildkachel). Keine absoluten Web-Mercator-Pixel ins SVG schreiben: SVG rechnet float32, bei Zoom 19 (~7·10⁷ px) verschwinden die Kacheln (0.3.64). UI-Test prüft |Koordinaten| < 10⁶.
- Bifazial (0.3.69): `bifacial`/`bifaciality` (0,5–1,0, Standard 0,7) je Fläche; `model_surfaces` gibt `bifaciality` nur bei bifazialen Flächen weiter, `solar_model.pv_hours` addiert Rückseite = `_clear_sky_poa(180−tilt, azimuth+180)` × Faktor. Monofaziale Flächen exakt unverändert (Test `BifacialTests.test_monofacial_unchanged`). Kalibrierung/Clipping-Erkennung nicht angepasst.
- Editor-Layout: Container-Query ab 860 px → Liste rechts (`.layout > .main | .side`), Einträge klappbar (`_open`). Formularfelder existieren nur im aufgeklappten Zustand.
- Alte Felder `solar_1_*`–`solar_4_*`: beim Lesen migrieren (`surfaces_from_config`), beim Speichern spiegeln (`legacy_mirror`, Downgrade). Nicht wieder in den Optionsdialog aufnehmen. Höchstens vier Flächen (`solar_model` nutzt vier). Tests: `tests/ha/test_pv_editor.py`.

## PV-Prognose heute = ganzer Tag (0.3.63)
- `forecast_today` (Sensor „PV-Prognose heute“, Flow-Card „Prog.“) ist die Prognose für den GANZEN lokalen Tag: `PVComparison.day_forecast_wh` – aktuelle Prognosestunden plus eingefrorene Ursprungsprognose für vergangene Stunden, die in `forecast.hours` fehlen (berechneter Modus hat nur ab laufender Stunde Wolkendaten). Nicht wieder auf reine Summe von `forecast.hours` zurückbauen. Live-Werte haben Vorrang, nichts doppelt zählen, keine Werte erfinden. Test: `tests/test_pv_comparison.py` (`DayForecastTests`).

## PV-Vergleich 14 Tage (0.3.61)
- Die bestehende `PVComparison`-Historie und der bestehende Store sind die einzige Quelle für den Ist-/Prognosevergleich. Vorhersagen ausschließlich für Zukunftsstunden einfrieren; fehlende Leistungsmessungen nie als 0 Wh ergänzen. Für Vergleich weiterhin >= 95 % Abdeckung.
- Die 14-tägige Verlaufsgrafik im `sensor:plan`-Attribut `pv_vergleich` enthält zusätzlich astronomische Sonnenaufgangs-/Sonnenuntergangszeiten pro lokalem Datum aus Home Assistant. UI zeigt die Stunde, wenn sie Tageslicht oder den Puffer von einer Stunde schneidet; andere Nachtstunden nur visuell entfernen.
- Lokale Datumsgruppen mit senkrechten Trennlinien, pro Stunde und pro Tag signierte Prozentabweichung (Ist/Prognose−1)×100. Fehlende Messwerte und 0-Wh-Prognosen ergeben keine Prozentabweichung. Teilweise Tagesauswertungen als „bisher“ markieren.
- Keine Änderungen an `_plan`, `ForecastProvider`, Kalibrierung, Gerätebudget oder 15-Minuten-Netzlaststeuerung.
- Regressionen: `tests/test_pv_comparison.py`, `tests/ui/card.test.cjs`; 14 Tage, Messlücken, Neustart, Nachtfilter, Datumstrennung, mobile Bedienbarkeit. `pv_vergleich` für HA Recorder als nicht aufzuzeichnendes Attribut kennzeichnen.

## PV-Plan Gitternetz und Y-Achse (0.3.60)
- PV-Plan zeigt Momentan-/Stundenleistung in **kW**, die neue ausklappbare historische Vergleichsgrafik Energie je Stunde in **kWh**. Einheiten nicht vertauschen.
- Links fixierte Werteachse (Nullpunkt und vier Niveaus), vier dezente horizontale Gitternetzlinien, Balkenhöhen einheitlich auf die beschriftete Obergrenze normieren. Beim 48h-Horizont bleibt die Achse beim horizontalen Scrollen fest stehen.
- Keine Änderungen am PV-Plan, Gerätebalken, Prognoseberechnung oder Budget. Tests/ui/card.test.cjs deckt beide Darstellungen ab.

## PV-Plan tatsächliche Energie vs. Prognose (unreleased)
- Kollabierbare, horizontal scrollbar 48h zurückblickende Anzeige direkt nach PV-Plan (initial rechts beim neuesten Wert): echte PV-Erzeugungsleistung aus bestehendem optionalem Solar-PV-Power-Entity, niemals Netzsaldo, Batterie oder Hauslast. Unterstützt externe und berechnete Prognose.
- Prognose pro UTC-Stunde einmalig vor Stundenbeginn einfrieren; niemals rückwirkend mit aktualisierter Prognose überschreiben. Daten sparsam persistent mit bisherigem Store, ältere Daten begrenzen.
- Istenergie nur über gültige Leistungsmessung integrieren (Wh). Große Messlücken nicht interpolieren und fehlende Werte nicht als Null darstellen. Stundenvergleich nur bei mindestens 95 % Datenabdeckung. DST und HA-Neustart absichern.
- UI standardmäßig zugeklappt, klappt unabhängig vom PV-Plan auf, bleibt beim HA-Rerender stabil; Layout auch auf iPhone/iPad. Regressionen tests/test_pv_comparison.py und tests/ui/card.test.cjs.

## Quellenanzeige und verlängerter PV-Plan (unreleased)
- PV-Prognose-Kachel UND PV-Plan zeigen dieselbe tatsächliche Quelle; bei zusammengeführten externen Quellen kein fälschliches Solcast-Label. Quelle als Attribut bereitstellen.
- Stundenmodell nimmt bis 48h My-Weather-Wolkendaten, alte 8h-Entity bleibt gültig. Nur echte Zeitstempel und Zahlen 0–100 %, keine fehlenden Stunden auffüllen.
- Die neuen Änderungen auf dem offenen Quellenanzeige-Branch erhalten, kein Merge/Release ohne abgeschlossene CI.

## PV-Kalibrierung (optional, in Vorbereitung)
- Nur berechneter PV-Modus mit explizitem Opt-in. Sensor muss echte Erzeugungsleistung aller modellierten Flächen messen; niemals Netzsaldo, Akkuleistung oder Hausverbrauch als PV-Erzeugung interpretieren.
- Prognosewerte vor Korrektur für Lernbeobachtungen verwenden, keine Selbstkalibrierung. Kalibrierung nur bei gültiger Vorhersage, mindestens 300 W; nachts, bei ungültigen Werten, Clipping und ohne ausreichende Daten bleibt Faktor 1.0.
- Robuste Faktoren nach drei Wolkenklassen, auf 0.60–1.25 begrenzt. Lernhistorie persistent und auf 30 Tage begrenzt, Reset nur auf Lernhistorie, ohne Änderung der Konfiguration.
- Externe Forecasts, Sicherheitsschaltungen und Budgetregelung unverändert. Vor Release Tests/Hassfest/HA-Versionen prüfen.

## Heizstab-Responsive-Layout (nach 0.3.50, für 0.3.51)
- `Auto | Ein | Aus` bleibt ausschließlich bei temperaturgeregeltem Heizstab, behält den vorhandenen `data-setmode`-Handler (auto/manual/off) und befindet sich als erstes Kindelement in `.power-budget.heater-power-budget`.
- Breite Ansicht: Umschalter und Messwerte liegen nebeneinander **innerhalb desselben rechten Leistungs-/Budgetblocks**. Schmale Karten (bestehende Container-Breakpoint 560 px): Umschalter **oberhalb** von Leistung und Budget in derselben rechten Spalte (`grid-column:5; grid-row:1`). Namen/Status links dürfen umbrechen. Weder Steuerlogik noch andere Gerätetypen ändern.
- Regression: `tests/ui/card.test.cjs` prüft Position, Reihenfolge, mobile CSS und bestehenden Modus-Serviceaufruf.

## Vier-Flächen-Eigenprognose (in Vorbereitung)

- Standard bleibt externe Prognose; berechneter Modus ist ausdrücklich optional.
  Niemals Prozent-Bewölkung als Wh-Sensor verwenden oder externe und berechnete
  Erträge unbemerkt addieren.
- HA-Standort ist Koordinatenquelle; Flächen: kWp, Neigung 0–90°,
  Azimut 0=N/90=E/180=S/270=W, maximal vier. Eingabe seit 0.3.64 über den
  PV-Flächen-Editor (siehe oben), nicht mehr über Optionsfelder.
- Prognose nur mit gültiger My-Weather-Zeitreihe; ungültige/fehlende
  Bewölkung nicht mit 0 % ersetzen. Keine neuen API-Anfragen.
- Externe Vorhersagen, bestehende Geräteprioritäten und Schutzlogik erhalten.
  Vor Release Forecast-Plan, Restart, Optionen und lokale DST prüfen.

# Smartify Energy Pro – Arbeitsregeln für alle Agenten

## Verbindliche Lesepflicht vor der ersten Änderung

- Es arbeiten mehrere Personen/Agenten am Repository. Zuerst aktuellen Remote-Stand von main und neuestes Release abrufen; niemals eine alte lokale Kopie als aktuell annehmen.
- Bei einem Git-Checkout zuerst Status/Diff prüfen und fremde lokale Änderungen erhalten. Bei einer API-Arbeitskopie den Ausgangs-Commit dokumentieren und betroffene Dateien aus genau diesem Commit laden.
- Vor dem ersten Edit diese Datei, CHANGELOG.md und die Dokumentation zur betroffenen Funktion lesen. Den aktuellen Code entlang des betroffenen Ablaufs sowie die zugehörigen Tests lesen. In der Git-Historie gezielt nach früheren Fixes suchen und deren Änderungen prüfen, auch wenn sie von anderen Agenten stammen.
- Vor dem Bearbeiten im Arbeitsbericht kurz festhalten, welches bestehende Verhalten erhalten bleiben muss und welcher Test es prüft. Fehlt ein passender Test, die geplante Prüfung benennen. Beispiel Kartenregistrierung: Beim HA-Start im Event-Loop ausführen und bei verspätetem Lovelace-Start erneut versuchen (tests/ha/test_card_resource.py).
- Vor dem Push Remote-HEAD erneut prüfen. API-Updates mit expected_sha, Git-Push ohne Force. Bei zwischenzeitlichen Änderungen neu abgleichen und Tests wiederholen. Keine Änderungen der Kollegin überschreiben.

## Stand und wichtige Regeln
Stand dieser Übergabe: Quellcode 0.3.34, 31.10.2026. Ausgangspunkt war main 87f2ffec013a225210a4240d26a7f51a76ff8ff9 (0.3.33). Verbindlich sind immer der frisch abgerufene Code und das Manifest, nicht diese historische Angabe. Veröffentlichung separat auf GitHub prüfen.
- 0.3.34: LoadDevice.decide prüft den fälligen Spätstart bereits bei „erkannt“, vor PV-/History-Prüfungen. Kein AUS/EIN-Impuls. Gilt auch für Trockner mit Wiederanlauf; früheste Startzeit und Programmerkennung bleiben erhalten.
- 0.3.33: Aktionen in der Gerätezeile, „Fertig“ löst Reset aus, Pflichtstart-Anzeige, Auto-SoC, Startprüfungen als Icons und „Info“. Diese Änderungen erhalten.
- 0.3.32: Notwendige Heizstab-Abschaltung vor Prognosen/anderen Geräten. Aktorfehler dürfen nicht andere Heizstäbe blockieren. Mindestlaufzeit darf diese Abschaltung nicht verhindern; kein Neustart im selben Zyklus.
- 0.3.31: Automatischer Heizstabstart benötigt gültige Netzsensoren; ungültige Werte erzwingen AUS. Bei getrennten Sensoren müssen beide gültig sein. Manuell erlaubt Netzbezug; Beobachten schaltet nicht.
- Akku-Ladeleistung ausschließlich höher priorisierten Geräten gutschreiben (kleinere Prioritätszahl). Gleiche/niedrigere Priorität erhält keinen Kredit.
- Freigegebene Haushaltsprogramme dürfen bei PV-Abfall weiterlaufen. Nicht wiederanlauffähige Trockner nicht durch Steckdosenabschaltung steuern.
- Reguläre PV-Starts: Langmittel, Kurztrend-Mittel und aktuelles individuelles Budget müssen jeweils ausreichen; bei stark fallendem Trend zusätzlich die Fortschreibung. Erzwungene Starts sind bewusst Ausnahmen.

## Änderung 0.3.35 (01.11.2026)
- Pro Haushaltsgerät: `detect_threshold` (9 W) und `detect_seconds` (20 s) in der bestehenden SEP-Karte. `finish_threshold` und `finish_minutes` in derselben Gruppe; beide Erkennungszustände „bereit“ und „fertig“ verwenden dieselben Startparameter.
- `pause_budget_release_pct` ersetzt `pause_reservation_pct`: 0 % Freigabe = volle Reservierung. Altwerte beim Laden invertieren; gemessene Last bleibt berücksichtigt. Die Einstellung erscheint am Ende des Gerätemenüs.
- Dokumentation, Test und Releaseversion synchron halten. Diese Zeilen beschreiben 0.3.35 und ersetzen nicht die Verpflichtung zum Remote-Abgleich.

## Manuelle Haushaltsgeräte-Aktionen (nach 0.3.35)
- Reset/Fertig und Sofortstart lösen einen sofortigen Regelzyklus aus. Reguläre Sensor- und Parameteränderungen behalten ihr Debounce. Ein noch geplanter verzögerter Zyklus wird vor dem manuellen Lauf abbestellt; bei belegtem Lock bewirkt der bestehende Rerun-Mechanismus einen Folgelauf.

## Release 0.3.36
- Manuelle Haushaltsgeräte-Aktionen sofort ausführen; Debounce für Sensoränderungen beibehalten.
- Alte Registry-Einträge `pause_reservation_pct` in der Karte filtern; `pause_budget_release_pct` bleibt die aktive Einstellung.

## Prioritäten per Drag & Drop (nach 0.3.36)
- Karten-Reihenfolge beim Loslassen optimistisch und unmittelbar zeichnen, Backendantwort nicht vor der Darstellung abwarten. Bei Servicefehler Position wiederherstellen und Fehler anzeigen. Prioritätsänderung als eine Aktion übernehmen und Regelzyklus ohne Sensor-Debounce ausführen. Laufende Sensoraktualisierungen dürfen die optimistische Ansicht nicht überschreiben.

## Stand 0.3.37
- Optimistische Prioritätssortierung mit sofortiger Anzeige, zusammengefasster Backend-Übernahme und Fehler-Rollback. Sensor-Debounce bleibt für normale Messwertänderungen erhalten.

## Stand 0.3.38 – Card-Einbindung
- **Geändert in 0.3.62:** Card wird NUR noch als Lovelace-Storage-Ressource eingebunden (`_async_ensure_lovelace_resource`, nach `homeassistant_started`). `add_extra_js_url` NICHT wieder zusätzlich aktivieren: Extra-JS steht im `<head>` der index.html und läuft im Wettlauf mit dem Scoped-Custom-Element-Registry-Polyfill des HA-Frontends. Definiert die Card ihre Elemente vor dem Polyfill, liefert `customElements.get()` danach nichts mehr und `whenDefined()` löst nie auf → dauerhaft „Konfigurationsfehler / Custom element doesn't exist“ bis zum Reload (am 11.11.2026 auf HA 2026.10.4 nachgestellt). Die identische Ressourcen-URL hilft dann nicht, weil das Modul nicht erneut ausgeführt wird. Extra-JS ist nur noch Ersatz, wenn nach allen Versuchen keine Storage-Ressource möglich ist (YAML-Modus, `_async_extra_js_fallback`). Tests: `test_async_setup_registers_without_thread_errors` (kein Extra-JS), `test_yaml_mode_falls_back_to_extra_js`. `customElements.define` bleibt durch `customElements.get` abgesichert.
- 0.3.44: Registrierung nur im Event-Loop. Event-Listener und Timer-Callbacks, die `hass.async_*` aufrufen, MÜSSEN `@callback` oder `async def` sein – eine normale `def`-Funktion führt HA im Executor-Thread aus (`RuntimeError` thread-safety). Wiederholungen über `asyncio.sleep` in einer `hass.async_create_background_task`. Test: tests/ha/test_card_resource.py.

## Kompakte Gerätezeilen (nach 0.3.38)
- Sofortstart, Nachladen und Fertig rechts unter Leistung/Budget statt unter Statusmeldungen. Aktionslogik und Click-Handler bleiben unverändert. Bei schmalen Displays dürfen Tasten umbrechen und der rechte Block wandert unter die Statusinfos.

## Release 0.3.39
- Kompaktere Haushaltsgeräte-Zeilen: Aktionsknöpfe rechts unter Leistungs-/Budgetwerten. Mobile Umbrüche erhalten; Event-Handler unverändert.

## Hintergrundtransparenz SEP-Karte
- `background_transparency` ist eine kartenspezifische Lovelace-Option (0–100 %, Standard 0 %), im Karteneditor über Schieberegler einstellbar. Nur Hintergründe mit themeabhängigen Farben mischen, nicht das komplette Element per opacity ausblenden; Lesbarkeit von Schrift, Icons und Schaltflächen erhalten. Karten- und Gerätehintergründe einschließlich Zeitleiste beachten.

## Release 0.3.40
- Kartenoption `background_transparency` (0–100 %, Standard 0 %) steuert ausschließlich Flächen via themeabhängigem CSS `color-mix`; Text und Aktionsknöpfe bleiben lesbar.

## Card-Ladestabilität (nach 0.3.40)
- Fehlende Lovelace-Ressource nach HA-Start nicht still ignorieren; bei später bereitgestelltem Lovelace mit begrenzten Wiederholungsversuchen nachregistrieren. Frühere Hash-URL sowie idempotente Ressourcen-Updates erhalten. Fehler protokollieren.

## Release 0.3.41
- Lovelace-Registrierung beim Start bei temporärer Nichtverfügbarkeit erneut versuchen und Fehler protokollieren (seit 0.3.62 nur noch Lovelace-Ressource, siehe „Stand 0.3.38 – Card-Einbindung“). Vor Veröffentlichung alle CI-Jobs prüfen.

## Responsive SEP-Karte (nach 0.3.41)
- Auf iPhone/iPad bleiben Leistung, Budget, Zahnrad und Aktionen stets in Spalte 5 rechts; keinen mobilen `grid-row:2`-Umbruch für `.right` verwenden. Status und Geräbename links dürfen mehrzeilig umbrechen; Bedienelemente und Drag-Handle bleiben bedienbar.

## Release 0.3.42
- Mobile Gerätezeilen behalten rechte Spalte für Leistung, Budget, Zahnrad und Aktionen bei. Linke Namen/Statustexte dürfen umbrechen; keine 2. Grid-Zeile für .right.

## Dokumentation bei jeder Änderung
Dokumentation gehört zur Änderung, nicht zu einem späteren Auftrag. Bei Verhaltens-/UI-Änderungen README.md (HACS-Infoseite), docs/SEP_CURRENT.md, docs/FUNCTIONS.md, relevante Update-/Konfigurationshinweise und CHANGELOG.md abgleichen. Veraltete widersprüchliche Aussagen ersetzen. Pflicht/optional und Bedeutung von Einstellungen in einfachen Worten erklären; DE/EN-UI und Übersetzungsschlüssel konsistent halten. AGENTS.md bei wichtigen Architektur-/Verhaltensänderungen aktualisieren. Vollständige Chronik im CHANGELOG, keine Zugangsdaten oder privaten Anlagenwerte eintragen.

## Prüfung und Veröffentlichung
- Passende Regressionstests ergänzen, insbesondere tatsächliche Aktorbefehle und Fehlerfälle. Für den Pflichtstart: tests/test_forced_start.py.
- Lokal: python -m unittest discover -s tests; python -m compileall -q custom_components tests; python scripts/validate_translations.py. Bei JS-Änderungen zusätzlich npm test und Syntaxprüfung.
- Mit HA-Testumgebung: python -m pytest tests/ha -q; ruff check custom_components. Fehlende lokale Abhängigkeiten offen nennen; GitHub-CI muss erfolgreich sein.
- Version in custom_components/smartify_energy/manifest.json und dazu passenden Changelog-Abschnitt pflegen. Manifeständerung auf main startet die bestehende Publish-SEP-Pipeline.
- Release erst als veröffentlicht melden, wenn GitHub-Release existiert, Ziel-Commit passt und erforderliche Prüfungen erfolgreich sind. Keine Prüfungen umgehen. Automatisierte Tests nicht als Test an echter Hardware darstellen.

- Schmale Prioritätenlisten anhand ihrer eigenen Breite formatieren. Die rechte Spalte begrenzen, damit Modus und Zahnrad den Gerätenamen nicht verdrängen.

## Wallbox PV-Stopp (0.3.45)
- `EvDevice.pv_stop_at` = `_deficit_since + stop_delay`, nur bei Status `charging_pv` (Statuscodes über `STATUS_CODES` vergleichen, nicht Legacy-Strings). `_deficit_since` wird bei nicht laufender Ladung, Sofort-/Pflichtladung, Abstecken und Verdrängung gelöscht. Strom wird weiterhin sofort reduziert, abgeschaltet erst nach Ablauf. Test: tests/test_ev_stop_delay.py.
- Karte: EV-Zeile Akku zuerst, Leistung/Budget in `.pb-stack` untereinander; andere Geräte `.pb-pair` (display:contents) unverändert.

## Heizstab-Umschalter (0.3.50)
- `_heaterSwitch(dev.mode)`: Auto=auto, Ein=manual, Aus=off über `select.select_option` (`data-setmode`). Kein `.mode-tag` beim Heizstab. UI-Test „heater row offers Auto/Ein/Aus…“.

## Gerätezeile (0.3.49)
- Kein `_modeSelect` mehr in Gerätezeilen (nur Kartenkopf/Hub). EV: `_quickSelect(dev.goal)`; Load: `.sep-actions` innerhalb `.power-budget`; Manuell/Aus als `.mode-tag`. UI-Test „device rows: no mode select…“.

## Kompakte Einstellungen (0.3.48)
- Karte: `SETTING_SHORT` (Kurzinfo, ≤ 34 Zeichen), `SETTING_GROUPS` (Reihenfolge, `collapsed`), `SETTING_VISIBLE` (kontextabhängig), lange Texte weiter in `SETTING_HELP` hinter (i). Neue Parameter MÜSSEN in SETTING_SHORT und einer Gruppe stehen – UI-Test „every documented setting has a short text and a group“ prüft das.

## Wallbox Ladeende / Karte (0.3.47)
- `EvDevice.full_at()` → Attribut `voll_um`: (Max-SoC − SoC) × Kapazität / Wirkungsgrad / gemessene Leistung; nur bei Ladung ≥ 500 W, verbunden, SoC und Kapazität vorhanden. Test: tests/test_ev_boost.py (EVFullAtTests).
- Karte: Boost-Toggle ist `button.gear.boost` neben dem Zahnrad (nicht in `.sep-actions`); `show_allocated` (Standard false) steuert die Kachel „Verteilt“.

## Auto-Startprüfung (0.3.56)
- `EvDevice.start_gate` wird nur im regulären PV-Startpfad (nicht ladend) gesetzt, sonst None; Card nutzt ausschließlich diese Werte (2-min-Ø = `budget_short`, nicht `mittel_w`). Tests: `EVStartGateTests`, UI „EV shows history + budget start check…“.

## Auto-Zeile (0.3.55)
- `.ev-power-budget` mit `.ev-ctl` (Ladeziel + Boost) als erstem Kind; breit nowrap, ≤560 px Bediengruppe volle Breite oben, Leistung/Budget untereinander. UI-Test „EV controls … before the battery“.

## Wallbox PV-Boost Wallbox-Minimum (0.3.54)
- `_decide_boost`: `boost_min_power > 0` ⇒ Ziel mindestens Wallbox-Minimum (`min_a × V × Phasen`), kein `_deficit_since`. Nur bei 0 W Stopp-Verzögerung. Tests: `test_minimum_below_three_phase_wallbox_minimum_keeps_charging`, `test_factor_only_on_three_phases_still_uses_stop_delay`; UI „Boost endet“.

## Wallbox PV-Boost (0.3.46)
- Param `boost` (switch), `boost_factor`, `boost_hours`, `boost_min_power`; Endzeit in `state["boost_until"]` (persistiert), gesetzt im ersten Zyklus nach dem Einschalten (ctx.now), Ablauf/Abstecken → `_end_boost()`. Boost-Zweig in `decide` NACH Sofort/Pflicht, VOR PV-Laden; ignoriert `preempt_until`; `can_preempt` False während Boost; `_can_reclaim_pv_power` gilt auch für Boost bei Ziel km/Tage. Test: tests/test_ev_boost.py.

## Release 0.3.43
- Kompakte Modusnamen und begrenzte rechte Spalte auf schmalen Karten.

## Schnelle aktuelle Budgets (Branch fix/fast-budget-input-refresh)
- Netz-, Akku- und sämtliche konfigurierten Geräte-Leistungssensoren werden mit 0,25 s kurzer Bündelung ausgewertet; weniger budgetkritische Sensoren bleiben bei 2 s.
- Ein früher geplanter langsamer Zyklus darf einen später eintreffenden schnelleren niemals blockieren. Schnellere Anforderung ersetzt den ausstehenden Timer; gleich schnelle/langsamere bleiben gebündelt.
- Geräte-Moduswechsel (inkl. Heizstab Auto/Ein/Aus) veranlassen einen Regelzyklus ohne absichtliche Verzögerung. Bestehende Verriegelung und Rerun schützen vor Parallelzyklen.
- Keine Aufweichung von Gerätehysterese, PV-Gates, Mindestzeiten, Stopp-Verzögerung, Hardware-Kommandogrenzen oder Akku-Prioritätsgutschrift. Tests in tests/ha/test_runtime.py.

## Optionale Abwesenheitssperre für Heizstab und WW-Boost
- Je Gerät optional `absence_entity` (`binary_sensor`/`input_boolean`), `on` = abwesend; `off` = freigegeben. Fehlende/unknown/unavailable konfigurierte Entität sperrt sicherheitshalber ebenfalls.
- Sperre wirkt als effektiver Modus `off`, ohne den vom Nutzer gespeicherten Modus zu überschreiben. Heizstab schaltet auch in Manuell ab und darf nicht neu starten; WW-Number-Boost wird auf Normalwert zurückgestellt.
- WW-One-shot (Button/Switch/Input-Boolean): keine neuen Auslösungen bei Abwesenheit; bereits von der Wärmepumpe selbst verwaltete WW-Zyklen werden nicht abgebrochen. Abwesenheitseingang als schnelles beobachtetes Ereignis berücksichtigen.
- Tests: `tests/ha/test_runtime.py`; Dokumentation/Übersetzungen DE/EN synchron halten.
