# Installation und Updates

## WP-WW-Einmalladung: vereinfachte Modi (0.3.7)

Nur bei der WP-WW-Einmalladung heißen die Modi jetzt **Automatik**, **Beobachten** und **Deaktiviert**. Automatik löst den Boost nach den eingestellten Bedingungen aus; Beobachten zeigt nur Empfehlungen. Deaktiviert löst keinen neuen Boost aus und verändert weder den Auslöser noch eine bereits laufende WW-Ladung. Diese wird von der Wärmepumpe beendet. Bisher gespeicherte Werte Manuell und Aus werden beim Laden zu Deaktiviert zusammengeführt; auch alte interne Moduswerte bleiben ohne Startfreigabe.

Heizstab, andere Verbraucher und der WP-Boost über einen dauerhaften Zahlensollwert behalten ihre bisherigen Modi. Nach dem Update Home Assistant neu starten und das Dashboard neu laden.


## Heizstab: temperaturgeregelter Handbetrieb (0.3.6)

**Manuell** schaltet den Heizstab temperaturabhängig, auch mit Netzstrom. Bei 50 °C Soll und 1 K Hysterese startet er unter 49 °C, läuft bis 50 °C und schaltet dann ab. Solange Manuell gewählt bleibt, wird nach Abkühlung erneut geheizt; dies ist keine einmalige Nachladung. Zum Beenden **Aus**, für PV-Betrieb **Automatik** wählen.

PV-Start-/Stop-Schwellen, früheste Startzeit und die Pause nach Prioritätsrücknahme gelten nur in Automatik. Im Handbetrieb bleiben Mindestpause, Temperaturüberwachung und sofortige Abschaltung bei ungültiger Temperatur oder Geräte-/Hub-Aus aktiv. Die Mindestlaufzeit kann die Temperaturabschaltung nicht verzögern. Manuelle Heizleistung ist nicht für andere Geräte rücknehmbar; noch nicht gemessene Heizleistung wird vor PV-Freigaben reserviert. Andere Gerätetypen behalten ihr bisheriges manuelles Verhalten.

Nach dem Update Home Assistant neu starten und die Dashboard-Seite neu laden. **Achtung beim bisherigen Modus Manuell:** Dieser regelt den Heizstab ab jetzt aktiv; vor dem Update bei unerwünschter Nachheizung auf Aus stellen.


Aktuelle Version: **0.3.15**. Integrationsdomain: `smartify_energy`.

## Neu in 0.3.1
- Der SEP-Hub bietet zwei getrennte Einstellungen: **Mittelungszeit** (1–60 Minuten, Standard 20) und **Trendzeitraum** (1–30 Minuten, Standard 10). Zusätzlich ist die Trendtoleranz (Standard 100 W) einstellbar.
- Die Trendprüfung wartet nach Start oder Parameteränderung auf zwei vollständige Trendabschnitte. Bei zehn Minuten Trenddauer sind das 20 Minuten. Die Mittelung muss ebenfalls ausreichend gefüllt sein.
- Es werden nur automatische PV-Freigaben von Haushaltsgeräten blockiert; Sofortstart, Spätstart und laufende Programme bleiben unberührt.
- Ein bereits gespeicherter Mittelungswert (z. B. zehn Minuten) wird beim Update **nicht automatisch auf 20 Minuten überschrieben**. Dafür den SEP-Zahlenwert manuell anpassen.

## Neu in 0.3.4 – Lastverdrängung
- Ein nachrangiger Heizstab darf nur bei aktiv steuerbarem Schalter und abgelaufener Mindestlaufzeit zurückgenommen werden.
- Eine nachrangige Wallbox darf nur während freiwilligem PV-Laden und mit schaltbarem OFF-Aktor unterbrochen werden. Sofort- und Pflichtladung bleiben geschützt.
- Rücknahme wird **nicht** ohne bestätigende neue Netz-/Leistungsmesswerte als freie Leistung gebucht. Die automatische Haushaltsfreigabe benötigt weiterhin aktuelle Leistung, Durchschnitt und Trend.
- Bei unzureichender Summe der gemessenen rücknehmbaren Lasten findet keine vorsorgliche Abschaltung statt.
- Externe Überschusssenken/Ohmpilot wurden nicht verändert; keine neue Prioritätsintegration.
- Nach dem Update die realen Lasten und Prioritäten in einem sicheren Testlauf prüfen.

## Neu in 0.3.9
Die allgemeine SEP-Konfiguration zeigt den Akku-Rang nicht mehr als leeres Zahlenfeld. Der Rang bleibt bei den Prioritäten des PV-Akkus erhalten. Nach dem Schließen eines Einstellungsmenüs wird die Karte sofort aus dem letzten HA-Zustand aktualisiert. Nach Installation über HACS: Home Assistant und bei Bedarf die Dashboard-Ansicht neu laden.

