# Smartify Energy Pro

**Update auf 0.3.8:** Heizstab im Modus Manuell heizt jetzt aktiv mit erlaubtem Netzbezug. Vor dem Update bei unerwünschter Nachheizung auf Aus stellen. Danach Home Assistant neu starten und das Dashboard neu laden. WP-WW-Einmalladung: Manuell/Aus werden zu Deaktiviert zusammengeführt; laufende Ladungen bleiben unberührt.

## WP-WW-Einmalladung: vereinfachte Modi (0.3.7)

Nur bei der WP-WW-Einmalladung heißen die Modi jetzt **Automatik**, **Beobachten** und **Deaktiviert**. Automatik löst den Boost nach den eingestellten Bedingungen aus; Beobachten zeigt nur Empfehlungen. Deaktiviert löst keinen neuen Boost aus und verändert weder den Auslöser noch eine bereits laufende WW-Ladung. Diese wird von der Wärmepumpe beendet. Bisher gespeicherte Werte Manuell und Aus werden beim Laden zu Deaktiviert zusammengeführt; auch alte interne Moduswerte bleiben ohne Startfreigabe.

Heizstab, andere Verbraucher und der WP-Boost über einen dauerhaften Zahlensollwert behalten ihre bisherigen Modi. Nach dem Update Home Assistant neu starten und das Dashboard neu laden.


## Heizstab: temperaturgeregelter Handbetrieb (0.3.6)

**Manuell** schaltet den Heizstab temperaturabhängig, auch mit Netzstrom. Bei 50 °C Soll und 1 K Hysterese startet er unter 49 °C, läuft bis 50 °C und schaltet dann ab. Solange Manuell gewählt bleibt, wird nach Abkühlung erneut geheizt; dies ist keine einmalige Nachladung. Zum Beenden **Aus**, für PV-Betrieb **Automatik** wählen.

PV-Start-/Stop-Schwellen, früheste Startzeit und die Pause nach Prioritätsrücknahme gelten nur in Automatik. Im Handbetrieb bleiben Mindestpause, Temperaturüberwachung und sofortige Abschaltung bei ungültiger Temperatur oder Geräte-/Hub-Aus aktiv. Die Mindestlaufzeit kann die Temperaturabschaltung nicht verzögern. Manuelle Heizleistung ist nicht für andere Geräte rücknehmbar; noch nicht gemessene Heizleistung wird vor PV-Freigaben reserviert. Andere Gerätetypen behalten ihr bisheriges manuelles Verhalten.


Home-Assistant-Integration **Smartify Energy Pro** zur Steuerung von PV-Überschuss mit Prioritäten, Prognosen und Batteriespeicherlogik.

Version: **0.3.17** · Integrationsdomain: `smartify_energy`

## Trendanzeige und Historie (0.3.10)
Haushaltsgeräte (WM/GS/Trockner) und WP-Warmwasser-Boost zeigen auf der SEP-Karte einen **grünen ↗** bei steigendem und einen **roten ↘** bei fallendem Steuerbudgettrend. Bei 0 W Trend erscheint →; solange die Zeitreihe nicht ausreicht, erscheint ein Uhrsymbol. Dazu stehen tatsächlich vorhandene **History-Minuten** und die konfigurierte **Trendzeit**. Die Trendberechnung vergleicht zwei unmittelbar aufeinanderfolgende Zeitfenster: 10 Minuten Trendzeit benötigen 20 Minuten Messhistorie. SEP behält bei Änderungen von Trendzeit und Mittelungszeit vorhandene Daten im Arbeitsspeicher und hält bis zu 60 Minuten vor; ein HA-Neustart setzt diese Historie zurück. Wallbox, Heizstab, Pool und PV-Akku zeigen keine Trendzeile.

## Persistente Messhistorie (0.3.11)
SEP speichert die letzten bis zu 60 Minuten Steuerbudget-, Netzsaldo- und Akkuladedaten platzsparend im Home-Assistant-Integrationsspeicher. Nach einem kurzen Neustart wird die Historie mit plausiblen Zeitstempeln wiederhergestellt. Längere Lücken über 2 Minuten werden nicht zu einem kontinuierlichen Trend verbunden. Für die erstmalige Aktivierung des neuen Python-Codes ist ein Home-Assistant-Neustart erforderlich. HACS kann Python-Code-Updates im laufenden Prozess nicht zuverlässig aktivieren.

