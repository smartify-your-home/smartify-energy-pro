## 0.3.88 – WW-Unterbrechung darf nur vorher aktive FBH erneut anstoßen
- **Keine** kurze Sollwert-Überhöhung allein aufgrund WW-Ende. Ein gültiger Übergang: FBH-Status war **vor WW EIN** und elektrische WP-Leistung > Standby; dann WW von AUS→EIN, danach EIN→AUS. Nur wenn der ursprüngliche FBH-Boost weiterhin aktiv ist, FBH *nicht selbst* anläuft und das Zeitfenster noch läuft, frühestens nach `fbh_restart_wait` Minuten erneut kurz erhöhen.
- Dazu müssen `ww_active_entity` UND `fbh_heating_active_entity` konfiguriert und verfügbar sein. Unbekannter Status und WP-Leistung ohne FBH-Betriebsart sind kein Freigabesignal. War die FBH schon vor WW aus, kein Wiederanlaufimpuls. Rekonstruktion nach Restart ohne gesicherte Statusflanken verboten.
- Option `fbh_restart_after_ww` standardmäßig AUS, Wartezeit 5 min, zusätzliche +3 K über schon aktiven Boost, Begrenzung 15 min, maximal eine Zusatzerhöhung je Zeitfenster. Maximaltemperatur nie überschreiten. Bei bestätigtem FBH-Neustart oder WW-Neustart Extraerhöhung vorzeitig zurücknehmen. PV-Betrieb nur bei gültigem Budget. Vor Extra-Schreibvorgang und Rückstellung alten Stand persistent sichern. Tests für vorher aktiv/inaktiv, Spontanstart, begrenzte Dauer, Sollwertmaximum und fehlendes Feedback.

## SEP 0.3.88 – WP-FBH-Boost, Vorausreservierung und verbleibende PV-Alltagstipps
- Neuen unabhängigen Subentry-Typ `heatpump_fbh` verwenden, bestehender `heatpump` bleibt rückwärtskompatibel und wird nur als **WP Warmwasser Boost** bezeichnet. Schreibbare temperature `number`, `input_number` oder `climate`-Entität, elektrische WP-Leistung und Nennleistung. Optional (dringend empfohlen) WW- und FBH-Heizbetrieb-Binarysensoren. Aktivierung standardmäßig im Modus Beobachten, so keine unbeabsichtigte Temperaturänderung beim Anlegen.
- **Zwei Zeitfenster**, Parameterschalter `fbh_control=time|pv`, Sollwertdelta Kelvin, Sicherheitsmaximum, Vorausreservierung **0–120 Minuten** (0 aus), Standby-Leistungsgrenze, Mindest-Heizlaufzeit und Standby-Dauer. Einen Boost einmal je Zeitfenster. Ursprünglichen Sollwert dauerhaft vor dem Anhebungsservice schreiben. Bei Ende/Fertig/Off/Moduswechsel Rückstellung; Sicherung nicht löschen bis bestätigte Rückstellung. Manuelle Temperaturveränderung nicht überschreiben.
- Nach 3 h tatsächlich zugeordneter FBH-Heizlaufzeit + 20 min elektrischem WP-Standby pro Zeitfenster fertig, Leistung freigeben und auf ursprünglichen Sollwert zurückstellen. WW-Zyklen niemals mitzählen; nach bestätigtem Fertig im selben Fenster kein erneuter Start. Ohne WP-Modus-/WW-Signal keine unzuverlässige automatische Fertigmeldung.
- Vorausschauender FBH-Budgetbedarf wird an der Gerätereihenfolge-Rangposition anderen noch nicht gestarteten Verbrauchern vorgezogen. Dabei nur **zusätzliche** WP-Watt gegenüber der aktuellen Messung reservieren und für gleiches WW/FBH-Leistungssensorpaar nur ein gemeinsames offenes Budget zählen. Keine laufenden Waschprogramme stoppen. Tests der Rückstellung, Reservierung und Fertigmeldung pflegen.
- `pv_advice.day_windows` bewertet am heutigen Tag nur **Rest der echten Stundenprognose ab jetzt bis 16 Uhr**, bereits vergangene Stunden weder als 0-Fehler noch als Ertrag. Nur wenn die verbleibende PV nicht für ein Waschprogramm reicht und ein folgender Tag erheblich besser ist, empfiehlt SEP eine Verschiebung. Ein gutes verbleibendes Tagesfenster hat Vorrang vor höherer zukünftiger Gesamtsumme.
- Waschtipp entfernen bei erkannter/gewarteter/laufender Wäsche, ebenso nach heute beendeter Wäsche. Geräte-Power allein als sicherheitshalber frühes Signal; ein nur mit Strom versorgter Leerlauf-Stecker zählt nicht als Waschprogramm. Nach jedem Regelzyklus neu berechnen, nicht nur beim 15-minütigen Forecast-Refresh.
- Manifest/AGENTS/README/CHANGELOG/DE-EN Übersetzungen vor Release prüfen; kein Merge bei fehlgeschlagener CI, Release nur über bestehenden Publish-SEP-Workflow.

