from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.schemas.prediction import (
    ContentInput, BatchContentInput, PredictionResponse, BatchPredictionResponse,
    ModelInfoResponse, HistoryResponse, HistoryItem,
)
from app.database.db import get_db, PredictionHistory, User
from app.services import prediction_service
from app.services.auth import get_current_verified_user

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/predict", response_model=PredictionResponse)
def predict(payload: ContentInput, db: Session = Depends(get_db),
            user: User = Depends(get_current_verified_user)):
    try:
        result = prediction_service.run_prediction(payload.model_dump())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {e}")
    record = prediction_service.save_prediction(db, payload.model_dump(), result, user_id=user.id)
    result["prediction_id"] = record.id
    result["created_at"] = record.created_at
    return result


@router.post("/predict/batch", response_model=BatchPredictionResponse)
def predict_batch(payload: BatchContentInput, db: Session = Depends(get_db),
                   user: User = Depends(get_current_verified_user)):
    results = []
    for item in payload.items:
        try:
            result = prediction_service.run_prediction(item.model_dump())
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Prediction failed: {e}")
        record = prediction_service.save_prediction(db, item.model_dump(), result, user_id=user.id)
        result["prediction_id"] = record.id
        result["created_at"] = record.created_at
        results.append(result)
    return {"results": results}


@router.get("/model-info", response_model=ModelInfoResponse)
def model_info():
    try:
        return prediction_service.get_model_info()
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/prediction-history", response_model=HistoryResponse)
def prediction_history(limit: int = 50, offset: int = 0, db: Session = Depends(get_db),
                        user: User = Depends(get_current_verified_user)):
    query = db.query(PredictionHistory).filter(PredictionHistory.user_id == user.id) \
        .order_by(desc(PredictionHistory.created_at))
    total = query.count()
    rows = query.offset(offset).limit(limit).all()
    return {"items": [HistoryItem.model_validate(r) for r in rows], "total": total}


@router.get("/prediction-history/{prediction_id}")
def prediction_detail(prediction_id: int, db: Session = Depends(get_db),
                       user: User = Depends(get_current_verified_user)):
    row = db.query(PredictionHistory).filter(
        PredictionHistory.id == prediction_id, PredictionHistory.user_id == user.id
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Prediction not found")
    import json
    return {
        "id": row.id,
        "created_at": row.created_at,
        "input": json.loads(row.input_json),
        "result": json.loads(row.result_json),
    }
