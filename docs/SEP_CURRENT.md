## SEP 0.3.88 – WP FBH Sollwerterhöhung, Vorausreservierung und Rest-Tages-Waschtipp
Der bisherige Gerätetyp heißt in der Oberfläche **WP Warmwasser Boost**. Ein neuer unabhängiger Gerätetyp **WP FBH Sollwerterhöhung** unterstützt eine schreibbare Temperatur-Sollwertentität, einen WP-Leistungssensor, Nennleistung, optionale FBH-/WW-Modusbestätigung, bis zu zwei lokale Zeitfenster, Zeit- oder PV-Startsteuerung, plus Kelvin und eine Maximaltemperatur. Alte Temperatur vor jeder Anhebung dauerhaft speichern, bei Zeitende, Erledigung und Moduswechsel sicher wiederherstellen; manuelle Änderungen nicht überschreiben. Ein aktivierter Boost markiert sich nach mindestens 3 h gemessener FBH-Heizlaufzeit und 20 min elektrischer WP-Ruhe als erledigt und wird im selben Fenster nicht neu gestartet. Ohne verlässliches FBH-/WW-Modussignal keine automatische Standby-Fertigerkennung.
Die vorauslaufende WP-Leistungsreservierung ist von 0–120 min in 5-min-Schritten wählbar (Standard 30 min). Sie blockiert neue, in der Priorität darunterliegende Gerätestarts, wenn diese mit dem angekündigten FBH-Boost kollidieren. Ein vorhandener gemeinsamer Leistungszähler der WP darf nicht doppelt zur reservierten oder freigegebenen Energie gerechnet werden. Laufende Haushaltsgeräte bleiben unangetastet.
PV-Tipps vergleichen künftig heute **nur noch den prognostizierten verbleibenden Ertrag bis 16 Uhr**. Ein ausreichend gutes noch freies Waschfenster heute wird nicht unnötig auf morgen verschoben. Bei erkanntem, wartendem oder laufendem Waschprogramm sowie nach dem heute abgeschlossenen Waschgang verschwindet der Waschtipp aus dem PV-Plan; andere Tipps bleiben. Sensoren `pv_tipp`/`pv_waschtipp` geben den aktuellen Zustand weiter aus und werden je Regelzyklus aktualisiert.

## SEP 0.3.87 – GeoSphere Cloud Forecast 60h im Bewölkungsmodell
- Im Eigenberechnungsmodus `cloud` wird der echte GeoSphere-C-LAEF-Wolkensensor (`source`, `dataset`, `max_forecast_hours=60`) bis zur tatsächlichen Modellreichweite von 60h ausgewertet. Frühere 48h-Grenze entfällt **nur** für diesen Sensor.
- Meteonomiqs Cloud Forecast 8h/48h bleibt unverändert. Bei GeoSphere-Modell `geosphere` wird weiterhin `ghi_w_m2` gerechnet, nicht Bewölkung; im Cloud-Modell `cloud_coverage`, nicht GHI. Nur echte Stunden, keine neuen API-Aufrufe oder Auffüllung fehlender Stunden.
- Der PV-Plan darf echte Daten im bestehenden 72h-Fenster anzeigen; keine Erweiterung der Geräteplanung über heute und morgen, keine Änderung an Schutz, Kalibrierung oder historischer Prognose. Version 0.3.86 bleibt zurückgezogen.
- Tests: `tests/test_geosphere_solar.py`, `tests/ha/test_geosphere_cloud_horizon.py`.

## SEP 0.3.85 – GeoSphere Solarstrahlung für eigene PV-Prognose (optional)
Im Schritt **Prognose** gibt es bei eigener Berechnung das neue Feld `solar_weather_source`: `cloud` (Standard wie bisher, Meteonomiqs Bewölkung) oder `geosphere` (GeoSphere C-LAEF GHI in W/m²). Als Wettersensor dient weiterhin `solar_cloud_entity`, bei GeoSphere aber `GeoSphere Cloud Forecast 60h` oder `GeoSphere Solar Irradiation 60h` von my-weather. Die GeoSphere-Option muss in my-weather aktiviert sein; der Datenabruf erfolgt dort direkt kostenlos ohne API-Key.

Das SEP-Backend prüft Quelle, Datensatz, Einheit, Zeitintervalle und gültige Strahlungswerte. Die vorhandenen im PV-Flächen-Editor eingetragenen Dach-/Bifazialflächen bestimmen aus horizontaler Strahlung die angenäherte Modulstrahlung und AC-Energie in Wh pro Stunde. **Keine zusätzliche Cloud-Dämpfung** bei GHI; fehlende Stunden bleiben fehlend (0 W/m² bleibt echte Null), bis zu 60 h für Prognose/Übermorgen-Tipps. Bestehende Installation bleibt im Modus `cloud`, keine stille Datenquellen- oder Geräte-Regelumstellung. SolarEdge-Istvergleich, feste 14-Tage-Achse, PV-Tipps und eingefrorene Stundenprognosen bleiben kompatibel. Kalibrierung wird je Wetterquelle separat gelernt; historische Meteonomiqs-Kalibrierung darf GeoSphere nicht verfälschen.

**Status/Abhängigkeit:** my-weather PR #9 (GeoSphere) muss separat validiert und veröffentlicht werden; dieser SEP-PR kann mit alten my-weather-Versionen auf Bewölkung weiterlaufen. Bei ungültigem/fehlendem GeoSphere-Sensor meldet SEP einen Prognosefehler, ohne künstlich Klarhimmel zu prognostizieren. Die Solarprojektion ist eine Näherung, der Vorteil für Pfaffstätt muss mit realen Istwerten überprüft werden.

## 0.3.84 – Reihenfolge der Bedienelemente in der Prioritätenüberschrift
Die Überschrift zeigt von links nach rechts **Ziehgriff · Schloss · PRIORITÄTEN**. Der Ziehgriff verschiebt den ganzen Bereich, das Schloss schützt die Geräteprioritäten. Dies gilt auf Smartphones, Tablets und Desktop unverändert.

