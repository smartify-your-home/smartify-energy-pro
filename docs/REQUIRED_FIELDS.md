# Pflichtfelder und optionale Entitäten – SEP 0.2.21

Diese Übersicht unterscheidet **Formular-Pflichtfelder** und **Funktionsvoraussetzungen**. Ein Feld, das sich technisch leer speichern lässt, kann für eine bestimmte Automatik trotzdem notwendig sein.

**Legende:** **Pflicht** = muss zur Anlage bzw. zum Gerät angegeben werden; **Bedingt** = nur bei genutzter Zusatzfunktion erforderlich; **Optional** = ohne diese Angabe sind Grundfunktionen weiterhin möglich. Die Zahlenparameter im SEP-Zahnrad-Menü besitzen häufig bereits einen Standardwert und müssen nicht alle von Hand gesetzt werden.

## Energiemanager / Netz
| Feld | Status | Bedeutung |
|---|---|---|
| Name | Pflicht bei Ersteinrichtung | Anzeigename |
| Netzleistung/Netzbezug | Pflicht | Leistungssensor (W/kW) |
| Vorzeichen der Netzleistung | Pflicht | Richtige Interpretation von Bezug/Einspeisung |
| Regelintervall | Pflicht, voreingestellt | Regulärer Zyklus; Sensorereignisse können schneller reagieren |
| Getrennter Einspeisungssensor | Bedingt | Nur bei getrennten positiven Bezugs-/Einspeisungssensoren; Vorzeichenwahl wird dann ignoriert |
| Überschuss-Senken | Optional | Selbstständig geregelte zusätzliche Senken |

## Prognose und Batteriestrategie
| Feld | Status | Bedeutung |
|---|---|---|
| Prognoseintegration(en) | Optional, für Prognoseplanung erforderlich | Künftiger PV-Ertrag; gleiche Fläche nicht mehrfach zählen |
| Prognosesensor(en) | Optional / alternative Quelle | Ergänzung oder Ersatz, wenn entsprechend konfiguriert |
| Speicher-SoC | Bedingt | Für SoC-Grenzen und zielorientierte Speicherpriorität |
| Speicherleistung | Bedingt | Für Berücksichtigung tatsächlicher Ladung/Entladung im Leistungsbudget |
| Vorzeichen Speicherleistung | Bedingt, mit Standardwert | Bei konfigurierter Speicherleistung korrekt wählen |
| Nutzbare Speicherkapazität | Bedingt | Für Berechnung der bis zum Ziel-SoC fehlenden Energie |
| Batterie-Strategie, Minimum-/Ziel-SoC, Sicherheit | Optional, Standardwerte | Wirken nur bei konfigurierter Batteriestrategie und geeigneten Eingangswerten |

**Wichtig:** Ein Speicher-Ladesollwert ist noch nicht implementiert. Keine der obigen Entitäten bewirkt eine aktive Ladeleistungsregelung des Akkus.

## Haushaltsgerät
| Feld | Status | Bedeutung |
|---|---|---|
| Name | Pflicht | Gerätebezeichnung |
| Schaltbare Steckdose/Schalter | Pflicht | SEP schaltet diese Entität |
| Nennleistung | Pflicht, vorbelegt | Leistungsreservierung / Ersatzwert |
| Typische Programmdauer | Pflicht, vorbelegt | Planung |
| Leistungssensor | Optional, für zuverlässige Programmerkennung empfohlen | Tatsächliche Leistungsaufnahme |

## Pool
| Feld | Status | Bedeutung |
|---|---|---|
| Name, Schalter, Nennleistung | Pflicht | Grundsteuerung |
| Leistungssensor | Optional | Gemessene Leistungsaufnahme |
| Wassertemperatur | Optional | Temperaturabhängige Laufzeit, sonst feste Soll-Laufzeit |

