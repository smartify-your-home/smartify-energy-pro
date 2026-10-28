## 0.3.10 – Trendpfeil und Messhistorie
- Bei Haushaltsgeräten und WP-Warmwasser-Boost zeigt die SEP-Prioritätenkarte den Trend des Steuerbudgets: grüner Pfeil nach rechts oben bei positivem, roter Pfeil nach rechts unten bei negativem Trend. Bei neutralem Trend waagerecht, bei noch unzureichender Messhistorie ein Uhrsymbol.
- Anzeige der verfügbaren Messhistorie in Minuten und der eingestellten Trendzeit; vollständige Trendberechnung erfordert zwei Trendfenster, z. B. 20 Minuten Messhistorie bei 10 Minuten Trendzeit.
- Beim Ändern der Mittelungszeit oder Trendzeit werden bestehende Messwerte nicht mehr gelöscht. SEP bewahrt bis zu 60 Minuten historische Messwerte im Arbeitsspeicher, solange die Integration läuft. Nach HA-Neustart beginnt die in-memory-Historie weiterhin neu.
- Trend und Historienanzeige nur bei Haushaltsgeräten sowie Wärmepumpen-Boost; Wallbox, Heizstab, Pool und Akku erhalten keine solche Anzeige.
- Tests für die Historienerhaltung und die Geräteeinschränkung ergänzt. Kein Realgerätetest.

## 0.3.9 – SEP-Karten-Einstellungen und sofortiges Aktualisieren
- Akku-Prioritätszahl nicht mehr als unbeschriftetes Feld in den allgemeinen Hub-Einstellungen; der PV-Akku bleibt in der Prioritätenliste samt Rang-Entität erhalten.
- Einstellungsmenüs aktualisieren beim Öffnen und Schließen mit den neuesten Home-Assistant-Zuständen, auch wenn ein fokussiertes Auswahlfeld Live-Aktualisierungen zuvor zurückgestellt hat.
- Beschriftung behält den vollständigen Namen, falls das Entfernen des Präfixes ein leeres Ergebnis erzeugen würde.
- UI-Regressionstests für Akku-Priorität und Menü-Aktualisierung.

## 0.3.8 – Heizstab-Handbetrieb und vereinfachter WP-WW-Boost

Dieses Update enthält auch die Änderungen der nicht veröffentlichten Versionen 0.3.6 und 0.3.7.

- **Heizstab – Manuell:** SEP heizt temperaturgeregelt auch mit Netzstrom. Abschaltung bei Solltemperatur, erneuter Start unter Soll minus Hysterese (z. B. 50 °C / unter 49 °C). Das wiederholt sich, solange Manuell aktiv bleibt. Aus beendet das Heizen, Automatik stellt auf PV-Regelung zurück. Temperaturüberwachung und Mindestpause bleiben aktiv.
- **Vor dem Update:** War der Heizstab bisher auf Manuell, bei unerwünschter Nachheizung vorher auf Aus stellen. Manuell bedeutete bisher keine SEP-Steuerung und erlaubt jetzt aktives Heizen mit Netzstrom.
- **Nur WP-WW-Einmalladung:** Automatik, Beobachten, Deaktiviert. Die bisherigen Einstellungen Manuell/Aus werden zu Deaktiviert übernommen. Deaktiviert startet keinen neuen Boost; eine laufende WW-Ladung wird nicht unterbrochen. Andere Geräte und der WP-Zahlensollwert behalten ihre Modi.
- **Nach dem Update:** Home Assistant neu starten, danach das Dashboard neu laden. Bei weiterhin alter Kartendarstellung den Browser-Cache aktualisieren.
- **Release-Korrektur:** Falsches Netzsaldo-Vorzeichen im neuen HA-Integrationstest korrigiert. Die Veröffentlichung von 0.3.6/0.3.7 war deshalb blockiert; keine Abschwächung der Testaussage.
- README (auch HACS-Infoseite), Funktionsstand, Update-Anleitung und Release-Hinweise aktualisiert. Kein Test an realer Heizstab-/WP-Hardware.

## 0.3.7 – Deaktiviert für WP-WW-Einmalladung
- Nur bei der WP-WW-Einmalladung werden Manuell und Aus zu Deaktiviert zusammengeführt. Auswahl: Automatik, Beobachten, Deaktiviert.
- Bestehende manuelle/ausgeschaltete Einmalladungen bleiben deaktiviert; laufende WW-Ladungen und Auslöser werden nicht zurückgesetzt.
- Heizstab und alle anderen Gerätetypen einschließlich WP-Zahlensollwert behalten ihre bisherigen Modi.
- Dashboard-Hilfe, HA-Übersetzungen, README, Funktions- und Update-Dokumentation angepasst. Regressionstests für Migration, laufende Ladung und unveränderte Zahlensollwert-Modi.

## 0.3.6 – Heizstab mit temperaturgeregeltem Handbetrieb
- Manuell regelt den Heizstab auf die eingestellte Solltemperatur, unabhängig vom PV-Budget, frühester Startzeit und Prioritätspause. Netzbezug ist ausdrücklich erlaubt.
- Wiederanlauf unter Soll minus Hysterese; wiederholtes Heizen, solange Manuell gewählt bleibt. Mindestpause, Temperaturabschaltung, ungültiger Temperatursensor und Geräte-/Hub-Aus bleiben wirksam.
- Manuelle Heizleistung ist nicht rücknehmbar. Noch ungemessene Leistung wird vor automatischen PV-Freigaben reserviert.
- Dashboard-Hilfe, Modusanzeige, README, Funktions- und Update-Dokumentation ergänzt. Verhaltensänderung: bisheriges Manuell war ohne SEP-Steuerung; vor Update bei unerwünschter Nachheizung Aus wählen.
- Regressionstests für Netzbezug, Hysterese, Sensorfehler, Hub-Aus, Mindestpause und Rückkehr zur Automatik; kein Test an realer Heizstab-Hardware.

