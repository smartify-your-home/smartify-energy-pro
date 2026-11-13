/**
 * smartify-energy-plan-card
 * Lovelace Custom Card für den smartify Energiemanager (Integration smartify_energy).
 * Zeigt Überschuss, Prioritäten (Drag & Drop) und den PV-Plan der nächsten Stunden.
 * Version: 1.4.0
 *
 * Installation: /config/www/smartify-energy-plan-card.js
 * Resource:     /local/smartify-energy-plan-card.js  (type: module)
 *
 * YAML (alles optional – Hub und Geräte werden automatisch gefunden):
 *   type: custom:smartify-energy-plan-card
 *   title: Energiemanager
 *   hub: <device_id>          # nur nötig bei mehreren Energiemanagern
 *   show_header: true
 *   show_allocated: false     # Kachel „Verteilt“ im Kopf
 *   show_priorities: true
 *   show_timeline: true
 *   timeline_hours: 24
 *   show_mode: true           # Schnellbedienung je Gerät: Auto = Ladeziel, Haushaltsgerät = Aktionen (Modus im Zahnrad)
 *   show_settings: true       # Zahnrad: alle Einstellungen je Gerät / Energiemanager
 *
 * Zweite Karte in dieser Datei: custom:smartify-energy-pv-card (PV-Flächen auf dem
 * Luftbild einzeichnen, ersetzt die früheren Eingabefelder im Optionsdialog).
 *
 * Theme-Variablen (haben Vorrang):
 *   smartify-plan-row-background   Zeilen-/Kachelhintergrund (default card-background-color)
 *   smartify-plan-border-radius    Eckenradius (default 6px)
 *   smartify-plan-text-color       Textfarbe (default primary-text-color)
 */

const CARD_VERSION = "1.6.3";
const DOMAIN = "smartify_energy";

const PALETTE = [
  ["#80DEEA", "#00ACC1"],
  ["#4FC3F7", "#0288D1"],
  ["#81C784", "#2E7D32"],
  ["#CE93D8", "#8E24AA"],
  ["#FFF59D", "#FF9800"],
  ["#F48FB1", "#C2185B"],
  ["#B0BEC5", "#546E7A"],
  ["#A5D6A7", "#00897B"],
];
const PV_GRADIENT = ["#ff9900", "#ffc34d"];
const FORCED_GRADIENT = ["#FFB74D", "#E65100"];
const BATTERY_GRADIENT = ["#9FA8DA", "#3949AB"];

const OPTION_LABELS = {
  auto: "Automatik", observe: "Beobachten", manual: "Manuell", off: "Aus", disabled: "Deaktiviert",
  forecast: "Prognose", battery_first: "Speicher zuerst", devices_first: "Geräte zuerst",
  summer: "Sommer", winter: "Winter",
  none: "Kein Filter", cloud: "Bewölkung", pv_forecast: "PV-Forecast",
  "1": "Nächste 1 Stunde", "2": "Nächste 2 Stunden",
  pv_only: "Nur PV", km_until: "km bis Uhrzeit", days: "Tage-Konfigurator", now: "Sofort laden",
  one: "1-phasig", three: "3-phasig",
};
const MODE_LABELS = { auto: "Automatik", observe: "Beobachten", manual: "Manuell", off: "Aus", disabled: "Deaktiviert" };
const TYPE_ICONS = { load: "mdi:washing-machine", pool: "mdi:pool", ev: "mdi:ev-station", heatpump: "mdi:heat-pump", heater: "mdi:water-boiler" };
const STATUS_LABELS = {"initializing": "Initialisierung", "ready": "Bereit", "detected": "Erkannt", "waiting": "Wartet", "running": "Läuft", "finished": "Fertig", "off": "Aus", "manual": "Manuell", "observing": "Beobachten", "inactive": "Inaktiv", "locked": "Sperrzeit", "limit_reached": "Grenze erreicht", "disconnected": "Nicht verbunden", "full": "Voll", "charging_now": "Lädt sofort", "charging_required": "Pflichtladen", "charging_pv": "PV-Laden", "boost": "Boost", "actuator_unavailable": "Aktor nicht verfügbar", "actuator_error": "Aktorfehler",
  laeuft: "läuft", wartet: "wartet", bereit: "bereit", erkannt: "erkannt", fertig: "fertig",
  aus: "aus", manuell: "manuell", beobachten: "beobachten", inaktiv: "inaktiv", sperrzeit: "Sperrzeit",
  max_erreicht: "Max erreicht", nicht_verbunden: "nicht angesteckt", voll: "voll",
  laedt_pv: "lädt PV", laedt_pflicht: "lädt (Ziel)", laedt_sofort: "lädt sofort", boost: "Boost",
};

const SETTING_HELP = {
  "heater_max_temp": "Maximale Wassertemperatur. Ab dieser Temperatur schaltet SEP den Heizstab sofort AUS – unabhängig von Mindestlaufzeiten. Ein eigenständiger physischer Temperaturbegrenzer bleibt erforderlich.",
  "heater_hysteresis": "Nach Erreichen der Maximaltemperatur darf der Heizstab erst unter Maximaltemperatur minus Hysterese erneut einschalten. Beispiel: 55 °C minus 3 K = unter 52 °C.",
  "heater_start_surplus": "Minimaler sofort verfügbarer PV-Überschuss für EIN. Für den Start wird mindestens die Nennleistung benötigt. Standard 2200 W bei 2000 W Heizleistung. Der 10-Minuten-Mittelwert wird NICHT verwendet.",
  "heater_stop_surplus": "Ab diesem verbleibenden Momentanbudget wird bei Unterschreitung ausgeschaltet. 0 W bedeutet bei Netzbezug AUS. Der Heizstab ist bereits im gemessenen Netzsaldo enthalten und wird nicht doppelt abgezogen.",
  "heater_earliest_start": "Vor dieser Uhrzeit startet der Heizstab nicht neu. Standard 10:00. Ein bereits laufender Heizstab wird dadurch nicht allein ausgeschaltet.",
  "heater_min_on": "Optionale Mindestlaufzeit gegen vorzeitige Rücknahme für andere Verbraucher. Die vorrangige Abschaltung bei PV-Mangel, ungültigem Netzsensor oder Temperaturgrenze wartet nicht auf diese Zeit.",
  "heater_min_off": "Optionale Mindestpause zwischen AUS und erneutem EIN (0 = keine Pause). Schaltzeitpunkt bleibt auch nach einem Home-Assistant-Neustart gespeichert.",

  "mode": "Automatik: SEP steuert dieses Gerät. Beobachten: SEP zeigt Empfehlungen, schaltet aber nicht. Manuell: Sie übernehmen die Bedienung. Ausnahme Heizstab: SEP regelt weiter auf die eingestellte Solltemperatur, auch mit Netzstrom. Start unter Soll minus Hysterese, Abschaltung bei Soll; erneutes Heizen bleibt aktiv, bis Sie Automatik oder Aus wählen. PV-Schwellen, früheste Startzeit und Prioritätspause werden ignoriert; Mindestpause und Temperaturüberwachung bleiben aktiv. Aus: Die automatische Regelung ist ausgesetzt. Das Verhalten beim Ausschalten hängt vom Gerätetyp ab. Zentral gilt die Auswahl für den Manager. Aus ist kein Not-Aus: Beim zentralen Ausschalten werden Haushaltsgeräte-Steckdosen einmal eingeschaltet und die Programmerkennung zurückgesetzt. Anschließend können Sie die Steckdosen manuell bedienen; Pool und Wallbox stoppen derzeit nur bei ihrem eigenen Modus Aus. Der WP-Boost wird beendet, eine Button-Ladung kann aber weiterlaufen.",
  "priority": "Kleinere Zahl bedeutet früher an der Reihe: 1 hat Vorrang vor 5. Bereits freigegebene Programme und Pflichtläufe können Vorrang behalten. Ziehen ändert diese Werte; ab dem zehnten Platz teilen Geräte Priorität 10.",
  "avg_window": "Über wie viele Minuten Netzsaldo und Steuerbudget separat gemittelt werden. Ein größerer Wert reagiert ruhiger auf Wolken, aber langsamer auf dauerhaft mehr Sonne. Standard: 10 Minuten.",
  "grid_reserve": "Diese Leistung bleibt bei der Verteilung ungenutzt. Beispiel: 200 W halten einen kleinen Puffer gegen unbeabsichtigten Netzbezug frei. Pflichtläufe können trotzdem Strom aus dem Netz brauchen.",
  "base_load": "Geschätzter Dauerverbrauch des Hauses, etwa Kühlschrank und Router. Wird von der PV-Prognose abgezogen. Beispiel: 400 W. Dieser Wert dient der Planung; die aktuelle Regelung nutzt die Messwerte.",
  "battery_min_soc": "Unter diesem Akkustand erhält der Hausspeicher Vorrang. Beispiel: 20 % schützt eine kleine Reserve. SEP steuert den Speicher nicht direkt und garantiert damit keine Entladegrenze.",
  "battery_target_soc": "Gewünschter Akkustand für die Speicherplanung. Beispiel: 90 %. Bei „Speicher zuerst“ erhalten Verbraucher erst ab diesem Stand Zugriff auf die Ladeleistung des Speichers.",
  "battery_safety": "Zusätzlicher Puffer bei der Prognose: 1,5 verlangt das 1,5-Fache der noch benötigten Speicherenergie. Höhere Werte bevorzugen den Speicher vorsichtiger.",
  "battery_strategy": "SEP berechnet weiter eine Prognose-Priorität für den Hausspeicher. Ohne direkte Stellmöglichkeit am Speicher wird dessen Ladeleistung jedoch aus Sicherheitsgründen nicht als sofort verfügbares Steuerbudget freigegeben. Die Auswahl steuert den Wechselrichter nicht.",
  "nominal_power": "Erwartete maximale Heizleistung dieses Haushaltsgeräts in Watt (W), z. B. 2000 W. Vor dem Ende der ersten Heizphase wird sie vollständig abgesichert. In späteren Heizpausen gilt die einstellbare Restreservierung. Bereits gemessener Verbrauch wird nicht doppelt abgezogen.",
  "pause_budget_release_pct": "Gibt nach der ersten abgeschlossenen Heizphase einen Teil der Nennleistung für weitere Geräte frei: 0 % = keine Freigabe (volle Reservierung), 50 % = halbe Reservierung, 100 % = volle Freigabe der zusätzlichen Reservierung. Die tatsächlich gemessene Leistung bleibt berücksichtigt. Ohne gültigen Leistungssensor bleibt die volle Nennleistung reserviert; bei späteren Heizphasen kann Netzbezug entstehen.",
  "detect_threshold": "Ein neues Programm wird erkannt, wenn die Leistungsaufnahme durchgehend über diesem Grenzwert liegt.",
  "detect_seconds": "Mindestdauer der Leistungsaufnahme über dem Grenzwert. Beispiel: 20 s ignoriert eine automatische Türöffnung mit 10 W für 10 s. Gilt sowohl nach Bereit als auch nach Fertig.",
  "min_surplus": "Zusätzliche einstellbare PV-Startschwelle in Watt (W). Für einen automatischen PV-Start zählt der höhere Wert aus Nennleistung und Mindest-Überschuss: z. B. bei 2000 W Heizleistung und 1500 W Schwelle müssen mindestens 2000 W frei sein. Auch der Mittelwert muss reichen. Negative Werte senken diese Heizlast-Absicherung nicht ab; Netzbezug kann aber durch Spätstart, Sofortfenster oder Sofort starten ausdrücklich erlaubt werden.",
  "finish_threshold": "Unter dieser Leistung kann das Programm als fertig gelten, sobald die Fertigerkennung freigegeben ist. Beispiel: 5 W. Eine zu hohe Schwelle kann längere Programmpausen mit dem Programmende verwechseln.",
  "finish_minutes": "So lange muss die Leistung unter der Fertig-Schwelle bleiben. Erst dann erscheint „Fertig“. Ein längerer Wert vermeidet Fehlmeldungen bei Pausen, meldet das Ende aber später.",
  "duration": "Geschätzte Programmdauer in Stunden für die Startempfehlung. Beispiel: 2,5 für zweieinhalb Stunden. Das Gerät wird nach dieser Zeit nicht automatisch abgeschaltet.",
  "sinks_yield": "Ein: Die Leistung von Ohmpilot/Heizstab steht den SEP-Geräten zur Verfügung, die Senke nimmt nur den restlichen Überschuss. Voraussetzung: Die Senke regelt sich selbst schnell zurück, sobald Netzbezug droht. Aus: Senken werden nur angezeigt.",
  "nachladen": "Gibt bei einem wartenden Haushaltsgerät die Steckdose frei, damit Sie zum Beispiel Wäsche nachlegen können. Nach dem Ausschalten entscheidet SEP wieder nach Überschuss und Uhrzeit; das Programm kann dann auch sofort freigegeben werden.",
  "latest_start": "Ab dieser Uhrzeit wird ein wartendes Programm auch ohne genügend Solarstrom freigegeben. Es kann dann Netzstrom verbrauchen. Das ist eine Startzeit, keine Fertigzeit.",
  "announce_finished": "Sagt an, sobald das Programm fertig ist, zum Beispiel „Waschmaschine ist fertig.“ Voraussetzung: In den SEP-Einstellungen (Schritt Netz) ist ein Script für Ansagen gewählt. Wo und wie laut angesagt wird, legt dieses Script fest.",
  "announce_reminder": "Wiederholt die Ansage alle 30 Minuten, solange das Gerät auf „Fertig“ steht. Endet mit „Fertig“-Taste oder sobald ein neues Programm erkannt wird. Nur wirksam, wenn „Ansage bei Fertig“ eingeschaltet ist.",
  "announce_start": "Ab dieser Uhrzeit darf SEP ansagen. Wird ein Gerät außerhalb des Zeitraums fertig, folgt die Ansage zu Beginn des nächsten Zeitraums, falls es dann noch auf „Fertig“ steht. Standard 07:00.",
  "announce_end": "Ab dieser Uhrzeit bleibt SEP still, auch Erinnerungen entfallen. Standard 22:00. Sind beide Zeiten gleich, wird rund um die Uhr angesagt.",
  "night_start": "Beginn des Sofortfensters für Haushaltsgeräte. In diesem Fenster dürfen Programme ohne genügend Solarstrom starten. Beispiel: 22:00 bis 05:00 geht über Mitternacht.",
  "night_end": "Ende des Sofortfensters. Bereits freigegebene Programme laufen weiter. Sind Beginn und Ende gleich, ist das Fenster deaktiviert.",
  "fixed_runtime": "Tägliche Soll-Laufzeit der Poolpumpe, wenn keine Wassertemperatur verfügbar ist. Beispiel: 6 Stunden. Mit gültigem Temperatursensor wird die Laufzeit aus der Temperatur berechnet.",
  "temp_factor": "Stunden Pumpenlaufzeit je Grad Wassertemperatur. Beispiel: 24 °C × 0,5 ergibt 12 Stunden, anschließend begrenzt durch die minimale und maximale Soll-Laufzeit.",
  "runtime_min": "Untergrenze für die temperaturabhängig berechnete Pool-Soll-Laufzeit. Beispiel: mindestens 3 Stunden pro Tag. Gilt bei aktiver Saison.",
  "runtime_max": "Obergrenze für die temperaturabhängig berechnete Pool-Soll-Laufzeit. Zusätzlicher Betrieb bei Sonne ist bis zur maximalen Gesamtlaufzeit möglich.",
  "max_runtime": "Tägliche Gesamtlaufzeit der Poolpumpe einschließlich zusätzlicher Sonnenstunden. Mindestens die berechnete Soll-Laufzeit bleibt erlaubt: Eine kleinere Eingabe begrenzt diese Soll-Laufzeit derzeit nicht.",
  "winter_temp": "Unterhalb dieser Wassertemperatur bleibt die Pumpe bei Saison „Automatik“ aus. Beispiel: 12 °C. Ohne gültige Temperatur wird die Saison als aktiv behandelt; eine Frostschutzregel ist das nicht.",
  "vm_share": "Anteil der täglichen Soll-Laufzeit, der schon vormittags erreicht werden soll. Beispiel: 40 % von 6 Stunden sind 2 Stunden 24 Minuten. Falls nötig wird dafür Netzstrom genutzt.",
  "vm_deadline": "Bis zu dieser Uhrzeit soll der Vormittagsanteil erledigt sein. SEP beginnt rechtzeitig einen Pflichtlauf, sofern andere Sperren ihn nicht verhindern.",
  "season": "Sommer: Poolregelung aktiv. Winter: Pumpe wird in Automatik ausgeschaltet. Automatik: Die Wassertemperatur entscheidet anhand der Wintergrenze.",
  "lock_enabled": "Aktiviert die tägliche Sperrzeit der Poolpumpe, zum Beispiel für eine ruhige Mittagspause. Währenddessen wird die Pumpe ausgeschaltet.",
  "lock_start": "Beginn der Pumpensperre. Beispiel: 12:00. Die Sperre kann eine laufende Pumpenphase unterbrechen.",
  "lock_end": "Ende der Pumpensperre. Danach gelten wieder die normalen Regeln. Gleiche Start- und Endzeit bedeuten keine Sperrzeit; ein Fenster über Mitternacht ist möglich.",
  "min_on": "Mindestzeit, die ein gestartetes Gerät möglichst weiterläuft, damit es nicht ständig ein- und ausschaltet. Zieltemperatur, Tageslimit oder eine Pumpensperre können den Betrieb früher beenden.",
  "min_off": "Mindestpause nach einem von SEP ausgelösten Stopp. Verhindert häufiges Neustarten. Bei der Wärmepumpe muss zusätzlich die gemessene WP-Ruhezeit erfüllt sein.",
  "goal": "Nur PV: nach verfügbarem Solarstrom laden. km bis Uhrzeit: nötigenfalls mit Netzstrom für die geplante Strecke laden. Tage-Konfigurator: Strecke aus dem Tagesplan lesen. Sofort: mit maximalem Ladestrom laden; dabei kann Netzstrom nötig sein.",
  "target_km": "Gewünschte Fahrstrecke bis zur eingestellten Abfahrtszeit. SEP schätzt die nötige Energie aus Verbrauch, Akkustand und Reserve. Gilt für das Ladeziel „km bis Uhrzeit“.",
  "deadline": "Bis zu dieser Uhrzeit soll die benötigte Reichweite geladen sein. SEP berechnet daraus den spätesten Beginn einer Netzladung. Nach Ablauf wird die nächste entsprechende Uhrzeit verwendet.",
  "reserve_soc": "Akkureserve des Autos, die bei der Reichweitenrechnung nicht als verfügbare Fahrenergie zählt. Beispiel: 20 %. Dies ist keine direkte Entladesperre im Fahrzeug.",
  "max_soc": "Ab diesem gemeldeten Fahrzeug-Akkustand beendet SEP die Ladung. Beispiel: 80 %. Dafür muss ein gültiger Akkustandsensor vorhanden sein.",
  "consumption": "Durchschnittlicher Fahrzeugverbrauch in kWh je 100 km. Beispiel: 18. Ein höherer Wert plant mehr Ladeenergie für die gleiche Strecke ein.",
  "pv_share": "Mindestens erforderlicher Solar-Anteil an der kleinsten Ladeleistung. 100 % startet nur bei vollständig gedeckter Mindestleistung; 50 % erlaubt den Rest aus dem Netz. Verzögerungen können vorübergehend zusätzlichen Netzbezug verursachen.",
  "phase_switch_minutes": "So lange muss mindestens zwischen zwei Umschaltungen ein-/dreiphasig liegen. Beispiel: 20 min. Längere Werte schonen Wallbox und Auto, nutzen schwankenden Überschuss aber ungenauer.",
  "phase_hysteresis": "Abstand zur Dreiphasen-Mindestleistung (6 A × 3). Dreiphasig ab Mindestleistung plus diesem Wert, zurück auf einphasig unter Mindestleistung minus diesem Wert. Beispiel: 500 W → ca. 4,6 kW hoch, 3,6 kW zurück.",
  "phase_mode": "Einphasig eignet sich für wenig Solarüberschuss, dreiphasig für höhere Ladeleistung. Automatik wählt passend zum Überschuss. In der aktuellen Version verwenden Sofort- und Pflichtladung bei vorhandener Umschaltung dennoch drei Phasen.",
  "boost": "Lädt das Auto für die eingestellte Boost-Dauer mit dem Boost-Faktor × PV-Überschuss, mindestens mit der Boost-Mindestleistung. Netzbezug ist erlaubt. Danach automatisch zurück zum normalen Laden; Abstecken beendet den Boost.",
  "boost_factor": "Vielfaches des PV-Überschusses beim Boost. ×2 heißt: etwa die Hälfte kommt aus PV, die andere Hälfte aus dem Netz.",
  "boost_hours": "So lange läuft ein Boost nach dem Einschalten. Eine Änderung während eines laufenden Boosts startet die Dauer neu.",
  "boost_min_power": "Mit dieser Leistung lädt der Boost mindestens, auch bei Wolken oder ohne PV (aus dem Netz). 0 W = nur Faktor × PV; reicht das nicht für den Mindeststrom, gilt die Stopp-Verzögerung.",
  "stop_delay": "So lange darf zu wenig Solarüberschuss vorhanden sein, bevor SEP den Betrieb beendet. Kurze Wolken führen dadurch nicht gleich zum Stopp. Währenddessen kann Netzstrom nötig sein.",
  "target_temp": "Warmwasser-Zieltemperatur: Ein neuer WW-Boost darf nur starten, wenn der Speicher um die Hysterese darunter liegt. Einmal ausgelöste WW-Ladungen über Button/Schalter werden von der Wärmepumpe selbst beendet. Bei Sollwert-Boost regelt SEP weiterhin aktiv.",
  "max_per_day": "Maximale Dauer der aktiv geregelten Sollwert-Boost-Freigabe pro Kalendertag (nur bei Number-Boost). Einmalige WW-Starts verwenden stattdessen den einstellbaren Mindestabstand.",
  "boost_value": "Diesen Sollwert schreibt SEP beim Start an die ausgewählte Number-Entität der Wärmepumpe. Er gilt nur bei Boost-Art „Sollwert“. Einheit und erlaubten Bereich der Ziel-Entität beachten.",
  "normal_value": "Diesen festen Sollwert schreibt SEP beim Ende des Boosts zurück. Der vorherige Wert wird nicht automatisch gemerkt. Wählen Sie hier den gewünschten normalen Warmwasser-Sollwert.",
  "boost_hysteresis": "Temperaturabstand für den Start. 4 Kelvin entsprechen 4 °C Unterschied: Bei 50 °C Ziel darf WW-Boost nur unter 46 °C starten; bei genau 46 °C noch nicht.",
  "idle_power_threshold": "Unter dieser gemessenen WP-Leistung zählt die Wärmepumpe als ruhend. Beispiel: 5 W. Ab genau 5 W beginnt die Wartezeit später wieder von vorn. Den Wert passend zum tatsächlichen Standby-Verbrauch wählen.",
  "idle_minutes": "So lange muss die WP-Leistung unter der Ruheschwelle liegen, bevor ein neuer WW-Boost gestartet werden darf. Standard: 15 Minuten. Aktivität, ungültige Werte und ein Neustart setzen die Ruheerkennung zurück. Unabhängig davon gilt der dauerhafte WW-Boost-Mindestabstand.",
  "start_now": "Gibt das Haushaltsgerät sofort frei und schaltet bei Bedarf seine Steckdose ein – auch ohne Solarüberschuss. Diese Taste löst direkt eine Aktion aus.",
  "reset": "Optional: Setzt die Erkennung des Haushaltsgeräts sofort auf „Bereit“ zurück. Normalerweise nicht nötig – ein neuer Programmstart nach „Fertig“ wird automatisch erkannt. Das Programm am Gerät wird nicht zurückgesetzt und die Steckdose nicht ausgeschaltet.",
  "sun_angle_min": "Optionaler Mindestwinkel. Beispiel: 12° erlaubt den Boost ab genau 12°. Leer bedeutet: Sonnenwinkel-Prüfung wird ignoriert. Entität in der Gerätekonfiguration auswählen und Prüfung aktivieren.",
  "cloud_now_max": "Boost startet nur bei einem Wert kleiner als diese Grenze. Beispiel: unter 75 %; genau 75 % sperrt den Start. Beide Stunden müssen ihre Grenze einhalten. Bei unvollständigen Angaben wird die gesamte Bewölkungsprüfung ignoriert.",
  "cloud_next_max": "Boost startet nur, wenn auch die kommende Stunde unter dieser Grenze liegt. Beispiel: unter 50 %; genau 50 % sperrt. Leer bedeutet bei dieser Prüfung: ignorieren, bis beide Entitäten und Grenzen vollständig sind.",
  "sun_filter_active": "Ein: Vor einem neuen Boost wird der Sonnenwinkel geprüft, wenn Entität und Mindestwinkel eingetragen sind. Aus oder unvollständige Angaben: ignorieren. Ein ungültiger Messwert bei vollständig aktiver Prüfung verhindert den Start. Laufende Boosts werden dadurch nicht beendet.",
  "boost_start_filter": "Für normale WW-Boost-Starts: Kein Filter, Bewölkung ODER PV-Forecast. Bewölkung nutzt die beiden konfigurierten Prozentgrenzen; PV-Forecast nutzt ausschließlich die vorhandene SEP-Prognose im gewählten Zeitfenster. Bei laufender WW-Bereitung gelten weder Bewölkung noch Forecast. Temperatur, Budget, Startsperre und optionaler Sonnenwinkelfilter bleiben wirksam.",
  "boost_forecast_hours": "Zeitraum ab jetzt: 1 oder 2 Stunden, Standard 2. Angebrochene Stunden werden anteilig berechnet. Nur wirksam bei Startfilter PV-Forecast. Beispiel: um 12:30 mit 2 Stunden bis 14:30.",
  "boost_forecast_min_kwh": "Mindestens erwarteter PV-Ertrag im gewählten Zeitraum, Standard 2 kWh; einstellbar 0,1–100 kWh. Das ist Erzeugung, kein freier Überschuss: Die Budgetprüfung bleibt erhalten. Fehlende, fehlerhafte, unvollständige oder über 60 Minuten alte Prognosen sperren im Forecast-Modus neue Starts. Quelle in den zentralen SEP-Prognoseeinstellungen wählen.",
  "ww_active_minutes": "So lange muss Warmwasser aktiv ununterbrochen EIN sein. Danach darf SEP bei aktuellem Steuerbudget ≥ 0 W einmalig boosten. Standard 10 Minuten, einstellbar 0–180 Minuten (0 deaktiviert die Sonderfreigabe). Temperatur, optionaler Sonnenwinkelfilter und Startsperre gelten weiter; Bewölkung wird hier ignoriert. Nur für Button/Schalter/Boolean; maximal ein Boost je WW-Zyklus.",
  "trigger_cooldown": "Mindestzeit zwischen zwei WW-Boost-Auslösungen in Minuten. Standard 60 min, einstellbar 60–720 min. Nach erfolgreicher Startfreigabe wird der Zeitstempel VOR dem WP-Befehl gespeichert und übersteht auch Home-Assistant-Neustarts. Während laufender WW-Ladung ist nach der konfigurierten WW-Aktiv-Wartezeit höchstens ein Boost je Zyklus möglich."
};

