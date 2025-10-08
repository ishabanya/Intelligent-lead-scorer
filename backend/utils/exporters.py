import csv
import json
import io
from typing import List, Dict, Any, Optional
from datetime import datetime
import xlsxwriter
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.lead import Lead
from models.scoring import LeadScore

class CSVExporter:
    """Export leads to CSV format"""
    
    @staticmethod
    def export_leads_basic(leads: List[Lead]) -> str:
        """Export basic lead information to CSV"""
        output = io.StringIO()
        
        fieldnames = [
            'company_name',
            'domain', 
            'industry',
            'lead_score',
            'qualification_status',
            'employee_count',
            'headquarters',
            'last_enriched'
        ]
        
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for lead in leads:
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
        
        return output.getvalue()
    
    @staticmethod
    def export_leads_detailed(leads: List[Lead]) -> str:
        """Export detailed lead information to CSV"""
        output = io.StringIO()
        
        fieldnames = [
            'id',
            'company_name',
            'domain',
            'industry',
            'lead_score',
            'qualification_status',
            'employee_count',
            'revenue_range',
            'funding_amount',
            'headquarters',
            'technologies',
            'marketing_tools',
            'sales_tools',
            'contact_count',
            'primary_email',
            'social_media_count',
            'data_quality_score',
            'completeness_percentage',
            'last_enriched',
            'created_at'
        ]
        
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for lead in leads:
            # Get primary contact email
            primary_email = ''
            if lead.contacts:
                for contact in lead.contacts:
                    if contact.email:
                        primary_email = contact.email
                        break
            
            writer.writerow({
                'id': lead.id or '',
                'company_name': lead.company_name,
                'domain': lead.domain,
                'industry': lead.industry or '',
                'lead_score': lead.lead_score or 0,
                'qualification_status': lead.qualification_status.value if lead.qualification_status else '',
                'employee_count': lead.metrics.employee_count or '',
                'revenue_range': lead.metrics.revenue_range.value if lead.metrics.revenue_range else '',
                'funding_amount': lead.metrics.funding_amount or '',
                'headquarters': lead.headquarters or '',
                'technologies': '; '.join(lead.tech_stack.technologies) if lead.tech_stack.technologies else '',
                'marketing_tools': '; '.join(lead.tech_stack.marketing_tools) if lead.tech_stack.marketing_tools else '',
                'sales_tools': '; '.join(lead.tech_stack.sales_tools) if lead.tech_stack.sales_tools else '',
                'contact_count': len(lead.contacts),
                'primary_email': primary_email,
                'social_media_count': len(lead.social_media_presence),
                'data_quality_score': lead.data_quality_score or 0,
                'completeness_percentage': lead.completeness_percentage or 0,
                'last_enriched': lead.last_enriched.isoformat() if lead.last_enriched else '',
                'created_at': lead.created_at.isoformat()
            })
        
        return output.getvalue()
    
    @staticmethod
    def export_leads_with_scores(leads_with_scores: List[tuple]) -> str:
        """Export leads with their scoring breakdowns"""
        output = io.StringIO()
        
        fieldnames = [
            'company_name',
            'domain',
            'total_score',
            'qualification_status',
            'company_fit_score',
            'growth_indicators_score', 
            'technology_fit_score',
            'engagement_signals_score',
            'timing_signals_score',
            'buying_signals_score',
            'confidence',
            'applied_rules',
            'improvement_suggestions'
        ]
        
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for lead, lead_score in leads_with_scores:
            writer.writerow({
                'company_name': lead.company_name,
                'domain': lead.domain,
                'total_score': lead_score.total_score,
                'qualification_status': lead_score.qualification_status,
                'company_fit_score': lead_score.category_scores.get('company_fit', 0),
                'growth_indicators_score': lead_score.category_scores.get('growth_indicators', 0),
                'technology_fit_score': lead_score.category_scores.get('technology_fit', 0),
                'engagement_signals_score': lead_score.category_scores.get('engagement_signals', 0),
                'timing_signals_score': lead_score.category_scores.get('timing_signals', 0),
                'buying_signals_score': lead_score.category_scores.get('buying_signals', 0),
                'confidence': lead_score.confidence,
                'applied_rules': '; '.join(lead_score.applied_rules),
                'improvement_suggestions': '; '.join(lead_score.improvement_suggestions)
            })
        
        return output.getvalue()

