# Smartify Energy Pro – aktueller Funktionsstand 0.3.15

## WP-WW-Einmalladung: vereinfachte Modi (0.3.7)

Nur bei der WP-WW-Einmalladung heißen die Modi jetzt **Automatik**, **Beobachten** und **Deaktiviert**. Automatik löst den Boost nach den eingestellten Bedingungen aus; Beobachten zeigt nur Empfehlungen. Deaktiviert löst keinen neuen Boost aus und verändert weder den Auslöser noch eine bereits laufende WW-Ladung. Diese wird von der Wärmepumpe beendet. Bisher gespeicherte Werte Manuell und Aus werden beim Laden zu Deaktiviert zusammengeführt; auch alte interne Moduswerte bleiben ohne Startfreigabe.

Heizstab, andere Verbraucher und der WP-Boost über einen dauerhaften Zahlensollwert behalten ihre bisherigen Modi. Nach dem Update Home Assistant neu starten und das Dashboard neu laden.


## Heizstab: temperaturgeregelter Handbetrieb (0.3.6)

**Manuell** schaltet den Heizstab temperaturabhängig, auch mit Netzstrom. Bei 50 °C Soll und 1 K Hysterese startet er unter 49 °C, läuft bis 50 °C und schaltet dann ab. Solange Manuell gewählt bleibt, wird nach Abkühlung erneut geheizt; dies ist keine einmalige Nachladung. Zum Beenden **Aus**, für PV-Betrieb **Automatik** wählen.

PV-Start-/Stop-Schwellen, früheste Startzeit und die Pause nach Prioritätsrücknahme gelten nur in Automatik. Im Handbetrieb bleiben Mindestpause, Temperaturüberwachung und sofortige Abschaltung bei ungültiger Temperatur oder Geräte-/Hub-Aus aktiv. Die Mindestlaufzeit kann die Temperaturabschaltung nicht verzögern. Manuelle Heizleistung ist nicht für andere Geräte rücknehmbar; noch nicht gemessene Heizleistung wird vor PV-Freigaben reserviert. Andere Gerätetypen behalten ihr bisheriges manuelles Verhalten.


**Stand:** 27. Oktober 2026. Diese Dokumentation erklärt die tatsächlich implementierten Funktionen. Automatisierte Regressionstests ersetzen keinen Test mit realen Verbrauchern.

## Persistente Historie und Updates (0.3.11)
Die bis zu 60-minütige Historie des Steuerbudgets, Netzsaldos und der Akkuladung wird im SEP-HA-Speicher gesichert. Nach einem kurzen Neustart kann die vorhandene Messabdeckung wiederverwendet werden, sofern der letzte Datenpunkt nicht mehr als 2 Minuten zurückliegt und keine größere Zeitlücke vorliegt. Die erste Installation dieser Python-Änderung benötigt einen vollständigen HA-Neustart; reine Dashboard-Änderungen benötigen meist nur einen Frontend-Reload. Ein HACS-Update ersetzt Python-Dateien, lädt sie aber im laufenden HA-Prozess nicht zuverlässig neu.

## Gerätebezogene Trendrichtung (0.3.12)
Neu wird die aus zwei vollständigen Trendzeitfenstern gewonnene Budgetänderung auf das aktuelle gerätespezifische Budget angewendet und mit der jeweils benötigten Startleistung verglichen. ↗ grün bedeutet: deutlicher Anstieg und geschätztes Budget erreicht den Gerätebedarf. ↘ rot bedeutet: deutlicher Rückgang und geschätztes Budget liegt unter dem Gerätebedarf. Grauer → bedeutet keine eindeutige Warn- oder Freigabetendenz. Ein geschätztes Budget ist keine PV-/Wolkenvorhersage, und der Trendpfeil entscheidet nicht allein über einen Gerätestart. Die bestehende Startfreigabelogik ist unverändert.