## PV-Plan-Abschnitt verschieben (0.3.83)
Die Reihenfolge der Abschnitte „Prioritäten“ und „PV-Plan“ ist jetzt veränderbar. Der PV-Plan **und alles darunter bis einschließlich Prognose-Ist-Vergleich** wechseln gemeinsam oberhalb oder unterhalb der Prioritäten. Am Abschnittstitel gibt es Ziehgriffe; mit Pointer-Drag wird die Ansicht unmittelbar neu angeordnet. Zum dauerhaften Speichern über mehrere Geräte den Lovelace-Karteneditor öffnen und unter „Reihenfolge der Bereiche“ per Drag & Drop oder Pfeilen `pv_plan_first` in der Kartenkonfiguration speichern. Der direkte Kartendrag merkt die Position lokal im Browser. Der Schlossschalter bleibt links in der Prioritätenüberschrift und schützt nur die Gerätereihenfolge, nicht die Abschnittsposition. Keine Änderung an der Energiesteuerung.

## SEP v0.3.83 – Prioritäten sperren / Nachtbeschriftung entfernen
Links in der Kopfzeile „Prioritäten“, direkt über der ersten Gerätezeile, befindet sich ein Schloss. Standardmäßig geschlossen: Drag & Drop der Geräte und des Batteriespeichers ist deaktiviert, der Touchscreen kann normal scrollen. Nach dem Antippen öffnet sich das Schloss und die Prioritäten können wie bisher verschoben werden. Nochmaliges Antippen sperrt; nach Neuladen der Karte ist das Schloss sicherheitshalber wieder geschlossen. Unterbrechungen von Touch-Gesten verändern die Reihenfolge nicht.
Die im PV-Plan bisher grau markierte und vertikal mit „Nacht“ bzw. „PV-Pause“ beschriftete Lücke ist durch einen sehr schmalen transparenten Tagestrenner ersetzt. Die Datumsüberschrift bleibt erhalten; die Prognose selbst ist unverändert.

## PV-Prognose-Ist-Vergleich: fixe Skala (0.3.82)
Die Y-Achse des 14-Tage-Prognose-Ist-Vergleichs endet jetzt exakt bei der konfigurierten gesamten PV-Peakleistung in kWh pro Stunde (z. B. 10 kWp → 10 kWh). Es gibt weder Reserve noch Rundung oder automatische Vergrößerung für Ausreißer. Einzelne höhere Messwerte werden grafisch bei 100 % gekappt; die Messwerte und Tooltips bleiben unverändert. Die Einstellung `pv_total_peak_kwp` bleibt die vollständige Anlagenleistung inklusive weiterer PV-Flächen, falls explizit eingetragen.

## 0.3.81 – PV-Plan ohne Scroll-Hinweis, Tipps besser lesbar
Die Zeile „PV-Prognose · Tage horizontal scrollen“ und die Tagwechsel-Pfeile entfallen vollständig. Weiterhin per Finger horizontal über den PV-Plan wischen; die feste kW-Achse, Tagesüberschriften sowie Datenlückenhinweise bleiben bestehen. Die PV-Tipp-Hauptzeile erscheint in 16 px, der Zusatztext in 14 px, mit bestehender Karten-Schriftfamilie. Tipp-Wechsel-Pfeile und die Kartenoption `show_pv_tips` bleiben bestehen.

## 0.3.80 – PV-Plan bis übermorgen / Warnung bei fehlenden Wetterstunden
Der PV-Plan bietet zusätzlich zum horizontalen Wischen Links-/Rechts-Pfeile zum Tagwechsel. Übermorgen wird auch bei fehlender Stundenvorhersage sichtbar, jedoch ausdrücklich ohne erfundene Balken. Ein Hinweis nennt den letzten tatsächlich verfügbaren Vorhersagezeitpunkt; bei Nutzung des 8h-Cloudsensors zeigt SEP den Weg zum 48h-Sensor. In „SEP → Konfigurieren → Prognose“ `sensor.meteonomiqs_cloud_forecast_48h` auswählen, falls vorhanden. My-Weather gibt in diesem Sensor maximal 48h aus, oft weniger, je nach Wetteranbieterantwort. Für einen vollständigen Vergleich übermorgen 08–16 Uhr bereits um 06:00 Uhr wären **mindestens 58h** an gültigen Stunden nötig – eine 48h-Prognose reicht dafür nicht. Sensorattribute `prognose_bis`, `prognose_stunden`, `wetter_sensor` helfen bei der Fehlersuche. Null-Erzeugung und fehlender Prognosewert sind unterschiedlich. Die Tippoverlay-Anzeige bleibt ausschließlich in der Kartenkonfiguration abschaltbar.
GitHub Actions: automatische Stornierung überholter PR-Läufe und keine doppelte main-Validierung; die eigentlichen Release-Prüfungen bleiben vollständig. GitHub-Mails werden separat in den persönlichen Benachrichtigungseinstellungen unter System → Actions deaktiviert.

## PV-Alltagstipps und Plan-Zukunftsscrollen (0.3.79)
SEP gibt auf Basis der eigenen oder externen PV-Stundenprognose ab 06:00 Uhr Hinweise zum besten Waschtag (08–16 Uhr, nur vollständige Tage, ab +25 % und +3 kWh sinnvoller Verschiebung). Wo konfiguriert, gibt es außerdem Tipps für Geschirrspüler, Trockner, Nur-PV-E-Auto, Warmwasser, Speicher und die adaptive Live-Wetterlage. Jeder Hinweis ist unverbindlich; reale Netz-/Gerätesteurung bleibt unverändert. Die neuen Sensoren `pv_tipp` und `pv_waschtipp` stellen Hinweistext und strukturierte Werte für Dashboards/Automationen bereit. Der PV-Plan ist mit tagweisen Überschriften und fester linker kW-Achse horizontal scrollbar und zeigt verfügbare Zukunfts-Prognosestunden bis maximal 72 h; zusätzliche Stunden beeinflussen die Gerätestartplanung nicht. Über den Balken stehen zwei kompakte Tippzeilen, weitere Hinweise durch Pfeile erreichbar. **Ein-/Ausblenden allein in der Lovelace-Konfiguration der SEP-PV-Plan-Karte:** „PV-Alltagstipps über den Balken anzeigen“ (`show_pv_tips`, Standard ein). Die Einstellung deaktiviert keine Sensoren und verändert keine Integrationseinstellungen.

