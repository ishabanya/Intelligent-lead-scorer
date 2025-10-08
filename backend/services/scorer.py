import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import json
import re
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.lead import Lead, QualificationStatus
from models.scoring import (
    ScoringModel, ScoringWeights, ScoreCategory, ScoringRule, 
    LeadScore, ScoreExplanation, QualificationThresholds
)

class LeadScoringEngine:
    """Intelligent lead scoring engine with weighted algorithms"""
    
    def __init__(self, scoring_model: Optional[ScoringModel] = None):
        self.model = scoring_model or ScoringModel()
        if not self.model.global_rules:
            self.model.global_rules = self.model.get_default_rules()
        
        # Industry-specific scoring adjustments
        self.industry_multipliers = {
            'technology': 1.2,
            'software': 1.2,
            'saas': 1.3,
            'fintech': 1.1,
            'healthcare': 1.0,
            'e-commerce': 1.1,
            'marketing': 0.9,
            'consulting': 0.8,
            'manufacturing': 0.7,
            'retail': 0.8
        }
        
        # Technology fit scoring
        self.target_tech_stack = [
            'python', 'react', 'node.js', 'aws', 'postgresql',
            'redis', 'docker', 'kubernetes', 'api', 'microservices'
        ]
        
        self.competitor_technologies = [
            'salesforce', 'hubspot', 'marketo', 'pardot',
            'mailchimp', 'constant-contact', 'pipedrive'
        ]
    
    def score_lead(self, lead: Lead) -> LeadScore:
        """Score a lead using the configured scoring model"""
        category_scores = {}
        explanations = []
        applied_rules = []
        
        # Calculate scores for each category
        category_scores[ScoreCategory.COMPANY_FIT] = self._score_company_fit(lead, explanations)
        category_scores[ScoreCategory.GROWTH_INDICATORS] = self._score_growth_indicators(lead, explanations)
        category_scores[ScoreCategory.TECHNOLOGY_FIT] = self._score_technology_fit(lead, explanations)
        category_scores[ScoreCategory.ENGAGEMENT_SIGNALS] = self._score_engagement_signals(lead, explanations)
        category_scores[ScoreCategory.TIMING_SIGNALS] = self._score_timing_signals(lead, explanations)
        category_scores[ScoreCategory.BUYING_SIGNALS] = self._score_buying_signals(lead, explanations)
        
        # Apply global rules
        rule_adjustments = self._apply_scoring_rules(lead, applied_rules)
        
        # Calculate weighted total score
        total_score = self._calculate_weighted_score(category_scores, rule_adjustments)
        
        # Apply data quality penalty
        if self.model.apply_data_quality_penalty and lead.data_quality_score:
            quality_factor = lead.data_quality_score / 100
            data_quality_impact = total_score * (1 - quality_factor) * 0.2  # Max 20% penalty
            total_score = max(0, total_score - data_quality_impact)
        else:
            data_quality_impact = 0
        
        # Determine qualification status
        qualification_status = self._determine_qualification(total_score)
        
        # Calculate confidence based on data completeness
        confidence = self._calculate_confidence(lead)
        
        # Generate recommendations
        improvement_suggestions = self._generate_improvement_suggestions(lead, category_scores)
        next_actions = self._generate_next_actions(lead, qualification_status)
        outreach_timing, outreach_approach = self._suggest_outreach_strategy(lead, total_score)
        
        return LeadScore(
            total_score=min(100, max(0, total_score)),
            category_scores=category_scores,
            explanations=explanations,
            qualification_status=qualification_status.value,
            confidence=confidence,
            data_quality_impact=data_quality_impact,
            applied_rules=applied_rules,
            improvement_suggestions=improvement_suggestions,
            next_actions=next_actions,
            outreach_timing=outreach_timing,
            outreach_approach=outreach_approach
        )
    
    def _score_company_fit(self, lead: Lead, explanations: List[ScoreExplanation]) -> float:
        """Score how well the company fits our ICP"""
        score = 0
        max_score = 25
        factors = []
        
        # Industry fit (0-8 points)
        if lead.industry:
            industry_lower = lead.industry.lower()
            if any(target in industry_lower for target in self.model.icp.target_industries):
                industry_points = 8
                factors.append({"factor": "Target industry match", "impact": 8, "value": lead.industry})
            elif industry_lower in self.industry_multipliers:
                industry_points = 6 * self.industry_multipliers[industry_lower]
                factors.append({"factor": "Industry compatibility", "impact": industry_points, "value": lead.industry})
            else:
                industry_points = 3
                factors.append({"factor": "Industry identified", "impact": 3, "value": lead.industry})
            score += industry_points
        
        # Company size fit (0-8 points)
        if lead.metrics.employee_count:
            size_points = self._score_company_size(lead.metrics.employee_count)
            score += size_points
            factors.append({
                "factor": "Company size fit", 
                "impact": size_points, 
                "value": f"{lead.metrics.employee_count} employees"
            })
        
        # Revenue range fit (0-5 points)
        if lead.metrics.revenue_range:
            revenue_points = 5  # Assume good fit if we have revenue data
            score += revenue_points
            factors.append({
                "factor": "Revenue information available", 
                "impact": revenue_points, 
                "value": lead.metrics.revenue_range.value
            })
        
        # Geographic fit (0-4 points)
        if lead.headquarters:
            geo_points = self._score_geographic_fit(lead.headquarters)
            score += geo_points
            factors.append({
                "factor": "Geographic location", 
                "impact": geo_points, 
                "value": lead.headquarters
            })
        
        explanations.append(ScoreExplanation(
            category=ScoreCategory.COMPANY_FIT,
            score=score,
            max_score=max_score,
            factors=factors,
            recommendations=self._get_company_fit_recommendations(lead, score)
        ))
        
        return score
    
    def _score_company_size(self, employee_count: int) -> float:
        """Score based on ideal company size"""
        if self.model.icp.company_size_min and self.model.icp.company_size_max:
            if self.model.icp.company_size_min <= employee_count <= self.model.icp.company_size_max:
                return 8  # Perfect fit
            elif employee_count < self.model.icp.company_size_min:
                ratio = employee_count / self.model.icp.company_size_min
                return 8 * ratio  # Partial credit for smaller companies
            else:
                # Larger companies get partial credit
                return 6
        
        # Default scoring if no ICP size range defined
        if 50 <= employee_count <= 500:
            return 8  # Sweet spot for many B2B tools
        elif 20 <= employee_count <= 1000:
            return 6  # Good fit
        elif 10 <= employee_count <= 2000:
            return 4  # Acceptable
        else:
            return 2  # Edge cases
    
    def _score_geographic_fit(self, location: str) -> float:
        """Score based on geographic targeting"""
        location_lower = location.lower()
        
        # High-value markets
        if any(market in location_lower for market in ['san francisco', 'new york', 'seattle', 'boston', 'austin']):
            return 4
        
        # US/Canada markets
        if any(country in location_lower for country in ['usa', 'us', 'united states', 'canada']):
            return 3
        
        # English-speaking markets
        if any(country in location_lower for country in ['uk', 'australia', 'ireland', 'new zealand']):
            return 2
        
        # Other markets
        return 1
    
    def _score_growth_indicators(self, lead: Lead, explanations: List[ScoreExplanation]) -> float:
        """Score growth and expansion signals"""
        score = 0
        max_score = 20
        factors = []
        
        # Recent funding (0-6 points)
        if lead.metrics.last_funding_date:
            days_since_funding = (datetime.now() - lead.metrics.last_funding_date).days
            if days_since_funding <= 90:
                funding_points = 6
                factors.append({"factor": "Recent funding (90 days)", "impact": 6, "value": "Recent"})
            elif days_since_funding <= 180:
                funding_points = 4
                factors.append({"factor": "Recent funding (6 months)", "impact": 4, "value": "Recent"})
            elif days_since_funding <= 365:
                funding_points = 2
                factors.append({"factor": "Funding within year", "impact": 2, "value": "Past year"})
            else:
                funding_points = 0
            score += funding_points
        
        # Hiring velocity (0-6 points)
        if lead.buying_signals.recent_hiring:
            hiring_rate = lead.buying_signals.recent_hiring
            if hiring_rate >= 10:
                hiring_points = 6
                factors.append({"factor": "High hiring velocity", "impact": 6, "value": f"{hiring_rate} recent hires"})
            elif hiring_rate >= 5:
                hiring_points = 4
                factors.append({"factor": "Moderate hiring", "impact": 4, "value": f"{hiring_rate} recent hires"})
            elif hiring_rate >= 2:
                hiring_points = 2
                factors.append({"factor": "Some hiring activity", "impact": 2, "value": f"{hiring_rate} recent hires"})
            else:
                hiring_points = 0
            score += hiring_points
        
        # Job postings (0-4 points)
        if lead.buying_signals.job_postings:
            job_count = len(lead.buying_signals.job_postings)
            job_points = min(4, job_count)
            score += job_points
            factors.append({
                "factor": "Active job postings", 
                "impact": job_points, 
                "value": f"{job_count} open positions"
            })
        
        # Growth rate (0-4 points)
        if lead.metrics.growth_rate:
            if lead.metrics.growth_rate >= 50:
                growth_points = 4
            elif lead.metrics.growth_rate >= 25:
                growth_points = 3
            elif lead.metrics.growth_rate >= 10:
                growth_points = 2
            else:
                growth_points = 1
            score += growth_points
            factors.append({
                "factor": "Company growth rate", 
                "impact": growth_points, 
                "value": f"{lead.metrics.growth_rate}%"
            })
        
        explanations.append(ScoreExplanation(
            category=ScoreCategory.GROWTH_INDICATORS,
            score=score,
            max_score=max_score,
            factors=factors,
            recommendations=self._get_growth_recommendations(lead, score)
        ))
        
        return score
    
    def _score_technology_fit(self, lead: Lead, explanations: List[ScoreExplanation]) -> float:
        """Score technology stack compatibility"""
        score = 0
        max_score = 15
        factors = []
        
        all_technologies = (
            lead.tech_stack.technologies + 
            lead.tech_stack.marketing_tools + 
            lead.tech_stack.sales_tools + 
            lead.tech_stack.analytics_tools
        )
        
        if not all_technologies:
            explanations.append(ScoreExplanation(
                category=ScoreCategory.TECHNOLOGY_FIT,
                score=0,
                max_score=max_score,
                factors=[{"factor": "No technology data", "impact": 0, "value": "Unknown"}],
                recommendations=["Gather technology stack information"]
            ))
            return 0
        
        # Technology compatibility (0-8 points)
        compatible_techs = [tech for tech in all_technologies if tech.lower() in self.target_tech_stack]
        if compatible_techs:
            tech_points = min(8, len(compatible_techs) * 2)
            score += tech_points
            factors.append({
                "factor": "Compatible technologies", 
                "impact": tech_points, 
                "value": ", ".join(compatible_techs)
            })
        
        # Competitor technology usage (0-5 points)
        competitor_techs = [tech for tech in all_technologies if tech.lower() in self.competitor_technologies]
        if competitor_techs:
            comp_points = min(5, len(competitor_techs) * 3)
            score += comp_points
            factors.append({
                "factor": "Uses competitor tools", 
                "impact": comp_points, 
                "value": ", ".join(competitor_techs)
            })
        
        # Modern tech stack (0-2 points)
        modern_indicators = ['api', 'cloud', 'microservices', 'docker', 'kubernetes', 'saas']
        modern_techs = [tech for tech in all_technologies if any(indicator in tech.lower() for indicator in modern_indicators)]
        if modern_techs:
            modern_points = 2
            score += modern_points
            factors.append({
                "factor": "Modern technology adoption", 
                "impact": modern_points, 
                "value": ", ".join(modern_techs)
            })
        
        explanations.append(ScoreExplanation(
            category=ScoreCategory.TECHNOLOGY_FIT,
            score=score,
            max_score=max_score,
            factors=factors,
            recommendations=self._get_technology_recommendations(lead, score)
        ))
        
        return score
    
    def _score_engagement_signals(self, lead: Lead, explanations: List[ScoreExplanation]) -> float:
        """Score engagement and interest signals"""
        score = 0
        max_score = 15
        factors = []
        
        # Website traffic rank (0-5 points)
        if lead.website_traffic_rank:
            if lead.website_traffic_rank <= 100000:
                traffic_points = 5
            elif lead.website_traffic_rank <= 500000:
                traffic_points = 3
            elif lead.website_traffic_rank <= 1000000:
                traffic_points = 2
            else:
                traffic_points = 1
            score += traffic_points
            factors.append({
                "factor": "Website traffic rank", 
                "impact": traffic_points, 
                "value": f"#{lead.website_traffic_rank:,}"
            })
        
        # Social media presence (0-5 points)
        if lead.social_media_presence:
            social_points = min(5, len(lead.social_media_presence) * 2)
            score += social_points
            factors.append({
                "factor": "Social media presence", 
                "impact": social_points, 
                "value": f"{len(lead.social_media_presence)} platforms"
            })
        
        # Content/thought leadership (0-3 points)
        thought_leadership_indicators = ['blog', 'content', 'webinar', 'podcast', 'speaking']
        if any(indicator in str(lead.social_media_presence).lower() for indicator in thought_leadership_indicators):
            content_points = 3
            score += content_points
            factors.append({
                "factor": "Content/thought leadership", 
                "impact": content_points, 
                "value": "Active content creation"
            })
        
        # Data recency (0-2 points)
        if lead.last_enriched and (datetime.now() - lead.last_enriched).days <= 30:
            recency_points = 2
            score += recency_points
            factors.append({
                "factor": "Recent data update", 
                "impact": recency_points, 
                "value": "Data is current"
            })
        
        explanations.append(ScoreExplanation(
            category=ScoreCategory.ENGAGEMENT_SIGNALS,
            score=score,
            max_score=max_score,
            factors=factors,
            recommendations=self._get_engagement_recommendations(lead, score)
        ))
        
        return score
    
    def _score_timing_signals(self, lead: Lead, explanations: List[ScoreExplanation]) -> float:
        """Score timing and trigger event signals"""
        score = 0
        max_score = 15
        factors = []
        
        # Recent company changes (0-6 points)
        if lead.buying_signals.decision_maker_changes:
            change_points = 6
            score += change_points
            factors.append({
                "factor": "Recent leadership changes", 
                "impact": change_points, 
                "value": "New decision makers"
            })
        
        # Expansion signals (0-4 points)
        if lead.buying_signals.expansion_signals:
            expansion_count = len(lead.buying_signals.expansion_signals)
            expansion_points = min(4, expansion_count * 2)
            score += expansion_points
            factors.append({
                "factor": "Expansion signals", 
                "impact": expansion_points, 
                "value": f"{expansion_count} indicators"
            })
        
        # Funding/growth timing (0-3 points)
        if lead.metrics.last_funding_date:
            days_since_funding = (datetime.now() - lead.metrics.last_funding_date).days
            if 30 <= days_since_funding <= 180:  # Sweet spot for post-funding outreach
                timing_points = 3
                score += timing_points
                factors.append({
                    "factor": "Post-funding timing", 
                    "impact": timing_points, 
                    "value": "Optimal outreach window"
                })
        
        # Technology adoption signals (0-2 points)
        modern_adoption_signals = ['migration', 'upgrade', 'implementation', 'new system']
        if any(signal in str(lead.buying_signals.expansion_signals).lower() for signal in modern_adoption_signals):
            adoption_points = 2
            score += adoption_points
            factors.append({
                "factor": "Technology adoption", 
                "impact": adoption_points, 
                "value": "System changes underway"
            })
        
        explanations.append(ScoreExplanation(
            category=ScoreCategory.TIMING_SIGNALS,
            score=score,
            max_score=max_score,
            factors=factors,
            recommendations=self._get_timing_recommendations(lead, score)
        ))
        
        return score
    
    def _score_buying_signals(self, lead: Lead, explanations: List[ScoreExplanation]) -> float:
        """Score direct buying intent signals"""
        score = 0
        max_score = 10
        factors = []
        
        # Budget indicators (0-4 points)
        if lead.buying_signals.budget_indicators:
            budget_count = len(lead.buying_signals.budget_indicators)
            budget_points = min(4, budget_count * 2)
            score += budget_points
            factors.append({
                "factor": "Budget indicators", 
                "impact": budget_points, 
                "value": f"{budget_count} signals"
            })
        
        # Relevant job postings (0-4 points)
        if lead.buying_signals.job_postings:
            relevant_roles = ['marketing', 'growth', 'digital', 'automation', 'operations', 'technology']
            relevant_postings = [
                job for job in lead.buying_signals.job_postings 
                if any(role in job.lower() for role in relevant_roles)
            ]
            if relevant_postings:
                role_points = min(4, len(relevant_postings) * 2)
                score += role_points
                factors.append({
                    "factor": "Relevant hiring", 
                    "impact": role_points, 
                    "value": f"{len(relevant_postings)} relevant roles"
                })
        
        # Pain point indicators (0-2 points)
        pain_point_keywords = ['inefficient', 'manual', 'time-consuming', 'outdated', 'challenge']
        company_text = f"{lead.company_name} {lead.industry} {' '.join(lead.buying_signals.expansion_signals)}"
        if any(keyword in company_text.lower() for keyword in pain_point_keywords):
            pain_points = 2
            score += pain_points
            factors.append({
                "factor": "Pain point indicators", 
                "impact": pain_points, 
                "value": "Efficiency challenges identified"
            })
        
        explanations.append(ScoreExplanation(
            category=ScoreCategory.BUYING_SIGNALS,
            score=score,
            max_score=max_score,
            factors=factors,
            recommendations=self._get_buying_signal_recommendations(lead, score)
        ))
        
        return score
    
    def _apply_scoring_rules(self, lead: Lead, applied_rules: List[str]) -> float:
        """Apply custom scoring rules"""
        total_adjustment = 0
        
        for rule in self.model.global_rules:
            if self._rule_matches(lead, rule):
                total_adjustment += rule.score_impact * rule.weight
                applied_rules.append(rule.name)
        
        return total_adjustment
    
    def _rule_matches(self, lead: Lead, rule: ScoringRule) -> bool:
        """Check if a scoring rule matches the lead"""
        condition = rule.condition
        field = condition.get('field')
        operator = condition.get('operator')
        value = condition.get('value')
        
        if not field:
            return False
        
        # Get field value from lead
        field_value = self._get_field_value(lead, field)
        if field_value is None:
            return False
        
        # Apply operator
        if operator == 'eq':
            return field_value == value
        elif operator == 'gt':
            return isinstance(field_value, (int, float)) and field_value > value
        elif operator == 'lt':
            return isinstance(field_value, (int, float)) and field_value < value
        elif operator == 'in':
            target_list = getattr(self.model.icp, value, [])
            return field_value in target_list
        elif operator == 'contains':
            return isinstance(field_value, str) and value.lower() in field_value.lower()
        elif operator == 'intersects':
            if isinstance(field_value, list):
                target_list = getattr(self.model.icp, value, [])
                return bool(set(field_value) & set(target_list))
        elif operator == 'within_days':
            if isinstance(field_value, datetime):
                days_diff = (datetime.now() - field_value).days
                return days_diff <= value
        
        return False
    
    def _get_field_value(self, lead: Lead, field: str) -> Any:
        """Get field value from lead object using dot notation"""
        try:
            parts = field.split('.')
            value = lead
            for part in parts:
                if hasattr(value, part):
                    value = getattr(value, part)
                else:
                    return None
            return value
        except:
            return None
    
    def _calculate_weighted_score(self, category_scores: Dict[ScoreCategory, float], rule_adjustments: float) -> float:
        """Calculate weighted total score"""
        weights = self.model.weights
        
        weighted_sum = (
            category_scores.get(ScoreCategory.COMPANY_FIT, 0) * weights.company_fit +
            category_scores.get(ScoreCategory.GROWTH_INDICATORS, 0) * weights.growth_indicators +
            category_scores.get(ScoreCategory.TECHNOLOGY_FIT, 0) * weights.technology_fit +
            category_scores.get(ScoreCategory.ENGAGEMENT_SIGNALS, 0) * weights.engagement_signals +
            category_scores.get(ScoreCategory.TIMING_SIGNALS, 0) * weights.timing_signals +
            category_scores.get(ScoreCategory.BUYING_SIGNALS, 0) * weights.buying_signals
        )
        
        return weighted_sum + rule_adjustments
    
    def _determine_qualification(self, score: float) -> QualificationStatus:
        """Determine qualification status based on score"""
        thresholds = self.model.thresholds
        
        if score >= thresholds.hot_threshold:
            return QualificationStatus.HOT
        elif score >= thresholds.warm_threshold:
            return QualificationStatus.WARM
        elif score >= thresholds.cold_threshold:
            return QualificationStatus.COLD
        else:
            return QualificationStatus.UNQUALIFIED
    
    def _calculate_confidence(self, lead: Lead) -> float:
        """Calculate confidence in the score based on data completeness"""
        if lead.data_quality_score and lead.completeness_percentage:
            return (lead.data_quality_score * 0.6 + lead.completeness_percentage * 0.4) / 100
        elif lead.data_quality_score:
            return lead.data_quality_score / 100
        elif lead.completeness_percentage:
            return lead.completeness_percentage / 100
        else:
            return 0.5  # Default moderate confidence
    
    def _generate_improvement_suggestions(self, lead: Lead, category_scores: Dict[ScoreCategory, float]) -> List[str]:
        """Generate suggestions for improving lead score"""
        suggestions = []
        
        # Identify weak categories
        weak_categories = [cat for cat, score in category_scores.items() if score < 5]
        
        for category in weak_categories:
            if category == ScoreCategory.COMPANY_FIT:
                suggestions.append("Verify industry classification and company size")
            elif category == ScoreCategory.GROWTH_INDICATORS:
                suggestions.append("Research recent funding, hiring, or expansion news")
            elif category == ScoreCategory.TECHNOLOGY_FIT:
                suggestions.append("Identify current technology stack and tools")
            elif category == ScoreCategory.ENGAGEMENT_SIGNALS:
                suggestions.append("Analyze web presence and social media activity")
            elif category == ScoreCategory.TIMING_SIGNALS:
                suggestions.append("Look for trigger events and company changes")
            elif category == ScoreCategory.BUYING_SIGNALS:
                suggestions.append("Search for job postings and budget indicators")
        
        return suggestions
    
    def _generate_next_actions(self, lead: Lead, qualification: QualificationStatus) -> List[str]:
        """Generate recommended next actions based on qualification"""
        actions = []
        
        if qualification == QualificationStatus.HOT:
            actions.extend([
                "Schedule immediate outreach call",
                "Research key decision makers",
                "Prepare personalized demo"
            ])
        elif qualification == QualificationStatus.WARM:
            actions.extend([
                "Send personalized email with value proposition",
                "Share relevant case studies",
                "Schedule discovery call"
            ])
        elif qualification == QualificationStatus.COLD:
            actions.extend([
                "Add to nurture campaign",
                "Share educational content",
                "Monitor for trigger events"
            ])
        else:
            actions.extend([
                "Gather more company information",
                "Reassess fit criteria",
                "Consider alternative contact approach"
            ])
        
        return actions
    
    def _suggest_outreach_strategy(self, lead: Lead, score: float) -> Tuple[str, str]:
        """Suggest optimal outreach timing and approach"""
        # Timing
        if score >= 80:
            timing = "Immediate"
        elif score >= 60:
            timing = "Within 48 hours"
        elif score >= 40:
            timing = "This week"
        else:
            timing = "When additional data available"
        
        # Approach
        if score >= 80:
            approach = "Direct phone call or personalized video"
        elif score >= 60:
            approach = "Personalized email with specific value proposition"
        elif score >= 40:
            approach = "Email sequence with educational content"
        else:
            approach = "General nurture campaign"
        
        return timing, approach
    
    def _get_company_fit_recommendations(self, lead: Lead, score: float) -> List[str]:
        """Get recommendations for improving company fit score"""
        recommendations = []
        if score < 10:
            recommendations.append("Verify company is in target market")
        if not lead.metrics.employee_count:
            recommendations.append("Determine company size")
        if not lead.headquarters:
            recommendations.append("Identify company location")
        return recommendations
    
    def _get_growth_recommendations(self, lead: Lead, score: float) -> List[str]:
        """Get recommendations for growth indicators"""
        recommendations = []
        if score < 8:
            recommendations.append("Research recent funding or growth news")
        if not lead.buying_signals.job_postings:
            recommendations.append("Check for active job postings")
        return recommendations
    
    def _get_technology_recommendations(self, lead: Lead, score: float) -> List[str]:
        """Get recommendations for technology fit"""
        recommendations = []
        if score < 5:
            recommendations.append("Identify current technology stack")
        if not lead.tech_stack.technologies:
            recommendations.append("Research tools and platforms used")
        return recommendations
    
    def _get_engagement_recommendations(self, lead: Lead, score: float) -> List[str]:
        """Get recommendations for engagement signals"""
        recommendations = []
        if score < 5:
            recommendations.append("Analyze website traffic and social presence")
        return recommendations
    
    def _get_timing_recommendations(self, lead: Lead, score: float) -> List[str]:
        """Get recommendations for timing signals"""
        recommendations = []
        if score < 5:
            recommendations.append("Look for recent company changes or trigger events")
        return recommendations
    
    def _get_buying_signal_recommendations(self, lead: Lead, score: float) -> List[str]:
        """Get recommendations for buying signals"""
        recommendations = []
        if score < 3:
            recommendations.append("Search for budget allocation and purchasing signals")
        return recommendations