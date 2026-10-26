# Funktionsstand und Grenzen

Stand: **0.2.8**, 26.10.2026. Diese Seite beschreibt implementiertes Verhalten im Repository, keine bestätigte Funktionstüchtigkeit auf einer bestimmten Home-Assistant-Installation.

## Regelung
- PV-Überschuss, Prioritäten, laufende Verbraucher und Batterie-Strategie fließen in das aktuelle Leistungsverteilungsbudget ein.
- Lasten mit höherer Priorität werden vor nachgeordneten Geräten berücksichtigt; Pflicht- und Sofortladungen können Netzstrom beanspruchen.
- Der reguläre Regelzyklus bleibt konfigurierbar. Änderungen ausgewählter Messwerte lösen schneller eine gebündelte Auswertung aus.

## E-Auto / Wallbox
- Modi: Nur PV, Fahrstreckenziel bis Uhrzeit, Tagesplanung, Sofortladung.
- Eine laufende PV-Ladung regelt ihren Sollstrom aus dem momentanen Restbudget. Die Startfreigabe nutzt weiterhin ein geglättetes Signal.
- Hardwaregrenzen beachten: Mindeststrom, maximale Stromstärke, ganze Ampere, ggf. 1-/3-Phasenwechsel sowie dessen Sperrzeit.
- Unterhalb der nötigen Leistung reduziert SEP bis zum Mindeststrom und schaltet erst nach Ablauf von `stop_delay` ab. Netzbezug ist dabei möglich.

## Batteriespeicher
- SEP kann Speicherleistung, SoC, Kapazität und PV-Prognosen nutzen, um die Priorität von Speicher und Verbrauchern zu bestimmen.
- Strategien: Speicher zuerst, Geräte zuerst oder prognosebasierte Entscheidung.
- **Nicht vorhanden:** Direkte Vorgabe einer Batterie-Ladeleistung, aktives Regeln eines Wechselrichters oder koordinierte Ladestromkommandos an Wallbox **und** Akku.
- Dafür sind passende schreibbare Home-Assistant-Entitäten und eine getrennt zu entwickelnde sichere Stellwertlogik nötig.

## Wärmepumpe
- Boost unter Berücksichtigung von Überschuss, Zieltemperatur, Hysterese, Ruhezeit und Mindestpause.
- Optional Sonnenhöhenwinkel sowie zwei stündliche Bewölkungswerte als Startfilter.
- Die Wetterfilter betreffen nur neue Boosts; sie ersetzen keine prognosebasierte Suche nach dem besten Boost-Zeitfenster.

## Bekannte Risiken und Tests
- Sensoren können langsamer aktualisieren als SEP prüft; Serviceaufrufe an Ladegeräte können verzögert sein.
- Momentane Überschüsse können stark schwanken; die Mindeststrom-/Stop-Regeln verhindern keine kurzfristigen Netzbezüge.
- Prüfen vor produktivem Betrieb: Sensor-Vorzeichen, Phasen, Leistungsgrenzen, Steuer-Entitäten, Fehlerfall bei fehlenden Messwerten und Zusammenspiel mit anderen Automationen.
- Automatisierte und reale Integrationstests sind nicht als vollständig nachgewiesen dokumentiert.
