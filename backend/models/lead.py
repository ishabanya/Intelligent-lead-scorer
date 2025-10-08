from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class QualificationStatus(str, Enum):
    HOT = "Hot"
    WARM = "Warm"
    COLD = "Cold"
    UNQUALIFIED = "Unqualified"

class RevenueRange(str, Enum):
    STARTUP = "0-1M"
    SMALL = "1M-10M"
    MEDIUM = "10M-100M"
    LARGE = "100M-1B"
    ENTERPRISE = "1B+"

class ContactInfo(BaseModel):
    name: Optional[str] = None
    title: Optional[str] = None
    email: Optional[str] = None
    linkedin_url: Optional[HttpUrl] = None
    phone: Optional[str] = None

class CompanyMetrics(BaseModel):
    employee_count: Optional[int] = None
    revenue_range: Optional[RevenueRange] = None
    growth_rate: Optional[float] = Field(None, ge=0, le=100)
    funding_amount: Optional[float] = None
    funding_stage: Optional[str] = None
    last_funding_date: Optional[datetime] = None

class TechnologyStack(BaseModel):
    technologies: List[str] = Field(default_factory=list)
    marketing_tools: List[str] = Field(default_factory=list)
    sales_tools: List[str] = Field(default_factory=list)
    analytics_tools: List[str] = Field(default_factory=list)

class BuyingSignals(BaseModel):
    job_postings: List[str] = Field(default_factory=list)
    recent_hiring: Optional[int] = None
    budget_indicators: List[str] = Field(default_factory=list)
    decision_maker_changes: bool = False
    expansion_signals: List[str] = Field(default_factory=list)

class Lead(BaseModel):
    id: Optional[str] = None
    company_name: str
    domain: str
    industry: Optional[str] = None
    sub_industry: Optional[str] = None
    
    # Contact information
    contacts: List[ContactInfo] = Field(default_factory=list)
    
    # Company metrics
    metrics: CompanyMetrics = Field(default_factory=CompanyMetrics)
    
    # Technology and tools
    tech_stack: TechnologyStack = Field(default_factory=TechnologyStack)
    
    # Buying signals
    buying_signals: BuyingSignals = Field(default_factory=BuyingSignals)
    
    # Scoring and qualification
    lead_score: Optional[float] = Field(None, ge=0, le=100)
    qualification_status: Optional[QualificationStatus] = None
    score_breakdown: Dict[str, float] = Field(default_factory=dict)
    
    # Data quality and metadata
    data_quality_score: Optional[float] = Field(None, ge=0, le=100)
    completeness_percentage: Optional[float] = Field(None, ge=0, le=100)
    last_enriched: Optional[datetime] = None
    data_sources: List[str] = Field(default_factory=list)
    
    # Additional insights
    competitor_analysis: Dict[str, Any] = Field(default_factory=dict)
    outreach_recommendations: List[str] = Field(default_factory=list)
    next_actions: List[str] = Field(default_factory=list)
    
    # Location information
    headquarters: Optional[str] = None
    locations: List[str] = Field(default_factory=list)
    
    # Social and web presence
    website_traffic_rank: Optional[int] = None
    social_media_presence: Dict[str, str] = Field(default_factory=dict)
    
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        use_enum_values = True