## Optionale adaptive Live-PV-Prognose (0.3.77)
Im Setup/Optionen → Prognose kann „Adaptive Live-PV-Prognose“ aktiviert werden (Standard AUS). Sie ist nur für „Eigene Berechnung“ mit konfiguriertem Sensor für tatsächliche PV-Erzeugungsleistung verfügbar. Die Leistung muss dieselben modellierten Flächen enthalten, sonst stimmt der Einstrahlungsindex nicht. SEP benötigt keine zusätzliche Wetter-API: Es vergleicht die Erzeugung während der letzten 30 Minuten mit der aus Standort und PV-Flächen bestimmten Klarhimmel-Leistung. Ab mindestens sechs Messungen in fünf Minuten erkennt es stabile Bedingungen, wechselhafte Bewölkung und Aufhellung/Eintrübung (Nebel und Wolken nicht unterscheidbar). Es korrigiert vorsichtig die nächsten etwa zwei Stunden, danach gilt die normale My-Weather-Vorhersage. Ohne gültige Messwerte, nachts oder bei möglicher Leistungsbegrenzung wird nichts angepasst. Der 14-Tage-Vergleich behält die einmalig eingefrorene Originalprognose. Zustands- und Trendwerte im Attribut `live_pv` des Sensors „PV-Prognose heute“. Heizstab-/Haushaltsgeräte-Schutzregeln bleiben unverändert.

## PV-Flächennamen – Bestandsdaten (0.3.75)
Automatische Standardnamen wie „Fläche 3“ und „Fläche 4“ werden bereits beim Öffnen der PV-Karte anhand der aktuellen Reihenfolge automatisch zu „Fläche 1“ und „Fläche 2“. Einmaliges Speichern erfolgt nur bei tatsächlich geänderten Namen. Selbst vergebene Bezeichnungen, Flächen-IDs, PV-Peakleistung und Zeichnungskoordinaten bleiben erhalten.

## PV-Flächen und Adresssuche (0.3.74)
Nach dem Löschen werden Standardnamen automatisch fortlaufend neu nummeriert; individuelle Namen und interne IDs bleiben erhalten. Nach mindestens drei Zeichen und kurzer Tipp-Pause zeigt Photon bis zu fünf Adressvorschläge. Auswahl lädt das Luftbild am gewählten Ort. Alternativ bleibt die manuelle Nominatim-Suche per Klick/Enter. Eingegebener Suchtext wird an den jeweiligen Anbieter übertragen.

## PV-Vergleich Tageswerte beim horizontalen Scrollen (0.3.71)
Die drei Werte oberhalb der 14-Tage-Ist-/Prognosegrafik sind keine Gesamtsummen mehr. Sie zeigen nur den Tag in der Mitte des horizontal sichtbaren Fensters, initial den jüngsten Tag. Das Datum inklusive Jahr ist sichtbar, laufende und bei Messlücken unvollständige Tage zeigen „bisher“. Prognose und Ist werden aus denselben vollständig beobachteten Stunden dieses Tages addiert (Tagesabweichung = Ist/Prognose−1; kein Prozentwert bei 0 oder fehlender Prognose). Der bestehende Sensor-Store, Kalibrierung und Gerätebetrieb sind unverändert.

## PV-Vergleich mit Gesamt-Peakleistung (0.3.70)
Die Y-Skala wird nicht aus der höchsten Stunde innerhalb der 14-Tage-Historie gebildet, sondern aus der installierten Gesamtnennleistung: Eingabe `pv_total_peak_kwp` (alle PV-Anlagen, inkl. Balkon) oder ersatzweise die Summe der modellierten PV-Flächen. Die Stundenenergie in kWh hat dabei für ein Stundenintervall denselben numerischen Nennwert wie die Peakleistung in kWp; 10 % Toleranz am oberen Rand und Aufrundung auf 0,5 kWh schaffen Platz für Prozentbeschriftungen. Jede Prozentbeschriftung befindet sich über dem jeweils höheren Ist-/Soll-Balken. Die Achse beginnt/endet an der Balkenfläche; Datum und Stundenbeschriftung liegen außerhalb. Senkrechte Trennlinien durchlaufen jeden Tageswechsel, einschließlich der Stundenachse. Fehlende Peakleistung wird als Konfigurationshinweis statt einer aus historischen Daten erfundenen Skala angezeigt.

## PV-Flächen-Editor (0.3.64)

PV-Flächen werden mit der Karte `custom:smartify-energy-pv-card` auf einem Luftbild (basemap.at, nur Österreich) eingezeichnet: Dachflächen als Polygon mit markierter Traufkante, Fassaden als Linie. Die Ausrichtung wird aus der Zeichnung berechnet (Backend `pv_layout.py`, gleiche Rechnung in der Karte für die Vorschau), Neigung und Leistung (kWp oder Module × Wp) werden eingegeben. Das Luftbild wird nur beim ersten Öffnen bzw. über „Luftbild neu laden“ geladen und in `.storage/smartify_energy_map/<entry_id>` gespeichert. Gespeichert wird in den Optionen (`solar_surfaces`); die alten Felder `solar_1_*`–`solar_4_*` werden zusätzlich gespiegelt (Downgrade) und erscheinen nicht mehr im Optionsdialog. Höchstens vier Flächen. Seit 0.3.69: bifaziale Flächen (`bifacial`, `bifaciality` 0,5–1,0, Standard 0,7) – das Modell addiert die Rückseite (Neigung 180°−Neigung, Azimut +180°) mal Faktor. Flächenliste auf breiten Karten rechts neben dem Luftbild, Einträge klappbar.

## PV-Prognose heute = ganzer Tag (0.3.63)

„PV-Prognose heute“ (Sensor `forecast_today`, Kopf der SEP-Karte, „Prog.“ in der Flow-Card) ist die Prognose für den ganzen Tag. Vergangene Stunden kommen aus der ursprünglich eingefrorenen Prognose, die laufende und künftige Stunden aus der aktuellen. Vorher zeigte der Wert bei eigener Berechnung im Tagesverlauf nur noch den Rest. `rest_heute_kwh` ist unverändert der Rest ab jetzt.

