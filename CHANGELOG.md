## 0.2.13 – Prioritätsanzeige und Drag & Drop repariert
- Fehler korrigiert: Nach Entfernung der Prioritäts-Zahlen-Entitäten zeigte die grafische Übersicht für jedes Gerät `?` und erwartete nicht mehr vorhandene Entitäten.
- Geräte werden jetzt aus ihrem Status ermittelt und die gespeicherte Priorität als Zahl aus dem Statusattribut `prioritaet` angezeigt.
- Die Reihenfolge wird über den eigenen Dienst `smartify_energy.set_priority_order` gespeichert. Eine sichtbare `number.priority`-Entität wird dafür nicht mehr benötigt.

## 0.2.12 – Bezeichnung der Startzeiten
- Haushaltsgeräte: Anzeigename der Zeit-Entität auf **„Frühester Start“** vereinheitlicht; **„Spätester Start“** bleibt bestehen.
- Keine Änderung der technischen Entitätsschlüssel oder gespeicherten Zeitwerte.

## 0.2.11 – Planungsanzeige bei Moduswechsel
- Fehler behoben: Nach dem Schalten eines Geräts (z. B. WP-Boost) auf „Aus“ wird die grafische Prognoseplanung unmittelbar neu berechnet; veraltete Boost-Balken bleiben nicht bis zum nächsten 15-Minuten-Planungsintervall stehen.
- Regelmäßiger Prognose-Abruf bleibt im bisherigen Intervall; eine Einstellungsänderung erzwingt nur die Neuplanung.

## 0.2.10 – Startzeit und grafische Priorisierung vorbereiten
- Haushaltsgeräte: neue einstellbare Uhrzeit **Frühester automatischer Start** (Standard 00:00). Sperrt automatische PV-, Spätstart- und Sofortfensterfreigabe bis zur Uhrzeit. Manueller Sofort-Start bleibt möglich.
- Prioritätseingaben (number-Entities) aller Gerätetypen aus der angezeigten Parameterauswahl entfernt. Gespeicherte Prioritäten bleiben erhalten und werden intern berücksichtigt; grafische Bedienung folgt separat.

# Änderungsprotokoll – Smartify Energy Pro

## Anzeigename (26.10.2026)
- Anzeigename in Home Assistant (Manifest und Standardname) auf **Smartify Energy Pro** vereinheitlicht. Die Integrationsdomain `smartify_energy` bleibt für bestehende Installationen unverändert. Vorhandene, individuell benannte Integrationseinträge behalten unter Umständen ihren bisherigen Eintragstitel; diese können in Home Assistant umbenannt werden.


Die Versionsnummer bezeichnet die Home-Assistant-Integration. Angaben zur Reaktionszeit beziehen sich auf die interne Planung und sind **keine garantierten Hardware-Schaltzeiten**. Eine Prüfung an einer realen Home-Assistant-Anlage steht noch aus.

## Korrektur des Standardwerts (26.10.2026)
- Mindestüberschuss bei **neu angelegten Haushaltsgeräten** jetzt **+1.500 W** statt −1.000 W. Bestehende Einstellungen werden nicht überschrieben. Die übrigen SEM-v3-Zustandsregeln bleiben unverändert.

## 0.2.9 – Haushaltsgeräte an SEM v3 angeglichen (26.10.2026)
- Programmerkennung bei eingeschalteter Steckdose nun erst nach 5 Sekunden stabil über 9 W (ohne Sensor über den Schaltzustand).
- Abschlusszustand „Fertig“ bleibt bis zum ausdrücklichen Reset erhalten; kein automatischer Neustart allein durch wieder steigende Leistung.
- Standardwerte für **neue** Haushaltsgeräte aus SEM v3: Mindestüberschuss -1000 W, Spätstart 16:00, Fertigerkennung 2 Minuten; Heizphasenerkennung > max(200 W, 8 % Nennleistung) über 10 Sekunden.
- Bei erstem Leistungsanstieg >100 W wird die Freigabe geprüft; bereits freigegebene Programme laufen weiter.
- Unterschied zur SEM-Vorlage: SEP verwendet die manuell festgelegten Geräteprioritäten anstelle der ausschließlich zeitlichen Reihenfolge. Die 10-Minuten-Mittelwertprüfung und Heizphasen-Sperre für wartende Geräte bleiben erhalten.
- Diese Änderungen sind im Repository umgesetzt, aber **nicht auf einer realen HA-Installation getestet**.
- Bei bestehenden Geräten bleiben bereits gespeicherte Parameterwerte unverändert.