## Gerätebezogene Trendbewertung (0.3.12)
Für Haushaltsgeräte und den WP-Boost wird der Trendpfeil gegen die benötigte Leistung des jeweiligen Geräts bewertet: Das jetzige individuelle Restbudget wird anhand der Änderung zwischen zwei vollständigen Trendzeitfenstern in das nächste Zeitfenster fortgeschrieben. Nur wenn diese Abschätzung die benötigte Leistung erreicht und der Trend stärker als die einstellbare Toleranz steigt, wird ↗ grün angezeigt; fällt die Abschätzung unter den Bedarf und der Trend ist ausreichend negativ, erscheint ↘ rot. Sonst steht → grau, bei fehlenden Daten eine Uhr. Die Berechnung ist eine indikative Fortschreibung, keine zuverlässige Wolkenprognose. Die Freigabelogik wird nicht verändert.

## Drei PV-Startbedingungen (0.3.13)
Für automatische Starts von Haushaltsgeräten und regulären PV-WW-Boosts gelten drei getrennte Prüfungen: **langes Budgetmittel** (frei einstellbar, z. B. 15 min) ≥ Gerätebedarf; **kurzes Trendfenster** (z. B. 2 min), dessen individuelles Budgetmittel ≥ Gerätebedarf oder dessen Verlauf gegenüber dem vorherigen Trendfenster mindestens neutral (nicht stärker fallend als die einstellbare W-Toleranz) ist; **aktuelles Gerätebudget** ≥ Gerätebedarf. Für die vollständige Richtungsauswertung sind zwei Trendfenster notwendig (bei 2 min Trenddauer insgesamt 4 min Messhistorie). Die Trendanzeige in der Karte entspricht nun dieser Prüfregel. Sofort-/Spätstarts und WW-Boost-Sonderauslösung während aktiver WW-Bereitung behalten ihre separaten Regeln.

## Fallender Kurztrend (0.3.14)
Bei deutlich fallendem Trend darf ein automatischer PV-Start nur erfolgen, wenn **Kurzzeit-Ø plus Trendänderung** weiterhin mindestens die benötigte Geräteleistung ergibt. Ein momentan noch ausreichend hohes Kurzmittel reicht nicht, wenn der Trendwert am Ende des nächsten Fensters unter die Startschwelle fällt. Bei neutralem/steigendem Trend ist diese dritte Prüfung erfüllt; der lange Mittelwert und das Momentanbudget müssen weiterhin jeweils den Gerätebedarf decken. Gleiche Regel für Haushaltsgeräte und regulären WP-Boost. Die Karte zeigt den Kurzmittelwert und die Fortschreibung. Die Fortschreibung ist keine sichere Wolkenprognose.

## Zeitangaben der Trendanzeige (0.3.15)
In der Gerätezeile für Haushaltsgeräte und WP-WW-Boost stehen die drei Zeitangaben getrennt: **Ø 16 min · Trend 2 min · Daten 38 min** (Beispiel). Ø bezeichnet das konfigurierte Mittelungsfenster, Trend das kurze Trendfenster und Daten die insgesamt vorhandene Messhistorie (bis ungefähr 60 Minuten). Eine längere gespeicherte Datenhistorie verändert die eingestellte Mittelungsdauer nicht. Reine Anzeigeänderung ohne Änderung an der Leistungsregelung.

## Kompakte Prioritätenzeilen (0.3.16)
Die Prioritätenkarte zeigt bei Haushaltsgeräten und WP-Boost z. B. **16 min History voll (2.080 W) · 2 min Trend (−320 W) / Sollwert 2.000 W**. Wenn die Mittelungs-Historie noch nicht bereit ist, wird „wartet“ sowie die fehlende Zeit angezeigt. „Voll“ bedeutet, dass die bestehende SEP-Freigabeschwelle von 90 % der Mittelungsdauer erreicht wurde. Der Gerätestatus „Fertig“ wird nicht mehr doppelt wiederholt, stattdessen steht „Neues Programm wird autom. erkannt“. Rechts entfällt die redundante Zeile mit Mittelwert und Vorreservierung; die technischen Statusattribute bleiben vorhanden. Die Leistungsregelung bleibt unverändert.