## 0.3.5 – Phasenumschaltung einstellbar
- Wallbox mit 1/3-Phasen-Umschaltung: neuer Mindestabstand zwischen zwei Umschaltungen (5–60 min, Standard 20 min; bisher fest 10 min) und neue Hysterese um die Dreiphasen-Mindestleistung (0–1500 W, Standard 500 W; bisher fest 300 W).
- Beispiel 6 A Mindeststrom: dreiphasig ab ca. 4,6 kW, zurück auf einphasig unter ca. 3,6 kW.
- Hilfetexte in der Card, deutsche/englische Bezeichnungen, Regressionstests. Keine bestätigte Prüfung an realen Geräten.

## 0.3.4 – Sichere prioritätsabhängige Lastverdrängung
- Nachrangige, gemessene Heizstäbe und freiwillige PV-Wallboxladung können vor dem Start einer höher priorisierten Waschmaschine oder eines Geschirrspülers zurückgenommen werden; Mindestlaufzeit, Modus und Aktorverfügbarkeit gelten weiter.
- Neue Absicherung: keine unnötige Unterbrechung, wenn die Summe der rücknehmbaren Leistung das Leistungsdefizit nicht deckt; bereits an vorrangige Geräte anrechenbare, nachrangige Akku-Ladung fließt in diese Vorprüfung ein.
- Abschaltbefehle zählen nie sofort als tatsächlich verfügbare Leistung: Freigabe erst nach Messwertänderung und normalen Momentan-/Mittelwert-/Trendprüfungen. Kurzfristige Wiedereinschaltung nach Rücknahme wird verhindert.
- Externe Überschusssenken und Ohmpilot unverändert; keine eigene Priorisierung. PV-Akku weiterhin nur durch bestehende externe Nachregelannahme berücksichtigt, nicht aktiv gesteuert.
- Regressionstests für Prioritäten, Mindestlaufzeit und unzureichende rücknehmbare Leistung. Kein End-to-End-Test an realer Wallbox/Heizstab-Hardware.

## 0.3.3 – Überschuss-Senken (Ohmpilot/Heizstab) im Budget
- Selbstregelnde Überschuss-Senken wie Ohmpilot oder Heizstab zählen jetzt zum Steuerbudget: Ihre Leistung steht den SEP-Geräten zur Verfügung, die Senke regelt selbst zurück und nimmt nur den restlichen Überschuss.
- Neuer Hub-Schalter **Überschuss-Senken weichen aus** (Standard ein, nur bei konfigurierten Senken). Aus = bisheriges Verhalten, Senken werden nur angezeigt.
- **Breaking Change für Templates:** Attribut `senken_nur_information_w` heißt jetzt `senken_w`; neu `senken_im_budget` (true/false).
- Voraussetzung: Die Senke regelt schnell zurück. Bis dahin kann kurz Netzbezug entstehen. Keine bestätigte Prüfung an realen Geräten.

## 0.3.2 – Automatischer Reset nach „Fertig“ und kompaktere Gerätezeilen
- Haushaltsgeräte (Waschmaschine, Geschirrspüler, Trockner): Ein neuer Programmstart nach „Fertig“ wird automatisch erkannt (5 s stabil über 9 W) und setzt die Erkennung zurück. Der Reset-Button ist nur noch optional.
- Ohne Leistungssensor: Die Steckdose muss nach „Fertig“ einmal aus- und wieder eingeschaltet werden, damit ein neuer Lauf erkannt wird.
- Nicht unterbrechbare Trockner wechseln beim neuen Programmstart direkt auf „läuft“; die Steckdose bleibt unangetastet.
- Card: Modus-Hilfetext im Auswahlfeld (z. B. „Automatik · SEP steuert“), Auswahlfeld neben dem Zahnrad, niedrigere Zeilen.
- Regressionstests für automatischen Reset ergänzt. Keine bestätigte Prüfung an realen Geräten.

## 0.3.1 – Mittelungszeit und PV-Trend separat einstellbar
- SEP-Hub: Mittelungszeit 1–60 Minuten (Standard 20) und Trendzeitraum 1–30 Minuten (Standard 10) unabhängig einstellbar; bestehende gespeicherte Mittelungswerte bleiben erhalten.
- Automatischer PV-Start von Waschmaschine, Geschirrspüler und wiederanlauffähigem Trockner benötigt zusätzlich zu aktuellem und durchschnittlichem Gerätebudget einen stabilen Trend: Mittelwert des jüngsten Trendfensters minus vorheriges Trendfenster mindestens minus Trendtoleranz (0–500 W, Standard 100 W).
- Bei unvollständiger Trendhistorie bleibt die automatische Freigabe aus. Sofort-/Spätstart und bereits laufende Programme werden nicht blockiert oder unterbrochen.
- Deutsche und englische Bezeichnungen für alle neuen SEP-Zahlen-Entitäten.
- Softwareprüfung im GitHub-Workflow; keine Bestätigung für reale Hardwaregeräte.

