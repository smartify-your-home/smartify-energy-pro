# SEM v3 → Smartify Energy Pro: Entitäten

Stand: SEP **0.2.18**. Grundlage: `smartify-your-home/smart_energy_manager` und `smartify-your-home/smartify-energy-pro` auf `main`.

## Wichtiger Unterschied

SEM v3 erzeugte einige Entitäts-IDs **explizit** mit `sem_v3` und dem aus dem Gerätenamen gebildeten `nid`, beispielsweise `number.sem_v3_waschmaschine_nennleistung`.

SEP erzeugt Home-Assistant-Entitäten unter eigenen Geräten und verwendet **übersetzte Anzeigenamen** und dauerhafte Unique-IDs aus `<Config-Entry-ID>_<Subentry-ID>_<Parameter-Key>`. **Die tatsächlichen `entity_id` werden von Home Assistant vergeben**, nicht von SEP als `<domain>.smartify_energy_<nid>_<key>` festgeschrieben. Sie können sich abhängig von Sprache, früheren Integrationen, eigenen Umbenennungen und Kollisionen unterscheiden; Suffix `_2` ist möglich. Deshalb enthalten die rechten Spalten unten **Anzeigenamen/Keys**, keine garantiert exakten IDs.

## Hub / global

| SEM v3 | SEP 0.2.18 | Änderung |
|---|---|---|
| `switch.sem_v3_master` | `select` am SEP-Hub, **Modus** (`mode`) | Kein einfacher Hauptschalter mehr; Auswahl Automatik/Beobachten/Aus |
| `number.sem_v3_window_start_h` + `_window_start_m` | `time` **Sofortfenster Beginn** (`night_start`) | Ein Uhrzeitfeld statt 2 Zahlen |
| `number.sem_v3_window_end_h` + `_window_end_m` | `time` **Sofortfenster Ende** (`night_end`) | Ein Uhrzeitfeld statt 2 Zahlen |
| SEM-Saldo aus dem konfigurierten Netzsensor | `sensor` **Tatsächlicher Netzüberschuss** (`surplus`) | Vorzeichen + Einspeisung, − Bezug, eigener Hub-Sensor |
| Kein separat gleichwertiger Wert | `sensor` **Verfügbares Steuerbudget** (`budget`) | Rechenbudget ausdrücklich getrennt vom Netzsaldo |
| Kein separat gleichwertiger Wert | `sensor` **Steuerbudget Mittelwert** (`budget_avg`) | Geglättetes Budget, konfigurierbares Zeitfenster |

## Pro Haushaltsgerät

| SEM v3 | SEP 0.2.18 | Änderung |
|---|---|---|
| `number.sem_v3_<nid>_nennleistung` | `number` **Nennleistung** (`nominal_power`) | Heizleistung und Reservierung |
| `number.sem_v3_<nid>_min_surplus` | `number` **Mindest-Überschuss** (`min_surplus`) | PV-Start benötigt mindestens **max(Nennleistung, Mindest-Überschuss)** |
| `number.sem_v3_<nid>_fertig_schwelle` | `number` **Fertig-Schwelle** (`finish_threshold`) | Name/Key geändert |
| `number.sem_v3_<nid>_fertig_dauer` | `number` **Fertig-Dauer** (`finish_minutes`) | Name/Key geändert |
| `number.sem_v3_<nid>_latest_h` + `_latest_m` | `time` **Spätester Start** (`latest_start`) | Ein Uhrzeitfeld |
| Nicht vorhanden | `time` **Frühester Start** (`earliest_start`) | Neue Option |
| `switch.sem_v3_nachladen_<nid>` | `switch` **Nachladen** (`nachladen`) | HA-generierte ID statt fester SEM-ID |
| SEM **Fertig**-Schalter | `binary_sensor` **Fertig** (`finished`) + `button` **Reset** (`reset`) | Fertig ist ein Sensor, Rücksetzen geschieht über Reset-Taste |
| SEM **Wartet**-Binary | `binary_sensor` **Wartet** (`waiting`) | Gleiche Bedeutung, neue eindeutige Identität |
| SEM **Heizphase**-Binary | `binary_sensor` **Heizphase** (`heating`) | Gleiche Bedeutung, neue eindeutige Identität |
| SEM **Läuft**-Binary | `sensor` **Zustand** (`phase`, Wert `laeuft`) + `binary_sensor` **Aktiv** (`active`) | `active` bedeutet physische Freigabe/Steckdose EIN, nicht zwingend das SEM-`RUNNING`-Flag |
| SEM **PV freigegeben**-Binary | `sensor` **Status** (`status`) / Attribut `grund` | Kein eigener gleichnamiger Binary-Sensor |
| SEM **Nachtfenster**-Binary | Hub-Uhrzeiten **Sofortfenster Beginn/Ende** | Kein eigenes Nachtfenster-Flag je Gerät |
| SEM **Sofortstart**-Taste | `button` **Sofort starten** (`start_now`) | Weiter vorhanden |

Die Haushaltsgeräte **benutzen weiterhin die von dir konfigurierten Steckdosen und Leistungssensoren**. Deren ursprüngliche `switch.`-/`sensor.`-IDs werden nicht automatisch umbenannt, wenn du statt SEM jetzt SEP zur Steuerung nutzt.

### Bestehende Automationen umstellen

Unter **Einstellungen → Geräte & Dienste → Smartify Energy Pro → Gerät → Entitäten** die *wirklich vergebenen* IDs aufrufen oder über **Entwicklerwerkzeuge → Zustände** nach Gerätename und Entitätsname suchen. Alte `sem_v3`-IDs werden durch SEP nicht automatisch übernommen und auch nicht als Alias angelegt. Für Automationen, Templates und Lovelace-Karten die neuen IDs gezielt auswählen.

## Heizphasenlogik seit 0.2.18

Jedes PV-freigegebene Haushaltsgerät reserviert vor Abschluss seiner Heizphase die Nennleistung, abzüglich des tatsächlich gemessenen aktuellen Verbrauchs. Ein anderes wartendes oder gerade erkanntes Gerät kann **parallel starten**, wenn sowohl sein aktuelles verfügbares Budget als auch der gemittelte Wert die gesamte zukünftige Heizleistung decken. Der bislang starre Ausschluss bei laufender anderer Heizphase entfällt. Nach abgeschlossenem Heizen fällt die Reservierung fort; der konfigurierte Mittelwert muss sich trotzdem wieder erholen. Sofortfenster und Spätstart dürfen weiterhin ausdrücklich unabhängig von PV freigeben.