## E-Auto / Wallbox
| Feld | Status | Bedeutung |
|---|---|---|
| Name, Strom-Sollwertentität, Ladefreigabe-Entität | Pflicht | Aktive Laderegelung |
| Min-/Max-Strom, Phasenzahl, Spannung | Pflicht, vorbelegt | Sichere Strom- und Leistungsgrenzen |
| Kapazität, Verbrauch (kWh/100 km), Wirkungsgrad | Pflicht im Formular, vorbelegt | Planung von Energie-/Kilometerzielen; für reines PV-Laden nicht alle rechnerisch notwendig |
| Ein-/Aus-Optionswerte | Bedingt | Erforderlich bei select/input_select als Ladefreigabe |
| Phasenwahl-Entität und Optionen für 1/3 Phasen | Bedingt | Nur wenn automatische Phasenumschaltung genutzt wird |
| Leistungssensor | Optional, empfohlen | Rückmeldung tatsächlicher Ladeleistung |
| Verbunden-Sensor | Optional | Erkennung eines angeschlossenen Autos |
| Verbindungs-Zustandswerte | Bedingt | Falls die verwendete Entität spezielle Zustände liefert |
| Fahrzeug-SoC | Optional | Maximal-SoC und genauere Zielplanung |
| Tagesplan-Entität | Bedingt | Für die Funktion „Tage-Konfigurator“ |

**Grenzen:** Die schnelle Stromanpassung arbeitet mit Messwerten und ganzzahligen Ampere-Schritten. Mindestladestrom, Abschaltverzögerung und Phasenwechsel-Sperre können Netzbezug verursachen.

## Heizstab / PV-Überschusssenke
| Feld | Status | Bedeutung |
|---|---|---|
| Schalter | **Pflicht** | `switch` oder `input_boolean`; bei Input-Boolean ein weiterer echter Aktor erforderlich |
| Wassertemperatur | **Pflicht** | `sensor` in °C; fehlender/ungültiger Wert führt zu AUS |
| Heizleistung | **Pflicht** | Watt-Nennleistung zur vollständigen PV-Startreservierung |
| Leistungssensor | Optional | Tatsächlich gemessene W/kW zur Vermeidung übervorsichtiger zusätzlicher Reservierung |
| Maximaltemperatur, Hysterese | Einstellbar | Standard 55 °C und 3 K |
| Start-/Stoppschwelle, Uhrzeit | Einstellbar | Standard 2200 W, 0 W, 10:00; **Momentanwert**, kein Mittelwert |
| Mindestlaufzeit / Mindestpause | Optional | Beide 0–120 min, Standard 0, nach Neustart erhalten; Temperatur-Sicherheit setzt Mindestlaufzeit außer Kraft |

## Wärmepumpe / Warmwasser-Boost
| Feld | Status | Bedeutung |
|---|---|---|
| Name, Boost-Art, Boost-Entität, Nennleistung | Pflicht | Boost-Ansteuerung und Leistungsbudget |
| WP-Leistungssensor | **Bedingt – für automatischen Boost notwendig** | Nachweis, dass die WP durchgehend ruht |
| Warmwasser aktiv (binary_sensor/input_boolean) | **Optional** | EIN verhindert erneute Boost-Auslösung während WW-Ladung; bei konfiguriertem aber ungültigem Signal wird der Start ausgesetzt |
| Warmwassertemperatursensor | **Bedingt – für automatischen Boost notwendig** | Temperaturprüfung vor neuem Start |
| Sonnenhöhe: Entität und Mindestgrenze | Bedingt | Nur wenn Sonnenhöhenfilter aktiviert und vollständig konfiguriert |
| Bewölkung aktuell/kommende Stunde und beide Grenzen | Bedingt | Nur wenn Bewölkungsfilter aktiviert und alle vier Angaben vorliegen |
| Filter-Aktiv-Schalter | Optional, standardmäßig aus | Zusatzprüfung vor Start |
| Boost-Temperatur, Hysterese, WP-Ruhezeit | Einstellbare Parameter mit Standardwerten | Gelten vor dem Start einer WW-Ladung |
| WW-Boost Mindestabstand (60–720 min) | Einstellbarer Geräteparameter, Standard 60 min | Dauerhafter Schutz vor mehr als einer Auslösung pro Stunde auch nach Neustart |

Die optionalen Wetterfilter werden bei fehlenden Entitäten/Grenzwerten ignoriert. Sind sie vollständig aktiviert, verhindern ungültige Messwerte den **Neustart**; laufende Boosts werden dadurch nicht abgebrochen.

## Hinweise zur Eingabemaske
- **[Pflicht]** markiert die im Formular technisch erforderlichen Angaben.
- **[Bedingt]** markiert Felder, die nur zusammen mit einer ausgewählten Zusatzfunktion erforderlich werden.
- **[Optional]** markiert Angaben, die für die Grundfunktion nicht nötig sind.
- Speichern ohne bedingt erforderliche Funktionssensoren kann möglich sein, obwohl die damit verbundene Automatik dann nicht arbeiten kann; insbesondere die beiden WP-Sensoren beachten.