// Kompakte Einstellungen: Kurzinfo je Einstellung, lange Erklärung über (i).
const SETTING_SHORT = {
  mode: "Wer das Gerät steuert", goal: "Wann und wie geladen wird", season: "Sommer/Winter-Betrieb",
  nachladen: "Steckdose kurz freigeben", start_now: "Programm jetzt freigeben", reset: "Erkennung zurücksetzen",
  deadline: "Abfahrtszeit", target_km: "Strecke bis Abfahrt",
  boost: "Mit Netzanteil laden", boost_factor: "× PV-Überschuss", boost_hours: "danach normales Laden", boost_min_power: "auch ohne PV",
  reserve_soc: "zählt nicht als Reichweite", max_soc: "Ladung endet hier", consumption: "je 100 km",
  pv_share: "Solaranteil für den Start", stop_delay: "Wartezeit bei Wolken",
  phase_mode: "1-, 3-phasig oder automatisch", phase_switch_minutes: "Abstand zwischen Umschaltungen", phase_hysteresis: "Puffer beim Umschalten",
  nominal_power: "typische Leistung", min_surplus: "Überschuss für den Start", pause_budget_release_pct: "Budget nach Heizphase freigeben",
  earliest_start: "nicht vor dieser Zeit", latest_start: "spätestens starten", duration: "typische Programmdauer",
  detect_threshold: "Programm erkannt ab", detect_seconds: "so lange darüber", finish_threshold: "fertig unter", finish_minutes: "so lange darunter",
  fixed_runtime: "Laufzeit pro Tag", temp_factor: "Laufzeit je °C", runtime_min: "mindestens pro Tag", runtime_max: "höchstens pro Tag (Temperatur)",
  max_runtime: "absolute Obergrenze", winter_temp: "darunter Winterbetrieb", vm_share: "Anteil bis Vormittags-Ziel", vm_deadline: "Vormittags-Ziel",
  lock_enabled: "tägliche Sperrzeit", lock_start: "Sperre ab", lock_end: "Sperre bis",
  min_on: "Mindestlaufzeit", min_off: "Mindestpause", max_per_day: "Maximum pro Tag",
  target_temp: "Ziel-Warmwasser", boost_hysteresis: "Abstand zum Ziel für Start", boost_value: "Sollwert im Boost", normal_value: "Sollwert normal",
  idle_power_threshold: "Leerlauf unter", idle_minutes: "Leerlauf-Dauer", trigger_cooldown: "Pause zwischen Auslösungen", ww_active_minutes: "WW-Bereitung erkannt nach",
  sun_filter_active: "nur bei Sonnenstand", sun_angle_min: "Sonnenwinkel mindestens", boost_start_filter: "Wetterbedingung für Start",
  boost_forecast_hours: "Prognosefenster", boost_forecast_min_kwh: "PV im Fenster mindestens", cloud_now_max: "Bewölkung jetzt höchstens", cloud_next_max: "Bewölkung nächste Stunde höchstens",
  heater_max_temp: "sofort aus ab", heater_hysteresis: "wieder ein unter Max − Wert", heater_start_surplus: "Überschuss für EIN", heater_stop_surplus: "AUS unter",
  heater_earliest_start: "nicht vor dieser Zeit", heater_min_on: "Mindestlaufzeit", heater_min_off: "Mindestpause",
  avg_window: "Mittelwert über", trend_window: "Trend über", trend_tolerance: "Toleranz für Trend", grid_reserve: "Puffer zum Netz", base_load: "Grundlast im Haus",
  announce_finished: "bei Programmende ansagen", announce_reminder: "alle 30 min wiederholen",
  announce_start: "Ansagen ab", announce_end: "Ansagen bis",
  night_start: "Nachtfenster ab", night_end: "Nachtfenster bis", sinks_yield: "Heizstab/Pool weichen Geräten",
  battery_strategy: "wer zuerst PV bekommt", battery_min_soc: "Speicher mindestens", battery_target_soc: "Speicher-Ziel", battery_safety: "Sicherheitsfaktor Prognose",
};

// Gruppen in Anzeigereihenfolge. collapsed: standardmäßig zugeklappt (mit Zusammenfassung).
const SETTING_GROUPS = [
  { id: "control", title: "Bedienung", keys: ["mode", "goal", "season", "nachladen", "start_now", "reset", "battery_strategy"] },
  { id: "goal", title: "Ladeziel", keys: ["deadline", "target_km"] },
  { id: "boost", title: "PV-Boost", keys: ["boost", "boost_factor", "boost_hours", "boost_min_power"] },
  { id: "vehicle", title: "Fahrzeug", keys: ["reserve_soc", "max_soc", "consumption"] },
  { id: "temp", title: "Temperatur", keys: ["target_temp", "boost_hysteresis", "boost_value", "normal_value", "heater_max_temp", "heater_hysteresis"] },
  { id: "runtime", title: "Laufzeit", keys: ["fixed_runtime", "temp_factor", "runtime_min", "runtime_max", "max_runtime", "winter_temp", "vm_share", "max_per_day", "duration"] },
  { id: "power", title: "Leistung & PV", keys: ["nominal_power", "min_surplus", "heater_start_surplus", "heater_stop_surplus", "grid_reserve", "base_load", "sinks_yield", "pause_budget_release_pct"] },
  { id: "times", title: "Zeiten", keys: ["earliest_start", "latest_start", "heater_earliest_start", "vm_deadline", "lock_enabled", "lock_start", "lock_end", "night_start", "night_end"] },
  { id: "announce", title: "Ansage", keys: ["announce_finished", "announce_reminder", "announce_start", "announce_end"] },
  { id: "battery", title: "Speicher", keys: ["battery_min_soc", "battery_target_soc", "battery_safety"] },
  { id: "detection", title: "Programm- & Fertigerkennung", collapsed: true, keys: ["detect_threshold", "detect_seconds", "finish_threshold", "finish_minutes"] },
  { id: "weather", title: "Wetterfilter", collapsed: true, keys: ["boost_start_filter", "boost_forecast_hours", "boost_forecast_min_kwh", "cloud_now_max", "cloud_next_max", "sun_filter_active", "sun_angle_min"] },
  { id: "advanced", title: "Erweitert", collapsed: true, keys: ["pv_share", "stop_delay", "phase_mode", "phase_switch_minutes", "phase_hysteresis", "min_on", "min_off", "heater_min_on", "heater_min_off", "avg_window", "trend_window", "trend_tolerance", "idle_power_threshold", "idle_minutes", "trigger_cooldown", "ww_active_minutes"] },
];

const SETTING_LABELS = {
  detect_threshold: "Programmerkennung: Leistung über", detect_seconds: "Programmerkennung: Zeitraum",
  finish_threshold: "Fertigerkennung: Leistung unter", finish_minutes: "Fertigerkennung: Zeitraum",
  pause_budget_release_pct: "Budgetfreigabe nach Heizphase",
};

// Nur anzeigen, wenn die Einstellung im aktuellen Zustand wirkt.
// state(key) liefert den aktuellen Zustand einer anderen Einstellung desselben Geräts.
const SETTING_VISIBLE = {
  announce_reminder: st => st("announce_finished") !== "off",
  deadline: st => st("goal") == null || st("goal") === "km_until",
  target_km: st => st("goal") == null || st("goal") === "km_until",
  lock_start: st => st("lock_enabled") !== "off",
  lock_end: st => st("lock_enabled") !== "off",
  sun_angle_min: st => st("sun_filter_active") !== "off",
  cloud_now_max: st => st("boost_start_filter") == null || st("boost_start_filter") === "cloud",
  cloud_next_max: st => st("boost_start_filter") == null || st("boost_start_filter") === "cloud",
  boost_forecast_hours: st => st("boost_start_filter") == null || st("boost_start_filter") === "pv_forecast",
  boost_forecast_min_kwh: st => st("boost_start_filter") == null || st("boost_start_filter") === "pv_forecast",
};

const SETTING_DOMAINS = ["select", "switch", "time", "number", "button"];

const esc = s => String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
const grad = g => `linear-gradient(to right,${g.join(",")})`;
const num = v => { const n = parseFloat(v); return isNaN(n) ? null : n; };
// Direction is evaluated against the particular device's PV requirement.
// A rising global trend is NOT a positive device signal if its projected
// priority-adjusted budget stays below that requirement.
function deviceTrend(recentAverage, needed, change, tolerance, ready) {
  if (!ready || ![recentAverage, needed, change, tolerance].every(Number.isFinite)) {
    return {direction: "pending", allowed: false};
  }
  // Short mean must always cover the requirement. A sharp drop additionally
  // requires the projected headroom to remain sufficient.
  const projected = recentAverage + change;
  const stable = change >= -tolerance;
  const allowed = recentAverage >= needed && (stable || projected >= needed);
  return {direction: change > tolerance && projected >= needed ? "up" :
          !allowed ? "down" : "neutral", allowed, projected};
}

const fmtW = w => (w == null ? "–" : Math.abs(w) >= 10000 ? `${(w / 1000).toFixed(1)} kW` : `${Math.round(w)} W`);
const fmtTime = iso => {
  const d = new Date(iso);
  if (isNaN(d)) return null;
  const today = new Date();
  const t = d.toLocaleTimeString("de-AT", { hour: "2-digit", minute: "2-digit" });
  return d.toDateString() === today.toDateString() ? t : `${d.toLocaleDateString("de-AT", { weekday: "short" })} ${t}`;
};

// ── Auto-Erkennung über Entity-/Device-Registry ─────────────────────────────

function findHubs(hass) {
  const hubs = new Map();
  for (const e of Object.values(hass?.entities || {})) {
    if (e.platform !== DOMAIN || e.translation_key !== "plan" || !e.device_id) continue;
    const dev = hass.devices?.[e.device_id];
    hubs.set(e.device_id, dev?.name_by_user || dev?.name || "Energiemanager");
  }
  return hubs;
}

function collect(hass, hubId) {
  const byDevice = {};
  const settings = {};
  for (const e of Object.values(hass?.entities || {})) {
    if (e.platform !== DOMAIN || !e.device_id) continue;
    (byDevice[e.device_id] ||= {})[`${e.entity_id.split(".")[0]}:${e.translation_key}`] = e.entity_id;
    const dom = e.entity_id.split(".")[0];
    if (SETTING_DOMAINS.includes(dom)) {
      // Old registry entries may survive an update even after their entity has been removed.
      // Never expose the obsolete inverted reservation parameter in the settings UI.
      if (!["priority", "battery_rank", "pause_reservation_pct"].includes(e.translation_key)) (settings[e.device_id] ||= []).push({ id: e.entity_id, dom, key: e.translation_key, config: e.entity_category === "config" });
    }
  }
  for (const list of Object.values(settings)) {
    list.sort((a, b) => (a.config - b.config) || (SETTING_DOMAINS.indexOf(a.dom) - SETTING_DOMAINS.indexOf(b.dom)));
  }
  const hubs = findHubs(hass);
  const hub = hubId && hubs.has(hubId) ? hubId : [...hubs.keys()][0];
  if (!hub) return null;
  const devices = Object.entries(byDevice)
    .filter(([id]) => id !== hub && hass.devices?.[id]?.via_device_id === hub)
    .map(([id, ents]) => {
      const dev = hass.devices[id];
      return {
        id,
        name: dev?.name_by_user || dev?.name || id,
        status: ents["sensor:status"],
        power: ents["sensor:power"],
        planned: ents["sensor:planned_start"],
        priority: ents["number:priority"],
        mode: ents["select:mode"],
        goal: ents["select:goal"],
        active: ents["binary_sensor:active"],
        startNow: ents["button:start_now"],
        reset: ents["button:reset"],
        nachladen: ents["switch:nachladen"],
        boost: ents["switch:boost"],
        settings: settings[id] || [],
      };
    })
    .filter(d => d.status);
  // Virtual storage position: a passive PV sink, with its rank saved on
  // the hub. It needs no real HA device and never receives charge commands.
  if (byDevice[hub]?.["sensor:battery_priority"] && byDevice[hub]?.["number:battery_rank"]) {
    devices.push({
      id: "__battery__", name: "PV-Akku", virtualBattery: true,
      status: byDevice[hub]["sensor:battery_priority"],
      batteryBudget: byDevice[hub]["sensor:budget"],
      rankEntity: byDevice[hub]["number:battery_rank"],
      power: null, planned: null, priority: null, mode: null, active: null,
      settings: [],
    });
  }
  devices.sort((a, b) => a.id.localeCompare(b.id));
  devices.forEach((d, i) => { d.color = PALETTE[i % PALETTE.length]; });
  return { hub, name: hubs.get(hub), ents: byDevice[hub] || {}, devices, hubSettings: settings[hub] || [] };
}


function sepNiceAxisMax(value) {
  // Four evenly spaced, human-readable ticks; never clip the tallest bar.
  const max = Math.max(0, Number(value) || 0);
  if (!Number.isFinite(max) || max <= 0) return 1000;
  const magnitude = 10 ** Math.floor(Math.log10(max));
  return ([1, 2, 2.5, 4, 5, 8, 10].find(v => v * magnitude >= max)
    || 10) * magnitude;
}

function sepAxisLabels(max, unit) {
  return [4,3,2,1,0].map(level => {
    const k = (max * level / 4) / 1000;
    const label = k.toLocaleString("de-AT",{maximumFractionDigits:2});
    return `<span>${esc(label)} ${unit}</span>`;
  }).join("");
}

const SEP_GRID = '<div class="sep-chart-grid" aria-hidden="true"><i></i><i></i><i></i><i></i></div>';

// ── Editor ──────────────────────────────────────────────────────────────────

const EDITOR_CSS = `
  :host { display:block; font-family:var(--primary-font-family,sans-serif); color:var(--primary-text-color); }
  .section { font-size:11px; font-weight:600; letter-spacing:.08em; text-transform:uppercase;
    color:var(--secondary-text-color); border-bottom:1px solid var(--divider-color);
    padding-bottom:4px; margin:14px 0 8px; }
  label { font-size:12px; color:var(--secondary-text-color); display:block; margin:6px 0 2px; }
  input[type=text], input[type=number], select { width:100%; box-sizing:border-box;
    background:var(--card-background-color); color:var(--primary-text-color);
    border:1px solid var(--divider-color); border-radius:4px; padding:6px 8px; font-size:13px; }
  .row { display:flex; gap:8px; align-items:center; margin:6px 0; }
  .row label { margin:0; font-size:13px; color:var(--primary-text-color); }
  input[type=checkbox] { width:16px; height:16px; cursor:pointer; flex-shrink:0; }
  .section-sort{display:flex;flex-direction:column;gap:4px;margin-top:6px}
  .section-sort-item{display:flex;align-items:center;gap:9px;border:1px solid var(--divider-color);
    background:var(--card-background-color);border-radius:6px;padding:8px;color:var(--primary-text-color);
    font-size:13px;cursor:grab;touch-action:pan-y;user-select:none}
  .section-sort-item .sort-grip{color:var(--secondary-text-color);font-size:19px;touch-action:none;cursor:grab}
  .section-sort-item button{margin-left:auto;border:1px solid var(--divider-color);background:transparent;
    color:var(--primary-text-color);border-radius:5px;padding:4px 8px;font-size:14px;cursor:pointer}

  input[type=range] { width:100%; accent-color:var(--primary-color); cursor:pointer; }
  .hint { font-size:11px; color:var(--secondary-text-color); margin-top:3px; }
`;

class SmartifyEnergyPlanCardEditor extends HTMLElement {
  constructor() { super(); this.attachShadow({ mode: "open" }); this._config = {}; }
  set hass(h) { const first = !this._hass; this._hass = h; if (first) this._render(); }
  setConfig(config) { this._config = { ...config }; this._render(); }

  _emit() {
    this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: this._config }, bubbles: true, composed: true }));
  }

  _render() {
    const c = this._config;
    const hubs = this._hass ? findHubs(this._hass) : new Map();
    const chk = (k, d = true) => (c[k] ?? d) ? "checked" : "";
    this.shadowRoot.innerHTML = `
      <style>${EDITOR_CSS}</style>
      <div class="section">Allgemein</div>
      <label>Titel</label>
      <input type="text" id="title" value="${esc(c.title ?? "")}" placeholder="Name des Energiemanagers">
      <div class="hint">Überschrift dieser Karte. Leer lassen übernimmt den Namen des Energiemanagers.</div>
      <label>Energiemanager</label>
      <select id="hub">
        <option value="">Automatisch (erster gefundener)</option>
        ${[...hubs].map(([id, name]) => `<option value="${id}" ${c.hub === id ? "selected" : ""}>${esc(name)}</option>`).join("")}
      </select>
      <div class="hint">Bei mehreren Energiemanagern wählen Sie hier das gewünschte Haus oder System. Automatisch verwendet den ersten gefundenen Manager.</div>
      ${hubs.size ? "" : `<div class="hint">Kein smartify Energiemanager gefunden – Integration installiert?</div>`}
      <div class="section">Darstellung</div>
      <label for="background_transparency">Hintergrundtransparenz: <strong id="background_transparency_value">${Math.max(0, Math.min(100, Number(c.background_transparency) || 0))} %</strong></label>
      <input type="range" id="background_transparency" min="0" max="100" step="5" value="${Math.max(0, Math.min(100, Number(c.background_transparency) || 0))}">
      <div class="hint">0 % = deckend (bisherige Darstellung), 100 % = vollständig transparent. Betrifft Kartenhintergrund, Gerätezeilen, Kennzahlen und Zeitleiste; Schrift und Bedienelemente bleiben lesbar.</div>
      <div class="section">Bereiche</div>
      <div class="row"><input type="checkbox" id="show_header" ${chk("show_header")}><label for="show_header">Netzsaldo- und Budgetleiste</label></div>
      <div class="row"><input type="checkbox" id="show_allocated" ${chk("show_allocated", false)}><label for="show_allocated">Kachel „Verteilt“ im Kopf</label></div>
      <div class="hint">Zeigt den echten Netzsaldo (+ Einspeisung, − Bezug) getrennt vom rechnerischen Steuerbudget sowie Verteilung, Prognose und Speicherdaten.</div>
      <div class="row"><input type="checkbox" id="show_priorities" ${chk("show_priorities")}><label for="show_priorities">Prioritäten (Drag &amp; Drop)</label></div>
      <div class="hint">Zeigt die Geräteliste mit ihrer Reihenfolge. Ziehen verändert, wer den verfügbaren Solarstrom zuerst bekommt.</div>
      <div class="row"><input type="checkbox" id="show_mode" ${chk("show_mode")}><label for="show_mode">Schnellbedienung je Gerät (Ladeziel / Aktionen)</label></div>
      <div class="hint">Zeigt die schnelle Betriebsmodus-Auswahl neben jedem Gerät.</div>
      <div class="row"><input type="checkbox" id="show_settings" ${chk("show_settings")}><label for="show_settings">Einstellungen (Zahnrad) erlauben</label></div>
      <div class="hint">Zeigt das Zahnrad mit Einstellungen und Erklärungen. Ausblenden verändert keine Regelung und ist keine Zugriffssperre.</div>
      <div class="row"><input type="checkbox" id="show_timeline" ${chk("show_timeline")}><label for="show_timeline">PV-Plan (Zeitleiste)</label></div>
      <div class="section">Reihenfolge der Bereiche</div>
      <div class="section-sort" id="section-sort">
        ${(c.pv_plan_first ? ["pv","priorities"] : ["priorities","pv"]).map((kind,i)=>`
        <div class="section-sort-item" draggable="true" data-order-item="${kind}" tabindex="0"
          aria-label="${kind==="pv"?"PV-Plan mit Prognose-Ist-Vergleich":"Prioritäten"} verschieben">
          <span class="sort-grip" aria-hidden="true">⠿</span>
          <span>${kind==="pv"?"PV-Plan + Prognose/Ist":"Prioritäten"}</span>
          <button type="button" data-order-swap aria-label="${kind==="pv"?"PV-Plan":"Prioritäten"} ${i===0?"nach unten":"nach oben"} verschieben">${i===0?"↓":"↑"}</button>
        </div>`).join("")}
      </div>
      <div class="hint">Bereiche durch Ziehen vertauschen; die Reihenfolge wird mit der Karte gespeichert.</div>
      <div class="row"><input type="checkbox" id="show_pv_tips" ${chk("show_pv_tips")}><label for="show_pv_tips">PV-Alltagstipps über den Balken anzeigen</label></div>
      <div class="hint">Nur Anzeige in dieser Karte: Ausblenden deaktiviert keine PV-Tipp-Sensoren und ändert keine Regelung.</div>
      <div class="hint">Zeigt die Prognose und die empfohlenen Zeiträume. Der Plan ist eine Empfehlung, keine feste Startzusage.</div>
      <div class="hint">Horizontal bis zum Ende der verfügbaren Prognose scrollen, auch übermorgen falls vorhanden. Nächte werden kompakt dargestellt.</div>
    `;
    const set = (k, v) => { this._config = { ...this._config, [k]: v }; if (v === "" || v == null) delete this._config[k]; this._emit(); };
    const $ = id => this.shadowRoot.getElementById(id);
    $("title").addEventListener("change", e => set("title", e.target.value));
    $("hub").addEventListener("change", e => set("hub", e.target.value));
    $("background_transparency").addEventListener("input", e => {
      $("background_transparency_value").textContent = `${e.target.value} %`;
      set("background_transparency", Number(e.target.value));
    });
    ["show_header", "show_allocated", "show_priorities", "show_mode", "show_settings", "show_timeline", "show_pv_tips"].forEach(k =>
      $(k).addEventListener("change", e => set(k, e.target.checked)));
    const saveOrder = first => { set("pv_plan_first", first === "pv"); this._render(); };
    const sort = $("section-sort");
    let dragged = null;
    sort.querySelectorAll(".section-sort-item").forEach(item => {
      item.addEventListener("dragstart", e => {
        dragged = item.dataset.orderItem;
        e.dataTransfer?.setData("text/plain", dragged);
        if (e.dataTransfer) e.dataTransfer.effectAllowed = "move";
      });
      item.addEventListener("dragend", () => { dragged = null; });
      item.addEventListener("dragover", e => e.preventDefault());
      item.addEventListener("drop", e => {
        e.preventDefault();
        const from = dragged || e.dataTransfer?.getData("text/plain");
        if (from && from !== item.dataset.orderItem)
          saveOrder(c.pv_plan_first ? "priorities" : "pv");
      });
      item.querySelector("[data-order-swap]").addEventListener("click", () =>
        saveOrder(c.pv_plan_first ? "priorities" : "pv"));
      const grip = item.querySelector(".sort-grip");
      grip.addEventListener("pointerdown", e => {
        if (e.pointerType === "mouse") return;
        e.preventDefault();
        const y = e.clientY;
        grip.setPointerCapture?.(e.pointerId);
        const finish = up => {
          grip.removeEventListener("pointerup", finish);
          grip.removeEventListener("pointercancel", cancel);
          const dy = up.clientY - y;
          const first = item.dataset.orderItem === (c.pv_plan_first ? "pv" : "priorities");
          if ((first && dy > 25) || (!first && dy < -25))
            saveOrder(c.pv_plan_first ? "priorities" : "pv");
        };
        const cancel = () => {
          grip.removeEventListener("pointerup", finish);
          grip.removeEventListener("pointercancel", cancel);
        };
        grip.addEventListener("pointerup", finish);
        grip.addEventListener("pointercancel", cancel);
      });
    });

  }
}
if (!customElements.get("smartify-energy-plan-card-editor")) customElements.define("smartify-energy-plan-card-editor", SmartifyEnergyPlanCardEditor);