## Logo und HACS-/Home-Assistant-Branding (0.3.17)
Das quadratische **smartify Energy Pro**-Logo befindet sich als Vektordatei unter `custom_components/smartify_energy/www/sep-logo.svg` und wird **30 × 30 Pixel links vor dem Titel** in der SEP-Dashboard-Karte angezeigt. Für das Integrationssymbol stehen lokale Brand-Dateien unter `custom_components/smartify_energy/brand/` zur Verfügung. Ab Home Assistant 2026.3 werden diese lokal ausgeliefert. **Hinweis:** HACS kann bei Custom-Repositories trotz korrekter Brand-Dateien weiterhin „Icon not available“ anzeigen; dieser HACS-Frontend-Befund ist unabhängig davon, ob das HA-Integrationssymbol erscheint. Nach der Aktualisierung Home Assistant neu starten und Dashboard hart neu laden.

## Dokumentation und Updates

- [Änderungsprotokoll](CHANGELOG.md)
- [SEM v3 → SEP: Entitätsnamen und Migration](docs/SEM_ENTITY_MIGRATION.md)
- [Update-Anleitung und Funktionstest](docs/UPDATE.md)
- [Funktionsstand und bekannte Grenzen](docs/FUNCTIONS.md)
- [Pflichtfelder, optionale und bedingte Entitäten je Funktion](docs/REQUIRED_FIELDS.md)
- [SEP: Prioritäten, Akku, WW-Boost und Dashboard](docs/SEP_CURRENT.md)

## Einstellbare PV-Startfreigabe für Haushaltsgeräte

- **Mittelungszeit:** 1–60 Minuten, Standard 20 Minuten (bei bestehenden Installationen bleibt der gespeicherte Wert erhalten).
- **Trendzeitraum:** 1–30 Minuten, Standard 10 Minuten. SEP vergleicht zwei aufeinanderfolgende, jeweils gleich lange Trendabschnitte (insgesamt doppelte Trenddauer).
- **Trendtoleranz:** 0–500 W, Standard 100 W. Automatischer PV-Start nur, wenn der neuere Durchschnitt nicht um mehr als die Toleranz unter dem älteren Durchschnitt liegt.
- **Startregeln:** Das aktuelle und das gemittelte Gerätebudget müssen weiterhin den Bedarf decken. Fehlt die vollständige Trendhistorie, erfolgt kein automatischer PV-Start. Sofort- und Spätstarts sowie bereits freigegebene Programme bleiben davon ausgenommen. Für Trockner gilt die Prüfung nur, wenn automatische Wiederaufnahme erlaubt wurde.
- Nach einer Änderung der Mittelungs- oder Trendzeit beginnt die betreffende Messhistorie neu. Die neuen Einstellungen sind als Zahlen-Entitäten des SEP-Hubs verfügbar.

## Prioritätsabhängige Lastverdrängung (0.3.4)
Ein wartendes, höher priorisiertes Haushaltsgerät kann steuerbare **nachrangige Heizstäbe** (nach Ablauf ihrer Mindestlaufzeit) und eine **freiwillige PV-Wallboxladung** verdrängen. SEP berücksichtigt nur verfügbare Aktoren mit zuverlässigen Leistungsmesswerten und vermeidet Unterbrechungen, wenn die zusammen rücknehmbare Leistung nicht zur Freigabe reicht. Nach dem Abschaltbefehl erfolgt **keine virtuelle sofortige Budgetgutschrift**: erst Netz-/Leistungsmessung und die vorhandenen Mittelungs-/Trendbedingungen können den Start freigeben. Freiwillige Ladevorgänge werden pausiert, Pflicht-/Sofortladung sowie laufende Haushaltsprogramme nicht. Eine vorübergehende Sperrzeit verhindert direktes Wiederzuschalten. Die PV-Batterie bleibt nach bestehender Prioritätsregelung berücksichtigt; sie wird nicht aktiv von SEP geschaltet. Externe Überschusssenken/Ohmpilot bleiben unverändert und erhalten keine eigene Priorität.

