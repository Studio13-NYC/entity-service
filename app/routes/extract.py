from fastapi import APIRouter
from app.models import ExtractRequest, ExtractResponse
from app.services.extractor import extract_entities

router = APIRouter()


@router.post("/extract", response_model=ExtractResponse)
def extract(req: ExtractRequest):
    label_filter = req.labels or None
    opts = req.options
    use_aliases = True if opts is None else opts.use_aliases
    use_model = False if opts is None else opts.use_model
    entities = extract_entities(
        req.text,
        label_filter,
        use_aliases=use_aliases,
        use_model=use_model,
        schema=req.entity_schema,
    )
    return ExtractResponse(entities=entities)
