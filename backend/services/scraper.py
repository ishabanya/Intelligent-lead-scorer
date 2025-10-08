import asyncio
import aiohttp
import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, urlparse
import time
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class ScrapingResult:
    success: bool
    data: Dict[str, Any]
    source: str
    timestamp: datetime
    error: Optional[str] = None

class RateLimiter:
    def __init__(self, max_requests: int = 10, time_window: int = 60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
    
    async def wait_if_needed(self):
        now = time.time()
        self.requests = [req_time for req_time in self.requests if now - req_time < self.time_window]
        
        if len(self.requests) >= self.max_requests:
            sleep_time = self.time_window - (now - self.requests[0])
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
        
        self.requests.append(now)

class WebScraper:
    def __init__(self):
        self.rate_limiter = RateLimiter()
        self.session = None
        self.cache = {}
        self.cache_ttl = 3600  # 1 hour
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers=self.headers)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def _is_cached(self, url: str) -> bool:
        if url in self.cache:
            cache_time, _ = self.cache[url]
            return (datetime.now() - cache_time).seconds < self.cache_ttl
        return False
    
    def _get_from_cache(self, url: str) -> Optional[Dict[str, Any]]:
        if self._is_cached(url):
            _, data = self.cache[url]
            return data
        return None
    
    def _cache_result(self, url: str, data: Dict[str, Any]):
        self.cache[url] = (datetime.now(), data)
    
    async def scrape_company_website(self, domain: str) -> ScrapingResult:
        """Scrape company website for basic information"""
        await self.rate_limiter.wait_if_needed()
        
        if not domain.startswith(('http://', 'https://')):
            domain = f'https://{domain}'
        
        cached = self._get_from_cache(domain)
        if cached:
            return ScrapingResult(True, cached, "website_cache", datetime.now())
        
        try:
            async with self.session.get(domain, timeout=10) as response:
                if response.status != 200:
                    return ScrapingResult(False, {}, "website", datetime.now(), f"HTTP {response.status}")
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                data = {
                    'company_name': self._extract_company_name(soup, domain),
                    'description': self._extract_description(soup),
                    'industry': self._extract_industry(soup),
                    'technologies': self._extract_technologies(soup),
                    'contact_info': self._extract_contact_info(soup),
                    'social_links': self._extract_social_links(soup),
                    'team_size_indicators': self._extract_team_indicators(soup),
                    'career_page_exists': self._check_career_page(soup, domain),
                    'about_page_content': await self._scrape_about_page(domain)
                }
                
                self._cache_result(domain, data)
                return ScrapingResult(True, data, "website", datetime.now())
                
        except Exception as e:
            return ScrapingResult(False, {}, "website", datetime.now(), str(e))
    
    def _extract_company_name(self, soup: BeautifulSoup, domain: str) -> Optional[str]:
        """Extract company name from various sources"""
        # Try title tag
        title = soup.find('title')
        if title:
            title_text = title.get_text().strip()
            # Clean up common title patterns
            name = re.sub(r'\s*[-|]\s*(Home|Homepage|Welcome).*$', '', title_text, flags=re.IGNORECASE)
            if name and len(name) < 100:
                return name
        
        # Try meta property
        og_title = soup.find('meta', property='og:title')
        if og_title and og_title.get('content'):
            return og_title['content'].strip()
        
        # Try h1 with company indicators
        h1_tags = soup.find_all('h1')
        for h1 in h1_tags:
            text = h1.get_text().strip()
            if any(word in text.lower() for word in ['welcome', 'company', 'about']):
                return text
        
        # Fallback to domain name
        domain_name = urlparse(domain).netloc.replace('www.', '').split('.')[0]
        return domain_name.title()
    
    def _extract_description(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract company description"""
        # Try meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            return meta_desc['content'].strip()
        
        # Try og:description
        og_desc = soup.find('meta', property='og:description')
        if og_desc and og_desc.get('content'):
            return og_desc['content'].strip()
        
        # Try to find description in common sections
        for selector in ['.hero-description', '.company-description', '.about-text', '.intro']:
            element = soup.select_one(selector)
            if element:
                text = element.get_text().strip()
                if 50 < len(text) < 500:
                    return text
        
        return None
    
    def _extract_industry(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract industry information"""
        # Look for industry keywords in text
        industry_keywords = {
            'saas': 'Software',
            'software': 'Software',
            'fintech': 'Financial Technology',
            'healthcare': 'Healthcare',
            'ecommerce': 'E-commerce',
            'marketing': 'Marketing',
            'analytics': 'Analytics',
            'consulting': 'Consulting',
            'education': 'Education',
            'real estate': 'Real Estate'
        }
        
        text = soup.get_text().lower()
        for keyword, industry in industry_keywords.items():
            if keyword in text:
                return industry
        
        return None
    
    def _extract_technologies(self, soup: BeautifulSoup) -> List[str]:
        """Extract technology stack indicators"""
        technologies = []
        
        # Check for common tech indicators in HTML
        html_str = str(soup).lower()
        
        tech_patterns = {
            'react': r'react[.\s]',
            'angular': r'angular[.\s]',
            'vue': r'vue[.\s]',
            'bootstrap': r'bootstrap[.\s]',
            'jquery': r'jquery[.\s]',
            'google-analytics': r'google-analytics|gtag|ga\(',
            'hubspot': r'hubspot',
            'salesforce': r'salesforce',
            'stripe': r'stripe',
            'intercom': r'intercom',
            'zendesk': r'zendesk'
        }
        
        for tech, pattern in tech_patterns.items():
            if re.search(pattern, html_str):
                technologies.append(tech)
        
        return technologies
    
    def _extract_contact_info(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract contact information"""
        contact_info = {}
        
        # Email patterns
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, soup.get_text())
        if emails:
            # Filter out common non-contact emails
            filtered_emails = [email for email in emails if not any(
                exclude in email.lower() for exclude in ['noreply', 'no-reply', 'example', 'test']
            )]
            if filtered_emails:
                contact_info['email'] = filtered_emails[0]
        
        # Phone patterns
        phone_pattern = r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b'
        phones = re.findall(phone_pattern, soup.get_text())
        if phones:
            contact_info['phone'] = f"({phones[0][0]}) {phones[0][1]}-{phones[0][2]}"
        
        return contact_info
    
    def _extract_social_links(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract social media links"""
        social_links = {}
        
        social_patterns = {
            'linkedin': r'linkedin\.com/company/([^/\s"]+)',
            'twitter': r'twitter\.com/([^/\s"]+)',
            'facebook': r'facebook\.com/([^/\s"]+)',
            'instagram': r'instagram\.com/([^/\s"]+)'
        }
        
        html_str = str(soup)
        for platform, pattern in social_patterns.items():
            match = re.search(pattern, html_str, re.IGNORECASE)
            if match:
                social_links[platform] = match.group(0)
        
        return social_links
    
    def _extract_team_indicators(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract team size indicators"""
        text = soup.get_text().lower()
        
        # Look for team size mentions
        team_patterns = [
            r'(\d+)\+?\s*(?:person|people|employee|team member|staff)',
            r'team\s*of\s*(\d+)',
            r'(\d+)[-\s]*person\s*team'
        ]
        
        for pattern in team_patterns:
            match = re.search(pattern, text)
            if match:
                size = int(match.group(1))
                if 1 <= size <= 10000:  # Reasonable range
                    return {'estimated_size': size, 'confidence': 'medium'}
        
        # Look for team page indicators
        if any(word in text for word in ['our team', 'meet the team', 'about us', 'leadership']):
            return {'has_team_page': True}
        
        return {}
    
    def _check_career_page(self, soup: BeautifulSoup, domain: str) -> bool:
        """Check if company has a career page"""
        # Look for career/jobs links
        links = soup.find_all('a', href=True)
        career_keywords = ['career', 'job', 'hiring', 'join', 'work', 'opportunity']
        
        for link in links:
            href = link['href'].lower()
            text = link.get_text().lower()
            if any(keyword in href or keyword in text for keyword in career_keywords):
                return True
        
        return False
    
    async def _scrape_about_page(self, domain: str) -> Optional[str]:
        """Scrape about page for additional company information"""
        about_urls = [
            urljoin(domain, '/about'),
            urljoin(domain, '/about-us'),
            urljoin(domain, '/company'),
            urljoin(domain, '/who-we-are')
        ]
        
        for url in about_urls:
            try:
                async with self.session.get(url, timeout=5) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Remove script and style elements
                        for script in soup(["script", "style"]):
                            script.decompose()
                        
                        text = soup.get_text()
                        # Clean up whitespace
                        text = ' '.join(text.split())
                        
                        if len(text) > 100:
                            return text[:1000]  # Limit length
            except:
                continue
        
        return None
    
    async def scrape_linkedin_company(self, company_url: str) -> ScrapingResult:
        """Scrape LinkedIn company page (basic information only due to restrictions)"""
        await self.rate_limiter.wait_if_needed()
        
        cached = self._get_from_cache(company_url)
        if cached:
            return ScrapingResult(True, cached, "linkedin_cache", datetime.now())
        
        try:
            # Note: LinkedIn heavily restricts scraping. This is a basic implementation
            # that would need to be enhanced with proper authentication for real use.
            async with self.session.get(company_url, timeout=10) as response:
                if response.status != 200:
                    return ScrapingResult(False, {}, "linkedin", datetime.now(), f"HTTP {response.status}")
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                data = {
                    'company_name': self._extract_linkedin_company_name(soup),
                    'follower_count': self._extract_linkedin_followers(soup),
                    'industry': self._extract_linkedin_industry(soup),
                    'company_size': self._extract_linkedin_size(soup),
                    'description': self._extract_linkedin_description(soup)
                }
                
                self._cache_result(company_url, data)
                return ScrapingResult(True, data, "linkedin", datetime.now())
                
        except Exception as e:
            return ScrapingResult(False, {}, "linkedin", datetime.now(), str(e))
    
    def _extract_linkedin_company_name(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract company name from LinkedIn"""
        # This would need to be updated based on LinkedIn's current HTML structure
        title = soup.find('title')
        if title:
            return title.get_text().split('|')[0].strip()
        return None
    
    def _extract_linkedin_followers(self, soup: BeautifulSoup) -> Optional[int]:
        """Extract follower count from LinkedIn"""
        # Look for follower count patterns
        text = soup.get_text()
        follower_pattern = r'([\d,]+)\s*followers?'
        match = re.search(follower_pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1).replace(',', ''))
        return None
    
    def _extract_linkedin_industry(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract industry from LinkedIn"""
        # This would need specific selectors based on LinkedIn's structure
        return None
    
    def _extract_linkedin_size(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract company size from LinkedIn"""
        text = soup.get_text()
        size_patterns = [
            r'(\d+[-–]\d+)\s*employees?',
            r'(\d+\+)\s*employees?'
        ]
        for pattern in size_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
    
    def _extract_linkedin_description(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract company description from LinkedIn"""
        # This would need specific selectors
        return None

    async def scrape_job_postings(self, company_name: str) -> ScrapingResult:
        """Scrape job postings to identify hiring signals"""
        await self.rate_limiter.wait_if_needed()
        
        try:
            # Search for jobs from the company
            search_query = f"{company_name} jobs"
            # This is a simplified implementation - would need actual job board APIs
            
            data = {
                'job_count': 0,
                'recent_postings': [],
                'hiring_roles': [],
                'locations': []
            }
            
            return ScrapingResult(True, data, "job_boards", datetime.now())
            
        except Exception as e:
            return ScrapingResult(False, {}, "job_boards", datetime.now(), str(e))

class CompanyScraper:
    """Main orchestrator for scraping company data from multiple sources"""
    
    def __init__(self):
        self.scraper = WebScraper()
    
    async def scrape_company_data(self, domain: str, linkedin_url: Optional[str] = None) -> Dict[str, ScrapingResult]:
        """Scrape company data from all available sources"""
        results = {}
        
        async with self.scraper:
            # Scrape website
            website_result = await self.scraper.scrape_company_website(domain)
            results['website'] = website_result
            
            # Scrape LinkedIn if URL provided
            if linkedin_url:
                linkedin_result = await self.scraper.scrape_linkedin_company(linkedin_url)
                results['linkedin'] = linkedin_result
            
            # Scrape job postings
            if website_result.success and website_result.data.get('company_name'):
                job_result = await self.scraper.scrape_job_postings(website_result.data['company_name'])
                results['jobs'] = job_result
        
        return results