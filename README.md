# Smartify Energy Pro

**PV-Überschuss intelligent verteilen – mit Prioritäten, Geräteprogrammen, Batteriespeicher, PV-Prognose und eigener Home-Assistant-Karte.**

Home-Assistant-Integration `smartify_energy` · Oberfläche Deutsch / Englisch · Installation über HACS

![SEP-Karte mit Kopfzeile, Prioritätenliste und PV-Plan](https://raw.githubusercontent.com/smartify-your-home/smartify-energy-pro/main/docs/images/sep-card-desktop.png)

> **Versionshinweis:** In HACS erscheint eine neue Version erst, wenn der zugehörige GitHub-Release veröffentlicht und von HACS erkannt wurde. [Veröffentlichte Versionen](https://github.com/smartify-your-home/smartify-energy-pro/releases) · [Alle Änderungen (CHANGELOG)](CHANGELOG.md)

## Inhalt

- [Was macht Smartify Energy Pro?](#was-macht-smartify-energy-pro)
- [Die SEP-Karte](#die-sep-karte)
- [Haushaltsgeräte: Start mit PV](#haushaltsgeräte-start-mit-pv)
- [E-Auto / Wallbox](#e-auto--wallbox)
- [Heizstab, Wärmepumpe, Pool](#heizstab-wärmepumpe-pool)
- [Diagnose: Historie, Trend und Budget](#diagnose-historie-trend-und-budget)
- [PV-Prognose und PV-Plan](#pv-prognose-und-pv-plan)
- [Installation](#installation)
- [Wichtige Hinweise](#wichtige-hinweise)
- [Dokumentation](#dokumentation)

## Was macht Smartify Energy Pro?

SEP verteilt den verfügbaren PV-Überschuss nach einstellbarer Priorität. Berücksichtigt werden der Netzsaldo, bereits laufende und reservierte Verbraucher sowie – je nach Konfiguration – Batteriespeicher und PV-Prognose. Geräte werden in Home Assistant eingerichtet und über die mitgelieferte Lovelace-Karte bedient.

| Gerät / Funktion | Verhalten |
| --- | --- |
| **Waschmaschine, Geschirrspüler** | Programm erkennen, auf PV-Freigabe warten, nach Freigabe ohne Unterbrechung durchlaufen; Spätstart (Pflichtstart), Sofortstart und Nachladen |
| **Heizpausen-Reservierung** | Nach der ersten Heizphase wahlweise weniger Leistung für spätere Heizphasen reservieren; pro Gerät einstellbar |
| **Wäschetrockner** | Eigenes Profil; Modelle ohne zuverlässigen Wiederanlauf werden nicht über die Steckdose angehalten |
| **E-Auto / Wallbox** | PV-Laden mit Stromanpassung und 1/3-Phasen-Umschaltung, Ladeziele (Nur PV, km bis Uhrzeit, Tage-Konfigurator, Sofort), zeitlich begrenzter **PV-Boost** mit Netzanteil, Ladeende-Prognose |
| **Heizstab** | PV-abhängige Temperaturregelung mit Hysterese, Start-/Stoppschwellen; Schnellumschalter Auto / Ein / Aus |
| **Wärmepumpe / Warmwasser** | PV-WW-Boost mit optionalen Wetter-, Sonnenwinkel- und Prognosebedingungen, Schutz vor Mehrfachauslösung |
| **Poolpumpe** | Tageslaufzeit nach Wassertemperatur, Vormittagsziel, optionale tägliche Sperrzeit |
| **Abwesenheit (optional)** | Für Heizstab und WW-Boost je ein `binary_sensor`/`input_boolean` (EIN = abwesend) |
| **Batteriespeicher** | Ladezustand und Ladeleistung in der Priorisierung berücksichtigen; keine direkte Speichersteuerung durch SEP |
| **Prioritäten** | Geräte per Drag & Drop ordnen; nachrangige regelbare Verbraucher werden für höher priorisierte Starts zurückgenommen |

## Die SEP-Karte

### Interaktive Diagramme mit Apache ECharts (ab 0.3.86)
SEP bringt Apache ECharts 6.1.0 unter der Apache-2.0-Lizenz inklusive Lizenz- und NOTICE-Datei direkt mit. Es wird **keine** weitere HACS-Karte und kein externer CDN-Zugriff benötigt. `ECharts-Diagramme` sind im SEP-Karteneditor standardmäßig eingeschaltet und bei Bedarf abschaltbar.

- **PV-Plan:** zusätzliche interaktive Kurve für die echten stündlichen PV-Prognosen (kW) mit Geräteplanung als Balken. Darunter bleibt die bisherige detaillierte Geräte-Zeitleiste unverändert.
- **PV-Prognose / Ist-Erzeugung (14 Tage):** ECharts-Balkendiagramm (kWh je Stunde), horizontales Touchscrollen; Diagramm antippen, um die Tages-Zusammenfassung auszuwählen. Die Obergrenze bleibt strikt bei der konfigurierten PV-Peakleistung (kWp), selbst bei höheren Messwerten. Fehlende Messstunden bleiben ohne Balken; historische Prognosen werden nicht nachträglich verändert.
- Passt Farben an Home-Assistant-Themes an. Bei Lade- oder Renderproblemen bleibt die bisherige native HTML-Darstellung verfügbar. Einstellungen und Gerätefreigaben werden nicht von der Grafik beeinflusst.

Die ECharts-Datei liegt auf dem HA-Server unter `/smartify_energy/echarts.common.min.js`; die Option installiert **keine zusätzliche Ressource** in Lovelace. Apache-Copyright und Lizenz siehe `custom_components/smartify_energy/www/ECHARTS-NOTICE.txt` und `ECHARTS-LICENSE.txt`.

**Umfang:** Die derzeitige Version visualisiert die bereits in SEP vorhandenen zwei Datenreihen-Sets (PV-Plan und historische Prognose/Ist-Erzeugung). Ein echter paralleler GeoSphere/Meteonomiqs-Vergleich benötigt zusätzliche Rohdaten im Backend; ein zeitaufgelöster SolarEdge-Einstrahlungsvergleich ebenso. Diese werden nicht durch ECharts allein erzeugt.



Die Integration bringt die Karte mit und registriert sie selbst als Lovelace-Ressource – kein manueller Ressourceneintrag nötig.

```yaml
type: custom:smartify-energy-plan-card
```

**Aufbau**

- **Kopf:** Netzsaldo und Steuerbudget (Mittelwert und aktuell), PV-Prognose heute (ganzer Tag: vergangene Stunden aus der ursprünglichen Prognose, ab jetzt aus der aktuellen) mit Restertrag, Modus des Energiemanagers. Die Kachel „Verteilt“ ist optional (`show_allocated: true`).
- **Prioritätenliste:** je Gerät Status, Leistung und aktuelles Budget an seiner Prioritätsposition. Rechts stehen nur die Bedienelemente, die im aktuellen Zustand wirken:
  - Haushaltsgeräte: **Sofortstart**, **Nachladen**, **Fertig** (setzt die Programmerkennung zurück)
  - E-Auto: **Ladeziel**-Auswahl und Rakete für den **PV-Boost**, Akkustand mit „voll HH:MM“
  - Heizstab: **Auto | Ein | Aus**
  - Ist ein Gerät auf Manuell oder Aus, erscheint der Modus als kleiner Hinweis.
- **PV-Plan:** prognostizierte PV-Leistung und geplante Geräte für heute und morgen, darunter aufklappbar der Vergleich Prognose / Ist-Erzeugung der letzten 48 Stunden.

<p align="center"><img src="https://raw.githubusercontent.com/smartify-your-home/smartify-energy-pro/main/docs/images/sep-card-mobile.png" alt="SEP-Karte auf dem Smartphone" width="380"></p>

Auf schmalen Karten (Smartphone) bleiben Werte und Bedienelemente rechts, lange Statustexte brechen links um.

### Einstellungen (Zahnrad)

Jedes Gerät und der Energiemanager haben ein Zahnrad mit allen Einstellungen – kompakt in thematischen Gruppen (Bedienung, Ladeziel, PV-Boost, Fahrzeug, Temperatur, Laufzeit, Leistung & PV, Zeiten, Speicher). Selten benötigte Gruppen (Programm- & Fertigerkennung, Wetterfilter, Erweitert) sind zugeklappt und zeigen ihre Werte als Zusammenfassung. Jede Einstellung hat eine Kurzinfo; die ausführliche Erklärung öffnet **(i)**. Einstellungen ohne Wirkung im aktuellen Zustand werden ausgeblendet (z. B. Abfahrtszeit und Ziel-Kilometer nur beim Ladeziel „km bis Uhrzeit“).

![Kompakte Einstellungen des E-Autos mit geöffneter Erklärung](https://raw.githubusercontent.com/smartify-your-home/smartify-energy-pro/main/docs/images/sep-settings.png)

### Kartenoptionen

| Option | Standard | Wirkung |
| --- | --- | --- |
| `title` | – | Kartentitel |
| `hub` | – | Geräte-ID des Energiemanagers (nur bei mehreren nötig) |
| `show_header` | `true` | Netzsaldo-, Budget- und Prognosekacheln |
| `show_allocated` | `false` | Kachel „Verteilt“ (vom Steuerbudget zugeteilte Leistung) |
| `show_priorities` | `true` | Prioritätenliste |
| `show_mode` | `true` | Ladeziel-Auswahl in der Auto-Zeile |
| `show_settings` | `true` | Zahnrad je Gerät und Energiemanager |
| `show_timeline` | `true` | PV-Plan |
| `timeline_hours` | `24` | Länge des PV-Plans |
| `background_transparency` | `0` | Hintergrundtransparenz 0–100 % (Schrift und Bedienelemente bleiben deckend) |

Alle Optionen sind auch im grafischen Karteneditor einstellbar.

## Haushaltsgeräte: Start mit PV

1. Steckdose und Leistungssensor werden dem Gerät in SEP zugeordnet.
2. Das Programm wird **am Gerät** gestartet; SEP erkennt es an der Leistungsaufnahme (Standard: über 9 W für 20 s; einstellbar).
3. Reicht der Überschuss noch nicht, wartet das Programm vor der Freigabe – **nur bei Geräten, die nach Stromunterbrechung zuverlässig fortsetzen**.
4. Für den regulären PV-Start prüft SEP Historie, Kurzzeittrend und Budget (siehe [Diagnose](#diagnose-historie-trend-und-budget)). Prioritäten und Reservierungen werden berücksichtigt.
5. Nach der Freigabe läuft das Programm durch, auch wenn der Überschuss später fehlt.
6. Ist die **späteste Startzeit** erreicht, gibt SEP das Programm auch ohne PV frei (Pflichtstart, Anzeige „Pflichtstart HH:MM“). Eine bereits eingeschaltete Steckdose bleibt dabei eingeschaltet.
7. Unterschreitet die Leistung die Fertig-Schwelle lange genug (Standard: unter 5 W für 2 min), gilt das Programm als beendet.

8. Optional sagt SEP das Programmende an (siehe [Ansage bei Programmende](#ansage-bei-programmende)).

**Startschwelle:** mindestens der höhere Wert aus **Nennleistung** und **Mindestüberschuss**.

**Heizpausen-Reservierung:** Nach der ersten abgeschlossenen Heizphase kann ein Teil der Nennleistung für spätere Heizphasen freigegeben werden (**Budgetfreigabe nach Heizphase**, 0 % = volle Reservierung). Der gemessene Verbrauch zählt immer; bei fehlendem Leistungssensor wird die volle Nennleistung reserviert. Mehr Freigabe lässt nachrangige Geräte früher starten, kann aber zu gleichzeitigem Heizen und Netzbezug führen.

### Ansage bei Programmende

Waschmaschine, Trockner, Geschirrspüler und sonstige Haushaltsgeräte können ansagen, wenn sie fertig sind.

1. **Einmalig:** In den SEP-Einstellungen (Zahnrad der Integration, Schritt **Netz**) unter **Script für Ansagen** ein Home-Assistant-Script wählen. SEP ruft es mit der Variable `message` auf, zum Beispiel „Waschmaschine ist fertig.“ Wo und wie laut angesagt wird (Lautsprecher, Sprachausgabe), legt dieses Script fest. Ohne Script gibt es keine Ansagen.
2. **Je Gerät** im Zahnrad, Gruppe **Ansage**:
   - **Ansage bei Fertig** – eine Ansage, sobald das Programm fertig ist. Standard: aus.
   - **Erinnerung alle 30 Minuten** – wiederholt die Ansage („… ist fertig – bitte ausräumen.“), solange das Gerät auf „Fertig“ steht. Endet mit der **Fertig**-Taste oder sobald ein neues Programm erkannt wird. Standard: aus.
3. **Am Hub:** **Ansagen ab** / **Ansagen bis** (Standard 07:00–22:00) begrenzen die Uhrzeit. Sind beide Zeiten gleich, wird rund um die Uhr angesagt. Wird ein Gerät außerhalb des Zeitraums fertig, folgt die Ansage zu Beginn des nächsten Zeitraums, falls es dann noch auf „Fertig“ steht.

Ein minimales Script, das den Text entgegennimmt:

```yaml
ansage:
  fields:
    message:
      required: true
  sequence:
    - action: tts.speak
      target:
        entity_id: tts.piper
      data:
        media_player_entity_id: media_player.wohnzimmer
        message: "{{ message }}"
```

Die Ansage ist unabhängig von der Regelung: SEP wartet nicht auf das Script, und ein Fehler im Script beeinflusst die Steuerung nicht.

## E-Auto / Wallbox

- **Nur PV:** Ladestrom folgt dem Überschuss. Start, wenn aktuelles Budget **und** 2-Minuten-Mittel die Startschwelle erreichen (Mindestladeleistung × Mindest-PV-Anteil). Fehlt Überschuss, wird der Strom sofort reduziert und erst nach der **Stopp-Verzögerung** abgeschaltet – die Karte zeigt dann „PV-Stopp HH:MM“.
- **km bis Uhrzeit / Tage-Konfigurator:** Für die geplante Strecke lädt SEP zuerst mit PV und rechtzeitig vor der Abfahrt mit Netzstrom (Pflichtladung). Solange für das Ziel noch Energie fehlt, wird eine laufende Ladung **nicht** per PV-Stopp abgeschaltet, sondern läuft bei zu wenig Überschuss mit Mindeststrom weiter (Netzbezug möglich). Erst wenn das Ziel erreicht ist, gilt die normale Stopp-Verzögerung.
- **Sofort:** maximaler Ladestrom, Netzbezug möglich.
- **PV-Boost** (Rakete): für eine einstellbare Dauer (Standard 3 h) mit Boost-Faktor × PV-Überschuss laden, mindestens mit der Boost-Mindestleistung; Netzbezug ist erlaubt. Liegt das Ziel unter dem Wallbox-Minimum (z. B. 6 A × 3), lädt der Boost mit diesem Minimum. Endet nach Ablauf, beim Ausschalten oder Abstecken; Anzeige „Boost bis HH:MM“.
- **Ladeende:** „voll HH:MM“ schätzt, wann Max-SoC bei gleichbleibender Ladeleistung erreicht ist.
- **Startprüfung:** Wartet das Auto auf Überschuss, zeigt die Karte Historie und Budget samt Ist-/Sollwerten unter „Info“. Eine Trendprüfung gibt es beim Auto nicht, weil die Ladung jederzeit angepasst oder gestoppt werden kann.

## Heizstab, Wärmepumpe, Pool

- **Heizstab Auto:** heizt nur mit Überschuss zwischen Start- und Stoppschwelle bis zur Maximaltemperatur. Ohne gültigen Netzsensor-Wert wird er abgeschaltet und nicht neu gestartet („Netzsensor ungültig“). Laufende Heizstäbe werden vor allen anderen Geräten geprüft, damit sie unterhalb der Abschaltschwelle zuverlässig ausgehen.
- **Heizstab Ein** (= Modus Manuell): heizt temperaturgeregelt bis zur Maximaltemperatur, auch mit Netzstrom; Temperaturschutz und Mindestpause bleiben aktiv. **Aus** schaltet sofort ab.
- **Wärmepumpe:** PV-WW-Boost mit optionalem Sonnenfilter, Bewölkungs- oder PV-Prognose-Startbedingung. Bei Abwesenheit wird ein Number-WW-Boost zurückgenommen und kein neuer Einmal-WW-Start ausgelöst; WP-eigene WW-Zyklen bleiben unberührt.
- **Poolpumpe:** Tageslaufzeit fix oder nach Wassertemperatur, Anteil bis zum Vormittagsziel (notfalls mit Netzstrom), optionale tägliche Sperrzeit (z. B. Mittagsruhe).

## Diagnose: Historie, Trend und Budget

Haushaltsgeräte und Wärmepumpe zeigen drei Startprüfungen als farbige Symbole, das E-Auto Historie und Budget. **Info ▾** öffnet die Ist- und Sollwerte.

![Startprüfung mit geöffnetem Info-Bereich](https://raw.githubusercontent.com/smartify-your-home/smartify-energy-pro/main/docs/images/sep-diagnose.png)

| Symbol | Bedeutung |
| --- | --- |
| **Historie** | Genügend Messdaten für das Langzeitmittel (90 % des Mittelungsfensters). Wird ausgeblendet, sobald erfüllt. |
| **Trend** | Der Kurzzeit-Mittelwert erreicht die Startleistung; bei stärker fallendem Trend muss auch die Fortschreibung reichen. |
| **Budget** | Aktuelles **und** gemitteltes Gerätebudget decken die Startleistung. |

Der grüne Haken erscheint nur, wenn alle Bedingungen erfüllt sind. Sofortstart, Sofortfenster und Pflichtstart haben eigene Regeln. Die Trendbewertung ist keine Wetterprognose.

## PV-Prognose und PV-Plan

Unter **Einstellungen → Geräte & Dienste → Smartify Energy Pro → Konfigurieren → Prognose**:

- **Externe Prognose (Standard):** eine Prognose-Integration der Home-Assistant-Energieplattform (z. B. Forecast.Solar, Solcast, Open-Meteo Solar Forecast) oder ein Prognosesensor.
- **Eigene Berechnung – GeoSphere Austria (neu, optional):** Im Prognose-Dialog bei **Wettermodell der Eigenprognose** die Option `GeoSphere Austria (Solarstrahlung GHI)` wählen und im Feld **My-Weather Prognosesensor** den neuen Sensor `GeoSphere Cloud Forecast 60h` oder `GeoSphere Solar Irradiation 60h` auswählen. In `my-weather` muss die GeoSphere-Solarprognose vorher aktiviert werden. Der Abruf läuft dort **direkt und kostenlos bei GeoSphere**, ohne API-Key oder zusätzlichen Open-Meteo-Dienst. SEP nutzt das stündliche `forecast[*].ghi_w_m2` (W/m²) und rechnet daraus mit den vorhandenen PV-Flächen (kWp, Neigung, Ausrichtung, bifaziale Rückseite) eine stündliche AC-Energieprognose (Wh). Die Strahlungsprognose ist **keine** fertige Wechselrichterprognose. Es erfolgt **kein zweiter Bewölkungsabschlag**; die Umrechnung zwischen horizontaler und Modulstrahlung bleibt eine Näherung. Der gewählte GeoSphere-Sensor hat bis zu 60 echte Stunden, nicht künstlich ergänzte Werte. Das Wettermodell steht für sich und ist nicht mit der externen Solcast-/Forecast.Solar-Quelle zu summieren.
- **Eigene Berechnung (My-Weather):** Standort aus Home Assistant und Bewölkung aus `Meteonomiqs Cloud Forecast 48h` (Attribut `forecast` mit `cloud_coverage` 0–100 %; der bisherige 8-h-Sensor funktioniert weiterhin, liefert aber nur 8 h). Die **PV-Flächen** werden seit 0.3.64 nicht mehr in diesem Dialog eingetragen, sondern im Dashboard eingezeichnet (siehe „PV-Flächen einzeichnen“). Flächen nicht doppelt erfassen. Für Stunden ohne Bewölkungswerte werden keine sonnigen Stunden ergänzt. SEP macht keinen eigenen Meteonomiqs-API-Aufruf.

Die Prognose speist PV-Plan und Planungswerte; Netzsaldo und Start-/Stoppschutz bleiben messwertbasiert. Bei Nebel und Hochnebel sind Prognosen besonders unsicher.

**Automatische Kalibrierung (optional, nur bei eigener Berechnung):** **PV-Prognose automatisch kalibrieren** aktivieren und den **PV-Erzeugungsleistungssensor (W)** wählen – er muss die gesamte Erzeugung aller konfigurierten Flächen abbilden (nicht Netzsaldo, Hausverbrauch oder Akku). Gelernt wird höchstens alle zehn Minuten bei mindestens 300 W Prognose, getrennt für klar / teilweise / bedeckt. Nächte, ungültige Messungen und wahrscheinliche Wechselrichter-Begrenzung werden ignoriert. Vor sechs Messungen bleibt der Faktor 1,0; Änderungen sind gedämpft und auf 0,60–1,25 begrenzt, Lernhistorie maximal 30 Tage (übersteht Neustarts). Das Attribut `kalibrierung` der Prognose-Entität zeigt Faktoren, Stichproben und mittlere Fehler (7/30 Tage); **PV-Kalibrierung zurücksetzen** löscht nur diese Lerndaten. Bei Abregelung, Defekten oder Verschattung die Kalibrierung deaktivieren.

Die Kalibrierung unterscheidet **Bewölkungsmodell und GeoSphere-Strahlungsmodell**: bisherige Meteonomiqs-Lernwerte werden für GeoSphere nicht übernommen. Die vorhandene optionale Live-Anpassung für die nächsten rund zwei Stunden und der eingefrorene historische Prognose-Ist-Vergleich bleiben erhalten. Nur echte PV-Erzeugungsmesswerte verwenden, nicht Netzsaldo oder Akkuleistung.

**Bei GeoSphere-Ausfall:** SEP erfindet keine Strahlungsstunden und fällt nicht heimlich auf das Bewölkungsmodell zurück. In der Prognose erscheint ein Fehler bzw. „Prognose fehlt“, soweit kein gültiger Zeitbereich geliefert wird. Geräte-Schutz und aktuelle Überschussfreigabe bleiben unverändert.

**PV-Plan:** kW-Achse mit Hilfslinien; prognostizierte PV-Leistung und geplante Geräte je Stunde. Der aufklappbare Bereich **PV-Prognose / Ist-Erzeugung** zeigt die letzten 48 Stunden (horizontal scrollbar, kWh je Stunde, prozentuale Abweichung). Verglichen werden nur Stunden mit mindestens 95 % gemessener Leistung und einer vorher gespeicherten Prognose; Messlücken erscheinen nicht als Nullertrag. Dafür den PV-Erzeugungsleistungssensor im Prognose-Dialog auswählen.

### PV-Flächen einzeichnen (ab 0.3.64)

Karte **SEP PV-Flächen** zu einem Dashboard hinzufügen:

```yaml
type: custom:smartify-energy-pv-card
title: PV-Flächen          # optional
# entry_id: …              # nur bei mehreren Energiemanagern
```

- **Luftbild:** Orthofoto von [basemap.at](https://basemap.at) (nur Österreich, CC BY 4.0) rund um den Home-Assistant-Standort. Es wird **nur beim ersten Öffnen** heruntergeladen und in Home Assistant gespeichert (`.storage/smartify_energy_map/`, ist damit Teil der Sicherung). Neu geladen wird es nur über **„Luftbild neu laden“** – dann für den aktuellen Kartenmittelpunkt. Ohne Luftbild (z. B. außerhalb Österreichs) kann auf einem Raster gezeichnet werden.
- **Dachfläche:** „+ Dachfläche“, die Ecken antippen, Doppelklick oder „Fertig“. Die dick markierte Kante ist die **Traufkante** (untere Dachkante); antippen einer anderen Kante der markierten Fläche ändert sie. Die **Ausrichtung** ergibt sich automatisch (Seite, zu der das Dach abfällt) und wird als Pfeil angezeigt.
- **Fassade/Linie:** „+ Fassade/Linie“, Anfang und Ende antippen; mit „Richtung umdrehen“ die Seite wählen.
- **Neigung** (0° flach – 90° senkrecht) je Fläche eingeben. **Leistung** wahlweise als **kWp gesamt** oder **Module × Wp**.
- **Bifazial:** Für Module, deren Rückseite mit erzeugt (Zaun, Fassade, aufgeständert), „bifazial“ anhaken und den **Bifazialfaktor** aus dem Datenblatt eintragen (Standard 0,7). Die Prognose rechnet dann zusätzlich die Rückseite in Gegenrichtung (direkte Sonne von hinten, Himmel, Bodenreflexion) mal Faktor. Bei senkrechten Ost/West-Zäunen kann das den Ertrag fast verdoppeln, bei Südzäunen im Winter nur wenige Prozent.
- Auf breiten Bildschirmen steht die Flächenliste rechts neben dem Luftbild; jede Fläche lässt sich auf- und zuklappen (Kopfzeile mit kWp, Ausrichtung und Neigung).
- Ecken lassen sich verschieben, die Karte mit Ziehen, Mausrad oder +/− bewegen. **Speichern** übernimmt die Flächen; der Energiemanager lädt neu und rechnet die Prognose damit.
- Höchstens vier Flächen. Bisher eingetragene Werte werden als „nicht eingezeichnet“ übernommen (Ausrichtung dort weiterhin als Zahl änderbar) und können eingezeichnet werden. Nur Administratoren können ändern.
- Die Flächen werden nur bei Prognose-Modus **Eigene Berechnung** verwendet.

### PV-Prognose gegen Ist-Erzeugung (14 Tage)

**Tageswerte statt 14-Tage-Summen:** Die Prognose, gemessene Erzeugung und Abweichung oberhalb der Grafik gehören immer zum gerade sichtbaren Datum. Beim seitlichen Wischen wird das Datum in der Mitte der Grafik gewählt und die Tageswerte sofort aktualisiert. Der jüngste Tag wird beim Öffnen vorausgewählt. Die Summen vergleichen nur die Stunden, für die sowohl Originalprognose als auch vollständige Ist-Messung vorhanden sind. Laufende oder unvollständige Tage werden als „bisher“ markiert. Das 14-tägige Scrollfenster bleibt erhalten.

Die Vergleichsgrafik verwendet eine feste Y-Skala aus der gesamten installierten PV-Peakleistung (kWp, alle Anlagen gemeinsam) plus 10 % Platz für die Abweichungswerte direkt über den Stundenbalken. Unter **SEP → Konfigurieren → Prognose** kann die gesamte Leistung inklusive Balkon-PV angegeben werden. Ohne diese Angabe summiert SEP die Leistung der eingezeichneten PV-Flächen. Zwischen Tagen markieren durchgehende senkrechte Linien die Trennung.

Unter dem PV-Plan öffnet die Vergleichsgrafik die letzten 14 Tage. Prognose und Ist-Erzeugung erscheinen je Stunde als Balkenpaar mit prozentualer Abweichung. Tagesüberschriften und senkrechte Trennlinien ordnen die Stunden; bei jeder Tagesüberschrift steht die Abweichung des Tages (bei Messlücken als „bisher“). Nachtstunden werden mithilfe der von Home Assistant berechneten Sonnenaufgangs- und Sonnenuntergangszeiten ausgeblendet; auf beiden Seiten bleibt eine Stunde sichtbar. Die Stundenprognose wird vor dem jeweiligen Zeitraum eingefroren, damit spätere Wetterupdates den Vergleich nicht verfälschen. Für Stunden mit fehlenden Messdaten zeigt SEP keine erfundene Ist-Energie an. Die Historie baut sich nach dem Update schrittweise auf.

## Installation

1. **HACS → Benutzerdefinierte Repositories** öffnen.
2. `https://github.com/smartify-your-home/smartify-energy-pro` als Kategorie **Integration** hinzufügen.
3. **Smartify Energy Pro** installieren bzw. aktualisieren.
4. **Home Assistant neu starten** (nötig bei jeder Änderung am Python-Code; reine Karten-Updates brauchen nur ein Neuladen des Browsers).
5. **Einstellungen → Geräte & Dienste → Integration hinzufügen → Smartify Energy Pro**, danach Geräte und benötigte Entitäten hinzufügen ([Benötigte Felder](docs/REQUIRED_FIELDS.md)).
6. Karte ins Dashboard einfügen und die Seite neu laden. Zeigt die Companion-App eine veraltete oder keine Karte, dort den Frontend-Cache zurücksetzen.

## Wichtige Hinweise

- **Nicht wiederanlauffähige Geräte** dürfen nicht über eine Steckdose angehalten werden – beim Trockner das passende Profil wählen.
- **Hauptschalter Aus** ist kein elektrischer Not-Aus. Haushaltsgeräte-Steckdosen werden zur manuellen Bedienung freigegeben; Pool und Wallbox stoppen nur bei ihrem eigenen Modus Aus.
- **Heizstab Ein/Manuell, Pflichtstart, Pflichtladung, Sofort und PV-Boost** können Netzstrom verwenden. Temperaturbegrenzung und elektrische Absicherung bleiben erforderlich.
- **Messsensoren und Prioritäten** müssen korrekt eingerichtet sein. Ein plausibler, aber eingefrorener Messwert wird nicht erkannt.
- **Reaktionszeit:** Netz-, Akku- und Geräteleistungen werden nach 0,25 s Bündelung neu bewertet; Moduswechsel und manuelle Aktionen ohne Wartezeit. Hysterese, Schutzzeiten und Startprüfungen bleiben wirksam.
- Nach Updates die [Release Notes](CHANGELOG.md) prüfen.

## Dokumentation

- [Alle Versionen und Release Notes](CHANGELOG.md)
- [Aktueller Funktionsstand und technische Grenzen](docs/FUNCTIONS.md)
- [SEP-Funktionen im Detail](docs/SEP_CURRENT.md)
- [Update-Anleitung und Funktionstest](docs/UPDATE.md)
- [Benötigte und optionale Entitäten](docs/REQUIRED_FIELDS.md)
- [Migration von SEM v3](docs/SEM_ENTITY_MIGRATION.md)
- [Fehler melden oder Funktionen vorschlagen](https://github.com/smartify-your-home/smartify-energy-pro/issues)

Die Bilder in dieser README zeigen die echte Karte mit Beispieldaten; neu erzeugen mit `npm i --no-save @mdi/js@7.4.47 @fontsource/roboto@5.1.0 && node scripts/readme_images.cjs . docs/images`.


PV-Flächeneditor (0.3.74): Beim Löschen Standardnamen fortlaufend neu nummerieren; eigene Namen bleiben erhalten. Photon-Adressvorschläge nach 700 ms Tipp-Pause, alternativ Nominatim-Suche über Klick/Enter. Suchtext wird an den jeweiligen Anbieter übermittelt.


Seit 0.3.75 nummeriert der PV-Flächeneditor auch ältere gespeicherte automatisch benannte Flächen beim Öffnen neu und sichert diese Namenskorrektur einmalig; individuelle Namen, Anlagenwerte und Geometrie bleiben unverändert.


### Adaptive Live-PV-Prognose (optional, seit v0.3.77)
Im Prognose-Schritt aktivierbar (Standard **Aus**), nur bei „Eigene Berechnung“ mit echter PV-Erzeugungsleistung für exakt dieselben modellierten PV-Flächen. SEP analysiert ohne externe API die tatsächliche Einstrahlung anhand der Wechselrichterleistung und des Klarhimmel-Modells. Nach mindestens 6 Messwerten über 5 Minuten passt es die nahe Prognose vorsichtig für rund zwei Stunden an. Bei veralteten oder ungültigen Sensorwerten bleibt die Prognose unverändert. Das Attribut `live_pv` des PV-Prognosesensors liefert Zustand, Einstrahlungsindex, Trend und Volatilität. Die historische Ist-/Prognosegrafik bleibt unverändert.


### PV-Alltagstipps und scrollbarer PV-Plan (v0.3.79)
Der PV-Plan kann horizontal durch die tatsächlich vorhandenen Stundenprognosen der kommenden Tage gewischt werden. Tagesüberschriften sind wie beim PV-Prognose-Ist-Vergleich, die kW-Achse bleibt links sichtbar; weitere reine Anzeige-Stunden führen zu keinen zusätzlichen automatischen Starts.

Ab 06:00 Uhr vergleicht SEP das Zeitfenster 08–16 Uhr über heute, morgen und, wenn vollständig verfügbar, übermorgen. Zum Verschieben der Wäsche müssen mindestens **25 % und 3 kWh** mehr Ertrag prognostiziert sein. Tipps zu Geschirrspüler, Trockner, reinem PV-E-Autoladen, Warmwasser, Speicher und auffälliger Live-Wetterlage werden nur bei passenden konfigurierten Komponenten angezeigt. Datenlücken ergeben keine erfundenen Erträge. Zwei HA-Sensoren **PV-Tipp** und **PV-Waschtipp** geben Hauptempfehlung, verfügbare Tipps und Tageswerte als Attribute aus. Keine automatische Aktion.

**Nur in der Konfiguration der Lovelace-PV-Plan-Karte:** Option „PV-Alltagstipps über den Balken anzeigen“ deaktivieren, um das zweizeilige Tipp-Overlay vollständig auszublenden. Dies beeinflusst die Sensoren und Energie-Steuerung nicht.


### PV-Plan: Übermorgen und fehlende Prognosedaten (v0.3.80)
Mit den neuen Tagespfeilen kann der PV-Plan auch am Desktop weitergeschaltet werden. Übermorgen bleibt als Tag erreichbar, selbst wenn die Wetterquelle nicht weit genug reicht. Statt fiktiver Nullbalken erscheint dann ein Hinweis, bis wann echte Prognosestunden vorhanden sind. Bei My-Weather für längere Vorschau in SEP → Konfigurieren → Prognose die **Meteonomiqs Cloud Forecast 48h**-Entität auswählen; der bisherige 8h-Sensor wurde aus Kompatibilitätsgründen nicht automatisch ersetzt. Auch 48h reichen morgens um 06:00 nicht für übermorgen bis 16:00 (dafür wären mindestens 58h nötig).

GitHub Actions: überholte PR-Testläufe werden abgebrochen, doppelte Validierung beim Release entfernt; die komplette Prüfung vor der Veröffentlichung bleibt bestehen. Um Actions-E-Mails abzustellen: [GitHub → Settings → Notifications](https://github.com/settings/notifications) → System → Actions → Don't notify (oder Email abwählen).


### Kompakte PV-Plan-Anzeige (v0.3.81)
Der PV-Plan lässt sich weiterhin direkt mit dem Finger horizontal durch Prognosetage bewegen. Die zusätzliche Hinweisspalte „PV-Prognose · Tage horizontal scrollen“ und die Tageswechsel-Pfeiltasten entfallen zugunsten eines ruhigeren Layouts. Der PV-Alltagstipp bleibt darüber eingeblendet, jetzt mit größerer Überschrift (16 px) und Detailzeile (14 px); die Pfeile zum Wechseln zwischen verschiedenen Tipps bleiben erhalten. Die Anzeige kann weiterhin ausschließlich in den Kartenoptionen vollständig ausgeblendet werden.


### Starre PV-Vergleichsskala (v0.3.82)
Der Prognose-Ist-Vergleich für 14 Tage verwendet als feste Y-Obergrenze **genau 1,0 × konfigurierte PV-Gesamt-Peakleistung**: bei 10 kWp also 10 kWh je Stunde. Anders als bisher gibt es keine 10-%-Reserve und keine Rundung auf 500 Wh. Oberhalb des festen Maximums liegende Messwerte bleiben als Tooltip und HA-Sensordaten erhalten, auch wenn ihr Balken visuell auf 100 % begrenzt wird.


### SEP 0.3.83 – Prioritäten per Schloss schützen
In der Kartenüberschrift **links über der ersten Prioritätszeile** gibt es ein Schloss zum Sperren/Entsperren der Drag-&-Drop-Reihenfolge. Standardmäßig ist die Sortierung gesperrt, auch nach Neuladen. Zum Bearbeiten Schloss öffnen, Geräte/Batterie wie gewohnt ziehen und anschließend wieder schließen. Gesperrte Ziehpunkte sind gedimmt; normales Scrollen am Handy bleibt erhalten.

Im PV-Plan ist die graue Nachtfläche samt vertikaler „Nacht“-Beschriftung entfallen. Ein schmaler transparenter Trenner und die Tagesüberschriften zeigen weiterhin den Tageswechsel.


### PV-Plan oberhalb der Prioritäten anordnen (v0.3.83)
Der ganze PV-Plan mit Prognose-Ist-Vergleich kann per Ziehgriff an der Abschnittsüberschrift oberhalb von **Prioritäten** angeordnet werden. Die Ziehgriffe verändern nur die Ansicht; das Schloss links neben „Prioritäten“ schützt weiterhin ausschließlich die Geräte-Reihenfolge. Für eine **dauerhaft für alle Geräte gespeicherte Reihenfolge** in der Lovelace-Kartenkonfiguration unter **Reihenfolge der Bereiche** die zwei Abschnitte mit Drag & Drop (oder den Pfeilen) vertauschen und die Karte speichern. Die Drag-Geste direkt in der Karte merkt sich die Anordnung zusätzlich lokal im jeweiligen Browser.


### Prioritätenüberschrift (v0.3.84)
Die Bedienelemente stehen ab sofort ganz links in der Reihenfolge **Ziehgriff · Schloss · PRIORITÄTEN**. Der Griff verschiebt den gesamten Bereich, das Schloss schützt das Verschieben einzelner Geräte.