## PV-Prognose-/Ist-Vergleich (0.3.61)
Die ausklappbare Grafik stellt 14 Tage statt 48 Stunden dar. Stunden-Balkenpaare zeigen die vorab gespeicherte Prognose und die aus gültiger Leistungsmessung integrierte Ist-Energie, mit signierter Abweichung je Stunde. Pro Tag erscheinen Datum, Tagesabweichung und eine senkrechte Trennlinie. Fehlende Beobachtung bleibt offen und kennzeichnet den Tag als teilweise („bisher“). Home Assistant liefert die astronomischen Sonnenaufgangs-/Sonnenuntergangszeiten jedes Datums; außerhalb des Tageslichts plus je einer Stunde Puffer werden Stunden nur in der Grafik ausgeblendet. Speicherung über den bestehenden Store mit 15-Tage-Grenze (14 Tage plus Puffer), kein historisches Nachberechnen und kein geändertes Regelwerk.

## Abwesenheitskontakt für Heizstab und Wärmepumpen-WW-Boost
Bei beiden Gerätetypen kann in der SEP-Gerätekonfiguration optional `Abwesenheit` auf einen `binary_sensor` oder `input_boolean` gesetzt werden. EIN = abwesend: Heizstab stoppt auch in Manuell; Number-WW-Boost stellt seinen Normalwert zurück; One-shot-WW-Boosts senden keinen neuen Startimpuls. Eine bereits gestartete, eigenständig laufende WW-Ladung der Wärmepumpe wird von SEP nicht abgebrochen. AUS = normaler gespeicherter Betriebsmodus. Ist der konfigurierte Sensor unbekannt/nicht verfügbar, bleibt die Freigabe vorsichtshalber gesperrt. Ohne Auswahl unverändertes Verhalten.

## Aktuelle Budgets und Reaktionszeiten (Unreleased)
Netzsaldo, Akkuleistung und die Leistungssensoren aller SEP-Geräte lösen eine kurzfristig gebündelte (0,25 s) Neuberechnung aus; andere Sensoränderungen bleiben bei 2 s. Schnellere Anforderungen verdrängen bereits vorgemerkte langsamere Aktualisierungen. Gerätemoduswechsel starten die Auswertung ohne absichtliche Verzögerung. Das Budget in der rechten Gerätezeile bleibt der momentane individuelle Wert, nicht der historische Mittelwert. Die Sensoraktualisierung selbst hängt weiterhin vom jeweiligen Gerät und Home Assistant ab. Schutzbedingungen, Start-/Stopplogik, Prognoseintervalle und Akkupriorität bleiben unverändert.

## Nach 0.3.50 – Responsiver Heizstab-Umschalter (0.3.51 vorbereitet)
Der vorhandene Auto/Ein/Aus-Umschalter wird in den Leistungs-/Budgetblock der Gerätezeile verschoben. Bei breiter Karte liegt er neben den Messwerten, bei schmaler Karte direkt oberhalb von Leistung und Budget. Er bleibt in der rechten Spalte und verdrängt nicht den umbruchfähigen Status links. Die vorhandene Modi-Zuordnung und die Temperaturregelung bleiben unverändert.

## Release 0.3.43

Auf schmalen Karten teilen sich Gerätetext und Bedienelemente den verfügbaren Platz. Messwerte, Modus und Zahnrad können innerhalb der rechten Spalte umbrechen. Die Modusauswahl im Kartenkopf zeigt Automatik, Beobachten, Manuell und Aus als kurze Namen. Ab 0.3.49 steht der Gerätemodus nur noch im Zahnrad (Gruppe „Bedienung“); in der Gerätezeile zeigt das Auto stattdessen die Ladeziel-Auswahl, Haushaltsgeräte zeigen die jeweils wirksamen Buttons Sofortstart, Nachladen und Fertig. Der Heizstab hat in der Zeile einen Umschalter Auto | Ein | Aus (Ein = Modus Manuell: heizt bis zur Maximaltemperatur, auch mit Netzstrom; Temperaturschutz und Mindestpause bleiben aktiv; Aus schaltet sofort ab). Ist ein anderes Gerät auf Manuell oder Aus, erscheint der Modus als kleiner Hinweis; Beobachten zeigt weiterhin den Status-Chip. Beim WP-Boost bleibt die gerätespezifische Auswahl erhalten.
Auf schmalen Bildschirmen bleiben Gerätekennzahlen und Aktionen rechts neben dem Status. Statusmeldungen und Gerätenamen können links mehrzeilig angezeigt werden. Keine Änderung der Automatik oder Bedienaktionen.

## Responsive Gerätezeilen (kommende Version)
Auf schmalen Home-Assistant-Dashboards bleiben Leistung, Budget, Einstellungszahnrad und Aktionen rechts in derselben Zeile. Namen und Statustexte brechen links um; die mobilen Bedienelemente behalten ihre Funktionen.

## 0.3.41 – Kartenregistrierung beim Start
Nach dem Home-Assistant-Start versucht SEP die Registrierung der Lovelace-Kartenressource erneut, falls die Lovelace-Verwaltung zunächst noch nicht bereit ist. Das bestehende Cache-Busting und die separate Frontend-JavaScript-Einbindung bleiben bestehen. Bei bleibendem Fehler werden Warnungen und ein Fehler im HA-Protokoll ausgegeben. Dieser Fix betrifft die Kartenverfügbarkeit, nicht die Energieregelung.

## 0.3.40 – Hintergrundtransparenz der SEP-Karte
Der Karteneditor enthält unter Darstellung einen Regler für Hintergrundtransparenz (0–100 %). Der Regler betrifft Hauptfläche, Gerätezeilen, Kacheln, Einstellungsflächen und Zeitleiste, nicht die Deckkraft der Texte oder Bedienelemente. 0 % erhält das bestehende Aussehen. Farben folgen dem Home-Assistant-Theme.

## 0.3.39 – Kompakte Gerätesteuerung
In der SEP-Karte werden die kontextabhängigen Schaltflächen Sofortstart, Nachladen und Fertig platzsparend rechts unter den Werten Leistung und Budget aktuell dargestellt. Bei schmalen Displays passen sich die Schaltflächen an. Die zugrunde liegenden Aktionen, Verfügbarkeitsbedingungen und Budgetregeln bleiben unverändert.

