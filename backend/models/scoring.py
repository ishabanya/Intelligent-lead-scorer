from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from enum import Enum

class ScoreCategory(str, Enum):
    COMPANY_FIT = "company_fit"
    GROWTH_INDICATORS = "growth_indicators"
    TECHNOLOGY_FIT = "technology_fit"
    ENGAGEMENT_SIGNALS = "engagement_signals"
    TIMING_SIGNALS = "timing_signals"
    BUYING_SIGNALS = "buying_signals"

class ScoringWeights(BaseModel):
    company_fit: float = Field(0.25, ge=0, le=1)
    growth_indicators: float = Field(0.20, ge=0, le=1)
    technology_fit: float = Field(0.15, ge=0, le=1)
    engagement_signals: float = Field(0.15, ge=0, le=1)
    timing_signals: float = Field(0.15, ge=0, le=1)
    buying_signals: float = Field(0.10, ge=0, le=1)
    
    def validate_weights(self):
        total = sum([
            self.company_fit,
            self.growth_indicators,
            self.technology_fit,
            self.engagement_signals,
            self.timing_signals,
            self.buying_signals
        ])
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0, got {total}")

class IdealCustomerProfile(BaseModel):
    target_industries: List[str] = Field(default_factory=list)
    company_size_min: Optional[int] = None
    company_size_max: Optional[int] = None
    revenue_min: Optional[float] = None
    revenue_max: Optional[float] = None
    target_technologies: List[str] = Field(default_factory=list)
    target_roles: List[str] = Field(default_factory=list)
    geographic_regions: List[str] = Field(default_factory=list)
    funding_stages: List[str] = Field(default_factory=list)
    
    # Negative indicators (companies to avoid)
    excluded_industries: List[str] = Field(default_factory=list)
    excluded_technologies: List[str] = Field(default_factory=list)

class ScoringRule(BaseModel):
    name: str
    category: ScoreCategory
    condition: Dict[str, Any]
    score_impact: float = Field(ge=-100, le=100)
    weight: float = Field(1.0, ge=0, le=1)
    description: Optional[str] = None

class IndustrySpecificRules(BaseModel):
    industry: str
    scoring_weights: ScoringWeights
    specific_rules: List[ScoringRule] = Field(default_factory=list)
    icp_adjustments: Dict[str, Any] = Field(default_factory=dict)

class QualificationThresholds(BaseModel):
    hot_threshold: float = Field(80, ge=0, le=100)
    warm_threshold: float = Field(60, ge=0, le=100)
    cold_threshold: float = Field(40, ge=0, le=100)
    min_data_quality: float = Field(50, ge=0, le=100)

class ScoreExplanation(BaseModel):
    category: ScoreCategory
    score: float
    max_score: float
    factors: List[Dict[str, Any]] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)

class ScoringModel(BaseModel):
    name: str = "Default Lead Scoring Model"
    version: str = "1.0"
    
    # Core configuration
    weights: ScoringWeights = Field(default_factory=ScoringWeights)
    icp: IdealCustomerProfile = Field(default_factory=IdealCustomerProfile)
    thresholds: QualificationThresholds = Field(default_factory=QualificationThresholds)
    
    # Rules engine
    global_rules: List[ScoringRule] = Field(default_factory=list)
    industry_rules: List[IndustrySpecificRules] = Field(default_factory=list)
    
    # Scoring parameters
    max_score: float = Field(100, ge=1)
    normalize_scores: bool = True
    apply_data_quality_penalty: bool = True
    
    def get_default_rules(self) -> List[ScoringRule]:
        return [
            ScoringRule(
                name="Target Industry Match",
                category=ScoreCategory.COMPANY_FIT,
                condition={"field": "industry", "operator": "in", "value": "target_industries"},
                score_impact=20,
                description="Company is in target industry"
            ),
            ScoringRule(
                name="Ideal Company Size",
                category=ScoreCategory.COMPANY_FIT,
                condition={"field": "employee_count", "operator": "between", "min": "size_min", "max": "size_max"},
                score_impact=15,
                description="Company size matches ICP"
            ),
            ScoringRule(
                name="Recent Funding",
                category=ScoreCategory.GROWTH_INDICATORS,
                condition={"field": "last_funding_date", "operator": "within_days", "value": 180},
                score_impact=15,
                description="Recently received funding"
            ),
            ScoringRule(
                name="High Hiring Velocity",
                category=ScoreCategory.GROWTH_INDICATORS,
                condition={"field": "hiring_velocity", "operator": "gt", "value": 5},
                score_impact=10,
                description="Actively hiring (growth signal)"
            ),
            ScoringRule(
                name="Technology Stack Match",
                category=ScoreCategory.TECHNOLOGY_FIT,
                condition={"field": "tech_stack", "operator": "intersects", "value": "target_technologies"},
                score_impact=12,
                description="Uses complementary technologies"
            ),
            ScoringRule(
                name="Decision Maker Job Postings",
                category=ScoreCategory.BUYING_SIGNALS,
                condition={"field": "job_postings", "operator": "contains_roles", "value": "target_roles"},
                score_impact=25,
                description="Hiring for relevant decision-making roles"
            ),
            ScoringRule(
                name="Competitor Technology",
                category=ScoreCategory.TIMING_SIGNALS,
                condition={"field": "tech_stack", "operator": "contains_competitor", "value": True},
                score_impact=8,
                description="Currently uses competitor solution"
            ),
            ScoringRule(
                name="Website Traffic Growth",
                category=ScoreCategory.ENGAGEMENT_SIGNALS,
                condition={"field": "website_traffic_trend", "operator": "eq", "value": "up"},
                score_impact=5,
                description="Growing web presence"
            )
        ]

class LeadScore(BaseModel):
    total_score: float = Field(ge=0, le=100)
    category_scores: Dict[ScoreCategory, float] = Field(default_factory=dict)
    explanations: List[ScoreExplanation] = Field(default_factory=list)
    qualification_status: str
    confidence: float = Field(ge=0, le=1)
    data_quality_impact: float = 0
    applied_rules: List[str] = Field(default_factory=list)
    
    # Recommendations
    improvement_suggestions: List[str] = Field(default_factory=list)
    next_actions: List[str] = Field(default_factory=list)
    outreach_timing: Optional[str] = None
    outreach_approach: Optional[str] = None