## Trendanzeige (0.3.10)
Bei Haushaltsgeräten und dem WP-Warmwasser-Boost zeigt die SEP-Karte den Trend des Steuerbudgets: grüner ↗ bei positivem Trend, roter ↘ bei negativem Trend, → bei 0 W und Uhr bei noch nicht auswertbarer Zeitreihe. Zusätzlich werden tatsächliches Alter der Messhistorie und konfigurierte Trendzeit in Minuten angezeigt. Die Berechnung benötigt zwei vollständige Trendfenster. Das Ändern von Trend- oder Mittelungszeit erhält vorhandene RAM-Messwerte; bis zu 60 Minuten bleiben zur nachträglichen Auswertung erhalten. Bei Neustart von Home Assistant beginnt die rein im Arbeitsspeicher gehaltene Historie neu.

## Drei PV-Startbedingungen (0.3.13)
Das automatische Einschalten wartender Haushaltsgeräte sowie der reguläre PV-Start des WP-Boosts erfordern gleichzeitig: (1) konfigurierter Langzeit-Mittelwert des gerätebezogenen Budgets ≥ Gerätebedarf; (2) kurzer Trendzeitraum, dessen Mittelwert den Bedarf erreicht **oder** dessen Trendänderung innerhalb der Toleranz nicht fallend ist; (3) aktuelles gerätebezogenes Restbudget ≥ Gerätebedarf. Beispiel: 15 Minuten Langzeitfenster, 2 Minuten Trendfenster (erfordert 4 Minuten Historie), aktuelle Messung. Die Anzeige gibt Kurzmittel und Bedarf wieder, nicht eine Hochrechnung. Die Ausnahmen für erzwungene Starts und die aktive WW-Sonderfreigabe sind unverändert.

## Projektionsprüfung bei fallendem Kurztrend (0.3.14)
Bei negativem Trend jenseits der einstellbaren Toleranz reicht der aktuelle Kurzzeit-Mittelwert allein nicht. SEP erwartet, dass Kurzzeit-Ø plus Differenz aus den beiden vollständigen Trendfenstern mindestens die erforderliche Geräteleistung ergeben. Bei neutral/steigend ist die Trendbedingung erfüllt. Langer Geräte-Mittelwert und aktueller Gerätewert bleiben unabhängig ≥ Bedarf. Betrifft reguläre PV-Starts der Haushaltsgeräte und WW-Boost. Die Fortschreibung bietet keine garantierte Wolkenerkennung.

## Trendanzeige-Zeitangaben (0.3.15)
Die SEP-Gerätekarte zeigt „Ø 16 min · Trend 2 min · Daten 38 min“ (Beispiel). Die 16 Minuten bestimmen das Langzeit-Mittelungsfenster, die 2 Minuten das Kurztrendfenster und 38 Minuten die gesamte vorhandene Messhistorie. Unterschiedliche Werte sind beabsichtigt; nur die Beschriftung wurde angepasst.

## 1. Zentrale Berechnungen

**Netzsaldo** = reale, vorzeichenbehaftete Netzmessung: Einspeisung positiv, Netzbezug negativ. **Steuerbudget** = Netzsaldo + unmittelbar durch SEP rückgewinnbare Geräteleistung − gemessene Akkuentladung − konfigurierte Netzreserve. Mittelwerte sind zeitgewichtete Vergangenheitswerte. Eine Gerätezusage berücksichtigt zusätzlich die **noch nicht physisch angefallene Leistung**, die durch höher priorisierte Geräte reserviert ist. Bereits tatsächlich gemessene Lasten dürfen dabei nicht doppelt abgezogen werden.

Der **individuelle Gerätesaldo** unterscheidet sich vom allgemeinen Header-Steuerbudget, sobald etwa Akku-Gutschriften oder höher priorisierte Gerätevormerkungen berücksichtigt werden. Der Header darf daher 0 W anzeigen, obwohl ein Gerät *vor* einem gerade ladenden Speicher zusätzlich verfügbare Leistung hat.