## SEP 0.3.87 – GeoSphere 60h-Bewölkung
- Für `solar_weather_source=cloud` verarbeitet SEP bis zu 60h echte Wolkenwerte nur bei GeoSphere-C-LAEF-Sensormetadaten: `source=GeoSphere Austria C-LAEF`, `dataset=nwp-v2-1h-1km`, `max_forecast_hours=60`. Für Meteonomiqs 8/48h und andere Quellen bleibt der bisherige 48h-Parserhorizont. Keine Entity-ID-Heuristik.
- `cloud_coverage` statt `ghi_w_m2` wird im Wolkenmodell genutzt. Bei GHI-Eigenberechnung keine Änderung: keine zweite Cloud-Dämpfung. Keine erfundenen Stunden, Kalibrierung und Messwert-Schutz unverändert; 72h-Anzeigefenster und Geräteplanung heute/morgen beibehalten.
- Version 0.3.86 wurde zurückgezogen; neuer Release 0.3.87, keine Wiederverwendung der Tagnummer. Regressionen: `tests/test_geosphere_solar.py` und `tests/ha/test_geosphere_cloud_horizon.py`; alle GitHub-Tests vor Release, Doku DE/EN/Changelog pflegen.

## GeoSphere-C-LAEF-Prognose in SEP (0.3.85)
- `solar_weather_source=cloud` ist der unveränderte Standard; `geosphere` ist eine ausdrücklich gewählte Alternative zur Bewölkungsabschätzung nur bei `solar_mode=calculated`. Bestehende `solar_cloud_entity`-Konfiguration wird als Wettersensor wiederverwendet, nicht mit externen Prognose-Sensoren addieren.
- GeoSphere-Sensoren von `my-weather` müssen stündliches `ghi_w_m2` als horizontalen Mittelwert W/m² liefern, inkl. `source`, `dataset`, `irradiance_unit`, gültigem `datetime` und `end`. Falsches Format/Einheit, fehlende/stale Stunden ⇒ keine erfundene 0- oder Klarhimmel-Prognose. 0 W/m² bei gültiger Stunde bleibt 0.
- `pv_hours_ghi` nutzt vorhandene Flächendaten (bis 4, inkl. bifazial) zur näherungsweisen POA-Umrechnung. **Nie** zusätzlich Cloud%-Abschlag anwenden; Cloud% nur für optionale Quellenspezifische Kalibrierung. Alte Kalibrierungsdaten ohne `source` gehören zu `cloud`; zwischen GeoSphere/Bewölkung keine Lernwerte vermischen.
- Kein neuer API-Call in SEP. GeoSphere ist optional und wird nur von `my-weather` direkt geladen. Aktuelle Netzleistung, Schutzbedingungen, Geräte-Prioritäten, 15-min-Plan, PV-Vergleich-Baseline und 14-Tage-Historie unverändert. Neue Funktion nur mit Regressionstests, Doku, DE/EN-Übersetzungen und grüner CI freigeben. My-weather PR #9 ist eigenständig zu validieren.

## Überschrift-Prioritäten: Bedienelemente links in Reihenfolge (0.3.84)
- In der Kopfzeile des Prioritätenabschnitts **exakt Ziehgriff · Schloss · „Prioritäten“** von links nach rechts anzeigen, im mobilen und Desktop-Layout. data-section-grip="priorities" steuert nur die Verschiebung des ganzen Abschnitts; data-priority-lock entsperrt nur die Reihenfolge einzelner Geräte. Tooltip/ARIA und Sperrschutz erhalten.
- UI-Test in tests/ui/card.test.cjs überprüft die tatsächliche DOM-Reihenfolge, auch nach Änderung des Sperrstatus. Versionierung, Changelog und CI beachten.

