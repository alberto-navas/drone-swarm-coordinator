"""
Internacionalizacion (ES/EN/DE) de todo lo que un humano lee: las
etiquetas del panel web y del CLI.

A diferencia de los proyectos hermanos (que ademas traducen descripciones
generadas dinamicamente por cada hallazgo, con un patron
message_key/message_params), este proyecto no tiene texto libre generado
por el motor de simulacion — todo lo que un humano lee es interfaz fija
(cabeceras, estados de un dron, nombre de un escenario), asi que basta con
diccionarios de etiquetas por idioma.

src/model.py, src/allocation.py, src/formation.py, src/conflict.py y
src/simulation.py nunca importan este modulo: no saben que existe el
concepto de idioma, igual que los detectores del proyecto hermano
Maritime Domain Awareness.
"""

SUPPORTED_LANGS = ("es", "en", "de")


def normalize_lang(lang: str | None) -> str:
    """Cualquier valor que no sea uno de los 3 idiomas soportados cae a "es", en vez de fallar."""
    return lang if lang in SUPPORTED_LANGS else "es"


_STATUS_LABELS: dict[str, dict[str, str]] = {
    "es": {"idle": "inactivo", "en_route": "en ruta", "on_station": "en posicion", "grounded": "en tierra"},
    "en": {"idle": "idle", "en_route": "en route", "on_station": "on station", "grounded": "grounded"},
    "de": {"idle": "inaktiv", "en_route": "unterwegs", "on_station": "in Position", "grounded": "am Boden"},
}


def status_label(status: str, lang: str) -> str:
    return _STATUS_LABELS[normalize_lang(lang)].get(status, status)


_SCENARIO_LABELS: dict[str, dict[str, str]] = {
    "es": {
        "cobertura": "Cobertura de area con conflicto forzado",
        "formacion": "Transito en formacion (sin conflicto forzado)",
    },
    "en": {
        "cobertura": "Area coverage with a forced conflict",
        "formacion": "Formation transit (no forced conflict)",
    },
    "de": {
        "cobertura": "Flaechenabdeckung mit erzwungenem Konflikt",
        "formacion": "Formationsflug (ohne erzwungenen Konflikt)",
    },
}


def scenario_label(scenario_id: str, lang: str) -> str:
    return _SCENARIO_LABELS[normalize_lang(lang)].get(scenario_id, scenario_id)