class JSONExporter:
    """Export leads to JSON format"""
    
    @staticmethod
    def export_leads_basic(leads: List[Lead]) -> str:
        """Export basic lead information to JSON"""
        export_data = []
        
        for lead in leads:
            export_data.append({
                'company_name': lead.company_name,
                'domain': lead.domain,
                'industry': lead.industry,
                'lead_score': lead.lead_score,
                'qualification_status': lead.qualification_status.value if lead.qualification_status else None,
                'employee_count': lead.metrics.employee_count,
                'headquarters': lead.headquarters,
                'last_enriched': lead.last_enriched.isoformat() if lead.last_enriched else None
            })
        
        return json.dumps(export_data, indent=2, default=str)
    
    @staticmethod
    def export_leads_detailed(leads: List[Lead]) -> str:
        """Export detailed lead information to JSON"""
        export_data = []
        
        for lead in leads:
            lead_dict = lead.dict()
            # Convert datetime objects to ISO strings
            if lead_dict.get('last_enriched'):
                lead_dict['last_enriched'] = lead.last_enriched.isoformat()
            if lead_dict.get('created_at'):
                lead_dict['created_at'] = lead.created_at.isoformat()
            if lead_dict.get('updated_at'):
                lead_dict['updated_at'] = lead.updated_at.isoformat()
            
            export_data.append(lead_dict)
        
        return json.dumps(export_data, indent=2, default=str)
    
    @staticmethod
    def export_leads_with_analysis(leads_with_analysis: List[tuple]) -> str:
        """Export leads with complete analysis"""
        export_data = []
        
        for lead, analysis in leads_with_analysis:
            lead_dict = lead.dict()
            
            # Convert datetime objects
            if lead_dict.get('last_enriched'):
                lead_dict['last_enriched'] = lead.last_enriched.isoformat()
            if lead_dict.get('created_at'):
                lead_dict['created_at'] = lead.created_at.isoformat()
            if lead_dict.get('updated_at'):
                lead_dict['updated_at'] = lead.updated_at.isoformat()
            
            # Add analysis data
            lead_dict['analysis'] = analysis
            
            export_data.append(lead_dict)
        
        return json.dumps(export_data, indent=2, default=str)

