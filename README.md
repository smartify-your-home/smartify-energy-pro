# Smartify Energy Pro

Home-Assistant-Integration zur Steuerung von PV-Überschuss mit Prioritäten, Prognosen und Batteriespeicherlogik.

Version: **0.2.2** · Integrationsdomain: `smartify_energy`

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
