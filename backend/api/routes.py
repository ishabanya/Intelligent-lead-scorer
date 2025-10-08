from fastapi import APIRouter, HTTPException, UploadFile, File, Query, BackgroundTasks
from typing import List, Optional, Dict, Any
import asyncio
import csv
import io
import json
from datetime import datetime

from ..models.lead import Lead, QualificationStatus
from ..models.scoring import LeadScore
from ..services.scraper import CompanyScraper
from ..services.enrichment import DataEnrichmentService
from ..services.scorer import LeadScoringEngine
from ..services.qualifier import LeadQualificationEngine

router = APIRouter()

# Initialize services
scraper = CompanyScraper()
enrichment_service = DataEnrichmentService()
scoring_engine = LeadScoringEngine()
qualification_engine = LeadQualificationEngine()

# This would be replaced with a proper database in production
leads_storage: Dict[str, Lead] = {}

@router.post("/leads/scrape", tags=["Lead Processing"])
async def scrape_company_data(
    domain: Optional[str] = None,
    linkedin_url: Optional[str] = None
):
    """
    Scrape company data from website or LinkedIn
    
    - **domain**: Company domain (e.g., "example.com")
    - **linkedin_url**: LinkedIn company page URL
    """
    if not domain and not linkedin_url:
        raise HTTPException(
            status_code=400, 
            detail="Either domain or linkedin_url must be provided"
        )
    
    try:
        # Extract domain from LinkedIn URL if not provided
        if not domain and linkedin_url:
            company_name = linkedin_url.split("/company/")[-1].split("/")[0]
            domain = f"{company_name}.com"
        
        # Perform scraping
        scraping_results = await scraper.scrape_company_data(domain, linkedin_url)
        
        return {
            "success": True,
            "domain": domain,
            "scraping_results": {
                source: {
                    "success": result.success,
                    "data": result.data if result.success else None,
                    "error": result.error
                }
                for source, result in scraping_results.items()
            }
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Scraping failed: {str(e)}"
        )

@router.post("/leads/enrich", tags=["Lead Processing"])
async def enrich_and_score_lead(lead_data: dict):
    """
    Enrich lead data and calculate intelligence score
    
    - **lead_data**: Basic lead information including domain and company_name
    """
    try:
        # Create lead object
        lead = Lead(**lead_data)
        lead.id = f"lead_{len(leads_storage) + 1}"
        
        # Enrich the lead
        enriched_lead = await enrichment_service.enrich_lead(lead)
        
        # Score the lead
        lead_score = scoring_engine.score_lead(enriched_lead)
        enriched_lead.lead_score = lead_score.total_score
        enriched_lead.qualification_status = QualificationStatus(lead_score.qualification_status)
        enriched_lead.score_breakdown = dict(lead_score.category_scores)
        
        # Qualify the lead
        qualification_result = qualification_engine.qualify_lead(enriched_lead)
        
        # Store the lead
        leads_storage[enriched_lead.id] = enriched_lead
        
        return {
            "success": True,
            "lead": enriched_lead.dict(),
            "scoring_details": lead_score.dict(),
            "qualification_analysis": qualification_result
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Enrichment failed: {str(e)}"
        )