## PV-Plan-Abschnitt vor Prioritäten verschieben (0.3.83)
- **PV-Plan inklusive „PV-Prognose / Ist-Erzeugung (14 Tage)“ als zusammenhängenden Block** verschieben. Der PV-Block kann vor bzw. hinter dem Prioritätenblock stehen; der HA-Header mit Saldo/Budget bleibt an seiner Position. Geräte-Prioritäten unverändert.
- Standard ist bisherige Reihenfolge `pv_plan_first=false`; Karteneditor stellt die zwei Bereiche als per Maus-/Touch-Drag-&-Drop vertauschbare Zeilen bereit und speichert `pv_plan_first` mit `config-changed` in Lovelace (geräteübergreifend). Pfeile sind barrierearme Alternative.
- Die Karte selbst hat `data-section-grip`-Handles und tauscht Bereiche nach zielgerichtetem Pointer-Drag, bei `pointercancel`/kurzen Bewegungen unverändert. Der normale Kartenbetrieb speichert die Ansicht lokal im Browser; zum geräteübergreifenden Speichern Card-Editor nutzen. Nie den `set_priority_order`-Service für Abschnittsverschiebung verwenden.
- Die Prioritäten-Sperre muss weiterhin **ganz links neben der Überschrift** stehen und ausschließlich Geräte-/Akku-Drag sperren. Abschnittsverschiebung vom Schloss unabhängig; PV-Stunden, Tagesvergleich, Tipps, Touchscroll, Geräte-Aktoren unverändert.
- Tests in `tests/ui/card.test.cjs`, Doku und Release-Notes pflegen; CI vor Veröffentlichung prüfen.

## Priority-Drag-Sperre und kompakter Tagestrenner (0.3.83)
- In der SEP-Lovelace-Karte über der ersten Gerätezeile **links** neben dem Wort `Prioritäten` einen Schlossschalter `data-priority-lock` anzeigen. Default in jeder Karteninstanz `_priorityLocked=true`, auch nach Neuladen. Nur nach bewusstem Entsperren Drag & Drop zulassen (auch Akku); gesperrte Handles optisch dimmen und mit `touch-action:pan-y` normales Touchscrollen erlauben.
- Vor jedem `_dragStart`, bei Bewegung und vor Senden von `set_priority_order` Sperrzustand prüfen. `pointercancel` verwirft den Sortierversuch. Keine Änderung am Backend-Prioritätsservice oder an der optimistischen Sortierung, wenn entsperrt. Während `_prioritySaving` Sperrschalter deaktivieren.
- Im PV-Plan die vertikale Nacht-/PV-Pausenbeschriftung samt grau hinterlegtem breitem Abschnitt entfernen. Ein **transparenter schmaler 12px-Trenner** mit Tooltip, plus bereits vorhandene Tagesüberschriften, genügen. Interne Zeitdaten und Vorhersagen nicht ändern.
- Regressionen `tests/ui/card.test.cjs`, Changelog und Doku aktualisieren; Versionierung/Release nur nach vollständiger CI.

## PV-Prognose-Ist-Vergleich: starre Peak-Skala (0.3.82)
- Diagramm-Y-Maximum **streng 1,0 × `pv_vergleich.gesamt_peak_kwp` × 1000 Wh**, nicht aufrunden und keinen 10-%-Puffer hinzufügen. Beispiel 10 kWp → 10 kWh/Stunde. `sepAxisLabels` teilt das feste Maximum in vier gleiche Achsenintervalle.
- Historische Messspitzen dürfen das Maximum **nicht** ändern. Bei beobachteten Leistungen über STC-Peak bleiben Sensorwerte/Tooltip vollständig erhalten; nur die Balken werden bei 100 % abgeschnitten. Das gilt ausschließlich für den 14-Tage-Prognose-Ist-Vergleich, nicht für die andere PV-Plan-Skala oder Regelungen.
- UI-Tests für kWp=2,5 und 10 inklusive gemessenem Ausreißer > 10 kWh; Dokumentation und Changelog aktualisieren.

