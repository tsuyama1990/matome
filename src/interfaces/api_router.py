import logging
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic_core.core_schema import ValidationInfo

from src.application.pivot_workflow import PivotWorkflow
from src.application.sq3r_service import SQ3REngine, SQ3RService
from src.domain_models.pivot import PivotRequestPayload
from src.interfaces.dependencies import DIContainer, LLMProtocol
from src.interfaces.repository import DocumentRepositoryProtocol

router = APIRouter()


class UserAnswerPayload(BaseModel):
    user_answer: str = Field(..., max_length=5000, description="The user's answer.")

    @field_validator("user_answer")
    @classmethod
    def sanitize_answer(cls, v: str, info: ValidationInfo) -> str:
        _ = info  # use it to pass ruff argument check if needed
        if len(v) > 5000:
            msg = "Answer too long"
            raise ValueError(msg)
        if not v.strip():
            msg = "Answer cannot be empty"
            raise ValueError(msg)
        return v

    model_config = ConfigDict(extra="forbid")


logger = logging.getLogger(__name__)


def get_di_container(request: Request) -> DIContainer:
    """Dependency injection container resolver from app state."""
    if not hasattr(request.app.state, "container"):
        msg = "DI Container is not initialized in app state."
        logger.error(msg)
        raise HTTPException(status_code=500, detail=msg)

    container = request.app.state.container
    if not isinstance(container, DIContainer):
        msg = "DI Container invalid type in app state."
        logger.error(msg)
        raise HTTPException(status_code=500, detail=msg)

    return container


def get_sq3r_service(
    container: Annotated[DIContainer, Depends(get_di_container)],
) -> SQ3RService:
    try:
        llm = container.resolve(LLMProtocol)  # type: ignore[type-abstract]
        engine = SQ3REngine(llm=llm)
        return SQ3RService(engine=engine)
    except Exception as e:
        msg = "LLM not configured."
        raise HTTPException(status_code=500, detail=msg) from e


def get_repository(
    container: Annotated[DIContainer, Depends(get_di_container)],
) -> DocumentRepositoryProtocol:
    try:
        return container.resolve(DocumentRepositoryProtocol)  # type: ignore[type-abstract]
    except Exception as e:
        msg = "Repository not configured."
        raise HTTPException(status_code=500, detail=msg) from e


@router.get("/nodes/{node_id}/question")
async def get_node_question(
    node_id: str,
    service: Annotated[SQ3RService, Depends(get_sq3r_service)],
    repository: Annotated[DocumentRepositoryProtocol, Depends(get_repository)],
) -> dict[str, str]:
    try:
        node = repository.get_node_by_id(node_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail="Node not found.") from e

    question = await service.get_question(node)
    return {"question": question}


@router.post("/nodes/{node_id}/unlock")
async def unlock_node(
    node_id: str,
    payload: UserAnswerPayload,
    service: Annotated[SQ3RService, Depends(get_sq3r_service)],
    repository: Annotated[DocumentRepositoryProtocol, Depends(get_repository)],
) -> dict[str, Any]:
    try:
        node = repository.get_node_by_id(node_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail="Node not found.") from e

    feedback = await service.unlock_node(node, payload.user_answer)
    repository.save_node(node)

    return {
        "feedback": feedback,
        "is_unlocked": node.is_unlocked,
        "summarized_content": node.summarized_content,
    }


def get_pivot_workflow(
    container: Annotated[DIContainer, Depends(get_di_container)],
) -> PivotWorkflow:
    try:
        return container.resolve(PivotWorkflow)
    except Exception as e:
        msg = "Pivot workflow not configured."
        raise HTTPException(status_code=500, detail=msg) from e


@router.post("/documents/{document_id:uuid}/pivot")
async def pivot_document(
    document_id: uuid.UUID,
    payload: PivotRequestPayload,
    workflow: Annotated[PivotWorkflow, Depends(get_pivot_workflow)],
) -> dict[str, Any]:
    try:
        result = await workflow.execute(str(document_id), payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    else:
        return result
