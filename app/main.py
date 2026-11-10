from fastapi import FastAPI

app = FastAPI(
    title="API Baches SDE",
    description="Sistema inteligente para detección de baches en Santo Domingo Este",
    version="1.0.0"
)

@app.get("/")
def read_root():
    return {"mensaje": "API de Baches SDE operativa y conectada"}