## Neu in 0.3.10 – Trendanzeige
Haushaltsgeräte und WP-Boost zeigen unter ihrer Gerätebeschreibung einen Trendpfeil und „History · Trend“ in Minuten. Grün ↗ bedeutet positiver, rot ↘ negativer Budgettrend. Zwei vollständige Zeitfenster werden benötigt; davor zeigt die Karte ein Uhrsymbol. Änderungen an Trendzeit und Mittelung behalten vorhandene Messwerte (bis 60 min) bei. Ein Neustart von Home Assistant setzt die Arbeitsspeicher-Historie weiterhin zurück.

## SEP 0.3.11 – Neustart und persistente History
SEP schreibt die Messhistorie dauerhaft in seinen bestehenden HA-Speicher und kann sie nach einem kurzen Neustart wieder einlesen. Bei mehr als 2 Minuten Messunterbrechung wird der Trend aus Sicherheitsgründen neu aufgebaut. **Das erstmalige Update erfordert einen vollständigen Home-Assistant-Neustart**, weil HACS Python-Module im laufenden Prozess nicht zuverlässig austauschen kann. Für Änderungen nur an der JavaScript-Karte reicht normalerweise ein Neuladen des Dashboards.

## Neu in 0.3.12 – Trend nach Geräteleistung
Die Trendanzeige der Haushaltsgeräte und des WP-Boosts bewertet nun die erwartete Veränderung der jeweils verfügbaren Leistung gegenüber dem Leistungsbedarf des Geräts. Ein positives Vorzeichen alleine färbt den Pfeil nicht mehr grün; ein negativer Trend bei weiterhin ausreichendem Budget wird nicht rot dargestellt. Im Tooltip sind Referenzwert, Trendänderung und Schätzwert nach einem Trendfenster sichtbar. Dieser Schätzwert ist keine Wettervorhersage. Die eigentlichen Startbedingungen bleiben unverändert.

## SEP 0.3.13 – Drei getrennte Startprüfungen
Automatische PV-Freigabe bei WM/GS/Trockner und normalem WP-WW-Boost: (1) konfigurierter langer Mittelwert ≥ Gerätelast, (2) kurzer Trendmittelwert ≥ Gerätelast **oder** Verlauf nicht relevant fallend (Trendtoleranz), (3) aktuelles Gerätebudget ≥ Gerätelast. Alle drei müssen gültig sein. Für den Trend werden zwei vollständige Trendfenster benötigt. Die Anzeige zeigt den kurzen Mittelwert gegen Gerätebedarf. Sofort-/Spätstarts und die Sonderauslösung bei laufender WW-Bereitung bleiben unverändert.

## 0.3.14 – Fallender Trend verlangt Reserve
Im Kurztrend werden zwei unmittelbar aufeinanderfolgende Zeitfenster verglichen. Bei deutlich fallender Entwicklung wird für die Startfreigabe verlangt: Kurzmittel + Veränderung ≥ Gerätebedarf. Auch ein bereits ausreichend hoher Kurzmittelwert allein genügt dann nicht mehr. Bei neutralem oder steigendem Verlauf bleibt die Kurztrendbedingung erfüllt. Der längere Mittelwert und das Momentanbudget müssen unabhängig davon jeweils mindestens dem Gerätebedarf entsprechen. Diese Änderung betrifft automatische Haushaltsstarts und reguläre PV-WW-Boost-Starts.

## 0.3.15 – Klarere Zeitangaben
Die Gerätekarte zeigt die Mittelungszeit, die Trendzeit und die Länge der vorhandenen History separat als „Ø 16 min · Trend 2 min · Daten 38 min“ (Beispiel). Die gesamte gespeicherte Datenhistorie darf länger als die Mittelungszeit sein. Es ändert sich nur die Anzeige, nicht die Regelberechnung. Nach dem HACS-Update für die JavaScript-Karte das Dashboard neu laden.

## Update über HACS
1. Vor dem Update Home-Assistant-Backup erstellen und die bestehenden SEP-Geräteeinstellungen dokumentieren.
2. In HACS **Smartify Energy Pro** öffnen und die neue Version herunterladen. Falls sie nicht angeboten wird, Repository in HACS neu laden.
3. **Home Assistant neu starten**, damit Python-Code und Integrationsversion geladen werden.
4. Browser-/App-Ansicht des Dashboards neu laden. Wenn die Karte noch veraltet aussieht, den Frontend-Cache aktualisieren.
5. In **Einstellungen → Geräte & Dienste** die Integration und den Status aller Untereinträge prüfen; erst dann Automatik aktivieren.

