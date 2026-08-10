"""
Mapa animado (Leaflet real) para el panel web: la trayectoria de cada dron
se dibuja progresivamente con el tiempo, y cada conflicto de separacion
detectado aparece como marcador en el punto medio entre los dos drones
implicados, en el instante exacto en que se detecto.

El motor de simulacion trabaja en ticks (segundos de mision desde el
arranque), no en fechas de calendario: se proyectan a partir de una fecha
de referencia arbitraria (`_TICK_EPOCH`) solo porque TimestampedGeoJson
exige timestamps ISO8601 para reproducir la animacion; la fecha en si no
tiene ningun significado.

Import de folium a nivel de modulo, igual que en el proyecto hermano
Maritime Domain Awareness: este modulo entero solo existe para construir
mapas Folium.
"""

import html
from datetime import UTC, datetime, timedelta

from folium import Map
from folium.plugins import TimestampedGeoJson

from src.model import GeoPoint, SimulationState

_DRONE_COLOR = "#2563eb"
_CONFLICT_COLOR = "#dc2626"
_TICK_EPOCH = datetime(2026, 1, 1, tzinfo=UTC)
_PERIOD = "PT1S"  # un fotograma por tick simulado (1 tick = 1 segundo de mision)


def _tick_time(tick: int) -> str:
    return (_TICK_EPOCH + timedelta(seconds=tick)).isoformat()


def _bounds(history: list[SimulationState]) -> list[list[float]] | None:
    lats = [d.position.lat for state in history for d in state.drones]
    lons = [d.position.lon for state in history for d in state.drones]
    if not lats:
        return None
    return [[min(lats), min(lons)], [max(lats), max(lons)]]


def _midpoint(a: GeoPoint, b: GeoPoint) -> GeoPoint:
    return GeoPoint(lat=(a.lat + b.lat) / 2, lon=(a.lon + b.lon) / 2)


def _drone_features(history: list[SimulationState]) -> list[dict]:
    if not history:
        return []
    features = []
    for drone_id in [d.id for d in history[0].drones]:
        coords: list[list[float]] = []
        times: list[str] = []
        for state in history:
            position = next(d.position for d in state.drones if d.id == drone_id)
            coords.append([position.lon, position.lat])
            times.append(_tick_time(state.tick))

        # La estela: se dibuja progresivamente a medida que avanza el tiempo.
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": coords},
                "properties": {"times": times, "style": {"color": _DRONE_COLOR, "weight": 2, "opacity": 0.5}},
            }
        )
        # Un marcador por tick: la posicion "actual" del dron en ese instante.
        for coord, time in zip(coords, times, strict=True):
            features.append(
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": coord},
                    "properties": {
                        "times": [time],
                        "icon": "circle",
                        "iconstyle": {"fillColor": _DRONE_COLOR, "fillOpacity": 0.8, "stroke": "false", "radius": 4},
                        "popup": drone_id,
                    },
                }
            )
    return features


def _conflict_features(history: list[SimulationState]) -> list[dict]:
    features = []
    for previous, current in zip(history, history[1:], strict=False):
        new_events = current.conflicts[len(previous.conflicts) :]
        if not new_events:
            continue
        positions_by_id = {d.id: d.position for d in previous.drones}
        for event in new_events:
            midpoint = _midpoint(positions_by_id[event.drone_a_id], positions_by_id[event.drone_b_id])
            features.append(
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [midpoint.lon, midpoint.lat]},
                    "properties": {
                        "times": [_tick_time(event.tick)],
                        "icon": "circle",
                        "iconstyle": {
                            "fillColor": _CONFLICT_COLOR,
                            "fillOpacity": 0.9,
                            "stroke": "true",
                            "color": "black",
                            "weight": 1,
                            "radius": 8,
                        },
                        "popup": (
                            f"Conflicto: {event.drone_a_id} / {event.drone_b_id}<br>"
                            f"{event.distance_m:.1f} m (minimo: {event.min_separation_m:.0f} m)"
                        ),
                    },
                }
            )
    return features


def build_animated_map(history: list[SimulationState]) -> str:
    """Devuelve el HTML autocontenido de un mapa Folium animado, listo para embeber en una pagina."""
    bounds = _bounds(history)
    m = Map(location=bounds[0] if bounds else [0.0, 0.0], zoom_start=14, tiles="OpenStreetMap")
    if bounds:
        m.fit_bounds(bounds)

    features = _drone_features(history) + _conflict_features(history)
    TimestampedGeoJson(
        {"type": "FeatureCollection", "features": features},
        period=_PERIOD,
        add_last_point=False,
        auto_play=False,
        loop=False,
        max_speed=10,
        loop_button=True,
        date_options="HH:mm:ss",
        time_slider_drag_update=True,
    ).add_to(m)

    # Se envuelve a mano en un iframe (ver misma justificacion en el
    # proyecto hermano MDA) para embeber el mapa, que es un documento HTML
    # completo en si mismo, dentro de report.html sin que sus estilos y
    # scripts (Leaflet) choquen con los de la pagina.
    map_document = html.escape(m.get_root().render(), quote=True)
    return (
        f'<iframe srcdoc="{map_document}" style="width:100%;height:600px;border:1px solid #ccc;'
        f'border-radius:8px;" title="Mapa animado del enjambre"></iframe>'
    )