// ── Card ────────────────────────────────────────────────────────────────────

const CARD_CSS = `
  :host { display:block; --row-bg:var(--smartify-plan-row-background, var(--card-background-color));
          --radius:var(--smartify-plan-border-radius, 6px); --txt:var(--smartify-plan-text-color, var(--primary-text-color)); }
  ha-card { padding:12px; color:var(--txt);
    background:color-mix(in srgb, var(--ha-card-background, var(--card-background-color)) var(--sep-surface-opacity,100%), transparent); }
  .tile, .dev, .timeline { background:color-mix(in srgb, var(--row-bg) var(--sep-surface-opacity,100%), transparent); }
  .settings { background:color-mix(in srgb, var(--secondary-background-color) var(--sep-surface-opacity,100%), transparent); }
  .title { font-size:16px; font-weight:600; margin:0 0 10px 2px; display:flex; align-items:center; gap:8px; }
  .sep-brand-icon { width:40px; height:40px; flex:0 0 40px; object-fit:contain; border-radius:7px; }
  .title .sp { flex:1; }
  .section { font-size:11px; font-weight:600; letter-spacing:.08em; text-transform:uppercase;
             color:var(--secondary-text-color); margin:14px 2px 6px; display:flex; justify-content:space-between; }
  .section span:last-child { text-transform:none; letter-spacing:0; font-weight:400; }
  .priority-heading { display:inline-flex;align-items:center;gap:7px;min-width:0; }
  .priority-lock { display:inline-flex;align-items:center;justify-content:center;
    width:27px;height:27px;flex:none;margin:-6px 0 -5px -2px;
    border:1px solid var(--divider-color);border-radius:6px;
    background:transparent;color:var(--secondary-text-color);cursor:pointer;padding:2px; }
  .priority-lock ha-icon { --mdc-icon-size:18px; }
  .priority-lock.unlocked { color:var(--primary-color);border-color:var(--primary-color); }
  .priority-lock:disabled { cursor:wait;opacity:.5; }
  .priority-lock:focus-visible { outline:2px solid var(--primary-color);outline-offset:2px; }
  .priority-hint { text-align:right; }
  .section-move-grip{display:inline-flex;align-items:center;justify-content:center;
    width:22px;height:24px;flex:none;border:0;background:transparent;color:var(--secondary-text-color);
    border-radius:4px;cursor:grab;touch-action:none;padding:0;margin:-4px 2px -4px -1px}
  .section-move-grip:focus-visible{outline:2px solid var(--primary-color)}
  .section-move-grip ha-icon{--mdc-icon-size:18px;pointer-events:none}
  .sep-order-block{position:relative}
  .sep-order-block.section-moving{outline:1px dashed var(--primary-color);border-radius:6px}



  .tiles { display:grid; grid-template-columns:repeat(auto-fit,minmax(112px,1fr)); gap:4px; }
  .tile { min-width:0; container-type:inline-size; background:var(--row-bg); border-radius:var(--radius); padding:8px 4px 6px;
          display:flex; flex-direction:column; align-items:center; cursor:pointer; box-sizing:border-box;
          border-style:solid; border-width:0 0 4px 0; border-image-slice:1; box-shadow:var(--ha-card-box-shadow,none); }
  .tile ha-icon { --mdc-icon-size:22px; }
  .tile .v { font-weight:bold; font-size:min(17px, 21cqw); margin-top:2px; white-space:nowrap; }
  .tile .n { font-size:min(11px, 16cqw); opacity:.75; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:100%; }
  .tile.paired { gap:2px; padding:7px 7px 6px; }
  .tile.paired .n { font-size:11px; opacity:.85; margin-bottom:2px; }
  .tile.paired .metrics { display:grid; grid-template-columns:28px auto; column-gap:6px;
                           align-items:baseline; justify-content:center; font-variant-numeric:tabular-nums; }
  .tile.paired .metric-label { font-size:11px; color:var(--secondary-text-color); text-align:right; }
  .tile.paired .metric-value { font-weight:700; color:var(--txt); white-space:nowrap; text-align:right; }
  .tile.paired .metric-value.avg { font-size:18px; }
  .tile.paired .metric-value.now { font-size:13px; font-weight:600; }


  select.mode { appearance:none; -webkit-appearance:none; border:1px solid var(--divider-color); border-radius:12px;
                background:var(--secondary-background-color); color:var(--txt); font-size:11px;
                padding:2px 10px; cursor:pointer; max-width:180px; white-space:nowrap; text-overflow:ellipsis; }
  select.mode.auto { border-color:#43A047; } select.mode.observe { border-color:#0288D1; }
  select.mode.off { border-color:#E65100; }
  select.mode.quick { border-color:var(--primary-color); }
  .power-budget .sep-actions { margin-top:0; }
  .mode-tag { font-size:11px; padding:1px 8px; border-radius:10px; border:1px solid var(--divider-color); color:var(--secondary-text-color); white-space:nowrap; }
  .mode-tag.observe { border-color:#0288D1; color:#0288D1; } .mode-tag.off { border-color:#E65100; color:#E65100; }
  .mode-tag.manual { border-color:#8E24AA; color:#8E24AA; }
  .seg { display:inline-flex; border:1px solid var(--divider-color); border-radius:12px; overflow:hidden; }
  .seg button { border:none; background:none; color:var(--secondary-text-color); font:inherit; font-size:11px; padding:2px 8px; cursor:pointer; }
  .seg button + button { border-left:1px solid var(--divider-color); }
  .seg button.on { color:#fff; }
  .seg button.on.auto { background:#43A047; } .seg button.on.manual { background:#E53935; } .seg button.on.off { background:#757575; }

  .list { container-type:inline-size; display:flex; flex-direction:column; gap:4px; position:relative; }
  .dev { display:grid; grid-template-columns:22px 26px 28px minmax(0,1fr) auto; align-items:center; gap:8px;
         background:var(--row-bg); border-radius:var(--radius); padding:4px 8px 4px 4px; box-sizing:border-box;
         border-style:solid; border-width:0 0 4px 0; border-image-slice:1; position:relative;
         transition:transform .18s ease; user-select:none; }
  .dev-wrap { transition:transform .18s ease; }
  .dev-wrap.dragging { transition:none; z-index:5; position:relative; }
  .dev-wrap.dragging .dev { box-shadow:0 8px 24px rgba(0,0,0,.35); }
  .dev.dragging { transition:none; z-index:5; box-shadow:0 8px 24px rgba(0,0,0,.35); opacity:.95; }
  .handle { cursor:grab; color:var(--secondary-text-color); font-size:18px; text-align:center; touch-action:none; }
  .handle:active { cursor:grabbing; }
  .handle.locked { cursor:default;touch-action:pan-y;opacity:.35; }
  .handle.locked:active { cursor:default; }
  .badge { width:24px; height:24px; border-radius:50%; display:flex; align-items:center; justify-content:center;
           font-size:12px; font-weight:700; color:#000; }
  .dev ha-icon { --mdc-icon-size:24px; cursor:pointer; }
  .main { min-width:0; cursor:pointer; }
  .main .name { font-size:14px; font-weight:500; display:flex; flex-wrap:wrap; align-items:center; gap:2px 6px; }
  .main .name span.t { white-space:nowrap; overflow:hidden; text-overflow:ellipsis; min-width:0; }
  .main .sub { font-size:11px; color:var(--secondary-text-color); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .main .plan { font-size:11px; color:var(--secondary-text-color); line-height:1.5; overflow-wrap:anywhere; }
  .main .plan ha-icon { display:inline-flex; vertical-align:middle; }
  .sep-gates { display:inline-flex; align-items:center; gap:7px; white-space:nowrap; vertical-align:middle; }
  .sep-history-icon { --mdc-icon-size:17px; display:inline-flex; vertical-align:middle; }
  .sep-gate { --mdc-icon-size:16px; display:inline-flex; vertical-align:middle; }
  .sep-log-toggle { border:1px solid var(--divider-color); border-radius:6px; padding:1px 6px; background:transparent; color:var(--secondary-text-color); font:inherit; font-size:10px; cursor:pointer; }
  .sep-actions { display:flex; flex-wrap:wrap; gap:4px; margin-top:3px; }
  .right .sep-actions { justify-content:flex-end; margin-top:5px; max-width:100%; }
  .right .sep-act { white-space:nowrap; }

  .sep-act { border:1px solid var(--divider-color); border-radius:12px; padding:2px 10px; background:var(--secondary-background-color);
             color:var(--txt); font:inherit; font-size:11px; cursor:pointer; display:inline-flex; align-items:center; gap:4px; }
  .sep-act ha-icon { --mdc-icon-size:14px; }
  .sep-act:hover { border-color:var(--primary-color); }
  .sep-act.on { border-color:var(--primary-color); color:var(--primary-color); }
  .sep-log-toggle:hover { color:var(--primary-text-color); }
  .sep-log { margin-top:5px; padding:7px 9px; border:1px solid var(--divider-color); border-radius:7px; background:var(--secondary-background-color); font-size:11px; line-height:1.55; max-width:480px; }
  .sep-log-row { display:grid; grid-template-columns:18px minmax(0,1fr); gap:6px; padding:2px 0; }
  .sep-log-row + .sep-log-row { border-top:1px solid var(--divider-color); }
  .sep-log-code { font-weight:800; }
  .sep-log-detail { overflow-wrap:anywhere; color:var(--primary-text-color); }


  .title { flex-wrap:wrap; }
  .right { display:flex; flex-direction:column; align-items:flex-end; gap:2px; min-width:0; }
  .power-budget { display:flex; gap:10px; justify-content:flex-end; align-items:center; flex-wrap:wrap; }
  .pb-item { display:flex; flex-direction:column; align-items:flex-end; gap:1px; white-space:nowrap; }
  .pb-pair { display:contents; }
  /* Heizstab: keep the three existing mode actions INSIDE the metrics area.
     Wide rows place the switch beside the numbers; narrow rows place it above. */
  .heater-power-budget { flex-wrap:nowrap; gap:10px; }
  .heater-power-budget .pb-pair { display:flex; gap:10px; align-items:center; justify-content:flex-end; }
  .heater-power-budget .seg { flex:none; }
  .pb-full { font-size:10px; color:var(--secondary-text-color); white-space:nowrap; }
  .gear.boost.on { color:var(--primary-color); }
  .pb-stack { display:flex; flex-direction:column; align-items:flex-end; gap:3px; }
  /* Auto: [Ladeziel + Boost] | Akku | Leistung | Budget | Zahnrad in einer Zeile (breit),
     schmal: Bediengruppe oben, darunter Akku links und Leistung/Budget untereinander. */
  .ev-power-budget { flex-wrap:nowrap; }
  .ev-power-budget .pb-stack { flex-direction:row; gap:10px; align-items:center; }
  .ev-ctl { display:flex; align-items:center; gap:4px; flex:none; }
  .plan.sep-stop { color:var(--warning-color, #f57c00); display:flex; align-items:center; gap:4px; }
  .plan.sep-stop ha-icon { --mdc-icon-size:14px; }
  .plan.sep-boost { color:var(--primary-color); display:flex; align-items:center; gap:4px; }
  .plan.sep-boost ha-icon { --mdc-icon-size:14px; }
  .pb-label { font-size:10px; opacity:.72; }
  .pw { font-size:13px; font-weight:bold; white-space:nowrap; }
  .pb-budget { font-size:13px; font-weight:700; font-variant-numeric:tabular-nums; }
  .pb-budget.negative { color:var(--error-color, #d45b48); }
  .pb-budget.positive { color:var(--success-color, #2e7d32); }
  @container (max-width:560px) {
    /* Never move metrics and actions below the status on phones/tablets. */
    .dev { grid-template-columns:16px 24px 24px minmax(0,1fr) min(42%, 150px); gap:4px; padding-right:4px; }
    .dev .main { min-width:0; overflow-wrap:anywhere; }
    .dev .main .name span.t { white-space:normal; overflow:visible; text-overflow:clip; overflow-wrap:anywhere; }
    .dev .main .sub { white-space:normal; overflow:visible; text-overflow:clip; overflow-wrap:anywhere; line-height:1.35; }
    .right { grid-column:5; grid-row:1; align-items:flex-end; width:auto; min-width:0; }
    .power-budget { width:100%; justify-content:flex-end; gap:4px 8px; }
    .heater-power-budget { flex-direction:column; flex-wrap:nowrap; align-items:flex-end; gap:5px; }
    .heater-power-budget .pb-pair { width:100%; justify-content:flex-end; gap:8px; }
    .heater-power-budget .seg { align-self:flex-end; }
    .ev-power-budget { flex-wrap:wrap; }
    .ev-power-budget .ev-ctl { width:100%; justify-content:flex-end; }
    .ev-power-budget .pb-stack { flex-direction:column; gap:3px; align-items:flex-end; }
    .power-budget select.mode { max-width:100%; box-sizing:border-box; }
    .pb-item { align-items:flex-end; }
    .right .sep-actions { justify-content:flex-end; }
    .right .sep-act { padding:2px 6px; }
    .dev .sep-gates { flex-wrap:wrap; white-space:normal; }
  }
  .chip { font-size:10px; padding:1px 6px; border-radius:8px; color:#000; font-weight:600; }

  .timeline { background:var(--row-bg); border-radius:var(--radius); padding:8px 6px 4px; box-sizing:border-box; }
  .sep-axis-layout { display:grid; grid-template-columns:49px minmax(0,1fr); gap:5px; min-width:0; }
  .sep-y-axis { height:96px; display:flex; flex-direction:column; justify-content:space-between;
    color:var(--secondary-text-color); font-size:10px; font-variant-numeric:tabular-nums;
    text-align:right; white-space:nowrap; line-height:1; padding:0 0 0 1px; box-sizing:border-box; }
  .sep-y-axis.compare { height:156px; margin-top:58px; padding-top:0; }
  .sep-chart-grid { position:absolute; inset:0; z-index:0; pointer-events:none; }
  .sep-chart-grid i { position:absolute; width:100%; left:0;
    border-top:1px solid color-mix(in srgb,var(--secondary-text-color) 24%,transparent); }
  .sep-chart-grid i:nth-child(1) { top:0; }
  .sep-chart-grid i:nth-child(2) { top:25%; }
  .sep-chart-grid i:nth-child(3) { top:50%; }
  .sep-chart-grid i:nth-child(4) { top:75%; }
  .bars { display:flex; align-items:flex-end; gap:2px; height:96px; position:relative;
    border-bottom:1px solid color-mix(in srgb,var(--secondary-text-color) 35%,transparent); box-sizing:border-box; }
  .bars > .col, .bars > .pv-break { z-index:1; }
  .col { flex:1 1 0; min-width:0; height:100%; position:relative; display:flex; flex-direction:column; justify-content:flex-end; }
  .col .pv { position:absolute; left:0; right:0; bottom:0; border-radius:3px 3px 0 0; opacity:.22; background:${grad(PV_GRADIENT).replace("to right", "to top")}; }
  .col .seg { position:relative; width:100%; }
  .col .seg:last-child { border-radius:3px 3px 0 0; }
  .pv-break { flex:0 0 12px;min-width:12px;height:100%;border-left:1px dashed var(--divider-color);
    box-sizing:border-box;background:transparent;opacity:.6; }
  .pv-break-label { flex:0 0 12px !important;min-width:12px !important; }
  .col.gap { margin-left:8px; }
  .col.gap::before { content:""; position:absolute; left:-6px; top:20%; bottom:0; border-left:1px dotted var(--divider-color); }
  .col.now::after { content:""; position:absolute; top:-2px; bottom:0; left:-1px; border-left:2px dashed var(--primary-color); }
  .labels { display:flex; gap:2px; margin-top:3px; }
  .labels div { flex:1 1 0; min-width:0; font-size:10px; color:var(--secondary-text-color); text-align:center; white-space:nowrap; }
  .legend { display:flex; flex-wrap:wrap; gap:4px 10px; margin-top:6px; font-size:11px; color:var(--secondary-text-color); }
  .legend i { display:inline-block; width:10px; height:10px; border-radius:2px; margin-right:4px; vertical-align:-1px; }
  .next { font-size:12px; margin:6px 2px 0; color:var(--secondary-text-color); }
  .empty { font-size:13px; color:var(--secondary-text-color); padding:12px; text-align:center; }
  .gear { background:none; border:none; color:var(--secondary-text-color); cursor:pointer; padding:2px;
          display:flex; align-items:center; justify-content:center; border-radius:50%; }
  .gear:hover { color:var(--primary-color); }
  .gear.open { color:var(--primary-color); }
  .gear ha-icon { --mdc-icon-size:20px; }
  .dev-wrap { display:flex; flex-direction:column; }
  .settings { background:var(--secondary-background-color); border-radius:0 0 var(--radius) var(--radius);
              margin:-4px 0 0; padding:6px 8px 8px; display:flex; flex-direction:column; gap:6px; font-size:13px; }
  .settings.hub { border-radius:var(--radius); margin:0 0 10px; }
  .settings .grp { grid-column:1 / -1; font-size:10px; font-weight:600; letter-spacing:.08em; text-transform:uppercase;
                   color:var(--secondary-text-color); margin-top:4px; }
  .settings label { color:var(--txt); white-space:normal; overflow-wrap:anywhere; }
  .setting-help { grid-column:1 / -1; font-size:12px; line-height:1.45; color:var(--txt); white-space:normal; overflow-wrap:anywhere;
                  background:color-mix(in srgb, var(--primary-color) 10%, transparent); border-radius:6px; padding:6px 8px; margin:2px 0 2px; }
  .sgrp { background:var(--card-background-color); border-radius:calc(var(--radius) - 2px); overflow:hidden; }
  .sgh { width:100%; display:flex; justify-content:space-between; align-items:center; gap:8px; background:none; border:none;
         padding:7px 10px; font:inherit; font-size:13px; font-weight:600; color:var(--txt); cursor:pointer; text-align:left; }
  .sgh small { font-weight:400; font-size:11px; color:var(--secondary-text-color); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; min-width:0; }
  .sgrid { display:grid; grid-template-columns:repeat(auto-fill,minmax(min(100%,300px),1fr)); column-gap:20px; align-items:start; padding:0 10px 4px; }
  .srow { display:grid; grid-template-columns:minmax(0,1fr) auto; align-items:center; column-gap:8px; padding:5px 0;
          border-top:1px solid var(--divider-color); min-height:34px; }
  .slabel { display:flex; flex-direction:column; min-width:0; }
  .sname { color:var(--txt); display:flex; align-items:center; gap:5px; min-width:0; }
  .sshort { font-size:11px; color:var(--secondary-text-color); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .info { flex:none; width:16px; height:16px; padding:0; border-radius:50%; border:1.3px solid var(--secondary-text-color);
          background:none; color:var(--secondary-text-color); font:700 10px/1 sans-serif; cursor:pointer; display:inline-flex;
          align-items:center; justify-content:center; }
  .info.on, .info:hover { background:var(--primary-color); border-color:var(--primary-color); color:var(--text-primary-color,#fff); }
  .settings .ctl { display:flex; align-items:center; gap:4px; justify-self:end; }
  .settings input[type=number], .settings input[type=time], .settings select.set {
    background:var(--card-background-color); color:var(--txt); border:1px solid var(--divider-color);
    border-radius:4px; padding:4px 6px; font-size:13px; box-sizing:border-box; }
  .settings input[type=number] { width:80px; text-align:right; }
  .settings select.set { max-width:170px; }
  .settings .unit { font-size:11px; color:var(--secondary-text-color); min-width:30px; }
  .settings button.act { border:1px solid var(--divider-color); background:var(--card-background-color); color:var(--txt);
                         border-radius:12px; padding:3px 12px; font-size:12px; cursor:pointer; }
  .settings button.act:hover { border-color:var(--primary-color); }
  .tgl { position:relative; width:36px; height:20px; }
  .tgl input { opacity:0; width:0; height:0; }
  .tgl span { position:absolute; inset:0; background:var(--divider-color); border-radius:10px; cursor:pointer; transition:.2s; }
  .tgl span::before { content:""; position:absolute; width:16px; height:16px; left:2px; top:2px; background:#fff; border-radius:50%; transition:.2s; }
  .tgl input:checked + span { background:var(--primary-color); }
  .tgl input:checked + span::before { transform:translateX(16px); }
  .pv-compare-toggle{display:flex;align-items:center;gap:8px;width:100%;padding:11px 8px;border:0;
    border-bottom:1px solid var(--divider-color);background:transparent;color:var(--primary-text-color);
    font:inherit;font-weight:600;text-align:left;cursor:pointer}
  .pv-compare-toggle span:last-child{margin-left:auto;color:var(--secondary-text-color);font-size:12px}
  .pv-compare-body{padding:10px 8px 14px;background:color-mix(in srgb,var(--row-bg) var(--sep-surface-opacity,100%),transparent);border-radius:var(--radius)}
  .pv-compare-totals{display:flex;gap:14px;flex-wrap:wrap;padding:5px 0 13px}
  .pv-compare-selected-day{flex:0 0 100%;font-weight:600;font-size:13px;color:var(--primary-text-color)}
  .pv-compare-totals>div{min-width:75px;display:flex;flex-direction:column;gap:3px}
  .pv-compare-totals small{color:var(--secondary-text-color);font-size:11px}
  .pv-compare-totals strong{font-size:16px;font-variant-numeric:tabular-nums}
  .pv-compare-scroll{overflow-x:auto;overscroll-behavior-x:contain;touch-action:pan-x pan-y}
  .pv-plan-scroll{overflow-x:auto;overscroll-behavior-x:contain;touch-action:pan-x pan-y;min-width:0;
    scrollbar-width:thin;scrollbar-color:var(--secondary-text-color) transparent}
  .pv-plan-missing{flex:none;box-sizing:border-box;height:96px;width:216px;
    display:flex;justify-content:center;align-items:center;text-align:center;
    border:1px dashed var(--divider-color);border-radius:4px;padding:10px;
    background:color-mix(in srgb,var(--secondary-text-color) 7%,transparent);
    color:var(--secondary-text-color);font-size:11px;line-height:1.4;white-space:normal}
  .pv-plan-coverage{font-size:11px;color:var(--secondary-text-color);padding:5px 2px 1px;
    overflow-wrap:anywhere}
  .pv-plan-missing-label{flex:none;width:216px;text-align:center;color:var(--secondary-text-color);
    font-size:10px}
  .pv-plan-days{display:flex;height:24px;box-sizing:border-box}
  .pv-plan-day{box-sizing:border-box;font-size:11px;font-weight:600;padding:3px 4px 5px;
    white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:var(--primary-text-color)}
  .pv-plan-scroll .bars>.col,.pv-plan-scroll .labels>.pv-hour-label{
    flex:0 0 40px;min-width:40px;box-sizing:border-box}
  .pv-plan-scroll .pv-break,.pv-plan-scroll .pv-break-label{flex:0 0 12px;min-width:12px}
  .pv-plan-scroll .labels{width:100%}
  .pv-tip{display:flex;align-items:center;justify-content:center;gap:6px;min-height:48px;
    padding:4px 0 10px;color:var(--primary-text-color);font:inherit}
  .pv-tip-content{min-width:0;text-align:center;line-height:1.35}
  .pv-tip-title{font-size:16px;font-weight:600;overflow-wrap:anywhere}
  .pv-tip-detail{font-size:14px;color:var(--secondary-text-color);overflow-wrap:anywhere}
  .pv-tip-nav{flex:none;border:0;background:transparent;color:var(--secondary-text-color);
    font:inherit;font-size:15px;cursor:pointer;padding:5px;min-width:27px}
  .pv-tip-nav:focus-visible{outline:2px solid var(--primary-color);border-radius:4px}
  .pv-tip-count{font-size:10px;color:var(--secondary-text-color);margin-left:5px}

  .pv-compare-days{display:flex;gap:5px;min-width:100%;height:28px;box-sizing:border-box;font-variant-numeric:tabular-nums}
  .pv-compare-day{flex:none;min-width:0;box-sizing:border-box;
    color:var(--primary-text-color);font-size:11px;font-weight:600;padding:4px 4px 6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .pv-compare-day small{font-size:10px;font-weight:400;margin-left:5px}
  .pv-compare-hour-pct{position:absolute;left:50%;transform:translateX(-50%);font-size:9px;text-align:center;white-space:nowrap;line-height:1;z-index:3}
  .pv-compare-hour-pct.good,.pv-compare-day .good{color:var(--success-color,#22a06b)}
  .pv-compare-hour-pct.medium,.pv-compare-day .medium{color:var(--warning-color,#e5a21a)}
  .pv-compare-hour-pct.bad,.pv-compare-day .bad{color:var(--error-color,#e53935)}
  .pv-compare-day-dividers{position:absolute;inset:0;pointer-events:none;z-index:3}
  .pv-compare-day-divider{position:absolute;top:0;bottom:0;border-left:2px dashed color-mix(in srgb,var(--primary-text-color) 65%,transparent)}
  .pv-compare-plot{min-width:max(100%,580px);height:186px;display:flex;align-items:end;gap:5px;position:relative;box-sizing:border-box;
    padding:30px 0 0;border-bottom:1px solid var(--divider-color)}
  .pv-compare-plot .sep-chart-grid{top:30px}
  .pv-compare-col{flex:0 0 40px;min-width:40px;height:100%;display:flex;align-items:end;justify-content:center;gap:2px;position:relative;z-index:1}
  .pv-compare-bar{width:42%;min-height:0;border-radius:3px 3px 0 0}
  .pv-compare-forecast{background:var(--warning-color,#e5a21a);opacity:.82}
  .pv-compare-actual{background:var(--success-color,#22a06b)}
  .pv-compare-labels{min-width:max(100%,580px);display:flex;gap:5px}
  .pv-compare-labels span{flex:0 0 40px;min-width:40px;text-align:center;color:var(--secondary-text-color);font-size:10px}
  .pv-compare-legend{display:flex;gap:16px;flex-wrap:wrap;margin-top:10px;font-size:12px;color:var(--secondary-text-color)}
  .pv-compare-legend i{display:inline-block;width:11px;height:11px;border-radius:2px;margin-right:5px;vertical-align:middle}
  .pv-compare-note{font-size:11px;color:var(--secondary-text-color);margin-top:8px}
  @media(max-width:560px){.pv-compare-totals{gap:9px}.pv-compare-totals strong{font-size:14px}}
  /* These rules must come after the default surface rules above. */
  .tile, .dev, .timeline { background:color-mix(in srgb, var(--row-bg) var(--sep-surface-opacity,100%), transparent); }
  .settings { background:color-mix(in srgb, var(--secondary-background-color) var(--sep-surface-opacity,100%), transparent); }
`;

