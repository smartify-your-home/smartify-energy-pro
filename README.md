# Smartify Energy Pro

**PV-Überschuss intelligent verteilen – mit Prioritäten, Geräteprogrammen, Batteriespeicher und Home-Assistant-Dashboard.**

**Aktueller Quellcode-Stand: 0.3.29** · Home-Assistant-Integration: `smartify_energy` · Oberfläche: Deutsch / Englisch

> **Versionshinweis:** Die Versionsnummer beschreibt den Repository-Stand. In HACS erscheint eine neue Version erst, wenn der zugehörige GitHub-Release-Tag erfolgreich veröffentlicht und von HACS erkannt wurde. [Veröffentlichte Versionen ansehen](https://github.com/smartify-your-home/smartify-energy-pro/releases).

## Was macht Smartify Energy Pro?

SEP verteilt den verfügbaren PV-Überschuss nach einstellbarer Priorität. Das System berücksichtigt den Netzsaldo, bereits laufende und reservierte Verbraucher sowie – abhängig von der Konfiguration – den Batteriespeicher und eine PV-Prognose. Die Geräte werden in Home Assistant eingerichtet und über eine integrierte Lovelace-Karte bedient.

| Funktion | Verhalten |
| --- | --- |
| **Waschmaschine und Geschirrspüler** | Programm erkennen, auf PV-Freigabe warten, nach Freigabe ohne Unterbrechung weiterlaufen; Spätstart und Sofortstart möglich |
| **Heizpausen-Reservierung** | Nach der ersten erkannten Heizphase wahlweise weniger Leistung für spätere Heizphasen reservieren; pro Gerät einstellbar |
| **Wäschetrockner** | Eigenes Profil; Modelle ohne zuverlässigen Wiederanlauf werden nicht durch Abschalten der Steckdose gesteuert |
| **Heizstab** | PV-abhängige Leistungs- und Temperaturregelung, Hysterese, Start- und Stoppschwellen; temperaturgeregelter Handbetrieb möglich |
| **Wärmepumpe / Warmwasser** | PV-WW-Boost mit optionalen Wetter-, Sonnenwinkel- und Prognosebedingungen sowie Schutz vor Mehrfachauslösung |
| **Elektroauto / Wallbox** | PV-Laderegelung, Priorisierung und Berücksichtigung von Ladebedingungen |
| **Batteriespeicher** | Ladezustand und Ladeleistung bei der Priorisierung berücksichtigen; keine automatische direkte Speichersteuerung durch SEP |
| **Prioritäten** | Geräte per Drag & Drop ordnen; nachrangige regelbare Verbraucher können für höher priorisierte Starts zurückgenommen werden |
| **Dashboard** | Gerätestatus, Leistungsbudget, Prioritäten, Einstellungen, Diagnose und PV-Plan in einer Karte |

## Neueste Änderungen

### 0.3.28 – HACS-Infoseite überarbeitet

Die bisherige Sammlung historischer Versionshinweise wurde durch eine aktuelle, kompakte Funktionsübersicht ersetzt. Technische Details und frühere Änderungen stehen weiterhin in den verlinkten Dokumentationen und im Changelog. **Keine Änderung der Regelungslogik gegenüber 0.3.26.**

### 0.3.26 – Restreservierung während Heizpausen

Für Waschmaschine und Geschirrspüler gibt es **Restreservierung in Heizpausen** (`pause_reservation_pct`). Der Wert ist pro Gerät von **0 bis 100 %** in 10-%-Schritten einstellbar; **Standard 100 %**.

- **Vor der ersten abgeschlossenen Heizphase:** volle Nennleistung reservieren.
- **Danach, in Heizpausen:** mindestens den eingestellten Prozentsatz der Nennleistung reservieren; der tatsächlich gemessene Verbrauch zählt immer.
- **Bei erneutem Heizen:** mindestens die tatsächliche Leistungsaufnahme berücksichtigen.
- **Bei fehlendem oder ungültigem Leistungssensor:** volle Nennleistung reservieren.
- **Trockner:** unverändert, mit eigener Dauerlastreservierung.

**Beispiel:** Geschirrspüler mit 2.000 W Nennleistung und 50 % Restreservierung hält in einer Heizpause 1.000 W für spätere Heizphasen zurück. Das übrige Budget kann die nachrangige Waschmaschine früher freigeben. **Achtung:** Wenn beide gleichzeitig heizen oder die PV-Leistung sinkt, kann zusätzlicher Netzbezug entstehen. Die Einstellung ist keine Netzbezugsbegrenzung.

### 0.3.25 – Diagnose H / T / B

Die Prioritätenkarte zeigt drei Startprüfungen mit farbigem Status und einem aufklappbaren **Log ▾** mit Ist-/Sollwerten:

| Anzeige | Bedeutung |
| --- | --- |
| **H – Historie** | Genügend Messdaten für das konfigurierte langfristige Mittel vorhanden |
| **T – Trend** | Zwei Trendfenster vorhanden und Trendprüfung für die PV-Freigabe bestanden |
| **B – Budget** | Aktuelles **und** gemitteltes Gerätebudget decken die erforderliche Startleistung |

Ein grüner Haken nach B erscheint nur, wenn alle drei Bedingungen erfüllt sind. **Sofortstart, Sofortfenster und Spätstart** haben eigene Ausnahmeregeln. Die Trendbewertung ist keine garantierte PV-Wetterprognose.

**Alle Änderungen und technischen Release Notes:** [CHANGELOG.md](CHANGELOG.md).

## So funktioniert der Start eines Haushaltsgeräts

1. Steckdose und Leistungssensor werden dem Gerät in SEP zugeordnet.
2. Das Programm wird **am Gerät** gestartet; SEP erkennt es anhand der Leistungsaufnahme.
3. Reicht der PV-Überschuss noch nicht aus, kann SEP das Programm vor der Freigabe warten lassen – **nur bei Geräten, die nach Stromunterbrechung zuverlässig fortsetzen können**.
4. Für den regulären PV-Start prüft SEP das verfügbare Gerätebudget, dessen Langzeitmittel und den Kurzzeittrend. Prioritäten und Leistungsreservierungen werden berücksichtigt.
5. Nach der Freigabe läuft das Programm weiter, auch wenn der PV-Überschuss später verschwindet. Das Programm wird nicht wegen einzelner Wolken abgeschaltet.
6. Nach Unterschreiten der einstellbaren Fertig-Leistung für die eingestellte Dauer wird das Programm als beendet erkannt. Ein neues Programm kann anschließend automatisch erkannt werden.

**Wichtig:** Die Startschwelle für ein Haushaltsgerät ist mindestens die höhere der beiden Einstellungen **Nennleistung** und **Mindestüberschuss**. Die Heizpausen-Reservierung beeinflusst die nachrangigen Geräte, **nicht** diese eigene Startschwelle.

## Installation über HACS

1. **HACS → Benutzerdefinierte Repositories** öffnen.
2. `https://github.com/smartify-your-home/smartify-energy-pro` als Kategorie **Integration** hinzufügen.
3. **Smartify Energy Pro** installieren beziehungsweise aktualisieren.
4. **Home Assistant neu starten**, damit geänderter Python-Code aktiv wird.
5. Unter **Einstellungen → Geräte & Dienste → Integration hinzufügen** Smartify Energy Pro einrichten. Geräte und benötigte Entitäten hinzufügen.
6. Das Dashboard neu laden, damit die aktuelle Karte angezeigt wird.

### Dashboard-Karte

Die Integration stellt die Karte bereit; sie kann bei Bedarf auch manuell eingefügt werden:

```yaml
type: custom:smartify-energy-plan-card
```

Die Karte bietet die Prioritätenliste, Geräteeinstellungen mit Hilfetexten, Statusanzeigen und den Prognoseplan. Für einzelne Einstellungen das Zahnrad des betreffenden Geräts verwenden.

## Wichtige Hinweise

- **Geräte mit nicht wiederanlaufenden Programmen** dürfen nicht durch eine schaltbare Steckdose angehalten werden. Bei Trocknern dafür das entsprechende nicht unterbrechbare Profil wählen.
- **50 % Restreservierung** kann Programme früher starten lassen, erhöht aber das Risiko von gleichzeitigem Heizen und Netzbezug. Wer möglichst keinen zusätzlichen Netzbezug möchte, lässt **100 %** eingestellt.
- **Messsensoren und Prioritäten** müssen korrekt eingerichtet sein. Ungültige Leistungsmessungen werden bei der Heizpausen-Reservierung konservativ behandelt.
- **H/T/B** gelten für reguläre PV-Starts. Ein ausdrücklich erzwungener oder zeitlich fälliger Start kann auch Netzstrom verwenden.
- **Hauptschalter Aus** ist kein elektrischer Not-Aus. Bei Haushaltsgeräten werden die Steckdosen zur manuellen Bedienung freigegeben.
- **Heizstab Manuell** kann temperaturgeregelt auch mit Netzstrom heizen. Temperaturbegrenzung und geeignete elektrische Absicherung bleiben erforderlich.
- Nach Updates die **Release Notes** prüfen, Home Assistant neu starten und die Dashboard-Seite neu laden.

## Dokumentation

- [Alle Versionen und Release Notes](CHANGELOG.md)
- [Aktueller Funktionsstand und technische Grenzen](docs/FUNCTIONS.md)
- [SEP-Funktionen und Details](docs/SEP_CURRENT.md)
- [Update-Anleitung und Funktionstest](docs/UPDATE.md)
- [Benötigte und optionale Entitäten](docs/REQUIRED_FIELDS.md)
- [Migration von SEM v3](docs/SEM_ENTITY_MIGRATION.md)
- [Fehler melden oder Funktionen vorschlagen](https://github.com/smartify-your-home/smartify-energy-pro/issues)

**Projekt:** [smartify-your-home/smartify-energy-pro](https://github.com/smartify-your-home/smartify-energy-pro)

## Kurztrend-Startbedingung (0.3.29)
Für den automatischen PV-Start muss der gerätespezifische Kurztrend-Mittelwert **immer mindestens den Sollwert** erreichen. Bei stärker fallendem Trend muss außerdem die Fortschreibung (Kurzzeit-Ø plus Änderung zwischen den Trendfenstern) mindestens den Sollwert erreichen. Ein steigender oder neutraler Trend ersetzt keinen ausreichenden Kurzzeit-Mittelwert. In der SEP-Karte zeigt T diese strengere Prüfung. History (H) und aktuelles Budget (B) sind weiterhin zusätzlich erforderlich.
