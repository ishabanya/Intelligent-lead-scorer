#!/usr/bin/env python3
"""
Test script to verify the Intelligent Lead Scorer system works correctly
"""

import sys
import os
import asyncio
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from models.lead import Lead, ContactInfo, CompanyMetrics, TechnologyStack
from services.enrichment import DataEnrichmentService
from services.scorer import LeadScoringEngine
from services.qualifier import LeadQualificationEngine
from services.insights import InsightsEngine
from services.competitive import CompetitiveIntelligenceEngine

async def test_lead_scoring_pipeline():
    """Test the complete lead scoring pipeline"""
    
    print("🚀 Testing Intelligent Lead Scorer Pipeline...")
    print("=" * 50)
    
    # Create a sample lead
    sample_lead = Lead(
        company_name="Example Tech Corp",
        domain="example-tech.com",
        industry="Technology",
        headquarters="San Francisco, CA",
        metrics=CompanyMetrics(
            employee_count=150,
            funding_amount=25000000,
            growth_rate=35.0
        ),
        tech_stack=TechnologyStack(
            technologies=["Python", "React", "AWS", "PostgreSQL"],
            marketing_tools=["HubSpot", "Google Analytics"],
            sales_tools=["Salesforce"]
        ),
        contacts=[
            ContactInfo(
                name="Jane Smith",
                email="jane@example-tech.com",
                title="VP of Marketing"
            )
        ]
    )
    
    print(f"📊 Created sample lead: {sample_lead.company_name}")
    
    # Initialize services
    enrichment_service = DataEnrichmentService()
    scoring_engine = LeadScoringEngine()
    qualifier = LeadQualificationEngine()
    insights_engine = InsightsEngine()
    competitive_engine = CompetitiveIntelligenceEngine()
    
    print("🔧 Initialized all services")
    
    # Test enrichment
    print("\n1️⃣ Testing Lead Enrichment...")
    enriched_lead = await enrichment_service.enrich_lead(sample_lead)
    print(f"   ✅ Data quality score: {enriched_lead.data_quality_score:.1f}%")
    print(f"   ✅ Completeness: {enriched_lead.completeness_percentage:.1f}%")
    
    # Test scoring
    print("\n2️⃣ Testing Lead Scoring...")
    lead_score = scoring_engine.score_lead(enriched_lead)
    print(f"   ✅ Total score: {lead_score.total_score:.1f}/100")
    print(f"   ✅ Qualification: {lead_score.qualification_status}")
    print(f"   ✅ Confidence: {lead_score.confidence:.2f}")
    
    # Show score breakdown
    print("\n   📈 Score Breakdown:")
    for category, score in lead_score.category_scores.items():
        print(f"      {category.value}: {score:.1f}")
    
    # Test qualification
    print("\n3️⃣ Testing Lead Qualification...")
    qualification_result = qualifier.qualify_lead(enriched_lead)
    print(f"   ✅ Final qualification: {qualification_result['final_qualification'].value}")
    print(f"   ✅ Priority score: {qualification_result['priority_score']:.1f}")
    print(f"   ✅ Intent level: {qualification_result['intent_analysis']['intent_level']}")
    
    # Test intelligent insights
    print("\n4️⃣ Testing Intelligent Insights...")
    email_template = insights_engine.generate_personalized_email(enriched_lead)
    print(f"   ✅ Generated email template")
    print(f"   ✅ Subject: {email_template['subject']}")
    print(f"   ✅ Personalization score: {email_template['personalization_score']:.1f}%")
    
    call_script = insights_engine.generate_call_script(enriched_lead)
    print(f"   ✅ Generated call script ({call_script['duration_estimate']})")
    
    outcome_prediction = insights_engine.predict_lead_outcome(enriched_lead)
    print(f"   ✅ Conversion probability: {outcome_prediction['conversion_probability']:.1%}")
    
    # Test competitive analysis
    print("\n5️⃣ Testing Competitive Intelligence...")
    competitive_analysis = competitive_engine.analyze_competitive_landscape(enriched_lead)
    print(f"   ✅ Detected {len(competitive_analysis['current_solutions'])} competitor solutions")
    print(f"   ✅ Switching likelihood: {competitive_analysis['switching_analysis']['switching_likelihood']}")
    
    # Test pattern analysis
    print("\n6️⃣ Testing Pattern Analysis...")
    leads_list = [enriched_lead]  # In real usage, this would be multiple leads
    pattern_analysis = insights_engine.analyze_lead_patterns(leads_list)
    print(f"   ✅ Analyzed {pattern_analysis['total_leads']} leads")
    print(f"   ✅ Qualification rate: {pattern_analysis['qualified_rate']:.1%}")
    print(f"   ✅ Generated {len(pattern_analysis['insights'])} insights")
    
    # Display key insights
    print("\n💡 Key Insights:")
    for insight in pattern_analysis['insights']:
        print(f"   • {insight}")
    
    # Display recommendations
    print("\n🎯 Recommended Actions:")
    for action in qualification_result['action_plan']['immediate_actions']:
        print(f"   • {action}")
    
    print("\n" + "=" * 50)
    print("✅ All tests completed successfully!")
    print(f"🏆 Lead Score: {lead_score.total_score:.1f}/100 ({lead_score.qualification_status})")
    print("🚀 System is ready for production use!")

def test_data_models():
    """Test that all data models work correctly"""
    print("\n🧪 Testing Data Models...")
    
    # Test Lead model
    lead = Lead(company_name="Test Corp", domain="test.com")
    assert lead.company_name == "Test Corp"
    print("   ✅ Lead model validation")
    
    # Test ContactInfo
    contact = ContactInfo(name="John Doe", email="john@test.com")
    assert contact.email == "john@test.com"
    print("   ✅ ContactInfo model validation")
    
    # Test CompanyMetrics
    metrics = CompanyMetrics(employee_count=100)
    assert metrics.employee_count == 100
    print("   ✅ CompanyMetrics model validation")
    
    print("   ✅ All data models working correctly")

if __name__ == "__main__":
    print("🧠 Intelligent Lead Scorer - System Test")
    print("=" * 50)
    
    # Test data models first
    test_data_models()
    
    # Run async pipeline test
    asyncio.run(test_lead_scoring_pipeline())
    
    print("\n🎉 System verification complete!")
    print("👨‍💻 Ready for demo and evaluation!")