// Patch live values in place. Preserve nodes, handlers, focus and scroll position.
function patchChildren(parent, source) {
  const key = node => node.nodeType === 1 ? (node.getAttribute("data-device") || node.getAttribute("data-select") || node.getAttribute("data-num") || node.getAttribute("data-gear") || "") : "";
  const same = (a, b) => a && a.nodeType === b.nodeType && a.nodeName === b.nodeName && key(a) === key(b);
  const wanted = [...source.childNodes];
  wanted.forEach((next, i) => {
    let old = parent.childNodes[i];
    if (!same(old, next)) {
      const match = key(next) && [...parent.childNodes].slice(i + 1).find(n => same(n, next));
      if (match) { parent.insertBefore(match, old || null); old = match; }
      else { const copy = next.cloneNode(true); parent.insertBefore(copy, old || null); old = copy; }
    }
    if (old.nodeType === 3) { if (old.textContent !== next.textContent) old.textContent = next.textContent; return; }
    if (old.nodeType !== 1) return;
    for (const attr of [...old.attributes]) if (!next.hasAttribute(attr.name)) old.removeAttribute(attr.name);
    for (const attr of next.attributes) if (old.getAttribute(attr.name) !== attr.value) old.setAttribute(attr.name, attr.value);
    patchChildren(old, next);
    if (old.matches("input")) { old.value = next.value; old.checked = next.checked; }
    if (old.matches("select")) old.value = next.value;
  });
  while (parent.childNodes.length > wanted.length) parent.lastChild.remove();
}

class SmartifyEnergyPlanCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this._sig = "";
    this._drag = null;
    this._priorityLocked = true; // Fail-safe default on reload: prevents accidental mobile reordering.
    this._sectionMove = null;
    this._pvPlanFirstOverride = null;
    this._priorityOrder = null;
    this._prioritySaving = false;
    this._priorityError = "";
    this._open = new Set();
    this._logOpen = new Set();
    this._infoOpen = new Set();   // (i) aufgeklappte Erklärungen
    this._grpOpen = new Set();    // geöffnete, standardmäßig zugeklappte Gruppen
    this._grpClosed = new Set();  // geschlossene, standardmäßig offene Gruppen
    this._boostUntil = {};
    this._pvCompareOpen = false;
    this._pvCompareDay = null;
    this._pvTipIndex = 0;
  }

  static getConfigElement() { return document.createElement("smartify-energy-plan-card-editor"); }
  static getStubConfig() { return { show_header: true, show_priorities: true, show_timeline: true, timeline_hours: 24 }; }

  setConfig(config) {
    this._config = { show_header: true, show_priorities: true, show_timeline: true, show_pv_tips: true, show_mode: true, timeline_hours: 24, pv_plan_first: false, ...config };
    this._pvPlanFirstOverride = null;
    // A saved Lovelace card option takes priority. Otherwise remember in-card
    // drag changes for this browser until the user saves a global card setting.
    if (!Object.prototype.hasOwnProperty.call(config, "pv_plan_first")) {
      try {
        const value = window.localStorage?.getItem(this._pvOrderKey());
        if (value === "1" || value === "0") this._pvPlanFirstOverride = value === "1";
      } catch (_) { /* Private-mode storage may be unavailable. */ }
    }
    this._sig = "";
    if (this._hass) this._render();
  }

  _pvOrderKey() {
    return "smartify-energy:pv-plan-first:" + (this._config.hub || "auto") + ":" + (this._config.title || "");
  }

  _changeSectionOrder(next) {
    if (this._config.pv_plan_first === next && this._pvPlanFirstOverride === next) return;
    this._pvPlanFirstOverride = next;
    try { window.localStorage?.setItem(this._pvOrderKey(), next ? "1" : "0"); } catch (_) { }
    // Lovelace card editor persists this option globally; normal card view
    // remembers the gesture locally and exposes an editable configuration.
    this.dispatchEvent(new CustomEvent("config-changed", {
      detail: { config: { ...this._config, pv_plan_first: next } }, bubbles: true, composed: true,
    }));
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    if (this._drag) return;
    const data = collect(hass, this._config.hub);
    const ids = data ? [...Object.values(data.ents), ...data.hubSettings.map(x => x.id),
      ...data.devices.flatMap(d => [d.status, d.power, d.planned, d.mode, d.active, d.nachladen, d.boost, ...d.settings.map(x => x.id)])] : [];
    const sig = ids.map(id => { const s = hass.states[id]; return s ? `${id}:${s.last_updated}` : id; }).join("|");
    if (sig === this._sig) return;
    this._data = data;
    // Retain optimistic order until the server has published all new ranks.
    if (this._priorityOrder && !this._prioritySaving && data) {
      const actual = data.devices.map(dev => ({
        id: dev.id,
        rank: dev.virtualBattery
          ? (num(hass.states[dev.rankEntity]?.state) ?? 99)
          : (num(hass.states[dev.status]?.attributes?.prioritaet) ?? 5),
      })).sort((a, b) => a.rank - b.rank || a.id.localeCompare(b.id)).map(x => x.id);
      if (actual.join("|") === this._priorityOrder.join("|")) this._priorityOrder = null;
    }
    // Do not replace an actively edited input OR native select dropdown.
    const active = this.shadowRoot.activeElement;
    if (active && active.matches?.("input[type=number], input[type=time], select")) {
      if (!this._pendingBlur) {
        this._pendingBlur = true;
        active.addEventListener("blur", () => { this._pendingBlur = false; this._sig = ""; this.hass = this._hass; }, { once: true });
      }
      return;
    }
    this._sig = sig;
    this._render();
  }

  getCardSize() { return 3 + (this._data?.devices.length || 0); }
  getGridOptions() { return { columns: 12, min_columns: 6 }; }

  _st(id) { return id ? this._hass.states[id] : undefined; }
  _moreInfo(entityId) {
    if (!entityId) return;
    const ev = new Event("hass-more-info", { bubbles: true, composed: true });
    ev.detail = { entityId };
    this.dispatchEvent(ev);
  }

  // ── Bereiche ──────────────────────────────────────────────────────────────
  _header(d) {
    const e = d.ents;
    const surplus = this._st(e["sensor:surplus"]);
    const avg = this._st(e["sensor:surplus_avg"]);
    const budget = this._st(e["sensor:budget"]);
    const budgetAvg = this._st(e["sensor:budget_avg"]);
    const alloc = this._st(e["sensor:allocated"]);
    const fc = this._st(e["sensor:forecast_today"]);
    const bat = this._st(e["sensor:battery_priority"]);
    const s = num(surplus?.state);
    const b = num(budget?.state);
    const paired = [
      { title: "Netzsaldo", avg: fmtW(num(avg?.state)), now: fmtW(s),
        ent: e["sensor:surplus_avg"], nowEnt: e["sensor:surplus"],
        icon: "mdi:transmission-tower", g: s >= 0 ? ["#81C784", "#00ACC1"] : ["#FFB74D", "#E65100"] },
      { title: "Steuerbudget", avg: budgetAvg ? fmtW(num(budgetAvg.state)) : "–",
        now: budget ? fmtW(b) : "–",
        ent: e["sensor:budget_avg"], nowEnt: e["sensor:budget"],
        icon: "mdi:solar-power-variant", g: b > 0 ? ["#81C784", "#00ACC1"] : ["#FFB74D", "#E65100"] },
    ];
    const tiles = this._config.show_allocated
      ? [{ ent: e["sensor:allocated"], icon: "mdi:call-split", v: fmtW(num(alloc?.state)), n: "Verteilt", g: PALETTE[0] }]
      : [];
    if (fc && fc.state !== "unknown" && fc.state !== "unavailable") {
      const rest = fc.attributes.rest_heute_kwh;
      const source = fc.attributes.prognose_quelle || (fc.attributes.prognose_modus === "calculated" ? "Eigene Berechnung" : "Externe Prognose");
      tiles.push({ ent: e["sensor:forecast_today"], icon: "mdi:weather-sunny", v: `${num(fc.state)?.toFixed(1)} kWh`,
                   n: rest != null ? `Rest ${Number(rest).toFixed(1)} kWh` : "Prognose heute",
                   src: `Quelle: ${source}`, g: PV_GRADIENT });
    }
    if (bat) {
      tiles.push({ ent: e["sensor:battery_priority"], icon: bat.state === "speicher" ? "mdi:home-battery" : "mdi:home-lightning-bolt",
                   v: bat.state === "speicher" ? "Speicher" : "Geräte", n: "Vorrang", g: BATTERY_GRADIENT });
    }
    return `<div class="tiles">
      ${paired.map(t => `
        <div class="tile paired" data-more="${t.ent || ""}" style="border-image-source:${grad(t.g)}">
          <ha-icon icon="${t.icon}"></ha-icon>
          <div class="n">${esc(t.title)}</div>
          <div class="metrics">
            <span class="metric-label">Ø</span><span class="metric-value avg">${esc(t.avg)}</span>
            <span class="metric-label">akt.</span><span class="metric-value now" data-more="${t.nowEnt || ""}">${esc(t.now)}</span>
          </div>
        </div>`).join("")}
      ${tiles.map(t => `
        <div class="tile" data-more="${t.ent || ""}" style="border-image-source:${grad(t.g)}">
          <ha-icon icon="${t.icon}"></ha-icon><div class="v">${esc(t.v)}</div><div class="n">${esc(t.n)}</div>${t.src ? `<div class="n forecast-source">${esc(t.src)}</div>` : ""}
        </div>`).join("")}</div>`;
  }

  // Kompakte Auswahl in der Gerätezeile (z. B. Ladeziel), gleiche Optik wie die Modus-Pille.
  _quickSelect(entityId, label) {
    const st = this._st(entityId);
    if (!st || ["unknown", "unavailable"].includes(st.state)) return "";
    return `<select class="mode quick" data-select="${entityId}" aria-label="${esc(label)}" title="${esc(label)}">
      ${(st.attributes.options || []).map(o => `<option value="${esc(o)}" ${o === st.state ? "selected" : ""}>${esc(OPTION_LABELS[o] || o)}</option>`).join("")}
    </select>`;
  }

  // Heizstab: Auto (PV) | Ein (= Modus Manuell: auf Maximaltemperatur, Netz erlaubt) | Aus.
  _heaterSwitch(entityId) {
    const st = this._st(entityId);
    if (!st) return "";
    const opts = [["auto", "Auto", "Automatik: nur mit PV-Überschuss"],
      ["manual", "Ein", "Ein: heizt bis zur Maximaltemperatur, auch mit Netzstrom (Temperaturschutz und Mindestpause bleiben aktiv)"],
      ["off", "Aus", "Aus: Heizstab sofort ausschalten"]];
    return `<div class="seg" role="group" aria-label="Heizstab">${opts.map(([v, l, t]) =>
      `<button type="button" class="${st.state === v ? "on " + v : ""}" data-setmode="${esc(entityId)}" data-opt="${v}" title="${esc(t)}" aria-pressed="${st.state === v}">${l}</button>`).join("")}</div>`;
  }

  _modeSelect(entityId, cls = "") {
    const st = this._st(entityId);
    if (!st) return "";
    const opts = st.attributes.options || Object.keys(MODE_LABELS);
    return `<select class="mode ${esc(st.state)} ${cls}" data-select="${entityId}" aria-label="Betriebsmodus">
      ${opts.map(o => `<option value="${esc(o)}" ${o === st.state ? "selected" : ""}>${esc(MODE_LABELS[o] || o)}</option>`).join("")}
    </select>`;
  }

  _label(entityId, prefix) {
    const st = this._st(entityId);
    let name = st?.attributes?.friendly_name || entityId;
    if (prefix && name.startsWith(prefix)) {
      const trimmed = name.slice(prefix.length).trim();
      if (trimmed) name = trimmed;
    }
    return name;
  }

  _control(item) {
    const st = this._st(item.id);
    if (!st) return "";
    const a = st.attributes || {};
    const unsetLimit = item.dom === "number" && ["sun_angle_min", "cloud_now_max", "cloud_next_max"].includes(item.key) && st.state === "unknown";
    const dis = ["unavailable", "unknown"].includes(st.state) && item.dom !== "button" && !unsetLimit ? "disabled" : "";
    switch (item.dom) {
      case "number": {
        const unit = a.unit_of_measurement ? `<span class="unit">${esc(a.unit_of_measurement)}</span>` : "";
        return `<input type="number" data-num="${item.id}" placeholder="Nicht festgelegt" value="${unsetLimit ? "" : esc(st.state)}" min="${a.min ?? ""}" max="${a.max ?? ""}" step="${a.step ?? "any"}" ${dis}>${unit}`;
      }
      case "select":
        return `<select class="set" data-select="${item.id}" ${dis}>${(a.options || []).map(o =>
          `<option value="${esc(o)}" ${o === st.state ? "selected" : ""}>${esc(OPTION_LABELS[o] || o)}</option>`).join("")}</select>`;
      case "switch":
        return `<label class="tgl"><input type="checkbox" data-switch="${item.id}" ${st.state === "on" ? "checked" : ""} ${dis}><span></span></label>`;
      case "time":
        return `<input type="time" data-time="${item.id}" value="${esc(String(st.state).slice(0, 5))}" ${dis}>`;
      case "button":
        return `<button class="act" data-press="${item.id}">Ausführen</button>`;
      default:
        return "";
    }
  }

  _settingValue(item) {
    const st = this._st(item.id);
    if (!st || ["unknown", "unavailable"].includes(st.state)) return "–";
    if (item.dom === "switch") return st.state === "on" ? "an" : "aus";
    if (item.dom === "select") return OPTION_LABELS[st.state] || MODE_LABELS[st.state] || st.state;
    if (item.dom === "time") return String(st.state).slice(0, 5);
    const n = num(st.state);
    const unit = st.attributes?.unit_of_measurement || "";
    return `${n == null ? st.state : String(n).replace(".", ",")}${unit ? ` ${unit}` : ""}`;
  }

  _settingHelp(item) {
    if (item.key === "mode" && this._st(item.id)?.attributes?.options?.includes("disabled"))
      return "Automatik: SEP löst den WW-Boost nach den eingestellten Bedingungen aus. Beobachten: nur Empfehlungen, kein Auslösen. Deaktiviert: kein neuer WW-Boost durch SEP. Eine bereits gestartete Warmwasserladung läuft unter Kontrolle der Wärmepumpe weiter.";
    return SETTING_HELP[item.key] || "";
  }

  _settings(items, prefix, cls = "", scope = "hub") {
    if (!items.length) return "";
    const byKey = Object.fromEntries(items.map(i => [i.key, i]));
    const stateOf = key => byKey[key] ? this._st(byKey[key].id)?.state ?? null : null;
    const visible = items.filter(i => !SETTING_VISIBLE[i.key] || SETTING_VISIBLE[i.key](stateOf));
    const known = new Set(SETTING_GROUPS.flatMap(g => g.keys));
    const groups = [
      ...SETTING_GROUPS.map(g => ({ ...g, items: g.keys.map(k => visible.find(i => i.key === k)).filter(Boolean) })),
      { id: "other", title: "Weitere", items: visible.filter(i => !known.has(i.key)) },
    ].filter(g => g.items.length);
    const row = i => {
      const help = this._settingHelp(i);
      const infoKey = `${scope}:${i.id}`;
      const infoOpen = this._infoOpen.has(infoKey);
      const label = SETTING_LABELS[i.key] || this._label(i.id, prefix);
      return `<div class="srow">
          <div class="slabel"><span class="sname" title="${esc(label)}">${esc(label)}${help ? ` <button type="button" class="info ${infoOpen ? "on" : ""}" data-info="${esc(infoKey)}" aria-expanded="${infoOpen}" aria-label="Erklärung ${esc(label)}">i</button>` : ""}</span>
            ${SETTING_SHORT[i.key] ? `<span class="sshort">${esc(SETTING_SHORT[i.key])}</span>` : ""}</div>
          <div class="ctl">${this._control(i)}</div>
          ${infoOpen && help ? `<div class="setting-help">${esc(help)}</div>` : ""}
        </div>`;
    };
    return `<div class="settings ${cls}">${groups.map(g => {
      const gKey = `${scope}:${g.id}`;
      const open = g.collapsed ? this._grpOpen.has(gKey) : !this._grpClosed.has(gKey);
      let summary = "";
      if (g.id === "boost") {
        const until = stateOf("boost") === "on" ? this._boostUntil?.[scope] : null;
        summary = until ? `läuft bis ${until}` : stateOf("boost") === "on" ? "läuft" : "";
      }
      if (!open && !summary) summary = g.items.slice(0, 3).map(i => `${SETTING_LABELS[i.key] || this._label(i.id, prefix)} ${this._settingValue(i)}`).join(" · ");
      return `<div class="sgrp ${open ? "open" : ""}">
        <button type="button" class="sgh" data-grp="${esc(gKey)}" data-collapsed="${g.collapsed ? 1 : 0}" aria-expanded="${open}">
          <span>${esc(g.title)}</span><small>${esc(summary)} ${open ? "▾" : "▸"}</small></button>
        ${open ? `<div class="sgrid">${g.items.map(row).join("")}</div>` : ""}
      </div>`;
    }).join("")}</div>`;
  }

  _devices(d) {
    const rows = d.devices
      .map(dev => ({ dev, prio: this._priorityOrder?.includes(dev.id)
        ? this._priorityOrder.indexOf(dev.id) + 1
        : dev.virtualBattery
          ? (num(this._st(dev.rankEntity)?.state) ?? 99)
          : (num(this._st(dev.status)?.attributes?.prioritaet) ?? 5) }))
      .sort((a, b) => {
        if (this._priorityOrder) {
          const x = this._priorityOrder.indexOf(a.dev.id);
          const y = this._priorityOrder.indexOf(b.dev.id);
          if (x >= 0 && y >= 0) return x - y;
        }
        return a.prio - b.prio || a.dev.name.localeCompare(b.dev.name);
      });
    if (!rows.length) return `<div class="empty">Noch keine Geräte – in der Integration „+ Gerät hinzufügen“.</div>`;
    return `${this._priorityError ? `<div role="alert" style="padding:8px 12px;color:var(--error-color);border:1px solid var(--error-color);border-radius:8px;margin-bottom:8px">Prioritäten konnten nicht gespeichert werden: ${esc(this._priorityError)}</div>` : ""}<div class="list">${rows.map(({ dev, prio }) => {
      if (dev.virtualBattery) {
        const charge = Math.max(0, num(this._st(dev.batteryBudget)?.attributes?.speicher_w) || 0);
        const soc = num(this._st(dev.status)?.attributes?.soc);
        return `<div class="dev-wrap" data-wrap="__battery__">
          <div class="dev" data-dev="__battery__" style="border-image-source:linear-gradient(var(--divider-color),var(--divider-color))">
            <div class="handle ${this._priorityLocked ? "locked" : ""}" title="${this._priorityLocked ? "Prioritäten gesperrt – oben entsperren" : "PV-Akku per Drag & Drop priorisieren"}">⠿</div>
            <div class="badge" style="background:${grad(BATTERY_GRADIENT)}">${Math.round(prio)}</div>
            <ha-icon icon="mdi:home-battery" style="color:var(--primary-text-color)"></ha-icon>
            <div class="main"><div class="name"><span class="t">PV-Akku</span></div>
              <div class="sub">Restverbraucher · Akku regelt selbst</div></div>
            <div class="right"><div class="power-budget">
              <div class="pb-item"><span class="pb-label">Lädt</span><span class="pw">${fmtW(charge)}</span></div>
              <div class="pb-item"><span class="pb-label">SoC</span><span class="pb-budget">${soc == null ? "–" : soc.toFixed(0) + " %"}</span></div>
            </div></div>
          </div></div>`;
      }
      const st = this._st(dev.status);
      const a = st?.attributes || {};
      const mode = a.modus || this._st(dev.mode)?.state;
      const reserved = num(a.reserviert_w) || 0;
      const on = reserved > 0;
      const forced = on && a.pflicht;
      const power = num(this._st(dev.power)?.state);
      const budgetNow = num(a.aktuell_w);
      const budgetAverage = num(a.mittel_w);
      const upstream = num(a.vorreservierung_w);
      const needed = num(a.benoetigt_w);
      const budgetOk = needed != null && budgetNow != null && budgetAverage != null
        && budgetNow >= needed && budgetAverage >= needed;
      const budgetTitle = budgetNow == null ? "Kein gerätespezifisches Budget verfügbar" :
        `Budget für ${dev.name}: aktuell ${fmtW(budgetNow)}, Mittelwert ${fmtW(budgetAverage)}, vorher reserviert ${fmtW(upstream)}, benötigt ${fmtW(needed)}`;
      const icon = a.icon || TYPE_ICONS[a.geraetetyp] || "mdi:flash";
      const border = forced ? FORCED_GRADIENT : on ? dev.color : null;
      const statusTxt = STATUS_LABELS[st?.state] || st?.state || "";
      const rawSub = mode === "observe" && a.empfehlung ? `Empfehlung: ${a.empfehlung}` : (a.reason || a.grund || statusTxt);
      const sub = ["finished", "fertig"].includes(st?.state) || ["finished", "fertig"].includes(a.status_code)
        ? "Neues Programm wird autom. erkannt" : rawSub;
      const planned = this._st(dev.planned);
      const pt = planned && planned.state && !["unknown", "unavailable"].includes(planned.state) ? fmtTime(planned.state) : null;
      const trendRelevant = ["load", "heatpump"].includes(a.geraetetyp);
      const trendAge = num(a.trend_history_min);
      const trendWindow = num(a.trend_window_min);
      const avgWindow = num(this._st(d.ents["number:avg_window"])?.state);
      const trendDelta = num(a.trend_delta_w);
      const trendReady = a.trend_ready === true;
      const trendTolerance = num(this._st(d.ents["number:trend_tolerance"])?.state) ?? 100;
      const trendRecent = num(a.trend_mittel_w);
      const direction = deviceTrend(trendRecent, needed, trendDelta, trendTolerance, trendReady);
      const avgReady = a.history_avg_ready === true;
      const avgMissing = avgWindow == null || trendAge == null ? null : Math.max(0, avgWindow * 0.9 - trendAge);
      // Drei unabhängige Startbedingungen: Historie (H), Trend (T), Budget (B).
      // Die Anzeige spiegelt die normale PV-Startfreigabe wider; Sonderfreigaben
      // (z. B. WW bereits aktiv) haben eigene Regeln.
      const trendOk = trendReady && direction.allowed;
      const gateColor = ok => ok ? "var(--success-color, #43a047)" : "var(--error-color, #e53935)";
      const GATE_ICONS = { H: "mdi:history", T: direction.direction === "down" ? "mdi:trending-down" : "mdi:trending-up", B: "mdi:scale-balance" };
      const gate = (letter, ok, explanation) =>
        `<ha-icon class="sep-gate" icon="${GATE_ICONS[letter]}" style="color:${gateColor(ok)}" title="${esc(explanation)}" aria-label="${esc(letter + ": " + explanation)}"></ha-icon>`;
      const historyInfo = `Historie: ${trendAge ?? "–"} min vorhanden, benötigt ${avgWindow ?? "–"} min; Ø ${fmtW(budgetAverage)}`;
      const trendInfo = `Trend: ${trendReady ? (trendOk ? "Bedingung erfüllt" : "Bedingung nicht erfüllt") : "Messhistorie noch nicht vollständig"}; Fenster ${trendWindow ?? "–"} min, Kurzzeit-Ø ${fmtW(trendRecent)}, Änderung ${fmtW(trendDelta)}, Fortschreibung ${fmtW(direction.projected)}, benötigt ${fmtW(needed)}`;
      const budgetInfo = `Budget: ${budgetOk ? "Bedingung erfüllt" : "Bedingung nicht erfüllt"}; aktuell ${fmtW(budgetNow)}, Ø ${fmtW(budgetAverage)}, benötigt ${fmtW(needed)}`;
      // Auto: eigene PV-Startprüfung (Historie + Budget aktuell/2-min-Ø gegen Startschwelle), kein Trend.
      const evGate = a.geraetetyp === "ev" ? a.pv_startpruefung : null;
      const evH = evGate ? evGate.mittel_bereit === true : true;
      const evB = evGate ? evGate.aktuell_w >= evGate.schwelle_w && evGate.mittel_w >= evGate.schwelle_w : true;
      const evThresholdTxt = evGate ? `${fmtW(evGate.schwelle_w)} (${fmtW(evGate.min_w)} Mindestladeleistung × ${evGate.pv_anteil} % PV-Anteil)` : "";
      const evHistoryInfo = evGate ? `Historie: ${evH ? "Mittelwert bereit" : `noch nicht vollständig (${trendAge ?? "–"} min von ${avgWindow == null ? "–" : (avgWindow * 0.9).toFixed(0)} min) – bis dahin zählt nur der aktuelle Wert`}` : "";
      const evBudgetInfo = evGate ? `Budget: ${evB ? "Bedingung erfüllt" : "Bedingung nicht erfüllt"}; aktuell ${fmtW(evGate.aktuell_w)}, 2-min-Ø ${fmtW(evGate.mittel_w)}, benötigt ≥ ${evThresholdTxt}` : "";
      const evGateText = evGate
        ? `<span class="sep-gates" title="${esc(evHistoryInfo + " | " + evBudgetInfo)}">${evH ? "" : gate("H", false, evHistoryInfo)}${gate("B", evB, evBudgetInfo)}${evH && evB ? '<ha-icon icon="mdi:check-circle" class="sep-history-icon" style="color:var(--success-color, #43a047)"></ha-icon>' : ""}</span>`
        : "";
      const trendText = evGateText || (trendRelevant
        ? `<span class="sep-gates" title="${esc(historyInfo + " | " + trendInfo + " | " + budgetInfo)}">${avgReady ? "" : gate("H", avgReady, historyInfo)}${gate("T", trendOk, trendInfo)}${gate("B", budgetOk, budgetInfo)}${avgReady && trendOk && budgetOk ? '<ha-icon icon="mdi:check-circle" class="sep-history-icon" style="color:var(--success-color, #43a047)"></ha-icon>' : ""}</span>`
        : "");
      const logOpen = this._logOpen.has(dev.id);
      const logRow = (letter, ok, detail) =>
        `<div class="sep-log-row"><ha-icon class="sep-gate" icon="${GATE_ICONS[letter]}" style="color:${gateColor(ok)}"></ha-icon><span class="sep-log-detail">${esc(detail)}</span></div>`;
      const historyNeed = avgWindow == null ? null : avgWindow * 0.9;
      const trendHistoryNeed = trendWindow == null ? null : trendWindow * 2;
      const logText = evGate ? `<div class="sep-log" data-log-panel="${esc(dev.id)}" id="sep-log-${esc(dev.id)}">
        ${logRow("H", evH, evH ? "Mittelwert bereit (90 % des Mittelungsfensters)" : `Ist ${trendAge == null ? "–" : trendAge.toFixed(1)} min / Soll ${historyNeed == null ? "–" : historyNeed.toFixed(1)} min – bis dahin zählt nur der aktuelle Wert`)}
        ${logRow("B", evB, `Aktuell Ist ${fmtW(evGate.aktuell_w)} / Soll ≥ ${fmtW(evGate.schwelle_w)}; 2-min-Ø Ist ${fmtW(evGate.mittel_w)} / Soll ≥ ${fmtW(evGate.schwelle_w)} · Schwelle = Mindestladeleistung ${fmtW(evGate.min_w)} (${evGate.phasen}-phasig) × ${evGate.pv_anteil} % PV-Anteil`)}
      </div>` : trendRelevant ? `<div class="sep-log" data-log-panel="${esc(dev.id)}" id="sep-log-${esc(dev.id)}">
        ${logRow("H", avgReady, `Ist ${trendAge == null ? "–" : trendAge.toFixed(1)} min / Soll ${historyNeed == null ? "–" : historyNeed.toFixed(1)} min (90 % von ${avgWindow ?? "–"} min)`)}
        ${logRow("T", trendOk, `Kurzzeit-Ø Ist ${fmtW(trendRecent)} / Soll ≥ ${fmtW(needed)} (Pflicht); Änderung Ist ${fmtW(trendDelta)} / Soll ≥ ${fmtW(-trendTolerance)} ODER bei stärkerem Abfall Prognose Ist ${fmtW(direction.projected)} / Soll ≥ ${fmtW(needed)}`)}
        ${logRow("B", budgetOk, `Aktuell Ist ${fmtW(budgetNow)} / Soll ≥ ${fmtW(needed)}; Ø Ist ${fmtW(budgetAverage)} / Soll ≥ ${fmtW(needed)}`)}
      </div>` : "";
      const logToggle = trendRelevant || evGate ? `<button type="button" class="sep-log-toggle" data-log="${esc(dev.id)}" aria-expanded="${logOpen}" aria-controls="sep-log-${esc(dev.id)}" title="Ist- und Sollwerte für Historie, Trend und Budget anzeigen">${logOpen ? "Info ▴" : "Info ▾"}</button>` : "";
      const forcedAt = a.pflicht_start && !forced ? Date.parse(a.pflicht_start) : NaN;
      const forcedTxt = Number.isFinite(forcedAt)
        ? (forcedAt <= Date.now() + 60e3 ? "Pflichtstart fällig" : `Pflichtstart ${fmtTime(a.pflicht_start)}`) : "";
      // Auto: läuft die Stopp-Verzögerung (zu wenig PV), Abschaltzeit zeigen.
      const evBoosting = a.geraetetyp === "ev" && (a.status_code === "boost" || st?.state === "boost");
      const pvStopTxt = a.geraetetyp === "ev" && a.pv_stopp_um && fmtTime(a.pv_stopp_um)
        ? `${evBoosting ? "Boost endet" : "PV-Stopp"} ${fmtTime(a.pv_stopp_um)} – zu wenig Überschuss` : "";
      // Lädt das Auto bereits, ist eine Start-Empfehlung irreführend.
      const evCharging = a.geraetetyp === "ev" && ["boost", "charging_pv", "charging_now", "charging_required"]
        .includes(a.status_code || st?.state);
      const planTxt = [pt && !evCharging ? `Empf. Start ${pt}${planned.attributes.pv_anteil_prozent != null ? ` · ${planned.attributes.pv_anteil_prozent} % PV` : ""}` : "", forcedTxt]
        .filter(Boolean).join(" · ");
      // Aktionen nur anzeigen, wenn sie im aktuellen Zustand wirken.
      const phase = a.phase || a.status_code || st?.state;
      const canAct = (a.geraetetyp === "load" || a.geraetetyp === "ev") && mode !== "off";
      const boostOn = this._st(dev.boost)?.state === "on";
      const boostUntil = a.geraetetyp === "ev" && boostOn && a.boost_bis ? fmtTime(a.boost_bis) : null;
      const boostTxt = boostUntil ? `Boost bis ${boostUntil}` : "";
      this._boostUntil[dev.id] = boostUntil;
      const boostPossible = mode === "auto" && !["nicht_verbunden", "disconnected", "voll", "full",
        "laedt_sofort", "charging_now", "laedt_pflicht", "charging_required"].includes(phase);
      // Auto: Ladeziel und Boost als eine Bediengruppe im Leistungsblock.
      const evGoalCtl = a.geraetetyp === "ev" && this._config.show_mode !== false ? this._quickSelect(dev.goal, "Ladeziel") : "";
      const evBoostCtl = dev.boost && canAct && (boostOn || boostPossible)
        ? `<button type="button" class="gear boost ${boostOn ? "on" : ""}" data-toggle="${esc(dev.boost)}" title="${boostOn ? "Boost beenden" : "PV-Boost starten"}" aria-label="${boostOn ? "Boost beenden" : "PV-Boost starten"}"><ha-icon icon="${boostOn ? "mdi:rocket-launch" : "mdi:rocket-launch-outline"}"></ha-icon></button>` : "";
      const nachladenOn = this._st(dev.nachladen)?.state === "on";
      const act = (attr, id, icon, label, cls = "") =>
        `<button type="button" class="sep-act ${cls}" ${attr}="${esc(id)}"><ha-icon icon="${icon}"></ha-icon>${esc(label)}</button>`;
      const actions = canAct ? [
        dev.startNow && ["erkannt", "wartet", "detected", "waiting"].includes(phase)
          ? act("data-press", dev.startNow, "mdi:play-circle", "Sofortstart") : "",
        dev.nachladen && ["wartet", "waiting"].includes(phase)
          ? act("data-toggle", dev.nachladen, "mdi:washing-machine-alert", nachladenOn ? "Nachladen beenden" : "Nachladen", nachladenOn ? "on" : "") : "",
        dev.reset && ["laeuft", "running"].includes(phase)
          ? act("data-press", dev.reset, "mdi:check-circle-outline", "Fertig") : "",
      ].join("") : "";
      const evSoc = a.geraetetyp === "ev" ? num(a.soc) : null;
      const chip = forced ? `<span class="chip" style="background:${grad(FORCED_GRADIENT)}">Pflicht</span>`
                 : on ? `<span class="chip" style="background:${grad(dev.color)}">${esc(statusTxt || "ein")}</span>`
                 : mode === "observe" ? `<span class="chip" style="background:#B3E5FC">beobachten</span>` : "";
      const open = this._open.has(dev.id);
      return `
        <div class="dev-wrap" data-wrap="${dev.id}">
        <div class="dev" data-dev="${dev.id}" style="${border ? `border-image-source:${grad(border)}` : "border-image-source:linear-gradient(var(--divider-color),var(--divider-color))"}">
          <div class="handle ${this._priorityLocked ? "locked" : ""}" title="${this._priorityLocked ? "Prioritäten gesperrt – oben entsperren" : "Halten und ziehen, um die Priorität zu ändern"}">⠿</div>
          <div class="badge" style="background:${grad(dev.color)}">${Math.round(prio)}</div>
          <ha-icon icon="${esc(icon)}" data-more="${dev.status}" style="color:${on ? dev.color[1] : "var(--secondary-text-color)"}"></ha-icon>
          <div class="main" data-more="${dev.status}">
            <div class="name"><span class="t">${esc(dev.name)}</span>${chip}</div>
            <div class="sub" title="${esc(sub)}">${esc(sub)}</div>
            ${planTxt ? `<div class="plan">${esc(planTxt)}</div>` : ""}
            ${boostTxt ? `<div class="plan sep-boost"><ha-icon icon="mdi:rocket-launch"></ha-icon>${esc(boostTxt)}</div>` : ""}
            ${pvStopTxt ? `<div class="plan sep-stop" title="Stopp-Verzögerung läuft. Kehrt der Überschuss vorher zurück, lädt das Auto weiter und die Anzeige verschwindet."><ha-icon icon="mdi:timer-pause"></ha-icon>${esc(pvStopTxt)}</div>` : ""}
            ${trendText ? `<div class="plan">${trendText} ${logToggle}</div>${logOpen ? logText : ""}` : ""}
          </div>
          <div class="right">
            <div class="power-budget${a.geraetetyp === "heater" ? " heater-power-budget" : a.geraetetyp === "ev" ? " ev-power-budget" : ""}" title="${esc(budgetTitle)}">
              ${a.geraetetyp === "heater" ? this._heaterSwitch(dev.mode) : ""}
              ${a.geraetetyp === "ev" && (evGoalCtl || evBoostCtl) ? `<div class="ev-ctl">${evGoalCtl}${evBoostCtl}</div>` : ""}
              ${a.geraetetyp === "ev" ? `<div class="pb-item"><span class="pb-label">Akku</span><span class="pw">${evSoc == null ? "–" : evSoc.toFixed(0) + " %"}</span>${a.voll_um && fmtTime(a.voll_um) ? `<span class="pb-full" title="Geschätzt bei gleichbleibender Ladeleistung bis Max-SoC">voll ${fmtTime(a.voll_um)}</span>` : ""}</div>` : ""}
              <div class="${a.geraetetyp === "ev" ? "pb-stack" : "pb-pair"}">
              <div class="pb-item">
                <span class="pb-label">Leistung</span>
                <span class="pw">${power != null ? fmtW(power) : "–"}</span>
              </div>
              <div class="pb-item">
                <span class="pb-label">Budget aktuell</span>
                <span class="pb-budget ${budgetNow == null ? "" : budgetNow < 0 ? "negative" : budgetOk ? "positive" : ""}">${fmtW(budgetNow)}</span>
              </div>
              </div>
              ${a.geraetetyp !== "heater" && mode && !["auto", "observe"].includes(mode) ? `<span class="mode-tag ${esc(mode)}" title="Modus – ändern im Zahnrad">${esc(MODE_LABELS[mode] || mode)}</span>` : ""}
              ${actions ? `<div class="sep-actions">${actions}</div>` : ""}
              ${this._config.show_settings !== false && dev.settings.length ? `<button class="gear ${open ? "open" : ""}" data-gear="${dev.id}" title="Einstellungen"><ha-icon icon="mdi:cog"></ha-icon></button>` : ""}
            </div>
          </div>
        </div>
        ${open ? this._settings(dev.settings, dev.name, "", dev.id) : ""}
        </div>`;
    }).join("")}</div>`;
  }

  _timeline(d) {
    const plan = this._st(d.ents["sensor:plan"]);
    const hours = (plan?.attributes?.stunden || []).slice();
    if (!hours.length) return `<div class="timeline"><div class="empty">Keine Prognose verfügbar.</div></div>`;
    const now = Date.now();
    // Backend limits display hours to real forecast coverage (up to 72 hours).
    const visible = hours.filter(h => Date.parse(h.zeit) + 3600e3 > now);
    // Do not draw zero-PV hours as full-width columns. Preserve a visible
    // separator for each consecutive gap, including the overnight interval.
    const cols = visible.filter(h => (h.pv_w !== null && Number(h.pv_w) > 0) ||
      Object.values(h.geraete || {}).some(w => Number(w) > 0));
    // Keep overmorgen reachable even when the weather service has no full
    // forecast yet. A placeholder is NOT a guessed zero-production forecast.
    const dayAfter = new Date();
    dayAfter.setHours(12, 0, 0, 0);
    dayAfter.setDate(dayAfter.getDate() + 2);
    const dayAfterKey = dayAfter.toLocaleDateString("sv-SE");
    const dayKey = h => new Date(Date.parse(h.zeit)).toLocaleDateString("sv-SE");
    const completeDayAfter = Array.from({length:8}, (_,i) => i + 8).every(hour =>
      visible.some(h => dayKey(h) === dayAfterKey &&
        new Date(Date.parse(h.zeit)).getHours() === hour &&
        h.prognose_verfuegbar !== false && h.pv_w !== null &&
        Number.isFinite(Number(h.pv_w))));
    if (!cols.some(h => dayKey(h) === dayAfterKey)) {
      cols.push({zeit:dayAfter.toISOString(), _missingDay:!completeDayAfter,
        _dayMarker:true, pv_w:0, frei_w:0, geraete:{}});
    }
    cols.sort((a,b)=>Date.parse(a.zeit)-Date.parse(b.zeit));
    const colorOf = name => name === "Speicher" ? BATTERY_GRADIENT : (d.devices.find(x => x.name === name)?.color || PALETTE[6]);
    const max = Math.max(...cols.map(h => Math.max(h.pv_w || 0, Object.values(h.geraete || {}).reduce((a, b) => a + b, 0))), 1);
    const axisMax = sepNiceAxisMax(max);
    const used = new Set();
    const bars = [];
    const labels = [];
    const step = cols.length > 16 ? 3 : cols.length > 8 ? 2 : 1;
    const dayStarts = [];
    let offsetPx = 0;
    let lastDay = null;
    cols.forEach((h, i) => {
      const t = Date.parse(h.zeit);
      const elapsedHours = i ? Math.round((t - Date.parse(cols[i - 1].zeit)) / 3600e3) : 1;
      if (elapsedHours > 1) {
        const omitted = elapsedHours - 1;
        const from = new Date(Date.parse(cols[i - 1].zeit) + 3600e3);
        const to = new Date(t);
        const tooltip = `${omitted} h ohne PV-Ertrag (${from.toLocaleString("de-AT")} – ${to.toLocaleString("de-AT")})`;
        // A slim transparent separator is enough: day headings already show the new date.
        bars.push(`<div class="pv-break" title="${esc(tooltip)}"></div>`);
        labels.push('<div class="pv-break-label"></div>');
        offsetPx += 14;
      }
      const localDay = new Date(t).toLocaleDateString("sv-SE");
      if (localDay !== lastDay) {
        dayStarts.push({key:localDay,start:offsetPx});
        lastDay = localDay;
      }
      offsetPx += 42;
      if (h._dayMarker) {
        const message = h._missingDay
          ? "Für übermorgen liegt noch keine vollständige Stundenprognose vor."
          : "Für übermorgen ist kein PV-Ertrag prognostiziert.";
        bars.push(`<div class="pv-plan-missing" title="${esc(message)}">${esc(message)}</div>`);
        labels.push('<div class="pv-plan-missing-label">08–16 Uhr</div>');
        offsetPx += 176; // 216 px marker instead of a 40 px hour
        return;
      }
      const isNow = t <= now && now < t + 3600e3;
      const segs = Object.entries(h.geraete || {}).map(([name, w]) => {
        used.add(name);
        const g = colorOf(name);
        return `<div class="seg" title="${esc(name)}: ${fmtW(w)}" style="height:${(w / axisMax) * 100}%;background:linear-gradient(to top,${g.join(",")})"></div>`;
      }).join("");
      const hour = new Date(t).toLocaleTimeString("de-AT", { hour: "2-digit" });
      bars.push(`<div class="col ${isNow ? "now" : ""}" title="${hour} Uhr – PV ${fmtW(h.pv_w)}, frei ${fmtW(h.frei_w)}">
          <div class="pv" style="height:${((h.pv_w || 0) / axisMax) * 100}%"></div>${segs}</div>`);
      labels.push(`<div class="pv-hour-label">${i % step === 0 || elapsedHours > 1 ? new Date(t).getHours() : ""}</div>`);
    });
    const legend = [`<span><i style="background:${grad(PV_GRADIENT)};opacity:.5"></i>PV-Prognose</span>`]
      .concat([...used].map(n => `<span><i style="background:${grad(colorOf(n))}"></i>${esc(n)}</span>`)).join("");
    const next = plan?.state && plan.state !== "–" ? `<div class="next">Als Nächstes: ${esc(plan.state)}</div>` : "";
    const advice = this._st(d.ents["sensor:pv_tipp"]);
    const tips = Array.isArray(advice?.attributes?.tipps) ? advice.attributes.tipps : [];
    const activeTip = tips.length ? tips[((this._pvTipIndex % tips.length) + tips.length) % tips.length] : null;
    const tipOverlay = this._config.show_pv_tips !== false && activeTip ? `
      <div class="pv-tip" aria-label="PV-Alltagstipp">
        ${tips.length > 1 ? '<button type="button" class="pv-tip-nav" data-pvtip="-1" aria-label="Vorheriger Tipp">‹</button>' : ""}
        <div class="pv-tip-content">
          <div class="pv-tip-title"><ha-icon icon="${esc(activeTip.icon || "mdi:lightbulb-outline")}" style="--mdc-icon-size:15px;vertical-align:middle"></ha-icon> ${esc(activeTip.text)}
            ${tips.length > 1 ? `<span class="pv-tip-count">${((this._pvTipIndex % tips.length) + tips.length) % tips.length + 1}/${tips.length}</span>` : ""}</div>
          <div class="pv-tip-detail">${esc(activeTip.detail || "")}</div>
        </div>
        ${tips.length > 1 ? '<button type="button" class="pv-tip-nav" data-pvtip="1" aria-label="Nächster Tipp">›</button>' : ""}
      </div>` : "";
    const dateFmt = key => new Date(key + "T12:00:00").toLocaleDateString("de-AT",
      {weekday:"short",day:"2-digit",month:"2-digit"});
    const headings = dayStarts.map((day,i) => {
      const left = day.start, right = i + 1 < dayStarts.length ? dayStarts[i+1].start : offsetPx;
      return `<div class="pv-plan-day" data-day="${esc(day.key)}" data-start="${left}"
        style="width:${right-left}px">${esc(dateFmt(day.key))}</div>`;
    }).join("");
    const separators = dayStarts.slice(1).map(day =>
      `<div class="pv-compare-day-divider" style="left:${day.start}px" aria-hidden="true"></div>`).join("");
    const horizon = plan?.attributes?.prognose_bis;
    const knownUntil = horizon && Number.isFinite(Date.parse(horizon))
      ? new Date(horizon).toLocaleString("de-AT",{day:"2-digit",month:"2-digit",hour:"2-digit",minute:"2-digit"})
      : "unbekannt";
    const cloudSensor = String(plan?.attributes?.wetter_sensor || "");
    const sourceHint = /8h/i.test(cloudSensor)
      ? " Unter SEP → Konfigurieren → Prognose den Sensor „Meteonomiqs Cloud Forecast 48h“ auswählen."
      : "";
    const coverageNote = !completeDayAfter
      ? `<div class="pv-plan-coverage">Übermorgen, 08–16 Uhr: Stundenprognose unvollständig
         (verfügbar bis ${esc(knownUntil)}).${esc(sourceHint)}</div>` : "";
    return `<div class="timeline">${tipOverlay}<div class="sep-axis-layout">
      <div class="sep-y-axis" aria-label="PV-Leistung in kW" style="margin-top:24px">${sepAxisLabels(axisMax,"kW")}</div>
      <div class="pv-plan-scroll" aria-label="PV-Plan horizontal scrollen">
        <div class="pv-plan-inner" style="min-width:max(100%,${offsetPx}px);position:relative">
          <div class="pv-plan-days">${headings}</div>
          <div class="bars">${SEP_GRID}${bars.join("")}</div>
          <div class="labels">${labels.join("")}</div>
          <div class="pv-compare-day-dividers">${separators}</div>
        </div>
      </div>
      </div><div class="legend">${legend}</div>${coverageNote}</div>${next}`;
  }

  _pvComparison(d) {
    const plan = this._st(d.ents["sensor:plan"]);
    const data = plan?.attributes?.pv_vergleich;
    const open = this._pvCompareOpen;
    const toggle = `<button type="button" class="pv-compare-toggle" data-pvcompare
      aria-expanded="${open ? "true" : "false"}" aria-controls="sep-pv-compare">
      <ha-icon icon="${open ? "mdi:chevron-down" : "mdi:chevron-right"}"></ha-icon>
      PV-Prognose / Ist-Erzeugung (14 Tage) <span>${open ? "Einklappen" : "Ausklappen"}</span>
    </button>`;
    if (!open) return toggle;
    if (!data?.konfiguriert) return toggle + `<div class="pv-compare-body" id="sep-pv-compare">
      <div class="pv-compare-note">Für diesen Vergleich unter SEP → Konfigurieren → Prognose
      den Sensor für die gesamte PV-Erzeugungsleistung (W) auswählen.
      Der Netzsaldo oder die Akkuleistung sind dafür nicht geeignet.</div></div>`;
    const windows = new Map((data.tageslicht || []).map(x => [x.datum, x]));
    const localDay = t => new Date(t).toLocaleDateString("sv-SE",{timeZone:data.zeitzone || undefined});
    const isDaylight = x => {
      const time = Date.parse(x.zeit);
      const daylight = windows.get(localDay(x.zeit));
      if (daylight) {
        const sunrise = Date.parse(daylight.sonnenaufgang);
        const sunset = Date.parse(daylight.sonnenuntergang);
        // Keep complete edge hours and one additional hour around daylight.
        if (Number.isFinite(sunrise) && Number.isFinite(sunset))
          return time + 3600000 > sunrise - 3600000 && time < sunset + 3600000;
      }
      // Compatibility with older SEP backends that do not expose daylight.
      return (Number(x.prognose_wh) || 0) > 0 || (Number(x.ist_wh) || 0) > 0;
    };
    const rows = Array.isArray(data.stunden) ? data.stunden.filter(x =>
      Number.isFinite(Date.parse(x.zeit)) && isDaylight(x)) : [];
    if (!rows.length) return toggle + `<div class="pv-compare-body" id="sep-pv-compare">
      <div class="pv-compare-note">Noch keine Tageslichtstunden mit gespeicherter Prognose verfügbar.
      Der Vergleich beginnt mit der nächsten vollständig gemessenen Stunde.</div></div>`;
    // Strict fixed chart scale: installed STC kWp equals the top kWh tick
    // for a one-hour bucket. No headroom, rounding, or history-based expansion.
    const peakKwp = Number(data.gesamt_peak_kwp);
    const axisMax = Number.isFinite(peakKwp) && peakKwp > 0 ? peakKwp * 1000 : null;
    if (!axisMax) return toggle + `<div class="pv-compare-body" id="sep-pv-compare">
      <div class="pv-compare-note">Für die feste Y-Achse die gesamte installierte PV-Peakleistung
      in SEP → Konfigurieren → Prognose hinterlegen (oder PV-Flächen einzeichnen).</div></div>`;
    const fmt = v => typeof v === "number" && Number.isFinite(v)
      ? v.toLocaleString("de-AT",{minimumFractionDigits:2,maximumFractionDigits:2})+" kWh" : "–";
    const bar = (wh,cls) => wh === null || wh === undefined ? "" :
      `<div class="pv-compare-bar ${cls}" style="height:${Math.max(0,Math.min(100,Number(wh)/axisMax*100))}%"></div>`;
    const classify = value => Math.abs(value) <= 10 ? "good" : Math.abs(value) <= 25 ? "medium" : "bad";
    const signed = pct => (pct > 0 ? "+" : "") + pct.toFixed(1) + " %";
    const deviationOf = x => typeof x.prognose_wh === "number" &&
      typeof x.ist_wh === "number" && x.prognose_wh > 0
      ? (x.ist_wh / x.prognose_wh - 1) * 100 : null;
    const days = [];
    rows.forEach((x,i) => {
      const key = localDay(x.zeit);
      if (!days.length || days[days.length-1].key !== key)
        days.push({key, first:i, count:0, expected:0, actual:0, compared:0, incomplete:0});
      const day=days[days.length-1];day.count++;
      if(typeof x.ist_wh === "number" && typeof x.prognose_wh === "number") {
        day.expected+=x.prognose_wh;day.actual+=x.ist_wh;day.compared++;
      } else day.incomplete++;
    });
    const starts = new Set(days.map(x=>x.first));
    const dayDividers = days.slice(1).map(day =>
      `<span class="pv-compare-day-divider" style="left:${day.first*45-3}px" aria-hidden="true"></span>`).join("");
    const unitWidth = 45;
    const totalWidth = Math.max(580, rows.length*unitWidth);
    const dayHead = days.map(day=>{
      const pct=day.compared && day.expected>0 ? (day.actual/day.expected-1)*100:null;
      const label=new Date(day.key+"T12:00:00").toLocaleDateString("de-AT",{weekday:"short",day:"2-digit",month:"2-digit"});
      return `<div class="pv-compare-day" data-day="${esc(day.key)}" data-expected-wh="${day.expected}"
        data-actual-wh="${day.actual}" data-compared="${day.compared}" data-incomplete="${day.incomplete}"
        data-start="${day.first}" data-count="${day.count}" style="width:${day.count*unitWidth-5}px"
        title="${esc(day.key)} · ${day.compared} verglichene Stunden${day.incomplete ? " · unvollständig" : ""}">
        ${esc(label)} <small class="${pct===null?"":classify(pct)}">${pct===null?"–":esc(signed(pct))}${day.incomplete?" · bisher":""}</small></div>`;
    }).join("");
    const plotted = rows.map((x,i)=>{
      const t=new Date(x.zeit);
      const label=t.toLocaleString("de-AT",{timeZone:data.zeitzone || undefined,weekday:"short",day:"2-digit",month:"2-digit",hour:"2-digit",minute:"2-digit"});
      const forecast=typeof x.prognose_wh==="number"?x.prognose_wh:null;
      const actual=typeof x.ist_wh==="number"?x.ist_wh:null;
      const deviation=deviationOf(x);
      const peak=Math.max(0,forecast || 0,actual || 0);
      const position=(Math.min(peak, axisMax) / axisMax * 100).toFixed(3);
      return `<div class="pv-compare-col ${starts.has(i)?"day-start":""}" title="${esc(label)} · Prognose ${forecast===null?"kein Wert":esc((forecast/1000).toFixed(2))+" kWh"} · Ist ${actual===null?"noch nicht vollständig gemessen":esc((actual/1000).toFixed(2))+" kWh"}">
        ${bar(forecast,"pv-compare-forecast")}${bar(actual,"pv-compare-actual")}
        ${deviation===null?"":`<span class="pv-compare-hour-pct ${classify(deviation)}" style="bottom:calc(${position}% + 8px)" title="${esc(signed(deviation))}">${esc(signed(deviation))}</span>`}</div>`;
    }).join("");
    const labels=rows.map((x,i)=>{
      const local=new Date(x.zeit);
      const time=i%2===0 || starts.has(i) ? local.toLocaleTimeString("de-AT",{timeZone:data.zeitzone || undefined,hour:"2-digit"}) : "";
      return `<span>${esc(time)}</span>`;
    }).join("");
    // Summary is always one local day, never the 14-day aggregate from pv_vergleich.
    // On first expansion default to newest day; a scroll event changes the selected day.
    const initialDay=days.find(x=>x.key===this._pvCompareDay) || days[days.length-1];
    const totalPct=initialDay.compared && initialDay.expected > 0
      ? (initialDay.actual/initialDay.expected-1)*100 : null;
    const partial=initialDay.incomplete > 0 || initialDay.key===localDay(new Date().toISOString());
    const labelDate=new Date(initialDay.key+"T12:00:00").toLocaleDateString("de-AT",
      {weekday:"long",day:"2-digit",month:"2-digit",year:"numeric"});
    return toggle + `<div class="pv-compare-body" id="sep-pv-compare">
      <div class="pv-compare-totals">
        <div class="pv-compare-selected-day" data-pv-selected-date>${esc(labelDate)}${partial?" · bisher":""}</div>
        <div><small>Prognose (vergleichbare Stunden)</small><strong data-pv-day-forecast>${initialDay.compared?fmt(initialDay.expected/1000):"–"}</strong></div>
        <div><small>Ist-Erzeugung (vergleichbar)</small><strong data-pv-day-actual>${initialDay.compared?fmt(initialDay.actual/1000):"–"}</strong></div>
        <div><small>Abweichung (Tag)</small><strong data-pv-day-deviation>${totalPct===null?"–":esc(signed(totalPct))}</strong></div>
      </div>
      <div class="sep-axis-layout">
        <div class="sep-y-axis compare" aria-label="PV-Energie je Stunde in kWh">${sepAxisLabels(axisMax,"kWh")}</div>
        <div class="pv-compare-scroll"><div class="pv-compare-chart-content" style="width:${totalWidth}px;position:relative">
          <div class="pv-compare-days">${dayHead}</div>
          <div class="pv-compare-plot" style="min-width:100%">${SEP_GRID}${plotted}</div>
          <div class="pv-compare-labels" style="min-width:100%">${labels}</div>
          <div class="pv-compare-day-dividers">${dayDividers}</div></div></div>
      </div>
      <div class="pv-compare-legend">
        <span><i style="background:var(--warning-color,#e5a21a)"></i>Ursprüngliche Prognose</span>
        <span><i style="background:var(--success-color,#22a06b)"></i>Gemessene Erzeugung</span>
      </div>
      <div class="pv-compare-note">Die Werte oben gelten nur für den ausgewählten Tag.
      Beim Wischen folgt die Tagesauswertung dem sichtbaren Datum. Nur Stunden mit gültigem
      Ist-Wert und ursprünglicher Prognose werden verglichen. Fehlende Messzeiten bleiben
      offen; die Prognose wird rückwirkend nicht überschrieben.</div>
    </div>`;
  }

  // ── Render ────────────────────────────────────────────────────────────────
  _render() {
    if (!this._hass) return;
    const c = this._config;
    const transparency = Math.max(0, Math.min(100, Number(c.background_transparency) || 0));
    const surfaceOpacity = 100 - transparency;
    const d = this._data ?? collect(this._hass, c.hub);
    if (!d) {
      this.shadowRoot.innerHTML = `<style>${CARD_CSS}</style><ha-card style="--sep-surface-opacity:${surfaceOpacity}%"><div class="empty">Kein smartify Energiemanager gefunden.</div></ha-card>`;
      return;
    }
    const title = c.title ?? d.name;
    // The PV timeline and its 14-day forecast/actual comparison move together.
    // The editor persists pv_plan_first to the Lovelace card configuration.
    const pvFirst = this._pvPlanFirstOverride ?? c.pv_plan_first;
    const priorityBlock = c.show_priorities ? `<div class="sep-order-block" data-order-block="priorities">
       <div class="section priority-section">
         <span class="priority-heading">
           <button type="button" class="section-move-grip" data-section-grip="priorities"
             aria-label="Prioritäten-Abschnitt verschieben" title="Abschnitt verschieben">
             <ha-icon icon="mdi:drag-vertical"></ha-icon>
           </button>
           <button type="button" class="priority-lock ${this._priorityLocked ? "locked" : "unlocked"}"
             data-priority-lock aria-label="${this._priorityLocked ? "Prioritäten entsperren" : "Prioritäten sperren"}"
             aria-pressed="${!this._priorityLocked}" title="${this._priorityLocked ? "Zum Sortieren entsperren" : "Sortierung wieder sperren"}"
             ${this._prioritySaving ? "disabled" : ""}>
             <ha-icon icon="${this._priorityLocked ? "mdi:lock" : "mdi:lock-open-variant"}"></ha-icon>
           </button>Prioritäten</span>
         <span class="priority-hint">${this._priorityLocked ? "Sortierung gesperrt" : "Ziehen zum Sortieren"}</span>
       </div>${this._devices(d)}</div>` : "";
    const pvBlock = c.show_timeline ? `<div class="sep-order-block" data-order-block="pv">
      <div class="section"><span class="priority-heading">
        <button type="button" class="section-move-grip" data-section-grip="pv"
          aria-label="PV-Plan-Abschnitt verschieben" title="PV-Plan und Prognose-Ist-Vergleich verschieben">
          <ha-icon icon="mdi:drag-vertical"></ha-icon>
        </button>PV-Plan</span>
        <span>Zukunft scrollen${this._st(d.ents["sensor:forecast_today"])?.attributes?.prognose_quelle ?
          ` · ${esc(this._st(d.ents["sensor:forecast_today"]).attributes.prognose_quelle)}` : ""}</span>
      </div>${this._timeline(d)}${this._pvComparison(d)}</div>` : "";
    const orderedBlocks = pvFirst ? pvBlock + priorityBlock : priorityBlock + pvBlock;
    const markup = `
      <style>${CARD_CSS}</style>
      <ha-card style="--sep-surface-opacity:${surfaceOpacity}%">
        ${title || d.ents["select:mode"] ? `<div class="title"><img class="sep-brand-icon" src="/smartify_energy/sep-logo.png" alt="Smartify Energy Pro Logo"><span>Smartify Energy Pro</span><span class="sp"></span>${this._modeSelect(d.ents["select:mode"])}
          ${c.show_settings !== false && d.hubSettings.length ? `<button class="gear ${this._open.has("hub") ? "open" : ""}" data-gear="hub" title="Einstellungen Energiemanager"><ha-icon icon="mdi:cog"></ha-icon></button>` : ""}</div>` : ""}
        ${this._open.has("hub") ? this._settings(d.hubSettings, d.name, "hub", "hub") : ""}
        ${c.show_header ? this._header(d) : ""}
        ${orderedBlocks}
      </ha-card>`;
    const template = document.createElement("template");
    template.innerHTML = markup;
    patchChildren(this.shadowRoot, template.content);
    this._bind(d);
    if (this._pvCompareOpen) this._updatePVSelectedDay();
  }

  _updatePVSelectedDay(scroll=this.shadowRoot.querySelector(".pv-compare-scroll")) {
    if (!scroll) return;
    const heads=[...scroll.querySelectorAll(".pv-compare-day[data-day]")];
    if (!heads.length) return;
    // Each hourly column occupies 45px. Choose the day at the viewport centre.
    // Using data-start/count also works before layout sizes are available in jsdom.
    const centre=scroll.scrollLeft+(scroll.clientWidth || scroll.offsetWidth || 0)/2;
    const chosen=heads.find(h=>centre >= Number(h.dataset.start)*45 &&
      centre < (Number(h.dataset.start)+Number(h.dataset.count))*45) ||
      (centre < Number(heads[0].dataset.start)*45 ? heads[0] : heads[heads.length-1]);
    if (!chosen) return;
    const key=chosen.dataset.day;
    this._pvCompareDay=key;
    const expected=Number(chosen.dataset.expectedWh);
    const actual=Number(chosen.dataset.actualWh);
    const compared=Number(chosen.dataset.compared);
    const incomplete=Number(chosen.dataset.incomplete);
    const timeZone=this._st(this._boundData?.ents["sensor:plan"])?.attributes?.pv_vergleich?.zeitzone;
    const today=new Date().toLocaleDateString("sv-SE",{timeZone:timeZone || undefined});
    const partial=incomplete>0 || key===today;
    const date=new Date(key+"T12:00:00").toLocaleDateString("de-AT",
      {weekday:"long",day:"2-digit",month:"2-digit",year:"numeric"});
    const format=v=>v.toLocaleString("de-AT",
      {minimumFractionDigits:2,maximumFractionDigits:2})+" kWh";
    const forecast=this.shadowRoot.querySelector("[data-pv-day-forecast]");
    const actualEl=this.shadowRoot.querySelector("[data-pv-day-actual]");
    const deviation=this.shadowRoot.querySelector("[data-pv-day-deviation]");
    const heading=this.shadowRoot.querySelector("[data-pv-selected-date]");
    if (heading) heading.textContent=date+(partial?" · bisher":"");
    if (forecast) forecast.textContent=compared?format(expected/1000):"–";
    if (actualEl) actualEl.textContent=compared?format(actual/1000):"–";
    if (deviation) deviation.textContent=compared && expected>0
      ? (actual>expected?"+":"")+((actual/expected-1)*100).toFixed(1)+" %" : "–";
  }

  _bind(d) {
    this._boundData = d;
    if (this._eventsBound) return;
    this._eventsBound = true;
    const root = this.shadowRoot;
    root.addEventListener("click", e => {
      const el = e.target.closest?.("[data-priority-lock], [data-pvtip], [data-pvcompare], [data-log], [data-gear], [data-more], [data-press], [data-toggle], [data-info], [data-grp], [data-setmode], select");
      if (!el) return;
      if (el.matches("select")) { e.stopPropagation(); return; }
      if (el.hasAttribute("data-priority-lock")) {
        e.stopPropagation();
        if (this._prioritySaving || this._drag) return;
        this._priorityLocked = !this._priorityLocked;
        this._render();
      } else if (el.hasAttribute("data-pvtip")) {
        e.stopPropagation();
        const tips = this._st(d.ents["sensor:pv_tipp"])?.attributes?.tipps || [];
        if (tips.length > 1) {
          this._pvTipIndex = (this._pvTipIndex + Number(el.dataset.pvtip) + tips.length) % tips.length;
          this._render();
        }
      } else if (el.hasAttribute("data-pvcompare")) {
        e.stopPropagation();
        this._pvCompareOpen = !this._pvCompareOpen;
        this._render();
        if (this._pvCompareOpen) {
          const scroll = this.shadowRoot.querySelector(".pv-compare-scroll");
          if (scroll) {
            scroll.scrollLeft = scroll.scrollWidth;
            this._updatePVSelectedDay(scroll);
          }
        }
      } else if (el.hasAttribute("data-log")) {
        e.stopPropagation();
        const id = el.dataset.log;
        this._logOpen.has(id) ? this._logOpen.delete(id) : this._logOpen.add(id);
        this._render();
      } else if (el.dataset.gear) {
        e.stopPropagation();
        const id = el.dataset.gear;
        this._open.has(id) ? this._open.delete(id) : this._open.add(id);
        // A focused select may have blocked incoming HA updates. The cached
        // data/signature must be discarded on menu transitions, especially
        // on close, even when no new HA event arrives afterward.
        this._pendingBlur = false;
        this._sig = "";
        this._data = collect(this._hass, this._config.hub);
        this._render();
      } else if (el.dataset.setmode) {
        e.stopPropagation();
        this._hass.callService("select", "select_option", {entity_id: el.dataset.setmode, option: el.dataset.opt});
      } else if (el.dataset.info) {
        e.stopPropagation(); e.preventDefault();
        const k = el.dataset.info;
        this._infoOpen.has(k) ? this._infoOpen.delete(k) : this._infoOpen.add(k);
        this._render();
      } else if (el.dataset.grp) {
        e.stopPropagation();
        const k = el.dataset.grp;
        const set = el.dataset.collapsed === "1" ? this._grpOpen : this._grpClosed;
        set.has(k) ? set.delete(k) : set.add(k);
        this._render();
      } else if (el.dataset.toggle) {
        e.stopPropagation();
        this._hass.callService("switch", "toggle", {entity_id: el.dataset.toggle});
      } else if (el.dataset.press) {
        e.stopPropagation();
        this._hass.callService("button", "press", {entity_id: el.dataset.press});
      } else this._moreInfo(el.dataset.more);
    });
    root.addEventListener("scroll", e=>{
      if (e.target?.classList?.contains("pv-compare-scroll")) this._updatePVSelectedDay(e.target);
    }, true);
    root.addEventListener("change", e => {
      const el = e.target;
      if (el.dataset.select) this._hass.callService(el.dataset.select.split(".")[0], "select_option", {entity_id: el.dataset.select, option: el.value});
      else if (el.dataset.num && Number.isFinite(parseFloat(el.value))) this._hass.callService("number", "set_value", {entity_id: el.dataset.num, value: parseFloat(el.value)});
      else if (el.dataset.switch) this._hass.callService("switch", el.checked ? "turn_on" : "turn_off", {entity_id: el.dataset.switch});
      else if (el.dataset.time && el.value) this._hass.callService("time", "set_value", {entity_id: el.dataset.time, time: `${el.value}:00`});
    });
    root.addEventListener("pointerdown", e => {
      if (e.target.closest?.("[data-section-grip]")) this._sectionDragStart(e);
      else if (!this._priorityLocked && e.target.closest?.(".handle")) this._dragStart(e, this._boundData);
    });
  }

  _sectionDragStart(e) {
    if (!this._config.show_priorities || !this._config.show_timeline || this._drag || this._sectionMove) return;
    const grip = e.target.closest("[data-section-grip]");
    const block = grip?.closest("[data-order-block]");
    if (!grip || !block) return;
    const from = grip.dataset.sectionGrip;
    const startY = e.clientY;
    const isFirst = this._pvPlanFirstOverride ?? this._config.pv_plan_first;
    this._sectionMove = { grip, block, from, startY };
    e.preventDefault();
    grip.setPointerCapture?.(e.pointerId);
    const move = ev => {
      if (Math.abs(ev.clientY - startY) > 8) block.classList.add("section-moving");
    };
    const finish = ev => {
      grip.removeEventListener("pointermove", move);
      grip.removeEventListener("pointerup", finish);
      grip.removeEventListener("pointercancel", finish);
      block.classList.remove("section-moving");
      this._sectionMove = null;
      if (ev.type === "pointercancel") return;
      const dy = ev.clientY - startY;
      if (Math.abs(dy) < 40) return;
      // Drag PV above priorities, or priorities below PV. Reverse works too.
      const next = from === "pv" ? dy < 0 : dy > 0;
      if (next !== isFirst) this._changeSectionOrder(next);
    };
    grip.addEventListener("pointermove", move);
    grip.addEventListener("pointerup", finish);
    grip.addEventListener("pointercancel", finish);
  }

  // ── Drag & Drop (Maus + Touch, ohne externe Bibliothek) ──────────────────
  _dragStart(e, d) {
    const row = e.target.closest(".dev-wrap");
    const list = row?.parentElement;
    if (!row || !list || this._priorityLocked || this._prioritySaving) return;
    e.preventDefault();
    const rows = [...list.querySelectorAll(":scope > .dev-wrap")];
    const rects = rows.map(r => r.getBoundingClientRect());
    const from = rows.indexOf(row);
    const step = rows.length > 1 ? Math.min(...rects.slice(1).map((r, i) => r.top - rects[i].top)) : rects[0].height + 4;
    this._drag = { row, rows, rects, from, to: from, startY: e.clientY, step, d };
    row.classList.add("dragging");
    row.setPointerCapture?.(e.pointerId);
    const move = ev => this._dragMove(ev);
    const end = ev => {
      row.removeEventListener("pointermove", move);
      row.removeEventListener("pointerup", end);
      row.removeEventListener("pointercancel", end);
      this._dragEnd(ev.type === "pointercancel");
    };
    row.addEventListener("pointermove", move);
    row.addEventListener("pointerup", end);
    row.addEventListener("pointercancel", end);
  }

  _dragMove(e) {
    const g = this._drag;
    if (!g || this._priorityLocked) return;
    const dy = e.clientY - g.startY;
    g.row.style.transform = `translateY(${dy}px)`;
    const to = Math.max(0, Math.min(g.rows.length - 1, g.from + Math.round(dy / g.step)));
    g.to = to;
    g.rows.forEach((r, i) => {
      if (r === g.row) return;
      let shift = 0;
      if (g.from < to && i > g.from && i <= to) shift = -g.step;
      if (g.from > to && i < g.from && i >= to) shift = g.step;
      r.style.transform = shift ? `translateY(${shift}px)` : "";
    });
  }

  async _dragEnd(cancelled = false) {
    const g = this._drag;
    if (!g) return;
    const order = g.rows.map(r => r.dataset.wrap);
    const [moved] = order.splice(g.from, 1);
    order.splice(g.to, 0, moved);
    g.rows.forEach(r => { r.style.transform = ""; r.classList.remove("dragging"); });
    this._drag = null;
    if (cancelled || this._priorityLocked || g.to === g.from) return;
    this._priorityOrder = order;
    this._prioritySaving = true;
    this._priorityError = "";
    this._sig = "";
    this.hass = this._hass; // Sort immediately, before the network request.
    try {
      await this._hass.callService(DOMAIN, "set_priority_order", { device_ids: order });
    } catch (err) {
      this._priorityOrder = null; // Roll back to authoritative HA ordering.
      this._priorityError = String(err?.message || err || "Unbekannter Fehler");
      // Show an explicit error; never leave a silently unsaved arrangement.
      this.dispatchEvent(new CustomEvent("hass-notification", {
        bubbles: true, composed: true,
        detail: { message: "SEP: Prioritäten konnten nicht gespeichert werden: " + this._priorityError },
      }));
    } finally {
      this._prioritySaving = false;
      this._sig = "";
      this.hass = this._hass;
    }
  }
}

