**Neu: Abwesenheit (optional):** Beim temperaturgeregelten Heizstab und Wärmepumpen-WW-Boost kann je ein `binary_sensor` oder `input_boolean` für Abwesenheit hinterlegt werden (`on` = abwesend). Bei Abwesenheit stoppt der Heizstab auch im Handbetrieb; Number-WW-Boost wird zurückgenommen und Einmal-WW-Starts werden verhindert. Bereits laufende WP-eigene WW-Zyklen bleiben unberührt. Nach Rückkehr gelten wieder die bisherigen Regeln.


**Budget-Reaktionszeit (0.3.52):** Netz-, Akku- und Geräteleistungen werden nach einer kurzen Bündelung von 0,25 Sekunden neu bewertet. Ein bereits geplanter langsamer Zyklus kann vorgezogen werden; Gerätemoduswechsel werden ohne absichtliche Wartezeit bewertet. Die individuellen aktuellen Budgets in der Gerätezeile sind Momentanwerte. Bestehende Hysterese, Schutzzeiten sowie Trend-/Mittelwertprüfungen für automatische Starts bleiben erhalten.

# Smartify Energy Pro

## Neue optionale eigene PV-Prognose (My-Weather)

Unter **Einstellungen → Geräte & Dienste → Smartify Energy Pro → Konfigurieren → Prognose** gibt es zwei Modi:

- **Externe Prognose (Standard):** unveränderte Forecast.Solar-/Solcast-/Sensor-Prognose.
- **Eigene Berechnung:** Standortkoordinaten aus Home Assistant und Bewölkung über
  `Meteonomiqs Cloud Forecast 48h` aus My-Weather (für die längere Prognose; der bisherige 8h-Sensor funktioniert weiterhin). Im Auswahlfeld den *wirklichen*
  Entity-ID des neuen My-Weather-Sensors wählen. Die Daten liegen im Attribut
  `forecast` mit UTC-Zeitstempel und `cloud_coverage` (0 bis 100 %). Nach dem My-Weather-Update unter SEP → Konfigurieren → Prognose den **neuen 48h-Sensor** auswählen, sonst bleibt SEP beim bisherigen 8h-Horizont.

Bis zu **vier getrennte PV-Flächen** können konfiguriert werden. Pro Fläche:
*installierte Peakleistung in kWp*, *Dachneigung* (0° flach bis 90° senkrecht),
*Azimut* (0° Nord, 90° Ost, 180° Süd, 270° West).
Leere Flächen werden ignoriert; die Summe der kWp entspricht der installierten
Gesamt-PV-Leistung. Vorhandene SolarEdge-/Balkon-Flächen nicht doppelt erfassen.

Die Berechnung benutzt Sonnenstand, Ausrichtung und eine vereinfachte
wolkenabhängige Einstrahlungs-/Verlustschätzung. Ihr Ergebnis wird in die
bestehenden **SEP-PV-Prognose-Kacheln und Planungswerte** (stündliche Wh)
eingespeist, ohne den gemessenen Netzsaldo oder die unmittelbaren
Start-/Stoppschutzbedingungen zu ersetzen. Die verfügbaren stündlichen Wolkendaten (bis zu 48 Stunden) begrenzen
den Vorhersagehorizont; für Zeiträume ohne gültige Bewölkungswerte
werden keine vermeintlich sonnigen Stunden ergänzt. PV-Prognosen sind
Schätzungen, bei Nebel/Hochnebel besonders unsicher. Kein zusätzlicher
Meteonomiqs-API-Aufruf durch SEP.

### Optionale automatische Kalibrierung