## 0.3.0 – Recorder, reaktive Regelung und HA-Qualität
- Recorder entlastet: Budget-/Planattribute nicht aufzeichnen, identische Zustände nicht schreiben; Live-Werte gebündelt veröffentlichen.
- Keine verlorenen Regelläufe: während eines laufenden Zyklus angeforderte Neubewertungen unmittelbar nachholen.
- Aktoraufrufe auf 10 Sekunden begrenzt, 30 Sekunden Wiederholpause nach Fehlern, Reservierung bei unsicherem Befehlsausgang erhalten. Unbekannte/nicht verfügbare Aktoren werden in allen Gerätetypen gesperrt.
- Statussensoren als übersetzte ENUMs mit englischen Codes. **Breaking Change für Templates mit Rohzustandsvergleichen:** z. B. `wartet` → `waiting`, `laeuft` → `running`. IDs bleiben erhalten; `legacy_status` und deutsche Detailattribute bleiben verfügbar. Vollständige Zuordnung: [Migrationshinweise](docs/REVIEW_0.3.0.md).
- Vollständige Übersetzungen einschließlich Trockner, verständliche Dienstfehler, datensparsamer Diagnose-Download.
- Speicherstrategie nutzt letzte positive Prognosestunde; Entity-Beobachtung explizit und schnelle Eingänge zwischengespeichert.
- Card aktualisiert bestehende DOM-Elemente statt vollständigem Neuaufbau; Fokus/Dropdowns bleiben geschützt.
- Ein gemeinsamer geprüfter Release-Workflow, Manifest als einzige Versionsquelle, HA-Mindestversion 2025.7.0. CI mit hassfest, HACS, Ruff, echten HA-Tests, Übersetzungsabgleich und DOM-Tests.
- Keine bestätigte Prüfung an realen Aktoren; Softwaretests ersetzen keinen HA-Anlagentest.

## 0.2.32 – Optionaler PV-Forecast als alternativer WW-Startfilter
- Neue Auswahl **Kein Filter / Bewölkung / PV-Forecast** in den SEP-Wärmepumpen-Geräteeinstellungen. Bestehende Bewölkung-Aktivierung und Grenzwerte werden übernommen.
- Vorhandene SEP-Prognose für die nächsten **1 oder 2 Stunden ab jetzt**, anteilig je Stunde; Mindestenergie **0,1–100 kWh**, Standard **2 kWh in 2 Stunden**. Forecast und Bewölkung werden alternativ geprüft.
- Fehlende, unvollständige, fehlerhafte oder über 60 Minuten alte Prognose sperrt im Forecast-Modus neue Starts. Diagnoseattribute und verständliche deutsche/englische Bezeichnungen sowie Hilfetexte ergänzt.
- Die Sonderfreigabe während laufender WW-Bereitung ignoriert weiterhin Bewölkung und Forecast. Temperaturhysterese, Budget, Wartezeit, Startsperre und optionaler Sonnenwinkelfilter bleiben wirksam. Laufende Boosts werden durch den Startfilter nicht abgebrochen.
- README und Update-Anleitung ergänzt; Regressionstests für Zeitfenster, Grenzwerte, Migration, alternative Filter und laufende WW-Bereitung ergänzt. Kein bestätigter HA-Hardwaretest.

## 0.2.31 – Bewölkung bei laufender WW-Bereitung ignorieren
- Die Sonderfreigabe während laufender WW-Bereitung berücksichtigt keine Bewölkung (aktuelle/kommende Stunde), auch keine fehlenden Bewölkungswerte. Für die Leistungsfreigabe zählt das aktuelle prioritätsbereinigte Steuerbudget ≥ 0 W.
- Wartezeit (0 deaktiviert), Temperatur strikt unter Zieltemperatur minus Hysterese, optionaler Sonnenwinkelfilter, Startsperre und maximal ein Boost je WW-Zyklus bleiben erhalten. Normale Starts und Number-Boosts behalten ihre Bewölkungsfilter.
- Hilfetexte, README und Update-Anleitung aktualisiert; Regressionstests für Bewölkung, fehlende Werte, Temperaturgrenze und negatives Budget ergänzt.

## 0.2.30 – Einstellbare WW-Aktiv-Wartezeit
- Neue Einstellung **WW aktiv: Wartezeit bis Boost** in Gerätekonfiguration und SEP-Geräteeinstellungen: 0–180 Minuten (0 deaktiviert die Sonderfreigabe), Standard 10 Minuten. Bestehende Geräte behalten das bisherige Verhalten; Änderungen werden gespeichert.
- Enthält die bisher unveröffentlichte Freigabe aus 0.2.29: einmaliger Boost während laufender WW-Bereitung nach der Wartezeit bei aktuellem prioritätsbereinigtem Steuerbudget ≥ 0 W. Temperatur, Wetterfilter, Startsperre und maximal ein Boost je WW-Zyklus bleiben wirksam; Number-Sollwertsteuerung unverändert.
- Deutsche/englische Hilfetexte, dynamische Wartemeldung, Diagnosewert, README und Update-Anleitung aktualisiert. Regressionstests für Wartezeitgrenzen, Budget, Zyklus und Wiederherstellung ergänzt; Test-Fixtures korrigiert.

