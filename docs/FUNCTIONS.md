# Funktionsstand und Grenzen

Stand: **0.2.20**, 26.10.2026. Diese Seite beschreibt implementiertes Verhalten im Repository, keine bestätigte Funktionstüchtigkeit auf einer bestimmten Home-Assistant-Installation.

## Regelung
- Der Sensor `surplus` ist der **reale Netzsaldo** (+ Einspeisung, − Netzbezug), `surplus_avg` dessen zeitlicher Mittelwert. `budget` und `budget_avg` zeigen dagegen das intern verwendete Steuerbudget.
- SEP rechnet nur tatsächlich steuerbare, unmittelbar absenkbare Leistung wieder zum Budget hinzu. Laufender WW-Boost und freigegebene Haushaltsprogramme sind bereits im Netzsaldo enthalten und werden nicht zurückgerechnet.
- Bei laufender PV-Wallbox-Ladung gilt nur der Teil oberhalb des aktuellen Mindeststroms als frei umverteilbar. Die Wallbox selbst darf ihre bereits belegte Mindestleistung für die eigene Modulation berücksichtigen.
- Leistung von externen Überschuss-Senken und das Laden eines Akkus bleiben für die Budgetfreigabe ohne SEP-Stelleingriff unberücksichtigt. Batterie-Entladung wird sicherheitshalber vom verfügbaren PV-Budget abgezogen. Der angezeigte Batterie-Vorrang bleibt eine Planungshilfe, keine Steuerung des Batterie-Wechselrichters.
- Lasten mit höherer Priorität werden vor nachgeordneten Geräten berücksichtigt; Pflicht- und Sofortladungen können Netzstrom beanspruchen.
- Der reguläre Regelzyklus bleibt konfigurierbar. Änderungen ausgewählter Messwerte lösen schneller eine gebündelte Auswertung aus.

## E-Auto / Wallbox
- Modi: Nur PV, Fahrstreckenziel bis Uhrzeit, Tagesplanung, Sofortladung.
- Eine laufende PV-Ladung regelt ihren Sollstrom aus dem momentanen Restbudget. Die Startfreigabe nutzt weiterhin ein geglättetes Signal.
- Hardwaregrenzen beachten: Mindeststrom, maximale Stromstärke, ganze Ampere, ggf. 1-/3-Phasenwechsel sowie dessen Sperrzeit.
- Unterhalb der nötigen Leistung reduziert SEP bis zum Mindeststrom und schaltet erst nach Ablauf von `stop_delay` ab. Netzbezug ist dabei möglich.

## Batteriespeicher
- SEP kann Speicherleistung, SoC, Kapazität und PV-Prognosen nutzen, um die Priorität von Speicher und Verbrauchern zu bestimmen.
- Strategien: Speicher zuerst, Geräte zuerst oder prognosebasierte Entscheidung.
- **Nicht vorhanden:** Direkte Vorgabe einer Batterie-Ladeleistung, aktives Regeln eines Wechselrichters oder koordinierte Ladestromkommandos an Wallbox **und** Akku.
- Dafür sind passende schreibbare Home-Assistant-Entitäten und eine getrennt zu entwickelnde sichere Stellwertlogik nötig.

## Wärmepumpe
- Warmwasser-Boost als einmaliger Start per Button oder Schalter: SEP prüft PV-Budget, Temperatur, Hysterese, Ruhezeit und Wetterbedingungen, stößt die WW-Ladung einmal an und schaltet den Einmal-Auslöser danach nicht wieder aus.
- Optionales Lesesignal **Warmwasser aktiv** (`binary_sensor`/`input_boolean`): EIN verhindert einen weiteren Start während einer WW-Ladung, ungültig/nicht verfügbar blockiert sicherheitshalber.
- **WW-Boost Mindestabstand:** 60–720 Minuten (Standard 60 min), dauerhafter letzter Startzeitpunkt wird vor dem Aktor-Befehl gespeichert. Auch ein HA-Neustart setzt die Sperre nicht zurück.
- Ein Schalter muss wieder AUS sein, bevor er erneut eingeschaltet werden darf; Number-basierte Boosts behalten die aktive Rückstellung und bekommen ebenfalls die dauerhafte Startsperre.
- Optional Sonnenhöhenwinkel sowie zwei stündliche Bewölkungswerte als Startfilter.
- Die Wetterfilter betreffen nur neue Boosts; sie ersetzen keine prognosebasierte Suche nach dem besten Boost-Zeitfenster.

## Bekannte Risiken und Tests
- Sensoren können langsamer aktualisieren als SEP prüft; Serviceaufrufe an Ladegeräte können verzögert sein.
- Momentane Überschüsse können stark schwanken; die Mindeststrom-/Stop-Regeln verhindern keine kurzfristigen Netzbezüge.
- Prüfen vor produktivem Betrieb: Sensor-Vorzeichen, Phasen, Leistungsgrenzen, Steuer-Entitäten, Fehlerfall bei fehlenden Messwerten und Zusammenspiel mit anderen Automationen.
- Automatisierte und reale Integrationstests sind nicht als vollständig nachgewiesen dokumentiert.

## Haushaltsgeräte – SEM v3

- Einschalten/Programmstart wird erst nach fünf Sekunden stabiler Erkennung (>9 W oder eingeschaltete Steckdose ohne Sensor) übernommen.
- Bei >100 W wird die erstmalige Überschuss-Freigabe geprüft. Bei Ablehnung wird abgeschaltet und auf Überschuss, Spätstart oder Sofortfenster gewartet.
- Heizphasen: > max(200 W, 8 % Nennleistung) während zehn Sekunden; Ende bei <100 W. **Keine starre Sperre anderer Geräte mehr**: Aktuelles und gemitteltes Steuerbudget müssen für die erwartete Heizlast des nächsten Geräts reichen.
- Bis zum Heizphasenende wird je freigegebenem Gerät die noch zu erwartende Nennleistung abzüglich tatsächlich gemessener Leistung reserviert. Ohne gültige Messung wird die volle Nennleistung reserviert. Nach der Heizphase wird die zusätzliche Reservierung freigegeben.
- Die automatische PV-Startschwelle ist max(Nennleistung, Mindest-Überschuss); Spätstart und ausdrücklich manuelle Freigabe können davon abweichen.
- **Ab 0.2.20:** Für jedes PV-startende Gerät werden das reale momentane und das gemittelte Restbudget **unabhängig** nach sämtlichen vorherigen zusätzlichen Heizreservierungen geprüft. Nur wenn beide Werte die Heizlast decken, darf ein weiteres Gerät starten.
- In der Prioritätenkarte erscheint neben der aktuellen Geräteleistung das **individuelle Momentanbudget**; darunter stehen das entsprechende Mittelwertbudget sowie die bis dahin zusätzlich vorgemerkte Leistung anderer Geräte. Diese Werte stammen direkt aus dem aktuellen Regelzyklus und sind auch als Statusattribute pro Gerät verfügbar.
- Nach Freigabe läuft das Programm durch. Sinkender Überschuss allein unterbricht es nicht mehr.
- Fertigerkennung gemäß Schwelle und Dauer, standardmäßig 5 W und zwei Minuten; Abschlussstatus bis Reset.
- **Bewusster SEP-Unterschied:** Konfigurierbare Prioritätszahl statt SEMs ältestem Programmstart.
