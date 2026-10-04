from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import cadquery as cq
import tempfile
import os

app = FastAPI(
    title="ConverterCAD Engine - 2D to 3D API",
    description="API para geração de modelos 3D paramétricos (STEP e GLTF) a partir de parâmetros 2D.",
    version="1.0.0"
)

# Modelo de dados de entrada recebido do app
class DimensionsInput(BaseModel):
    outer_diameter: float = 60.0
    inner_diameter: float = 20.0
    length: float = 100.0
    chamfer: float = 2.0

@app.get("/")
def read_root():
    return {"status": "API ConverterCAD online e operacional"}

@app.post("/generate-gltf/")
def generate_gltf(data: DimensionsInput):
    try:
        # 1. Criação da geometria paramétrica com CadQuery
        result = (
            cq.Workplane("XY")
            .circle(data.outer_diameter / 2.0)
            .circle(data.inner_diameter / 2.0)
            .extrude(data.length)
            .edges(">Z or <Z")
            .chamfer(data.chamfer)
        )

        # 2. Criação de um ficheiro temporário para salvar o GLTF
        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, "modelo_3d.gltf")

        # 3. Exportação corrigida (o CadQuery deteta o formato pela extensão .gltf)
        cq.exporters.export(result, file_path)

        # 4. Retorna o ficheiro gerado
        return FileResponse(
            path=file_path,
            filename="modelo_3d.gltf",
            media_type="model/gltf+json"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar modelo GLTF: {str(e)}")


@app.post("/generate-step/")
def generate_step(data: DimensionsInput):
    try:
        result = (
            cq.Workplane("XY")
            .circle(data.outer_diameter / 2.0)
            .circle(data.inner_diameter / 2.0)
            .extrude(data.length)
            .edges(">Z or <Z")
            .chamfer(data.chamfer)
        )

        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, "modelo_3d.step")

        cq.exporters.export(result, file_path)

        return FileResponse(
            path=file_path,
            filename="modelo_3d.step",
            media_type="application/STEP"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar modelo STEP: {str(e)}")
