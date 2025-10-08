import asyncio
import aiohttp
import json
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import re
from dataclasses import dataclass
from urllib.parse import urlparse
import os
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.lead import Lead, ContactInfo, CompanyMetrics, TechnologyStack, BuyingSignals
from models.company import Company, CompanyIdentifiers, GrowthIndicators

@dataclass
class EnrichmentResult:
    success: bool
    data: Dict[str, Any]
    source: str
    confidence: float
    timestamp: datetime
    error: Optional[str] = None

class DataValidator:
    """Validates and cleans enriched data"""
    
    @staticmethod
    def validate_email(email: str) -> bool:
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_phone(phone: str) -> bool:
        # Remove all non-digit characters
        digits_only = re.sub(r'\D', '', phone)
        return len(digits_only) >= 10
    
    @staticmethod
    def validate_url(url: str) -> bool:
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False
    
    @staticmethod
    def validate_employee_count(count: Union[int, str]) -> Optional[int]:
        if isinstance(count, int):
            return count if 1 <= count <= 1000000 else None
        
        if isinstance(count, str):
            # Handle ranges like "50-100"
            if '-' in count:
                try:
                    parts = count.split('-')
                    return int(parts[0])
                except:
                    return None
            
            # Handle "+" notation like "500+"
            if '+' in count:
                try:
                    return int(count.replace('+', ''))
                except:
                    return None
            
            # Try direct conversion
            try:
                return int(count)
            except:
                return None
        
        return None

class ClearbitEnricher:
    """Enrichment using Clearbit API (mock implementation)"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('CLEARBIT_API_KEY')
        self.base_url = "https://company.clearbit.com/v1/domains/find"
    
    async def enrich_company(self, domain: str) -> EnrichmentResult:
        """Enrich company data using Clearbit"""
        if not self.api_key:
            return self._mock_clearbit_response(domain)
        
        try:
            headers = {'Authorization': f'Bearer {self.api_key}'}
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}?domain={domain}", headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        enriched_data = self._process_clearbit_data(data)
                        return EnrichmentResult(True, enriched_data, "clearbit", 0.9, datetime.now())
                    else:
                        return EnrichmentResult(False, {}, "clearbit", 0.0, datetime.now(), f"API Error: {response.status}")
        except Exception as e:
            return EnrichmentResult(False, {}, "clearbit", 0.0, datetime.now(), str(e))
    
    def _mock_clearbit_response(self, domain: str) -> EnrichmentResult:
        """Mock Clearbit response for demo purposes"""
        company_name = domain.split('.')[0].title()
        
        mock_data = {
            'company_name': f"{company_name} Inc.",
            'industry': 'Technology',
            'employee_count': 150,
            'annual_revenue': 25000000,
            'founded_year': 2015,
            'headquarters': 'San Francisco, CA',
            'description': f"{company_name} is a leading technology company providing innovative solutions for modern businesses.",
            'tech_stack': ['Python', 'React', 'AWS', 'PostgreSQL'],
            'social_media': {
                'linkedin': f"https://linkedin.com/company/{company_name.lower()}",
                'twitter': f"https://twitter.com/{company_name.lower()}"
            }
        }
        
        return EnrichmentResult(True, mock_data, "clearbit_mock", 0.7, datetime.now())
    
    def _process_clearbit_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process Clearbit API response"""
        return {
            'company_name': data.get('name'),
            'industry': data.get('category', {}).get('industry'),
            'employee_count': data.get('metrics', {}).get('employees'),
            'annual_revenue': data.get('metrics', {}).get('annualRevenue'),
            'founded_year': data.get('foundedYear'),
            'headquarters': data.get('geo', {}).get('city'),
            'description': data.get('description'),
            'tech_stack': data.get('tech', []),
            'social_media': {
                'linkedin': data.get('linkedin', {}).get('handle'),
                'twitter': data.get('twitter', {}).get('handle')
            }
        }

