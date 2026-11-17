from pydantic import BaseModel, ConfigDict
from typing import Optional

class RouteResponse(BaseModel):
    id: int
    name: str
    buffer_meters: float
    priority_weight: float
    road_geometry: str

    model_config = ConfigDict(from_attributes=True)