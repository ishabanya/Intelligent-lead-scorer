from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class CompanySize(str, Enum):
    STARTUP = "Startup (1-10)"
    SMALL = "Small (11-50)"
    MEDIUM = "Medium (51-200)"
    LARGE = "Large (201-1000)"
    ENTERPRISE = "Enterprise (1000+)"

class FundingStage(str, Enum):
    BOOTSTRAP = "Bootstrap"
    SEED = "Seed"
    SERIES_A = "Series A"
    SERIES_B = "Series B"
    SERIES_C = "Series C"
    SERIES_D_PLUS = "Series D+"
    IPO = "IPO"
    ACQUIRED = "Acquired"

class GrowthIndicators(BaseModel):
    hiring_velocity: Optional[int] = Field(None, description="New hires in last 90 days")
    job_openings: Optional[int] = None
    news_mentions: Optional[int] = Field(None, description="Mentions in last 30 days")
    funding_events: List[Dict[str, Any]] = Field(default_factory=list)
    expansion_signals: List[str] = Field(default_factory=list)
    website_traffic_trend: Optional[str] = Field(None, description="up/down/stable")

class TechnologySignals(BaseModel):
    current_stack: List[str] = Field(default_factory=list)
    recent_adoptions: List[Dict[str, datetime]] = Field(default_factory=list)
    integration_capabilities: List[str] = Field(default_factory=list)
    tech_spend_indicators: List[str] = Field(default_factory=list)

class SocialSignals(BaseModel):
    linkedin_followers: Optional[int] = None
    linkedin_engagement_rate: Optional[float] = None
    content_publishing_frequency: Optional[str] = None
    community_activity: List[str] = Field(default_factory=list)
    thought_leadership_signals: List[str] = Field(default_factory=list)

class CompanyIdentifiers(BaseModel):
    domain: str
    linkedin_url: Optional[HttpUrl] = None
    crunchbase_url: Optional[HttpUrl] = None
    crm_id: Optional[str] = None
    ein: Optional[str] = None
    duns_number: Optional[str] = None

class Company(BaseModel):
    id: Optional[str] = None
    
    # Basic identifiers
    identifiers: CompanyIdentifiers
    
    # Basic company information
    name: str
    description: Optional[str] = None
    tagline: Optional[str] = None
    founded_year: Optional[int] = None
    
    # Industry classification
    industry: Optional[str] = None
    sub_industry: Optional[str] = None
    naics_code: Optional[str] = None
    sic_code: Optional[str] = None
    
    # Size and structure
    size: Optional[CompanySize] = None
    employee_count: Optional[int] = None
    employee_count_range: Optional[str] = None
    
    # Financial information
    annual_revenue: Optional[float] = None
    revenue_range: Optional[str] = None
    funding_stage: Optional[FundingStage] = None
    total_funding: Optional[float] = None
    last_funding_amount: Optional[float] = None
    last_funding_date: Optional[datetime] = None
    valuation: Optional[float] = None
    
    # Location information
    headquarters: Optional[str] = None
    headquarters_city: Optional[str] = None
    headquarters_state: Optional[str] = None
    headquarters_country: Optional[str] = None
    office_locations: List[str] = Field(default_factory=list)
    
    # Growth and signals
    growth_indicators: GrowthIndicators = Field(default_factory=GrowthIndicators)
    technology_signals: TechnologySignals = Field(default_factory=TechnologySignals)
    social_signals: SocialSignals = Field(default_factory=SocialSignals)
    
    # Buying signals
    budget_indicators: List[str] = Field(default_factory=list)
    decision_maker_signals: Dict[str, Any] = Field(default_factory=dict)
    competitive_landscape: List[str] = Field(default_factory=list)
    pain_point_indicators: List[str] = Field(default_factory=list)
    
    # Web presence
    website_analysis: Dict[str, Any] = Field(default_factory=dict)
    seo_metrics: Dict[str, Any] = Field(default_factory=dict)
    
    # Contact information
    phone: Optional[str] = None
    email_domain: Optional[str] = None
    main_email: Optional[str] = None
    
    # Metadata
    data_sources: List[str] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=datetime.now)
    confidence_score: Optional[float] = Field(None, ge=0, le=1)
    
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        use_enum_values = True