## Update 0.3.37: Prioritäten
Ziehen und Loslassen in der SEP-Karte sortiert Geräte und Prioritätsnummern sofort. Eine Backend-Anforderung übernimmt die neue gesamte Folge und triggert unmittelbar eine Aktualisierung. Normale Sensoränderungen behalten ihren Debounce. Bei Servicefehlern zeigt die Karte eine Fehlermeldung und kehrt zur Server-Reihenfolge zurück.

## 0.3.35: Programmerkennung, Fertigerkennung und Freigabe
Die SEP-Geräteeinstellungen erlauben pro Waschmaschine und Geschirrspüler Start-Erkennung über einer Leistungsschwelle (Standard 9 W) für eine Mindestdauer (Standard 20 s). Die identische Prüfung gilt in Bereit und Fertig. Unterbrechungen setzen den Timer zurück. Die Startfreigabegrenze über 100 W ist davon unabhängig. Ende: standardmäßig unter 5 W für zwei Minuten.

**Budgetfreigabe nach Heizphase** (letzter Geräte-Einstellungspunkt): 0 % = volle Reservierung, 50 % = halbe Reservierung, 100 % = keine zusätzliche Reservierung. Während laufender Heizphasen zählt die gemessene Leistung und ohne gültigen Sensor bleibt die volle Nennleistung reserviert. Altwerte werden beim Laden von der früheren inversen Reservierung auf Freigabe migriert; bisherige reale Budgetwirkung bleibt erhalten.

# Smartify Energy Pro – aktueller Funktionsstand 0.3.26

## Historie: Heizpausen-Reservierung (0.3.26; durch 0.3.35 abgelöst)
Waschmaschine und Geschirrspüler erhalten den Geräteparameter `pause_budget_release_pct` (0–100 %, 10-%-Schritte, Standard 0 %). Vor dem Ende der ersten erkannten Heizphase gilt 100 % Nennleistung. Danach wird während der Heizpausen der eingestellte Anteil der Nennleistung reserviert, mindestens jedoch der gemessene Verbrauch. Bei erneutem Heizen wird die tatsächlich gemessene Leistung berücksichtigt; die physische Netzbilanz enthält diese bereits. Fehlt der Leistungssensor oder liefert er keine gültigen Werte, bleibt die volle Nennleistung reserviert. Die Reservierung reduziert im selben Regelzyklus das verfügbare Budget nachrangiger Geräte; sie ist keine harte Grenze für Netzbezug. Trockner sind ausgenommen. Bereits freigegebene Programme werden nicht unterbrochen. Die H/T/B-Freigabelogik wird dadurch nicht verändert.

## WP-WW-Einmalladung: vereinfachte Modi (0.3.7)

Nur bei der WP-WW-Einmalladung heißen die Modi jetzt **Automatik**, **Beobachten** und **Deaktiviert**. Automatik löst den Boost nach den eingestellten Bedingungen aus; Beobachten zeigt nur Empfehlungen. Deaktiviert löst keinen neuen Boost aus und verändert weder den Auslöser noch eine bereits laufende WW-Ladung. Diese wird von der Wärmepumpe beendet. Bisher gespeicherte Werte Manuell und Aus werden beim Laden zu Deaktiviert zusammengeführt; auch alte interne Moduswerte bleiben ohne Startfreigabe.

Heizstab, andere Verbraucher und der WP-Boost über einen dauerhaften Zahlensollwert behalten ihre bisherigen Modi. Nach dem Update Home Assistant neu starten und das Dashboard neu laden.


## Heizstab: temperaturgeregelter Handbetrieb (0.3.6)

**Manuell** schaltet den Heizstab temperaturabhängig, auch mit Netzstrom. Bei 50 °C Soll und 1 K Hysterese startet er unter 49 °C, läuft bis 50 °C und schaltet dann ab. Solange Manuell gewählt bleibt, wird nach Abkühlung erneut geheizt; dies ist keine einmalige Nachladung. Zum Beenden **Aus**, für PV-Betrieb **Automatik** wählen.

PV-Start-/Stop-Schwellen, früheste Startzeit und die Pause nach Prioritätsrücknahme gelten nur in Automatik. Im Handbetrieb bleiben Mindestpause, Temperaturüberwachung und sofortige Abschaltung bei ungültiger Temperatur oder Geräte-/Hub-Aus aktiv. Die Mindestlaufzeit kann die Temperaturabschaltung nicht verzögern. Manuelle Heizleistung ist nicht für andere Geräte rücknehmbar; noch nicht gemessene Heizleistung wird vor PV-Freigaben reserviert. Andere Gerätetypen behalten ihr bisheriges manuelles Verhalten.


**Stand:** 0.3.34, 31. Oktober 2026. Diese Dokumentation erklärt die tatsächlich implementierten Funktionen. Automatisierte Regressionstests ersetzen keinen Test mit realen Verbrauchern.

## Persistente Historie und Updates (0.3.11)
Die bis zu 60-minütige Historie des Steuerbudgets, Netzsaldos und der Akkuladung wird im SEP-HA-Speicher gesichert. Nach einem kurzen Neustart kann die vorhandene Messabdeckung wiederverwendet werden, sofern der letzte Datenpunkt nicht mehr als 2 Minuten zurückliegt und keine größere Zeitlücke vorliegt. Die erste Installation dieser Python-Änderung benötigt einen vollständigen HA-Neustart; reine Dashboard-Änderungen benötigen meist nur einen Frontend-Reload. Ein HACS-Update ersetzt Python-Dateien, lädt sie aber im laufenden HA-Prozess nicht zuverlässig neu.

## Projektionsprüfung bei fallendem Kurztrend (0.3.14)
Bei negativem Trend jenseits der einstellbaren Toleranz reicht der aktuelle Kurzzeit-Mittelwert allein nicht. SEP erwartet, dass Kurzzeit-Ø plus Differenz aus den beiden vollständigen Trendfenstern mindestens die erforderliche Geräteleistung ergeben. Auch bei neutralem oder steigendem Trend muss der Kurzzeit-Mittelwert mindestens den Gerätebedarf erreichen. Langer Geräte-Mittelwert und aktueller Gerätewert bleiben unabhängig ≥ Bedarf. Betrifft reguläre PV-Starts der Haushaltsgeräte und WW-Boost. Die Fortschreibung bietet keine garantierte Wolkenerkennung.