## PV-Plan-Karte: kompakte Bedienung und größere Tipps (0.3.81)
- Keine eigene Zeile „PV-Prognose · Tage horizontal scrollen“, **keine** Tagwechsel-Buttons `data-pvplan`; horizontales Touchscrolling über `.pv-plan-scroll`, Tagesüberschriften, feste kW-Achse und Übermorgen-Prognoseabdeckung bleiben erhalten.
- Tipp-Bereich **über** den Balken mit SEP-Standardfont: `.pv-tip-title` 16px / halbfett, `.pv-tip-detail` 14px / sekundäre Farbe. Pfeile `data-pvtip` zum Wechseln zwischen mehreren Tipps bleiben ausdrücklich bestehen. Kartenoption `show_pv_tips` bleibt erhalten.
- Bei UI-Änderungen Tests in `tests/ui/card.test.cjs`, Dokumentation und Release-Notes aktualisieren; Release nur nach grüner CI veröffentlichen.

## Release 0.3.80 – Prognoseabdeckung / fehlende Stunden / CI-Flut
- Datenverfügbarkeit strikt von 0 W unterscheiden: `plan.stunden[*].prognose_verfuegbar` und bei fehlenden Prognosewerten `pv_w=null`; `forecast_today/plan` zeigen `prognose_bis`, `prognose_stunden` und bei berechneter Prognose `wetter_sensor`. Ohne gültigen Anbieterwert keine erfundenen Balken oder Waschtipps.
- Übermorgen muss im PV-Plan navigierbar bleiben, auch wenn echte Prognose bis dahin nicht reicht: Tagesüberschrift plus expliziter „Prognose fehlt“-Block. Tagespfeile für Desktop und horizontales Wischen für Touch, linke kW-Skala fest. Volle 08–16-Uhr-Prognose für übermorgen um 06:00 erfordert mehr als 48h Forecast (58h); My-Weather 48h gibt nur tatsächlich gelieferte Stunden aus. Alternative 8h-Sensorauswahl nicht stillschweigend verändern.
- `.github/workflows/validation.yml`: gleichzeitige PR-Läufe pro PR per concurrency cancel-in-progress, `workflow_call` für verpflichtende Publish-SEP-Validierung, `workflow_dispatch` für manuelle Prüfläufe. Kein doppelter main-Push-Validierungslauf neben Publish-SEP. Keine Reduktion der eigentlichen Tests. E-Mail-Abonnement nur durch Benutzer unter GitHub Notification Settings deaktivierbar.
- Regressionen: `tests/ui/card.test.cjs` (übermorgen, Pfeile, fehlende Quellen), `tests/ha/test_runtime.py` (fehlende PV-Werte `null`), `tests/test_ci_workflow.py`.

## PV-Alltagstipps und scrollbarer PV-Plan (0.3.79)
- Reine **Anzeige-/Sensorfunktion**, keine neue Gerätesteuerung. `pv_advice.build_advice` vergleicht nur **vollständige** stündliche Prognosewerte 08:00–16:00 Lokalzeit für heute/morgen/übermorgen. Eine Verschiebung braucht gleichzeitig mindestens +25 % und +3 kWh gegenüber dem frühesten vollständig vergleichbaren Tag; Übermorgen nur bei zusätzlichem klaren Vorteil. Fehlende Stunden nie als Nullertrag interpretieren; vor 06:00 keine Empfehlung.
- 06:00-Uhr-Lokalauslösung per `async_track_time_change`, danach Forecast-Aktualisierung im bisherigen Intervall; keine Eingriffe in Gerätestarts/Stopps. Geräte-Tipps nur für konfigurierte aktive Gerätetypen, E-Auto nur für PV-only, Wetterstatus nur bei aktiver Live-PV-Analyse. Sensoren `pv_tipp` und `pv_waschtipp` immer verfügbar.
- PV-Plan 08–16-Tipps **über** der horizontal scrollbaren Balkenanzeige; tageweise Überschriften, feste kW-Achse, bisherige Legenden/Belegungen. Zusätzliche Prognosestunden für übermorgen sind ausschließlich Display-Daten und werden nicht für neue Plandisposition verwendet. Keine künstlichen Zukunftswerte.
- Lovelace-Card-Option **`show_pv_tips`** ausschließlich im Karteneditor (Standard true). Bei false Einblendung vollständig entfernen, **HA-Sensoren bleiben aktiv**. Nicht in die Integrationskonfiguration verschieben.
- Regressionen `tests/test_pv_advice.py` und `tests/ui/card.test.cjs`; README/docs/CHANGELOG pflegen. Für release vollständige CI abwarten.

