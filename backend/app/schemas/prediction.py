from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Literal
from datetime import datetime


CONTENT_TYPES = ["reel", "image", "carousel"]
CREATOR_CATEGORIES = ["Technology", "Fitness", "Beauty", "Music", "Photography",
                       "Food", "Lifestyle", "Travel", "Fashion", "Comedy"]
ACCOUNT_TYPES = ["brand", "creator"]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

ContentTypeT = Literal["reel", "image", "carousel"]
CreatorCategoryT = Literal["Technology", "Fitness", "Beauty", "Music", "Photography",
                            "Food", "Lifestyle", "Travel", "Fashion", "Comedy"]
AccountTypeT = Literal["brand", "creator"]
DayOfWeekT = Literal["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


class ContentInput(BaseModel):
    # Literal types (not plain str) so FastAPI rejects any value outside the
    # trained model's known categories with a clear 422 error, instead of
    # silently passing an unrecognized category through to the model - where
    # OneHotEncoder(handle_unknown="ignore") would zero it out and produce a
    # prediction that looks valid but silently ignored part of the input.
    content_type: ContentTypeT = Field(..., description=f"One of {CONTENT_TYPES}")
    creator_category: CreatorCategoryT = Field(..., description=f"One of {CREATOR_CATEGORIES}")
    account_type: AccountTypeT = Field(..., description=f"One of {ACCOUNT_TYPES}")
    has_call_to_action: int = Field(..., ge=0, le=1, description="1 if the post includes a call-to-action, else 0")
    description_length: int = Field(..., ge=0, le=5000, description="Caption length in characters")
    hashtags: int = Field(..., ge=0, le=50)
    followers: int = Field(..., ge=0, le=500_000_000)
    account_age_months: float = Field(..., ge=0, le=300)
    historical_avg_views: int = Field(..., ge=0)
    historical_engagement_rate: float = Field(..., ge=0, le=100, description="Percent, e.g. 4.2")
    posting_hour: int = Field(..., ge=0, le=23)
    day_of_week: DayOfWeekT = Field(..., description=f"One of {DAYS}")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "content_type": "reel",
            "creator_category": "Technology",
            "account_type": "creator",
            "has_call_to_action": 1,
            "description_length": 120,
            "hashtags": 8,
            "followers": 25000,
            "account_age_months": 6,
            "historical_avg_views": 5000,
            "historical_engagement_rate": 4.2,
            "posting_hour": 19,
            "day_of_week": "Saturday",
        }
    })


class BatchContentInput(BaseModel):
    items: List[ContentInput]


class ImportantFactor(BaseModel):
    feature: str
    importance: float
    description: str


class TimeSlot(BaseModel):
    time_slot: str
    predicted_views: int
    delta_vs_current: int


class DayRanking(BaseModel):
    day: str
    predicted_views: int
    delta_vs_current: int
    is_current: bool


class HourRanking(BaseModel):
    hour: str
    predicted_views: int
    delta_vs_current: int
    is_current: bool


class PostingSchedule(BaseModel):
    best_day: str
    best_day_views: int
    best_hour: str
    best_hour_views: int
    current_day: str
    current_hour: str
    current_slot_views: int
    best_slot: str
    best_slot_views: int
    potential_gain: int
    top_time_slots: List[TimeSlot]
    day_rankings: List[DayRanking]
    hour_rankings: List[HourRanking]


class TestedLength(BaseModel):
    length: int
    predicted_views: int
    delta_vs_current: int
    is_current: bool


class CaptionStrategy(BaseModel):
    current_length: int
    optimal_length: int
    optimal_views: int
    potential_gain: int
    advice: str
    tested_lengths: List[TestedLength]


class TestedCount(BaseModel):
    count: int
    predicted_views: int
    delta_vs_current: int
    is_current: bool


class HashtagStrategy(BaseModel):
    current_count: int
    optimal_count: int
    optimal_views: int
    potential_gain: int
    advice: str
    tested_counts: List[TestedCount]


class PredictionResponse(BaseModel):
    performance_score: float
    performance_category: str
    model_category_prediction: str
    category_probabilities: Dict[str, float]
    confidence: float
    expected_views: int
    expected_engagement_rate: float
    important_factors: List[ImportantFactor]
    recommendations: List[str]
    posting_schedule: Optional[PostingSchedule] = None
    caption_strategy: Optional[CaptionStrategy] = None
    hashtag_strategy: Optional[HashtagStrategy] = None
    data_quality_notice: Optional[str] = None
    signal_detected: bool = True
    prediction_id: Optional[int] = None
    created_at: Optional[datetime] = None


class BatchPredictionResponse(BaseModel):
    results: List[PredictionResponse]


class ModelInfoResponse(BaseModel):
    best_model_names: Dict[str, str]
    test_metrics: dict
    top_feature_importance: List[Dict]
    feature_columns: List[str]
    random_state: int
    data_quality: Optional[dict] = None


class HistoryItem(BaseModel):
    id: int
    created_at: datetime
    content_type: str
    creator_category: str
    performance_score: float
    performance_category: str
    expected_views: int
    expected_engagement_rate: float

    model_config = ConfigDict(from_attributes=True)


class HistoryResponse(BaseModel):
    items: List[HistoryItem]
    total: int