UI_LABELS: dict[str, dict[str, str]] = {
    "es": {
        "index_h1": "Coordinacion de un enjambre de drones propios",
        "index_subtitle": (
            "Reparto de mision, formacion y evitacion de colisiones para una flota propia "
            "— define tu propia mision o elige un escenario de demostracion, y velo simulado "
            "sobre un mapa real."
        ),
        "ticks_label": "Duracion de la simulacion (ticks; 1 tick = 1 segundo de mision)",
        "run_button": "Ejecutar",
        "limits_text": (
            "Esto es una herramienta de simulacion, planificacion y visualizacion: no controla "
            "drones reales ni se conecta a ningun hardware de vuelo."
        ),
        "back_link": "← Volver",
        "summary_drones": "drones",
        "summary_ticks": "ticks simulados",
        "summary_conflicts": "conflictos de separacion",
        "map_heading": "Mapa animado",
        "fleet_heading": "Estado final de la flota",
        "th_drone": "Dron",
        "th_status": "Estado",
        "th_battery": "Bateria",
        "th_position": "Posicion",
        "th_task": "Tarea",
        "conflicts_heading": "Conflictos de separacion",
        "conflicts_hint": (
            "Agrupados por pareja de drones: dos drones con rutas cercanas pueden quedar por "
            "debajo del minimo de seguridad durante varios ticks seguidos."
        ),
        "conflicts_empty": "No se detecto ningun conflicto de separacion durante la simulacion.",
        "th_pair": "Drones",
        "th_since": "Desde (tick)",
        "th_until": "Hasta (tick)",
        "th_occurrences": "Ocurrencias",
        "th_min_distance": "Distancia minima",
        "th_min_separation": "Minimo",
        "custom_mission_heading": "Construye tu propia mision",
        "custom_mission_hint": (
            "En vez de una demo ya cerrada, define tu propia flota y mision: cuantos drones, "
            "desde donde despegan, y que tienen que hacer."
        ),
        "custom_mission_label": "Mision personalizada",
        "field_drones": "Numero de drones",
        "field_launch": "Punto de despegue (latitud, longitud)",
        "field_mode": "Tipo de mision",
        "mode_area": "Cubrir un area",
        "mode_point": "Vigilar puntos",
        "mode_destination": "Llegar a destinos",
        "mode_formation": "Formacion (sin tarea)",
        "field_points": "Puntos (uno por linea: latitud,longitud)",
        "field_area_sw": "Esquina suroeste (latitud, longitud)",
        "field_area_ne": "Esquina noreste (latitud, longitud)",
        "field_formation_shape": "Forma",
        "formation_line": "Linea",
        "formation_v": "V",
        "formation_grid": "Rejilla",
        "field_spacing": "Separacion entre drones (m)",
        "field_leader": "Lider (opcional, p.ej. drone-1; vacio = centroide del grupo)",
        "field_min_separation": "Separacion minima de seguridad (m)",
    },
    "en": {
        "index_h1": "Coordinating a swarm of your own drones",
        "index_subtitle": (
            "Mission allocation, formation flying and collision avoidance for your own fleet "
            "— define your own mission or pick a demo scenario, and see it simulated on a "
            "real map."
        ),
        "ticks_label": "Simulation duration (ticks; 1 tick = 1 second of mission time)",
        "run_button": "Run",
        "limits_text": (
            "This is a simulation, planning and visualization tool: it does not control real "
            "drones or connect to any flight hardware."
        ),
        "back_link": "← Back",
        "summary_drones": "drones",
        "summary_ticks": "simulated ticks",
        "summary_conflicts": "separation conflicts",
        "map_heading": "Animated map",
        "fleet_heading": "Final fleet status",
        "th_drone": "Drone",
        "th_status": "Status",
        "th_battery": "Battery",
        "th_position": "Position",
        "th_task": "Task",
        "conflicts_heading": "Separation conflicts",
        "conflicts_hint": (
            "Grouped by drone pair: two drones on nearby routes can stay below the safety "
            "minimum for several ticks in a row."
        ),
        "conflicts_empty": "No separation conflict was detected during the simulation.",
        "th_pair": "Drones",
        "th_since": "Since (tick)",
        "th_until": "Until (tick)",
        "th_occurrences": "Occurrences",
        "th_min_distance": "Minimum distance",
        "th_min_separation": "Minimum",
        "custom_mission_heading": "Build your own mission",
        "custom_mission_hint": (
            "Instead of a canned demo, define your own fleet and mission: how many drones, "
            "where they launch from, and what they have to do."
        ),
        "custom_mission_label": "Custom mission",
        "field_drones": "Number of drones",
        "field_launch": "Launch point (latitude, longitude)",
        "field_mode": "Mission type",
        "mode_area": "Cover an area",
        "mode_point": "Watch points",
        "mode_destination": "Reach destinations",
        "mode_formation": "Formation (no task)",
        "field_points": "Points (one per line: latitude,longitude)",
        "field_area_sw": "Southwest corner (latitude, longitude)",
        "field_area_ne": "Northeast corner (latitude, longitude)",
        "field_formation_shape": "Shape",
        "formation_line": "Line",
        "formation_v": "V",
        "formation_grid": "Grid",
        "field_spacing": "Spacing between drones (m)",
        "field_leader": "Leader (optional, e.g. drone-1; empty = group centroid)",
        "field_min_separation": "Minimum safety separation (m)",
    },
    "de": {
        "index_h1": "Koordination eines eigenen Drohnenschwarms",
        "index_subtitle": (
            "Missionsverteilung, Formationsflug und Kollisionsvermeidung fuer eine eigene "
            "Flotte — definiere deine eigene Mission oder waehle ein Demo-Szenario, und sieh "
            "es auf einer echten Karte simuliert."
        ),
        "ticks_label": "Simulationsdauer (Ticks; 1 Tick = 1 Sekunde Missionszeit)",
        "run_button": "Starten",
        "limits_text": (
            "Dies ist ein Simulations-, Planungs- und Visualisierungswerkzeug: es steuert keine "
            "echten Drohnen und verbindet sich mit keiner Flughardware."
        ),
        "back_link": "← Zurueck",
        "summary_drones": "Drohnen",
        "summary_ticks": "simulierte Ticks",
        "summary_conflicts": "Abstandskonflikte",
        "map_heading": "Animierte Karte",
        "fleet_heading": "Endstatus der Flotte",
        "th_drone": "Drohne",
        "th_status": "Status",
        "th_battery": "Akku",
        "th_position": "Position",
        "th_task": "Aufgabe",
        "conflicts_heading": "Abstandskonflikte",
        "conflicts_hint": (
            "Gruppiert nach Drohnenpaar: zwei Drohnen auf nahen Routen koennen mehrere Ticks in "
            "Folge unter dem Sicherheitsminimum bleiben."
        ),
        "conflicts_empty": "Wahrend der Simulation wurde kein Abstandskonflikt festgestellt.",
        "th_pair": "Drohnen",
        "th_since": "Seit (Tick)",
        "th_until": "Bis (Tick)",
        "th_occurrences": "Vorkommen",
        "th_min_distance": "Minimaler Abstand",
        "th_min_separation": "Minimum",
        "custom_mission_heading": "Baue deine eigene Mission",
        "custom_mission_hint": (
            "Statt einer fertigen Demo definierst du deine eigene Flotte und Mission: wie viele "
            "Drohnen, von wo sie starten und was sie tun sollen."
        ),
        "custom_mission_label": "Eigene Mission",
        "field_drones": "Anzahl Drohnen",
        "field_launch": "Startpunkt (Breite, Laenge)",
        "field_mode": "Missionstyp",
        "mode_area": "Flaeche abdecken",
        "mode_point": "Punkte ueberwachen",
        "mode_destination": "Ziele erreichen",
        "mode_formation": "Formation (ohne Aufgabe)",
        "field_points": "Punkte (einer pro Zeile: Breite,Laenge)",
        "field_area_sw": "Suedwest-Ecke (Breite, Laenge)",
        "field_area_ne": "Nordost-Ecke (Breite, Laenge)",
        "field_formation_shape": "Form",
        "formation_line": "Linie",
        "formation_v": "V",
        "formation_grid": "Raster",
        "field_spacing": "Abstand zwischen Drohnen (m)",
        "field_leader": "Anfuehrer (optional, z.B. drone-1; leer = Gruppenschwerpunkt)",
        "field_min_separation": "Sicherheitsmindestabstand (m)",
    },
}


_CLI_LABELS: dict[str, dict[str, str]] = {
    "es": {
        "mission": "Mision",
        "drones": "drones",
        "tick": "tick",
        "conflicts_detected": "Conflictos de separacion detectados en toda la simulacion",
        "status": "estado",
        "battery": "bateria",
        "position": "pos",
        "task": "tarea",
    },
    "en": {
        "mission": "Mission",
        "drones": "drones",
        "tick": "tick",
        "conflicts_detected": "Separation conflicts detected across the whole simulation",
        "status": "status",
        "battery": "battery",
        "position": "pos",
        "task": "task",
    },
    "de": {
        "mission": "Mission",
        "drones": "Drohnen",
        "tick": "Tick",
        "conflicts_detected": "Waehrend der gesamten Simulation festgestellte Abstandskonflikte",
        "status": "Status",
        "battery": "Akku",
        "position": "Pos",
        "task": "Aufgabe",
    },
}


def cli_label(key: str, lang: str) -> str:
    return _CLI_LABELS[normalize_lang(lang)][key]
