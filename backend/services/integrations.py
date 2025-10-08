from typing import Dict, List, Optional, Any
import aiohttp
import json
from datetime import datetime
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.lead import Lead
from utils.exporters import CRMExporter

class CRMIntegration:
    """Base class for CRM integrations"""
    
    def __init__(self, api_key: str = None, base_url: str = None):
        self.api_key = api_key
        self.base_url = base_url
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def sync_leads(self, leads: List[Lead]) -> Dict[str, Any]:
        """Sync leads to CRM - to be implemented by subclasses"""
        raise NotImplementedError
    
    async def test_connection(self) -> bool:
        """Test CRM connection"""
        raise NotImplementedError

class HubSpotIntegration(CRMIntegration):
    """HubSpot CRM integration"""
    
    def __init__(self, api_key: str = None):
        super().__init__(api_key, "https://api.hubapi.com")
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    async def test_connection(self) -> bool:
        """Test HubSpot API connection"""
        if not self.api_key:
            return False
        
        try:
            async with self.session.get(
                f"{self.base_url}/crm/v3/owners",
                headers=self.headers
            ) as response:
                return response.status == 200
        except Exception:
            return False
    
    async def sync_leads(self, leads: List[Lead]) -> Dict[str, Any]:
        """Sync leads to HubSpot as companies and contacts"""
        results = {
            "synced_count": 0,
            "failed_count": 0,
            "errors": [],
            "created_companies": [],
            "created_contacts": []
        }
        
        for lead in leads:
            try:
                # Create company
                company_data = self._prepare_company_data(lead)
                company_result = await self._create_company(company_data)
                
                if company_result["success"]:
                    results["created_companies"].append(company_result["id"])
                    
                    # Create contacts associated with company
                    for contact in lead.contacts:
                        if contact.email:
                            contact_data = self._prepare_contact_data(contact, lead, company_result["id"])
                            contact_result = await self._create_contact(contact_data)
                            
                            if contact_result["success"]:
                                results["created_contacts"].append(contact_result["id"])
                    
                    results["synced_count"] += 1
                else:
                    results["failed_count"] += 1
                    results["errors"].append(f"{lead.company_name}: {company_result['error']}")
            
            except Exception as e:
                results["failed_count"] += 1
                results["errors"].append(f"{lead.company_name}: {str(e)}")
        
        return results
    
    async def _create_company(self, company_data: Dict) -> Dict[str, Any]:
        """Create company in HubSpot"""
        try:
            async with self.session.post(
                f"{self.base_url}/crm/v3/objects/companies",
                headers=self.headers,
                json=company_data
            ) as response:
                if response.status == 201:
                    result = await response.json()
                    return {"success": True, "id": result["id"]}
                else:
                    error_text = await response.text()
                    return {"success": False, "error": error_text}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _create_contact(self, contact_data: Dict) -> Dict[str, Any]:
        """Create contact in HubSpot"""
        try:
            async with self.session.post(
                f"{self.base_url}/crm/v3/objects/contacts",
                headers=self.headers,
                json=contact_data
            ) as response:
                if response.status == 201:
                    result = await response.json()
                    return {"success": True, "id": result["id"]}
                else:
                    error_text = await response.text()
                    return {"success": False, "error": error_text}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _prepare_company_data(self, lead: Lead) -> Dict:
        """Prepare company data for HubSpot"""
        properties = {
            "name": lead.company_name,
            "domain": lead.domain,
            "industry": lead.industry or "",
            "numberofemployees": lead.metrics.employee_count or "",
            "city": "",
            "state": "",
            "country": ""
        }
        
        # Parse headquarters
        if lead.headquarters:
            location_parts = lead.headquarters.split(", ")
            if len(location_parts) >= 1:
                properties["city"] = location_parts[0]
            if len(location_parts) >= 2:
                properties["state"] = location_parts[1]
            if len(location_parts) >= 3:
                properties["country"] = location_parts[2]
        
        # Add custom properties
        properties.update({
            "lead_score": lead.lead_score or 0,
            "qualification_status": lead.qualification_status.value if lead.qualification_status else "Unqualified",
            "data_quality_score": lead.data_quality_score or 0,
            "technologies": ", ".join(lead.tech_stack.technologies) if lead.tech_stack.technologies else "",
            "last_enriched": lead.last_enriched.isoformat() if lead.last_enriched else ""
        })
        
        return {"properties": properties}
    
    def _prepare_contact_data(self, contact, lead: Lead, company_id: str) -> Dict:
        """Prepare contact data for HubSpot"""
        properties = {
            "email": contact.email,
            "firstname": contact.name.split()[0] if contact.name else "",
            "lastname": " ".join(contact.name.split()[1:]) if contact.name and len(contact.name.split()) > 1 else "",
            "jobtitle": contact.title or "",
            "company": lead.company_name
        }
        
        return {
            "properties": properties,
            "associations": [
                {
                    "to": {"id": company_id},
                    "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 1}]
                }
            ]
        }