## Trendanzeige-Zeitangaben (0.3.15)
Die SEP-Gerätekarte zeigt „Ø 16 min · Trend 2 min · Daten 38 min“ (Beispiel). Die 16 Minuten bestimmen das Langzeit-Mittelungsfenster, die 2 Minuten das Kurztrendfenster und 38 Minuten die gesamte vorhandene Messhistorie. Unterschiedliche Werte sind beabsichtigt; nur die Beschriftung wurde angepasst.

## Prioritätenzeilen (0.3.16)
Die kompakte Zeile zeigt z. B. „16 min History voll (2.080 W) · 2 min Trend (−320 W) / Sollwert 2.000 W“. Noch nicht bereite Mittelung erscheint als „wartet“ mit Restzeit. Die bisherige 90-%-Schwelle für die Gültigkeit des langen Mittelwerts bleibt erhalten. Doppelte Fertigbeschreibung und redundanter rechter Ø-/Vorreserviert-Block wurden entfernt; Leistung, aktuelles Budget, Betriebsmodus und Einstellungen bleiben sichtbar. Die Freigabelogik ändert sich nicht.

## 1. Zentrale Berechnungen

**Netzsaldo** = reale, vorzeichenbehaftete Netzmessung: Einspeisung positiv, Netzbezug negativ. **Steuerbudget** = Netzsaldo + unmittelbar durch SEP rückgewinnbare Geräteleistung − gemessene Akkuentladung − konfigurierte Netzreserve. Mittelwerte sind zeitgewichtete Vergangenheitswerte. Eine Gerätezusage berücksichtigt zusätzlich die **noch nicht physisch angefallene Leistung**, die durch höher priorisierte Geräte reserviert ist. Bereits tatsächlich gemessene Lasten dürfen dabei nicht doppelt abgezogen werden.

Der **individuelle Gerätesaldo** unterscheidet sich vom allgemeinen Header-Steuerbudget, sobald etwa Akku-Gutschriften oder höher priorisierte Gerätevormerkungen berücksichtigt werden. Der Header darf daher 0 W anzeigen, obwohl ein Gerät *vor* einem gerade ladenden Speicher zusätzlich verfügbare Leistung hat.

## 2. Grafische Prioritäten und PV-Akku

Im SEP-Dashboard ordnen Anwender die Geräte per Drag & Drop. Der PV-Akku erscheint bei konfiguriertem Speicher als **passive, verschiebbare Zeile**. SEP **steuert keine Lade-/Entladeleistung des Wechselrichters**.

Wenn der Akku mit beispielsweise 2.000 W lädt und der Netzsaldo 0 W beträgt, kann ein Verbraucher **oberhalb** des Akkus mit bis zu 2.000 W zusätzlichem rechnerischen Headroom bewertet werden. Ein Gerät **unterhalb** des Speichers darf diese bereits verwendete Leistung nicht noch einmal beanspruchen. Voraussetzung ist eine **autonome Eigenverbrauchsregelung** des Akkus, die bei zusätzlicher Hauslast die Akkuladung reduziert. Die Akku-Gutschrift wird für Momentanwert, 2-Minuten-Mittelwert und konfigurierten längeren Mittelwert getrennt ermittelt. Die gemessene Akkuentladung wird grundsätzlich **vom PV-Steuerbudget abgezogen**, unabhängig von der Position in der Prioritätenliste.

**Beispiel:** Heizstab vor Akku → Heizstab erhält bei ausreichendem Gerätesaldo Vorrang. Akku vor Heizstab → Akku absorbiert Überschuss zuerst; Heizstab sieht nur den verbleibenden Überschuss. Pflichtläufe können eine Prioritätsreihenfolge übersteuern und zeitweise Netzbezug verursachen.

## 3. Haushaltsgeräte

SEP kennt die Zustände `bereit`, `erkannt`, `wartet`, `laeuft` und `fertig`. Ein Programm wird zunächst erkannt und anschließend bei ausreichendem **momentanem und gemitteltem, gerätebezogenem PV-Budget** freigegeben. Für die Startfreigabe zählt mindestens das Maximum aus Nennleistung und konfiguriertem Mindestüberschuss. Vorreservierungen von früher in der Priorität stehenden Heizphasen reduzieren das Budget. Bereits freigegebene Programme werden bei sinkender Sonne **nicht mitten im Programm abgeschaltet**. `fertig` bleibt bis zum SEP-Reset bestehen. Startzeiten heißen **Frühester Start** und **Spätester Start**. Die eigenen SEP-Entitäten sind `status`, `phase`, `waiting`, `heating`, `finished`, `start_now`, `reset`, `earliest_start`, `latest_start`, `nachladen`, `mode`. Die tatsächlichen Entity-IDs werden beim Einrichten vergeben; SEM-Entitäten sind nicht Teil von SEP.

### Ansage bei Programmende

Optional ruft SEP beim Wechsel auf `fertig` ein Home-Assistant-Script auf (Hub-Einstellung **Script für Ansagen**, Variable `message`). Je Haushaltsgerät gibt es die Schalter **Ansage bei Fertig** (`announce_finished`) und **Erinnerung alle 30 Minuten** (`announce_reminder`), beide standardmäßig aus. Die Erinnerung wiederholt sich, solange das Gerät auf `fertig` steht, und endet mit Reset oder neuem Programmstart. Mit gewähltem Script hat der Hub die Zeiten **Ansagen ab** / **Ansagen bis** (`announce_start`, `announce_end`, Standard 07:00–22:00; gleiche Zeiten = rund um die Uhr). Außerhalb des Zeitraums bleibt eine fällige Ansage offen und wird zu Beginn des nächsten Zeitraums nachgeholt, sofern das Gerät dann noch `fertig` ist. Ohne Script gibt es keine Ansage. Der Scriptaufruf blockiert die Regelung nicht; Fehler werden nur protokolliert. Der Ansagezustand übersteht einen Home-Assistant-Neustart, es gibt dann keine doppelte Erstansage.

## 4. Poolpumpe

Die Poolpumpe berücksichtigt Wassertemperatur bzw. feste Soll-Laufzeit, Vormittagsziel, Tageslaufzeit, Sonnenuntergang, Sperrzeit, Saison, Mindestlaufzeit/-pause, maximale Laufzeit und eine 15-Minuten-PV-Unterdeckung mit 50-W-Marge. **Pflichtlaufzeiten** können auch bei unzureichendem PV-Budget erforderlich sein. Die Akku-Priorisierung ist mit der Poollogik in isolierten Regressionstests geprüft; reale Anlagen müssen separat geprüft werden.

