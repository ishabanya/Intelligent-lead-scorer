from typing import Dict, List, Optional, Any, Set
import re
from datetime import datetime
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.lead import Lead

class CompetitiveIntelligenceEngine:
    """Analyze competitive landscape and generate positioning strategies"""
    
    def __init__(self):
        # Define competitor mappings and their characteristics
        self.competitors = {
            'hubspot': {
                'name': 'HubSpot',
                'category': 'Marketing Automation',
                'strengths': ['All-in-one platform', 'User-friendly interface', 'Strong content marketing'],
                'weaknesses': ['Can be expensive at scale', 'Limited customization', 'Complex for advanced users'],
                'pricing_model': 'Freemium with tiered subscriptions',
                'target_market': 'SMB to Mid-market',
                'key_features': ['CRM', 'Email marketing', 'Landing pages', 'Analytics'],
                'integration_challenges': ['Limited API flexibility', 'Data export restrictions'],
                'switching_triggers': ['Cost concerns', 'Scalability limits', 'Feature limitations']
            },
            'salesforce': {
                'name': 'Salesforce',
                'category': 'CRM',
                'strengths': ['Highly customizable', 'Extensive ecosystem', 'Enterprise-grade'],
                'weaknesses': ['Complex setup', 'High cost', 'Steep learning curve'],
                'pricing_model': 'Per-user subscription',
                'target_market': 'Mid-market to Enterprise',
                'key_features': ['Sales Cloud', 'Service Cloud', 'Marketing Cloud', 'Custom apps'],
                'integration_challenges': ['Complex configuration', 'High implementation cost'],
                'switching_triggers': ['Cost optimization', 'Simplification needs', 'User adoption issues']
            },
            'marketo': {
                'name': 'Marketo',
                'category': 'Marketing Automation',
                'strengths': ['Advanced automation', 'Lead scoring', 'Enterprise features'],
                'weaknesses': ['Complex interface', 'High learning curve', 'Expensive'],
                'pricing_model': 'Enterprise subscriptions',
                'target_market': 'Enterprise',
                'key_features': ['Lead nurturing', 'Campaign automation', 'Analytics', 'ABM'],
                'integration_challenges': ['Technical complexity', 'Resource intensive'],
                'switching_triggers': ['Complexity reduction', 'Cost concerns', 'Ease of use']
            },
            'pardot': {
                'name': 'Pardot',
                'category': 'B2B Marketing Automation',
                'strengths': ['Salesforce integration', 'B2B focused', 'Lead qualification'],
                'weaknesses': ['Salesforce dependency', 'Limited flexibility', 'Reporting limitations'],
                'pricing_model': 'Salesforce add-on',
                'target_market': 'Mid-market B2B',
                'key_features': ['Lead scoring', 'Email marketing', 'Landing pages', 'ROI reporting'],
                'integration_challenges': ['Salesforce lock-in', 'Limited third-party integrations'],
                'switching_triggers': ['Independence from Salesforce', 'Better integrations', 'Cost optimization']
            },
            'mailchimp': {
                'name': 'MailChimp',
                'category': 'Email Marketing',
                'strengths': ['Easy to use', 'Affordable', 'Good templates'],
                'weaknesses': ['Limited automation', 'Basic CRM', 'Scalability issues'],
                'pricing_model': 'Freemium with usage-based pricing',
                'target_market': 'Small business',
                'key_features': ['Email campaigns', 'Basic automation', 'Templates', 'Analytics'],
                'integration_challenges': ['Limited CRM features', 'Basic segmentation'],
                'switching_triggers': ['Need for advanced features', 'Better segmentation', 'CRM integration']
            },
            'pipedrive': {
                'name': 'Pipedrive',
                'category': 'Sales CRM',
                'strengths': ['Simple pipeline management', 'Visual interface', 'Affordable'],
                'weaknesses': ['Limited marketing features', 'Basic reporting', 'Scalability limits'],
                'pricing_model': 'Per-user subscription',
                'target_market': 'SMB Sales teams',
                'key_features': ['Pipeline management', 'Contact management', 'Activity tracking', 'Mobile app'],
                'integration_challenges': ['Limited marketing automation', 'Basic customization'],
                'switching_triggers': ['Need for marketing features', 'Advanced analytics', 'Customization needs']
            }
        }
        
        # Our solution's positioning against competitors
        self.our_positioning = {
            'key_differentiators': [
                'AI-powered lead qualification',
                'Unified sales and marketing platform',
                'Advanced integration capabilities',
                'Predictive analytics and insights',
                'Flexible pricing model'
            ],
            'target_advantages': {
                'vs_hubspot': 'Better customization and advanced AI features',
                'vs_salesforce': 'Simpler setup with enterprise-grade capabilities',
                'vs_marketo': 'User-friendly interface with advanced automation',
                'vs_pardot': 'Platform independence and better integrations',
                'vs_mailchimp': 'Advanced automation and CRM capabilities',
                'vs_pipedrive': 'Comprehensive marketing automation features'
            }
        }
    
    def analyze_competitive_landscape(self, lead: Lead) -> Dict[str, Any]:
        """Analyze the competitive landscape for a specific lead"""
        
        # Detect current solutions
        current_solutions = self._detect_current_solutions(lead)
        
        # Analyze switching opportunities
        switching_analysis = self._analyze_switching_opportunities(current_solutions, lead)
        
        # Generate competitive positioning
        positioning = self._generate_competitive_positioning(current_solutions, lead)
        
        # Create battle cards
        battle_cards = self._create_battle_cards(current_solutions)
        
        return {
            'current_solutions': current_solutions,
            'switching_analysis': switching_analysis,
            'competitive_positioning': positioning,
            'battle_cards': battle_cards,
            'recommended_strategy': self._recommend_competitive_strategy(current_solutions, lead),
            'objection_handling': self._generate_objection_handling(current_solutions),
            'proof_points': self._generate_proof_points(current_solutions, lead)
        }
    
    def _detect_current_solutions(self, lead: Lead) -> List[Dict[str, Any]]:
        """Detect what competitive solutions the lead is currently using"""
        detected_solutions = []
        
        # Check technology stack
        all_technologies = (
            lead.tech_stack.technologies +
            lead.tech_stack.marketing_tools +
            lead.tech_stack.sales_tools +
            lead.tech_stack.analytics_tools
        )
        
        for tech in all_technologies:
            tech_lower = tech.lower()
            
            for competitor_key, competitor_data in self.competitors.items():
                if competitor_key in tech_lower or competitor_data['name'].lower() in tech_lower:
                    detected_solutions.append({
                        'solution': competitor_data['name'],
                        'category': competitor_data['category'],
                        'confidence': 'high',
                        'source': 'technology_stack',
                        'details': competitor_data
                    })
        
        # Check for indirect signals in job postings
        for job_posting in lead.buying_signals.job_postings:
            job_lower = job_posting.lower()
            
            # Look for mentions of competitors in job requirements
            for competitor_key, competitor_data in self.competitors.items():
                if competitor_key in job_lower or any(feature.lower() in job_lower for feature in competitor_data['key_features']):
                    # Check if already detected
                    if not any(sol['solution'] == competitor_data['name'] for sol in detected_solutions):
                        detected_solutions.append({
                            'solution': competitor_data['name'],
                            'category': competitor_data['category'],
                            'confidence': 'medium',
                            'source': 'job_posting',
                            'details': competitor_data
                        })
        
        # Remove duplicates and sort by confidence
        unique_solutions = []
        seen_solutions = set()
        
        for solution in detected_solutions:
            if solution['solution'] not in seen_solutions:
                unique_solutions.append(solution)
                seen_solutions.add(solution['solution'])
        
        return sorted(unique_solutions, key=lambda x: {'high': 3, 'medium': 2, 'low': 1}[x['confidence']], reverse=True)
    
    def _analyze_switching_opportunities(self, current_solutions: List[Dict], lead: Lead) -> Dict[str, Any]:
        """Analyze opportunities for the lead to switch from current solutions"""
        
        if not current_solutions:
            return {
                'opportunity_score': 30,  # Medium opportunity for greenfield
                'switching_likelihood': 'medium',
                'primary_drivers': ['new_implementation', 'growth_needs'],
                'timeline_estimate': '3-6 months',
                'decision_factors': ['features', 'ease_of_use', 'integration', 'cost']
            }
        
        opportunity_score = 0
        switching_triggers = []
        timeline_factors = []
        
        for solution in current_solutions:
            competitor = solution['details']
            
            # Analyze company characteristics vs competitor target market
            company_size = lead.metrics.employee_count or 50
            
            # Size mismatch analysis
            if competitor['target_market'] == 'Small business' and company_size > 100:
                opportunity_score += 30
                switching_triggers.append('outgrowing_current_solution')
                timeline_factors.append('immediate_need')
            elif competitor['target_market'] == 'Enterprise' and company_size < 200:
                opportunity_score += 20
                switching_triggers.append('over_engineered_solution')
            
            # Growth signals analysis
            if lead.buying_signals.recent_hiring and lead.buying_signals.recent_hiring > 5:
                opportunity_score += 25
                switching_triggers.append('scaling_challenges')
                timeline_factors.append('growth_pressure')
            
            # Technology sophistication analysis
            if len(lead.tech_stack.technologies) > 5:  # Tech-savvy company
                if 'Complex setup' in competitor['weaknesses']:
                    opportunity_score += 15
                    switching_triggers.append('seeking_simplification')
            
            # Budget considerations
            if lead.metrics.last_funding_date:
                days_since_funding = (datetime.now() - lead.metrics.last_funding_date).days
                if 30 <= days_since_funding <= 180:  # Post-funding optimization period
                    opportunity_score += 20
                    switching_triggers.append('budget_optimization')
                    timeline_factors.append('funding_timeline')
        
        # Determine switching likelihood
        if opportunity_score >= 70:
            likelihood = 'high'
            timeline = '1-3 months'
        elif opportunity_score >= 40:
            likelihood = 'medium'
            timeline = '3-6 months'
        else:
            likelihood = 'low'
            timeline = '6+ months'
        
        return {
            'opportunity_score': min(opportunity_score, 100),
            'switching_likelihood': likelihood,
            'primary_drivers': switching_triggers,
            'timeline_estimate': timeline,
            'key_triggers': self._get_switching_triggers(current_solutions),
            'decision_factors': self._get_decision_factors(lead, current_solutions)
        }
    
    def _generate_competitive_positioning(self, current_solutions: List[Dict], lead: Lead) -> Dict[str, Any]:
        """Generate positioning strategy against detected competitors"""
        
        if not current_solutions:
            return {
                'primary_message': 'Next-generation lead intelligence platform',
                'key_differentiators': self.our_positioning['key_differentiators'],
                'value_props': [
                    'AI-powered qualification reduces manual effort by 70%',
                    'Unified platform eliminates tool fragmentation',
                    'Predictive insights improve conversion rates by 40%'
                ]
            }
        
        primary_competitor = current_solutions[0]['solution']
        positioning = {
            'primary_competitor': primary_competitor,
            'competitive_message': self._get_competitive_message(primary_competitor),
            'key_differentiators': self._get_key_differentiators(primary_competitor),
            'migration_benefits': self._get_migration_benefits(primary_competitor, lead),
            'risk_mitigation': self._get_risk_mitigation_points(primary_competitor)
        }
        
        return positioning
    
    def _get_competitive_message(self, competitor: str) -> str:
        """Get primary competitive message against specific competitor"""
        messages = {
            'HubSpot': 'More advanced AI capabilities with better customization at scale',
            'Salesforce': 'Enterprise-grade features with startup-friendly simplicity',
            'Marketo': 'Advanced automation with intuitive user experience',
            'Pardot': 'Platform independence with superior integration capabilities',
            'MailChimp': 'Professional automation features while maintaining ease of use',
            'Pipedrive': 'Complete sales and marketing platform beyond just CRM'
        }
        
        return messages.get(competitor, 'Next-generation platform with AI-powered insights')
    
    def _get_key_differentiators(self, competitor: str) -> List[str]:
        """Get key differentiators against specific competitor"""
        differentiators = {
            'HubSpot': [
                'Advanced AI-powered lead scoring',
                'Better customization for complex workflows',
                'More cost-effective at scale',
                'Superior integration flexibility'
            ],
            'Salesforce': [
                'Simpler setup and configuration',
                'Lower total cost of ownership',
                'Faster time to value',
                'Built-in intelligence without additional modules'
            ],
            'Marketo': [
                'Intuitive user interface',
                'Faster user adoption',
                'More transparent pricing',
                'Better small-to-medium business support'
            ],
            'Pardot': [
                'Platform independence',
                'Better third-party integrations',
                'More flexible deployment options',
                'Superior analytics and reporting'
            ],
            'MailChimp': [
                'Advanced automation capabilities',
                'Professional CRM features',
                'Better segmentation and targeting',
                'Enterprise-grade security'
            ],
            'Pipedrive': [
                'Comprehensive marketing automation',
                'Advanced analytics and insights',
                'Better lead qualification features',
                'Unified sales and marketing platform'
            ]
        }
        
        return differentiators.get(competitor, self.our_positioning['key_differentiators'])
    
    def _get_migration_benefits(self, competitor: str, lead: Lead) -> List[str]:
        """Get specific migration benefits for the lead"""
        company_size = lead.metrics.employee_count or 50
        
        general_benefits = [
            'Reduced manual lead qualification effort',
            'Improved data quality and insights',
            'Better ROI tracking and attribution',
            'Enhanced team productivity'
        ]
        
        # Add size-specific benefits
        if company_size > 100:
            general_benefits.extend([
                'Better scalability for growing teams',
                'Advanced reporting for leadership',
                'Enterprise-grade security and compliance'
            ])
        
        # Add competitor-specific benefits
        competitor_benefits = {
            'HubSpot': [
                'More flexible pricing as you scale',
                'Better API access and customization',
                'Advanced AI features included'
            ],
            'Salesforce': [
                'Significantly lower implementation costs',
                'Faster user adoption and training',
                'All-in-one pricing model'
            ],
            'Marketo': [
                'Easier campaign creation and management',
                'Better user experience and adoption',
                'More transparent and predictable costs'
            ]
        }
        
        specific_benefits = competitor_benefits.get(competitor, [])
        return general_benefits + specific_benefits
    
    def _create_battle_cards(self, current_solutions: List[Dict]) -> List[Dict[str, Any]]:
        """Create battle cards for detected competitors"""
        battle_cards = []
        
        for solution in current_solutions:
            competitor = solution['details']
            
            battle_card = {
                'competitor_name': competitor['name'],
                'category': competitor['category'],
                'our_advantages': [
                    f"Our platform offers {adv}" for adv in self._get_key_differentiators(competitor['name'])[:3]
                ],
                'their_weaknesses': competitor['weaknesses'],
                'common_objections': self._get_common_objections(competitor['name']),
                'proof_points': [
                    '40% faster lead qualification',
                    '60% improvement in lead quality',
                    '50% reduction in manual data entry'
                ],
                'competitive_traps': self._get_competitive_traps(competitor['name']),
                'win_loss_factors': self._get_win_loss_factors(competitor['name'])
            }
            
            battle_cards.append(battle_card)
        
        return battle_cards
    
    def _get_common_objections(self, competitor: str) -> List[Dict[str, str]]:
        """Get common objections when competing against specific competitor"""
        objections = {
            'HubSpot': [
                {'objection': 'We already have HubSpot and it works fine', 'response': 'HubSpot is great for basic needs, but our AI-powered qualification can reduce your manual effort by 70% while improving lead quality.'},
                {'objection': 'HubSpot has all the features we need', 'response': 'What about predictive lead scoring and automated competitive intelligence? These advanced features can significantly boost your conversion rates.'}
            ],
            'Salesforce': [
                {'objection': 'Salesforce is the industry standard', 'response': 'While Salesforce is comprehensive, our solution offers the same enterprise capabilities with 75% faster implementation and significantly lower TCO.'},
                {'objection': 'We have too much invested in Salesforce', 'response': 'We offer seamless data migration and can integrate with your existing Salesforce instance during transition, minimizing disruption.'}
            ]
        }
        
        return objections.get(competitor, [
            {'objection': 'Our current solution works fine', 'response': 'Working fine and optimizing for growth are different. Our platform can help you achieve the next level of efficiency and insights.'}
        ])
    
    def _get_competitive_traps(self, competitor: str) -> List[str]:
        """Get competitive traps to set against competitor"""
        traps = {
            'HubSpot': [
                'Ask about their predictive lead scoring capabilities',
                'Inquire about custom integration flexibility',
                'Discuss enterprise-grade customization options'
            ],
            'Salesforce': [
                'Ask about total implementation cost and timeline',
                'Discuss user adoption rates and training requirements',
                'Inquire about included AI features vs add-on costs'
            ],
            'Marketo': [
                'Ask about user-friendliness for non-technical users',
                'Discuss small business pricing and support',
                'Inquire about campaign creation complexity'
            ]
        }
        
        return traps.get(competitor, [
            'Ask about AI-powered automation capabilities',
            'Discuss predictive analytics and insights',
            'Inquire about all-in-one platform benefits'
        ])
    
    def _get_win_loss_factors(self, competitor: str) -> Dict[str, List[str]]:
        """Get factors that typically lead to wins or losses against competitor"""
        return {
            'win_factors': [
                'Easier implementation and faster time-to-value',
                'Better user experience and adoption',
                'More advanced AI and automation features',
                'Superior customer support and success'
            ],
            'loss_factors': [
                'Existing investment and switching costs',
                'Feature parity perception',
                'Brand recognition and market presence',
                'Integration with existing ecosystem'
            ]
        }
    
    def _recommend_competitive_strategy(self, current_solutions: List[Dict], lead: Lead) -> Dict[str, Any]:
        """Recommend overall competitive strategy"""
        
        if not current_solutions:
            return {
                'strategy': 'greenfield',
                'approach': 'value_selling',
                'key_messages': [
                    'Modern AI-powered approach to lead management',
                    'Unified platform eliminates tool fragmentation',
                    'Predictive insights drive better outcomes'
                ],
                'timeline': 'standard',
                'decision_makers': ['Marketing Director', 'Sales Director', 'Operations']
            }
        
        primary_competitor = current_solutions[0]['solution']
        
        strategies = {
            'HubSpot': {
                'strategy': 'displacement',
                'approach': 'feature_differentiation',
                'key_messages': [
                    'Advanced AI beyond basic automation',
                    'Better scalability and customization',
                    'Superior ROI at enterprise scale'
                ]
            },
            'Salesforce': {
                'strategy': 'simplification',
                'approach': 'ease_of_use',
                'key_messages': [
                    'Get enterprise features without complexity',
                    'Faster implementation and adoption',
                    'Lower total cost of ownership'
                ]
            },
            'Marketo': {
                'strategy': 'modernization',
                'approach': 'user_experience',
                'key_messages': [
                    'Modern interface for better productivity',
                    'Easier campaign management',
                    'Better user adoption and satisfaction'
                ]
            }
        }
        
        return strategies.get(primary_competitor, strategies['HubSpot'])
    
    def _generate_objection_handling(self, current_solutions: List[Dict]) -> List[Dict[str, str]]:
        """Generate objection handling guide"""
        
        common_objections = [
            {
                'objection': 'We\'re happy with our current solution',
                'response': 'That\'s great to hear! Many of our best customers were happy with their previous solutions too. However, they found that our AI-powered approach helped them achieve 40% better results with less manual effort. Would you be interested in seeing how?'
            },
            {
                'objection': 'Switching would be too disruptive',
                'response': 'I understand that concern. That\'s why we\'ve designed our migration process to be seamless. Most customers are up and running within 2 weeks with zero downtime. We also provide dedicated support throughout the transition.'
            },
            {
                'objection': 'Your solution is too expensive',
                'response': 'I appreciate your focus on ROI. When you factor in the time savings from automation and the improved conversion rates, most customers see positive ROI within 3 months. Plus, our flexible pricing scales with your growth.'
            }
        ]
        
        # Add competitor-specific objections
        for solution in current_solutions:
            competitor_objections = self._get_common_objections(solution['solution'])
            common_objections.extend(competitor_objections)
        
        return common_objections
    
    def _generate_proof_points(self, current_solutions: List[Dict], lead: Lead) -> List[Dict[str, Any]]:
        """Generate proof points for competitive situations"""
        
        proof_points = [
            {
                'claim': '70% reduction in manual lead qualification',
                'proof': 'Customer case study with similar company size',
                'relevance': 'high'
            },
            {
                'claim': '40% improvement in lead conversion rates',
                'proof': 'Benchmark study across 100+ customers',
                'relevance': 'high'
            },
            {
                'claim': '60% faster implementation than enterprise solutions',
                'proof': 'Average implementation timeline comparison',
                'relevance': 'medium'
            }
        ]
        
        # Add industry-specific proof points
        if lead.industry:
            industry_proof = {
                'claim': f'Proven results in {lead.industry} industry',
                'proof': f'Case studies from 3 similar {lead.industry} companies',
                'relevance': 'high'
            }
            proof_points.append(industry_proof)
        
        return proof_points
    
    def _get_switching_triggers(self, current_solutions: List[Dict]) -> List[str]:
        """Get common triggers that cause switches from current solutions"""
        triggers = []
        
        for solution in current_solutions:
            competitor = solution['details']
            triggers.extend(competitor['switching_triggers'])
        
        # Remove duplicates while preserving order
        return list(dict.fromkeys(triggers))
    
    def _get_decision_factors(self, lead: Lead, current_solutions: List[Dict]) -> List[str]:
        """Get key decision factors for this lead"""
        factors = ['functionality', 'ease_of_use', 'cost', 'support']
        
        # Add company-size specific factors
        company_size = lead.metrics.employee_count or 50
        
        if company_size > 200:
            factors.extend(['scalability', 'security', 'compliance'])
        elif company_size < 50:
            factors.extend(['simplicity', 'quick_setup', 'affordable_pricing'])
        
        # Add growth-stage specific factors
        if lead.buying_signals.recent_hiring or lead.metrics.last_funding_date:
            factors.extend(['scalability', 'integration_capabilities'])
        
        return list(dict.fromkeys(factors))  # Remove duplicates