class ExcelExporter:
    """Export leads to Excel format"""
    
    @staticmethod
    def export_leads_to_excel(leads: List[Lead], filename: str = None) -> bytes:
        """Export leads to Excel with multiple sheets"""
        if filename is None:
            filename = f"leads_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        # Create Excel file in memory
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        
        # Create formats
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4F81BD',
            'font_color': 'white',
            'border': 1
        })
        
        hot_format = workbook.add_format({'bg_color': '#FF6B6B'})
        warm_format = workbook.add_format({'bg_color': '#FFD93D'})
        cold_format = workbook.add_format({'bg_color': '#74C0FC'})
        
        # Summary sheet
        summary_sheet = workbook.add_worksheet('Summary')
        ExcelExporter._create_summary_sheet(summary_sheet, leads, header_format)
        
        # Detailed leads sheet
        leads_sheet = workbook.add_worksheet('Leads')
        ExcelExporter._create_leads_sheet(leads_sheet, leads, header_format, hot_format, warm_format, cold_format)
        
        # Technology analysis sheet
        tech_sheet = workbook.add_worksheet('Technology Analysis')
        ExcelExporter._create_technology_sheet(tech_sheet, leads, header_format)
        
        workbook.close()
        output.seek(0)
        
        return output.getvalue()
    
    @staticmethod
    def _create_summary_sheet(worksheet, leads: List[Lead], header_format):
        """Create summary statistics sheet"""
        worksheet.write('A1', 'Lead Generation Summary', header_format)
        
        # Basic statistics
        total_leads = len(leads)
        qualified_leads = len([l for l in leads if l.qualification_status and l.qualification_status.value != 'Unqualified'])
        avg_score = sum([l.lead_score for l in leads if l.lead_score]) / len([l for l in leads if l.lead_score]) if leads else 0
        
        stats = [
            ['Metric', 'Value'],
            ['Total Leads', total_leads],
            ['Qualified Leads', qualified_leads],
            ['Qualification Rate', f"{(qualified_leads/total_leads*100):.1f}%" if total_leads > 0 else "0%"],
            ['Average Score', f"{avg_score:.1f}"],
        ]
        
        for row, (metric, value) in enumerate(stats):
            if row == 0:
                worksheet.write(row + 2, 0, metric, header_format)
                worksheet.write(row + 2, 1, value, header_format)
            else:
                worksheet.write(row + 2, 0, metric)
                worksheet.write(row + 2, 1, value)
        
        # Qualification breakdown
        worksheet.write('A8', 'Qualification Breakdown', header_format)
        qualification_counts = {}
        for lead in leads:
            if lead.qualification_status:
                status = lead.qualification_status.value
                qualification_counts[status] = qualification_counts.get(status, 0) + 1
        
        row = 9
        for status, count in qualification_counts.items():
            worksheet.write(row, 0, status)
            worksheet.write(row, 1, count)
            row += 1
    
    @staticmethod
    def _create_leads_sheet(worksheet, leads: List[Lead], header_format, hot_format, warm_format, cold_format):
        """Create detailed leads sheet"""
        headers = [
            'Company Name', 'Domain', 'Industry', 'Score', 'Qualification',
            'Employee Count', 'Headquarters', 'Technologies', 'Contacts',
            'Data Quality', 'Last Enriched'
        ]
        
        # Write headers
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)
        
        # Write lead data
        for row, lead in enumerate(leads, 1):
            # Determine row format based on qualification
            row_format = None
            if lead.qualification_status:
                if lead.qualification_status.value == 'Hot':
                    row_format = hot_format
                elif lead.qualification_status.value == 'Warm':
                    row_format = warm_format
                elif lead.qualification_status.value == 'Cold':
                    row_format = cold_format
            
            data = [
                lead.company_name,
                lead.domain,
                lead.industry or '',
                lead.lead_score or 0,
                lead.qualification_status.value if lead.qualification_status else '',
                lead.metrics.employee_count or '',
                lead.headquarters or '',
                '; '.join(lead.tech_stack.technologies) if lead.tech_stack.technologies else '',
                len(lead.contacts),
                lead.data_quality_score or 0,
                lead.last_enriched.strftime('%Y-%m-%d') if lead.last_enriched else ''
            ]
            
            for col, value in enumerate(data):
                if row_format:
                    worksheet.write(row, col, value, row_format)
                else:
                    worksheet.write(row, col, value)
        
        # Auto-adjust column widths
        worksheet.autofit()
    
    @staticmethod
    def _create_technology_sheet(worksheet, leads: List[Lead], header_format):
        """Create technology analysis sheet"""
        worksheet.write('A1', 'Technology Stack Analysis', header_format)
        
        # Collect all technologies
        tech_counts = {}
        for lead in leads:
            all_tech = (
                lead.tech_stack.technologies +
                lead.tech_stack.marketing_tools +
                lead.tech_stack.sales_tools +
                lead.tech_stack.analytics_tools
            )
            for tech in all_tech:
                tech_counts[tech] = tech_counts.get(tech, 0) + 1
        
        # Sort by count
        sorted_tech = sorted(tech_counts.items(), key=lambda x: x[1], reverse=True)
        
        # Write headers
        worksheet.write(2, 0, 'Technology', header_format)
        worksheet.write(2, 1, 'Count', header_format)
        worksheet.write(2, 2, 'Percentage', header_format)
        
        total_leads = len(leads)
        for row, (tech, count) in enumerate(sorted_tech[:50], 3):  # Top 50 technologies
            percentage = (count / total_leads) * 100 if total_leads > 0 else 0
            worksheet.write(row, 0, tech)
            worksheet.write(row, 1, count)
            worksheet.write(row, 2, f"{percentage:.1f}%")