## 0.2.29 – WW-Boost nach zehn Minuten laufender Warmwasserbereitung
- Einmaliger Boost per Button, Schalter oder Input-Boolean ist jetzt auch während aktiver WW-Bereitung zulässig: WW-Aktiv-Signal seit mindestens 10 Minuten ununterbrochen EIN und aktuelles prioritätsbereinigtes Steuerbudget ≥ 0 W.
- Für diesen Sonderfall entfallen die normale Nennleistungs-Schwelle und WP-Ruhewartezeit, da die Wärmepumpe bereits läuft; Zieltemperatur/Hysterese, Wetterfilter und mindestens 60 Minuten Startsperre gelten weiterhin.
- Maximal eine Boost-Auslösung je beobachtetem WW-Zyklus; Diagnoseattribute für WW-Aktivdauer und bereits erfolgte Auslösung ergänzt. Number-Sollwert-Boost bleibt unverändert.

## 0.2.28 – Kritischer Startfehler behoben
- Die Optionsübersetzungen für den Trockner-Wiederanlauf waren irrtümlich als JSON-Liste statt als Schlüssel-Text-Objekt hinterlegt. Home Assistant 2026.10 brach deshalb beim Laden der Übersetzungen mit `TypeError: expected str, got list` ab und markierte sämtliche SEP-Entitäten als `unavailable`.
- Deutsche und englische Übersetzungen auf das korrekte Format umgestellt; bestehende Einstellungen und gespeicherte Werte bleiben unverändert.
- Die neue Typauswahl für Haushaltsgeräte (Waschmaschine, Geschirrspüler, Sonstiges) bleibt erhalten.

## 0.2.27 – Eigenes Wäschetrockner-Modell

- Neuer Untereintrag **Wäschetrockner** mit standardmäßig 800 W Leistungsbedarf und 2,5 h Programmdauer.
- Dauerlastreservierung über die gesamte freigegebene Laufzeit statt Heizphasenende wie bei Waschmaschine/GS; berücksichtigt tatsächliche Messung ohne Doppelzählung.
- **Wiederanlauf nach Stromausfall** muss vom Benutzer am konkreten Trockner geprüft und ausdrücklich bestätigt werden. Standard `Nein`: SEP schaltet die Steckdose niemals, Trockner läuft nur manuell und wird überwacht. Option `Ja`: PV-Startsteuerung über die Steckdose zulässig; nach Freigabe keine PV-bedingte Unterbrechung.
- Testhinweis: Zunächst im Modus Beobachten prüfen, dann Schaltverhalten beaufsichtigen.

## 0.2.26 – Netzsaldo/Steuerbudget bündig anzeigen

- Im kompakten SEP-Header stehen die Kennzeichen **Ø** und **akt.** in einer eigenen Spalte unterhalb der jeweiligen Überschrift.
- Durchschnitt und aktuelle Leistung werden in einer gemeinsamen Zweispalten-Anordnung dargestellt: Zahlen und Watt-Einheit sind rechtsbündig exakt untereinander ausgerichtet.
- Der aktuelle Wert ersetzt die bisherige Bezeichnung „Ist“; Live-Werte und Steuerlogik bleiben unverändert.

## 0.2.25 – Modus-Auswahl bleibt während Sensorupdates geöffnet

- Der SEP-Header und die Geräteeinstellungen werden bei Live-Sensorupdates **nicht mehr vollständig neu gerendert**, während ein Auswahlfeld (z. B. Automatik / Beobachten / Manuell / Aus) fokussiert ist.
- Der vorherige Schutz für Zahlen- und Uhrzeitfelder bleibt bestehen. Nach Verlassen des Auswahlfeldes werden die zwischenzeitlich eingegangenen Sensorwerte automatisch nachgezeichnet.
- Steuerlogik und WW-Boost-Boolean bleiben unverändert.

## 0.2.24 – Kompakte Saldo-Anzeige im SEP-Header

- Vier separate Kacheln für Netzsaldo und Steuerbudget (Ist und Durchschnitt) werden zu zwei kompakten Kacheln zusammengefasst.
- Je Kachel erscheint der **Durchschnittswert groß**, darunter der **Ist-Wert kleiner**. Die Anzeige des Netzbezugs bleibt negativ; Netzsaldo und Steuerbudget bleiben zwei verschiedene Messgrößen.
- Weitere Kacheln (Verteilt, Prognose, Speichervorrang) bleiben erhalten. Durch Antippen der oberen Kachel öffnet sich die gemittelte Sensorentität; Ist-Wert hat eigenen Info-Aufruf.
- Unveränderte WW-Boost-Boolean-Logik: Eine externe Automation übernimmt weiterhin das Zurücksetzen.

## 0.2.23 – WW-Boost-Temperatur per Entität

- Im Wärmepumpen-/WW-Boost-Gerät kann optional eine Entität **WW-Boost Solltemperatur** (`input_number`, `number` oder `sensor`) ausgewählt werden.
- Ihr aktueller Wert (30–75 °C) ersetzt die feste **Zieltemperatur** für die Startprüfung mit Hysterese und das Temperaturziel bei laufender Sollwertregelung.
- Bei einem als `number` gesteuerten Boost wird dieser Wert auch als Boost-Sollwert geschrieben; die bisherige **Normal-Sollwert**-Rückstellung bleibt erhalten.
- Ohne Auswahl gilt weiterhin die bisherige SEP-Zieltemperatur. Ist eine ausgewählte Entität ungültig oder nicht verfügbar, wird ein neuer WW-Boost sicher gesperrt; der konfigurierte Wert und die Quelle erscheinen als Statusattribute.
- Bei Button-/Schalter-Boost wird weiterhin nur der Start ausgelöst; die WP übernimmt ihren eigenen WW-Sollwert. Dieser wird durch die neue SEP-Entität **nicht** physisch in die WP geschrieben.