class HunterEnricher:
    """Email enrichment using Hunter.io API (mock implementation)"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('HUNTER_API_KEY')
        self.base_url = "https://api.hunter.io/v2"
    
    async def find_emails(self, domain: str, role: Optional[str] = None) -> EnrichmentResult:
        """Find email addresses for a domain"""
        if not self.api_key:
            return self._mock_hunter_response(domain, role)
        
        try:
            params = {'domain': domain, 'api_key': self.api_key}
            if role:
                params['type'] = role
            
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/domain-search", params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        enriched_data = self._process_hunter_data(data)
                        return EnrichmentResult(True, enriched_data, "hunter", 0.8, datetime.now())
                    else:
                        return EnrichmentResult(False, {}, "hunter", 0.0, datetime.now(), f"API Error: {response.status}")
        except Exception as e:
            return EnrichmentResult(False, {}, "hunter", 0.0, datetime.now(), str(e))
    
    def _mock_hunter_response(self, domain: str, role: Optional[str] = None) -> EnrichmentResult:
        """Mock Hunter.io response"""
        company_name = domain.split('.')[0]
        
        mock_emails = [
            {
                'value': f'contact@{domain}',
                'type': 'generic',
                'confidence': 85,
                'first_name': None,
                'last_name': None,
                'position': None
            },
            {
                'value': f'john.doe@{domain}',
                'type': 'personal',
                'confidence': 75,
                'first_name': 'John',
                'last_name': 'Doe',
                'position': 'CEO'
            },
            {
                'value': f'jane.smith@{domain}',
                'type': 'personal',
                'confidence': 70,
                'first_name': 'Jane',
                'last_name': 'Smith',
                'position': 'VP of Sales'
            }
        ]
        
        mock_data = {
            'emails': mock_emails,
            'pattern': '{first}.{last}@{domain}',
            'organization': company_name.title()
        }
        
        return EnrichmentResult(True, mock_data, "hunter_mock", 0.6, datetime.now())
    
    def _process_hunter_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process Hunter.io API response"""
        return {
            'emails': data.get('data', {}).get('emails', []),
            'pattern': data.get('data', {}).get('pattern'),
            'organization': data.get('data', {}).get('organization')
        }

class TechStackDetector:
    """Detect technology stack using various methods"""
    
    def __init__(self):
        self.tech_indicators = {
            'frontend': {
                'react': ['react', 'jsx', 'react-dom'],
                'angular': ['angular', 'ng-', '@angular'],
                'vue': ['vue.js', 'vue', 'vuex'],
                'bootstrap': ['bootstrap', 'btn-primary', 'container-fluid'],
                'tailwind': ['tailwind', 'tw-', 'bg-blue-'],
                'jquery': ['jquery', '$.', 'document.ready']
            },
            'backend': {
                'django': ['django', 'csrf_token', 'django-admin'],
                'rails': ['ruby on rails', 'rails', 'actionpack'],
                'nodejs': ['node.js', 'express', 'npm'],
                'php': ['php', 'laravel', 'symfony'],
                'python': ['python', 'flask', 'fastapi'],
                'java': ['java', 'spring', 'hibernate']
            },
            'analytics': {
                'google-analytics': ['google-analytics', 'gtag', 'ga('],
                'mixpanel': ['mixpanel', 'track'],
                'amplitude': ['amplitude', 'logEvent'],
                'hotjar': ['hotjar', 'hj('],
                'segment': ['segment.com', 'analytics.track']
            },
            'marketing': {
                'hubspot': ['hubspot', 'hs-'],
                'marketo': ['marketo', 'munchkin'],
                'pardot': ['pardot', 'pi.pardot'],
                'mailchimp': ['mailchimp', 'mc_embed'],
                'intercom': ['intercom', 'messenger-launcher']
            },
            'ecommerce': {
                'shopify': ['shopify', 'shop.js'],
                'woocommerce': ['woocommerce', 'wc-'],
                'magento': ['magento', 'mage'],
                'stripe': ['stripe', 'stripe.com'],
                'paypal': ['paypal', 'paypal.com']
            }
        }
    
    def detect_from_html(self, html_content: str) -> Dict[str, List[str]]:
        """Detect technologies from HTML content"""
        html_lower = html_content.lower()
        detected = {category: [] for category in self.tech_indicators}
        
        for category, techs in self.tech_indicators.items():
            for tech, indicators in techs.items():
                for indicator in indicators:
                    if indicator in html_lower:
                        detected[category].append(tech)
                        break
        
        # Remove empty categories
        return {k: v for k, v in detected.items() if v}
    
    def detect_from_headers(self, headers: Dict[str, str]) -> List[str]:
        """Detect technologies from HTTP headers"""
        detected = []
        headers_lower = {k.lower(): v.lower() for k, v in headers.items()}
        
        # Server headers
        server = headers_lower.get('server', '')
        if 'nginx' in server:
            detected.append('nginx')
        if 'apache' in server:
            detected.append('apache')
        if 'cloudflare' in server:
            detected.append('cloudflare')
        
        # Framework headers
        if 'x-powered-by' in headers_lower:
            powered_by = headers_lower['x-powered-by']
            if 'express' in powered_by:
                detected.append('express')
            if 'php' in powered_by:
                detected.append('php')
        
        return detected

