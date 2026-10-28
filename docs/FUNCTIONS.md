# Funktionsstand und Grenzen

## WP-WW-Einmalladung: vereinfachte Modi (0.3.7)

Nur bei der WP-WW-Einmalladung heißen die Modi jetzt **Automatik**, **Beobachten** und **Deaktiviert**. Automatik löst den Boost nach den eingestellten Bedingungen aus; Beobachten zeigt nur Empfehlungen. Deaktiviert löst keinen neuen Boost aus und verändert weder den Auslöser noch eine bereits laufende WW-Ladung. Diese wird von der Wärmepumpe beendet. Bisher gespeicherte Werte Manuell und Aus werden beim Laden zu Deaktiviert zusammengeführt; auch alte interne Moduswerte bleiben ohne Startfreigabe.

Heizstab, andere Verbraucher und der WP-Boost über einen dauerhaften Zahlensollwert behalten ihre bisherigen Modi. Nach dem Update Home Assistant neu starten und das Dashboard neu laden.


## Heizstab: temperaturgeregelter Handbetrieb (0.3.6)

**Manuell** schaltet den Heizstab temperaturabhängig, auch mit Netzstrom. Bei 50 °C Soll und 1 K Hysterese startet er unter 49 °C, läuft bis 50 °C und schaltet dann ab. Solange Manuell gewählt bleibt, wird nach Abkühlung erneut geheizt; dies ist keine einmalige Nachladung. Zum Beenden **Aus**, für PV-Betrieb **Automatik** wählen.

PV-Start-/Stop-Schwellen, früheste Startzeit und die Pause nach Prioritätsrücknahme gelten nur in Automatik. Im Handbetrieb bleiben Mindestpause, Temperaturüberwachung und sofortige Abschaltung bei ungültiger Temperatur oder Geräte-/Hub-Aus aktiv. Die Mindestlaufzeit kann die Temperaturabschaltung nicht verzögern. Manuelle Heizleistung ist nicht für andere Geräte rücknehmbar; noch nicht gemessene Heizleistung wird vor PV-Freigaben reserviert. Andere Gerätetypen behalten ihr bisheriges manuelles Verhalten.


Stand: **0.3.15**, 27.10.2026. Diese Seite beschreibt implementiertes Verhalten im Repository, keine bestätigte Funktionstüchtigkeit auf einer bestimmten Home-Assistant-Installation.

## Gerätebezogene Budget-Trendbewertung (0.3.12)
Für Haushaltsgeräte und den WP-Boost wird die positive/negative Differenz zweier vollständiger Trendfenster auf das aktuelle individuell verfügbare Budget fortgeschrieben. Nur ein ansteigender Trend, der damit die jeweilige erforderliche Leistung erreicht, erhält einen grünen ↗; ein fallender Trend, der die Anforderung unterschreitet, einen roten ↘. Andere Fälle bleiben neutral →, unvollständige Zeitreihen zeigen eine Uhr. Diese Anzeige ist keine Wetterprognose und ändert die Startfreigaben nicht.

## Trendanzeige und Verlauf (ab 0.3.10)
- In der Gerätezeile von Haushaltsgeräten und WP-WW-Boost zeigt ↗ grün einen positiven und ↘ rot einen negativen Trend des gemessenen Steuerbudgets; → zeigt einen Trend von 0 W, eine Uhr unzureichende Messhistorie.
- Die zusätzliche Minutenangabe nennt das tatsächlich vorhandene Alter der History; daneben steht die konfigurierte Trendzeit. Zur korrekten Trendberechnung müssen zwei vollständige aufeinanderfolgende Trendfenster aufgezeichnet sein.
- Änderung an Mittelungs- oder Trendzeit verwirft die bisherigen Messpunkte nicht mehr. In der laufenden Sitzung werden bis zu 60 Minuten gehalten; HA-Neustart leert weiterhin die rein im RAM gespeicherte Historie.
- Diese Trendanzeige betrifft keine Wallbox, keinen Heizstab, keinen Pool und keine Akku-Zeile; die bestehenden Freigabe- und Trendregeln bleiben erhalten.

## PV-Startfreigabe mit drei Prüfungen (0.3.13)
- Für automatische Starts von Haushaltsgeräten und reguläre PV-WW-Boosts sind **langes Durchschnittsbudget ≥ benötigte Leistung**, **kurzer Trend erfüllt** und **aktuelles Budget ≥ benötigte Leistung** nötig.
- „Kurzer Trend erfüllt“ bedeutet: der gerätebezogene Durchschnitt im letzten konfigurierten Trendfenster erreicht den Gerätebedarf **oder** die Differenz zum vorherigen gleichlangen Trendfenster ist mindestens neutral (≥ minus einstellbare Trendtoleranz).
- Die Kurztrendbewertung respektiert die Akkukreditierung nach Priorität und die aktuellen vorgelagerten Gerätevorreservierungen. Die gesamte benötigte Trendhistorie beträgt zweimal die Trendzeit.
- Ausnahmen: erzwungene Haushaltsstarts (Sofort/Spätstart) und WP-Sonderauslösung bei bereits laufender Warmwasserbereitung haben weiterhin ihre eigene Freigabelogik.

