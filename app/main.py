from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Importar los routers que acabamos de crear
from app.api.v1 import auth, catalogs, users

app = FastAPI(
    title="API de Baches SDE",
    description="Sistema inteligente para la detección y priorización de baches",
    version="1.0.0"
)

# Manejador para errores HTTP lanzados manualmente (ej. 400, 401, 404)
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "code": exc.status_code,
            "message": str(exc.detail),
            "details": None
        }
    )

# Manejador para errores de validación de Pydantic (Cambiado a 400 Bad Request)
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content={
            "error": True,
            "code": 400,
            "message": "Error de validación en los datos enviados.",
            "details": jsonable_encoder(exc.errors())
        }
    )

# ... tus otros imports ...

# Manejador GLOBAL para cualquier error no controlado (Fuerza el formato en errores 500)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Imprimimos el error real en la terminal para que el desarrollador pueda depurarlo
    print(f"Error interno no controlado: {str(exc)}") 
    
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "code": 500,
            "message": "Ha ocurrido un error interno en el servidor.",
            # Envolvemos el detalle del error en nuestra estructura estándar de lista
            "details": [{"msg": str(exc)}] 
        }
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
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Autenticación"])

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