@router.post("/leads/bulk-process", tags=["Lead Processing"])
async def bulk_process_leads_from_csv(file: UploadFile = File(...)):
    """
    Process multiple leads from CSV upload
    
    Expected CSV columns: domain, company_name (optional), industry (optional)
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    try:
        # Read and parse CSV
        content = await file.read()
        csv_reader = csv.DictReader(io.StringIO(content.decode('utf-8')))
        
        # Create lead objects
        leads_to_process = []
        for i, row in enumerate(csv_reader):
            if 'domain' in row and row['domain'].strip():
                lead_data = {
                    "domain": row['domain'].strip(),
                    "company_name": row.get('company_name', '').strip() or row['domain'].split('.')[0].title()
                }
                
                # Add optional fields
                if 'industry' in row and row['industry'].strip():
                    lead_data['industry'] = row['industry'].strip()
                if 'headquarters' in row and row['headquarters'].strip():
                    lead_data['headquarters'] = row['headquarters'].strip()
                
                lead = Lead(**lead_data)
                lead.id = f"bulk_lead_{len(leads_storage) + i + 1}"
                leads_to_process.append(lead)
        
        if not leads_to_process:
            raise HTTPException(status_code=400, detail="No valid leads found in CSV")
        
        # Process leads in batches (limit for demo)
        batch_size = min(20, len(leads_to_process))
        leads_batch = leads_to_process[:batch_size]
        
        # Enrich all leads concurrently
        enriched_leads = await enrichment_service.batch_enrich_leads(leads_batch)
        
        # Score and qualify each lead
        processed_results = []
        for lead in enriched_leads:
            try:
                # Score the lead
                lead_score = scoring_engine.score_lead(lead)
                lead.lead_score = lead_score.total_score
                lead.qualification_status = QualificationStatus(lead_score.qualification_status)
                lead.score_breakdown = dict(lead_score.category_scores)
                
                # Qualify the lead
                qualification_result = qualification_engine.qualify_lead(lead)
                
                # Store the lead
                leads_storage[lead.id] = lead
                
                processed_results.append({
                    "lead_id": lead.id,
                    "company_name": lead.company_name,
                    "domain": lead.domain,
                    "score": lead.lead_score,
                    "qualification": lead.qualification_status.value,
                    "processing_status": "success"
                })
            
            except Exception as e:
                processed_results.append({
                    "company_name": lead.company_name,
                    "domain": lead.domain,
                    "processing_status": "failed",
                    "error": str(e)
                })
        
        return {
            "success": True,
            "total_uploaded": len(leads_to_process),
            "processed_count": len([r for r in processed_results if r.get("processing_status") == "success"]),
            "failed_count": len([r for r in processed_results if r.get("processing_status") == "failed"]),
            "results": processed_results
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Bulk processing failed: {str(e)}"
        )

@router.get("/leads", tags=["Lead Management"])
async def get_leads(
    score_min: Optional[float] = Query(None, ge=0, le=100, description="Minimum lead score"),
    score_max: Optional[float] = Query(None, ge=0, le=100, description="Maximum lead score"),
    qualification: Optional[str] = Query(None, description="Qualification status filter"),
    industry: Optional[str] = Query(None, description="Industry filter"),
    search: Optional[str] = Query(None, description="Search company names"),
    sort_by: Optional[str] = Query("score", description="Sort by: score, name, date"),
    sort_order: Optional[str] = Query("desc", description="Sort order: asc, desc"),
    limit: Optional[int] = Query(50, ge=1, le=1000, description="Number of results"),
    offset: Optional[int] = Query(0, ge=0, description="Pagination offset")
):
    """
    Get filtered and sorted list of leads
    """
    # Start with all leads
    filtered_leads = list(leads_storage.values())
    
    # Apply filters
    if score_min is not None:
        filtered_leads = [l for l in filtered_leads if l.lead_score and l.lead_score >= score_min]
    
    if score_max is not None:
        filtered_leads = [l for l in filtered_leads if l.lead_score and l.lead_score <= score_max]
    
    if qualification:
        filtered_leads = [l for l in filtered_leads 
                         if l.qualification_status and l.qualification_status.value == qualification]
    
    if industry:
        filtered_leads = [l for l in filtered_leads 
                         if l.industry and industry.lower() in l.industry.lower()]
    
    if search:
        search_lower = search.lower()
        filtered_leads = [l for l in filtered_leads 
                         if search_lower in l.company_name.lower() or search_lower in l.domain.lower()]
    
    # Apply sorting
    if sort_by == "score":
        filtered_leads.sort(key=lambda x: x.lead_score or 0, reverse=(sort_order == "desc"))
    elif sort_by == "name":
        filtered_leads.sort(key=lambda x: x.company_name.lower(), reverse=(sort_order == "desc"))
    elif sort_by == "date":
        filtered_leads.sort(key=lambda x: x.created_at, reverse=(sort_order == "desc"))
    
    # Apply pagination
    total_count = len(filtered_leads)
    paginated_leads = filtered_leads[offset:offset + limit]
    
    return {
        "leads": [
            {
                "id": lead.id,
                "company_name": lead.company_name,
                "domain": lead.domain,
                "industry": lead.industry,
                "lead_score": lead.lead_score,
                "qualification_status": lead.qualification_status.value if lead.qualification_status else None,
                "employee_count": lead.metrics.employee_count,
                "headquarters": lead.headquarters,
                "last_enriched": lead.last_enriched.isoformat() if lead.last_enriched else None,
                "created_at": lead.created_at.isoformat()
            }
            for lead in paginated_leads
        ],
        "pagination": {
            "total_count": total_count,
            "offset": offset,
            "limit": limit,
            "has_next": offset + limit < total_count,
            "has_prev": offset > 0
        }
    }

@router.get("/leads/{lead_id}", tags=["Lead Management"])
async def get_lead_details(lead_id: str):
    """
    Get detailed information for a specific lead
    """
    if lead_id not in leads_storage:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    lead = leads_storage[lead_id]
    
    # Generate fresh qualification analysis
    qualification_result = qualification_engine.qualify_lead(lead)
    
    return {
        "lead": lead.dict(),
        "qualification_analysis": qualification_result
    }

@router.get("/leads/{lead_id}/recommendations", tags=["Lead Intelligence"])
async def get_outreach_recommendations(lead_id: str):
    """
    Get personalized outreach recommendations for a lead
    """
    if lead_id not in leads_storage:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    lead = leads_storage[lead_id]
    qualification_result = qualification_engine.qualify_lead(lead)
    
    # Generate comprehensive recommendations
    recommendations = {
        "outreach_strategy": qualification_result.get("outreach_strategy", {}),
        "action_plan": qualification_result.get("action_plan", {}),
        "email_templates": _generate_email_templates(lead, qualification_result),
        "call_scripts": _generate_call_scripts(lead, qualification_result),
        "content_recommendations": _get_content_recommendations(lead),
        "optimal_timing": _get_optimal_timing(lead),
        "competitive_positioning": _get_competitive_positioning(lead)
    }
    
    return recommendations

@router.post("/leads/export", tags=["Data Export"])
async def export_leads(
    lead_ids: List[str],
    format: str = Query("csv", description="Export format: csv or json"),
    include_details: bool = Query(False, description="Include detailed analysis")
):
    """
    Export selected leads in CSV or JSON format
    """
    if format not in ["csv", "json"]:
        raise HTTPException(status_code=400, detail="Format must be 'csv' or 'json'")
    
    # Get valid leads
    export_leads = [leads_storage[lead_id] for lead_id in lead_ids if lead_id in leads_storage]
    
    if not export_leads:
        raise HTTPException(status_code=404, detail="No valid leads found")
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    if format == "csv":
        output = io.StringIO()
        
        if include_details:
            fieldnames = [
                'id', 'company_name', 'domain', 'industry', 'lead_score', 'qualification_status',
                'employee_count', 'headquarters', 'technologies', 'contacts', 'data_quality_score',
                'last_enriched', 'created_at'
            ]
        else:
            fieldnames = [
                'company_name', 'domain', 'industry', 'lead_score', 'qualification_status',
                'employee_count', 'headquarters'
            ]
        
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for lead in export_leads:
            row_data = {
                'company_name': lead.company_name,
                'domain': lead.domain,
                'industry': lead.industry or '',
                'lead_score': lead.lead_score or 0,
                'qualification_status': lead.qualification_status.value if lead.qualification_status else '',
                'employee_count': lead.metrics.employee_count or '',
                'headquarters': lead.headquarters or ''
            }
            
            if include_details:
                row_data.update({
                    'id': lead.id,
                    'technologies': ', '.join(lead.tech_stack.technologies) if lead.tech_stack.technologies else '',
                    'contacts': len(lead.contacts),
                    'data_quality_score': lead.data_quality_score or 0,
                    'last_enriched': lead.last_enriched.isoformat() if lead.last_enriched else '',
                    'created_at': lead.created_at.isoformat()
                })
            
            writer.writerow(row_data)
        
        return {
            "success": True,
            "format": "csv",
            "data": output.getvalue(),
            "filename": f"leads_export_{timestamp}.csv",
            "count": len(export_leads)
        }
    
    else:  # JSON format
        export_data = []
        for lead in export_leads:
            lead_data = lead.dict()
            if include_details:
                # Add qualification analysis for detailed export
                qualification_result = qualification_engine.qualify_lead(lead)
                lead_data['qualification_analysis'] = qualification_result
            
            export_data.append(lead_data)
        
        return {
            "success": True,
            "format": "json",
            "data": export_data,
            "filename": f"leads_export_{timestamp}.json",
            "count": len(export_leads)
        }

# Helper functions
def _generate_email_templates(lead: Lead, qualification_result: Dict) -> List[Dict]:
    """Generate personalized email templates"""
    templates = []
    
    qualification = lead.qualification_status
    
    if qualification == QualificationStatus.HOT:
        templates.append({
            "type": "immediate_outreach",
            "subject": f"Quick question about {lead.company_name}'s growth initiatives",
            "preview": f"Noticed {lead.company_name} is scaling rapidly...",
            "body": f"""Hi {{name}},

