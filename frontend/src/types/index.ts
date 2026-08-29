export const CONTENT_TYPES = ["reel", "image", "carousel"] as const
export const CREATOR_CATEGORIES = ["Technology", "Fitness", "Beauty", "Music", "Photography", "Food", "Lifestyle", "Travel", "Fashion", "Comedy"] as const
export const ACCOUNT_TYPES = ["brand", "creator"] as const
export const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"] as const

export interface ContentInput {
  content_type: string
  creator_category: string
  account_type: string
  has_call_to_action: number
  description_length: number
  hashtags: number
  followers: number
  account_age_months: number
  historical_avg_views: number
  historical_engagement_rate: number
  posting_hour: number
  day_of_week: string
}

export interface ImportantFactor {
  feature: string
  importance: number
  description: string
}

export interface PredictionResponse {
  performance_score: number
  performance_category: 'Low' | 'Moderate' | 'Good' | 'Excellent'
  model_category_prediction: string
  category_probabilities: Record<string, number>
  confidence: number
  expected_views: number
  expected_engagement_rate: number
  important_factors: ImportantFactor[]
  recommendations: string[]
  data_quality_notice?: string | null
  signal_detected: boolean
  prediction_id?: number
  created_at?: string
}

export interface HistoryItem {
  id: number
  created_at: string
  content_type: string
  creator_category: string
  performance_score: number
  performance_category: string
  expected_views: number
  expected_engagement_rate: number
}

export interface HistoryResponse {
  items: HistoryItem[]
  total: number
}

export interface ModelInfoResponse {
  best_model_names: Record<string, string>
  test_metrics: Record<string, any>
  top_feature_importance: { feature: string; importance: number }[]
  feature_columns: string[]
  random_state: number
  data_quality?: {
    signal_detected: boolean
    notice: string
    max_abs_feature_target_correlation: number
    category_roc_auc: number
  }
}
