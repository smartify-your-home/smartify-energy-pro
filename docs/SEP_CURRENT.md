# Smartify Energy Pro – aktueller Funktionsstand 0.2.26

**Stand:** 26. Oktober 2026. Diese Dokumentation erklärt die tatsächlich implementierten Funktionen. Automatisierte Regressionstests ersetzen keinen Test mit realen Verbrauchern.

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