## 5. Wallbox

Laufende PV-Ladung passt den Ampere-Sollwert anhand des aktuellen Budgets an. Neue PV-Ladevorgänge benötigen auch ausreichend geglätteten Überschuss. Die eigene laufende Mindestladeleistung wird nicht an fremde Verbraucher weitergegeben. Mindeststrom, Stromschritte, Abschaltverzögerung und ggf. Phasenumschaltung bleiben technische Grenzen. Bei kurzfristiger Unterdeckung kann es Netzbezug geben.

**PV-Stopp-Anzeige (ab 0.3.45):** Fällt der Überschuss während einer laufenden PV-Ladung unter die Mindestleistung (z. B. Wolke), läuft die Stopp-Verzögerung. Die Karte zeigt dann „PV-Stopp HH:MM – zu wenig Überschuss“ (Status-Attribut `pv_stopp_um`). Die Zeit ist fest: Beginn der Unterdeckung + Stopp-Verzögerung. Die Anzeige verschwindet, sobald der Überschuss wieder reicht (nächster Regelzyklus), die Ladung zur angezeigten Zeit gestoppt wurde, das Auto abgesteckt wird, Sofort-/Pflichtladung übernimmt oder ein vorrangiger Verbraucher die Wallbox verdrängt. Nach einem HA-Neustart oder Neuladen der Integration beginnt die Verzögerung neu. **Ab 0.3.78** gilt bei Ziel „km bis Uhrzeit“ oder „Tage-Konfigurator“: Solange für das Ziel noch Energie fehlt, gibt es keinen PV-Stopp – die laufende Ladung bleibt mit Mindeststrom an (Netzbezug möglich), weil die Energie ohnehin bis zur Abfahrt geladen werden muss. Ist das Ziel erreicht, gilt wieder die normale Stopp-Verzögerung. Ein Start ohne Überschuss erfolgt weiterhin erst zum Pflichtstart.

**PV-Boost (ab 0.3.46):** Schalter `PV-Boost` bzw. Button „Boost“ in der Karte. Für `Boost-Dauer` (Standard 3 h) lädt die Wallbox mit `Boost-Faktor` × PV-Überschuss (1,5–4, Standard ×2), mindestens mit `Boost-Mindestleistung` (Standard 1.400 W; 0 W = nur Faktor × PV). Netzbezug ist ausdrücklich erlaubt; begrenzt durch Mindest-/Maximalstrom und ganze Ampere. Die Karte zeigt „Boost bis HH:MM“. Ende: Ablauf der Dauer, Ausschalten, Abstecken. Sofort- und Pflichtladung haben Vorrang. Vorrangige Verbraucher erhalten weiterhin ihren Anteil (der Boost reduziert sich dann), dürfen die Wallbox aber nicht komplett abschalten. Nachrangige Verbraucher bekommen während des Boosts praktisch kein Budget. Liegt das Ziel unter dem Wallbox-Minimum (z. B. 6 A × 3 = 4.140 W) und ist eine Mindestleistung gesetzt, lädt der Boost mit dem Wallbox-Minimum weiter (Grund „Wallbox-Minimum“, kein Stopp). Reicht ohne Mindestleistung (0 W) Faktor × PV nicht für den Mindeststrom, startet kein Boost bzw. ein laufender stoppt nach der Stopp-Verzögerung. Eine Änderung der Dauer während des Boosts startet die Dauer neu. Die Endzeit wird gespeichert und übersteht einen Neustart.

In der Gerätezeile steht der Fahrzeug-Akku links, Leistung und Budget stehen rechts untereinander.

## 6. Warmwasser-Boost (0.2.23)

Im Wärmepumpen-Untereintrag kann die optionale **WW-Boost-Solltemperatur als Entität** auf `input_number`, `number` oder `sensor` gesetzt werden. Gültig: **30–75 °C**. Ohne Auswahl gilt `Zieltemperatur` als feste SEP-Einstellung. Ist eine ausgewählte Entität ungültig oder nicht verfügbar, wird **kein neuer Boost** freigegeben. Hysterese, PV-Budget, WP-Ruhezeit, optionale Wettergrenzen sowie die dauerhaft gespeicherte Startsperre bleiben erhalten.

**Button-/Schalter-/Boolean-Auslöser:** SEP sendet genau einen Startimpuls über `press` oder `turn_on` und stoppt die laufende Warmwasserbereitung nicht. Einen `input_boolean` setzt SEP **nicht** automatisch auf AUS; das übernimmt gegebenenfalls eine separate Home-Assistant-Automation. Die konfigurierte Solltemperatur ist in diesem Fall eine **Startprüfschwelle**, wird aber nicht automatisch als Temperaturkommando an Hoval gesendet. **Number-Sollwertsteuerung:** Beim Einschalten wird die dynamische Boost-Temperatur tatsächlich als Zielwert geschrieben; beim Ausschalten bleibt die Rückstellung auf den konfigurierten Normalwert erhalten.

## 7. Heizstab

Eigenständiger Gerätetyp mit aktiver Temperatur-Sicherheitsprüfung, Hysterese, frühestem Start, konfigurierbarem Ein- und Ausschaltbudget sowie optionaler Mindestlaufzeit und Mindestpause. Die Leistungsentscheidung nutzt das **momentane**, nach höher priorisierten Lasten reservierte Budget – keinen langen Mittelwert. Ein externer unabhängiger Temperaturbegrenzer bleibt erforderlich.

## 8. Dashboard: Versionen 0.2.24–0.2.26

Die vier bisherigen Header-Kacheln für Netzsaldo/Steuerbudget (je Momentanwert und Durchschnitt) sind zu **zwei** zusammengefasst:

```text
Netzsaldo          Steuerbudget
 Ø     -1454 W      Ø     -1454 W
akt.    -862 W     akt.    -862 W
```