## 2. Grafische Prioritäten und PV-Akku

Im SEP-Dashboard ordnen Anwender die Geräte per Drag & Drop. Der PV-Akku erscheint bei konfiguriertem Speicher als **passive, verschiebbare Zeile**. SEP **steuert keine Lade-/Entladeleistung des Wechselrichters**.

Wenn der Akku mit beispielsweise 2.000 W lädt und der Netzsaldo 0 W beträgt, kann ein Verbraucher **oberhalb** des Akkus mit bis zu 2.000 W zusätzlichem rechnerischen Headroom bewertet werden. Ein Gerät **unterhalb** des Speichers darf diese bereits verwendete Leistung nicht noch einmal beanspruchen. Voraussetzung ist eine **autonome Eigenverbrauchsregelung** des Akkus, die bei zusätzlicher Hauslast die Akkuladung reduziert. Die Akku-Gutschrift wird für Momentanwert, 2-Minuten-Mittelwert und konfigurierten längeren Mittelwert getrennt ermittelt. Die gemessene Akkuentladung wird grundsätzlich **vom PV-Steuerbudget abgezogen**, unabhängig von der Position in der Prioritätenliste.

**Beispiel:** Heizstab vor Akku → Heizstab erhält bei ausreichendem Gerätesaldo Vorrang. Akku vor Heizstab → Akku absorbiert Überschuss zuerst; Heizstab sieht nur den verbleibenden Überschuss. Pflichtläufe können eine Prioritätsreihenfolge übersteuern und zeitweise Netzbezug verursachen.

## 3. Haushaltsgeräte

SEP kennt die Zustände `bereit`, `erkannt`, `wartet`, `laeuft` und `fertig`. Ein Programm wird zunächst erkannt und anschließend bei ausreichendem **momentanem und gemitteltem, gerätebezogenem PV-Budget** freigegeben. Für die Startfreigabe zählt mindestens das Maximum aus Nennleistung und konfiguriertem Mindestüberschuss. Vorreservierungen von früher in der Priorität stehenden Heizphasen reduzieren das Budget. Bereits freigegebene Programme werden bei sinkender Sonne **nicht mitten im Programm abgeschaltet**. `fertig` bleibt bis zum SEP-Reset bestehen. Startzeiten heißen **Frühester Start** und **Spätester Start**. Die eigenen SEP-Entitäten sind `status`, `phase`, `waiting`, `heating`, `finished`, `start_now`, `reset`, `earliest_start`, `latest_start`, `nachladen`, `mode`. Die tatsächlichen Entity-IDs werden beim Einrichten vergeben; SEM-Entitäten sind nicht Teil von SEP.

## 4. Poolpumpe

Die Poolpumpe berücksichtigt Wassertemperatur bzw. feste Soll-Laufzeit, Vormittagsziel, Tageslaufzeit, Sonnenuntergang, Sperrzeit, Saison, Mindestlaufzeit/-pause, maximale Laufzeit und eine 15-Minuten-PV-Unterdeckung mit 50-W-Marge. **Pflichtlaufzeiten** können auch bei unzureichendem PV-Budget erforderlich sein. Die Akku-Priorisierung ist mit der Poollogik in isolierten Regressionstests geprüft; reale Anlagen müssen separat geprüft werden.

## 5. Wallbox

Laufende PV-Ladung passt den Ampere-Sollwert anhand des aktuellen Budgets an. Neue PV-Ladevorgänge benötigen auch ausreichend geglätteten Überschuss. Die eigene laufende Mindestladeleistung wird nicht an fremde Verbraucher weitergegeben. Mindeststrom, Stromschritte, Abschaltverzögerung und ggf. Phasenumschaltung bleiben technische Grenzen. Bei kurzfristiger Unterdeckung kann es Netzbezug geben.

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

