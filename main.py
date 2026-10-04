import os
import tempfile
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
import cadquery as cq

app = FastAPI(
    title="ConverterCAD Engine - 2D to 3D API",
    description="API para geração de modelos 3D paramétricos (STEP e GLTF) a partir de parâmetros 2D.",
    version="1.0.0"
)

# --- MODELO DE DADOS DE ENTRADA (JSON) ---
class DimensionsInput(BaseModel):
    outer_diameter: float = Field(..., gt=0, description="Diâmetro externo da peça em mm", example=50.0)
    inner_diameter: float = Field(0.0, ge=0, description="Diâmetro do furo central em mm (0 se for sólido)", example=20.0)
    length: float = Field(..., gt=0, description="Comprimento total da peça em mm", example=100.0)
    chamfer: float = Field(0.0, ge=0, description="Tamanho do chanfro nas bordas externas em mm", example=1.5)

    class Config:
        schema_extra = {
            "example": {
                "outer_diameter": 60.0,
                "inner_diameter": 25.0,
                "length": 120.0,
                "chamfer": 2.0
            }
        }


# --- FUNÇÃO AUXILIAR PARA LIMPEZA DE ARQUIVOS TEMPORÁRIOS ---
def cleanup_temp_files(*file_paths: str):
    for path in file_paths:
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass


# --- LÓGICA DE MODELAGEM COM CADQUERY ---
def generate_cad_model(dims: DimensionsInput) -> cq.Workplane:
    """
    Cria uma peça cilíndrica/flange com furo e chanfros paramétricos.
    """
    # 1. Cria o cilindro base (extrusão a partir do diâmetro externo)
    result = cq.Workplane("XY").circle(dims.outer_diameter / 2.0).extrude(dims.length)

    # 2. Aplica furo central passante se houver diâmetro interno definido
    if dims.inner_diameter > 0:
        if dims.inner_diameter >= dims.outer_diameter:
            raise ValueError("O diâmetro interno deve ser menor que o diâmetro externo.")
        result = result.faces(">Z").hole(dims.inner_diameter)

    # 3. Aplica chanfro nas bordas extremas do diâmetro externo
    if dims.chamfer > 0:
        try:
            result = result.edges("|Z").chamfer(dims.chamfer)
        except Exception:
            # Caso a geometria não permita o chanfro exato, ignora para não interromper a API
            pass

    return result


# --- ENDPOINTS DA API ---

@app.get("/")
def read_root():
    return {"message": "API ConverterCAD Motor Paramétrico rodando com sucesso!"}


@app.post("/generate-step/", summary="Gera arquivo STEP para CAD")
def generate_step_file(dims: DimensionsInput, background_tasks: BackgroundTasks):
    """
    Recebe dimensões via JSON e retorna um arquivo .STEP pronto para download.
    """
    try:
        model = generate_cad_model(dims)

        # Cria arquivo temporário .step
        temp_dir = tempfile.gettempdir()
        step_filename = os.path.join(temp_dir, f"peca_{os.getpid()}_{id(dims)}.step")

        # Exporta via CadQuery
        cq.exporters.export(model, step_filename)

        # Adiciona tarefa em segundo plano para apagar o arquivo temporário após o envio
        background_tasks.add_task(cleanup_temp_files, step_filename)

        return FileResponse(
            path=step_filename,
            filename="modelo_peca_3d.step",
            media_type="application/octet-stream"
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao gerar modelo STEP: {str(e)}")


@app.post("/generate-gltf/", summary="Gera arquivo GLTF para visualização no App Android")
def generate_gltf_file(dims: DimensionsInput, background_tasks: BackgroundTasks):
    """
    Recebe dimensões via JSON e retorna um arquivo .GLTF para renderização 3D no celular.
    """
    try:
        model = generate_cad_model(dims)

        temp_dir = tempfile.gettempdir()
        gltf_filename = os.path.join(temp_dir, f"peca_{os.getpid()}_{id(dims)}.gltf")

        # Exporta formato GLTF otimizado para web/mobile
        cq.exporters.export(model, gltf_filename, exportType=cq.exporters.ExportTypes.GLTF)

        background_tasks.add_task(cleanup_temp_files, gltf_filename)

        return FileResponse(
            path=gltf_filename,
            filename="modelo_peca_3d.gltf",
            media_type="model/gltf+json"
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao gerar modelo GLTF: {str(e)}")
  