## Fallender Kurztrend: projizierter Bedarf (0.3.14)
Ist die Änderung zwischen den beiden Kurztrendfenstern stärker negativ als die einstellbare W-Toleranz, verlangt SEP für automatische Haushaltsgeräte und regulären WP-Boost: **letzter Trendfenster-Mittelwert + Trendfenster-Differenz ≥ Gerätebedarf**. Die beiden anderen Anforderungen (langer Mittelwert und Momentanbudget jeweils ≥ Gerätebedarf) bleiben verpflichtend. Bei neutraler oder positiver Entwicklung ist die Kurztrendprüfung erfüllt. Eine Fortschreibung ist keine meteorologische Vorhersage.

## Zeitangaben in der Gerätekarte (0.3.15)
Die Ansicht für Haushaltsgeräte und WP-Boost zeigt getrennt die eingestellte Mittelungszeit (Ø), Trendzeit (Trend) und tatsächlich vorhandene Aufzeichnungsdauer (Daten). Die Aufzeichnungsdauer kann bis rund 60 Minuten reichen und ist unabhängig von der für Freigaben konfigurierten Mittelungszeit. Nur die Darstellung wurde verändert.

## Regelung
- Der Sensor `surplus` ist der **reale Netzsaldo** (+ Einspeisung, − Netzbezug), `surplus_avg` dessen zeitlicher Mittelwert. `budget` und `budget_avg` zeigen dagegen das intern verwendete Steuerbudget.
- SEP rechnet nur tatsächlich steuerbare, unmittelbar absenkbare Leistung wieder zum Budget hinzu. Laufender WW-Boost und freigegebene Haushaltsprogramme sind bereits im Netzsaldo enthalten und werden nicht zurückgerechnet.
- Bei laufender PV-Wallbox-Ladung gilt nur der Teil oberhalb des aktuellen Mindeststroms als frei umverteilbar. Die Wallbox selbst darf ihre bereits belegte Mindestleistung für die eigene Modulation berücksichtigen.
- **Ab 0.2.22:** Die *gemessene Akkuladung* kann Geräten **oberhalb des PV-Akkus in der grafischen Prioritätenliste** als verfügbarer Überschuss angerechnet werden. Unterhalb des Speichers erfolgt keine solche Gutschrift. Voraussetzung ist, dass der Speicher seinen Ladevorgang bei zusätzlichem Verbrauch eigenständig zurückregelt. Akkuentladung wird sicherheitshalber vom PV-Budget abgezogen. Sonstige externe Überschusssenken sind weiterhin nicht pauschal rückrechenbar.
- Lasten mit höherer Priorität werden vor nachgeordneten Geräten berücksichtigt; Pflicht- und Sofortladungen können Netzstrom beanspruchen.
- Der reguläre Regelzyklus bleibt konfigurierbar. Änderungen ausgewählter Messwerte lösen schneller eine gebündelte Auswertung aus.

## E-Auto / Wallbox
- Modi: Nur PV, Fahrstreckenziel bis Uhrzeit, Tagesplanung, Sofortladung.
- Eine laufende PV-Ladung regelt ihren Sollstrom aus dem momentanen Restbudget. Die Startfreigabe nutzt weiterhin ein geglättetes Signal.
- Hardwaregrenzen beachten: Mindeststrom, maximale Stromstärke, ganze Ampere, ggf. 1-/3-Phasenwechsel sowie dessen Sperrzeit.
- Unterhalb der nötigen Leistung reduziert SEP bis zum Mindeststrom und schaltet erst nach Ablauf von `stop_delay` ab. Netzbezug ist dabei möglich.

## Batteriespeicher
- SEP kann Speicherleistung, SoC, Kapazität und PV-Prognosen berücksichtigen. Seit 0.2.22 ist der **PV-Akku als passiver Teilnehmer in der Drag-and-Drop-Prioritätenliste** enthalten; seine Position bestimmt, welche höher priorisierten Geräte gemessene Akkuladung nutzen dürfen. Die Gutschrift verwendet getrennte Messreihen für Momentanwert, 2-Minuten- und konfigurierten Mittelwert.
- Strategien: Speicher zuerst, Geräte zuerst oder prognosebasierte Entscheidung.
- **Nicht vorhanden:** Direkte Vorgabe einer Batterie-Ladeleistung, aktives Regeln eines Wechselrichters oder koordinierte Ladestromkommandos an Wallbox **und** Akku.
- Dafür sind passende schreibbare Home-Assistant-Entitäten und eine getrennt zu entwickelnde sichere Stellwertlogik nötig.