class SalesforceIntegration(CRMIntegration):
    """Salesforce CRM integration"""
    
    def __init__(self, instance_url: str = None, access_token: str = None):
        super().__init__(access_token, instance_url)
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
    
    async def test_connection(self) -> bool:
        """Test Salesforce API connection"""
        if not self.api_key or not self.base_url:
            return False
        
        try:
            async with self.session.get(
                f"{self.base_url}/services/data/v52.0/sobjects/Account/describe",
                headers=self.headers
            ) as response:
                return response.status == 200
        except Exception:
            return False
    
    async def sync_leads(self, leads: List[Lead]) -> Dict[str, Any]:
        """Sync leads to Salesforce as Leads or Accounts"""
        results = {
            "synced_count": 0,
            "failed_count": 0,
            "errors": [],
            "created_leads": []
        }
        
        for lead in leads:
            try:
                # Create lead record
                lead_data = self._prepare_lead_data(lead)
                lead_result = await self._create_lead(lead_data)
                
                if lead_result["success"]:
                    results["created_leads"].append(lead_result["id"])
                    results["synced_count"] += 1
                else:
                    results["failed_count"] += 1
                    results["errors"].append(f"{lead.company_name}: {lead_result['error']}")
            
            except Exception as e:
                results["failed_count"] += 1
                results["errors"].append(f"{lead.company_name}: {str(e)}")
        
        return results
    
    async def _create_lead(self, lead_data: Dict) -> Dict[str, Any]:
        """Create lead in Salesforce"""
        try:
            async with self.session.post(
                f"{self.base_url}/services/data/v52.0/sobjects/Lead",
                headers=self.headers,
                json=lead_data
            ) as response:
                if response.status == 201:
                    result = await response.json()
                    return {"success": True, "id": result["id"]}
                else:
                    error_text = await response.text()
                    return {"success": False, "error": error_text}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _prepare_lead_data(self, lead: Lead) -> Dict:
        """Prepare lead data for Salesforce"""
        # Use first contact or create placeholder
        primary_contact = lead.contacts[0] if lead.contacts else None
        
        data = {
            "Company": lead.company_name,
            "Website": f"https://{lead.domain}",
            "Industry": lead.industry or "",
            "NumberOfEmployees": lead.metrics.employee_count,
            "LeadSource": "Lead Scorer Tool"
        }
        
        # Add contact information
        if primary_contact:
            if primary_contact.name:
                name_parts = primary_contact.name.split()
                data["FirstName"] = name_parts[0]
                data["LastName"] = " ".join(name_parts[1:]) if len(name_parts) > 1 else "Unknown"
            else:
                data["FirstName"] = "Unknown"
                data["LastName"] = "Contact"
            
            data["Email"] = primary_contact.email or ""
            data["Title"] = primary_contact.title or ""
        else:
            data["FirstName"] = "Unknown"
            data["LastName"] = "Contact"
            data["Email"] = f"contact@{lead.domain}"
        
        # Parse location
        if lead.headquarters:
            location_parts = lead.headquarters.split(", ")
            if len(location_parts) >= 1:
                data["City"] = location_parts[0]
            if len(location_parts) >= 2:
                data["State"] = location_parts[1]
            if len(location_parts) >= 3:
                data["Country"] = location_parts[2]
        
        # Add qualification info
        rating_map = {
            "Hot": "Hot",
            "Warm": "Warm", 
            "Cold": "Cold",
            "Unqualified": "Unqualified"
        }
        
        if lead.qualification_status:
            data["Rating"] = rating_map.get(lead.qualification_status.value, "Unqualified")
        
        # Add description with lead intelligence
        description_parts = [f"Lead Score: {lead.lead_score or 0}/100"]
        
        if lead.tech_stack.technologies:
            description_parts.append(f"Technologies: {', '.join(lead.tech_stack.technologies[:5])}")
        
        if lead.buying_signals.recent_hiring:
            description_parts.append(f"Recent Hiring: {lead.buying_signals.recent_hiring} positions")
        
        data["Description"] = " | ".join(description_parts)
        
        return data