I noticed {lead.company_name} has been experiencing significant growth in the {lead.industry or 'technology'} space{', especially with your recent hiring surge' if lead.buying_signals.recent_hiring else ''}.

Companies similar to yours have achieved 40-60% efficiency improvements and 3x faster time-to-market using our platform.

Would you be open to a brief 15-minute conversation this week to explore how this might apply to {lead.company_name}?

Best regards,
{{your_name}}""",
            "tone": "direct",
            "urgency": "high"
        })
    
    elif qualification == QualificationStatus.WARM:
        templates.append({
            "type": "value_introduction",
            "subject": f"How {lead.company_name} can accelerate growth",
            "preview": f"Sharing insights relevant to {lead.industry or 'your industry'}...",
            "body": f"""Hi {{name}},

I've been following {lead.company_name}'s progress in the {lead.industry or 'technology'} space and wanted to share some insights that might be valuable.

We've helped similar companies in {lead.industry or 'your industry'} achieve:
• 50% reduction in manual processes
• 3x faster customer acquisition
• 25% improvement in team productivity

I'd love to share a brief case study of how a company like yours implemented these improvements.

Would you be interested in a 20-minute conversation next week?

Best regards,
{{your_name}}""",
            "tone": "consultative",
            "urgency": "medium"
        })
    
    return templates

def _generate_call_scripts(lead: Lead, qualification_result: Dict) -> List[Dict]:
    """Generate call scripts"""
    scripts = []
    
    if lead.qualification_status == QualificationStatus.HOT:
        scripts.append({
            "type": "discovery_call",
            "opening": f"Hi {{name}}, I'm calling about {lead.company_name}'s growth initiatives. I noticed you've been expanding rapidly - is now a good time to chat?",
            "value_prop": f"We help companies like {lead.company_name} streamline their operations during growth phases",
            "questions": [
                f"What are the biggest challenges {lead.company_name} faces with your current growth rate?",
                "How are you currently handling [specific process related to our solution]?",
                "What would ideal efficiency look like for your team?"
            ],
            "closing": "Would it make sense to schedule a brief demo to show you exactly how this works?"
        })
    
    return scripts

def _get_content_recommendations(lead: Lead) -> List[Dict]:
    """Get content recommendations"""
    content = []
    
    if lead.industry:
        content.append({
            "type": "industry_report",
            "title": f"{lead.industry} Growth Trends 2024",
            "description": "Industry-specific insights and benchmarks"
        })
    
    if lead.metrics.employee_count:
        if lead.metrics.employee_count < 100:
            content.append({
                "type": "scaling_guide",
                "title": "Scaling from Startup to Growth Stage",
                "description": "Operational best practices for growing companies"
            })
    
    return content

def _get_optimal_timing(lead: Lead) -> Dict:
    """Get optimal outreach timing"""
    timing = {"urgency": "medium", "best_days": ["Tuesday", "Wednesday", "Thursday"], "best_times": ["10 AM", "2 PM"]}
    
    if lead.qualification_status == QualificationStatus.HOT:
        timing["urgency"] = "high"
        timing["recommendation"] = "Reach out within 24 hours"
    elif lead.qualification_status == QualificationStatus.WARM:
        timing["recommendation"] = "Reach out within 48-72 hours"
    else:
        timing["recommendation"] = "Add to nurture sequence"
    
    return timing

def _get_competitive_positioning(lead: Lead) -> Dict:
    """Get competitive positioning insights"""
    positioning = {}
    
    # Analyze tech stack for competitive insights
    competitor_tools = []
    if lead.tech_stack.marketing_tools:
        competitors = ['hubspot', 'salesforce', 'marketo']
        competitor_tools = [tool for tool in lead.tech_stack.marketing_tools if any(comp in tool.lower() for comp in competitors)]
    
    if competitor_tools:
        positioning["current_solutions"] = competitor_tools
        positioning["differentiation_points"] = [
            "Better integration capabilities",
            "More cost-effective pricing",
            "Faster implementation"
        ]
    
    return positioning