Im SEP-Prognose-Schritt **PV-Prognose automatisch kalibrieren** aktivieren und
**PV-Erzeugungsleistung (W)** wählen. Der Sensor muss die reale gesamte
PV-Erzeugung **aller konfigurierten Flächen** abbilden – nicht Netzsaldo,
Hausverbrauch, Batterieentladung oder einen einzelnen Wechselrichter, wenn
dessen Leistung nicht der modellierten Gesamtanlage entspricht. Standard ist
**deaktiviert**. Kalibrierung wirkt ausschließlich im Modus **Eigene
Berechnung**; der externe Forecast bleibt unverändert.

Die Messung erfolgt höchstens alle zehn Minuten während ausreichender
PV-Erzeugungsprognose (mindestens 300 W). Nächte, ungültige Messungen und
wahrscheinliche Wechselrichter-Begrenzung nahe der installierten kWp werden
nicht gelernt. Für die drei Bewölkungsbereiche (klar, teilweise, bedeckt)
werden getrennte robuste Faktoren gebildet: vor sechs verwertbaren Messungen
bleibt der Faktor **1,0**. Änderungen sind gedämpft und auf **0,60–1,25**
begrenzt. Lernhistorie maximal 30 Tage, Speicherung in SEP-Restore-Daten;
Neustarts bewahren die Werte. Die Prognose-Entität enthält im Attribut
`kalibrierung` Faktoren, Stichproben und mittlere absolute Fehler der letzten
7 und 30 Tage (W). Ein optionaler Button **PV-Kalibrierung zurücksetzen**
setzt ausschließlich diese Lerndaten zurück.

**Grenzen:** Kein Ersatz für eine lokale Nebelvorhersage. Abregelung, Defekte
oder lokale Verschattung können Messungen verfälschen. Bei konfigurierter
Leistungsbegrenzung die Kalibrierung deaktivieren. Die Leistungssumme der
PV-Sensoren muss mit den eingetragenen Flächen übereinstimmen.



Auf schmalen Karten teilen sich Gerätetext und Bedienelemente den verfügbaren Platz. Messwerte, Modus und Zahnrad können innerhalb der rechten Spalte umbrechen. Die Modusauswahl im Kartenkopf zeigt Automatik, Beobachten, Manuell und Aus als kurze Namen. Ab 0.3.49 steht der Gerätemodus nur noch im Zahnrad (Gruppe „Bedienung“); in der Gerätezeile zeigt das Auto stattdessen die Ladeziel-Auswahl, Haushaltsgeräte zeigen die jeweils wirksamen Buttons Sofortstart, Nachladen und Fertig. Der Heizstab hat im rechten Leistungs-/Budgetblock einen Umschalter Auto | Ein | Aus (Ein = Modus Manuell: heizt bis zur Maximaltemperatur, auch mit Netzstrom; Temperaturschutz und Mindestpause bleiben aktiv; Aus schaltet sofort ab). Auf breiten Karten liegen die drei Tasten neben Leistung/Budget, bei schmaler Kartenbreite darüber. Werte und Tasten bleiben rechts, Status links darf umbrechen. Ist ein anderes Gerät auf Manuell oder Aus, erscheint der Modus als kleiner Hinweis; Beobachten zeigt weiterhin den Status-Chip. Beim WP-Boost bleibt die gerätespezifische Auswahl erhalten.

**PV-Überschuss intelligent verteilen – mit Prioritäten, Geräteprogrammen, Batteriespeicher und Home-Assistant-Dashboard.**

**Aktueller Quellcode-Stand (vorbereitet): 0.3.53** · Home-Assistant-Integration: `smartify_energy` · Oberfläche: Deutsch / Englisch