## 0.2.22 – PV-Akku in der Prioritätenliste

- **PV-Akku als verschiebbare Zeile** im SEP-Prioritätenmanager (bei konfiguriertem Akku-Leistungs-/SoC-Sensor); zeigt Ladeleistung und SoC. Position wird als `number.*battery_rank` im Hub gespeichert.
- **Priorisierte Saldo-Logik:** Nur Verbraucher **oberhalb** des PV-Akkus dürfen dessen gemessene Ladung zum aktuellen Gerätesaldo hinzurechnen. Geräte **unterhalb** des Akkus erhalten diese Leistung nicht erneut.
- Der Speicher bleibt **passiv selbstregelnd**: SEP gibt keine Batteriebefehle aus. Damit eine höhere Verbraucherpriorität physisch durchgesetzt werden kann, muss der Speicher seine Ladung automatisch reduzieren, sobald Netzexport sinkt beziehungsweise Hausverbrauch steigt.
- Laufende Akkuladung wird nicht doppelt vom Netzsaldo abgezogen. Akku-Entladung wird wie zuvor beim Budget abgezogen; sie ist keine frei verfügbare PV.
- Akkuladung wird aus echten Messwerten separat als **Momentanwert, 2-Minuten-Mittelwert und konfigurierter Langzeitmittelwert** geführt. Nur Geräte vor dem Akku dürfen diese Leistung in ihrem jeweiligen Prüffenster anrechnen. Damit erhalten auch Haushaltsgeräte und das E-Auto eine korrekte Startprüfung, wenn der Akku vorher alles geschluckt hat. Der PV-Akku bleibt ein virtuelles Gerät ohne HA-Aktor oder Ladeleistungsbegrenzung.

## 0.2.21 – Heizstab als sofort reagierende PV-Restverbrauchssenke
- **Neuer Gerätetyp „Heizstab / PV-Überschusssenke“**, unabhängig von Haushaltsgeräten, Pool und WP-Boost. Ansteuerung über `switch` oder `input_boolean`, obligatorischer Warmwasser-Temperatursensor, optionale echte Heizstab-Leistungsmessung.
- Nur **aktuelles Steuerbudget**, ausdrücklich **kein 10-Minuten-Mittelwert**: Bei ausreichend unmittelbar verfügbarem Restbudget EIN, bei Netzbezug bzw. Unterschreitung der konfigurierten Stoppschwelle AUS. Die Reservierungen höher priorisierter Geräte werden berücksichtigt. Der eigene laufende Verbrauch ist bereits im physikalischen Netzsaldo enthalten und wird nicht nochmals abgezogen.
- Parameter: Heizleistung (2000 W), PV-Startschwelle (2200 W), PV-Stoppschwelle (0 W), Maximaltemperatur (55 °C), Hysterese (3 K), frühester Start (10:00), optionale Mindestlaufzeit (0 min) und Mindestpause (0 min); sämtliche Zahlen und Uhrzeit über SEP-Entities konfigurierbar.
- Fehlt ein gültiger Temperaturwert oder ist die maximale Temperatur erreicht, schaltet SEP den Heizstab auch während der Mindestlaufzeit **sofort AUS**. Modus Aus schaltet ebenfalls AUS. Eine unabhängige thermische Sicherheitseinrichtung ist weiterhin erforderlich.
- Die Schaltzeitpunkte werden nach tatsächlichem Serviceaufruf dauerhaft gespeichert und über HA-Neustarts fortgeführt. Bei manuellen Änderungen wird ein Zustandswechsel erkannt, soweit der Schaltzustand lesbar ist.
- Neue Tests für fehlenden Mittelwert, aktuellen Überschuss, aufeinanderfolgende Geräteleistungen, Temperatur-Hysterese, Sicherheitsabschaltung, früheste Uhrzeit, Neustart und die Schaltentitäten `switch` / `input_boolean`.
- **Achtung:** Bisherige Automationen für denselben Relaisausgang deaktivieren, damit SEP und sie nicht gegeneinander schalten.

## 0.2.20 – Aktuelles Einzelbudget pro Gerät und kombinierte Heizreservierung
- Die Freigabe des nächsten PV-Haushaltsgeräts bewertet **aktuelles** und **gemitteltes** Steuerbudget getrennt und berücksichtigt in beiden Budgets alle noch offenen Heizleistungs-Reservierungen vorheriger Geräte. Ein hoher alter Mittelwert ersetzt niemals eine zu geringe momentane Leistung.
- Im Grundsatz: PV-Budget jetzt − Vorreservierungen ≥ erwartete Heizlast des nächsten Geräts **und** PV-Budget Mittelwert − Vorreservierungen ≥ erwartete Heizlast. Bereits tatsächlich gemessener Verbrauch wird nicht doppelt abgezogen; die noch nicht eingetretene Heizlast bleibt vollständig reserviert.
- Die Zustandsmeldung zeigt bei einer Ablehnung jetzt **aktuell / Ø / benötigt / Vorreservierungen** nachvollziehbar an.
- In der **Prioritätenliste** steht direkt neben der gemessenen Geräteleistung das **aktuell pro Gerät verfügbare Budget**; darunter der Mittelwert und die Reservierungen der weiter oben eingeplanten Verbraucher. Die Ansicht wird mit jedem Regelzyklus aktualisiert. Statusattribute und die „Verteilt“-Sensorattribute enthalten ebenfalls diese Werte.
- Regressionstests simulieren zwei gleichzeitige 2-kW-Heizer, alten hohen Mittelwert, zu niedrigen aktuellen Wert, drei Geräte mit dritter Ablehnung, tatsächlich gemessene Heizleistung und Ende der Heizphase.
- Bereits freigegebene Programme werden bei später fehlender Sonne weiterhin nicht abgeschaltet; Sofort- und Spätstarts behalten ihre Ausnahmen. Die historische Wärmepumpen-Abtauhaltezeit des früheren **saldo_manager** wurde nicht übernommen: Dessen beabsichtigte 15-min-Nennleistungs-Haltezeit enthielt eine vorzeitige Rücksetzung und war nicht zuverlässig.