HACS-Repository: https://github.com/smartify-your-home/smartify-energy-pro (Kategorie **Integration**). Es ist kein eigener JavaScript-Installationsschritt für die mitgelieferte SEP-Karte dokumentiert.

## Manuelles Update
Den gesamten Ordner `custom_components/smartify_energy` aus dieser Repository-Version nach `/config/custom_components/smartify_energy` kopieren (Dateien ersetzen), Home Assistant neu starten und Dashboard neu laden. Keine einzelnen Python-Dateien verschiedener Versionen mischen.

## Hinweise für 0.2.22–0.2.26
- **0.2.22:** PV-Akku kann in der Prioritätenliste verschoben werden; höher priorisierte Verbraucher erhalten gemessene Akkuladung als Budgetgutschrift, wenn der Speicher seine Ladung autonom reduziert. Akkuentladung bleibt vom PV-Budget abgezogen.
- **0.2.23:** WW-Boost-Zieltemperatur kann aus `sensor`, `number` oder `input_number` kommen. Bei Button-/Boolean-Boost wird der Wert **nicht** physisch zum Regler geschrieben; der Boolean muss bei Bedarf extern zurückgesetzt werden.
- **0.2.24:** Netzsaldo und Steuerbudget erhalten kompakte gemeinsame Ist-/Durchschnittsanzeigen.
- **0.2.25:** Offene Modus-Dropdowns schließen nicht mehr bei Sensordatenaktualisierung.
- **0.2.26:** Ø und akt. unter der Überschrift, Wattwerte rechtsbündig ausgerichtet.
- Nach HACS-Update immer HA neu starten und das Dashboard gegebenenfalls mit geleertem Browsercache neu laden, insbesondere bei JavaScript-Änderungen.
- [Funktionsbeschreibung der aktuellen Version](SEP_CURRENT.md)

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

## 0.2.13 – Grafische Prioritäten

Nach dieser Aktualisierung zeigen die Gerätekacheln die Priorität wieder als Zahl statt `?`. Die manuelle Prioritäten-Number-Entität bleibt entfernt. Zum Sortieren einen Geräte-Handle halten und an die gewünschte Position ziehen. Die Karte schreibt die neue Reihenfolge über den Dienst `smartify_energy.set_priority_order`; damit werden die Prioritäten im SEP-Gerätespeicher persistiert. Home Assistant nach dem Update neu starten und die Dashboard-Seite komplett neu laden, damit die neue JS-Karte aktiv wird.

## Wäschetrockner (0.2.27)

Für den neuen Gerätetyp **Wäschetrockner** die Nennleistung und Programmdauer passend zum eigenen Modell eintragen. Vor der Einstellung „Programm läuft nach Stromwiederkehr weiter“ den tatsächlichen Wiederanlauf nach Spannungsunterbrechung am Gerät sicher testen. Bei „Nein“ ist die SEP-Steckdosensteuerung gesperrt und es erfolgt ausschließlich eine Beobachtung nach manuellem Start. Bei „Ja“ darf SEP einmalig für eine spätere PV-Startfreigabe unterbrechen; ein freigegebenes Programm läuft unabhängig vom weiteren Überschuss durch. Test zunächst im Modus Beobachten und unter Aufsicht durchführen.

## 0.2.28 – Wiederherstellung bei `unavailable`

Behebt den Fehler `homeassistant.helpers.translation TypeError: expected str, got list` durch Korrektur der Übersetzungsoptionen für den Trockner. Nach dem Update Home Assistant vollständig neu starten; die Integration nicht löschen oder neu anlegen. Vorhandene SEP-Konfigurationen bleiben erhalten.

## 0.2.29 – Boost bei aktivem WW

Ist ein WW-Aktiv-Binärsensor konfiguriert und mindestens zehn Minuten ununterbrochen `on`, darf ein einmaliger Boost schon bei einem aktuellen, prioritätsbereinigten SEP-Steuerbudget ≥ 0 W ausgelöst werden. Temperaturbedingungen und optionaler Sonnenwinkelfilter sowie Startsperre gelten weiterhin. Ein Boost-Auslöser wird je laufendem WW-Zyklus maximal einmal betätigt. Die Number-Sollwertsteuerung bleibt unverändert. Für HACS ein Release mit dem Tag `0.2.29` auf `main` veröffentlichen und Home Assistant nach dem Update neu starten.

## 0.2.30 – WW-Aktiv-Wartezeit einstellen