> **Versionshinweis:** Die Versionsnummer beschreibt den Repository-Stand. In HACS erscheint eine neue Version erst, wenn der zugehörige GitHub-Release-Tag erfolgreich veröffentlicht und von HACS erkannt wurde. [Veröffentlichte Versionen ansehen](https://github.com/smartify-your-home/smartify-energy-pro/releases).

## Was macht Smartify Energy Pro?

SEP verteilt den verfügbaren PV-Überschuss nach einstellbarer Priorität. Das System berücksichtigt den Netzsaldo, bereits laufende und reservierte Verbraucher sowie – abhängig von der Konfiguration – den Batteriespeicher und eine PV-Prognose. Die Geräte werden in Home Assistant eingerichtet und über eine integrierte Lovelace-Karte bedient.

| Funktion | Verhalten |
| --- | --- |
| **Waschmaschine und Geschirrspüler** | Programm erkennen, auf PV-Freigabe warten, nach Freigabe ohne Unterbrechung weiterlaufen; Spätstart und Sofortstart möglich |
| **Heizpausen-Reservierung** | Nach der ersten erkannten Heizphase wahlweise weniger Leistung für spätere Heizphasen reservieren; pro Gerät einstellbar |
| **Wäschetrockner** | Eigenes Profil; Modelle ohne zuverlässigen Wiederanlauf werden nicht durch Abschalten der Steckdose gesteuert |
| **Heizstab** | PV-abhängige Leistungs- und Temperaturregelung, Hysterese, Start- und Stoppschwellen; temperaturgeregelter Handbetrieb möglich |
| **Wärmepumpe / Warmwasser** | PV-WW-Boost mit optionalen Wetter-, Sonnenwinkel- und Prognosebedingungen sowie Schutz vor Mehrfachauslösung |
| **Elektroauto / Wallbox** | PV-Laderegelung, Priorisierung und Berücksichtigung von Ladebedingungen |
| **Batteriespeicher** | Ladezustand und Ladeleistung bei der Priorisierung berücksichtigen; keine automatische direkte Speichersteuerung durch SEP |
| **Prioritäten** | Geräte per Drag & Drop ordnen; nachrangige regelbare Verbraucher können für höher priorisierte Starts zurückgenommen werden |
| **Dashboard** | Gerätestatus, Leistungsbudget, Prioritäten, Einstellungen, Diagnose und PV-Plan in einer Karte |

### PV-Plan: Prognose und tatsächliche Erzeugung

Unter dem PV-Plan befindet sich ein standardmäßig eingeklappter Bereich **PV-Prognose / Ist-Erzeugung**. Er zeigt stündliche Balken, den vorhergesagten und gemessenen Energieertrag (kWh) sowie die prozentuale Abweichung. Verglichen werden nur Stunden mit mindestens 95 % tatsächlich beobachteter PV-Leistung und einer **vorher** gespeicherten Prognose. Die Stundenprognose wird nicht rückwirkend ersetzt. Für den Vergleich im Prognose-Dialog den vorhandenen optionalen **PV-Erzeugungsleistungssensor (W)** auswählen (Gesamt-PV-Leistung, nicht Netzsaldo oder Akku); dies funktioniert sowohl mit externer Prognose als auch eigener Berechnung. Die Aufzeichnung beginnt ab dem Update; frühere Tage werden nicht rückwirkend erfunden. Messlücken (z. B. HA-Neustart) erscheinen nicht als Nullertrag.

## Neueste Änderungen

### 0.3.28 – HACS-Infoseite überarbeitet

Die bisherige Sammlung historischer Versionshinweise wurde durch eine aktuelle, kompakte Funktionsübersicht ersetzt. Technische Details und frühere Änderungen stehen weiterhin in den verlinkten Dokumentationen und im Changelog. **Keine Änderung der Regelungslogik gegenüber 0.3.26.**

### 0.3.26 – Restreservierung während Heizpausen

Für Waschmaschine und Geschirrspüler gibt es **Restreservierung in Heizpausen** (`pause_reservation_pct`). Der Wert ist pro Gerät von **0 bis 100 %** in 10-%-Schritten einstellbar; **Standard 100 %**.

- **Vor der ersten abgeschlossenen Heizphase:** volle Nennleistung reservieren.
- **Danach, in Heizpausen:** mindestens den eingestellten Prozentsatz der Nennleistung reservieren; der tatsächlich gemessene Verbrauch zählt immer.
- **Bei erneutem Heizen:** mindestens die tatsächliche Leistungsaufnahme berücksichtigen.
- **Bei fehlendem oder ungültigem Leistungssensor:** volle Nennleistung reservieren.
- **Trockner:** unverändert, mit eigener Dauerlastreservierung.

**Beispiel:** Geschirrspüler mit 2.000 W Nennleistung und 50 % Restreservierung hält in einer Heizpause 1.000 W für spätere Heizphasen zurück. Das übrige Budget kann die nachrangige Waschmaschine früher freigeben. **Achtung:** Wenn beide gleichzeitig heizen oder die PV-Leistung sinkt, kann zusätzlicher Netzbezug entstehen. Die Einstellung ist keine Netzbezugsbegrenzung.

### Diagnose: Historie, Trend und Budget

Die Prioritätenkarte zeigt drei Startprüfungen mit farbigem Status und einem aufklappbaren **Info ▾** mit Ist-/Sollwerten:

| Anzeige | Bedeutung |
| --- | --- |
| **H – Historie** | Genügend Messdaten für das konfigurierte langfristige Mittel vorhanden |
| **T – Trend** | Zwei Trendfenster vorhanden und Trendprüfung für die PV-Freigabe bestanden |
| **B – Budget** | Aktuelles **und** gemitteltes Gerätebudget decken die erforderliche Startleistung |

Ein grüner Freigabehaken erscheint nur, wenn alle drei Bedingungen erfüllt sind. **Sofortstart, Sofortfenster und Spätstart** haben eigene Ausnahmeregeln. Die Trendbewertung ist keine garantierte PV-Wetterprognose.

**Alle Änderungen und technischen Release Notes:** [CHANGELOG.md](CHANGELOG.md).

## So funktioniert der Start eines Haushaltsgeräts

1. Steckdose und Leistungssensor werden dem Gerät in SEP zugeordnet.
2. Das Programm wird **am Gerät** gestartet; SEP erkennt es anhand der Leistungsaufnahme.
3. Reicht der PV-Überschuss noch nicht aus, kann SEP das Programm vor der Freigabe warten lassen – **nur bei Geräten, die nach Stromunterbrechung zuverlässig fortsetzen können**.
4. Für den regulären PV-Start prüft SEP das verfügbare Gerätebudget, dessen Langzeitmittel und den Kurzzeittrend. Prioritäten und Leistungsreservierungen werden berücksichtigt.
5. Nach der Freigabe läuft das Programm weiter, auch wenn der PV-Überschuss später verschwindet. Das Programm wird nicht wegen einzelner Wolken abgeschaltet.
6. Nach Unterschreiten der einstellbaren Fertig-Leistung für die eingestellte Dauer wird das Programm als beendet erkannt. Ein neues Programm kann anschließend automatisch erkannt werden.

**Wichtig:** Die Startschwelle für ein Haushaltsgerät ist mindestens die höhere der beiden Einstellungen **Nennleistung** und **Mindestüberschuss**. Die Heizpausen-Reservierung beeinflusst die nachrangigen Geräte, **nicht** diese eigene Startschwelle.

## Installation über HACS

1. **HACS → Benutzerdefinierte Repositories** öffnen.
2. `https://github.com/smartify-your-home/smartify-energy-pro` als Kategorie **Integration** hinzufügen.
3. **Smartify Energy Pro** installieren beziehungsweise aktualisieren.
4. **Home Assistant neu starten**, damit geänderter Python-Code aktiv wird.
5. Unter **Einstellungen → Geräte & Dienste → Integration hinzufügen** Smartify Energy Pro einrichten. Geräte und benötigte Entitäten hinzufügen.
6. Das Dashboard neu laden, damit die aktuelle Karte angezeigt wird.

### Dashboard-Karte

Die Integration stellt die Karte bereit und registriert sie selbst als Lovelace-Ressource – kein manueller Ressourceneintrag nötig. Sie kann bei Bedarf auch manuell eingefügt werden:

```yaml
type: custom:smartify-energy-plan-card
```

Die Karte bietet die Prioritätenliste, Geräteeinstellungen mit Hilfetexten, Statusanzeigen und den Prognoseplan. Für einzelne Einstellungen das Zahnrad des betreffenden Geräts verwenden. Ab 0.3.48 sind die Einstellungen kompakt: thematische Gruppen (Bedienung, Ladeziel, PV-Boost, Fahrzeug, Temperatur, Laufzeit, Leistung & PV, Zeiten, Speicher; zugeklappt: Programm- & Fertigerkennung, Wetterfilter, Erweitert mit Zusammenfassung der Werte), je Einstellung eine Kurzinfo; die ausführliche Erklärung öffnet (i). Am Desktop zweispaltig, am Handy einspaltig. Einstellungen ohne Wirkung im aktuellen Zustand werden ausgeblendet: Abfahrtszeit/Ziel-Kilometer nur bei Ladeziel „km bis Uhrzeit“, Pool-Sperrzeiten nur bei aktiver Sperre, Sonnenwinkel nur bei aktivem Sonnenfilter, Bewölkungs- bzw. Prognosegrenzen nur beim passenden WW-Boost-Startfilter.

## Wichtige Hinweise

- **Geräte mit nicht wiederanlaufenden Programmen** dürfen nicht durch eine schaltbare Steckdose angehalten werden. Bei Trocknern dafür das entsprechende nicht unterbrechbare Profil wählen.
- **50 % Restreservierung** kann Programme früher starten lassen, erhöht aber das Risiko von gleichzeitigem Heizen und Netzbezug. Wer möglichst keinen zusätzlichen Netzbezug möchte, lässt **100 %** eingestellt.
- **Messsensoren und Prioritäten** müssen korrekt eingerichtet sein. Ungültige Leistungsmessungen werden bei der Heizpausen-Reservierung konservativ behandelt.
- **H/T/B** gelten für reguläre PV-Starts. Ein ausdrücklich erzwungener oder zeitlich fälliger Start kann auch Netzstrom verwenden.
- **Hauptschalter Aus** ist kein elektrischer Not-Aus. Bei Haushaltsgeräten werden die Steckdosen zur manuellen Bedienung freigegeben.
- **Heizstab Manuell** kann temperaturgeregelt auch mit Netzstrom heizen. Temperaturbegrenzung und geeignete elektrische Absicherung bleiben erforderlich.
- Nach Updates die **Release Notes** prüfen, Home Assistant neu starten und die Dashboard-Seite neu laden.

## Dokumentation

- [Alle Versionen und Release Notes](CHANGELOG.md)
- [Aktueller Funktionsstand und technische Grenzen](docs/FUNCTIONS.md)
- [SEP-Funktionen und Details](docs/SEP_CURRENT.md)
- [Update-Anleitung und Funktionstest](docs/UPDATE.md)
- [Benötigte und optionale Entitäten](docs/REQUIRED_FIELDS.md)
- [Migration von SEM v3](docs/SEM_ENTITY_MIGRATION.md)
- [Fehler melden oder Funktionen vorschlagen](https://github.com/smartify-your-home/smartify-energy-pro/issues)

**Projekt:** [smartify-your-home/smartify-energy-pro](https://github.com/smartify-your-home/smartify-energy-pro)

## Kurztrend-Startbedingung (0.3.29)
Für den automatischen PV-Start muss der gerätespezifische Kurztrend-Mittelwert **immer mindestens den Sollwert** erreichen. Bei stärker fallendem Trend muss außerdem die Fortschreibung (Kurzzeit-Ø plus Änderung zwischen den Trendfenstern) mindestens den Sollwert erreichen. Ein steigender oder neutraler Trend ersetzt keinen ausreichenden Kurzzeit-Mittelwert. In der SEP-Karte zeigt das Trend-Icon diese strengere Prüfung. History (H) und aktuelles Budget (B) sind weiterhin zusätzlich erforderlich.


### Heizstab: Ausfall des Netzsensors (ab 0.3.31)
Im Automatikmodus braucht der Heizstab einen gültigen Netz-Messwert. Fehlt er oder meldet der Sensor einen ungültigen Wert, schaltet SEP den Heizstab aus – auch wenn die Mindestlaufzeit noch läuft. Ein neuer Start bleibt gesperrt. Bei getrennten Sensoren für Bezug und Einspeisung müssen beide gültig sein. Sobald gültige Werte zurückkehren, gelten wieder die normalen Startbedingungen einschließlich Mindestpause. Im Status steht bei der Sperre „Netzsensor ungültig“.
Der temperaturgeregelte Modus **Manuell** erlaubt weiterhin Netzstrom; **Beobachten** schaltet grundsätzlich nicht. Ein numerisch plausibler, aber eingefrorener Messwert wird durch diese Prüfung nicht erkannt.

### Vorrangige Heizstab-Abschaltung (ab 0.3.32)
SEP prüft laufende Heizstäbe zuerst, bevor Prognosen und andere Geräte verarbeitet werden. Ein Fehler eines Haushaltsgeräts kann diesen Ausschaltversuch deshalb nicht verhindern. Im Automatikmodus schaltet der Heizstab unterhalb seiner Abschaltschwelle auch während einer Mindestlaufzeit ab. Für diese Prüfung zählt die tatsächliche Netzleistung mit Netzreserve und Akkuentladung; Akku-Ladeleistung darf nur ein höher priorisierter Heizstab nutzen. Versprochene Leistungsfreigaben anderer Verbraucher reichen nicht. Ein abgeschalteter Heizstab wird im selben Durchlauf nicht erneut gestartet. Manuell erlaubt weiterhin Netzstrom, Beobachten schaltet nicht. Die Ausführung des Befehls setzt einen erreichbaren Aktor voraus.

## Pflichtstart ohne Aus-/Ein-Impuls (0.3.35)
Ist die späteste Startzeit erreicht, gibt SEP ein erkanntes Haushaltsprogramm direkt frei. Eine bereits eingeschaltete Steckdose bleibt eingeschaltet – auch ohne ausreichenden PV-Überschuss oder vollständige Messhistorie. Ein zuvor wartendes, ausgeschaltetes Gerät erhält nur den Einschaltbefehl. Dies gilt für Waschmaschine, Geschirrspüler, sonstige Haushaltsgeräte und Trockner mit aktiviertem Wiederanlauf. Die Programmerkennung und die früheste Startzeit bleiben wirksam; noch nicht gestartete Programme im niedrigen Standby werden dadurch nicht automatisch gestartet. Pflichtstarts dürfen Netzstrom nutzen.

## Aktuelle Gerätezeile (seit 0.3.33)
Wirksame Aktionen stehen direkt beim Gerät: Sofortstart, Nachladen/Nachladen beenden und bei laufendem Programm „Fertig“ (setzt die Programmerkennung zurück). „Pflichtstart“ zeigt die berechnete Startzeit; die Wallbox zeigt zusätzlich den Fahrzeug-SoC mit „voll HH:MM“ (Schätzung bis Max-SoC bei gleichbleibender Ladeleistung; links, Leistung und Budget rechts untereinander), während der Stopp-Verzögerung die geplante Abschaltzeit „PV-Stopp HH:MM“ und neben dem Zahnrad ein Raketen-Symbol zum Starten/Beenden des PV-Boosts mit „Boost bis HH:MM“. Die Kopf-Kachel „Verteilt“ ist ab 0.3.47 standardmäßig ausgeblendet und im Karten-Editor bzw. per `show_allocated: true` einblendbar. Historie, Trend und Budget werden als Icons dargestellt, Details stehen unter „Info“. Die Historienanzeige wird ausgeblendet, sobald die Historie vollständig ist; die Prüfung bleibt aktiv.


## Neu in 0.3.35: Programmerkennung und Budgetfreigabe
Bei Waschmaschine und Geschirrspüler sind in der bestehenden SEP-Karte über das Zahnrad die vier Werte für Programm- und Fertigerkennung pro Gerät einstellbar. Standard Programmerkennung: über 9 W für 20 Sekunden (ignoriert z. B. eine kurze Türöffnung mit 10 W für 10 Sekunden). Standard Fertigerkennung: unter 5 W für zwei Minuten. Die Freigabeprüfung über 100 W bleibt unverändert.

Ganz unten befindet sich **Budgetfreigabe nach Heizphase**. 0 % gibt kein zusätzliches Budget frei (100 % Reservierung), 100 % gibt den gesamten ungemessenen Reservierungsanteil frei. Der gemessene Verbrauch zählt weiterhin. Bestehende Reservierungsprozente werden beim Update automatisch umgerechnet; die tatsächliche Budgetwirkung bleibt erhalten.

## Update 0.3.36
- In der SEP-Karte werden verwaiste, nicht verfügbare Einstellungen der früheren Heizpausen-Reservierung (`pause_reservation_pct`) nicht mehr angezeigt.
- Die manuellen Aktionen **Reset/Fertig** und **Sofortstart** lösen den Regelzyklus ohne die übliche 2-Sekunden-Bündelung unmittelbar aus. Die Sensor-Bündelung bleibt unverändert.

## Version 0.3.37 – Direkte Prioritätsänderung
Beim Verschieben der Geräte in der SEP-Karte werden Reihenfolge und Prioritätsnummern sofort angezeigt, ohne auf den Home-Assistant-Service zu warten. Das Backend übernimmt die Reihenfolge gesammelt und löst ohne 2-s-Sensor-Debounce einen Regelzyklus aus. Bei Speicherfehlern wird die tatsächliche Reihenfolge wiederhergestellt und ein Fehler eingeblendet.

## Neu in 0.3.39 – Kompaktere Gerätezeilen
Die Aktionen Sofortstart, Nachladen und Fertig befinden sich direkt rechts unter Leistung und Budget aktuell. Dadurch wird die Anzeige der Waschmaschine und des Geschirrspülers flacher. Auf schmalen Ansichten umbrechen die Aktionsknöpfe bei Bedarf. Die Schaltlogik ist unverändert.

## Neu in 0.3.40 – Hintergrundtransparenz
Der Lovelace-Karteneditor bietet unter „Darstellung“ eine Hintergrundtransparenz von 0 bis 100 %. Die Kartenoberfläche, Gerätezeilen, Kacheln und Zeitleiste folgen den Theme-Farben, ohne die Deckkraft von Schrift und Schaltflächen zu verändern. Standard 0 % entspricht der bisherigen Ansicht.

## 0.3.41 – Stabilere SEP-Kartenregistrierung
Die Karte wird weiterhin über die versions-/hashbasierte JavaScript-Adresse und die Lovelace-Ressource geladen. Falls Lovelace beim Start noch nicht bereit ist, versucht SEP die Ressourcenregistrierung erneut (bis zu sechs Versuche); anhaltende Fehler werden protokolliert. Damit wird ein möglicher Auslöser für „Custom element doesn't exist: smartify-energy-plan-card“ behoben. Bei fortbestehenden Fehlern die HA-Protokolle und Dashboards → Ressourcen prüfen.

## Responsive Geräteliste (kommende Version)
Auf Smartphone und Tablet bleiben Leistungsanzeige, Budget, Zahnrad und Aktionsknöpfe rechts neben den Geräteinformationen. Lange Statustexte werden links über mehrere Zeilen dargestellt. Die Steuerlogik bleibt unverändert.