## 0.2.19 – Veraltete PV-Freigabe bei Haushaltsgeräten korrigiert
- Laufende freigegebene Haushaltsgeräte zeigen nicht länger den bei Programmstart gemessenen Überschuss als angeblich aktuellen Wert; sie melden stattdessen „Programm läuft – bereits freigegeben“.
- Eine reguläre PV-Freigabe wird nicht mehr fälschlich als Pflicht-Start gekennzeichnet. Sofortfenster, Spätstart und manueller Sofort-Start bleiben erzwungene Freigaben.
- Bereits freigegebene Programme werden durch sinkendes PV-Budget weiterhin nicht unterbrochen.

## 0.2.18 – Heizphasenkalkulation und paralleler PV-Start
- Die bisherige pauschale Sperre „Anderes Gerät in Heizphase“ wurde entfernt. Ein wartendes zweites Haushaltsgerät darf auch dann starten, wenn das verbleibende reale und gemittelte Steuerbudget für seine erwartete Heizleistung reicht.
- Jedes freigegebene Haushaltsgerät reserviert vor dem Ende seiner Heizphase die Nennleistung. Bereits **tatsächlich gemessene** Leistung wird nicht doppelt als noch zu reservieren abgezogen; nach einer abgeschlossenen Heizphase entfällt die zusätzliche Heizreservierung.
- Ohne gültige Leistungsmessung wird die erwartete Heizlast vorsichtshalber vollständig reserviert, anstatt eine nicht gemessene Nennleistung als bereits verbraucht anzurechnen.
- Neue Starts benötigen in PV-Automatik mindestens **max(Nennleistung, konfigurierter Mindest-Überschuss)**, sowohl im Momentanwert als auch im reifen, einstellbaren Mittelwert. Damit führt z. B. 1500 W als Mindest-Überschuss nicht zur Freigabe eines erwarteten 2200-W-Heizers bei nur 1500 W freiem PV-Budget.
- Bei einem gerade erst erkannten, noch eingeschalteten Programm wird die **eigene tatsächlich gemessene** Leistung nur für die eigene Startprüfung zum momentanen Budget berücksichtigt. Für andere Verbraucher wird diese Leistung nicht freigegeben.
- Prioritäten, späteste Startzeit, Sofortfenster und ausdrücklich manueller Sofortstart bleiben wirksam. Die Änderung setzt vorhandene Einstellungen nicht zurück.
- Erweiterte Regressionstests für parallele Heizphasen, Heizlast-Reservierung, Ende der Heizphase, fehlenden Zähler und fehlendes aktuelles/mittleres PV-Budget.
- [SEM-zu-SEP-Entitätsnamen und Migrationshinweise](docs/SEM_ENTITY_MIGRATION.md) dokumentiert.

## 0.2.17 – WW-Aktiv-Rückmeldung und dauerhafte Boost-Startsperre
- Optionales Feld **Warmwasser aktiv** im Wärmepumpen-Konfigurationsformular (nur `binary_sensor` oder `input_boolean`). Wenn EIN, gibt SEP keinen neuen WW-Boost aus; bei nicht verfügbarem konfiguriertem Signal wird ein neuer Start vorsorglich gesperrt.
- Button-/Schalter-Boosts lösen ausschließlich einen **einmaligen WW-Start** aus. SEP beendet die danach laufende Warmwasserladung nicht wegen Netzbezug, Bewölkung oder Modus Aus. Ein Schalter muss extern wieder AUS werden, um eine neue Auslösung zu ermöglichen.
- Neue Geräteeinstellung **WW-Boost Mindestabstand**: Standard **60 Minuten**, einstellbar **60–720 Minuten**. Die harte Untergrenze von 60 Minuten garantiert höchstens einen Start pro Stunde.
- Vor dem Aktor-Befehl wird der Auslösezeitpunkt unverzüglich in HA Storage geschrieben. Die Sperre bleibt so auch bei einem HA-Neustart oder fehlgeschlagenem/unsicherem Aktoraufruf erhalten. Vorhandene Startzeitstempel älterer SEP-Versionen werden übernommen.
- Die normalen Prüfungen auf PV-Budget, Temperatur, WP-Ruhezeit sowie optional Sonne und Bewölkung gelten weiterhin **nur für den Start**.
- Number-basierte Sollwert-Boosts behalten die aktive Rückstellung, erhalten aber ebenso die dauerhaft gespeicherte Startsperre. FBH bleibt außerhalb des Funktionsumfangs.
- Automatisierte Regressionstests für 60-/125-Minuten-Sperre, Neustart, WW-Aktiv-Sensor, Sensorfehler und Einmalbefehl ergänzt.

