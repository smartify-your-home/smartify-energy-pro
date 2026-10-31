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

## Dokumentation bei jeder Änderung
Dokumentation gehört zur Änderung, nicht zu einem späteren Auftrag. Bei Verhaltens-/UI-Änderungen README.md (HACS-Infoseite), docs/SEP_CURRENT.md, docs/FUNCTIONS.md, relevante Update-/Konfigurationshinweise und CHANGELOG.md abgleichen. Veraltete widersprüchliche Aussagen ersetzen. Pflicht/optional und Bedeutung von Einstellungen in einfachen Worten erklären; DE/EN-UI und Übersetzungsschlüssel konsistent halten. AGENTS.md bei wichtigen Architektur-/Verhaltensänderungen aktualisieren. Vollständige Chronik im CHANGELOG, keine Zugangsdaten oder privaten Anlagenwerte eintragen.

## Prüfung und Veröffentlichung
- Passende Regressionstests ergänzen, insbesondere tatsächliche Aktorbefehle und Fehlerfälle. Für den Pflichtstart: tests/test_forced_start.py.
- Lokal: python -m unittest discover -s tests; python -m compileall -q custom_components tests; python scripts/validate_translations.py. Bei JS-Änderungen zusätzlich npm test und Syntaxprüfung.
- Mit HA-Testumgebung: python -m pytest tests/ha -q; ruff check custom_components. Fehlende lokale Abhängigkeiten offen nennen; GitHub-CI muss erfolgreich sein.
- Version in custom_components/smartify_energy/manifest.json und dazu passenden Changelog-Abschnitt pflegen. Manifeständerung auf main startet die bestehende Publish-SEP-Pipeline.
- Release erst als veröffentlicht melden, wenn GitHub-Release existiert, Ziel-Commit passt und erforderliche Prüfungen erfolgreich sind. Keine Prüfungen umgehen. Automatisierte Tests nicht als Test an echter Hardware darstellen.