Unter Gerätekonfiguration → Wärmepumpe Boost steht **WW aktiv: Wartezeit bis Boost** zur Verfügung: **0–180 Minuten (0 deaktiviert die Sonderfreigabe)**, Standard **10 Minuten**. Der Wert ist auch als Zahlen-Entität in den SEP-Geräteeinstellungen änderbar und bleibt nach einem Neustart erhalten. Bestehende Geräte verwenden weiterhin 10 Minuten. Die Wartezeit gilt nur für einmalige Button-/Schalter-/Boolean-Boosts bei laufender Warmwasserbereitung. Das aktuelle prioritätsbereinigte Steuerbudget muss ≥ 0 W sein; Temperatur, optionaler Sonnenwinkelfilter, Startsperre und höchstens ein Boost je WW-Zyklus gelten weiterhin. Nach dem HACS-Update Home Assistant neu starten.

## 0.2.31 – Keine Bewölkungsprüfung bei laufendem WW

Die Sonderfreigabe während aktiver WW-Bereitung ignoriert die Bewölkung der aktuellen und kommenden Stunde, auch bei unbekannten/nicht verfügbaren Bewölkungssensoren. Entscheidend für die Leistung ist ausschließlich das aktuelle prioritätsbereinigte Steuerbudget ≥ 0 W. Eingestellte Wartezeit (0 = deaktiviert), Temperatur unter Ziel minus Hysterese, optionaler Sonnenwinkelfilter, Startsperre und maximal eine Auslösung je WW-Zyklus bleiben wirksam. Bei normalen Boost-Starts und Number-Sollwertsteuerung bleiben die Bewölkungsfilter erhalten.

## 0.2.32 – Wahlweise Bewölkung oder PV-Forecast vor WW-Boost

In den **SEP-Geräteeinstellungen der Wärmepumpe** (auch als Konfigurationsentitäten auf der HA-Geräteseite) ersetzt **WW-Boost Startfilter** den bisherigen Bewölkung-Aktiv-Schalter:

| Auswahl | Wirkung bei normalem Boost-Start |
| --- | --- |
| Kein Filter | Keine Bewölkungs- oder Forecastprüfung |
| Bewölkung | Vorhandene Grenzen für aktuelle und kommende Stunde; wie bisher nur bei vollständig konfigurierten Entitäten/Grenzen |
| PV-Forecast | Erwartete PV-Energie muss die eingestellte Mindestenergie erreichen; Bewölkung wird ignoriert |

**PV-Forecast Zeitraum ab jetzt:** nächste 1 oder 2 Stunden (Standard 2). **PV-Forecast Mindestenergie:** 0,1–100 kWh (Standard 2 kWh). Quelle ist die bereits zentral in SEP konfigurierte PV-Prognose. Angebrochene Stunden werden entsprechend ihrem Anteil berücksichtigt: um 12:30 bedeutet „2 Stunden“ den Zeitraum bis 14:30. Gleichheit mit der Mindestenergie reicht aus.

Im Forecast-Modus verhindern fehlende Quellen, Fehler, ungültige/fehlende Stundenwerte oder über 60 Minuten alte Prognosedaten einen neuen Start; der Grund steht im Gerätestatus. Explizite 0-Wh-Stunden sind gültig, fehlende Stunden gelten nicht als Null. Prognoseenergie beschreibt Erzeugung, nicht verfügbaren Überschuss; die normale aktuelle/gemittelte Budgetprüfung bleibt bestehen. Bereits laufende Boosts werden durch den Filter nicht beendet.

**Sonderfreigabe während laufender WW-Bereitung:** weder Bewölkung noch PV-Forecast. Wartezeit (0 deaktiviert), Temperatur unter Ziel minus Hysterese, aktuelles prioritätsbereinigtes Budget ≥ 0 W, Startsperre, optionaler Sonnenwinkelfilter und höchstens ein Boost je WW-Zyklus bleiben wirksam. Normale Number-Boost-Starts verwenden ebenfalls den ausgewählten Startfilter.

**Update:** Ein bisher aktivierter Bewölkungsschalter wird automatisch zu „Bewölkung“, sonst zu „Kein Filter“. Die bisherigen Bewölkungsgrenzen bleiben gespeichert. Die zwei Forecast-Parameter wirken ausschließlich bei Auswahl „PV-Forecast“. Nach dem HACS-Update Home Assistant neu starten. Kein bestätigter Test an realer HA-Hardware.

## Update 0.3.0

Recorder-Entlastung, zuverlässige Neubewertung, Aktor-Timeouts und Verfügbarkeitsschutz, übersetzte ENUM-Statuscodes, Diagnose-Download sowie neue CI/Release-Pipeline. **Rohzustände ändern sich:** etwa `wartet` → `waiting`, `laeuft` → `running`. Bestehende IDs und deutsche Attribute bleiben erhalten. Vor dem Update Statusvergleiche in eigenen Templates/Automationen anpassen oder das Attribut `legacy_status` nutzen.

[Alle Änderungen und Migration](REVIEW_0.3.0.md). Nach dem Update Home Assistant neu starten. Mindestversion: **2025.7.0**.

