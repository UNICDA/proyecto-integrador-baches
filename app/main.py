from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Inicialización de la aplicación
app = FastAPI(
    title="API de Baches SDE",
    description="Sistema inteligente para la detección y priorización de baches",
    version="1.0.0"
)

# Configuración de CORS para permitir conexiones desde la app móvil y el panel web
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, esto debe cambiarse por los dominios reales
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Endpoint de comprobación de salud (Health Check)
@app.get("/health", tags=["Sistema"])
def health_check():
    return {
        "status": "online",
        "message": "La API de Baches SDE está operativa.",
        "services": {
            "database": "Pendiente de conexión",
            "celery": "Pendiente de conexión"
        }
    }

# Endpoint raíz
@app.get("/", include_in_schema=False)
def read_root():
    return {"message": "Bienvenido a la API de Baches SDE. Visita /docs para ver la documentación."}