Die Bezeichnungen `Ø` und `akt.` stehen unter der Überschrift in einer festen Spalte, die Leistungswerte sind rechtsbündig und mit Tabularziffern ausgerichtet. 0.2.25 verhindert, dass ein geöffnetes natives Dropdown durch periodisches Neuzeichnen verschwindet. Änderungen an JavaScript erfordern ggf. erneutes Laden des Browser-Frontends.

## 9. Installation, Updates und Release Notes

Die Versionsnummer steht in `custom_components/smartify_energy/manifest.json` und `const.py`. HACS liefert die Integration als Custom Repository. Nach Update Home Assistant neu starten und Dashboard im Browser neu laden. `CHANGELOG.md` enthält die versionierten Änderungen; GitHub-Release-Texte sollen aus diesen Kapiteln synchronisiert werden. Der Workflow `.github/workflows/release-notes.yml` aktualisiert **bestehende** Releases nach Changelog-Änderungen und nach Veröffentlichung eines Releases. Er legt fehlende historische Tags nicht blind an.

## 10. Grenzen und Sicherheitsprinzipien

SEP ist keine Schutz- oder Notabschaltvorrichtung. Netzsensor-Vorzeichen, gemessene Speicherleistungsrichtung, Temperatur-Sensorausfall, Mindestladeleistung und Konkurrenz durch andere Automationen müssen vor Echtbetrieb geprüft werden. Ein aktiver Speicher muss seine Ladung selbstständig reduzieren können, um Geräten *vor* dem Speicher real Energie freizugeben. Die KI-basierte Tagessteuerung ist derzeit ein Konzept, **nicht implementiert**.



### Heizstab: Ausfall des Netzsensors (ab 0.3.31)
Im Automatikmodus braucht der Heizstab einen gültigen Netz-Messwert. Fehlt er oder meldet der Sensor einen ungültigen Wert, schaltet SEP den Heizstab aus – auch wenn die Mindestlaufzeit noch läuft. Ein neuer Start bleibt gesperrt. Bei getrennten Sensoren für Bezug und Einspeisung müssen beide gültig sein. Sobald gültige Werte zurückkehren, gelten wieder die normalen Startbedingungen einschließlich Mindestpause. Im Status steht bei der Sperre „Netzsensor ungültig“.
Der temperaturgeregelte Modus **Manuell** erlaubt weiterhin Netzstrom; **Beobachten** schaltet grundsätzlich nicht. Ein numerisch plausibler, aber eingefrorener Messwert wird durch diese Prüfung nicht erkannt.

### Vorrangige Heizstab-Abschaltung (ab 0.3.32)
SEP prüft laufende Heizstäbe zuerst, bevor Prognosen und andere Geräte verarbeitet werden. Ein Fehler eines Haushaltsgeräts kann diesen Ausschaltversuch deshalb nicht verhindern. Im Automatikmodus schaltet der Heizstab unterhalb seiner Abschaltschwelle auch während einer Mindestlaufzeit ab. Für diese Prüfung zählt die tatsächliche Netzleistung mit Netzreserve und Akkuentladung; Akku-Ladeleistung darf nur ein höher priorisierter Heizstab nutzen. Versprochene Leistungsfreigaben anderer Verbraucher reichen nicht. Ein abgeschalteter Heizstab wird im selben Durchlauf nicht erneut gestartet. Manuell erlaubt weiterhin Netzstrom, Beobachten schaltet nicht. Die Ausführung des Befehls setzt einen erreichbaren Aktor voraus.

## Pflichtstart ohne Aus-/Ein-Impuls (0.3.34)
Ist die späteste Startzeit erreicht, gibt SEP ein erkanntes Haushaltsprogramm direkt frei. Eine bereits eingeschaltete Steckdose bleibt eingeschaltet – auch ohne ausreichenden PV-Überschuss oder vollständige Messhistorie. Ein zuvor wartendes, ausgeschaltetes Gerät erhält nur den Einschaltbefehl. Dies gilt für Waschmaschine, Geschirrspüler, sonstige Haushaltsgeräte und Trockner mit aktiviertem Wiederanlauf. Die Programmerkennung und die früheste Startzeit bleiben wirksam; noch nicht gestartete Programme im niedrigen Standby werden dadurch nicht automatisch gestartet. Pflichtstarts dürfen Netzstrom nutzen.

## Aktuelle Gerätezeile (seit 0.3.33)
Wirksame Aktionen stehen direkt beim Gerät: Sofortstart, Nachladen/Nachladen beenden und bei laufendem Programm „Fertig“ (setzt die Programmerkennung zurück). „Pflichtstart“ zeigt die berechnete Startzeit; die Wallbox zeigt zusätzlich den Fahrzeug-SoC mit „voll HH:MM“ (Schätzung bis Max-SoC bei gleichbleibender Ladeleistung; links, Leistung und Budget rechts untereinander), während der Stopp-Verzögerung die geplante Abschaltzeit „PV-Stopp HH:MM“ und neben dem Zahnrad ein Raketen-Symbol zum Starten/Beenden des PV-Boosts mit „Boost bis HH:MM“. Die Kopf-Kachel „Verteilt“ ist ab 0.3.47 standardmäßig ausgeblendet und im Karten-Editor bzw. per `show_allocated: true` einblendbar. Historie, Trend und Budget werden als Icons dargestellt, Details stehen unter „Info“. Die Historienanzeige wird ausgeblendet, sobald die Historie vollständig ist; die Prüfung bleibt aktiv.

## Aktuelle PV-Prüfungen und Messhistorie
Für reguläre PV-Starts müssen der langfristige gerätebezogene Mittelwert, der Kurztrend-Mittelwert und das aktuelle Gerätebudget jeweils mindestens den Bedarf decken. Bei stärker fallendem Trend muss zusätzlich Kurztrend-Mittelwert plus Trendänderung den Bedarf decken. Ein neutraler oder steigender Trend ersetzt kein ausreichendes Kurzzeitmittel. Die Trendberechnung benötigt zwei vollständige Trendfenster. Explizite Pflichtstarts haben eigene Ausnahmen.
Die Messhistorie wird gespeichert und nach einem kurzen Neustart wiederverwendet, sofern Datenabdeckung und Zeitlücken gültig sind; eine Messunterbrechung von mehr als zwei Minuten erfordert einen Neuaufbau. Sie ist nicht mehr ausschließlich im Arbeitsspeicher gehalten.