## 0.2.16 – Echtes Netzsaldo und sicheres Steuerbudget
- Die bestehende Entität `surplus` zeigt jetzt den gemessenen signierten Netzsaldo: Einspeisung positiv, Netzbezug negativ. `surplus_avg` ist der Mittelwert dieses echten Netzsaldos.
- Neue Entitäten `budget` und `budget_avg` zeigen das getrennte, für die SEP-Regelung verwendete Steuerbudget.
- Laufende WW-Wärmepumpen-Ladungen, nicht unterbrechbare Haushaltsprogramme, Pflichtläufe und unveränderliche Lasten werden nicht länger fälschlich als frei verfügbarer Solarüberschuss addiert.
- Im EV-PV-Modus wird nur die oberhalb des aktuellen Mindest-Ladestroms sofort reduzierbare Leistung als umverteilbar anerkannt; die bereits laufende Mindestleistung wird nur der Wallbox selbst zugerechnet.
- Leistung von rein externen Überschuss-Senken und Speicherladeleistung wird ohne SEP-Stellmöglichkeit nicht mehr als frei verteilbar vorausgesetzt. Speichereinspeisung ins Haus wird weiterhin vorsichtig vom PV-Budget abgezogen.
- Bestehender Verbrauch wird bei der Reservierung nicht doppelt abgezogen; Beobachten/Manuell bucht keine hypothetischen Schaltbefehle als real verteilt.
- Wartende Haushaltsprogramme benötigen für PV-Freigabe jetzt sowohl den positiven geglätteten als auch den ausreichenden momentanen Wert; ein positiver historischer Mittelwert allein reicht bei aktuellem Netzbezug nicht.
- WW-Boost-Steuerung und FBH bleiben in dieser Korrektur unverändert. Regressionstests für Netzbezug und Gerätelasten ergänzt.

## 0.2.15 – PV-Pausen kompakt darstellen
- Stunden ohne prognostizierten PV-Ertrag werden in der Zeitleiste nicht mehr als einzelne Balken angezeigt. Eine kompakte markierte Lücke zeigt den übersprungenen Zeitraum als „Nacht“ oder „PV-Pause“; genaue Dauer per Tooltip.
- Planungshorizont bleibt bis zum Ende des morgigen Tages erhalten.

## 0.2.14 – PV-Plan einschließlich des ganzen morgigen Tages
- Der Planungszeitraum reicht ab der aktuellen Stunde bis zum Ende des morgigen Kalendertages (00:00 Uhr übermorgen).
- Auch Stunden ohne Sonnenleistung werden in der Prognosezeitleiste gezeigt; frühere Anzeigegrenzen von 24/36 Stunden entfallen.

## 0.2.13 – Prioritätsanzeige und Drag & Drop repariert
- Fehler korrigiert: Nach Entfernung der Prioritäts-Zahlen-Entitäten zeigte die grafische Übersicht für jedes Gerät `?` und erwartete nicht mehr vorhandene Entitäten.
- Geräte werden jetzt aus ihrem Status ermittelt und die gespeicherte Priorität als Zahl aus dem Statusattribut `prioritaet` angezeigt.
- Die Reihenfolge wird über den eigenen Dienst `smartify_energy.set_priority_order` gespeichert. Eine sichtbare `number.priority`-Entität wird dafür nicht mehr benötigt.

## 0.2.12 – Bezeichnung der Startzeiten
- Haushaltsgeräte: Anzeigename der Zeit-Entität auf **„Frühester Start“** vereinheitlicht; **„Spätester Start“** bleibt bestehen.
- Keine Änderung der technischen Entitätsschlüssel oder gespeicherten Zeitwerte.

## 0.2.11 – Planungsanzeige bei Moduswechsel
- Fehler behoben: Nach dem Schalten eines Geräts (z. B. WP-Boost) auf „Aus“ wird die grafische Prognoseplanung unmittelbar neu berechnet; veraltete Boost-Balken bleiben nicht bis zum nächsten 15-Minuten-Planungsintervall stehen.
- Regelmäßiger Prognose-Abruf bleibt im bisherigen Intervall; eine Einstellungsänderung erzwingt nur die Neuplanung.

## 0.2.10 – Startzeit und grafische Priorisierung vorbereiten
- Haushaltsgeräte: neue einstellbare Uhrzeit **Frühester automatischer Start** (Standard 00:00). Sperrt automatische PV-, Spätstart- und Sofortfensterfreigabe bis zur Uhrzeit. Manueller Sofort-Start bleibt möglich.
- Prioritätseingaben (number-Entities) aller Gerätetypen aus der angezeigten Parameterauswahl entfernt. Gespeicherte Prioritäten bleiben erhalten und werden intern berücksichtigt; grafische Bedienung folgt separat.

# Änderungsprotokoll – Smartify Energy Pro

## Anzeigename (26.10.2026)
- Anzeigename in Home Assistant (Manifest und Standardname) auf **Smartify Energy Pro** vereinheitlicht. Die Integrationsdomain `smartify_energy` bleibt für bestehende Installationen unverändert. Vorhandene, individuell benannte Integrationseinträge behalten unter Umständen ihren bisherigen Eintragstitel; diese können in Home Assistant umbenannt werden.