class DataEnrichmentService:
    """Main service for enriching lead and company data"""
    
    def __init__(self):
        self.clearbit = ClearbitEnricher()
        self.hunter = HunterEnricher()
        self.tech_detector = TechStackDetector()
        self.validator = DataValidator()
    
    async def enrich_lead(self, lead: Lead) -> Lead:
        """Enrich a lead with additional data from multiple sources"""
        enrichment_tasks = []
        
        # Enrich company data
        if lead.domain:
            enrichment_tasks.append(self.clearbit.enrich_company(lead.domain))
            enrichment_tasks.append(self.hunter.find_emails(lead.domain))
        
        # Execute enrichment tasks concurrently
        results = await asyncio.gather(*enrichment_tasks, return_exceptions=True)
        
        # Process results
        for result in results:
            if isinstance(result, EnrichmentResult) and result.success:
                self._merge_enrichment_data(lead, result)
        
        # Calculate data quality scores
        lead.data_quality_score = self._calculate_data_quality_score(lead)
        lead.completeness_percentage = self._calculate_completeness_percentage(lead)
        lead.last_enriched = datetime.now()
        
        return lead
    
    def _merge_enrichment_data(self, lead: Lead, result: EnrichmentResult):
        """Merge enrichment data into lead object"""
        data = result.data
        
        if result.source.startswith('clearbit'):
            # Merge Clearbit data
            if not lead.company_name and data.get('company_name'):
                lead.company_name = data['company_name']
            
            if not lead.industry and data.get('industry'):
                lead.industry = data['industry']
            
            if not lead.metrics.employee_count and data.get('employee_count'):
                valid_count = self.validator.validate_employee_count(data['employee_count'])
                if valid_count:
                    lead.metrics.employee_count = valid_count
            
            if not lead.headquarters and data.get('headquarters'):
                lead.headquarters = data['headquarters']
            
            if data.get('tech_stack'):
                lead.tech_stack.technologies.extend(data['tech_stack'])
            
            # Add social media links
            if data.get('social_media'):
                lead.social_media_presence.update(data['social_media'])
        
        elif result.source.startswith('hunter'):
            # Merge Hunter.io email data
            emails = data.get('emails', [])
            for email_data in emails:
                email = email_data.get('value')
                if email and self.validator.validate_email(email):
                    contact = ContactInfo(
                        name=f"{email_data.get('first_name', '')} {email_data.get('last_name', '')}".strip(),
                        email=email,
                        title=email_data.get('position')
                    )
                    
                    # Avoid duplicates
                    if not any(c.email == email for c in lead.contacts):
                        lead.contacts.append(contact)
        
        # Add data source
        if result.source not in lead.data_sources:
            lead.data_sources.append(result.source)
    
    def _calculate_data_quality_score(self, lead: Lead) -> float:
        """Calculate data quality score based on validation"""
        total_points = 0
        max_points = 0
        
        # Company name (required)
        max_points += 20
        if lead.company_name and len(lead.company_name.strip()) > 0:
            total_points += 20
        
        # Domain (required)
        max_points += 20
        if lead.domain and self.validator.validate_url(f"https://{lead.domain}"):
            total_points += 20
        
        # Industry
        max_points += 10
        if lead.industry:
            total_points += 10
        
        # Employee count
        max_points += 10
        if lead.metrics.employee_count and lead.metrics.employee_count > 0:
            total_points += 10
        
        # Contact information
        max_points += 15
        valid_contacts = sum(1 for contact in lead.contacts if contact.email and self.validator.validate_email(contact.email))
        if valid_contacts > 0:
            total_points += min(15, valid_contacts * 5)
        
        # Technology stack
        max_points += 10
        if lead.tech_stack.technologies:
            total_points += 10
        
        # Location
        max_points += 5
        if lead.headquarters:
            total_points += 5
        
        # Social presence
        max_points += 10
        if lead.social_media_presence:
            total_points += min(10, len(lead.social_media_presence) * 3)
        
        return (total_points / max_points) * 100 if max_points > 0 else 0
    
    def _calculate_completeness_percentage(self, lead: Lead) -> float:
        """Calculate data completeness percentage"""
        total_fields = 12
        completed_fields = 0
        
        if lead.company_name:
            completed_fields += 1
        if lead.domain:
            completed_fields += 1
        if lead.industry:
            completed_fields += 1
        if lead.metrics.employee_count:
            completed_fields += 1
        if lead.contacts:
            completed_fields += 1
        if lead.tech_stack.technologies:
            completed_fields += 1
        if lead.headquarters:
            completed_fields += 1
        if lead.social_media_presence:
            completed_fields += 1
        if lead.metrics.revenue_range:
            completed_fields += 1
        if lead.metrics.funding_amount:
            completed_fields += 1
        if lead.buying_signals.job_postings:
            completed_fields += 1
        if lead.buying_signals.recent_hiring:
            completed_fields += 1
        
        return (completed_fields / total_fields) * 100
    
    async def batch_enrich_leads(self, leads: List[Lead], max_concurrent: int = 5) -> List[Lead]:
        """Enrich multiple leads concurrently"""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def enrich_with_semaphore(lead):
            async with semaphore:
                return await self.enrich_lead(lead)
        
        tasks = [enrich_with_semaphore(lead) for lead in leads]
        enriched_leads = await asyncio.gather(*tasks)
        
        return enriched_leads
    
    def deduplicate_leads(self, leads: List[Lead]) -> List[Lead]:
        """Remove duplicate leads based on domain"""
        seen_domains = set()
        unique_leads = []
        
        for lead in leads:
            if lead.domain not in seen_domains:
                seen_domains.add(lead.domain)
                unique_leads.append(lead)
        
        return unique_leads
    
    def merge_leads(self, existing_lead: Lead, new_lead: Lead) -> Lead:
        """Merge two leads, keeping the best data from each"""
        # Use the lead with higher data quality as base
        if new_lead.data_quality_score and existing_lead.data_quality_score:
            if new_lead.data_quality_score > existing_lead.data_quality_score:
                base_lead, merge_lead = new_lead, existing_lead
            else:
                base_lead, merge_lead = existing_lead, new_lead
        else:
            base_lead, merge_lead = existing_lead, new_lead
        
        # Merge contacts (avoid duplicates)
        for contact in merge_lead.contacts:
            if not any(c.email == contact.email for c in base_lead.contacts):
                base_lead.contacts.append(contact)
        
        # Merge technology stack
        base_lead.tech_stack.technologies = list(set(
            base_lead.tech_stack.technologies + merge_lead.tech_stack.technologies
        ))
        
        # Merge data sources
        base_lead.data_sources = list(set(
            base_lead.data_sources + merge_lead.data_sources
        ))
        
        # Update timestamp
        base_lead.last_enriched = datetime.now()
        
        return base_lead