## 0.2.8 – Schnellere Wallbox-Regelung (26.10.2026)
- Änderungen des Netzleistungssensors, des konfigurierten Speicher-Leistungssensors sowie von Wallbox-Leistungs- und Stromsensoren stoßen eine gebündelte Neubewertung mit ca. 0,5 s Verzögerung an; andere verfolgte Entitäten weiterhin ca. 2 s. Der reguläre Zyklus läuft zusätzlich.
- Eine bereits laufende PV-Ladung berechnet ihren Strom nun aus dem momentanen Restbudget einschließlich vorrangiger Reservierungen, nicht länger aus dem geglätteten 2-Minuten-Wert.
- Bei fallendem Überschuss wird der Sollstrom soweit möglich bis zum konfigurierten Mindeststrom reduziert. Darunter bleibt die Abschaltverzögerung wirksam; dadurch kann vorübergehend Netzbezug entstehen.
- Beim PV-Ladestart bleibt eine geglättete Startbedingung bestehen. Stromregelung erfolgt in ganzen Ampere; die Phasenumschalt-Sperrzeit bleibt bestehen.
- **Keine direkte Speicher-Ladestromsteuerung** implementiert. SoC, Speicherleistung, Prognose und Priorität fließen in die Verteilung ein.

## 0.2.7 – Optionale WP-Boost-Startfilter
- Optionaler Mindest-Sonnenhöhenwinkel und getrennte Obergrenzen für Bewölkung dieser und der kommenden Stunde.
- Eigene Aktivierung pro Filter; fehlende Einstellungen deaktivieren den jeweiligen Filter.
- Vollständig aktivierte Filter sperren neue Starts bei ungültigen Messwerten; laufende Boosts bleiben davon unberührt.
- Beschreibung und Diagnosewerte im Gerät ergänzt.

## 0.2.6 – Zentraler Modus Aus
- Beim Ausschalten des Hauptschalters werden Steckdosen angelegter Haushaltsgeräte freigegeben und deren Programmerkennung zurückgesetzt; nicht für Pool, Wallbox und WP.

## 0.2.5 – Erklärungen in der Bedienoberfläche
- Deutsche Hilfetexte bei Einrichtung, Gerätekonfiguration, Parametern und Priorität; Bedienung auch ohne Hover.

## 0.2.4 – WP-Ruhezeit einstellbar
- Ruhezeit vor Boost von festen 15 Minuten auf einstellbare 1–180 Minuten geändert; Standard weiterhin 15 Minuten.

## 0.2.3 – Boost-Startschutz und Ereignisreaktion
- Leistungs-/Temperaturprüfung, WP-Ruhezeit und Hysterese vor Boost.
- Bei Änderungen relevanter Sensoren gebündelte Neuberechnung nach ungefähr 2 Sekunden ergänzt.

## Bekannte Grenzen
- Keine bestätigten Integrationstests auf produktivem Home Assistant; vor dem Automatikbetrieb mit realen Verbrauchern sorgfältig testen.
- Schnellere interne Berechnung garantiert keine Antwortzeit der Wallbox oder des Akkus.
- 6-A-Mindeststrom (oder abweichend konfigurierter Mindestwert), Abschaltverzögerung und Phasenwechsel-Sperre können kurzfristigen Netzbezug verursachen.
- Die Akku-Priorität ist eine Budgetentscheidung, keine Schreibschnittstelle zum Batterie-Wechselrichter.
