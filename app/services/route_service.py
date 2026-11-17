from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.users import RoadRoute
from app.schemas.route_schema import RouteResponse

class RouteService:
    @staticmethod
    def get_all_routes(db: Session) -> list[RouteResponse]:
        """
        Consulta las rutas viales y convierte la geometría binaria de PostGIS a formato texto (WKT).
        """
        routes = db.query(
            RoadRoute.id,
            RoadRoute.name,
            RoadRoute.buffer_meters,
            RoadRoute.priority_weight,
            func.ST_AsText(RoadRoute.road_geometry).label("road_geometry")
        ).order_by(RoadRoute.id).all()
        
        return routes