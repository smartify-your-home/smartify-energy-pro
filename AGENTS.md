# Smartify Energy Pro – Arbeitsregeln für alle Agenten

## Vor jeder Arbeit
- Diese Datei, CHANGELOG.md und die zum Auftrag passenden Dokumente lesen.
- Es arbeiten mehrere Personen/Agenten am Repository. Zuerst aktuellen Remote-Stand von main und neuestes Release abrufen; niemals eine alte lokale Kopie als aktuell annehmen.
- Bei einem Git-Checkout zuerst Status/Diff prüfen und fremde lokale Änderungen erhalten. Bei einer API-Arbeitskopie den Ausgangs-Commit dokumentieren und betroffene Dateien aus genau diesem Commit laden.
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
- Card wird zweifach mit identischer URL eingebunden: `add_extra_js_url` und Lovelace-Storage-Ressource (`_async_ensure_lovelace_resource`, nach `homeassistant_started`). Grund: Extra-JS steht fest in der beim Seitenaufruf geladenen index.html und fehlt, wenn das Dashboard vor SEP-Setup geladen wurde → „Konfigurationsfehler“. Beide Wege erhalten; `customElements.define` bleibt durch `customElements.get` abgesichert.

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
- Lovelace-Registrierung beim Start bei temporärer Nichtverfügbarkeit erneut versuchen; beide bestehenden Ressourcenwege erhalten und Fehler protokollieren. Vor Veröffentlichung alle CI-Jobs prüfen.

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

## Release 0.3.43
- Kompakte Modusnamen und begrenzte rechte Spalte auf schmalen Karten.
