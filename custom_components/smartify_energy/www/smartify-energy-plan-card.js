/**
 * smartify-energy-plan-card
 * Lovelace Custom Card für den smartify Energiemanager (Integration smartify_energy).
 * Zeigt Überschuss, Prioritäten (Drag & Drop) und den PV-Plan der nächsten Stunden.
 * Version: 1.3.5
 *
 * Installation: /config/www/smartify-energy-plan-card.js
 * Resource:     /local/smartify-energy-plan-card.js  (type: module)
 *
 * YAML (alles optional – Hub und Geräte werden automatisch gefunden):
 *   type: custom:smartify-energy-plan-card
 *   title: Energiemanager
 *   hub: <device_id>          # nur nötig bei mehreren Energiemanagern
 *   show_header: true
 *   show_priorities: true
 *   show_timeline: true
 *   timeline_hours: 24
 *   show_mode: true           # Modus-Auswahl je Gerät
 *   show_settings: true       # Zahnrad: alle Einstellungen je Gerät / Energiemanager
 *
 * Theme-Variablen (haben Vorrang):
 *   smartify-plan-row-background   Zeilen-/Kachelhintergrund (default card-background-color)
 *   smartify-plan-border-radius    Eckenradius (default 6px)
 *   smartify-plan-text-color       Textfarbe (default primary-text-color)
 */

