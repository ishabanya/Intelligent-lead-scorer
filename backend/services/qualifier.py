from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import re
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.lead import Lead, QualificationStatus
from models.scoring import LeadScore
from services.scorer import LeadScoringEngine

class BuyerIntentAnalyzer:
    """Analyzes buyer intent signals from various data points"""
    
    def __init__(self):
        self.intent_keywords = {
            'high_intent': [
                'looking for', 'need help with', 'shopping for', 'evaluating',
                'comparing', 'budget approved', 'ready to purchase', 'urgent',
                'implementation', 'switch from', 'replace', 'upgrade'
            ],
            'medium_intent': [
                'interested in', 'considering', 'exploring options',
                'research', 'learning about', 'demo', 'trial',
                'improve', 'optimize', 'streamline'
            ],
            'timing_indicators': [
                'this quarter', 'next month', 'asap', 'immediately',
                'by end of year', 'Q1', 'Q2', 'Q3', 'Q4'
            ]
        }
        
        self.negative_signals = [
            'satisfied with current', 'not looking', 'happy with',
            'just implemented', 'recently purchased', 'under contract'
        ]
    
    def analyze_intent(self, lead: Lead) -> Dict[str, Any]:
        """Analyze buyer intent from lead data"""
        intent_score = 0
        intent_signals = []
        intent_level = "Low"
        
        # Analyze job postings for intent signals
        if lead.buying_signals.job_postings:
            job_intent = self._analyze_job_posting_intent(lead.buying_signals.job_postings)
            intent_score += job_intent['score']
            intent_signals.extend(job_intent['signals'])
        
        # Analyze technology stack for switching signals
        tech_intent = self._analyze_technology_intent(lead)
        intent_score += tech_intent['score']
        intent_signals.extend(tech_intent['signals'])
        
        # Analyze growth indicators for expansion intent
        growth_intent = self._analyze_growth_intent(lead)
        intent_score += growth_intent['score']
        intent_signals.extend(growth_intent['signals'])
        
        # Analyze funding for investment intent
        funding_intent = self._analyze_funding_intent(lead)
        intent_score += funding_intent['score']
        intent_signals.extend(funding_intent['signals'])
        
        # Determine intent level
        if intent_score >= 15:
            intent_level = "High"
        elif intent_score >= 8:
            intent_level = "Medium"
        elif intent_score >= 3:
            intent_level = "Low"
        else:
            intent_level = "Minimal"
        
        return {
            'intent_score': intent_score,
            'intent_level': intent_level,
            'intent_signals': intent_signals,
            'urgency_indicators': self._identify_urgency_indicators(lead),
            'buying_committee_signals': self._identify_buying_committee(lead)
        }
    
    def _analyze_job_posting_intent(self, job_postings: List[str]) -> Dict[str, Any]:
        """Analyze job postings for buying intent"""
        score = 0
        signals = []
        
        relevant_roles = {
            'high_intent': ['vp marketing', 'marketing director', 'growth lead', 'head of growth'],
            'medium_intent': ['marketing manager', 'digital marketing', 'marketing analyst'],
            'decision_maker': ['cmo', 'ceo', 'vp', 'director', 'head of']
        }
        
        for posting in job_postings:
            posting_lower = posting.lower()
            
            # High intent roles
            if any(role in posting_lower for role in relevant_roles['high_intent']):
                score += 5
                signals.append(f"Hiring for high-intent role: {posting}")
            
            # Medium intent roles
            elif any(role in posting_lower for role in relevant_roles['medium_intent']):
                score += 3
                signals.append(f"Hiring for relevant role: {posting}")
            
            # Decision maker roles
            if any(role in posting_lower for role in relevant_roles['decision_maker']):
                score += 2
                signals.append(f"Hiring decision maker: {posting}")
            
            # Technology-specific roles
            tech_keywords = ['automation', 'analytics', 'crm', 'marketing ops', 'martech']
            if any(keyword in posting_lower for keyword in tech_keywords):
                score += 4
                signals.append(f"Technology-focused role: {posting}")
        
        return {'score': min(score, 10), 'signals': signals}
    
    def _analyze_technology_intent(self, lead: Lead) -> Dict[str, Any]:
        """Analyze technology stack for switching/adoption intent"""
        score = 0
        signals = []
        
        all_tech = (
            lead.tech_stack.technologies +
            lead.tech_stack.marketing_tools +
            lead.tech_stack.sales_tools
        )
        
        # Competitor usage (switching opportunity)
        competitors = ['hubspot', 'salesforce', 'marketo', 'pardot', 'mailchimp']
        for tech in all_tech:
            if tech.lower() in competitors:
                score += 3
                signals.append(f"Uses competitor technology: {tech}")
        
        # Outdated technology (modernization opportunity)
        outdated_tech = ['legacy', 'on-premise', 'excel', 'manual', 'spreadsheet']
        for tech in all_tech:
            if any(old in tech.lower() for old in outdated_tech):
                score += 2
                signals.append(f"Uses outdated technology: {tech}")
        
        # Technology gaps (integration opportunity)
        if len(all_tech) < 3:
            score += 2
            signals.append("Limited technology stack - integration opportunity")
        
        return {'score': min(score, 8), 'signals': signals}
    
    def _analyze_growth_intent(self, lead: Lead) -> Dict[str, Any]:
        """Analyze growth indicators for expansion intent"""
        score = 0
        signals = []
        
        # Recent hiring surge
        if lead.buying_signals.recent_hiring and lead.buying_signals.recent_hiring >= 5:
            score += 3
            signals.append(f"High hiring velocity: {lead.buying_signals.recent_hiring} recent hires")
        
        # Expansion signals
        expansion_keywords = ['expansion', 'new market', 'scaling', 'growth', 'international']
        for signal in lead.buying_signals.expansion_signals:
            if any(keyword in signal.lower() for keyword in expansion_keywords):
                score += 2
                signals.append(f"Expansion signal: {signal}")
        
        # High growth rate
        if lead.metrics.growth_rate and lead.metrics.growth_rate >= 25:
            score += 2
            signals.append(f"High growth rate: {lead.metrics.growth_rate}%")
        
        return {'score': min(score, 6), 'signals': signals}
    
    def _analyze_funding_intent(self, lead: Lead) -> Dict[str, Any]:
        """Analyze funding events for investment intent"""
        score = 0
        signals = []
        
        if lead.metrics.last_funding_date:
            days_since_funding = (datetime.now() - lead.metrics.last_funding_date).days
            
            # Recent funding indicates budget availability
            if days_since_funding <= 90:
                score += 4
                signals.append("Recent funding - budget available")
            elif days_since_funding <= 180:
                score += 2
                signals.append("Funding within 6 months")
        
        # Large funding amount
        if lead.metrics.funding_amount and lead.metrics.funding_amount >= 10000000:
            score += 2
            signals.append(f"Significant funding: ${lead.metrics.funding_amount:,.0f}")
        
        return {'score': min(score, 5), 'signals': signals}
    
    def _identify_urgency_indicators(self, lead: Lead) -> List[str]:
        """Identify urgency indicators in the lead data"""
        urgency_signals = []
        
        # Decision maker changes
        if lead.buying_signals.decision_maker_changes:
            urgency_signals.append("Recent leadership changes")
        
        # Rapid hiring
        if lead.buying_signals.recent_hiring and lead.buying_signals.recent_hiring >= 10:
            urgency_signals.append("Rapid scaling/hiring")
        
        # Recent funding with growth pressure
        if lead.metrics.last_funding_date:
            days_since = (datetime.now() - lead.metrics.last_funding_date).days
            if 30 <= days_since <= 90:
                urgency_signals.append("Post-funding growth pressure")
        
        return urgency_signals
    
    def _identify_buying_committee(self, lead: Lead) -> Dict[str, Any]:
        """Identify potential buying committee members"""
        committee_signals = {}
        
        # Analyze job postings for committee roles
        decision_roles = ['ceo', 'cmo', 'vp marketing', 'head of growth']
        influencer_roles = ['marketing manager', 'operations', 'analyst']
        technical_roles = ['cto', 'engineering', 'it', 'developer']
        
        for posting in lead.buying_signals.job_postings:
            posting_lower = posting.lower()
            
            if any(role in posting_lower for role in decision_roles):
                committee_signals['decision_makers'] = committee_signals.get('decision_makers', []) + [posting]
            
            if any(role in posting_lower for role in influencer_roles):
                committee_signals['influencers'] = committee_signals.get('influencers', []) + [posting]
            
            if any(role in posting_lower for role in technical_roles):
                committee_signals['technical_evaluators'] = committee_signals.get('technical_evaluators', []) + [posting]
        
        return committee_signals