if (!customElements.get("smartify-energy-plan-card")) customElements.define("smartify-energy-plan-card", SmartifyEnergyPlanCard);

/* ═══════════════════════════════════════════════════════════════════════════
 * smartify-energy-pv-card – PV-Flächen auf dem Luftbild einzeichnen
 *
 *   type: custom:smartify-energy-pv-card
 *   title: PV-Flächen            # optional
 *   entry_id: <config entry>     # nur bei mehreren Energiemanagern
 *
 * Luftbild: basemap.at (Österreich). Es wird nur beim ersten Öffnen bzw. über
 * „Luftbild neu laden“ heruntergeladen und in Home Assistant gespeichert.
 * Ausrichtung = Außenseite der markierten Traufkante (Fläche) bzw. Normale der
 * Linie (Fassade). Neigung und Leistung werden eingegeben.
 * ═══════════════════════════════════════════════════════════════════════════ */
const PV_TILE = 256;
const pvWorld = z => PV_TILE * 2 ** z;
const pvLon2x = (lon, z) => (lon + 180) / 360 * pvWorld(z);
const pvLat2y = (lat, z) => { const r = lat * Math.PI / 180; return (1 - Math.log(Math.tan(r) + 1 / Math.cos(r)) / Math.PI) / 2 * pvWorld(z); };
const pvX2lon = (x, z) => x / pvWorld(z) * 360 - 180;
const pvY2lat = (y, z) => { const n = Math.PI - 2 * Math.PI * y / pvWorld(z); return 180 / Math.PI * Math.atan(0.5 * (Math.exp(n) - Math.exp(-n))); };
const pvAz = (e, n) => Math.round(((Math.atan2(e, n) * 180 / Math.PI) + 360) % 360 * 10) / 10;
const PV_DIRS = ["N", "NNO", "NO", "ONO", "O", "OSO", "SO", "SSO", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"];
const pvDir = a => PV_DIRS[Math.round((((a % 360) + 360) % 360) / 22.5) % 16];

/** Ausrichtung aus der Zeichnung (gleiches Verfahren wie pv_layout.py, in Pixelkoordinaten: Ost = +x, Nord = −y). */
function pvSurfaceAzimuth(s, z) {
  if (s.kind === "manual" || !Array.isArray(s.points)) return Number(s.azimuth) || 0;
  const xy = s.points.map(([lat, lon]) => [pvLon2x(lon, z), pvLat2y(lat, z)]);
  const normals = i => {
    const [x1, y1] = xy[i], [x2, y2] = xy[(i + 1) % xy.length];
    const e = x2 - x1, n = -(y2 - y1);
    return [[n, -e], [-n, e]];
  };
  if (s.kind === "line") {
    if (xy.length !== 2) return Number(s.azimuth) || 0;
    const [n1, n2] = normals(0), a1 = pvAz(...n1), a2 = pvAz(...n2);
    const [first, second] = Math.abs(a1 - 180) <= Math.abs(a2 - 180) ? [a1, a2] : [a2, a1];
    return s.flip ? second : first;
  }
  if (xy.length < 3) return Number(s.azimuth) || 0;
  const edge = Number.isInteger(s.edge) && s.edge >= 0 && s.edge < xy.length ? s.edge : 0;
  const cx = xy.reduce((a, p) => a + p[0], 0) / xy.length, cy = xy.reduce((a, p) => a + p[1], 0) / xy.length;
  const [x1, y1] = xy[edge], [x2, y2] = xy[(edge + 1) % xy.length];
  const me = (x1 + x2) / 2 - cx, mn = -((y1 + y2) / 2 - cy);
  const [n1, n2] = normals(edge);
  let out = n1[0] * me + n1[1] * mn >= 0 ? n1 : n2;
  if (s.flip) out = [-out[0], -out[1]];
  return pvAz(...out);
}

/** Längste Kanten zuerst, davon die am ehesten nach Süden zeigende (wie default_edge in Python). */
function pvDefaultEdge(points, z) {
  const xy = points.map(([lat, lon]) => [pvLon2x(lon, z), pvLat2y(lat, z)]);
  const len = xy.map((p, i) => Math.hypot(xy[(i + 1) % xy.length][0] - p[0], xy[(i + 1) % xy.length][1] - p[1]));
  const max = Math.max(...len);
  let best = 0, bestDiff = Infinity;
  len.forEach((l, i) => {
    if (l < 0.5 * max) return;
    const d = Math.abs(pvSurfaceAzimuth({ kind: "area", points, edge: i }, z) - 180);
    if (d < bestDiff) { best = i; bestDiff = d; }
  });
  return best;
}

/** Projizierte Fläche in m² (Web-Mercator-Pixel → Meter am Breitengrad). */
function pvAreaM2(points, z) {
  if (!Array.isArray(points) || points.length < 3) return null;
  const mpp = 156543.03392 * Math.cos(points[0][0] * Math.PI / 180) / 2 ** z;
  const xy = points.map(([lat, lon]) => [pvLon2x(lon, z), pvLat2y(lat, z)]);
  let s = 0;
  xy.forEach(([x1, y1], i) => { const [x2, y2] = xy[(i + 1) % xy.length]; s += x1 * y2 - x2 * y1; });
  return Math.round(Math.abs(s) / 2 * mpp * mpp * 10) / 10;
}

const pvKwp = s => s.input === "modules" ? (Number(s.modules) || 0) * (Number(s.module_wp) || 0) / 1000 : Number(s.kwp) || 0;
const pvFmt = (v, d = 2) => Number(v).toLocaleString("de-AT", { maximumFractionDigits: d, minimumFractionDigits: 0 });
const PV_COLORS = ["#FFB300", "#29B6F6", "#66BB6A", "#EC407A"];

const PV_CSS = `
  :host { display:block; }
  ha-card { padding:14px; color:var(--primary-text-color); container-type:inline-size; }
  .layout { display:block; }
  @container (min-width: 860px) {
    .layout { display:grid; grid-template-columns:minmax(0,1fr) minmax(300px,380px); gap:14px; align-items:start; }
    .side { max-height:calc(min(62vh,520px) + 90px); overflow:auto; padding-right:2px; }
    .side .surf:first-child { margin-top:0; }
  }
  .s-head .tog { font:inherit; border:0; background:none; color:inherit; cursor:pointer; padding:2px 4px; font-size:16px; min-height:30px;
    transition:transform .15s; }
  .s-head .tog[aria-expanded="true"] { transform:rotate(90deg); }
  .s-head .nm { flex:1 1 120px; font-weight:700; cursor:pointer; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .chk { display:flex; align-items:center; gap:6px; min-height:34px; font-size:14px; color:var(--primary-text-color); }
  .chk input { width:auto; min-height:0; }
  .hd { display:flex; align-items:center; gap:8px; flex-wrap:wrap; margin-bottom:10px; }
  .hd h2 { margin:0; font-size:1.1em; font-weight:700; flex:1 1 auto; }
  .chip { font-size:12px; padding:2px 8px; border-radius:10px; background:var(--secondary-background-color); }
  .chip.warn { background:var(--warning-color,#ff9800); color:#111; }
  .map { position:relative; border-radius:8px; overflow:hidden; background:#30363b; }
  svg { display:block; width:100%; height:min(62vh,520px); touch-action:none; user-select:none; cursor:grab; }
  svg.drawing { cursor:crosshair; }
  .tools { position:absolute; right:8px; top:8px; display:flex; flex-direction:column; gap:6px; }
  .tools button, .bar button, .s-actions button { font:inherit; font-size:13px; min-height:34px; padding:6px 10px; border-radius:8px; cursor:pointer;
    border:1px solid var(--divider-color); background:var(--card-background-color); color:var(--primary-text-color); }
  .tools button { width:36px; padding:0; font-size:18px; font-weight:700; }
  .address-row {display:flex;align-items:center;gap:6px;margin:8px 0;flex-wrap:wrap}
  .address-row input { flex:1 1 200px;width:auto;min-width:140px; }
  .address-row button { flex:0 0 auto }
  .address-hint {font-size:11px;color:var(--secondary-text-color);margin:0 0 6px}
  .address-results {display:grid;gap:2px;margin:-4px 0 8px;max-height:220px;overflow-y:auto}
  .address-results:empty {display:none}
  .address-results button {font:inherit;font-size:13px;text-align:left;min-height:34px;padding:7px 10px;
    border:1px solid var(--divider-color);border-radius:6px;background:var(--card-background-color);
    color:var(--primary-text-color);cursor:pointer;overflow-wrap:anywhere}
  .address-results button:hover,.address-results button:focus-visible {background:var(--secondary-background-color)}
  button.primary { background:var(--primary-color); color:var(--text-primary-color,#fff); border-color:var(--primary-color); }
  button:disabled { opacity:.5; cursor:default; }
  .attr { position:absolute; left:6px; bottom:4px; font-size:10px; color:#fff; text-shadow:0 0 3px #000; pointer-events:none; }
  .drawhint { position:absolute; left:8px; top:8px; right:56px; font-size:12px; padding:6px 8px; border-radius:6px; background:rgba(0,0,0,.65); color:#fff; }
  .bar { display:flex; flex-wrap:wrap; gap:6px; align-items:center; margin:10px 0; }
  .bar .sp { flex:1 1 auto; }
  .msg { font-size:13px; margin:6px 0; }
  .msg.err { color:var(--error-color,#db4437); }
  .msg.ok { color:var(--success-color,#43a047); }
  .surf { border:1px solid var(--divider-color); border-left:5px solid var(--c); border-radius:8px; padding:10px; margin-top:8px; }
  .surf.sel { box-shadow:0 0 0 2px var(--c) inset; }
  .s-head { display:flex; gap:8px; align-items:center; flex-wrap:wrap; }
  .s-head input.name { flex:1 1 140px; font-weight:700; }
  .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(130px,1fr)); gap:8px; margin-top:8px; }
  label { display:block; font-size:12px; color:var(--secondary-text-color); margin-bottom:2px; }
  input, select { font:inherit; font-size:14px; width:100%; box-sizing:border-box; min-height:34px; padding:4px 6px; border-radius:6px;
    border:1px solid var(--divider-color); background:var(--secondary-background-color); color:var(--primary-text-color); }
  .val { font-size:15px; font-weight:700; min-height:34px; display:flex; align-items:center; gap:6px; }
  .val small { font-weight:400; color:var(--secondary-text-color); }
  .s-actions { display:flex; flex-wrap:wrap; gap:6px; margin-top:8px; }
  .hint { font-size:12px; color:var(--secondary-text-color); margin-top:4px; }
`;

class SmartifyEnergyPvCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this._data = null;        // Antwort von smartify_energy/pv_layout
    this._surfaces = [];      // Arbeitskopie
    this._dirty = false;
    this._sel = null;
    this._draw = null;        // {id, kind, points:[]}
    this._view = null;        // viewBox in Weltpixeln
    this._busy = "";
    this._msg = null;         // {type:'ok'|'err', text}
    this._autoMap = false;
    this._loading = false;
    this._open = new Set();   // aufgeklappte Flächen in der Liste
    this._tileUrls = [];      // Blob-URLs der gespeicherten Kacheln (nicht bei jedem Zeichnen neu einbetten)
    this._refreshTimer = null; // Debounced tile refresh after zoom / pan end.
    this._address = "";
    this._suggestions = [];
    this._suggestTimer = null;
    this._suggestRequest = 0;
    this._mapSource = "home";  // Persist explicit address selection via map metadata.
  }

  _setMap(map) {
    this._tileUrls.forEach(t => URL.revokeObjectURL(t.url));
    this._tileUrls = [];
    if (this._data) this._data.map = map || null;
    for (const t of map?.tiles || []) {
      try {
        const bin = atob(t.data), bytes = new Uint8Array(bin.length);
        for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
        this._tileUrls.push({ x: t.x, y: t.y, url: URL.createObjectURL(new Blob([bytes], { type: "image/jpeg" })) });
      } catch (err) { console.warn("smartify-energy-pv-card: Kachel defekt", err); }
    }
  }

  static getStubConfig() { return { title: "PV-Flächen" }; }
  setConfig(config) { this._config = { ...(config || {}) }; if (this._hass) this._render(); }
  getCardSize() { return 12; }
  getGridOptions() { return { columns: 12, rows: "auto" }; }

  set hass(hass) {
    // Darf nie werfen (sonst ersetzt HA die Karte durch „Konfigurationsfehler“).
    try {
      const first = !this._hass;
      this._hass = hass;
      if (first) { this._render(); this._load(); }
    } catch (err) { console.error("smartify-energy-pv-card", err); }
  }

  get _admin() { return !!this._hass?.user?.is_admin; }
  // SVG rechnet in float32: absolute Web-Mercator-Pixel (~7·10⁷ bei Zoom 19) verlieren
  // Genauigkeit und Kacheln verschwinden. Darum relativ zu einem Ursprung zeichnen.
  _lx(lon) { return pvLon2x(lon, this._zoom) - (this._origin?.x || 0); }
  _ly(lat) { return pvLat2y(lat, this._zoom) - (this._origin?.y || 0); }
  _lon(lx) { return pvX2lon(lx + (this._origin?.x || 0), this._zoom); }
  _lat(ly) { return pvY2lat(ly + (this._origin?.y || 0), this._zoom); }
  get _zoom() { return this._data?.map?.zoom ?? this._data?.zoom?.default ?? 19; }

  async _ws(msg) {
    const extra = this._config.entry_id ? { entry_id: this._config.entry_id } : {};
    return this._hass.callWS({ ...msg, ...extra });
  }

  async _load() {
    if (this._loading) return;
    this._loading = true;
    try {
      this._data = await this._ws({ type: `${DOMAIN}/pv_layout` });
      this._mapSource = ["address","browse"].includes(this._data.map?.source) ? this._data.map.source : "home";
      this._setMap(this._data.map);
      this._surfaces = JSON.parse(JSON.stringify(this._data.surfaces || []));
      this._dirty = false;
      this._resetView();
      // Migrate already-saved default labels (e.g. 3/4 -> 1/2) once on load.
      // Keep IDs, geometry, user-defined names and every other field untouched.
      if (this._admin && this._renumberDefaultSurfaces()) {
        this._dirty = true;
        await this._save();  // persist through the existing validated WebSocket path
      }
      const old = this._data.map;
      const home = this._data.home;
      const mismatched = old && home && !["address","browse"].includes(old.source) &&
        (Math.abs(Number(old.lat)-Number(home.lat)) > 0.002 ||
         Math.abs(Number(old.lon)-Number(home.lon)) > 0.002);
      if ((!old || mismatched) && this._admin && !this._autoMap) {
        this._autoMap = true;   // nur einmal automatisch, danach nur per Knopf
        this._render();
        await this._reloadMap(true, {lat:home.lat, lon:home.lon,
          zoom:this._data.zoom.default, source:"home"});
      }
    } catch (err) {
      this._msg = { type: "err", text: `PV-Flächen konnten nicht geladen werden: ${err?.message || err}` };
    } finally {
      this._loading = false;
      this._render();
    }
  }

  async _reloadMap(auto = false, target = null) {
    if (!this._admin || this._busy) return;
    if (!auto && this._data?.map && !confirm("Luftbild für den aktuellen Kartenmittelpunkt neu herunterladen?")) return;
    const v = this._view;
    const center = target || (v ? {lat:this._lat(v.y+v.h/2),lon:this._lon(v.x+v.w/2)} : this._data?.home);
    if (!center) return;
    this._busy = "map";
    this._msg = {type:"ok",text:"Luftbild wird von basemap.at geladen …"};
    this._render();
    try {
      const response = await this._ws({type:`${DOMAIN}/pv_map/reload`,
        lat:center.lat,lon:center.lon,zoom:target?.zoom ?? this._zoom,
        source:target?.source ?? this._mapSource});
      this._setMap(response.map);
      this._mapSource = response.map.source;
      this._resetView();
      this._msg = null;
    } catch (err) {
      this._msg = {type:"err",text:`Luftbild konnte nicht geladen werden: ${err?.message || err}`};
    } finally {
      this._busy = "";
      this._render();
    }
  }

  _renumberDefaultSurfaces() {
    let changed = false;
    this._surfaces.forEach((s, i) => {
      const name = `Fläche ${i + 1}`;
      if (/^Fläche [0-9]+$/.test(s.name || "") && s.name !== name) {
        s.name = name;
        changed = true;
      }
    });
    return changed;
  }

  _showAddressSuggestions() {
    const list = this.shadowRoot?.querySelector("[data-address-results]");
    if (!list) return;
    list.innerHTML = this._suggestions.map((s, i) =>
      `<button type="button" data-suggest="${i}">${esc(s.display_name)}</button>`).join("");
    list.querySelectorAll("[data-suggest]").forEach(button =>
      button.addEventListener("click", () => this._chooseAddress(Number(button.dataset.suggest))));
  }

  _queueSuggestions() {
    clearTimeout(this._suggestTimer);
    const seq = ++this._suggestRequest;
    this._suggestions = [];
    this._showAddressSuggestions();
    const query = this._address.trim();
    if (!this._admin || query.length < 3) return;
    this._suggestTimer = setTimeout(async () => {
      if (seq !== this._suggestRequest || this._busy) return;
      try {
        const res = await this._ws({type:`${DOMAIN}/pv_map/suggest`,query});
        if (seq !== this._suggestRequest || this._address.trim() !== query) return;
        this._suggestions = Array.isArray(res?.results) ? res.results : [];
        this._showAddressSuggestions();
      } catch (err) {
        if (seq === this._suggestRequest) { this._suggestions = []; this._showAddressSuggestions(); }
      }
    }, 700);
  }

  async _chooseAddress(index) {
    const found = this._suggestions[index];
    if (!found || this._busy) return;
    clearTimeout(this._suggestTimer);
    ++this._suggestRequest;
    this._address = found.display_name;
    this._suggestions = [];
    await this._reloadMap(true, {lat:found.lat,lon:found.lon,
      zoom:this._data?.zoom?.default ?? 19,source:"address"});
    if (!this._msg || this._msg.type !== "err")
      this._setMsg("ok", `Adresse gefunden: ${found.display_name}`);
    this._render();
  }

  async _searchAddress() {
    if (!this._admin || this._busy) return;
    clearTimeout(this._suggestTimer);
    ++this._suggestRequest;
    this._suggestions = [];
    const address = this._address.trim();
    if (address.length < 4) {
      this._msg = {type:"err",text:"Bitte Straße, Hausnummer und Ort angeben."};
      this._render(); return;
    }
    this._busy = "geocode";
    this._msg = {type:"ok",text:"Adresse wird gesucht …"};
    this._render();
    try {
      const found = await this._ws({type:`${DOMAIN}/pv_map/geocode`,address});
      this._busy = "";
      // The lookup is performed only on explicit button press. Download imagery
      // for that result without modifying or deleting any PV surface.
      await this._reloadMap(true, {lat:found.lat,lon:found.lon,
        zoom:this._data?.zoom?.default ?? 19,source:"address"});
      if (!this._msg || this._msg.type !== "err")
        this._msg = {type:"ok",text:`Adresse gefunden: ${found.display_name}`};
    } catch (err) {
      this._msg = {type:"err",text:`Adresse nicht gefunden: ${err?.message || err}`};
    } finally {
      this._busy = "";
      this._render();
    }
  }

  _scheduleMapRefresh() {
    if (this._refreshTimer) clearTimeout(this._refreshTimer);
    this._refreshTimer = setTimeout(() => {
      this._refreshTimer = null;
      this._maybeRefreshMap();
    }, 550);
  }

  _maybeRefreshMap() {
    if (!this._admin || this._busy || !this._view || !this._data?.map || this._draw) return;
    const v=this._view, z=this._zoom;
    const minZoom=this._data?.zoom?.min ?? 17, maxZoom=this._data?.zoom?.max ?? 20;
    // One level up/down when the visible world width crosses the image-native
    // scale threshold. Browser zooming remains smooth between tile levels.
    const requestedZoom = v.w < 360 && z < maxZoom ? z+1
      : v.w > 1250 && z > minZoom ? z-1 : z;
    const bounds=v.bounds;
    const margin=90;
    const outside = bounds &&
      (v.x < bounds.x0+margin || v.y < bounds.y0+margin ||
       v.x+v.w > bounds.x0+bounds.w-margin ||
       v.y+v.h > bounds.y0+bounds.h-margin);
    if (requestedZoom===z && !outside) return;
    const center={lat:this._lat(v.y+v.h/2),lon:this._lon(v.x+v.w/2)};
    this._reloadMap(true,{...center,zoom:requestedZoom,source:outside ? "browse" : this._mapSource});
  }

  _goHome() {
    const home=this._data?.home;
    if (!home || !this._admin) return;
    this._mapSource="home";
    this._reloadMap(true,{lat:home.lat,lon:home.lon,
      zoom:this._data?.zoom?.default ?? 19,source:"home"});
  }

  _resetView() {
    const z = this._zoom, m = this._data?.map;
    if (m?.tiles?.length) {
      const xs = m.tiles.map(t => t.x), ys = m.tiles.map(t => t.y);
      const x0 = Math.min(...xs) * PV_TILE, y0 = Math.min(...ys) * PV_TILE;
      const w = (Math.max(...xs) + 1) * PV_TILE - x0, h = (Math.max(...ys) + 1) * PV_TILE - y0;
      // Ausschnitt um den Mittelpunkt (Haus), nicht das ganze 5×5-Raster.
      this._origin = { x: x0, y: y0 };
      const cx = this._lx(m.lon), cy = this._ly(m.lat), vw = w * 0.55, vh = vw * 0.66;
      this._view = { x: cx - vw / 2, y: cy - vh / 2, w: vw, h: vh, bounds: { x0: 0, y0: 0, w, h } };
    } else if (this._data?.home) {
      this._origin = { x: Math.floor(pvLon2x(this._data.home.lon, z)), y: Math.floor(pvLat2y(this._data.home.lat, z)) };
      const cx = this._lx(this._data.home.lon), cy = this._ly(this._data.home.lat), vw = 700, vh = 460;
      this._view = { x: cx - vw / 2, y: cy - vh / 2, w: vw, h: vh, bounds: null };
    }
  }

  _setMsg(type, text) { this._msg = text ? { type, text } : null; }

  _change(id, patch) {
    const s = this._surfaces.find(x => x.id === id);
    if (!s) return;
    Object.assign(s, patch);
    if (s.kind !== "manual") s.azimuth = pvSurfaceAzimuth(s, this._zoom);
    this._dirty = true;
    this._render();
  }

  _newId() {
    let i = 1;
    while (this._surfaces.some(s => s.id === `f${i}`)) i++;
    return `f${i}`;
  }

  _startDraw(kind, id = null) {
    if (!this._admin) return;
    if (!id) {
      if (this._surfaces.length >= (this._data?.max_surfaces ?? 4)) return;
      id = this._newId();
      this._renumberDefaultSurfaces();
      this._surfaces.push({ id, name: `Fläche ${this._surfaces.length + 1}`, kind: "manual", points: [], edge: 0, flip: false,
        tilt: kind === "line" ? 90 : 30, azimuth: 180, input: "kwp", kwp: 1, modules: 0, module_wp: 0, area_m2: null, _new: true });
      this._dirty = true;
    }
    this._sel = id;
    this._open.add(id);
    this._draw = { id, kind, points: [] };
    this._setMsg("ok", kind === "area"
      ? "Ecken der Dachfläche nacheinander antippen. Startpunkt erneut antippen, Doppelklick oder „Fertig“ schließt die Fläche."
      : "Anfang und Ende der Fassade/Kante antippen.");
    this._render();
  }

  _finishDraw() {
    const d = this._draw;
    if (!d) return;
    if (d.kind === "area" && d.points.length > 3) {
      // Schlusspunkt (fast) auf dem Startpunkt → kein zusätzlicher Eckpunkt
      const [f, l] = [d.points[0], d.points[d.points.length - 1]];
      const tol = 12 * this._view.w / Math.max(1, this._svgWidth || 700);
      if (Math.hypot(this._lx(f[1]) - this._lx(l[1]), this._ly(f[0]) - this._ly(l[0])) < tol) d.points.pop();
    }
    const need = d.kind === "area" ? 3 : 2;
    if (d.points.length < need) { this._cancelDraw(); return; }
    const s = this._surfaces.find(x => x.id === d.id);
    const z = this._zoom;
    s.kind = d.kind;
    s.points = d.points;
    s.edge = d.kind === "area" ? pvDefaultEdge(d.points, z) : 0;
    s.flip = false;
    s.area_m2 = d.kind === "area" ? pvAreaM2(d.points, z) : null;
    s.azimuth = pvSurfaceAzimuth(s, z);
    delete s._new;
    this._draw = null;
    this._dirty = true;
    this._setMsg("ok", d.kind === "area"
      ? "Traufkante (untere Dachkante) prüfen: Kante der markierten Fläche antippen, um sie zu ändern."
      : "Ausrichtung prüfen, bei Bedarf „Richtung umdrehen“.");
    this._render();
  }

  _cancelDraw() {
    const d = this._draw;
    this._draw = null;
    if (d) {
      const s = this._surfaces.find(x => x.id === d.id);
      if (s?._new) { this._surfaces = this._surfaces.filter(x => x.id !== d.id); this._renumberDefaultSurfaces(); }
    }
    this._setMsg(null);
    this._render();
  }

  async _save() {
    if (!this._admin || this._busy) return;
    this._busy = "save";
    this._render();
    try {
      const surfaces = this._surfaces.map(({ _new, ...s }) => s);
      const res = await this._ws({ type: `${DOMAIN}/pv_layout/save`, surfaces });
      this._surfaces = JSON.parse(JSON.stringify(res.surfaces));
      this._data.surfaces = res.surfaces;
      this._dirty = false;
      this._setMsg("ok", `Gespeichert (${pvFmt(res.total_kwp)} kWp). Der Energiemanager lädt neu und rechnet die Prognose mit diesen Flächen.`);
    } catch (err) {
      this._setMsg("err", `Speichern fehlgeschlagen: ${err?.message || err}`);
    } finally {
      this._busy = "";
      this._render();
    }
  }

  _discard() {
    this._surfaces = JSON.parse(JSON.stringify(this._data?.surfaces || []));
    this._dirty = false;
    this._draw = null;
    this._setMsg(null);
    this._render();
  }

  // ── Darstellung ─────────────────────────────────────────────────────────
  _svg() {
    const v = this._view;
    if (!v) return `<svg viewBox="0 0 10 10"></svg>`;
    const z = this._zoom, m = this._data?.map;
    const px = ([lat, lon]) => `${this._lx(lon).toFixed(2)},${this._ly(lat).toFixed(2)}`;
    const scale = v.w / Math.max(1, this._svgWidth || 700);
    const r = 6 * scale, fs = 13 * scale;
    const tiles = this._tileUrls.map(t =>
      `<image href="${t.url}" x="${t.x * PV_TILE - (this._origin?.x || 0)}" y="${t.y * PV_TILE - (this._origin?.y || 0)}" width="${PV_TILE}" height="${PV_TILE}" preserveAspectRatio="none"/>`).join("");
    const grid = m ? "" : (() => {
      const step = 64, x0 = Math.floor(v.x / step) * step, y0 = Math.floor(v.y / step) * step;
      let g = "";
      for (let x = x0; x < v.x + v.w; x += step) g += `<line x1="${x}" y1="${v.y}" x2="${x}" y2="${v.y + v.h}"/>`;
      for (let y = y0; y < v.y + v.h; y += step) g += `<line x1="${v.x}" y1="${y}" x2="${v.x + v.w}" y2="${y}"/>`;
      return `<g stroke="rgba(255,255,255,.12)" vector-effect="non-scaling-stroke">${g}</g>`;
    })();
    const shapes = this._surfaces.map((s, i) => {
      if (s.kind === "manual" || !s.points?.length) return "";
      const c = PV_COLORS[i % PV_COLORS.length], sel = s.id === this._sel;
      const pts = s.points.map(px).join(" ");
      const xy = s.points.map(([lat, lon]) => [this._lx(lon), this._ly(lat)]);
      let shape, eave = "", edges = "", handles = "";
      if (s.kind === "area") {
        shape = `<polygon points="${pts}" data-surface="${esc(s.id)}" fill="${c}" fill-opacity="${sel ? .35 : .22}" stroke="${c}" stroke-width="2" vector-effect="non-scaling-stroke"/>`;
        const e = s.edge ?? 0, [a, b] = [xy[e], xy[(e + 1) % xy.length]];
        eave = `<line x1="${a[0]}" y1="${a[1]}" x2="${b[0]}" y2="${b[1]}" stroke="${c}" stroke-width="6" stroke-linecap="round" vector-effect="non-scaling-stroke" pointer-events="none"/>`;
        if (sel && !this._draw && this._admin) edges = xy.map((p, k) => { const q = xy[(k + 1) % xy.length];
          return `<line class="edge" data-edge="${k}" x1="${p[0]}" y1="${p[1]}" x2="${q[0]}" y2="${q[1]}" stroke="transparent" stroke-width="18" vector-effect="non-scaling-stroke" style="cursor:pointer"/>`; }).join("");
      } else {
        shape = `<polyline points="${pts}" data-surface="${esc(s.id)}" fill="none" stroke="${c}" stroke-width="6" stroke-linecap="round" vector-effect="non-scaling-stroke"/>`;
      }
      // Pfeil in Ausrichtung ab Mitte der Traufkante / Linie
      const e = s.kind === "area" ? (s.edge ?? 0) : 0, a = xy[e], b = xy[(e + 1) % xy.length];
      const mx = (a[0] + b[0]) / 2, my = (a[1] + b[1]) / 2, az = (Number(s.azimuth) || 0) * Math.PI / 180;
      const L = 34 * scale, tx = mx + Math.sin(az) * L, ty = my - Math.cos(az) * L;
      const arrow = `<line x1="${mx}" y1="${my}" x2="${tx}" y2="${ty}" stroke="#fff" stroke-width="2.5" vector-effect="non-scaling-stroke" marker-end="url(#pvArrow)" pointer-events="none"/>`;
      // Beschriftung außerhalb an der Pfeilspitze (schmale Nachbarflächen überdecken sich sonst)
      const sx = Math.sin(az), cy0 = Math.cos(az), gap = 6 * scale;
      const lx = tx + sx * gap, ly = ty - cy0 * gap;
      const anchor = sx > 0.3 ? "start" : sx < -0.3 ? "end" : "middle";
      const base = cy0 > 0.3 ? "auto" : cy0 < -0.3 ? "hanging" : "middle";
      const label = `<text class="pv-label" x="${lx}" y="${ly}" font-size="${fs}" text-anchor="${anchor}" dominant-baseline="${base}" fill="#fff" stroke="#000" stroke-width="${3 * scale}" paint-order="stroke" pointer-events="none">${esc(s.name)} · ${pvFmt(Math.round(s.azimuth))}° ${pvDir(s.azimuth)}</text>`;
      if (sel && !this._draw && this._admin) handles = xy.map((p, k) =>
        `<circle class="vtx" data-vtx="${k}" cx="${p[0]}" cy="${p[1]}" r="${r}" fill="#fff" stroke="${c}" stroke-width="2" vector-effect="non-scaling-stroke" style="cursor:move"/>`).join("");
      return `<g>${shape}${eave}${arrow}${edges}${label}${handles}</g>`;
    }).join("");
    let preview = "";
    if (this._draw?.points.length) {
      const pts = this._draw.points.map(px).join(" ");
      preview = `<polyline points="${pts}" fill="none" stroke="#fff" stroke-dasharray="6 4" stroke-width="2" vector-effect="non-scaling-stroke" pointer-events="none"/>`
        + this._draw.points.map(p => { const [x, y] = px(p).split(","); return `<circle cx="${x}" cy="${y}" r="${r}" fill="#fff" pointer-events="none"/>`; }).join("");
    }
    return `<svg class="${this._draw ? "drawing" : ""}" viewBox="${v.x} ${v.y} ${v.w} ${v.h}" preserveAspectRatio="xMidYMid slice">
      <defs><marker id="pvArrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M0,0L10,5L0,10z" fill="#fff"/></marker></defs>
      <rect x="${v.x - v.w}" y="${v.y - v.h}" width="${v.w * 3}" height="${v.h * 3}" fill="#30363b"/>
      ${grid}<g>${tiles}</g>${shapes}${preview}</svg>`;
  }

  _surfaceForm(s, i) {
    const c = PV_COLORS[i % PV_COLORS.length], ro = this._admin ? "" : "disabled";
    const kwp = pvKwp(s), drawn = s.kind !== "manual";
    const az = Number(s.azimuth) || 0;
    const open = this._open.has(s.id);
    return `<div class="surf ${s.id === this._sel ? "sel" : ""}" style="--c:${c}" data-id="${esc(s.id)}">
      <div class="s-head">
        <button class="tog" data-act="toggle" aria-expanded="${open}" title="${open ? "Zuklappen" : "Aufklappen"}">▸</button>
        ${open ? `<input class="name" data-f="name" value="${esc(s.name)}" maxlength="40" ${ro} aria-label="Name">`
          : `<span class="nm" data-act="toggle">${esc(s.name)}</span>`}
        <span class="chip">${pvFmt(kwp)} kWp</span>
        <span class="chip">${pvFmt(Math.round(az))}° ${pvDir(az)} · ${pvFmt(Number(s.tilt))}°</span>
        ${s.bifacial ? `<span class="chip">bifazial</span>` : ""}
        ${drawn ? "" : `<span class="chip warn">nicht eingezeichnet</span>`}
      </div>
      ${open ? `<div class="grid">
        <div><label>Neigung (°)</label><input type="number" data-f="tilt" min="0" max="90" step="1" value="${esc(s.tilt)}" ${ro}>
          <div class="hint">0° flach · 90° senkrecht</div></div>
        <div><label>Ausrichtung</label>${drawn
          ? `<div class="val">${pvFmt(Math.round(az))}° <small>${pvDir(az)}</small></div><div class="hint">aus der Zeichnung</div>`
          : `<input type="number" data-f="azimuth" min="0" max="360" step="1" value="${esc(az)}" ${ro}><div class="hint">0° N · 90° O · 180° S · 270° W</div>`}</div>
        <div><label>Leistung angeben als</label><select data-f="input" ${ro}>
          <option value="kwp" ${s.input !== "modules" ? "selected" : ""}>kWp gesamt</option>
          <option value="modules" ${s.input === "modules" ? "selected" : ""}>Module × Wp</option></select></div>
        ${s.input === "modules"
          ? `<div><label>Anzahl Module</label><input type="number" data-f="modules" min="1" max="500" step="1" value="${esc(s.modules || "")}" ${ro}></div>
             <div><label>Wp je Modul</label><input type="number" data-f="module_wp" min="50" max="1000" step="5" value="${esc(s.module_wp || "")}" ${ro}></div>`
          : `<div><label>Leistung (kWp)</label><input type="number" data-f="kwp" min="0.01" max="100" step="0.01" value="${esc(s.kwp || "")}" ${ro}></div>`}
        ${s.kind === "area" ? `<div><label>Grundfläche</label><div class="val">${pvFmt(s.area_m2 ?? pvAreaM2(s.points, this._zoom), 1)} m²
          <small>${Number(s.tilt) < 85 ? `≈ ${pvFmt((s.area_m2 ?? 0) / Math.cos(Number(s.tilt) * Math.PI / 180), 0)} m² Dach` : ""}</small></div></div>` : ""}
        <div><label>Module</label><label class="chk"><input type="checkbox" data-f="bifacial" ${s.bifacial ? "checked" : ""} ${ro}> bifazial</label>
          <div class="hint">Rückseite erzeugt mit (z. B. Zaun, Fassade, aufgeständert)</div></div>
        ${s.bifacial ? `<div><label>Bifazialfaktor</label><input type="number" data-f="bifaciality" min="0.5" max="1" step="0.05" value="${esc(s.bifaciality ?? 0.7)}" ${ro}>
          <div class="hint">Rückseite/Vorderseite laut Datenblatt, meist 0,65–0,8</div></div>` : ""}
      </div>
      ${this._admin ? `<div class="s-actions">
        <button data-act="sel">Auf Karte zeigen</button>
        <button data-act="draw-area">${s.kind === "area" ? "Fläche neu zeichnen" : "Als Dachfläche zeichnen"}</button>
        <button data-act="draw-line">${s.kind === "line" ? "Linie neu zeichnen" : "Als Fassade/Linie zeichnen"}</button>
        ${drawn ? `<button data-act="flip">Richtung umdrehen</button>` : ""}
        <button data-act="del">Löschen</button></div>` : ""}` : ""}
    </div>`;
  }

  _render() {
    if (!this.shadowRoot) return;
    const d = this._data, admin = this._admin;
    const title = this._config.title || "PV-Flächen";
    const total = this._surfaces.reduce((t, s) => t + pvKwp(s), 0);
    const max = d?.max_surfaces ?? 4;
    let body;
    if (!this._hass || (!d && this._loading)) body = `<div class="msg">Lade PV-Flächen …</div>`;
    else if (!d) body = "";
    else body = `<div class="layout"><div class="main">
      <div class="map">${this._svg()}
        ${this._draw ? `<div class="drawhint">${this._draw.kind === "area" ? "Ecken antippen · Startpunkt oder Doppelklick = fertig" : "Anfang und Ende antippen"}</div>` : ""}
        <div class="tools"><button data-act="zin" title="Vergrößern">+</button><button data-act="zout" title="Verkleinern">−</button><button data-act="reset" title="Gespeicherte Kartenansicht zurücksetzen">⤢</button><button data-act="home" title="Zum Home-Assistant-Standort">⌂</button></div>
        <div class="attr">${d.map ? esc(d.map.attribution || d.attribution) : "kein Luftbild – Raster 64 px"}</div>
      </div>
      ${admin ? `<div class="address-row">
        <input type="search" data-map-address placeholder="Adresse, PLZ, Ort suchen"
          aria-label="Adresse für PV-Karte" value="${esc(this._address)}" maxlength="180">
        <button type="button" data-act="address" ${this._busy ? "disabled" : ""}>Adresse suchen</button>
      </div><div class="address-results" data-address-results role="listbox" aria-label="Adressvorschläge"></div>
      <div class="address-hint">Vorschläge nach Tipp-Pause über Photon; manuelle Suche über Nominatim mit Klick/Enter.
      Suchtext wird an den jeweiligen Anbieter übertragen. PV-Flächen bleiben erhalten.</div>` : ""}
      <div class="bar">
        ${this._draw ? `<button class="primary" data-act="finish">Fertig</button><button data-act="cancel">Abbrechen</button>` : admin ? `
          <button data-act="add-area" ${this._surfaces.length >= max ? "disabled" : ""}>+ Dachfläche</button>
          <button data-act="add-line" ${this._surfaces.length >= max ? "disabled" : ""}>+ Fassade/Linie</button>` : ""}
        <span class="sp"></span>
        ${admin ? `<button data-act="map" ${this._busy ? "disabled" : ""}>${d.map ? "Luftbild neu laden" : "Luftbild laden"}</button>` : ""}
      </div>
      ${this._msg ? `<div class="msg ${this._msg.type}">${esc(this._msg.text)}</div>` : ""}
      ${d.map ? `<div class="hint">Luftbild vom ${esc(new Date(d.map.fetched).toLocaleDateString("de-AT"))}. „Luftbild neu laden“ lädt den aktuellen Kartenmittelpunkt neu.</div>` : ""}
      </div><div class="side">
      ${this._surfaces.map((s, i) => this._surfaceForm(s, i)).join("")}
      ${this._surfaces.length ? "" : `<div class="hint">Noch keine PV-Fläche. Mit „+ Dachfläche“ die Fläche auf dem Luftbild einzeichnen.</div>`}
      <div class="hint">Höchstens ${max} Flächen. Dachfläche: Ecken einzeichnen und die untere Dachkante (Traufe) markieren – die Ausrichtung ist die Seite, zu der das Dach abfällt. Fassade: Linie entlang der Wand, Ausrichtung mit „Richtung umdrehen“ wählen.</div>
      ${admin ? `<div class="bar"><span class="sp"></span>
        <button data-act="discard" ${this._dirty ? "" : "disabled"}>Verwerfen</button>
        <button class="primary" data-act="save" ${this._dirty && !this._busy && !this._draw ? "" : "disabled"}>Speichern</button></div>`
        : `<div class="hint">Nur Administratoren können PV-Flächen ändern.</div>`}</div></div>`;
    this.shadowRoot.innerHTML = `<style>${PV_CSS}</style><ha-card>
      <div class="hd"><h2>${esc(title)}</h2>
        ${d ? `<span class="chip">${pvFmt(total)} kWp</span>` : ""}
        ${d && d.solar_mode !== "calculated" ? `<span class="chip warn">Prognose-Modus: extern – Flächen werden nur bei „Eigene Berechnung“ verwendet</span>` : ""}
        ${this._dirty ? `<span class="chip warn">nicht gespeichert</span>` : ""}</div>
      ${this._msg && !d ? `<div class="msg ${this._msg.type}">${esc(this._msg.text)}</div>` : ""}
      ${body}</ha-card>`;
    this._bind();
  }

  _redrawMap() {
    const svg = this.shadowRoot?.querySelector("svg");
    if (!svg) return;
    const tpl = document.createElement("template");
    tpl.innerHTML = this._svg();
    svg.replaceWith(tpl.content.firstElementChild);
    this._bindSvg();
  }

  _bind() {
    const root = this.shadowRoot;
    root.querySelectorAll(".s-head .nm[data-act]").forEach(b => b.addEventListener("click", e => this._action("toggle", e.currentTarget.closest(".surf")?.dataset.id)));
    root.querySelectorAll("button[data-act]").forEach(b => b.addEventListener("click", e => this._action(e.currentTarget.dataset.act, e.currentTarget.closest(".surf")?.dataset.id)));
    const addressInput=root.querySelector("[data-map-address]");
    if (addressInput) {
      addressInput.addEventListener("input",e=>{this._address=e.target.value;this._queueSuggestions();});
      addressInput.addEventListener("keydown",e=>{
        if(e.key==="Enter"){e.preventDefault();this._address=e.target.value;this._searchAddress();}
      });
    }
    root.querySelectorAll(".surf [data-f]").forEach(el => el.addEventListener("change", e => {
      const id = e.target.closest(".surf").dataset.id, f = e.target.dataset.f;
      const v = f === "name" || f === "input" ? e.target.value : f === "bifacial" ? e.target.checked : Number(e.target.value);
      const patch = { [f]: v };
      if (f === "input" && v === "modules") { const s = this._surfaces.find(x => x.id === id); if (!s.module_wp) patch.module_wp = 400; if (!s.modules) patch.modules = Math.max(1, Math.round(pvKwp(s) * 1000 / 400)); }
      if (f === "input" && v === "kwp") { const s = this._surfaces.find(x => x.id === id); patch.kwp = Math.round(pvKwp(s) * 1000) / 1000 || 1; }
      this._change(id, patch);
    }));
    this._showAddressSuggestions();
    this._bindSvg();
  }

  _action(act, id) {
    const s = id ? this._surfaces.find(x => x.id === id) : null;
    switch (act) {
      case "zin": case "zout": { const v = this._view, f = act === "zin" ? 0.7 : 1 / 0.7;
        this._zoomAt(v.x + v.w / 2, v.y + v.h / 2, f); break; }
      case "home": this._goHome(); break;
      case "reset": this._resetView(); this._redrawMap(); break;
      case "address": this._searchAddress(); break;
      case "map": this._reloadMap(); break;
      case "add-area": this._startDraw("area"); break;
      case "add-line": this._startDraw("line"); break;
      case "finish": this._finishDraw(); break;
      case "cancel": this._cancelDraw(); break;
      case "save": this._save(); break;
      case "discard": this._discard(); break;
      case "sel": this._sel = id; this._focus(s); this._render(); break;
      case "toggle": if (this._open.has(id)) this._open.delete(id); else this._open.add(id); this._render(); break;
      case "draw-area": this._startDraw("area", id); break;
      case "draw-line": this._startDraw("line", id); break;
      case "flip": this._change(id, { flip: !s.flip }); break;
      case "del": if (confirm(`„${s.name}“ löschen?`)) { this._surfaces = this._surfaces.filter(x => x.id !== id); this._renumberDefaultSurfaces(); this._dirty = true; this._render(); } break;
    }
  }

  _focus(s) {
    if (!s?.points?.length) return;
    const xs = s.points.map(p => this._lx(p[1])), ys = s.points.map(p => this._ly(p[0]));
    const cx = (Math.min(...xs) + Math.max(...xs)) / 2, cy = (Math.min(...ys) + Math.max(...ys)) / 2;
    this._view = { ...this._view, x: cx - this._view.w / 2, y: cy - this._view.h / 2 };
  }

  _zoomAt(wx, wy, f) {
    const v = this._view, w = Math.min(4000, Math.max(60, v.w * f)), k = w / v.w, h = v.h * k;
    this._view = { ...v, x: wx - (wx - v.x) * k, y: wy - (wy - v.y) * k, w, h };
    this._redrawMap();
    this._scheduleMapRefresh();
  }

  _toWorld(svg, ev) {
    const pt = svg.createSVGPoint();
    pt.x = ev.clientX; pt.y = ev.clientY;
    const ctm = svg.getScreenCTM();
    if (!ctm) return null;
    const p = pt.matrixTransform(ctm.inverse());
    return [p.x, p.y];
  }

  _bindSvg() {
    const svg = this.shadowRoot?.querySelector("svg");
    if (!svg || !this._view) return;
    this._svgWidth = svg.clientWidth || this._svgWidth;
    if (svg.clientWidth && svg.clientHeight) {
      const h = this._view.w * svg.clientHeight / svg.clientWidth;
      if (Math.abs(h - this._view.h) > 0.5) {
        this._view = { ...this._view, y: this._view.y + (this._view.h - h) / 2, h };
        svg.setAttribute("viewBox", `${this._view.x} ${this._view.y} ${this._view.w} ${this._view.h}`);
      }
    }
    let start = null;
    svg.addEventListener("pointerdown", ev => {
      const vtx = ev.target.closest?.(".vtx");
      start = { x: ev.clientX, y: ev.clientY, view: { ...this._view }, vtx: vtx ? Number(vtx.dataset.vtx) : null, moved: false, target: ev.target };
      svg.setPointerCapture(ev.pointerId);
    });
    svg.addEventListener("pointermove", ev => {
      if (!start) return;
      const dx = ev.clientX - start.x, dy = ev.clientY - start.y;
      if (!start.moved && Math.hypot(dx, dy) < 5) return;
      start.moved = true;
      if (start.vtx != null && this._admin) {
        const w = this._toWorld(svg, ev), s = this._surfaces.find(x => x.id === this._sel), z = this._zoom;
        if (!w || !s) return;
        s.points[start.vtx] = [Math.round(this._lat(w[1]) * 1e8) / 1e8, Math.round(this._lon(w[0]) * 1e8) / 1e8];
        if (s.kind === "area") s.area_m2 = pvAreaM2(s.points, z);
        s.azimuth = pvSurfaceAzimuth(s, z);
        this._dirty = true;
        this._redrawMap();
        return;
      }
      const k = start.view.w / (svg.clientWidth || 1);
      this._view = { ...start.view, x: start.view.x - dx * k, y: start.view.y - dy * k };
      svg.setAttribute("viewBox", `${this._view.x} ${this._view.y} ${this._view.w} ${this._view.h}`);
    });
    svg.addEventListener("pointerup", ev => {
      const s0 = start; start = null;
      if (!s0) return;
      if (s0.moved) {
        if (s0.vtx != null) this._render(); else { this._redrawMap(); this._scheduleMapRefresh(); }
        return;
      }
      this._click(svg, ev, s0.target);
    });
    svg.addEventListener("dblclick", ev => { if (this._draw) { ev.preventDefault(); this._finishDraw(); } });
    svg.addEventListener("wheel", ev => {
      ev.preventDefault();
      const w = this._toWorld(svg, ev);
      if (w) this._zoomAt(w[0], w[1], ev.deltaY > 0 ? 1.15 : 1 / 1.15);
    }, { passive: false });
  }

  _click(svg, ev, target) {
    const z = this._zoom;
    if (this._draw) {
      const w = this._toWorld(svg, ev);
      if (!w) return;
      const p = [Math.round(this._lat(w[1]) * 1e8) / 1e8, Math.round(this._lon(w[0]) * 1e8) / 1e8];
      const last = this._draw.points[this._draw.points.length - 1];
      const tol = 6 * this._view.w / Math.max(1, svg.clientWidth || 700);
      const first = this._draw.points[0];
      if (this._draw.kind === "area" && this._draw.points.length >= 3
          && Math.hypot(this._lx(first[1]) - w[0], this._ly(first[0]) - w[1]) < 2 * tol) { this._finishDraw(); return; }   // Klick auf Startpunkt schließt die Fläche
      if (last && Math.hypot(this._lx(last[1]) - w[0], this._ly(last[0]) - w[1]) < tol) return;   // Doppelklick → kein Doppelpunkt
      this._draw.points.push(p);
      if (this._draw.kind === "line" && this._draw.points.length === 2) this._finishDraw();
      else this._redrawMap();
      return;
    }
    const edge = target.closest?.(".edge");
    if (edge && this._admin) {
      this._change(this._sel, { edge: Number(edge.dataset.edge), flip: false });
      return;
    }
    const surf = target.closest?.("[data-surface]");
    this._sel = surf ? surf.dataset.surface : null;
    if (this._sel) this._open.add(this._sel);
    this._render();
    this.shadowRoot.querySelector(`.surf[data-id="${CSS.escape(this._sel || "")}"]`)?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }
}

if (!customElements.get("smartify-energy-pv-card")) customElements.define("smartify-energy-pv-card", SmartifyEnergyPvCard);

window.customCards = window.customCards || [];
if (!window.customCards.some(c => c.type === "smartify-energy-plan-card")) window.customCards.push({
  type: "smartify-energy-plan-card",
  name: "smartify Energiemanager",
  description: "Überschuss, Prioritäten (Drag & Drop) und PV-Plan des smartify Energiemanagers.",
  preview: false,
});
if (!window.customCards.some(c => c.type === "smartify-energy-pv-card")) window.customCards.push({
  type: "smartify-energy-pv-card",
  name: "SEP PV-Flächen",
  description: "PV-Flächen des smartify Energiemanagers auf dem Luftbild einzeichnen (Ausrichtung, Neigung, Leistung).",
  preview: false,
});
console.info(`%c SMARTIFY-ENERGY-PLAN-CARD %c v${CARD_VERSION} `, "background:#00ACC1;color:#fff", "background:#333;color:#fff");


