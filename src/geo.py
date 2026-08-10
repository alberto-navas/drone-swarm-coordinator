"""
Utilidades geograficas compartidas: distancias y desplazamientos locales
sobre WGS84.

`offset_point` usa una aproximacion de plano tangente local (norte/este en
metros -> delta de lat/lon), no una proyeccion geodesica completa. Es valida
a la escala de operacion de un enjambre (formaciones y separaciones de
decenas/cientos de metros, areas de mision de pocos kilometros); no esta
pensada para desplazamientos largos donde la curvatura terrestre y la
convergencia de meridianos dejen de ser despreciables.
"""

import math

from src.model import GeoPoint

_EARTH_RADIUS_M = 6_371_000.0


def haversine_distance_m(a: GeoPoint, b: GeoPoint) -> float:
    """Distancia en metros entre dos puntos WGS84, sobre una Tierra esferica."""
    phi1, phi2 = math.radians(a.lat), math.radians(b.lat)
    d_phi = math.radians(b.lat - a.lat)
    d_lambda = math.radians(b.lon - a.lon)
    sin_a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * _EARTH_RADIUS_M * math.asin(math.sqrt(sin_a))


def offset_point(origin: GeoPoint, north_m: float, east_m: float) -> GeoPoint:
    """Punto resultante de desplazar `origin` north_m/east_m metros (plano tangente local)."""
    d_lat = north_m / _EARTH_RADIUS_M
    d_lon = east_m / (_EARTH_RADIUS_M * math.cos(math.radians(origin.lat)))
    return GeoPoint(lat=origin.lat + math.degrees(d_lat), lon=origin.lon + math.degrees(d_lon))


def bearing_deg(a: GeoPoint, b: GeoPoint) -> float:
    """Rumbo inicial en grados (0 = norte, sentido horario) para ir de a a b."""
    phi1, phi2 = math.radians(a.lat), math.radians(b.lat)
    d_lambda = math.radians(b.lon - a.lon)
    x = math.sin(d_lambda) * math.cos(phi2)
    y = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(d_lambda)
    # Doble modulo: un rumbo que matematicamente es 0 puede llegar aqui
    # como un valor negativo minusculo por redondeo de coma flotante
    # (p.ej. -1e-15), y "% 360.0" de eso da 360.0 en vez de 0.0 (el propio
    # 360.0 no es multiplo exacto representable de ese resto). Repetir el
    # modulo normaliza ese caso limite a 0.0.
    return (math.degrees(math.atan2(x, y)) % 360.0) % 360.0


def centroid(points: list[GeoPoint]) -> GeoPoint:
    """Centroide simple (media aritmetica de lat/lon); suficiente a escala de enjambre local."""
    return GeoPoint(
        lat=sum(p.lat for p in points) / len(points),
        lon=sum(p.lon for p in points) / len(points),
    )