const CARD_VERSION = "1.3.5";
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
const MODE_HELP = { auto: "SEP steuert", observe: "nur Empfehlung", manual: "Sie steuern", off: "ausgesetzt", disabled: "kein neuer WW-Boost" };
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
  "heater_min_on": "Optionale Mindestlaufzeit gegen Flattern (0 = sofortige Abschaltung bei PV-Mangel). Temperaturfehler oder maximale Temperatur schalten dennoch sofort AUS.",
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
  "pause_reservation_pct": "Restreservierung in Heizpausen nach der ersten erkannten Heizphase. 100 % (Standard) sichert die volle Nennleistung ab; 50 % reserviert bei 2000 W Nennleistung nur 1000 W, sodass nachrangige Geräte früher starten können. Während tatsächlicher Heizphasen zählt mindestens der gemessene Verbrauch. Ohne gültigen Leistungssensor bleibt die volle Nennleistung reserviert. Niedrigere Werte können bei gleichzeitigem Heizen Netzbezug verursachen; bereits gestartete Programme werden nicht unterbrochen.",
  "min_surplus": "Zusätzliche einstellbare PV-Startschwelle in Watt (W). Für einen automatischen PV-Start zählt der höhere Wert aus Nennleistung und Mindest-Überschuss: z. B. bei 2000 W Heizleistung und 1500 W Schwelle müssen mindestens 2000 W frei sein. Auch der Mittelwert muss reichen. Negative Werte senken diese Heizlast-Absicherung nicht ab; Netzbezug kann aber durch Spätstart, Sofortfenster oder Sofort starten ausdrücklich erlaubt werden.",
  "finish_threshold": "Unter dieser Leistung kann das Programm als fertig gelten, sobald die Fertigerkennung freigegeben ist. Beispiel: 5 W. Eine zu hohe Schwelle kann längere Programmpausen mit dem Programmende verwechseln.",
  "finish_minutes": "So lange muss die Leistung unter der Fertig-Schwelle bleiben. Erst dann erscheint „Fertig“. Ein längerer Wert vermeidet Fehlmeldungen bei Pausen, meldet das Ende aber später.",
  "duration": "Geschätzte Programmdauer in Stunden für die Startempfehlung. Beispiel: 2,5 für zweieinhalb Stunden. Das Gerät wird nach dieser Zeit nicht automatisch abgeschaltet.",
  "sinks_yield": "Ein: Die Leistung von Ohmpilot/Heizstab steht den SEP-Geräten zur Verfügung, die Senke nimmt nur den restlichen Überschuss. Voraussetzung: Die Senke regelt sich selbst schnell zurück, sobald Netzbezug droht. Aus: Senken werden nur angezeigt.",
  "nachladen": "Gibt bei einem wartenden Haushaltsgerät die Steckdose frei, damit Sie zum Beispiel Wäsche nachlegen können. Nach dem Ausschalten entscheidet SEP wieder nach Überschuss und Uhrzeit; das Programm kann dann auch sofort freigegeben werden.",
  "latest_start": "Ab dieser Uhrzeit wird ein wartendes Programm auch ohne genügend Solarstrom freigegeben. Es kann dann Netzstrom verbrauchen. Das ist eine Startzeit, keine Fertigzeit.",
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
  // Same two-way third gate as the appliance controller: short mean meets
  // the required watts, OR the short change is neutral/nonfalling.
  const projected = recentAverage + change;
  const stable = change >= -tolerance;
  const allowed = stable || projected >= needed;
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
      if (!["priority", "battery_rank"].includes(e.translation_key)) (settings[e.device_id] ||= []).push({ id: e.entity_id, dom, key: e.translation_key, config: e.entity_category === "config" });
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
        active: ents["binary_sensor:active"],
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
      <div class="section">Bereiche</div>
      <div class="row"><input type="checkbox" id="show_header" ${chk("show_header")}><label for="show_header">Netzsaldo- und Budgetleiste</label></div>
      <div class="hint">Zeigt den echten Netzsaldo (+ Einspeisung, − Bezug) getrennt vom rechnerischen Steuerbudget sowie Verteilung, Prognose und Speicherdaten.</div>
      <div class="row"><input type="checkbox" id="show_priorities" ${chk("show_priorities")}><label for="show_priorities">Prioritäten (Drag &amp; Drop)</label></div>
      <div class="hint">Zeigt die Geräteliste mit ihrer Reihenfolge. Ziehen verändert, wer den verfügbaren Solarstrom zuerst bekommt.</div>
      <div class="row"><input type="checkbox" id="show_mode" ${chk("show_mode")}><label for="show_mode">Modus-Auswahl je Gerät</label></div>
      <div class="hint">Zeigt die schnelle Betriebsmodus-Auswahl neben jedem Gerät.</div>
      <div class="row"><input type="checkbox" id="show_settings" ${chk("show_settings")}><label for="show_settings">Einstellungen (Zahnrad) erlauben</label></div>
      <div class="hint">Zeigt das Zahnrad mit Einstellungen und Erklärungen. Ausblenden verändert keine Regelung und ist keine Zugriffssperre.</div>
      <div class="row"><input type="checkbox" id="show_timeline" ${chk("show_timeline")}><label for="show_timeline">PV-Plan (Zeitleiste)</label></div>
      <div class="hint">Zeigt die Prognose und die empfohlenen Zeiträume. Der Plan ist eine Empfehlung, keine feste Startzusage.</div>
      <div class="hint">Zeigt den restlichen heutigen Tag und den gesamten morgigen Tag (00:00–24:00 Uhr), einschließlich Stunden ohne PV-Ertrag.</div>
    `;
    const set = (k, v) => { this._config = { ...this._config, [k]: v }; if (v === "" || v == null) delete this._config[k]; this._emit(); };
    const $ = id => this.shadowRoot.getElementById(id);
    $("title").addEventListener("change", e => set("title", e.target.value));
    $("hub").addEventListener("change", e => set("hub", e.target.value));
    ["show_header", "show_priorities", "show_mode", "show_settings", "show_timeline"].forEach(k =>
      $(k).addEventListener("change", e => set(k, e.target.checked)));

  }
}
customElements.define("smartify-energy-plan-card-editor", SmartifyEnergyPlanCardEditor);

// ── Card ────────────────────────────────────────────────────────────────────

const CARD_CSS = `
  :host { display:block; --row-bg:var(--smartify-plan-row-background, var(--card-background-color));
          --radius:var(--smartify-plan-border-radius, 6px); --txt:var(--smartify-plan-text-color, var(--primary-text-color)); }
  ha-card { padding:12px; color:var(--txt); }
  .title { font-size:16px; font-weight:600; margin:0 0 10px 2px; display:flex; align-items:center; gap:8px; }
  .sep-brand-icon { width:40px; height:40px; flex:0 0 40px; object-fit:contain; border-radius:7px; }
  .title .sp { flex:1; }
  .section { font-size:11px; font-weight:600; letter-spacing:.08em; text-transform:uppercase;
             color:var(--secondary-text-color); margin:14px 2px 6px; display:flex; justify-content:space-between; }
  .section span:last-child { text-transform:none; letter-spacing:0; font-weight:400; }

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

  .list { display:flex; flex-direction:column; gap:4px; position:relative; }
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
  .sep-gate { font-size:12px; font-weight:800; line-height:1.2; min-width:12px; text-align:center; }
  .sep-log-toggle { border:1px solid var(--divider-color); border-radius:6px; padding:1px 6px; background:transparent; color:var(--secondary-text-color); font:inherit; font-size:10px; cursor:pointer; }
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
  .pb-label { font-size:10px; opacity:.72; }
  .pw { font-size:13px; font-weight:bold; white-space:nowrap; }
  .pb-budget { font-size:13px; font-weight:700; font-variant-numeric:tabular-nums; }
  .pb-budget.negative { color:var(--error-color, #d45b48); }
  .pb-budget.positive { color:var(--success-color, #2e7d32); }
  @media (max-width:560px) {
    .dev { grid-template-columns:18px 24px 24px minmax(0,1fr); gap:5px; }
    .right { grid-column:4; grid-row:2; align-items:flex-start; width:100%; }
    .power-budget { justify-content:flex-start; gap:12px; }
    .pb-item { align-items:flex-start; }
    }
  .chip { font-size:10px; padding:1px 6px; border-radius:8px; color:#000; font-weight:600; }

  .timeline { background:var(--row-bg); border-radius:var(--radius); padding:8px 6px 4px; box-sizing:border-box; }
  .bars { display:flex; align-items:flex-end; gap:2px; height:96px; position:relative; }
  .col { flex:1 1 0; min-width:0; height:100%; position:relative; display:flex; flex-direction:column; justify-content:flex-end; }
  .col .pv { position:absolute; left:0; right:0; bottom:0; border-radius:3px 3px 0 0; opacity:.22; background:${grad(PV_GRADIENT).replace("to right", "to top")}; }
  .col .seg { position:relative; width:100%; }
  .col .seg:last-child { border-radius:3px 3px 0 0; }
  .pv-break { flex:0 0 30px; min-width:30px; height:100%; border-left:1px dashed var(--divider-color); border-right:1px dashed var(--divider-color); display:flex; align-items:center; justify-content:center; color:var(--secondary-text-color); font-size:9px; writing-mode:vertical-rl; box-sizing:border-box; background:var(--secondary-background-color,transparent); opacity:.8; }\n  .pv-break-label { flex:0 0 30px !important; min-width:30px !important; }\n  .col.gap { margin-left:8px; }
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
              margin:-4px 0 0; padding:8px 10px 10px; display:grid; grid-template-columns:1fr auto; gap:6px 10px;
              align-items:center; font-size:13px; }
  .settings.hub { border-radius:var(--radius); margin:0 0 10px; }
  .settings .grp { grid-column:1 / -1; font-size:10px; font-weight:600; letter-spacing:.08em; text-transform:uppercase;
                   color:var(--secondary-text-color); margin-top:4px; }
  .settings label { color:var(--txt); white-space:normal; overflow-wrap:anywhere; }
  .setting-help { grid-column:1 / -1; font-size:12px; line-height:1.5; color:var(--secondary-text-color); padding:0 0 12px; border-bottom:1px solid var(--divider-color); white-space:normal; overflow-wrap:anywhere; }
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
    this._open = new Set();
    this._logOpen = new Set();
  }

  static getConfigElement() { return document.createElement("smartify-energy-plan-card-editor"); }
  static getStubConfig() { return { show_header: true, show_priorities: true, show_timeline: true, timeline_hours: 24 }; }

  setConfig(config) {
    this._config = { show_header: true, show_priorities: true, show_timeline: true, show_mode: true, timeline_hours: 24, ...config };
    this._sig = "";
    if (this._hass) this._render();
  }

  set hass(hass) {
    this._hass = hass;
    if (this._drag) return;
    const data = collect(hass, this._config.hub);
    const ids = data ? [...Object.values(data.ents), ...data.hubSettings.map(x => x.id),
      ...data.devices.flatMap(d => [d.status, d.power, d.planned, d.mode, d.active, ...d.settings.map(x => x.id)])] : [];
    const sig = ids.map(id => { const s = hass.states[id]; return s ? `${id}:${s.last_updated}` : id; }).join("|");
    if (sig === this._sig) return;
    this._data = data;
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
    const tiles = [
      { ent: e["sensor:allocated"], icon: "mdi:call-split", v: fmtW(num(alloc?.state)), n: "Verteilt", g: PALETTE[0] },
    ];
    if (fc && fc.state !== "unknown" && fc.state !== "unavailable") {
      const rest = fc.attributes.rest_heute_kwh;
      tiles.push({ ent: e["sensor:forecast_today"], icon: "mdi:weather-sunny", v: `${num(fc.state)?.toFixed(1)} kWh`,
                   n: rest != null ? `Rest ${Number(rest).toFixed(1)} kWh` : "Prognose heute", g: PV_GRADIENT });
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
          <ha-icon icon="${t.icon}"></ha-icon><div class="v">${esc(t.v)}</div><div class="n">${esc(t.n)}</div>
        </div>`).join("")}</div>`;
  }

  _modeSelect(entityId, cls = "", heater = false) {
    const st = this._st(entityId);
    if (!st) return "";
    const opts = st.attributes.options || Object.keys(MODE_LABELS);
    const label = o => [MODE_LABELS[o] || o, (heater && o === "manual" ? "Temperaturregelung · Netz erlaubt" : MODE_HELP[o])].filter(Boolean).join(" · ");
    return `<select class="mode ${esc(st.state)} ${cls}" data-select="${entityId}" aria-label="Betriebsmodus">
      ${opts.map(o => `<option value="${esc(o)}" ${o === st.state ? "selected" : ""}>${esc(label(o))}</option>`).join("")}
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

  _settings(items, prefix, cls = "") {
    if (!items.length) return "";
    const main = items.filter(i => !i.config);
    const cfg = items.filter(i => i.config);
    const rows = list => list.map(i => `
      <label title="${esc(this._label(i.id, prefix))}">${esc(this._label(i.id, prefix))}</label>
      <div class="ctl">${this._control(i)}</div>
      <div class="setting-help">${esc((i.key === "mode" && this._st(i.id)?.attributes?.options?.includes("disabled")
        ? "Automatik: SEP löst den WW-Boost nach den eingestellten Bedingungen aus. Beobachten: nur Empfehlungen, kein Auslösen. Deaktiviert: kein neuer WW-Boost durch SEP. Eine bereits gestartete Warmwasserladung läuft unter Kontrolle der Wärmepumpe weiter."
        : SETTING_HELP[i.key]) || "")}</div>`).join("");
    return `<div class="settings ${cls}">
      ${main.length ? `<div class="grp">Bedienung</div>${rows(main)}` : ""}
      ${cfg.length ? `<div class="grp">Einstellungen</div>${rows(cfg)}` : ""}
    </div>`;
  }

  _devices(d) {
    const rows = d.devices
      .map(dev => ({ dev, prio: dev.virtualBattery
        ? (num(this._st(dev.rankEntity)?.state) ?? 99)
        : (num(this._st(dev.status)?.attributes?.prioritaet) ?? 5) }))
      .sort((a, b) => a.prio - b.prio || a.dev.name.localeCompare(b.dev.name));
    if (!rows.length) return `<div class="empty">Noch keine Geräte – in der Integration „+ Gerät hinzufügen“.</div>`;
    return `<div class="list">${rows.map(({ dev, prio }) => {
      if (dev.virtualBattery) {
        const charge = Math.max(0, num(this._st(dev.batteryBudget)?.attributes?.speicher_w) || 0);
        const soc = num(this._st(dev.status)?.attributes?.soc);
        return `<div class="dev-wrap" data-wrap="__battery__">
          <div class="dev" data-dev="__battery__" style="border-image-source:linear-gradient(var(--divider-color),var(--divider-color))">
            <div class="handle" title="PV-Akku per Drag & Drop priorisieren">⠿</div>
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
      const gate = (letter, ok, explanation) =>
        `<span class="sep-gate" style="color:${gateColor(ok)}" title="${esc(explanation)}" aria-label="${esc(letter + ": " + explanation)}">${letter}</span>`;
      const historyInfo = `Historie: ${trendAge ?? "–"} min vorhanden, benötigt ${avgWindow ?? "–"} min; Ø ${fmtW(budgetAverage)}`;
      const trendInfo = `Trend: ${trendReady ? (trendOk ? "Bedingung erfüllt" : "Bedingung nicht erfüllt") : "Messhistorie noch nicht vollständig"}; Fenster ${trendWindow ?? "–"} min, Kurzzeit-Ø ${fmtW(trendRecent)}, Änderung ${fmtW(trendDelta)}, Fortschreibung ${fmtW(direction.projected)}, benötigt ${fmtW(needed)}`;
      const budgetInfo = `Budget: ${budgetOk ? "Bedingung erfüllt" : "Bedingung nicht erfüllt"}; aktuell ${fmtW(budgetNow)}, Ø ${fmtW(budgetAverage)}, benötigt ${fmtW(needed)}`;
      const trendText = trendRelevant
        ? `<span class="sep-gates" title="${esc(historyInfo + " | " + trendInfo + " | " + budgetInfo)}">${gate("H", avgReady, historyInfo)}${gate("T", trendOk, trendInfo)}${gate("B", budgetOk, budgetInfo)}${avgReady && trendOk && budgetOk ? '<ha-icon icon="mdi:check-circle" class="sep-history-icon" style="color:var(--success-color, #43a047)"></ha-icon>' : ""}</span>`
        : "";
      const logOpen = this._logOpen.has(dev.id);
      const logRow = (letter, ok, detail) =>
        `<div class="sep-log-row"><span class="sep-log-code" style="color:${gateColor(ok)}">${letter}</span><span class="sep-log-detail">${esc(detail)}</span></div>`;
      const historyNeed = avgWindow == null ? null : avgWindow * 0.9;
      const trendHistoryNeed = trendWindow == null ? null : trendWindow * 2;
      const logText = trendRelevant ? `<div class="sep-log" data-log-panel="${esc(dev.id)}" id="sep-log-${esc(dev.id)}">
        ${logRow("H", avgReady, `Ist ${trendAge == null ? "–" : trendAge.toFixed(1)} min / Soll ${historyNeed == null ? "–" : historyNeed.toFixed(1)} min (90 % von ${avgWindow ?? "–"} min)`)}
        ${logRow("T", trendOk, `Historie Ist ${trendAge == null ? "–" : trendAge.toFixed(1)} / Soll ${trendHistoryNeed == null ? "–" : trendHistoryNeed.toFixed(1)} min; Änderung Ist ${fmtW(trendDelta)} / Soll ≥ ${fmtW(-trendTolerance)} ODER Prognose Ist ${fmtW(direction.projected)} / Soll ≥ ${fmtW(needed)}`)}
        ${logRow("B", budgetOk, `Aktuell Ist ${fmtW(budgetNow)} / Soll ≥ ${fmtW(needed)}; Ø Ist ${fmtW(budgetAverage)} / Soll ≥ ${fmtW(needed)}`)}
      </div>` : "";
      const logToggle = trendRelevant ? `<button type="button" class="sep-log-toggle" data-log="${esc(dev.id)}" aria-expanded="${logOpen}" aria-controls="sep-log-${esc(dev.id)}" title="Ist- und Sollwerte für H, T und B anzeigen">${logOpen ? "Log ▴" : "Log ▾"}</button>` : "";
      const planTxt = pt ? `Empf. Start ${pt}${planned.attributes.pv_anteil_prozent != null ? ` · ${planned.attributes.pv_anteil_prozent} % PV` : ""}` : "";
      const chip = forced ? `<span class="chip" style="background:${grad(FORCED_GRADIENT)}">Pflicht</span>`
                 : on ? `<span class="chip" style="background:${grad(dev.color)}">${esc(statusTxt || "ein")}</span>`
                 : mode === "observe" ? `<span class="chip" style="background:#B3E5FC">beobachten</span>` : "";
      const open = this._open.has(dev.id);
      return `
        <div class="dev-wrap" data-wrap="${dev.id}">
        <div class="dev" data-dev="${dev.id}" style="${border ? `border-image-source:${grad(border)}` : "border-image-source:linear-gradient(var(--divider-color),var(--divider-color))"}">
          <div class="handle" title="Halten und ziehen, um die Priorität zu ändern">⠿</div>
          <div class="badge" style="background:${grad(dev.color)}">${Math.round(prio)}</div>
          <ha-icon icon="${esc(icon)}" data-more="${dev.status}" style="color:${on ? dev.color[1] : "var(--secondary-text-color)"}"></ha-icon>
          <div class="main" data-more="${dev.status}">
            <div class="name"><span class="t">${esc(dev.name)}</span>${chip}</div>
            <div class="sub" title="${esc(sub)}">${esc(sub)}</div>
            ${planTxt ? `<div class="plan">${esc(planTxt)}</div>` : ""}
            ${trendText ? `<div class="plan">${trendText} ${logToggle}</div>${logOpen ? logText : ""}` : ""}
          </div>
          <div class="right" title="${esc(budgetTitle)}">
            <div class="power-budget">
              <div class="pb-item">
                <span class="pb-label">Leistung</span>
                <span class="pw">${power != null ? fmtW(power) : "–"}</span>
              </div>
              <div class="pb-item">
                <span class="pb-label">Budget aktuell</span>
                <span class="pb-budget ${budgetNow == null ? "" : budgetNow < 0 ? "negative" : budgetOk ? "positive" : ""}">${fmtW(budgetNow)}</span>
              </div>
              ${this._config.show_mode ? this._modeSelect(dev.mode, "", a.geraetetyp === "heater") : ""}
              ${this._config.show_settings !== false && dev.settings.length ? `<button class="gear ${open ? "open" : ""}" data-gear="${dev.id}" title="Einstellungen"><ha-icon icon="mdi:cog"></ha-icon></button>` : ""}
            </div>
          </div>
        </div>
        ${open ? this._settings(dev.settings, dev.name) : ""}
        </div>`;
    }).join("")}</div>`;
  }

  _timeline(d) {
    const plan = this._st(d.ents["sensor:plan"]);
    const hours = (plan?.attributes?.stunden || []).slice();
    if (!hours.length) return `<div class="timeline"><div class="empty">Keine Prognose verfügbar.</div></div>`;
    const now = Date.now();
    const horizon = new Date();
    horizon.setDate(horizon.getDate() + 2);
    horizon.setHours(0, 0, 0, 0);
    const visible = hours.filter(h => {
      const t = Date.parse(h.zeit);
      return t + 3600e3 > now && t < horizon.getTime();
    });
    // Do not draw zero-PV hours as full-width columns. Preserve a visible
    // separator for each consecutive gap, including the overnight interval.
    const cols = visible.filter(h => (Number(h.pv_w) || 0) > 0 ||
      Object.values(h.geraete || {}).some(w => Number(w) > 0));
    if (!cols.length) return `<div class="timeline"><div class="empty">Kein PV-Ertrag im Zeitraum.</div></div>`;
    const colorOf = name => name === "Speicher" ? BATTERY_GRADIENT : (d.devices.find(x => x.name === name)?.color || PALETTE[6]);
    const max = Math.max(...cols.map(h => Math.max(h.pv_w || 0, Object.values(h.geraete || {}).reduce((a, b) => a + b, 0))), 1);
    const used = new Set();
    const bars = [];
    const labels = [];
    const step = cols.length > 16 ? 3 : cols.length > 8 ? 2 : 1;
    cols.forEach((h, i) => {
      const t = Date.parse(h.zeit);
      const elapsedHours = i ? Math.round((t - Date.parse(cols[i - 1].zeit)) / 3600e3) : 1;
      if (elapsedHours > 1) {
        const omitted = elapsedHours - 1;
        const from = new Date(Date.parse(cols[i - 1].zeit) + 3600e3);
        const to = new Date(t);
        const night = from.toDateString() !== to.toDateString() ||
          (from.getHours() >= 18 || to.getHours() <= 7);
        const label = night ? "Nacht" : "PV-Pause";
        const tooltip = `${omitted} h ohne PV-Ertrag (${from.toLocaleString("de-AT")} – ${to.toLocaleString("de-AT")})`;
        bars.push(`<div class="pv-break" title="${esc(tooltip)}"><span>${label}</span></div>`);
        labels.push(`<div class="pv-break-label">⋯</div>`);
      }
      const isNow = t <= now && now < t + 3600e3;
      const segs = Object.entries(h.geraete || {}).map(([name, w]) => {
        used.add(name);
        const g = colorOf(name);
        return `<div class="seg" title="${esc(name)}: ${fmtW(w)}" style="height:${(w / max) * 100}%;background:linear-gradient(to top,${g.join(",")})"></div>`;
      }).join("");
      const hour = new Date(t).toLocaleTimeString("de-AT", { hour: "2-digit" });
      bars.push(`<div class="col ${isNow ? "now" : ""}" title="${hour} Uhr – PV ${fmtW(h.pv_w)}, frei ${fmtW(h.frei_w)}">
          <div class="pv" style="height:${((h.pv_w || 0) / max) * 100}%"></div>${segs}</div>`);
      labels.push(`<div>${i % step === 0 || elapsedHours > 1 ? new Date(t).getHours() : ""}</div>`);
    });
    const legend = [`<span><i style="background:${grad(PV_GRADIENT)};opacity:.5"></i>PV-Prognose</span>`]
      .concat([...used].map(n => `<span><i style="background:${grad(colorOf(n))}"></i>${esc(n)}</span>`)).join("");
    const next = plan?.state && plan.state !== "–" ? `<div class="next">Als Nächstes: ${esc(plan.state)}</div>` : "";
    return `<div class="timeline"><div class="bars">${bars.join("")}</div><div class="labels">${labels.join("")}</div>
      <div class="legend">${legend}</div></div>${next}`;
  }

  // ── Render ────────────────────────────────────────────────────────────────
  _render() {
    if (!this._hass) return;
    const c = this._config;
    const d = this._data ?? collect(this._hass, c.hub);
    if (!d) {
      this.shadowRoot.innerHTML = `<style>${CARD_CSS}</style><ha-card><div class="empty">Kein smartify Energiemanager gefunden.</div></ha-card>`;
      return;
    }
    const title = c.title ?? d.name;
    const markup = `
      <style>${CARD_CSS}</style>
      <ha-card>
        ${title || d.ents["select:mode"] ? `<div class="title"><img class="sep-brand-icon" src="/smartify_energy/sep-logo.png" alt="Smartify Energy Pro Logo"><span>Smartify Energy Pro</span><span class="sp"></span>${this._modeSelect(d.ents["select:mode"])}
          ${c.show_settings !== false && d.hubSettings.length ? `<button class="gear ${this._open.has("hub") ? "open" : ""}" data-gear="hub" title="Einstellungen Energiemanager"><ha-icon icon="mdi:cog"></ha-icon></button>` : ""}</div>` : ""}
        ${this._open.has("hub") ? this._settings(d.hubSettings, d.name, "hub") : ""}
        ${c.show_header ? this._header(d) : ""}
        ${c.show_priorities ? `<div class="section"><span>Prioritäten</span><span>1 = hoher Vorrang · ziehen zum Sortieren</span></div>${this._devices(d)}` : ""}
        ${c.show_timeline ? `<div class="section"><span>PV-Plan</span><span>Heute + morgen</span></div>${this._timeline(d)}` : ""}
      </ha-card>`;
    const template = document.createElement("template");
    template.innerHTML = markup;
    patchChildren(this.shadowRoot, template.content);
    this._bind(d);
  }

  _bind(d) {
    this._boundData = d;
    if (this._eventsBound) return;
    this._eventsBound = true;
    const root = this.shadowRoot;
    root.addEventListener("click", e => {
      const el = e.target.closest?.("[data-log], [data-gear], [data-more], [data-press], select");
      if (!el) return;
      if (el.matches("select")) { e.stopPropagation(); return; }
      if (el.hasAttribute("data-log")) {
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
      } else if (el.dataset.press) {
        e.stopPropagation();
        this._hass.callService("button", "press", {entity_id: el.dataset.press});
      } else this._moreInfo(el.dataset.more);
    });
    root.addEventListener("change", e => {
      const el = e.target;
      if (el.dataset.select) this._hass.callService(el.dataset.select.split(".")[0], "select_option", {entity_id: el.dataset.select, option: el.value});
      else if (el.dataset.num && Number.isFinite(parseFloat(el.value))) this._hass.callService("number", "set_value", {entity_id: el.dataset.num, value: parseFloat(el.value)});
      else if (el.dataset.switch) this._hass.callService("switch", el.checked ? "turn_on" : "turn_off", {entity_id: el.dataset.switch});
      else if (el.dataset.time && el.value) this._hass.callService("time", "set_value", {entity_id: el.dataset.time, time: `${el.value}:00`});
    });
    root.addEventListener("pointerdown", e => {
      if (e.target.closest?.(".handle")) this._dragStart(e, this._boundData);
    });
  }

  // ── Drag & Drop (Maus + Touch, ohne externe Bibliothek) ──────────────────
  _dragStart(e, d) {
    const row = e.target.closest(".dev-wrap");
    const list = row?.parentElement;
    if (!row || !list) return;
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
      this._dragEnd(ev);
    };
    row.addEventListener("pointermove", move);
    row.addEventListener("pointerup", end);
    row.addEventListener("pointercancel", end);
  }

  _dragMove(e) {
    const g = this._drag;
    if (!g) return;
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

  async _dragEnd() {
    const g = this._drag;
    if (!g) return;
    const order = g.rows.map(r => r.dataset.wrap);
    const [moved] = order.splice(g.from, 1);
    order.splice(g.to, 0, moved);
    g.rows.forEach(r => { r.style.transform = ""; r.classList.remove("dragging"); });
    this._drag = null;
    if (g.to !== g.from) {
      await this._hass.callService(DOMAIN, "set_priority_order", { device_ids: order });
    }
    this._sig = "";
    this.hass = this._hass;
  }
}

customElements.define("smartify-energy-plan-card", SmartifyEnergyPlanCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "smartify-energy-plan-card",
  name: "smartify Energiemanager",
  description: "Überschuss, Prioritäten (Drag & Drop) und PV-Plan des smartify Energiemanagers.",
  preview: false,
});
console.info(`%c SMARTIFY-ENERGY-PLAN-CARD %c v${CARD_VERSION} `, "background:#00ACC1;color:#fff", "background:#333;color:#fff");

