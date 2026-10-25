# Smartify Energy Pro

Home-Assistant-Integration zur Steuerung von PV-Überschuss mit Prioritäten, Prognosen und Batteriespeicherlogik.

Version: **0.2.3** · Integrationsdomain: `smartify_energy`

## Funktionen

- Konfiguration über die Home-Assistant-Oberfläche
- Netzleistung, PV-Prognosen und Batteriespeicher berücksichtigen
- Verbraucher, Pool, Elektroauto und Wärmepumpe als Untereinträge verwalten
- Integrierte Dashboard-Karte und deutsche sowie englische Übersetzungen

## Installation mit HACS

1. In HACS unter **Benutzerdefinierte Repositories** die URL `https://github.com/smartify-your-home/smartify-energy-pro` mit Kategorie **Integration** hinzufügen.
2. **Smartify Energy Pro** herunterladen und Home Assistant neu starten.
3. Unter **Einstellungen → Geräte & Dienste → Integration hinzufügen** nach **smartify Energiemanager** suchen und die Einrichtung durchführen.

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

## Warmwasser-Boost per Button

Als Boost-Art kann Schalter, Button oder Sollwert gewählt werden. Button unterstützt `button` und `input_button` und löst beim Start einmal `press` aus. Während der intern verwalteten Boost-Phase wird nicht erneut gedrückt. Ein Button liefert keinen Laufstatus und kann die Einmalladung nicht abbrechen: Zieltemperatur, Zeitlimit und Aus beenden nur die interne Freigabe; den tatsächlichen Ladezyklus beendet die Wärmepumpe. Nach Ende der internen Phase gilt die Mindestpause vor einer erneuten Auslösung.

## Boost-Startschutz (0.2.3)

Für jeden automatischen Warmwasser-Boost sind Leistungs- und Temperatursensor nötig. Die WP-Leistung muss durchgehend 15 Minuten unter der einstellbaren WP-Ruheschwelle (Standard 5 W) liegen. Aktivität oder ungültige Leistungswerte setzen die Wartezeit zurück; nach Neustart/Reload beginnt sie neu. Start nur unter Zieltemperatur minus Boost-Hysterese (Standard 4 K): bei 50 °C Ziel also unter 46 °C. Die bestehende Mindestpause und PV-Bedingungen gelten zusätzlich. Ein gestarteter Boost verbraucht die Ruhefreigabe.

Änderungen relevanter Eingänge lösen eine innerhalb von 2 Sekunden gebündelte Neubewertung aus. Der periodische Zyklus bleibt erhalten; Mittelwerte sind zeitgewichtet.
