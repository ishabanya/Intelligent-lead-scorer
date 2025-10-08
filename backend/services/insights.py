from typing import Dict, List, Optional, Any, Tuple
import re
from datetime import datetime, timedelta
import json
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.lead import Lead, QualificationStatus
from models.scoring import LeadScore

class InsightsEngine:
    """Generate intelligent insights for leads and sales strategies"""
    
    def __init__(self):
        self.email_templates = {
            'hot_leads': {
                'subject_templates': [
                    "Quick question about {company_name}'s {pain_point}",
                    "{company_name}: 15-minute solution overview?",
                    "How {company_name} can achieve {benefit} in {timeframe}",
                    "Noticed {company_name}'s {growth_signal} - let's talk",
                    "{first_name}, quick chat about {company_name}'s growth?"
                ],
                'opening_lines': [
                    "I noticed {company_name} has been {growth_indicator} - congratulations!",
                    "Saw that {company_name} recently {trigger_event}. Perfect timing to discuss how we can help with {solution_area}.",
                    "Quick question: What's the biggest challenge {company_name} faces with {current_process}?",
                    "{first_name}, I've been following {company_name}'s progress in {industry}.",
                    "Given {company_name}'s recent {growth_signal}, I thought you'd be interested in how similar companies have achieved {specific_outcome}."
                ],
                'value_props': [
                    "Companies like yours typically see {roi_metric} improvement in {timeframe}",
                    "We've helped {industry} companies reduce {pain_point} by {percentage}",
                    "Our solution has enabled {similar_company_type} to {specific_benefit}",
                    "Based on your {company_characteristic}, you could achieve {projected_outcome}"
                ],
                'calls_to_action': [
                    "Would you be open to a 15-minute conversation {timeframe}?",
                    "Could we schedule a brief call to explore this further?",
                    "I'd love to share a relevant case study - do you have 10 minutes?",
                    "Would it make sense to discuss how this applies to {company_name}?"
                ]
            },
            'warm_leads': {
                'subject_templates': [
                    "{industry} growth strategies for {company_name}",
                    "Helping {company_name} scale more efficiently",
                    "Resource for {company_name}: {specific_topic}",
                    "{first_name}, thought you'd find this interesting",
                    "Quick insight for {company_name}'s {department} team"
                ],
                'opening_lines': [
                    "I've been researching companies in the {industry} space and came across {company_name}.",
                    "Hope you're having a great week! I wanted to reach out because {reason}.",
                    "{first_name}, I thought you might find this {resource_type} relevant to {company_name}.",
                    "Given {company_name}'s focus on {business_area}, I wanted to share some insights.",
                    "I noticed {company_name} is {company_activity} - this reminded me of a similar situation."
                ],
                'value_props': [
                    "We've helped similar companies in {industry} achieve {outcome}",
                    "Other {company_size} organizations have found value in {solution_area}",
                    "This approach has worked well for companies facing {similar_challenge}",
                    "Based on trends we're seeing in {industry}, this could be valuable for {company_name}"
                ],
                'calls_to_action': [
                    "Would you like me to send over the full case study?",
                    "I'd be happy to share more details if you're interested.",
                    "Would it be helpful to discuss how this might apply to your situation?",
                    "Let me know if you'd like to explore this further."
                ]
            }
        }
        
        self.industry_insights = {
            'technology': {
                'common_pain_points': ['scaling infrastructure', 'customer acquisition', 'technical debt', 'team productivity'],
                'growth_metrics': ['user acquisition', 'revenue per user', 'churn rate', 'feature adoption'],
                'decision_factors': ['ROI', 'integration ease', 'scalability', 'security'],
                'typical_buying_process': 'Technical evaluation → Business case → Procurement'
            },
            'saas': {
                'common_pain_points': ['customer churn', 'onboarding efficiency', 'feature adoption', 'support overhead'],
                'growth_metrics': ['MRR growth', 'CAC payback', 'NPS score', 'expansion revenue'],
                'decision_factors': ['time to value', 'ease of use', 'integration capabilities', 'support quality'],
                'typical_buying_process': 'Trial → Use case validation → Team buy-in → Contract'
            },
            'fintech': {
                'common_pain_points': ['regulatory compliance', 'security concerns', 'user trust', 'transaction processing'],
                'growth_metrics': ['transaction volume', 'user growth', 'AUM', 'compliance metrics'],
                'decision_factors': ['security', 'compliance', 'reliability', 'cost efficiency'],
                'typical_buying_process': 'Security review → Compliance check → Risk assessment → Approval'
            }
        }
    
    def generate_personalized_email(self, lead: Lead, template_type: str = "auto") -> Dict[str, Any]:
        """Generate a personalized email for a lead"""
        
        # Determine template type based on qualification if auto
        if template_type == "auto":
            if lead.qualification_status == QualificationStatus.HOT:
                template_type = "hot_leads"
            else:
                template_type = "warm_leads"
        
        # Extract personalization variables
        variables = self._extract_personalization_variables(lead)
        
        # Get templates
        templates = self.email_templates.get(template_type, self.email_templates['warm_leads'])
        
        # Generate email components
        subject = self._generate_subject(templates['subject_templates'], variables)
        opening = self._generate_opening(templates['opening_lines'], variables)
        value_prop = self._generate_value_prop(templates['value_props'], variables)
        cta = self._generate_cta(templates['calls_to_action'], variables)
        
        # Construct full email
        email_body = f"{opening}\n\n{value_prop}\n\n{cta}\n\nBest regards,\n{{sender_name}}"
        
        return {
            'subject': subject,
            'body': email_body,
            'tone': 'professional' if template_type == 'warm_leads' else 'direct',
            'urgency': 'high' if template_type == 'hot_leads' else 'medium',
            'personalization_score': self._calculate_personalization_score(variables),
            'variables_used': list(variables.keys()),
            'sending_recommendations': self._get_sending_recommendations(lead, template_type)
        }
    
    def _extract_personalization_variables(self, lead: Lead) -> Dict[str, str]:
        """Extract variables for email personalization"""
        variables = {
            'company_name': lead.company_name,
            'industry': lead.industry or 'technology',
            'domain': lead.domain
        }
        
        # Add contact information if available
        if lead.contacts:
            primary_contact = lead.contacts[0]
            if primary_contact.name:
                variables['first_name'] = primary_contact.name.split()[0]
            if primary_contact.title:
                variables['title'] = primary_contact.title
        
        # Add company size context
        if lead.metrics.employee_count:
            if lead.metrics.employee_count < 50:
                variables['company_size'] = 'startup'
                variables['company_type'] = 'growing startup'
            elif lead.metrics.employee_count < 200:
                variables['company_size'] = 'mid-size'
                variables['company_type'] = 'mid-size company'
            else:
                variables['company_size'] = 'enterprise'
                variables['company_type'] = 'enterprise organization'
        
        # Add growth signals
        growth_signals = []
        if lead.buying_signals.recent_hiring:
            growth_signals.append(f"hiring {lead.buying_signals.recent_hiring} new team members")
            variables['growth_indicator'] = 'expanding your team'
        
        if lead.metrics.last_funding_date:
            days_since = (datetime.now() - lead.metrics.last_funding_date).days
            if days_since <= 180:
                growth_signals.append("recent funding")
                variables['trigger_event'] = 'raised funding'
        
        if growth_signals:
            variables['growth_signal'] = growth_signals[0]
        
        # Add technology context
        if lead.tech_stack.technologies:
            variables['current_tech'] = ', '.join(lead.tech_stack.technologies[:3])
        
        # Add industry-specific context
        industry_key = lead.industry.lower() if lead.industry else 'technology'
        if industry_key in self.industry_insights:
            industry_data = self.industry_insights[industry_key]
            variables['pain_point'] = industry_data['common_pain_points'][0]
            variables['growth_metric'] = industry_data['growth_metrics'][0]
        
        # Add location context
        if lead.headquarters:
            variables['location'] = lead.headquarters
        
        return variables
    
    def _generate_subject(self, templates: List[str], variables: Dict[str, str]) -> str:
        """Generate email subject line"""
        import random
        template = random.choice(templates)
        return self._fill_template(template, variables)
    
    def _generate_opening(self, templates: List[str], variables: Dict[str, str]) -> str:
        """Generate email opening line"""
        import random
        template = random.choice(templates)
        return self._fill_template(template, variables)
    
    def _generate_value_prop(self, templates: List[str], variables: Dict[str, str]) -> str:
        """Generate value proposition"""
        import random
        template = random.choice(templates)
        
        # Add specific metrics for value props
        enhanced_variables = variables.copy()
        enhanced_variables.update({
            'roi_metric': '40-60%',
            'timeframe': '3-6 months',
            'percentage': '50%',
            'specific_outcome': 'faster time-to-market',
            'projected_outcome': '3x efficiency improvement'
        })
        
        return self._fill_template(template, enhanced_variables)
    
    def _generate_cta(self, templates: List[str], variables: Dict[str, str]) -> str:
        """Generate call-to-action"""
        import random
        template = random.choice(templates)
        
        enhanced_variables = variables.copy()
        enhanced_variables.update({
            'timeframe': 'this week',
            'specific_topic': 'growth strategies'
        })
        
        return self._fill_template(template, enhanced_variables)
    
    def _fill_template(self, template: str, variables: Dict[str, str]) -> str:
        """Fill template with variables, handling missing ones gracefully"""
        try:
            return template.format(**variables)
        except KeyError as e:
            # Handle missing variables by providing defaults
            defaults = {
                'company_name': 'your company',
                'first_name': 'there',
                'industry': 'technology',
                'pain_point': 'scaling challenges',
                'growth_signal': 'growth',
                'timeframe': 'soon',
                'benefit': 'improved efficiency',
                'company_size': 'organization',
                'company_type': 'company'
            }
            
            enhanced_variables = {**defaults, **variables}
            return template.format(**enhanced_variables)
    
    def _calculate_personalization_score(self, variables: Dict[str, str]) -> float:
        """Calculate how personalized the email is"""
        base_score = 30  # Base score for having company name
        
        score_additions = {
            'first_name': 15,
            'title': 10,
            'growth_signal': 20,
            'current_tech': 15,
            'location': 5,
            'trigger_event': 20,
            'company_size': 10
        }
        
        score = base_score
        for var, points in score_additions.items():
            if var in variables and variables[var]:
                score += points
        
        return min(score, 100)
    
    def _get_sending_recommendations(self, lead: Lead, template_type: str) -> Dict[str, Any]:
        """Get recommendations for when and how to send"""
        
        recommendations = {
            'best_days': ['Tuesday', 'Wednesday', 'Thursday'],
            'best_times': ['10 AM', '2 PM'],
            'follow_up_schedule': []
        }
        
        if template_type == 'hot_leads':
            recommendations.update({
                'urgency': 'Send within 24 hours',
                'follow_up_schedule': [
                    {'delay_days': 2, 'type': 'phone_call'},
                    {'delay_days': 4, 'type': 'follow_up_email'},
                    {'delay_days': 7, 'type': 'linkedin_message'}
                ]
            })
        else:
            recommendations.update({
                'urgency': 'Send within 48-72 hours',
                'follow_up_schedule': [
                    {'delay_days': 5, 'type': 'follow_up_email'},
                    {'delay_days': 14, 'type': 'value_content'},
                    {'delay_days': 30, 'type': 'check_in'}
                ]
            })
        
        return recommendations
    
    def generate_call_script(self, lead: Lead) -> Dict[str, Any]:
        """Generate a call script for the lead"""
        
        variables = self._extract_personalization_variables(lead)
        
        # Determine call type based on qualification
        if lead.qualification_status == QualificationStatus.HOT:
            script_type = "discovery_call"
        else:
            script_type = "introduction_call"
        
        scripts = {
            'discovery_call': {
                'opening': f"Hi {{first_name}}, this is {{caller_name}} from {{company}}. I'm calling about {lead.company_name}'s {variables.get('growth_signal', 'growth initiatives')}. Do you have a few minutes to chat?",
                'agenda': [
                    f"I wanted to learn more about {lead.company_name}'s current {variables.get('pain_point', 'challenges')}",
                    "Share how we've helped similar companies achieve their goals",
                    "Explore if there's a potential fit for working together"
                ],
                'discovery_questions': [
                    f"What are the biggest challenges {lead.company_name} faces with {variables.get('pain_point', 'scaling')}?",
                    f"How are you currently handling {variables.get('current_process', 'this process')}?",
                    "What would the ideal solution look like for your team?",
                    "What's driving the urgency to solve this now?",
                    "Who else would be involved in evaluating a solution like this?"
                ],
                'value_statements': [
                    f"We've helped other {variables.get('company_type', 'companies')} reduce {variables.get('pain_point', 'inefficiencies')} by 40-60%",
                    f"Companies like {lead.company_name} typically see ROI within 3-6 months",
                    f"Our solution integrates seamlessly with {variables.get('current_tech', 'existing tools')}"
                ],
                'next_steps': [
                    "Schedule a demo tailored to your specific use case",
                    "Introduce you to our implementation team",
                    "Provide a custom ROI analysis"
                ]
            },
            'introduction_call': {
                'opening': f"Hi {{first_name}}, this is {{caller_name}} from {{company}}. I've been researching companies in the {variables.get('industry', 'technology')} space and came across {lead.company_name}. Do you have a moment?",
                'agenda': [
                    f"Learn more about {lead.company_name}'s current priorities",
                    "Share relevant insights from our work with similar companies",
                    "Determine if there might be value in continuing the conversation"
                ],
                'discovery_questions': [
                    f"What are {lead.company_name}'s main priorities for this year?",
                    f"How is the {variables.get('department', 'team')} handling {variables.get('business_area', 'current processes')}?",
                    "What tools and solutions are you currently using?",
                    "Are there any challenges or pain points you're looking to address?"
                ],
                'value_statements': [
                    f"We work with many {variables.get('company_type', 'organizations')} to improve their {variables.get('focus_area', 'operations')}",
                    "I thought you might find our approach interesting given your current situation",
                    "We've seen some great results with companies similar to yours"
                ],
                'next_steps': [
                    "Send relevant case studies and resources",
                    "Schedule a more detailed conversation",
                    "Connect you with others who've faced similar challenges"
                ]
            }
        }
        
        script = scripts[script_type]
        
        return {
            'script_type': script_type,
            'opening': script['opening'],
            'agenda': script['agenda'],
            'discovery_questions': script['discovery_questions'],
            'value_statements': script['value_statements'],
            'next_steps': script['next_steps'],
            'duration_estimate': '15-20 minutes' if script_type == 'discovery_call' else '10-15 minutes',
            'preparation_notes': self._generate_preparation_notes(lead, variables)
        }
    
    def _generate_preparation_notes(self, lead: Lead, variables: Dict[str, str]) -> List[str]:
        """Generate preparation notes for the call"""
        notes = [f"Company: {lead.company_name} ({lead.domain})"]
        
        if lead.industry:
            notes.append(f"Industry: {lead.industry}")
        
        if lead.metrics.employee_count:
            notes.append(f"Company size: ~{lead.metrics.employee_count} employees")
        
        if variables.get('growth_signal'):
            notes.append(f"Growth signal: {variables['growth_signal']}")
        
        if lead.tech_stack.technologies:
            notes.append(f"Tech stack: {', '.join(lead.tech_stack.technologies[:5])}")
        
        if lead.buying_signals.job_postings:
            notes.append(f"Active hiring: {len(lead.buying_signals.job_postings)} open positions")
        
        return notes
    
    def analyze_lead_patterns(self, leads: List[Lead]) -> Dict[str, Any]:
        """Analyze patterns across multiple leads to provide insights"""
        
        if not leads:
            return {}
        
        # Analyze conversion patterns
        qualified_leads = [l for l in leads if l.qualification_status in [QualificationStatus.HOT, QualificationStatus.WARM]]
        
        analysis = {
            'total_leads': len(leads),
            'qualified_rate': len(qualified_leads) / len(leads) if leads else 0,
            'average_score': sum(l.lead_score for l in leads if l.lead_score) / len([l for l in leads if l.lead_score]) if leads else 0
        }
        
        # Industry analysis
        industry_stats = {}
        for lead in leads:
            industry = lead.industry or 'Unknown'
            if industry not in industry_stats:
                industry_stats[industry] = {'total': 0, 'qualified': 0, 'avg_score': 0, 'scores': []}
            
            industry_stats[industry]['total'] += 1
            industry_stats[industry]['scores'].append(lead.lead_score or 0)
            
            if lead.qualification_status in [QualificationStatus.HOT, QualificationStatus.WARM]:
                industry_stats[industry]['qualified'] += 1
        
        # Calculate averages
        for industry, stats in industry_stats.items():
            stats['avg_score'] = sum(stats['scores']) / len(stats['scores']) if stats['scores'] else 0
            stats['qualification_rate'] = stats['qualified'] / stats['total'] if stats['total'] else 0
            del stats['scores']  # Remove raw scores
        
        analysis['industry_breakdown'] = industry_stats
        
        # Size analysis
        size_stats = {'startup': 0, 'small': 0, 'medium': 0, 'large': 0}
        for lead in leads:
            if lead.metrics.employee_count:
                if lead.metrics.employee_count < 50:
                    size_stats['startup'] += 1
                elif lead.metrics.employee_count < 200:
                    size_stats['small'] += 1
                elif lead.metrics.employee_count < 1000:
                    size_stats['medium'] += 1
                else:
                    size_stats['large'] += 1
        
        analysis['company_size_distribution'] = size_stats
        
        # Technology analysis
        tech_frequency = {}
        for lead in leads:
            for tech in lead.tech_stack.technologies:
                tech_frequency[tech] = tech_frequency.get(tech, 0) + 1
        
        # Get top 10 technologies
        top_technologies = sorted(tech_frequency.items(), key=lambda x: x[1], reverse=True)[:10]
        analysis['top_technologies'] = dict(top_technologies)
        
        # Generate insights
        insights = self._generate_pattern_insights(analysis, leads)
        analysis['insights'] = insights
        
        return analysis
    
    def _generate_pattern_insights(self, analysis: Dict, leads: List[Lead]) -> List[str]:
        """Generate actionable insights from lead patterns"""
        insights = []
        
        # Qualification rate insights
        qual_rate = analysis['qualified_rate']
        if qual_rate > 0.7:
            insights.append("🎯 High qualification rate suggests strong lead targeting")
        elif qual_rate < 0.3:
            insights.append("⚠️ Low qualification rate - consider refining lead criteria")
        
        # Industry insights
        if analysis['industry_breakdown']:
            best_industry = max(analysis['industry_breakdown'].items(), 
                              key=lambda x: x[1]['qualification_rate'])
            if best_industry[1]['qualification_rate'] > 0.6:
                insights.append(f"💡 {best_industry[0]} industry shows highest conversion potential")
        
        # Score insights
        avg_score = analysis['average_score']
        if avg_score > 75:
            insights.append("🌟 High average scores indicate quality lead sources")
        elif avg_score < 50:
            insights.append("📈 Consider focusing on higher-quality lead sources")
        
        # Technology insights
        if analysis['top_technologies']:
            top_tech = list(analysis['top_technologies'].keys())[0]
            insights.append(f"🔧 {top_tech} is the most common technology - consider targeted messaging")
        
        # Growth signals
        growth_leads = [l for l in leads if l.buying_signals.recent_hiring or l.metrics.last_funding_date]
        if len(growth_leads) / len(leads) > 0.3:
            insights.append("📈 Many leads show growth signals - emphasize scaling solutions")
        
        return insights
    
    def predict_lead_outcome(self, lead: Lead) -> Dict[str, Any]:
        """Predict likely outcomes for a lead"""
        
        # Simple rule-based prediction (could be enhanced with ML)
        prediction = {
            'conversion_probability': 0.0,
            'time_to_close_estimate': None,
            'predicted_value': None,
            'success_factors': [],
            'risk_factors': [],
            'recommended_approach': 'standard'
        }
        
        score = lead.lead_score or 0
        
        # Base conversion probability on score
        if score >= 80:
            prediction['conversion_probability'] = 0.75
            prediction['time_to_close_estimate'] = '2-4 weeks'
            prediction['recommended_approach'] = 'expedited'
        elif score >= 60:
            prediction['conversion_probability'] = 0.45
            prediction['time_to_close_estimate'] = '4-8 weeks'
            prediction['recommended_approach'] = 'standard'
        elif score >= 40:
            prediction['conversion_probability'] = 0.25
            prediction['time_to_close_estimate'] = '8-12 weeks'
            prediction['recommended_approach'] = 'nurture'
        else:
            prediction['conversion_probability'] = 0.1
            prediction['time_to_close_estimate'] = '12+ weeks'
            prediction['recommended_approach'] = 'qualify_further'
        
        # Identify success factors
        if lead.buying_signals.recent_hiring:
            prediction['success_factors'].append('Active hiring indicates growth/budget')
        
        if lead.metrics.last_funding_date:
            days_since = (datetime.now() - lead.metrics.last_funding_date).days
            if days_since <= 180:
                prediction['success_factors'].append('Recent funding provides budget availability')
        
        if lead.tech_stack.technologies:
            prediction['success_factors'].append('Clear technology stack shows technical sophistication')
        
        if lead.contacts:
            prediction['success_factors'].append('Contact information available for direct outreach')
        
        # Identify risk factors
        if not lead.industry:
            prediction['risk_factors'].append('Unknown industry makes targeting difficult')
        
        if not lead.metrics.employee_count:
            prediction['risk_factors'].append('Unknown company size complicates value proposition')
        
        if lead.data_quality_score and lead.data_quality_score < 50:
            prediction['risk_factors'].append('Low data quality may indicate outdated information')
        
        return prediction