class LeadQualificationEngine:
    """Main engine for lead qualification and prioritization"""
    
    def __init__(self):
        self.scorer = LeadScoringEngine()
        self.intent_analyzer = BuyerIntentAnalyzer()
        
        # Qualification criteria weights
        self.qualification_weights = {
            'lead_score': 0.4,
            'intent_score': 0.3,
            'data_quality': 0.2,
            'timing_score': 0.1
        }
    
    def qualify_lead(self, lead: Lead) -> Dict[str, Any]:
        """Perform comprehensive lead qualification"""
        
        # Score the lead
        lead_score = self.scorer.score_lead(lead)
        
        # Analyze buyer intent
        intent_analysis = self.intent_analyzer.analyze_intent(lead)
        
        # Calculate timing score
        timing_score = self._calculate_timing_score(lead)
        
        # Determine final qualification
        final_qualification = self._determine_final_qualification(
            lead_score, intent_analysis, timing_score, lead
        )
        
        # Generate action recommendations
        action_plan = self._generate_action_plan(lead, final_qualification, intent_analysis)
        
        # Calculate priority score
        priority_score = self._calculate_priority_score(
            lead_score.total_score, 
            intent_analysis['intent_score'], 
            timing_score,
            lead.data_quality_score or 50
        )
        
        return {
            'lead_score': lead_score,
            'intent_analysis': intent_analysis,
            'timing_score': timing_score,
            'final_qualification': final_qualification,
            'priority_score': priority_score,
            'action_plan': action_plan,
            'qualification_reasons': self._get_qualification_reasons(lead_score, intent_analysis),
            'next_review_date': self._calculate_next_review_date(final_qualification),
            'outreach_strategy': self._generate_outreach_strategy(lead, final_qualification, intent_analysis)
        }
    
    def _calculate_timing_score(self, lead: Lead) -> float:
        """Calculate timing score based on trigger events and opportunity windows"""
        timing_score = 0
        
        # Recent funding timing
        if lead.metrics.last_funding_date:
            days_since = (datetime.now() - lead.metrics.last_funding_date).days
            if 30 <= days_since <= 120:  # Sweet spot
                timing_score += 8
            elif 120 <= days_since <= 180:
                timing_score += 5
            elif days_since <= 30:
                timing_score += 3  # Too soon
        
        # Hiring velocity timing
        if lead.buying_signals.recent_hiring:
            if lead.buying_signals.recent_hiring >= 5:
                timing_score += 6
            elif lead.buying_signals.recent_hiring >= 2:
                timing_score += 3
        
        # Decision maker changes
        if lead.buying_signals.decision_maker_changes:
            timing_score += 5
        
        # Quarter timing (higher scores at beginning of quarters)
        current_month = datetime.now().month
        if current_month in [1, 4, 7, 10]:  # Start of quarters
            timing_score += 2
        
        return min(timing_score, 20)
    
    def _determine_final_qualification(self, lead_score: LeadScore, intent_analysis: Dict, timing_score: float, lead: Lead) -> QualificationStatus:
        """Determine final qualification status considering all factors"""
        
        # Base qualification from lead score
        base_qualification = QualificationStatus(lead_score.qualification_status)
        
        # Intent-based adjustments
        intent_level = intent_analysis['intent_level']
        
        # Upgrade qualification based on high intent
        if intent_level == "High" and base_qualification == QualificationStatus.WARM:
            return QualificationStatus.HOT
        elif intent_level == "High" and base_qualification == QualificationStatus.COLD:
            return QualificationStatus.WARM
        elif intent_level == "Medium" and base_qualification == QualificationStatus.COLD:
            return QualificationStatus.WARM
        
        # Timing-based adjustments
        if timing_score >= 15 and base_qualification == QualificationStatus.WARM:
            return QualificationStatus.HOT
        
        # Data quality considerations
        if lead.data_quality_score and lead.data_quality_score < 40:
            # Downgrade if data quality is too poor
            if base_qualification == QualificationStatus.HOT:
                return QualificationStatus.WARM
            elif base_qualification == QualificationStatus.WARM:
                return QualificationStatus.COLD
        
        return base_qualification
    
    def _calculate_priority_score(self, lead_score: float, intent_score: float, timing_score: float, data_quality: float) -> float:
        """Calculate overall priority score for lead ranking"""
        weights = self.qualification_weights
        
        normalized_scores = {
            'lead_score': lead_score / 100,
            'intent_score': min(intent_score / 20, 1),  # Normalize intent score
            'timing_score': timing_score / 20,
            'data_quality': data_quality / 100
        }
        
        priority = (
            normalized_scores['lead_score'] * weights['lead_score'] +
            normalized_scores['intent_score'] * weights['intent_score'] +
            normalized_scores['data_quality'] * weights['data_quality'] +
            normalized_scores['timing_score'] * weights['timing_score']
        )
        
        return priority * 100  # Scale to 0-100
    
    def _generate_action_plan(self, lead: Lead, qualification: QualificationStatus, intent_analysis: Dict) -> Dict[str, Any]:
        """Generate specific action plan based on qualification"""
        
        if qualification == QualificationStatus.HOT:
            return {
                'immediate_actions': [
                    "Research key decision makers and recent company news",
                    "Prepare personalized demo focused on identified pain points",
                    "Schedule outreach within 24 hours"
                ],
                'follow_up_actions': [
                    "Send follow-up within 48 hours if no response",
                    "Engage on social media",
                    "Research competitive landscape"
                ],
                'timeline': "Immediate",
                'priority': "High",
                'assigned_rep_type': "Senior AE"
            }
        
        elif qualification == QualificationStatus.WARM:
            return {
                'immediate_actions': [
                    "Send personalized email with relevant case study",
                    "Research company's current solution and pain points",
                    "Identify best contact method and timing"
                ],
                'follow_up_actions': [
                    "Follow up within 3-5 business days",
                    "Share educational content",
                    "Invite to relevant webinar or event"
                ],
                'timeline': "Within 48 hours",
                'priority': "Medium-High",
                'assigned_rep_type': "AE"
            }
        
        elif qualification == QualificationStatus.COLD:
            return {
                'immediate_actions': [
                    "Add to nurture campaign",
                    "Research for trigger events",
                    "Gather additional company intelligence"
                ],
                'follow_up_actions': [
                    "Monitor for buying signals",
                    "Send educational content monthly",
                    "Re-evaluate quarterly"
                ],
                'timeline': "This week",
                'priority': "Medium",
                'assigned_rep_type': "SDR"
            }
        
        else:  # UNQUALIFIED
            return {
                'immediate_actions': [
                    "Gather more qualifying information",
                    "Verify company fit criteria",
                    "Research alternative contact approaches"
                ],
                'follow_up_actions': [
                    "Re-evaluate if additional data becomes available",
                    "Monitor for significant company changes",
                    "Consider alternative products/services"
                ],
                'timeline': "When additional data available",
                'priority': "Low",
                'assigned_rep_type': "Marketing"
            }
    
    def _get_qualification_reasons(self, lead_score: LeadScore, intent_analysis: Dict) -> List[str]:
        """Get specific reasons for the qualification decision"""
        reasons = []
        
        # Lead score reasons
        if lead_score.total_score >= 80:
            reasons.append(f"High lead score ({lead_score.total_score:.1f}/100)")
        elif lead_score.total_score >= 60:
            reasons.append(f"Good lead score ({lead_score.total_score:.1f}/100)")
        
        # Intent reasons
        if intent_analysis['intent_level'] == "High":
            reasons.append("High buyer intent detected")
            reasons.extend(intent_analysis['intent_signals'][:2])  # Top 2 signals
        
        # Urgency reasons
        if intent_analysis['urgency_indicators']:
            reasons.append("Urgency indicators present")
            reasons.extend(intent_analysis['urgency_indicators'])
        
        # Category-specific reasons
        top_categories = sorted(
            lead_score.category_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:2]
        
        for category, score in top_categories:
            if score >= 15:
                reasons.append(f"Strong {category.value.replace('_', ' ')} signals")
        
        return reasons[:5]  # Limit to top 5 reasons
    
    def _calculate_next_review_date(self, qualification: QualificationStatus) -> datetime:
        """Calculate when to next review this lead"""
        base_date = datetime.now()
        
        if qualification == QualificationStatus.HOT:
            return base_date + timedelta(days=3)
        elif qualification == QualificationStatus.WARM:
            return base_date + timedelta(days=7)
        elif qualification == QualificationStatus.COLD:
            return base_date + timedelta(days=30)
        else:
            return base_date + timedelta(days=90)
    
    def _generate_outreach_strategy(self, lead: Lead, qualification: QualificationStatus, intent_analysis: Dict) -> Dict[str, Any]:
        """Generate specific outreach strategy"""
        
        # Base messaging themes
        messaging_themes = []
        if intent_analysis['intent_signals']:
            messaging_themes.append("Address identified pain points")
        
        if lead.tech_stack.technologies:
            messaging_themes.append("Leverage technology compatibility")
        
        if lead.metrics.funding_amount:
            messaging_themes.append("Focus on growth and scaling")
        
        # Channel recommendations
        if qualification == QualificationStatus.HOT:
            channels = ["Direct phone call", "Personalized video", "LinkedIn message"]
        elif qualification == QualificationStatus.WARM:
            channels = ["Personalized email", "LinkedIn connection", "Social media engagement"]
        else:
            channels = ["Email sequence", "Content sharing", "Event invitation"]
        
        # Value proposition focus
        value_props = []
        if intent_analysis['intent_level'] in ["High", "Medium"]:
            value_props.append("ROI and efficiency gains")
        
        if lead.buying_signals.recent_hiring:
            value_props.append("Scaling and growth support")
        
        if any('competitor' in signal.lower() for signal in intent_analysis.get('intent_signals', [])):
            value_props.append("Competitive advantages")
        
        return {
            'recommended_channels': channels,
            'messaging_themes': messaging_themes,
            'value_proposition_focus': value_props,
            'personalization_hooks': self._identify_personalization_hooks(lead),
            'content_recommendations': self._recommend_content(lead, qualification)
        }
    
    def _identify_personalization_hooks(self, lead: Lead) -> List[str]:
        """Identify specific personalization opportunities"""
        hooks = []
        
        if lead.metrics.last_funding_date:
            hooks.append(f"Recent funding round congratulations")
        
        if lead.buying_signals.recent_hiring:
            hooks.append(f"Scaling team reference")
        
        if lead.industry:
            hooks.append(f"Industry-specific challenges")
        
        if lead.headquarters:
            hooks.append(f"Local market knowledge")
        
        return hooks
    
    def _recommend_content(self, lead: Lead, qualification: QualificationStatus) -> List[str]:
        """Recommend specific content for outreach"""
        content = []
        
        if qualification == QualificationStatus.HOT:
            content.extend([
                "ROI calculator",
                "Implementation timeline",
                "Reference customer contact"
            ])
        elif qualification == QualificationStatus.WARM:
            content.extend([
                "Industry case study",
                "Product demo video",
                "Competitive comparison"
            ])
        else:
            content.extend([
                "Educational whitepaper",
                "Industry report",
                "Best practices guide"
            ])
        
        # Industry-specific content
        if lead.industry:
            content.append(f"{lead.industry} industry insights")
        
        return content