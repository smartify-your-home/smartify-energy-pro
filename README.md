# Smartify Energy Pro

Home-Assistant-Integration **Smartify Energy Pro** zur Steuerung von PV-Überschuss mit Prioritäten, Prognosen und Batteriespeicherlogik.

Version: **0.2.17** · Integrationsdomain: `smartify_energy`

## Dokumentation und Updates

- [Änderungsprotokoll (0.2.8 und Vorgängerversionen)](CHANGELOG.md)
- [Update-Anleitung und Funktionstest](docs/UPDATE.md)
- [Funktionsstand und bekannte Grenzen](docs/FUNCTIONS.md)
- [Pflichtfelder, optionale und bedingte Entitäten je Funktion](docs/REQUIRED_FIELDS.md)

## Funktionen

- Konfiguration über die Home-Assistant-Oberfläche
- Netzleistung, PV-Prognosen und Batteriespeicher berücksichtigen
- Verbraucher, Pool, Elektroauto und Wärmepumpe als Untereinträge verwalten
- Integrierte Dashboard-Karte und deutsche sowie englische Übersetzungen

## Installation mit HACS

1. In HACS unter **Benutzerdefinierte Repositories** die URL `https://github.com/smartify-your-home/smartify-energy-pro` mit Kategorie **Integration** hinzufügen.
2. **Smartify Energy Pro** herunterladen und Home Assistant neu starten.
3. Unter **Einstellungen → Geräte & Dienste → Integration hinzufügen** nach **Smartify Energy Pro** suchen und die Einrichtung durchführen.

## Manuelle Installation

Den Ordner `custom_components/smartify_energy` nach `/config/custom_components/smartify_energy` kopieren, Home Assistant neu starten und die Integration über die Oberfläche hinzufügen.

## Dashboard

Die Integration stellt die Dashboard-Karte automatisch bereit. Beispiel für eine manuelle Karte:

```yaml
type: custom:smartify-energy-plan-card
```

## Hinweise

Die Integration nutzt aktuelle Home-Assistant-Schnittstellen, unter anderem Konfigurations-Untereinträge. Eine Laufzeitprüfung in Home Assistant steht noch aus. Änderungen an der Verbrauchersteuerung zunächst mit passenden Testgeräten prüfen.