## Funktionen

- Konfiguration über die Home-Assistant-Oberfläche
- Netzleistung, PV-Prognosen und Batteriespeicher berücksichtigen
- Verbraucher, Pool, Elektroauto und Wärmepumpe als Untereinträge verwalten
- Integrierte Dashboard-Karte und deutsche sowie englische Übersetzungen

## Installation mit HACS

1. In HACS unter **Benutzerdefinierte Repositories** die URL `https://github.com/smartify-your-home/smartify-energy-pro` mit Kategorie **Integration** hinzufügen.
2. **Smartify Energy Pro** herunterladen und Home Assistant neu starten.
3. Unter **Einstellungen → Geräte & Dienste → Integration hinzufügen** nach **Smartify Energy Pro** suchen und die Einrichtung durchführen.

## Manuelle Installation

Den Ordner `custom_components/smartify_energy` nach `/config/custom_components/smartify_energy` kopieren, Home Assistant neu starten und die Integration über die Oberfläche hinzufügen.

## Dashboard

Die Integration stellt die Dashboard-Karte automatisch bereit. Beispiel für eine manuelle Karte:

```yaml
type: custom:smartify-energy-plan-card
```

## Hinweise

Die Integration nutzt aktuelle Home-Assistant-Schnittstellen, unter anderem Konfigurations-Untereinträge. Eine Laufzeitprüfung in Home Assistant steht noch aus. Änderungen an der Verbrauchersteuerung zunächst mit passenden Testgeräten prüfen.

