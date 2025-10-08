from fastapi import FastAPI, HTTPException, UploadFile, File, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from typing import List, Optional, Dict, Any
import uvicorn
import asyncio
import csv
import io
import json
from datetime import datetime
import os

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.lead import Lead, QualificationStatus
from models.company import Company
from models.scoring import ScoringModel, LeadScore
from services.scraper import CompanyScraper
from services.enrichment import DataEnrichmentService
from services.scorer import LeadScoringEngine
from services.qualifier import LeadQualificationEngine
from services.insights import InsightsEngine
from services.competitive import CompetitiveIntelligenceEngine
from services.integrations import IntegrationManager, HubSpotIntegration, SalesforceIntegration

app = FastAPI(
    title="Intelligent Lead Scorer",
    description="Advanced lead generation and qualification system with intelligent scoring algorithms",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

# Initialize services
scraper = CompanyScraper()
enrichment_service = DataEnrichmentService()
scoring_engine = LeadScoringEngine()
qualification_engine = LeadQualificationEngine()
insights_engine = InsightsEngine()
competitive_engine = CompetitiveIntelligenceEngine()
integration_manager = IntegrationManager()

# In-memory storage (in production, use a proper database)
leads_db: Dict[str, Lead] = {}
analytics_data = {
    "total_leads": 0,
    "qualification_breakdown": {
        "Hot": 0,
        "Warm": 0,
        "Cold": 0,
        "Unqualified": 0
    },
    "average_score": 0,
    "recent_leads": []
}

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main frontend page"""
    try:
        with open(os.path.join(frontend_path, "index.html"), "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="""
        <html>
            <body>
                <h1>Intelligent Lead Scorer API</h1>
                <p>Backend is running. Frontend files not found.</p>
                <p>Visit <a href="/docs">/docs</a> for API documentation.</p>
            </body>
        </html>
        """)

@app.post("/api/leads/scrape")
async def scrape_lead(domain: str = None, linkedin_url: str = None):
    """Scrape company data from domain or LinkedIn URL"""
    if not domain and not linkedin_url:
        raise HTTPException(status_code=400, detail="Either domain or linkedin_url must be provided")
    
    try:
        # Use domain as primary, extract from LinkedIn URL if needed
        if not domain and linkedin_url:
            # Extract company name from LinkedIn URL for domain guessing
            company_name = linkedin_url.split("/company/")[-1].split("/")[0]
            domain = f"{company_name}.com"  # Simple heuristic
        
        # Scrape data
        scraping_results = await scraper.scrape_company_data(domain, linkedin_url)
        
        # Create basic lead from scraped data
        lead_data = {"domain": domain, "company_name": domain.split('.')[0].title()}
        
        # Merge scraped data
        for source, result in scraping_results.items():
            if result.success:
                if source == "website":
                    lead_data.update({
                        "company_name": result.data.get("company_name", lead_data["company_name"]),
                        "industry": result.data.get("industry"),
                        "headquarters": result.data.get("contact_info", {}).get("location")
                    })
                    if result.data.get("technologies"):
                        lead_data["tech_stack"] = {"technologies": result.data["technologies"]}
        
        lead = Lead(**lead_data)
        lead.id = f"lead_{len(leads_db) + 1}"
        
        return {
            "success": True,
            "lead": lead.dict(),
            "scraping_results": {k: {"success": v.success, "source": v.source} for k, v in scraping_results.items()}
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")

@app.post("/api/leads/enrich")
async def enrich_lead(lead_data: dict):
    """Enrich lead data and calculate score"""
    try:
        # Create lead object
        lead = Lead(**lead_data)
        
        # Enrich the lead
        enriched_lead = await enrichment_service.enrich_lead(lead)
        
        # Score the lead
        lead_score = scoring_engine.score_lead(enriched_lead)
        
        # Qualify the lead
        qualification_result = qualification_engine.qualify_lead(enriched_lead)
        
        # Update lead with scores
        enriched_lead.lead_score = lead_score.total_score
        enriched_lead.qualification_status = QualificationStatus(lead_score.qualification_status)
        enriched_lead.score_breakdown = dict(lead_score.category_scores)
        
        # Store in database
        if not enriched_lead.id:
            enriched_lead.id = f"lead_{len(leads_db) + 1}"
        leads_db[enriched_lead.id] = enriched_lead
        
        # Update analytics
        _update_analytics(enriched_lead, qualification_result)
        
        return {
            "success": True,
            "lead": enriched_lead.dict(),
            "score_details": lead_score.dict(),
            "qualification": qualification_result
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Enrichment failed: {str(e)}")

@app.post("/api/leads/bulk-process")
async def bulk_process_leads(file: UploadFile = File(...)):
    """Process multiple leads from CSV upload"""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    try:
        content = await file.read()
        csv_data = csv.DictReader(io.StringIO(content.decode('utf-8')))
        
        leads = []
        for row in csv_data:
            if 'domain' in row and row['domain']:
                lead_data = {
                    "domain": row['domain'],
                    "company_name": row.get('company_name', row['domain'].split('.')[0].title())
                }
                
                # Add optional fields if present
                if 'industry' in row:
                    lead_data['industry'] = row['industry']
                if 'headquarters' in row:
                    lead_data['headquarters'] = row['headquarters']
                
                leads.append(Lead(**lead_data))
        
        if not leads:
            raise HTTPException(status_code=400, detail="No valid leads found in CSV")
        
        # Process leads concurrently (limited batch size for demo)
        batch_size = min(10, len(leads))
        leads_batch = leads[:batch_size]
        
        # Enrich leads
        enriched_leads = await enrichment_service.batch_enrich_leads(leads_batch)
        
        # Score and qualify each lead
        results = []
        for lead in enriched_leads:
            lead_score = scoring_engine.score_lead(lead)
            qualification_result = qualification_engine.qualify_lead(lead)
            
            lead.lead_score = lead_score.total_score
            lead.qualification_status = QualificationStatus(lead_score.qualification_status)
            lead.score_breakdown = dict(lead_score.category_scores)
            lead.id = f"lead_{len(leads_db) + 1}"
            
            leads_db[lead.id] = lead
            _update_analytics(lead, qualification_result)
            
            results.append({
                "lead": lead.dict(),
                "score_details": lead_score.dict(),
                "qualification": qualification_result
            })
        
        return {
            "success": True,
            "processed_count": len(results),
            "total_uploaded": len(leads),
            "results": results
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bulk processing failed: {str(e)}")

@app.get("/api/leads")
async def get_leads(
    score_min: Optional[float] = Query(None, ge=0, le=100),
    score_max: Optional[float] = Query(None, ge=0, le=100),
    qualification: Optional[str] = Query(None),
    industry: Optional[str] = Query(None),
    limit: Optional[int] = Query(50, ge=1, le=1000),
    offset: Optional[int] = Query(0, ge=0)
):
    """Get filtered list of leads"""
    filtered_leads = list(leads_db.values())
    
    # Apply filters
    if score_min is not None:
        filtered_leads = [lead for lead in filtered_leads if lead.lead_score and lead.lead_score >= score_min]
    
    if score_max is not None:
        filtered_leads = [lead for lead in filtered_leads if lead.lead_score and lead.lead_score <= score_max]
    
    if qualification:
        filtered_leads = [lead for lead in filtered_leads if lead.qualification_status and lead.qualification_status.value == qualification]
    
    if industry:
        filtered_leads = [lead for lead in filtered_leads if lead.industry and industry.lower() in lead.industry.lower()]
    
    # Sort by score (descending)
    filtered_leads.sort(key=lambda x: x.lead_score or 0, reverse=True)
    
    # Apply pagination
    total_count = len(filtered_leads)
    paginated_leads = filtered_leads[offset:offset + limit]
    
    return {
        "leads": [lead.dict() for lead in paginated_leads],
        "total_count": total_count,
        "offset": offset,
        "limit": limit
    }

@app.get("/api/leads/{lead_id}")
async def get_lead(lead_id: str):
    """Get detailed information for a specific lead"""
    if lead_id not in leads_db:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    lead = leads_db[lead_id]
    
    # Re-generate fresh qualification analysis
    qualification_result = qualification_engine.qualify_lead(lead)
    
    return {
        "lead": lead.dict(),
        "qualification_analysis": qualification_result
    }

@app.get("/api/leads/{lead_id}/recommendations")
async def get_lead_recommendations(lead_id: str):
    """Get personalized outreach recommendations for a lead"""
    if lead_id not in leads_db:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    lead = leads_db[lead_id]
    qualification_result = qualification_engine.qualify_lead(lead)
    
    # Generate personalized recommendations
    recommendations = {
        "outreach_strategy": qualification_result["outreach_strategy"],
        "action_plan": qualification_result["action_plan"],
        "email_templates": _generate_email_templates(lead, qualification_result),
        "meeting_suggestions": _generate_meeting_suggestions(lead),
        "content_recommendations": qualification_result["outreach_strategy"]["content_recommendations"]
    }
    
    return recommendations

@app.post("/api/leads/export")
async def export_leads(lead_ids: List[str], format: str = "csv"):
    """Export selected leads"""
    if format not in ["csv", "json"]:
        raise HTTPException(status_code=400, detail="Format must be 'csv' or 'json'")
    
    # Get leads
    export_leads = [leads_db[lead_id] for lead_id in lead_ids if lead_id in leads_db]
    
    if not export_leads:
        raise HTTPException(status_code=404, detail="No valid leads found")
    
    if format == "csv":
        # Generate CSV
        output = io.StringIO()
        fieldnames = [
            'company_name', 'domain', 'industry', 'lead_score', 'qualification_status',
            'employee_count', 'headquarters', 'last_enriched'
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for lead in export_leads:
            writer.writerow({
                'company_name': lead.company_name,
                'domain': lead.domain,
                'industry': lead.industry or '',
                'lead_score': lead.lead_score or 0,
                'qualification_status': lead.qualification_status.value if lead.qualification_status else '',
                'employee_count': lead.metrics.employee_count or '',
                'headquarters': lead.headquarters or '',
                'last_enriched': lead.last_enriched.isoformat() if lead.last_enriched else ''
            })
        
        return JSONResponse(
            content={
                "data": output.getvalue(),
                "filename": f"leads_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            }
        )
    
    else:  # JSON format
        return {
            "data": [lead.dict() for lead in export_leads],
            "filename": f"leads_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        }

@app.get("/api/analytics/dashboard")
async def get_analytics_dashboard():
    """Get dashboard analytics"""
    return {
        "summary_stats": {
            "total_leads": analytics_data["total_leads"],
            "average_score": analytics_data["average_score"],
            "qualification_breakdown": analytics_data["qualification_breakdown"]
        },
        "recent_leads": analytics_data["recent_leads"][-10:],  # Last 10 leads
        "score_distribution": _calculate_score_distribution(),
        "industry_breakdown": _calculate_industry_breakdown(),
        "trends": _calculate_trends()
    }

@app.put("/api/leads/{lead_id}")
async def update_lead(lead_id: str, updates: dict):
    """Update lead information"""
    if lead_id not in leads_db:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    lead = leads_db[lead_id]
    
    # Update allowed fields
    allowed_fields = ['company_name', 'industry', 'headquarters']
    for field, value in updates.items():
        if field in allowed_fields and hasattr(lead, field):
            setattr(lead, field, value)
    
    # Re-score if significant changes
    if any(field in updates for field in ['industry', 'company_name']):
        lead_score = scoring_engine.score_lead(lead)
        lead.lead_score = lead_score.total_score
        lead.qualification_status = QualificationStatus(lead_score.qualification_status)
    
    lead.updated_at = datetime.now()
    
    return {"success": True, "lead": lead.dict()}

@app.delete("/api/leads/{lead_id}")
async def delete_lead(lead_id: str):
    """Delete a lead"""
    if lead_id not in leads_db:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    del leads_db[lead_id]
    analytics_data["total_leads"] = len(leads_db)
    
    return {"success": True, "message": "Lead deleted"}

# Helper functions
def _update_analytics(lead: Lead, qualification_result: Dict):
    """Update analytics data"""
    analytics_data["total_leads"] = len(leads_db)
    
    # Update qualification breakdown
    if lead.qualification_status:
        status = lead.qualification_status.value
        analytics_data["qualification_breakdown"][status] = sum(
            1 for l in leads_db.values() 
            if l.qualification_status and l.qualification_status.value == status
        )
    
    # Update average score
    scores = [l.lead_score for l in leads_db.values() if l.lead_score]
    analytics_data["average_score"] = sum(scores) / len(scores) if scores else 0
    
    # Add to recent leads
    analytics_data["recent_leads"].append({
        "id": lead.id,
        "company_name": lead.company_name,
        "score": lead.lead_score,
        "qualification": lead.qualification_status.value if lead.qualification_status else "Unknown",
        "timestamp": datetime.now().isoformat()
    })

def _calculate_score_distribution():
    """Calculate score distribution for charts"""
    scores = [l.lead_score for l in leads_db.values() if l.lead_score]
    if not scores:
        return {"0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0}
    
    distribution = {"0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0}
    for score in scores:
        if score <= 20:
            distribution["0-20"] += 1
        elif score <= 40:
            distribution["21-40"] += 1
        elif score <= 60:
            distribution["41-60"] += 1
        elif score <= 80:
            distribution["61-80"] += 1
        else:
            distribution["81-100"] += 1
    
    return distribution

def _calculate_industry_breakdown():
    """Calculate breakdown by industry"""
    industries = {}
    for lead in leads_db.values():
        if lead.industry:
            industries[lead.industry] = industries.get(lead.industry, 0) + 1
    
    return dict(sorted(industries.items(), key=lambda x: x[1], reverse=True)[:10])

def _calculate_trends():
    """Calculate trends over time"""
    # Simple mock trend data
    return {
        "weekly_leads": [12, 18, 15, 22, 25, 20, 28],
        "weekly_scores": [65, 68, 70, 72, 75, 73, 76]
    }

def _generate_email_templates(lead: Lead, qualification_result: Dict):
    """Generate personalized email templates"""
    templates = []
    
    if lead.qualification_status == QualificationStatus.HOT:
        templates.append({
            "type": "immediate_outreach",
            "subject": f"Quick question about {lead.company_name}'s growth",
            "body": f"Hi there,\n\nI noticed {lead.company_name} has been expanding rapidly in the {lead.industry} space. I'd love to share how companies like yours have achieved 3x efficiency gains with our solution.\n\nWould you be open to a 15-minute conversation this week?\n\nBest regards"
        })
    
    return templates

def _generate_meeting_suggestions(lead: Lead):
    """Generate meeting type suggestions"""
    suggestions = []
    
    if lead.qualification_status == QualificationStatus.HOT:
        suggestions.append({
            "type": "demo",
            "duration": "30 minutes",
            "agenda": "Personalized product demonstration focused on scaling challenges"
        })
    elif lead.qualification_status == QualificationStatus.WARM:
        suggestions.append({
            "type": "discovery",
            "duration": "20 minutes",
            "agenda": "Understanding current processes and pain points"
        })
    
    return suggestions

@app.post("/api/leads/{lead_id}/insights")
async def generate_lead_insights(lead_id: str):
    """Generate intelligent insights for a lead"""
    if lead_id not in leads_db:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    lead = leads_db[lead_id]
    
    try:
        # Generate personalized email
        email_template = insights_engine.generate_personalized_email(lead)
        
        # Generate call script
        call_script = insights_engine.generate_call_script(lead)
        
        # Predict outcome
        outcome_prediction = insights_engine.predict_lead_outcome(lead)
        
        # Competitive analysis
        competitive_analysis = competitive_engine.analyze_competitive_landscape(lead)
        
        return {
            "lead_id": lead_id,
            "email_template": email_template,
            "call_script": call_script,
            "outcome_prediction": outcome_prediction,
            "competitive_analysis": competitive_analysis,
            "generated_at": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate insights: {str(e)}")

@app.post("/api/analytics/patterns")
async def analyze_lead_patterns():
    """Analyze patterns across all leads"""
    try:
        all_leads = list(leads_db.values())
        analysis = insights_engine.analyze_lead_patterns(all_leads)
        
        return {
            "analysis": analysis,
            "analyzed_at": datetime.now().isoformat(),
            "lead_count": len(all_leads)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze patterns: {str(e)}")

@app.post("/api/integrations/crm/{crm_name}/sync")
async def sync_to_crm(crm_name: str, lead_ids: List[str]):
    """Sync selected leads to CRM"""
    if crm_name not in ["hubspot", "salesforce"]:
        raise HTTPException(status_code=400, detail="Unsupported CRM")
    
    # Get leads to sync
    leads_to_sync = [leads_db[lead_id] for lead_id in lead_ids if lead_id in leads_db]
    
    if not leads_to_sync:
        raise HTTPException(status_code=404, detail="No valid leads found")
    
    try:
        # Configure CRM integration (would use actual API keys in production)
        if crm_name == "hubspot":
            integration = HubSpotIntegration(api_key=os.getenv("HUBSPOT_API_KEY"))
        else:
            integration = SalesforceIntegration(
                instance_url=os.getenv("SALESFORCE_INSTANCE_URL"),
                access_token=os.getenv("SALESFORCE_ACCESS_TOKEN")
            )
        
        integration_manager.add_crm_integration(crm_name, integration)
        
        # Sync leads
        result = await integration_manager.sync_to_crm(crm_name, leads_to_sync)
        
        return {
            "crm": crm_name,
            "sync_result": result,
            "synced_at": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CRM sync failed: {str(e)}")

@app.get("/api/integrations/status")
async def get_integration_status():
    """Get status of all integrations"""
    try:
        status = integration_manager.get_integration_status()
        test_results = await integration_manager.test_all_integrations()
        
        return {
            "status": status,
            "connection_tests": test_results,
            "checked_at": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get integration status: {str(e)}")

@app.post("/api/webhooks/register")
async def register_webhook(webhook_data: dict):
    """Register a new webhook"""
    try:
        webhook_id = webhook_data.get("id")
        url = webhook_data.get("url")
        events = webhook_data.get("events", [])
        secret = webhook_data.get("secret")
        
        if not webhook_id or not url or not events:
            raise HTTPException(status_code=400, detail="Missing required webhook data")
        
        integration_manager.webhook_manager.register_webhook(webhook_id, url, events, secret)
        
        return {
            "success": True,
            "webhook_id": webhook_id,
            "registered_at": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to register webhook: {str(e)}")

@app.get("/api/zapier/triggers")
async def get_zapier_triggers():
    """Get available Zapier triggers"""
    from services.integrations import ZapierIntegration
    return ZapierIntegration.get_trigger_endpoints()

@app.get("/api/zapier/actions")
async def get_zapier_actions():
    """Get available Zapier actions"""
    from services.integrations import ZapierIntegration
    return ZapierIntegration.get_action_endpoints()

# Enhanced export endpoint with more options
@app.post("/api/leads/export/advanced")
async def export_leads_advanced(
    export_request: dict
):
    """Advanced export with multiple format and integration options"""
    lead_ids = export_request.get("lead_ids", [])
    format_type = export_request.get("format", "csv")
    detail_level = export_request.get("detail_level", "basic")
    target_system = export_request.get("target_system")
    include_insights = export_request.get("include_insights", False)
    
    # Get leads
    export_leads = [leads_db[lead_id] for lead_id in lead_ids if lead_id in leads_db]
    
    if not export_leads:
        raise HTTPException(status_code=404, detail="No valid leads found")
    
    try:
        from utils.exporters import ExportManager
        export_manager = ExportManager()
        
        # Add insights if requested
        if include_insights:
            enhanced_leads = []
            for lead in export_leads:
                insights = insights_engine.generate_personalized_email(lead)
                competitive = competitive_engine.analyze_competitive_landscape(lead)
                
                # Create enhanced lead data
                enhanced_lead_data = lead.dict()
                enhanced_lead_data["insights"] = {
                    "email_template": insights,
                    "competitive_analysis": competitive
                }
                enhanced_leads.append(enhanced_lead_data)
            
            if format_type == "json":
                data = json.dumps(enhanced_leads, indent=2, default=str)
                filename = f"leads_with_insights_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                return {
                    "success": True,
                    "data": data,
                    "filename": filename,
                    "content_type": "application/json"
                }
        
        # Use standard export manager
        data, filename, content_type = export_manager.export_leads(
            export_leads, format_type, detail_level, target_system
        )
        
        return {
            "success": True,
            "data": data,
            "filename": filename,
            "content_type": content_type,
            "count": len(export_leads)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)