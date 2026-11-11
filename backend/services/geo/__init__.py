"""Real geography for ResQ Nexus: roads, facilities, population and zones.

* ``distance``   - haversine distance and nearest-first sorting (pure maths, no data).
* ``osm``        - Overpass API client with on-disk JSON caching.
* ``roads``      - OpenStreetMap road network for a bounding box (OSMnx), cached as GraphML,
                   with travel times by road type and nearest-node snapping.
* ``facilities`` - hospitals, clinics, fire and police stations, schools / community halls
                   (potential shelters) from OpenStreetMap, as editable resources.
* ``population`` - WorldPop 1 km raster (downloaded separately) or an estimate from
                   OSM building counts.
* ``zones``      - H3 hexagons covering an incident area, each a ``ZoneAssessment``.

Network access happens only in the ``fetch_*`` / ``download_*`` functions; everything
else reads the caches under ``data/geo/``.
"""
from services.geo.distance import EARTH_RADIUS_KM, bounding_box, haversine_km, sort_by_distance

__all__ = ["EARTH_RADIUS_KM", "bounding_box", "haversine_km", "sort_by_distance"]