Fehler und Verbesserungsvorschläge: [Issues](https://github.com/smartify-your-home/smartify-energy-pro/issues).

## Warmwasser-Boost: ein Start, Wärmepumpe übernimmt den Zyklus (0.2.17)

SEP kann für **Warmwasser aktiv** optional einen bestehenden `binary_sensor` oder `input_boolean` auswählen (unter **Wärmepumpe → Neu konfigurieren**). **EIN** bedeutet WW läuft: Ein weiterer Boost wird dann nicht ausgelöst. Wenn das Feld nicht belegt ist, schützt weiterhin die Leistungs-Ruheerkennung zusammen mit der Startsperre. Ist das Feld belegt, aber die Entität nicht verfügbar, löst SEP aus Sicherheitsgründen nichts aus.

Bei **Button** (`button` / `input_button`) sendet SEP einmal `press`; bei **Schalter** (`switch` / `input_boolean`) einmal `turn_on`. SEP sendet bei diesen Einmalstartern **kein `turn_off`** zum Beenden des WW-Zyklus; die Wärmepumpe steuert die eigentliche Ladung selbst. Ein Schalter, der auf EIN stehen bleibt, verhindert weitere Startbefehle und muss extern wieder auf AUS zurückgehen. Sollwert-/Number-Boosts bleiben davon verschieden, da dort ein Normal-Sollwert zurückgesetzt werden muss.

Die Geräteeinstellung **WW-Boost Mindestabstand** ist standardmäßig **60 min** und lässt sich von **60 bis 720 min** einstellen. **Unter 60 Minuten ist nicht erlaubt**, damit maximal ein Start pro Stunde erfolgt. Vor dem Startbefehl speichert SEP den letzten Startzeitpunkt sofort dauerhaft in Home Assistant. Nach HA-Neustart läuft die Restzeit weiter; auch ein unklarer Aktorfehler hebt die Sperre nicht auf.

## Boost-Startschutz (0.2.3)

Für jeden automatischen Warmwasser-Boost sind Leistungs- und Temperatursensor nötig. Die WP-Leistung muss durchgehend für die einstellbare „WP-Ruhezeit vor Boost“ (0–180 Minuten (0 deaktiviert die Sonderfreigabe), Standard 15 Minuten) unter der einstellbaren WP-Ruheschwelle (Standard 5 W) liegen. Aktivität oder ungültige Leistungswerte setzen die Wartezeit zurück; nach Neustart/Reload beginnt sie neu. Start nur unter Zieltemperatur minus Boost-Hysterese (Standard 4 K): bei 50 °C Ziel also unter 46 °C. Der dauerhafte Mindestabstand seit der letzten WW-Auslösung und die PV-Bedingungen gelten zusätzlich. Ein gestarteter Boost verbraucht die Ruhefreigabe.

Seit 0.2.8 lösen ausgewählte Leistungs- und Wallbox-Messwerte nach etwa 0,5 Sekunden eine gebündelte Neubewertung aus; sonstige beobachtete Eingänge bleiben bei ungefähr 2 Sekunden. Der periodische Zyklus bleibt erhalten; Mittelwerte sind zeitgewichtet.

## Verständliche Einstellungen (0.2.5)

Die deutsche Einrichtung und Gerätekonfiguration erklärt jedes Feld direkt darunter. In der SEP-Karte stehen unter jeder Einstellung im Zahnrad-Menü verständliche Hinweise mit Beispielen; auch Modus und Priorität sind dort enthalten. Die Erklärungen sind ohne Maus-Hover auf Handy und Tablet lesbar. Der Karteneditor erklärt seine Anzeigeoptionen ebenfalls.

## Hauptschalter Aus (0.2.6)

Beim zentralen Ausschalten schaltet SEP die Steckdosen aller angelegten Haushaltsgeräte einmal ein und setzt deren Programmerkennung zurück. Danach bleiben manuelle Schaltbefehle möglich. Bei erneutem Ausschalten sowie beim Laden der Integration mit Hauptmodus Aus erfolgt die Freigabe erneut. Dies gilt für Haushaltsgeräte, nicht für Pool, Wallbox oder Wärmepumpe. Die Steckdose liefert Strom; ob das angeschlossene Gerät sein Programm fortsetzt, hängt vom Gerät ab.

## Optionale Boost-Startbedingungen (0.2.7)

In der Gerätekonfiguration der Wärmepumpe können ein Sonnenhöhen-Sensor und zwei Bewölkungssensoren (aktuelle/kommende Stunde) mit optionalen Grenzwerten ausgewählt werden. Beide Prüfungen haben im Zahnrad-Menü einen eigenen Aktiv-Schalter; anfangs sind sie aus. Grenzwerte lassen sich dort ebenfalls einstellen. Fehlende Entitäten oder Grenzwerte deaktivieren die jeweilige Prüfung; bei Bewölkung müssen beide Entitäten und beide Grenzen vorhanden sein.

Beispiel: Sonnenhöhe mindestens 12° (12° erlaubt), Bewölkung aktuell unter 75 % und kommende Stunde unter 50 % (Gleichheit sperrt). Sind beide Prüfungen aktiv und vollständig, müssen beide erfüllt sein. Ungültige Messwerte einer wirksamen Prüfung sperren neue Starts. Die zusätzlichen Bedingungen stoppen keinen bereits laufenden Boost. Die bisherigen Bedingungen für Überschuss, Temperatur und Ruhezeit gelten weiterhin. Der Gerätestatus zeigt unter boost_startbedingungen, ob eine Prüfung wirkt oder ignoriert wird.

Die Entitäten müssen Zahlenzustände liefern; die Bewölkungssensoren müssen selbst stets die aktuelle bzw. kommende Stunde bereitstellen. Das ist eine zusätzliche Startfreigabe und keine automatische Wahl des besten Prognose-Zeitfensters.

## Schnelle Wallbox-Regelung (0.2.8)

Bei Änderungen am Netzleistungs-, Batterie-Leistungs- oder Wallbox-Leistungssensor wird die Neubewertung nach etwa 0,5 Sekunden gebündelt angestoßen (andere Ereignisse bleiben bei etwa 2 Sekunden). Die laufende Wallbox passt ihren Ladestrom anhand des **aktuellen** verfügbaren Überschusses statt des 2-Minuten-Mittelwerts an; höhere priorisierte Reservierungen werden weiterhin berücksichtigt. Der Kurzzeitmittelwert dient nur noch als zusätzliche Startbedingung. Stromschritte bleiben durch die Auflösung der Wallbox auf ganze Ampere begrenzt. Bei zu wenig Überschuss reduziert SEP unmittelbar auf den Mindeststrom; die konfigurierbare Abschaltverzögerung gilt weiterhin. Die tatsächliche Reaktion hängt von der Aktualisierung der Sensoren, Service-Laufzeit und Wallbox ab.

**Batterie:** SEP berücksichtigt Speicherleistung, SoC, Prognose und Strategie bei der Überschussverteilung, steuert jedoch aktuell **keinen Akku-Ladesollwert**. Die schnellere Messwertauswertung bedeutet daher noch keine direkte Akku-Laderegelung. Vor einer solchen Erweiterung müssen geeignete schreibbare Akku-Entitäten bekannt sein.

## Haushaltsgeräte: SEM-v3-Abgleich und parallele Heizphasen (0.2.18)

Die Zustandsmaschine wurde anhand der bereitgestellten SEM-v3-Integration abgeglichen: 5 Sekunden stabile Leistung über 9 W zur Programmerkennung (ohne Leistungssensor bei eingeschalteter Steckdose), 10 Sekunden über max(200 W, 8 % Nennleistung) zur Heizphasenerkennung, 2 Minuten unter der einstellbaren Fertigschwelle als Standard, standardmäßige Spätstartzeit 16:00 und Zustand „Fertig“ bis zum manuellen Reset. Bereits ausdrücklich freigegebene Programme werden nicht wegen später sinkenden Überschusses gestoppt. SEP behält die grafisch angeordneten Prioritäten anstelle der ausschließlich zeitlichen Reihenfolge von SEM. **Ab 0.2.18 gibt es keine pauschale Sperre mehr bei anderer Heizphase:** Je freigegebenem Gerät wird die noch offene Nennheizleistung unter Abzug tatsächlich gemessener Watt reserviert. Das nächste Gerät darf bei ausreichend aktuellem und gemitteltem Budget auch parallel starten. Nach Heizphasenende entfällt die Reservierung und nur der reale PV-Mittelwert kann den nächsten Start weiterhin verzögern. Neue Standardwerte betreffen neue Einträge; bereits gespeicherte Parameter bleiben bestehen. Eine Prüfung mit echten Geräten steht aus.

## Heizstab / PV-Restverbrauch (0.2.21)

Der neue Subentry-Gerätetyp **Heizstab / PV-Überschusssenke** kann direkt einen Home-Assistant-`switch` oder `input_boolean` steuern. Er benötigt einen *gültigen* Temperaturmesswert (`sensor`) und optional einen echten Leistungssensor. Die Start- und Stop-Entscheidungen verwenden **ausschließlich das aktuelle Restbudget**, nicht den 10-Minuten-Mittelwert. Vorrangige, noch ausstehende Geräte-Reservierungen bleiben berücksichtigt. Der gemessene, bereits laufende Verbrauch wird nicht erneut abgezogen.

Nach Einrichtung im SEP-Gerät die Automatik aktivieren. Die Standardwerte entsprechen der bisherigen Elektroheizstab-Automation: **2000 W** Nennleistung, **2200 W** PV-Startschwelle, **0 W** Stoppschwelle (Netzbezug → AUS), **55 °C** Maximaltemperatur, **3 K** Hysterese (Neustart unter 52 °C), **10:00** frühester Start. `heater_min_on` und `heater_min_off` sind optional (je 0 min = deaktiviert) und können bis 120 min eingestellt werden. Die Temperaturabschaltung sowie Modus AUS übersteuern jede Mindestlaufzeit.

Für einen echten Shelly-Ausgang einen `switch.*` wählen. Bei `input_boolean.*` muss eine separate HA-Automation den logischen Zustand in den echten Schaltausgang umsetzen. Bevor SEP die Steuerung übernimmt, die bisherigen **EStab_Automatik_on/off**-Automationen deaktivieren. Der Regler ersetzt weder einen unabhängigen Temperaturbegrenzer noch die elektrische Schutzabschaltung.

## Mindestüberschuss für Haushaltsgeräte

Der Standardwert für **neu angelegte** Haushaltsgeräte lautet **+1.500 W**. Für einen PV-Automatikstart müssen jedoch mindestens die **erwartete Nennleistung des Geräts oder der höhere konfigurierte Mindest-Überschuss** gedeckt sein; Beispiel: 2.000 W Nennleistung und 1.500 W Mindest-Überschuss bedeuten 2.000 W erforderliches aktuelles und gemitteltes Restbudget. Negative Mindest-Überschuss-Einstellungen ermöglichen hier keinen zusätzlichen automatischen Netzbezug mehr. Spätstart, Sofortfenster und Sofortstart sind bewusst davon ausgenommen. Bereits gespeicherte Parameter bleiben bestehen.

### Startzeit und Priorität

Haushaltsgeräte haben eine **früheste automatische Startzeit** (Standard 00:00). Vor dieser Uhrzeit erfolgt keine automatische Freigabe – auch nicht durch Spätstart oder Sofortfenster. Ein ausdrücklich gedrückter **Sofort-Start** bleibt möglich. Die bisherigen Prioritäts-Nummern werden nicht mehr als Einstellungs-Entitäten angezeigt; die Prioritätslogik bleibt intern für die spätere grafische Anordnung erhalten.

**Prioritäten:** Die Prioritäts-Zahlen-Entitäten sind bewusst nicht mehr sichtbar. Die grafische Übersicht zeigt die intern gespeicherte Priorität aus dem Gerätestatus; per Drag & Drop wird die Reihenfolge über `smartify_energy.set_priority_order` dauerhaft gespeichert.

## Wäschetrockner – eigenes Leistungsprofil (0.2.27)

Unter **Gerät hinzufügen → Wäschetrockner** kann ein Trockner separat konfiguriert werden (Standard 800 W, 2,5 Stunden). SEP reserviert während des freigegebenen Programms die eingestellte Dauerlast als erwartete Leistung, berücksichtigt die bereits am Netzanschluss gemessene Leistung und darf sie nicht doppelt als zusätzlichen Verbrauch ansetzen.

**Wiederanlauf nach Stromunterbrechung vorher am eigenen Gerät prüfen:** Bei **„Nein – kein Wiederanlauf“ (sichere Voreinstellung)** lässt SEP die Steckdose vollständig unangetastet. Der Trockner wird manuell am Gerät gestartet und von SEP nur überwacht; ein verzögerter automatischer PV-Start ist dann nicht möglich. **„Ja“** ausschließlich auswählen, wenn das Gerät nach Wegfall und Rückkehr der Netzspannung ein zuvor laufendes Programm zuverlässig fortsetzt. Dann ist vor der einmaligen PV-Freigabe ein Abschalten der Steckdose möglich; nach Freigabe wird das Programm nicht wegen sinkender PV-Leistung unterbrochen. Den Wiederanlauf nur unter sicheren Bedingungen nach Herstellerangaben testen.

## WW-Boost bei laufender Warmwasserbereitung (0.2.29)

Für einmalige WW-Boost-Auslöser (Button/Schalter/Input-Boolean) darf SEP auch während einer bereits laufenden Warmwasserbereitung einmalig boosten, sobald der konfigurierte WW-Aktiv-Binärsensor **für die eingestellte Wartezeit durchgehend `on`** (Standard 10 Minuten) ist und das **aktuelle prioritätsbereinigte Steuerbudget mindestens 0 W** beträgt. Die normale Mindestleistungsfreigabe und WP-Ruhebedingung werden in diesem speziellen Fall nicht benötigt; Solltemperatur, Temperaturhysterese, optionaler Sonnenwinkelfilter (keine Bewölkungsprüfung) und Boost-Startsperre bleiben wirksam. Pro erfasstem WW-Zyklus wird höchstens ein Boost ausgelöst. Ohne gültigen WW-Aktiv-Sensor ist diese Sonderfreigabe nicht möglich. Sollwertgesteuerte Number-Boosts bleiben vorerst unverändert.

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

[Alle Änderungen und Migration](docs/REVIEW_0.3.0.md). Nach dem Update Home Assistant neu starten. Mindestversion: **2025.7.0**.

