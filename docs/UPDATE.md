# Installation und Updates

Aktuelle Version: **0.2.10**. Integrationsdomain: `smartify_energy`.

## Update über HACS
1. Vor dem Update Home-Assistant-Backup erstellen und die bestehenden SEP-Geräteeinstellungen dokumentieren.
2. In HACS **Smartify Energy Pro** öffnen und die neue Version herunterladen. Falls sie nicht angeboten wird, Repository in HACS neu laden.
3. **Home Assistant neu starten**, damit Python-Code und Integrationsversion geladen werden.
4. Browser-/App-Ansicht des Dashboards neu laden. Wenn die Karte noch veraltet aussieht, den Frontend-Cache aktualisieren.
5. In **Einstellungen → Geräte & Dienste** die Integration und den Status aller Untereinträge prüfen; erst dann Automatik aktivieren.

HACS-Repository: https://github.com/smartify-your-home/smartify-energy-pro (Kategorie **Integration**). Es ist kein eigener JavaScript-Installationsschritt für die mitgelieferte SEP-Karte dokumentiert.

## Manuelles Update
Den gesamten Ordner `custom_components/smartify_energy` aus dieser Repository-Version nach `/config/custom_components/smartify_energy` kopieren (Dateien ersetzen), Home Assistant neu starten und Dashboard neu laden. Keine einzelnen Python-Dateien verschiedener Versionen mischen.

## Besonderheiten von 0.2.8
- Der Strom einer laufenden PV-Wallbox folgt dem **momentanen** Restüberschuss. Vorher wurde für die Regelung ein 2-Minuten-Mittelwert verwendet.
- Eingangsmesswert-Änderungen können intern nach rund **0,5 Sekunden** eine Prüfung auslösen, sofern die Entität in SEP konfiguriert und überwacht wird. Das ist **keine garantierte Ladegeräte-Reaktionszeit**.
- Start der PV-Ladung verwendet weiterhin Glättung; bei Unterschreitung des Mindestladestroms bleibt die Stop-Verzögerung aktiv.
- Nach dem Update Netzbezug, Ladestrom in Ampere, Anzahl Phasen, Überschuss und Prioritäten unter wechselnder Einstrahlung beobachten.
- Der Batteriespeicher wird weiterhin nicht aktiv auf einen Ladeleistungs-Sollwert geregelt.

## Empfohlener Funktionstest
1. SEP zunächst im Beobachtungsmodus prüfen, ob Netzleistungs-Vorzeichen und momentaner Überschuss plausibel sind.
2. Nur mit beaufsichtigtem Auto im Modus **Nur PV** testen; Wallbox-Mindeststrom, maximalen Strom und Phasenwerte prüfen.
3. Bei stark sinkendem Überschuss sicherstellen, dass der Sollstrom reduziert wird und die konfigurierte Stop-Verzögerung wie erwartet greift.
4. Prüfen, ob der Akku entsprechend der Prioritätsstrategie berücksichtigt wird, aber **keinen** ungewollten Schreibbefehl erhält.
5. Andere laufende Haushaltsgeräte, Wärmepumpe und Hauptschalter separat prüfen.

## Rückweg bei Problemen
Automatik zuerst in den Beobachtungs- bzw. sicheren manuellen Betrieb versetzen. Danach Backup bzw. letzte funktionierende HACS-Version wiederherstellen und Home Assistant neu starten. Dabei Konfiguration und Gerätezustände kontrollieren; „Aus“ ist kein elektrischer Not-Aus.

## Weitere Infos
- [Änderungsprotokoll](../CHANGELOG.md)
- [Repository und README](../README.md)
- [Probleme melden](https://github.com/smartify-your-home/smartify-energy-pro/issues)

## Besonderheiten von 0.2.9 – Haushaltsgeräte

Bei neuen Haushaltsgeräten gelten SEM-v3-nahe Standardwerte: Mindestüberschuss **+1.500 W** (aktuelle Korrektur; zuvor −1.000 W), späteste Startzeit 16:00, Fertigerkennung 2 Minuten. Bereits gespeicherte Werte werden nicht automatisch überschrieben. Nach dem Update prüfen, ob Start, Heizphase, Unterbrechung bei fehlender Erstfreigabe, Warten, Freigabe und Reset wie vorgesehen funktionieren. Insbesondere echte Steckdosen und Geräte zunächst nur beaufsichtigt testen.

## Name in Home Assistant

Ab der aktuellen Repository-Fassung lautet der Integrationsname **Smartify Energy Pro**. Die technische Domain `smartify_energy` bleibt unverändert. Nach dem Update Home Assistant neu starten. Ein bereits angelegter Eintrag kann seinen alten individuell gespeicherten Namen behalten; diesen bei Bedarf in Geräte & Dienste umbenennen. Es ist keine Neuinstallation notwendig.

## Neu in 0.2.10

Haushaltsgeräte: `Frühester automatischer Start` (Standard `00:00`) vor automatischen Freigaben, einschließlich Spätstart und Sofortfenster. `Sofort-Start` per Taste bleibt manuell möglich. Prioritäts-Number-Entities aller Geräte werden nicht mehr bereitgestellt; bisher gespeicherte Prioritäten bleiben intern unverändert. Bereits bestehende Prioritäts-Entities können nach dem Update als nicht mehr bereitgestellt markiert werden und bei Bedarf aus der Entitätsregistrierung entfernt werden. Die grafische Prioritätensteuerung ist noch nicht implementiert.