Fehler und Verbesserungsvorschläge: [Issues](https://github.com/smartify-your-home/smartify-energy-pro/issues).

## Warmwasser-Boost: ein Start, Wärmepumpe übernimmt den Zyklus (0.2.17)

SEP kann für **Warmwasser aktiv** optional einen bestehenden `binary_sensor` oder `input_boolean` auswählen (unter **Wärmepumpe → Neu konfigurieren**). **EIN** bedeutet WW läuft: Ein weiterer Boost wird dann nicht ausgelöst. Wenn das Feld nicht belegt ist, schützt weiterhin die Leistungs-Ruheerkennung zusammen mit der Startsperre. Ist das Feld belegt, aber die Entität nicht verfügbar, löst SEP aus Sicherheitsgründen nichts aus.

Bei **Button** (`button` / `input_button`) sendet SEP einmal `press`; bei **Schalter** (`switch` / `input_boolean`) einmal `turn_on`. SEP sendet bei diesen Einmalstartern **kein `turn_off`** zum Beenden des WW-Zyklus; die Wärmepumpe steuert die eigentliche Ladung selbst. Ein Schalter, der auf EIN stehen bleibt, verhindert weitere Startbefehle und muss extern wieder auf AUS zurückgehen. Sollwert-/Number-Boosts bleiben davon verschieden, da dort ein Normal-Sollwert zurückgesetzt werden muss.

Die Geräteeinstellung **WW-Boost Mindestabstand** ist standardmäßig **60 min** und lässt sich von **60 bis 720 min** einstellen. **Unter 60 Minuten ist nicht erlaubt**, damit maximal ein Start pro Stunde erfolgt. Vor dem Startbefehl speichert SEP den letzten Startzeitpunkt sofort dauerhaft in Home Assistant. Nach HA-Neustart läuft die Restzeit weiter; auch ein unklarer Aktorfehler hebt die Sperre nicht auf.

## Boost-Startschutz (0.2.3)

Für jeden automatischen Warmwasser-Boost sind Leistungs- und Temperatursensor nötig. Die WP-Leistung muss durchgehend für die einstellbare „WP-Ruhezeit vor Boost“ (1–180 Minuten, Standard 15 Minuten) unter der einstellbaren WP-Ruheschwelle (Standard 5 W) liegen. Aktivität oder ungültige Leistungswerte setzen die Wartezeit zurück; nach Neustart/Reload beginnt sie neu. Start nur unter Zieltemperatur minus Boost-Hysterese (Standard 4 K): bei 50 °C Ziel also unter 46 °C. Der dauerhafte Mindestabstand seit der letzten WW-Auslösung und die PV-Bedingungen gelten zusätzlich. Ein gestarteter Boost verbraucht die Ruhefreigabe.

Seit 0.2.8 lösen ausgewählte Leistungs- und Wallbox-Messwerte nach etwa 0,5 Sekunden eine gebündelte Neubewertung aus; sonstige beobachtete Eingänge bleiben bei ungefähr 2 Sekunden. Der periodische Zyklus bleibt erhalten; Mittelwerte sind zeitgewichtet.

## Verständliche Einstellungen (0.2.5)

Die deutsche Einrichtung und Gerätekonfiguration erklärt jedes Feld direkt darunter. In der SEP-Karte stehen unter jeder Einstellung im Zahnrad-Menü verständliche Hinweise mit Beispielen; auch Modus und Priorität sind dort enthalten. Die Erklärungen sind ohne Maus-Hover auf Handy und Tablet lesbar. Der Karteneditor erklärt seine Anzeigeoptionen ebenfalls.

## Hauptschalter Aus (0.2.6)

Beim zentralen Ausschalten schaltet SEP die Steckdosen aller angelegten Haushaltsgeräte einmal ein und setzt deren Programmerkennung zurück. Danach bleiben manuelle Schaltbefehle möglich. Bei erneutem Ausschalten sowie beim Laden der Integration mit Hauptmodus Aus erfolgt die Freigabe erneut. Dies gilt für Haushaltsgeräte, nicht für Pool, Wallbox oder Wärmepumpe. Die Steckdose liefert Strom; ob das angeschlossene Gerät sein Programm fortsetzt, hängt vom Gerät ab.

## Optionale Boost-Startbedingungen (0.2.7)

In der Gerätekonfiguration der Wärmepumpe können ein Sonnenhöhen-Sensor und zwei Bewölkungssensoren (aktuelle/kommende Stunde) mit optionalen Grenzwerten ausgewählt werden. Beide Prüfungen haben im Zahnrad-Menü einen eigenen Aktiv-Schalter; anfangs sind sie aus. Grenzwerte lassen sich dort ebenfalls einstellen. Fehlende Entitäten oder Grenzwerte deaktivieren die jeweilige Prüfung; bei Bewölkung müssen beide Entitäten und beide Grenzen vorhanden sein.

Beispiel: Sonnenhöhe mindestens 12° (12° erlaubt), Bewölkung aktuell unter 75 % und kommende Stunde unter 50 % (Gleichheit sperrt). Sind beide Prüfungen aktiv und vollständig, müssen beide erfüllt sein. Ungültige Messwerte einer wirksamen Prüfung sperren neue Starts. Die zusätzlichen Bedingungen stoppen keinen bereits laufenden Boost. Die bisherigen Bedingungen für Überschuss, Temperatur und Ruhezeit gelten weiterhin. Der Gerätestatus zeigt unter boost_startbedingungen, ob eine Prüfung wirkt oder ignoriert wird.

Die Entitäten müssen Zahlenzustände liefern; die Bewölkungssensoren müssen selbst stets die aktuelle bzw. kommende Stunde bereitstellen. Das ist eine zusätzliche Startfreigabe und keine automatische Wahl des besten Prognose-Zeitfensters.

## Schnelle Wallbox-Regelung (0.2.8)

Bei Änderungen am Netzleistungs-, Batterie-Leistungs- oder Wallbox-Leistungssensor wird die Neubewertung nach etwa 0,5 Sekunden gebündelt angestoßen (andere Ereignisse bleiben bei etwa 2 Sekunden). Die laufende Wallbox passt ihren Ladestrom anhand des **aktuellen** verfügbaren Überschusses statt des 2-Minuten-Mittelwerts an; höhere priorisierte Reservierungen werden weiterhin berücksichtigt. Der Kurzzeitmittelwert dient nur noch als zusätzliche Startbedingung. Stromschritte bleiben durch die Auflösung der Wallbox auf ganze Ampere begrenzt. Bei zu wenig Überschuss reduziert SEP unmittelbar auf den Mindeststrom; die konfigurierbare Abschaltverzögerung gilt weiterhin. Die tatsächliche Reaktion hängt von der Aktualisierung der Sensoren, Service-Laufzeit und Wallbox ab.

**Batterie:** SEP berücksichtigt Speicherleistung, SoC, Prognose und Strategie bei der Überschussverteilung, steuert jedoch aktuell **keinen Akku-Ladesollwert**. Die schnellere Messwertauswertung bedeutet daher noch keine direkte Akku-Laderegelung. Vor einer solchen Erweiterung müssen geeignete schreibbare Akku-Entitäten bekannt sein.

## Haushaltsgeräte: SEM-v3-Abgleich (0.2.9)

Die Zustandsmaschine wurde anhand der bereitgestellten SEM-v3-Integration abgeglichen: 5 Sekunden stabile Leistung über 9 W zur Programmerkennung (ohne Leistungssensor bei eingeschalteter Steckdose), 10 Sekunden über max(200 W, 8 % Nennleistung) zur Heizphasenerkennung, 2 Minuten unter der einstellbaren Fertigschwelle als Standard, standardmäßige Spätstartzeit 16:00 und Zustand „Fertig“ bis zum manuellen Reset. Bereits ausdrücklich freigegebene Programme werden nicht wegen später sinkenden Überschusses gestoppt. SEP behält jedoch die zentral einstellbaren Prioritätszahlen anstelle der ausschließlich zeitlichen Reihenfolge von SEM. Neue Standardwerte betreffen neue Einträge; bereits gespeicherte Parameter bleiben bestehen. Eine Prüfung mit echten Geräten steht aus.

## Mindestüberschuss für Haushaltsgeräte

Der Standardwert für **neu angelegte** Haushaltsgeräte lautet **+1.500 W**: Erst bei einem berechneten Überschuss von mindestens 1.500 W ist die PV-Startbedingung erfüllt. Bereits gespeicherte Geräteparameter werden durch Updates nicht automatisch geändert. Vorhandene Geräte bei Bedarf manuell auf +1.500 W einstellen.

### Startzeit und Priorität

Haushaltsgeräte haben eine **früheste automatische Startzeit** (Standard 00:00). Vor dieser Uhrzeit erfolgt keine automatische Freigabe – auch nicht durch Spätstart oder Sofortfenster. Ein ausdrücklich gedrückter **Sofort-Start** bleibt möglich. Die bisherigen Prioritäts-Nummern werden nicht mehr als Einstellungs-Entitäten angezeigt; die Prioritätslogik bleibt intern für die spätere grafische Anordnung erhalten.

**Prioritäten:** Die Prioritäts-Zahlen-Entitäten sind bewusst nicht mehr sichtbar. Die grafische Übersicht zeigt die intern gespeicherte Priorität aus dem Gerätestatus; per Drag & Drop wird die Reihenfolge über `smartify_energy.set_priority_order` dauerhaft gespeichert.