Die Versionsnummer bezeichnet die Home-Assistant-Integration. Angaben zur Reaktionszeit beziehen sich auf die interne Planung und sind **keine garantierten Hardware-Schaltzeiten**. Eine Prüfung an einer realen Home-Assistant-Anlage steht noch aus.

## Korrektur des Standardwerts (26.10.2026)
- Mindestüberschuss bei **neu angelegten Haushaltsgeräten** jetzt **+1.500 W** statt −1.000 W. Bestehende Einstellungen werden nicht überschrieben. Die übrigen SEM-v3-Zustandsregeln bleiben unverändert.

## 0.2.9 – Haushaltsgeräte an SEM v3 angeglichen (26.10.2026)
- Programmerkennung bei eingeschalteter Steckdose nun erst nach 5 Sekunden stabil über 9 W (ohne Sensor über den Schaltzustand).
- Abschlusszustand „Fertig“ bleibt bis zum ausdrücklichen Reset erhalten; kein automatischer Neustart allein durch wieder steigende Leistung.
- Standardwerte für **neue** Haushaltsgeräte aus SEM v3: Mindestüberschuss -1000 W, Spätstart 16:00, Fertigerkennung 2 Minuten; Heizphasenerkennung > max(200 W, 8 % Nennleistung) über 10 Sekunden.
- Bei erstem Leistungsanstieg >100 W wird die Freigabe geprüft; bereits freigegebene Programme laufen weiter.
- Unterschied zur SEM-Vorlage: SEP verwendet die manuell festgelegten Geräteprioritäten anstelle der ausschließlich zeitlichen Reihenfolge. Die 10-Minuten-Mittelwertprüfung und Heizphasen-Sperre für wartende Geräte bleiben erhalten.
- Diese Änderungen sind im Repository umgesetzt, aber **nicht auf einer realen HA-Installation getestet**.
- Bei bestehenden Geräten bleiben bereits gespeicherte Parameterwerte unverändert.

## 0.2.8 – Schnellere Wallbox-Regelung (26.10.2026)
- Änderungen des Netzleistungssensors, des konfigurierten Speicher-Leistungssensors sowie von Wallbox-Leistungs- und Stromsensoren stoßen eine gebündelte Neubewertung mit ca. 0,5 s Verzögerung an; andere verfolgte Entitäten weiterhin ca. 2 s. Der reguläre Zyklus läuft zusätzlich.
- Eine bereits laufende PV-Ladung berechnet ihren Strom nun aus dem momentanen Restbudget einschließlich vorrangiger Reservierungen, nicht länger aus dem geglätteten 2-Minuten-Wert.
- Bei fallendem Überschuss wird der Sollstrom soweit möglich bis zum konfigurierten Mindeststrom reduziert. Darunter bleibt die Abschaltverzögerung wirksam; dadurch kann vorübergehend Netzbezug entstehen.
- Beim PV-Ladestart bleibt eine geglättete Startbedingung bestehen. Stromregelung erfolgt in ganzen Ampere; die Phasenumschalt-Sperrzeit bleibt bestehen.
- **Keine direkte Speicher-Ladestromsteuerung** implementiert. SoC, Speicherleistung, Prognose und Priorität fließen in die Verteilung ein.

## 0.2.7 – Optionale WP-Boost-Startfilter
- Optionaler Mindest-Sonnenhöhenwinkel und getrennte Obergrenzen für Bewölkung dieser und der kommenden Stunde.
- Eigene Aktivierung pro Filter; fehlende Einstellungen deaktivieren den jeweiligen Filter.
- Vollständig aktivierte Filter sperren neue Starts bei ungültigen Messwerten; laufende Boosts bleiben davon unberührt.
- Beschreibung und Diagnosewerte im Gerät ergänzt.

## 0.2.6 – Zentraler Modus Aus
- Beim Ausschalten des Hauptschalters werden Steckdosen angelegter Haushaltsgeräte freigegeben und deren Programmerkennung zurückgesetzt; nicht für Pool, Wallbox und WP.

## 0.2.5 – Erklärungen in der Bedienoberfläche
- Deutsche Hilfetexte bei Einrichtung, Gerätekonfiguration, Parametern und Priorität; Bedienung auch ohne Hover.

## 0.2.4 – WP-Ruhezeit einstellbar
- Ruhezeit vor Boost von festen 15 Minuten auf einstellbare 0–180 Minuten (0 deaktiviert die Sonderfreigabe) geändert; Standard weiterhin 15 Minuten.

## 0.2.3 – Boost-Startschutz und Ereignisreaktion
- Leistungs-/Temperaturprüfung, WP-Ruhezeit und Hysterese vor Boost.
- Bei Änderungen relevanter Sensoren gebündelte Neuberechnung nach ungefähr 2 Sekunden ergänzt.

## Bekannte Grenzen
- Keine bestätigten Integrationstests auf produktivem Home Assistant; vor dem Automatikbetrieb mit realen Verbrauchern sorgfältig testen.
- Schnellere interne Berechnung garantiert keine Antwortzeit der Wallbox oder des Akkus.
- 6-A-Mindeststrom (oder abweichend konfigurierter Mindestwert), Abschaltverzögerung und Phasenwechsel-Sperre können kurzfristigen Netzbezug verursachen.
- Die Akku-Priorität ist eine Budgetentscheidung, keine Schreibschnittstelle zum Batterie-Wechselrichter.

