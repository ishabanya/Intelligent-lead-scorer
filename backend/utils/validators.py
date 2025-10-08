import re
import validators
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.lead import Lead

class DataValidator:
    """Comprehensive data validation utilities"""
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email address format"""
        if not email or not isinstance(email, str):
            return False
        
        # Basic email regex pattern
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        # Check format
        if not re.match(pattern, email):
            return False
        
        # Additional checks
        if len(email) > 254:  # RFC 5321 limit
            return False
        
        # Check for common invalid patterns
        invalid_patterns = [
            r'\.{2,}',  # Multiple consecutive dots
            r'^\.|\.$',  # Starts or ends with dot
            r'@.*@',  # Multiple @ symbols
        ]
        
        for invalid_pattern in invalid_patterns:
            if re.search(invalid_pattern, email):
                return False
        
        return True
    
    @staticmethod
    def validate_domain(domain: str) -> bool:
        """Validate domain name format"""
        if not domain or not isinstance(domain, str):
            return False
        
        # Remove protocol if present
        domain = domain.replace('http://', '').replace('https://', '').replace('www.', '')
        
        # Basic domain validation
        domain_pattern = r'^[a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9]?\.[a-zA-Z]{2,}$'
        
        if not re.match(domain_pattern, domain):
            return False
        
        # Check for valid TLD
        parts = domain.split('.')
        if len(parts) < 2:
            return False
        
        tld = parts[-1].lower()
        if len(tld) < 2 or not tld.isalpha():
            return False
        
        return True
    
    @staticmethod
    def validate_url(url: str) -> bool:
        """Validate URL format"""
        if not url or not isinstance(url, str):
            return False
        
        try:
            return validators.url(url)
        except Exception:
            return False
    
    @staticmethod
    def validate_linkedin_url(url: str) -> bool:
        """Validate LinkedIn company URL format"""
        if not DataValidator.validate_url(url):
            return False
        
        parsed = urlparse(url.lower())
        
        # Check domain
        if parsed.netloc not in ['linkedin.com', 'www.linkedin.com']:
            return False
        
        # Check path pattern for company pages
        company_pattern = r'^/company/[a-zA-Z0-9-]+/?$'
        if not re.match(company_pattern, parsed.path):
            return False
        
        return True
    
    @staticmethod
    def validate_phone(phone: str) -> bool:
        """Validate phone number format"""
        if not phone or not isinstance(phone, str):
            return False
        
        # Remove common formatting characters
        cleaned = re.sub(r'[\s\(\)\-\.\+]', '', phone)
        
        # Check if remaining characters are digits
        if not cleaned.isdigit():
            return False
        
        # Check length (most phone numbers are 7-15 digits)
        if len(cleaned) < 7 or len(cleaned) > 15:
            return False
        
        return True
    
    @staticmethod
    def validate_employee_count(count: Any) -> Optional[int]:
        """Validate and normalize employee count"""
        if count is None:
            return None
        
        if isinstance(count, int):
            return count if 0 <= count <= 10000000 else None
        
        if isinstance(count, str):
            count = count.strip()
            
            # Handle range formats like "50-100", "100-200"
            if '-' in count:
                try:
                    parts = count.split('-')
                    if len(parts) == 2:
                        min_count = int(parts[0].strip())
                        return min_count if 0 <= min_count <= 10000000 else None
                except ValueError:
                    pass
            
            # Handle "+" notation like "500+"
            if count.endswith('+'):
                try:
                    base_count = int(count[:-1].strip())
                    return base_count if 0 <= base_count <= 10000000 else None
                except ValueError:
                    pass
            
            # Handle comma-separated numbers like "1,000"
            count_clean = count.replace(',', '')
            try:
                numeric_count = int(count_clean)
                return numeric_count if 0 <= numeric_count <= 10000000 else None
            except ValueError:
                pass
        
        return None
    
    @staticmethod
    def validate_revenue(revenue: Any) -> Optional[float]:
        """Validate and normalize revenue amount"""
        if revenue is None:
            return None
        
        if isinstance(revenue, (int, float)):
            return float(revenue) if revenue >= 0 else None
        
        if isinstance(revenue, str):
            revenue = revenue.strip().replace(',', '').replace('$', '')
            
            # Handle millions/billions notation
            multipliers = {
                'k': 1000,
                'm': 1000000,
                'b': 1000000000,
                'million': 1000000,
                'billion': 1000000000
            }
            
            for suffix, multiplier in multipliers.items():
                if revenue.lower().endswith(suffix):
                    try:
                        base_amount = float(revenue[:-len(suffix)].strip())
                        return base_amount * multiplier
                    except ValueError:
                        continue
            
            # Try direct conversion
            try:
                return float(revenue) if float(revenue) >= 0 else None
            except ValueError:
                pass
        
        return None
    
    @staticmethod
    def validate_industry(industry: str) -> bool:
        """Validate industry classification"""
        if not industry or not isinstance(industry, str):
            return False
        
        # Basic validation - industry should be reasonable length and format
        industry = industry.strip()
        
        if len(industry) < 2 or len(industry) > 100:
            return False
        
        # Should contain mostly letters, spaces, and basic punctuation
        pattern = r'^[a-zA-Z\s\-&/,\.]+$'
        return bool(re.match(pattern, industry))
    
    @staticmethod
    def validate_funding_stage(stage: str) -> bool:
        """Validate funding stage"""
        if not stage or not isinstance(stage, str):
            return False
        
        valid_stages = {
            'bootstrap', 'bootstrapped', 'self-funded',
            'pre-seed', 'seed', 'series a', 'series b', 'series c', 'series d',
            'series e', 'series f', 'late stage', 'ipo', 'acquired', 'public'
        }
        
        return stage.lower().strip() in valid_stages

class LeadValidator:
    """Specific validation for Lead objects"""
    
    @staticmethod
    def validate_lead(lead: Lead) -> Dict[str, Any]:
        """Comprehensive lead validation"""
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'score': 100
        }
        
        # Required field validation
        if not lead.company_name or not lead.company_name.strip():
            validation_result['errors'].append("Company name is required")
            validation_result['is_valid'] = False
            validation_result['score'] -= 20
        
        if not lead.domain:
            validation_result['errors'].append("Domain is required")
            validation_result['is_valid'] = False
            validation_result['score'] -= 20
        elif not DataValidator.validate_domain(lead.domain):
            validation_result['errors'].append("Invalid domain format")
            validation_result['is_valid'] = False
            validation_result['score'] -= 15
        
        # Optional field validation
        if lead.industry and not DataValidator.validate_industry(lead.industry):
            validation_result['warnings'].append("Industry format may be invalid")
            validation_result['score'] -= 5
        
        # Contact validation
        for i, contact in enumerate(lead.contacts):
            if contact.email and not DataValidator.validate_email(contact.email):
                validation_result['warnings'].append(f"Contact {i+1} has invalid email format")
                validation_result['score'] -= 5
            
            if contact.linkedin_url and not DataValidator.validate_linkedin_url(str(contact.linkedin_url)):
                validation_result['warnings'].append(f"Contact {i+1} has invalid LinkedIn URL")
                validation_result['score'] -= 3
        
        # Metrics validation
        if lead.metrics.employee_count is not None:
            validated_count = DataValidator.validate_employee_count(lead.metrics.employee_count)
            if validated_count is None:
                validation_result['warnings'].append("Employee count format may be invalid")
                validation_result['score'] -= 5
        
        # Data quality checks
        if lead.data_quality_score is not None and (lead.data_quality_score < 0 or lead.data_quality_score > 100):
            validation_result['warnings'].append("Data quality score should be between 0-100")
            validation_result['score'] -= 5
        
        if lead.lead_score is not None and (lead.lead_score < 0 or lead.lead_score > 100):
            validation_result['warnings'].append("Lead score should be between 0-100")
            validation_result['score'] -= 5
        
        # Technology stack validation
        tech_count = (
            len(lead.tech_stack.technologies) +
            len(lead.tech_stack.marketing_tools) +
            len(lead.tech_stack.sales_tools) +
            len(lead.tech_stack.analytics_tools)
        )
        
        if tech_count == 0:
            validation_result['warnings'].append("No technology information available")
            validation_result['score'] -= 10
        
        # Social media validation
        for platform, url in lead.social_media_presence.items():
            if url and not DataValidator.validate_url(url):
                validation_result['warnings'].append(f"Invalid {platform} URL")
                validation_result['score'] -= 3
        
        # Ensure score doesn't go below 0
        validation_result['score'] = max(0, validation_result['score'])
        
        return validation_result
    
    @staticmethod
    def suggest_improvements(lead: Lead) -> List[str]:
        """Suggest improvements for lead data quality"""
        suggestions = []
        
        # Missing critical information
        if not lead.industry:
            suggestions.append("Add industry classification for better targeting")
        
        if not lead.headquarters:
            suggestions.append("Add headquarters location for geographic targeting")
        
        if not lead.contacts:
            suggestions.append("Find contact information for key decision makers")
        
        if not lead.metrics.employee_count:
            suggestions.append("Determine company size for better qualification")
        
        # Empty technology stack
        tech_count = (
            len(lead.tech_stack.technologies) +
            len(lead.tech_stack.marketing_tools) +
            len(lead.tech_stack.sales_tools)
        )
        
        if tech_count == 0:
            suggestions.append("Research technology stack for compatibility assessment")
        
        # No buying signals
        if not lead.buying_signals.job_postings and not lead.buying_signals.recent_hiring:
            suggestions.append("Monitor for hiring activity and job postings")
        
        # No social presence
        if not lead.social_media_presence:
            suggestions.append("Find social media profiles for engagement opportunities")
        
        # Low data quality
        if lead.data_quality_score and lead.data_quality_score < 60:
            suggestions.append("Improve data quality by filling missing information")
        
        return suggestions

class BulkValidator:
    """Validation for bulk operations"""
    
    @staticmethod
    def validate_csv_headers(headers: List[str]) -> Dict[str, Any]:
        """Validate CSV headers for bulk import"""
        required_headers = ['domain']
        optional_headers = ['company_name', 'industry', 'headquarters', 'employee_count']
        
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'missing_required': [],
            'unrecognized': []
        }
        
        headers_lower = [h.lower().strip() for h in headers]
        
        # Check required headers
        for required in required_headers:
            if required not in headers_lower:
                validation_result['missing_required'].append(required)
                validation_result['is_valid'] = False
        
        # Check for unrecognized headers
        all_known_headers = required_headers + optional_headers
        for header in headers_lower:
            if header not in all_known_headers:
                validation_result['unrecognized'].append(header)
        
        if validation_result['missing_required']:
            validation_result['errors'].append(f"Missing required columns: {', '.join(validation_result['missing_required'])}")
        
        if validation_result['unrecognized']:
            validation_result['warnings'].append(f"Unrecognized columns will be ignored: {', '.join(validation_result['unrecognized'])}")
        
        return validation_result
    
    @staticmethod
    def validate_bulk_leads(leads_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate bulk lead data"""
        validation_result = {
            'total_count': len(leads_data),
            'valid_count': 0,
            'invalid_count': 0,
            'errors': [],
            'warnings': [],
            'lead_validations': []
        }
        
        for i, lead_data in enumerate(leads_data):
            try:
                # Create lead object
                lead = Lead(**lead_data)
                
                # Validate lead
                lead_validation = LeadValidator.validate_lead(lead)
                lead_validation['row_number'] = i + 1
                lead_validation['company_name'] = lead.company_name
                
                validation_result['lead_validations'].append(lead_validation)
                
                if lead_validation['is_valid']:
                    validation_result['valid_count'] += 1
                else:
                    validation_result['invalid_count'] += 1
            
            except Exception as e:
                validation_result['invalid_count'] += 1
                validation_result['errors'].append(f"Row {i + 1}: {str(e)}")
        
        return validation_result