## Wärmepumpe
- Warmwasser-Boost als einmaliger Start per Button oder Schalter: SEP prüft PV-Budget, Temperatur, Hysterese, Ruhezeit und Wetterbedingungen, stößt die WW-Ladung einmal an und schaltet den Einmal-Auslöser danach nicht wieder aus.
- Optionales Lesesignal **Warmwasser aktiv** (`binary_sensor`/`input_boolean`): EIN verhindert einen weiteren Start während einer WW-Ladung, ungültig/nicht verfügbar blockiert sicherheitshalber.
- **WW-Boost Mindestabstand:** 60–720 Minuten (Standard 60 min), dauerhafter letzter Startzeitpunkt wird vor dem Aktor-Befehl gespeichert. Auch ein HA-Neustart setzt die Sperre nicht zurück.
- Ein Schalter muss wieder AUS sein, bevor er erneut eingeschaltet werden darf; Number-basierte Boosts behalten die aktive Rückstellung und bekommen ebenfalls die dauerhafte Startsperre.
- Optional Sonnenhöhenwinkel sowie zwei stündliche Bewölkungswerte als Startfilter.
- **Ab 0.2.23:** Eine optionale `input_number`-, `number`- oder `sensor`-Entität (30–75 °C) legt das WW-Boost-Temperaturziel fest. Ohne Auswahl gilt der feste Sollwert; eine konfigurierte, aber ungültige Entität sperrt neue Booststarts. Bei Sollwert-Steuerung wird dieser Wert zum Boost geschrieben. Bei einmaligem Button-/Boolean-Start wird nur der Auslöser betätigt: SEP schreibt den Temperaturwert **nicht** zusätzlich in die Wärmepumpe und schaltet einen Boolean **nicht** zurück. Das muss bei Bedarf die eigene HA-Automation übernehmen.
- Die Wetterfilter betreffen nur neue Boosts; sie ersetzen keine prognosebasierte Suche nach dem besten Boost-Zeitfenster.

## Heizstab / PV-Überschusssenke (ab 0.2.21)
- Eigener Gerätetyp mit `switch`/`input_boolean`-Stellglied, erforderlichem Temperaturwert, optionalem Leistungssensor und konfigurierbarer Nennleistung.
- Heizstab **saugt das direkt gemessene aktuelle Restbudget auf**, soweit bei einem fest schaltbaren Heizstab genügend Leistung für einen ganzen Schaltvorgang verfügbar ist. **Kein** gleitender Mittelwert oder Prognosewert bei Start und Stop. Vorrangige Vorreservierungen werden abgezogen. Ein bereits laufender Heizstab ist im Netzsaldo enthalten.
- Einstellbare **EIN-Schwelle** (Standard 2200 W, mindestens die Nennleistung), **AUS-Schwelle** (Standard 0 W), **Maximaltemperatur** (55 °C), **Hysterese** (3 K), **frühester Start** (10:00) und jeweils optionale **Mindestlauf-/Mindestpause** (Standard 0 min).
- Temperatur ungültig oder Temperatur ≥ Maximaltemperatur ⇒ AUS ohne Mindestlaufzeit. Unter max − Hysterese darf ein neuer Start erfolgen; genau an der unteren Schwelle noch nicht.
- Schaltpause nur wenn > 0 konfiguriert, Zeitstempel wird direkt nach dem Schaltbefehl persistiert. Positiver Mindestlaufzeit-Wert kann absichtlich kurzen Netzbezug zulassen; Temperatur-Sicherheit hat Vorrang.
- Modus Aus (auch Hub Aus) schaltet ab; Beobachten zeigt nur Empfehlungen, Manuell regelt die Heizstabtemperatur auch mit Netzstrom. Kein eigener stufenloser Leistungssteller.
- Die physische Sicherheitskette des Heizelements bleibt zwingend unabhängig; bei nicht lesbarer Aktor-Entität kann SEP keine physische AUS-Bestätigung garantieren.

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

## Dashboard ab 0.2.24–0.2.26
- Netzsaldo und Steuerbudget jeweils in einer kombinierten Kachel: **Ø** mit großem Durchschnitt und **akt.** mit kleinerem Momentanwert. Die Zahlen inklusive `W` sind rechtsbündig untereinander ausgerichtet.
- Die grafische Prioritätenliste einschließlich der passiven Akku-Zeile zeigt individuelle Gerätebudgets.
- Native Modus-Auswahllisten werden während der Bedienung nicht mehr durch Sensorupdates geschlossen (0.2.25); die Werte werden nach Verlassen des Feldes erneut gerendert.

