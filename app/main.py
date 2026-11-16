from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Importar los routers que acabamos de crear
from app.api.v1 import catalogs, users

app = FastAPI(
    title="API de Baches SDE",
    description="Sistema inteligente para la detección y priorización de baches",
    version="1.0.0"
)

# Configuración de CORS para permitir solicitudes desde cualquier origen (útil para desarrollo y pruebas)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Integrar los routers (Step 4)
app.include_router(catalogs.router, prefix="/api/v1/catalogs", tags=["Catálogos"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Usuarios"])

# Endpoint de prueba y salud del sistema
@app.get("/health", tags=["Sistema"])
def health_check():
    return {
        "status": "online",
        "message": "La API de Baches SDE está operativa."
    }

@app.get("/", include_in_schema=False)
def read_root():
    return {"message": "Bienvenido a la API de Baches SDE. Visita /docs para ver la documentación."}