## Adaptive Live-PV-Prognose (0.3.77)
- Nur bei `solar_mode=calculated` mit ausdrücklicher Option `solar_live_adapt_enabled=true`, Standard AUS. Echter PV-Erzeugungsleistungssensor zwingend; Messung muss dieselben Flächen umfassen wie das Modell, weder Netzsaldo noch Batterie/Hauslast.
- `live_pv.LivePVEstimator`: lokale 30-min-Historie, mindestens 6 Messwerte über 5 Minuten, normale Sample-Distanz >=25 s, letzte gültige Messung maximal 4 Minuten alt. Klarhimmel-Referenz anhand bereits eingetragener Flächen und Sonnenstand. Nicht nachts oder bei begrenztem Wechselrichterausgang.
- Prognose nur für aktuellen/kommende rund 2 Stunden zwischen baseline und momentaner Strahlungsannahme mischen, abklingend und eng begrenzt. Nie vergangene Stunden, eingefrorene Prognose des PV-Vergleichs, externe Prognosen, Gerätesicherheiten oder direkte Aktorsteuerung ändern.
- Baseline liegt in `forecast.base_hours`; die Grafik friert diese Baseline ein, während `forecast.hours` Live-Anpassungen für Planung enthält. Diagnosedaten in `forecast_today.live_pv` ausgeben. Regressionen `tests/test_live_pv.py`.

## Ansage für Haushaltsgeräte (0.3.76)
- SEP spricht nicht selbst. Hub-Option `announce_script` (`CONF_ANNOUNCE_SCRIPT`, Schritt Netz, optional) wird über `EnergyManager.announce()` mit `script.turn_on` und `variables: {message}` aufgerufen, nicht blockierend als Background-Task; Fehler nur protokollieren. `announce_script` NICHT in `HUB_ENTITY_FIELDS` aufnehmen (keine Zustandsüberwachung eines Scripts).
- Je Haushaltsgerät (`load` und `dryer`, auch Trockner ohne Wiederanlauf) Schalter `announce_finished` und `announce_reminder`, Standard aus. Logik in `LoadDevice._announce` am Ende von `pre_update`: nur im Zustand „fertig“, Erstansage einmal, Erinnerung alle `REMINDER_SECONDS` (30 min). Zustand `announced`/`announce_at` liegt in `state` (persistiert) und wird in `_reset()` gelöscht.
- Hub-Zeiten `announce_start`/`announce_end` existieren nur mit gewähltem Script; gleiche Zeiten = rund um die Uhr. Lehnt `announce()` ab (kein Script, außerhalb des Zeitraums), darf das Gerät nichts als angesagt vermerken – die Ansage wird im nächsten Zyklus erneut versucht.
- Keine Änderung an Programmerkennung, Freigabe, Budget oder Steckdosensteuerung. Tests: `tests/test_announce.py`, `tests/ha/test_announce.py`; Karte: Gruppe „Ansage“ in `SETTING_GROUPS`, `announce_reminder` nur sichtbar bei eingeschalteter Ansage.

## Bestandsflächen automatisch neu nummerieren (0.3.75)
- Beim Laden des PV-Editors auch bereits gespeicherte automatische Namen ("Fläche N") auf ihre aktuelle Listenposition korrigieren; ausschließlich bei tatsächlich geänderten Namen über den vorhandenen admin-only Save-WebSocket persistieren.
- Bestehende individuelle Namen und stabile IDs, alle Koordinaten, Leistung (kWp), Neigung, Azimut und sämtliche Prognosewerte unverändert lassen.
- Regression: tests/ui/pv-card.test.cjs prüft Wiederherstellung von Fläche 3/4 zu 1/2, eine automatische Speicherung und keine Speicherung bei unveränderten/individuellen Namen.

## PV-Flächennamen und Photon-Suche (0.3.74)
- Nur automatische Namen nach dem Löschen/Abbrechen fortlaufend neu nummerieren; eigene Namen, IDs, Geometrien, Leistungen erhalten.
- Photon nach mindestens 3 Zeichen und 700-ms-Tipp-Pause, maximal 5 Treffer, Backend-Cache und Lock mit mindestens 1,1 Sekunden zwischen Requests. Kein Autocomplete über Nominatim; manuelle Suche per Klick/Enter weiterhin.
- Auswahl verändert nur Kartenmitte. Tests in tests/ui/pv-card.test.cjs und tests/ha/test_pv_editor.py.