class WebhookManager:
    """Manage webhooks for real-time integrations"""
    
    def __init__(self):
        self.webhooks = {}
        self.event_handlers = {
            "lead_scored": [],
            "lead_qualified": [],
            "lead_updated": [],
            "batch_processed": []
        }
    
    def register_webhook(self, webhook_id: str, url: str, events: List[str], secret: str = None):
        """Register a new webhook"""
        self.webhooks[webhook_id] = {
            "url": url,
            "events": events,
            "secret": secret,
            "created_at": datetime.now(),
            "active": True
        }
    
    async def trigger_webhook(self, event_type: str, data: Dict[str, Any]):
        """Trigger webhooks for a specific event"""
        if event_type not in self.event_handlers:
            return
        
        # Find webhooks subscribed to this event
        relevant_webhooks = [
            webhook for webhook in self.webhooks.values()
            if event_type in webhook["events"] and webhook["active"]
        ]
        
        # Send webhook notifications
        results = []
        async with aiohttp.ClientSession() as session:
            for webhook in relevant_webhooks:
                try:
                    payload = {
                        "event": event_type,
                        "timestamp": datetime.now().isoformat(),
                        "data": data
                    }
                    
                    headers = {"Content-Type": "application/json"}
                    if webhook["secret"]:
                        # Add webhook signature if secret is provided
                        import hmac
                        import hashlib
                        signature = hmac.new(
                            webhook["secret"].encode(),
                            json.dumps(payload).encode(),
                            hashlib.sha256
                        ).hexdigest()
                        headers["X-Webhook-Signature"] = f"sha256={signature}"
                    
                    async with session.post(
                        webhook["url"],
                        json=payload,
                        headers=headers,
                        timeout=10
                    ) as response:
                        results.append({
                            "url": webhook["url"],
                            "status": response.status,
                            "success": response.status < 400
                        })
                
                except Exception as e:
                    results.append({
                        "url": webhook["url"],
                        "error": str(e),
                        "success": False
                    })
        
        return results

class ZapierIntegration:
    """Zapier integration endpoints"""
    
    @staticmethod
    def get_trigger_endpoints():
        """Get available Zapier trigger endpoints"""
        return {
            "new_hot_lead": {
                "description": "Triggers when a new hot lead is identified",
                "sample_data": {
                    "id": "lead_123",
                    "company_name": "Example Corp",
                    "domain": "example.com",
                    "lead_score": 85,
                    "qualification_status": "Hot",
                    "created_at": "2024-01-01T12:00:00Z"
                }
            },
            "lead_qualified": {
                "description": "Triggers when a lead changes qualification status",
                "sample_data": {
                    "id": "lead_123",
                    "company_name": "Example Corp",
                    "old_status": "Warm",
                    "new_status": "Hot",
                    "lead_score": 85,
                    "updated_at": "2024-01-01T12:00:00Z"
                }
            },
            "batch_completed": {
                "description": "Triggers when a batch processing job completes",
                "sample_data": {
                    "batch_id": "batch_123",
                    "total_leads": 50,
                    "qualified_leads": 12,
                    "completed_at": "2024-01-01T12:00:00Z"
                }
            }
        }
    
    @staticmethod
    def get_action_endpoints():
        """Get available Zapier action endpoints"""
        return {
            "create_lead": {
                "description": "Create and score a new lead",
                "required_fields": ["company_name", "domain"],
                "optional_fields": ["industry", "headquarters", "linkedin_url"]
            },
            "update_lead": {
                "description": "Update an existing lead",
                "required_fields": ["lead_id"],
                "optional_fields": ["company_name", "industry", "headquarters"]
            },
            "get_lead_score": {
                "description": "Get the current score for a lead",
                "required_fields": ["lead_id"],
                "returns": ["lead_score", "qualification_status", "score_breakdown"]
            }
        }

class IntegrationManager:
    """Main manager for all integrations"""
    
    def __init__(self):
        self.webhook_manager = WebhookManager()
        self.crm_integrations = {}
    
    def add_crm_integration(self, name: str, integration: CRMIntegration):
        """Add a CRM integration"""
        self.crm_integrations[name] = integration
    
    async def sync_to_crm(self, crm_name: str, leads: List[Lead]) -> Dict[str, Any]:
        """Sync leads to specified CRM"""
        if crm_name not in self.crm_integrations:
            return {"error": f"CRM integration '{crm_name}' not found"}
        
        integration = self.crm_integrations[crm_name]
        
        async with integration:
            # Test connection first
            connection_ok = await integration.test_connection()
            if not connection_ok:
                return {"error": f"Failed to connect to {crm_name}"}
            
            # Sync leads
            result = await integration.sync_leads(leads)
            
            # Trigger webhook if successful
            if result["synced_count"] > 0:
                await self.webhook_manager.trigger_webhook("leads_synced", {
                    "crm": crm_name,
                    "synced_count": result["synced_count"],
                    "timestamp": datetime.now().isoformat()
                })
            
            return result
    
    async def test_all_integrations(self) -> Dict[str, bool]:
        """Test all configured integrations"""
        results = {}
        
        for name, integration in self.crm_integrations.items():
            async with integration:
                results[name] = await integration.test_connection()
        
        return results
    
    def get_integration_status(self) -> Dict[str, Any]:
        """Get status of all integrations"""
        return {
            "crm_integrations": list(self.crm_integrations.keys()),
            "active_webhooks": len([w for w in self.webhook_manager.webhooks.values() if w["active"]]),
            "webhook_events": list(self.webhook_manager.event_handlers.keys())
        }