class CRMExporter:
    """Export leads for CRM systems"""
    
    @staticmethod
    def export_for_hubspot(leads: List[Lead]) -> str:
        """Export leads in HubSpot CSV format"""
        output = io.StringIO()
        
        # HubSpot standard fields
        fieldnames = [
            'Company name',
            'Company domain name',
            'Industry',
            'Number of employees',
            'City',
            'State/Region',
            'Country',
            'Website URL',
            'Lead Status',
            'Lead Score',
            'Description'
        ]
        
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for lead in leads:
            # Parse headquarters for location info
            city, state, country = '', '', ''
            if lead.headquarters:
                parts = lead.headquarters.split(', ')
                if len(parts) >= 1:
                    city = parts[0]
                if len(parts) >= 2:
                    state = parts[1]
                if len(parts) >= 3:
                    country = parts[2]
            
            # Create description from available data
            description_parts = []
            if lead.tech_stack.technologies:
                description_parts.append(f"Technologies: {', '.join(lead.tech_stack.technologies[:5])}")
            if lead.buying_signals.job_postings:
                description_parts.append(f"Active hiring: {len(lead.buying_signals.job_postings)} positions")
            
            writer.writerow({
                'Company name': lead.company_name,
                'Company domain name': lead.domain,
                'Industry': lead.industry or '',
                'Number of employees': lead.metrics.employee_count or '',
                'City': city,
                'State/Region': state,
                'Country': country,
                'Website URL': f"https://{lead.domain}",
                'Lead Status': lead.qualification_status.value if lead.qualification_status else 'New',
                'Lead Score': lead.lead_score or 0,
                'Description': '; '.join(description_parts)
            })
        
        return output.getvalue()
    
    @staticmethod
    def export_for_salesforce(leads: List[Lead]) -> str:
        """Export leads in Salesforce CSV format"""
        output = io.StringIO()
        
        # Salesforce standard fields
        fieldnames = [
            'Company',
            'Website',
            'Industry',
            'NumberOfEmployees',
            'City',
            'State',
            'Country',
            'LeadSource',
            'Rating',
            'Description'
        ]
        
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for lead in leads:
            # Convert qualification to Salesforce rating
            rating_map = {
                'Hot': 'Hot',
                'Warm': 'Warm',
                'Cold': 'Cold',
                'Unqualified': 'Unqualified'
            }
            
            rating = 'Unqualified'
            if lead.qualification_status:
                rating = rating_map.get(lead.qualification_status.value, 'Unqualified')
            
            # Parse location
            city, state, country = '', '', ''
            if lead.headquarters:
                parts = lead.headquarters.split(', ')
                if len(parts) >= 1:
                    city = parts[0]
                if len(parts) >= 2:
                    state = parts[1]
                if len(parts) >= 3:
                    country = parts[2]
            
            writer.writerow({
                'Company': lead.company_name,
                'Website': f"https://{lead.domain}",
                'Industry': lead.industry or '',
                'NumberOfEmployees': lead.metrics.employee_count or '',
                'City': city,
                'State': state,
                'Country': country,
                'LeadSource': 'Lead Scorer Tool',
                'Rating': rating,
                'Description': f"Lead Score: {lead.lead_score or 0}/100"
            })
        
        return output.getvalue()

class ExportManager:
    """Main export manager for coordinating different export formats"""
    
    def __init__(self):
        self.csv_exporter = CSVExporter()
        self.json_exporter = JSONExporter()
        self.excel_exporter = ExcelExporter()
        self.crm_exporter = CRMExporter()
    
    def export_leads(self, leads: List[Lead], format: str, detail_level: str = 'basic', target_system: str = None) -> tuple:
        """
        Export leads in specified format
        
        Args:
            leads: List of Lead objects
            format: 'csv', 'json', 'excel'
            detail_level: 'basic', 'detailed', 'analysis'
            target_system: 'hubspot', 'salesforce' (for CRM-specific formats)
        
        Returns:
            tuple: (data, filename, content_type)
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if format == 'csv':
            if target_system == 'hubspot':
                data = self.crm_exporter.export_for_hubspot(leads)
                filename = f"leads_hubspot_{timestamp}.csv"
            elif target_system == 'salesforce':
                data = self.crm_exporter.export_for_salesforce(leads)
                filename = f"leads_salesforce_{timestamp}.csv"
            elif detail_level == 'detailed':
                data = self.csv_exporter.export_leads_detailed(leads)
                filename = f"leads_detailed_{timestamp}.csv"
            else:
                data = self.csv_exporter.export_leads_basic(leads)
                filename = f"leads_basic_{timestamp}.csv"
            
            return data, filename, 'text/csv'
        
        elif format == 'json':
            if detail_level == 'detailed':
                data = self.json_exporter.export_leads_detailed(leads)
            else:
                data = self.json_exporter.export_leads_basic(leads)
            
            filename = f"leads_{detail_level}_{timestamp}.json"
            return data, filename, 'application/json'
        
        elif format == 'excel':
            data = self.excel_exporter.export_leads_to_excel(leads)
            filename = f"leads_export_{timestamp}.xlsx"
            return data, filename, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        
        else:
            raise ValueError(f"Unsupported export format: {format}")