## PV-Luftbild: Standort, Adresse und dynamisches Nachladen (0.3.73)
- `pv_layout` liefert den HA-Standort aus `hass.config.latitude/longitude`. Ein altes Luftbild ohne explizit gewählte Adresse/Browse-Position darf den HA-Standort nicht dauerhaft überschreiben. Bei Standortabweichung über 0,002 Grad wird beim Laden **einmal** ein neues Home-Luftbild angefordert. `source: address|browse|home` im Karten-Metadaten-Store aufbewahren.
- Neuer expliziter „HA-Standort“-Knopf; Adresssuche ausschließlich nach Eingabe plus Klick/Enter (`pv_map/geocode`, admin only). Anfrage über Backend an OpenStreetMap Nominatim mit User-Agent, maximal 1 Anfrage/s je HA, einfachem Cache; keine Autocomplete-Anfragen. Fällt die Suche oder ein Luftbild-Download aus, bleibt das bisherige Luftbild bestehen. Den Nutzer vorsehen, dass die eingegebene Adresse an Nominatim übertragen wird.
- Bei SVG-Zoom/Pan bleibt die Kartenbedienung unmittelbar responsiv. Kacheln beim Überschreiten der Zoomschwelle oder Bildgrenzen nach einer 550-ms-Ruhezeit von basemap.at abrufen; vorhandene PV-Flächen/Koordinaten NICHT verändern. Keine Änderung an `pv_layout/save` oder der Prognoselogik.
- Alle Luftbilder weiterhin gecacht in `.storage/smartify_energy_map/<entry_id>`, limitierte parallele Abrufe, vollständige JPEG-Prüfung und local SVG coordinates erhalten. Regressionstests für HA-Ort, Adresse, Zoom/Pan, Fehlschlag und Cache sind verpflichtend.
- Lovelace-Karte wie bisher ausschließlich über versionierte Ressourcen laden (kein reguläres `add_extra_js_url`).

## Kritischer Setup-Schutz (0.3.72)
- `HUB_ENTITY_FIELDS` enthält ausschließlich Konfigurationsschlüssel für Home-Assistant-Entitäts-IDs. Numerische Konfigurationswerte wie `CONF_PV_TOTAL_PEAK_KWP` dürfen nie als `async_track_state_change_event`-IDs registriert werden.
- Regression: `tests/ha/test_pv_editor.py::test_numeric_total_peak_does_not_register_as_entity`. Integration muss mit `pv_total_peak_kwp: 10.5` starten und die Peakleistung an den Plan-Sensor ausgeben.
- Keine Änderungen an fester PV-Y-Achse, Prognose/Regelung oder Karteneinbindung.

## PV-Vergleich: Tagesauswertung beim Scrollen (0.3.71)
- Die Zusammenfassung oberhalb der 14-Tage-Balkengrafik zeigt **nur den ausgewählten lokalen Kalendertag**, niemals `pv_vergleich.prognose_kwh` / `ist_kwh` / `abweichung_pct` (diese Attribute fassen weiterhin sämtliche vergleichbare Stunden der Historie zusammen).
- Sichtbarer Tag wird beim Öffnen auf den jüngsten Tag gesetzt und beim horizontalen Scrollen anhand der Bildschirmmitte bestimmt. Eine HA-Neuzeichnung darf den Scrollstand nicht verlieren; der bereits vorhandene `patchChildren`-Mechanismus bleibt erhalten. Keine zeitliche Debounce-Verzögerung bei der Tagessumme.
- Tageswerte verwenden nur Stunden mit vollständiger echter PV-Erzeugungsmessung UND eingefrorener ursprünglicher Stundenprognose. Bei Lücken „bisher“ und keine erfundene Istenergie; `Ist/Prognose-1` nur bei positivem Prognose-Nenner. Die Tagesgrafik bleibt 14 Tage horizontal scrollbar mit fester Peak-Skala.
- Tests `tests/ui/card.test.cjs` prüfen Tagwechsel, aktuellen Tag, Lücken und Refresh.

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

## Wallbox km-/Tage-Ziel ohne PV-Stopp (0.3.78)
- In `EvDevice.decide` (laufende Ladung, nach Pflicht/Boost): Ziel `km_until`/`days` und `_need_wh > 0` ⇒ kein `_deficit_since`, mindestens Mindeststrom, kein Abschalten. Start ohne Überschuss weiterhin nur über Pflichtstart. Ziel erreicht ⇒ normale Stopp-Verzögerung. Tests: `tests/test_ev_stop_delay.py` (`test_km_goal_*`).

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
