class LeadScorerApp {
    constructor() {
        this.leads = [];
        this.currentPage = 1;
        this.pageSize = 20;
        this.selectedLeads = new Set();
        this.filters = {
            search: '',
            qualification: '',
            sortBy: 'score',
            sortOrder: 'desc'
        };
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.loadDashboardData();
        this.initChart();
    }
    
    setupEventListeners() {
        // Tab switching
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', () => this.switchTab(btn.dataset.tab));
        });
        
        // Single lead analysis
        document.getElementById('analyzeBtn').addEventListener('click', () => this.analyzeSingleLead());
        
        // Bulk upload
        document.getElementById('uploadBtn').addEventListener('click', () => {
            document.getElementById('csvFile').click();
        });
        
        document.getElementById('csvFile').addEventListener('change', (e) => this.handleFileUpload(e));
        
        // Drag and drop
        const uploadArea = document.getElementById('uploadArea');
        uploadArea.addEventListener('dragover', (e) => this.handleDragOver(e));
        uploadArea.addEventListener('dragleave', (e) => this.handleDragLeave(e));
        uploadArea.addEventListener('drop', (e) => this.handleDrop(e));
        uploadArea.addEventListener('click', () => document.getElementById('csvFile').click());
        
        // Search and filters
        document.getElementById('searchInput').addEventListener('input', (e) => {
            this.filters.search = e.target.value;
            this.filterAndDisplayLeads();
        });
        
        document.getElementById('qualificationFilter').addEventListener('change', (e) => {
            this.filters.qualification = e.target.value;
            this.filterAndDisplayLeads();
        });
        
        document.getElementById('sortBy').addEventListener('change', (e) => {
            this.filters.sortBy = e.target.value;
            this.filterAndDisplayLeads();
        });
        
        // Select all checkbox
        document.getElementById('selectAll').addEventListener('change', (e) => {
            this.toggleSelectAll(e.target.checked);
        });
        
        // Pagination
        document.getElementById('prevPage').addEventListener('click', () => this.previousPage());
        document.getElementById('nextPage').addEventListener('click', () => this.nextPage());
        
        // Theme toggle
        document.getElementById('themeToggle').addEventListener('click', () => this.toggleTheme());
        
        // Export
        document.getElementById('exportBtn').addEventListener('click', () => this.showExportModal());
        
        // Modal controls
        document.getElementById('closeModal').addEventListener('click', () => this.hideModal('leadModal'));
        document.getElementById('modalClose').addEventListener('click', () => this.hideModal('leadModal'));
        document.getElementById('closeExportModal').addEventListener('click', () => this.hideModal('exportModal'));
        document.getElementById('cancelExport').addEventListener('click', () => this.hideModal('exportModal'));
        document.getElementById('confirmExport').addEventListener('click', () => this.exportLeads());
        
        // Close modals on backdrop click
        document.querySelectorAll('.modal').forEach(modal => {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.hideModal(modal.id);
                }
            });
        });
        
        // Enter key for single lead input
        document.getElementById('companyDomain').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.analyzeSingleLead();
            }
        });
    }
    
    switchTab(tabName) {
        // Update tab buttons
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tabName);
        });
        
        // Update tab content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.toggle('active', content.id === `${tabName}Tab`);
        });
    }
    
    async analyzeSingleLead() {
        const domain = document.getElementById('companyDomain').value.trim();
        const linkedinUrl = document.getElementById('linkedinUrl').value.trim();
        
        if (!domain) {
            this.showToast('Please enter a company domain', 'error');
            return;
        }
        
        this.showLoading('Analyzing lead...');
        
        try {
            // First scrape the company data
            const scrapeResponse = await fetch('/api/leads/scrape', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    domain: domain,
                    linkedin_url: linkedinUrl || null
                })
            });
            
            if (!scrapeResponse.ok) {
                throw new Error('Failed to scrape company data');
            }
            
            const scrapeData = await scrapeResponse.json();
            
            // Then enrich and score the lead
            const enrichResponse = await fetch('/api/leads/enrich', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    domain: domain,
                    company_name: scrapeData.lead?.company_name || domain.split('.')[0]
                })
            });
            
            if (!enrichResponse.ok) {
                throw new Error('Failed to enrich lead data');
            }
            
            const enrichData = await enrichResponse.json();
            
            // Add to leads array
            this.leads.unshift(enrichData.lead);
            
            // Update display
            this.updateDashboardStats();
            this.filterAndDisplayLeads();
            this.showResultsSection();
            
            // Clear inputs
            document.getElementById('companyDomain').value = '';
            document.getElementById('linkedinUrl').value = '';
            
            this.showToast(`Successfully analyzed ${enrichData.lead.company_name}`, 'success');
            
        } catch (error) {
            console.error('Error analyzing lead:', error);
            this.showToast('Failed to analyze lead. Please try again.', 'error');
        } finally {
            this.hideLoading();
        }
    }
    
    handleDragOver(e) {
        e.preventDefault();
        document.getElementById('uploadArea').classList.add('dragover');
    }
    
    handleDragLeave(e) {
        e.preventDefault();
        document.getElementById('uploadArea').classList.remove('dragover');
    }
    
    handleDrop(e) {
        e.preventDefault();
        document.getElementById('uploadArea').classList.remove('dragover');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            this.processCSVFile(files[0]);
        }
    }
    
    handleFileUpload(e) {
        const file = e.target.files[0];
        if (file) {
            this.processCSVFile(file);
        }
    }
    
    async processCSVFile(file) {
        if (!file.name.endsWith('.csv')) {
            this.showToast('Please upload a CSV file', 'error');
            return;
        }
        
        this.showProcessingStatus(true);
        
        try {
            const formData = new FormData();
            formData.append('file', file);
            
            const response = await fetch('/api/leads/bulk-process', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                throw new Error('Failed to process CSV file');
            }
            
            const data = await response.json();
            
            // Add successful leads to the array
            const successfulLeads = data.results.filter(r => r.processing_status === 'success');
            successfulLeads.forEach(result => {
                // Find the full lead data from the results
                const leadData = data.results.find(r => r.lead_id === result.lead_id);
                if (leadData && leadData.lead) {
                    this.leads.unshift(leadData.lead);
                }
            });
            
            // Update display
            this.updateDashboardStats();
            this.filterAndDisplayLeads();
            this.showResultsSection();
            
            // Show summary
            const message = `Processed ${data.processed_count} of ${data.total_uploaded} leads successfully`;
            this.showToast(message, 'success');
            
            if (data.failed_count > 0) {
                this.showToast(`${data.failed_count} leads failed to process`, 'warning');
            }
            
        } catch (error) {
            console.error('Error processing CSV:', error);
            this.showToast('Failed to process CSV file. Please try again.', 'error');
        } finally {
            this.showProcessingStatus(false);
        }
    }
    
    showProcessingStatus(show) {
        const statusElement = document.getElementById('processingStatus');
        if (show) {
            statusElement.style.display = 'block';
            // Simulate progress
            let progress = 0;
            const interval = setInterval(() => {
                progress += Math.random() * 20;
                if (progress >= 100) {
                    progress = 100;
                    clearInterval(interval);
                }
                document.getElementById('progressFill').style.width = `${progress}%`;
            }, 200);
        } else {
            statusElement.style.display = 'none';
            document.getElementById('progressFill').style.width = '0%';
        }
    }
    
    filterAndDisplayLeads() {
        let filteredLeads = [...this.leads];
        
        // Apply search filter
        if (this.filters.search) {
            const search = this.filters.search.toLowerCase();
            filteredLeads = filteredLeads.filter(lead => 
                lead.company_name.toLowerCase().includes(search) ||
                lead.domain.toLowerCase().includes(search) ||
                (lead.industry && lead.industry.toLowerCase().includes(search))
            );
        }
        
        // Apply qualification filter
        if (this.filters.qualification) {
            filteredLeads = filteredLeads.filter(lead => 
                lead.qualification_status === this.filters.qualification
            );
        }
        
        // Apply sorting
        filteredLeads.sort((a, b) => {
            let aVal, bVal;
            
            switch (this.filters.sortBy) {
                case 'score':
                    aVal = a.lead_score || 0;
                    bVal = b.lead_score || 0;
                    break;
                case 'name':
                    aVal = a.company_name.toLowerCase();
                    bVal = b.company_name.toLowerCase();
                    break;
                case 'date':
                    aVal = new Date(a.created_at);
                    bVal = new Date(b.created_at);
                    break;
                default:
                    aVal = a.lead_score || 0;
                    bVal = b.lead_score || 0;
            }
            
            if (this.filters.sortOrder === 'desc') {
                return bVal > aVal ? 1 : -1;
            } else {
                return aVal > bVal ? 1 : -1;
            }
        });
        
        this.displayLeads(filteredLeads);
        this.updatePagination(filteredLeads.length);
    }
    
    displayLeads(leads) {
        const tbody = document.getElementById('resultsBody');
        tbody.innerHTML = '';
        
        const startIndex = (this.currentPage - 1) * this.pageSize;
        const endIndex = startIndex + this.pageSize;
        const pageLeads = leads.slice(startIndex, endIndex);
        
        pageLeads.forEach(lead => {
            const row = this.createLeadRow(lead);
            tbody.appendChild(row);
        });
        
        // Update select all checkbox state
        const selectAllCheckbox = document.getElementById('selectAll');
        const visibleLeadIds = pageLeads.map(lead => lead.id);
        const allVisible = visibleLeadIds.every(id => this.selectedLeads.has(id));
        const someVisible = visibleLeadIds.some(id => this.selectedLeads.has(id));
        
        selectAllCheckbox.checked = allVisible && visibleLeadIds.length > 0;
        selectAllCheckbox.indeterminate = someVisible && !allVisible;
        
        this.updateSelectedCount();
    }
    
    createLeadRow(lead) {
        const row = document.createElement('tr');
        
        // Qualification badge
        const qualificationClass = lead.qualification_status ? 
            `qualification-${lead.qualification_status.toLowerCase()}` : 'qualification-unqualified';
        
        // Score badge
        const score = lead.lead_score || 0;
        let scoreClass = 'score-low';
        if (score >= 70) scoreClass = 'score-high';
        else if (score >= 40) scoreClass = 'score-medium';
        
        row.innerHTML = `
            <td>
                <input type="checkbox" ${this.selectedLeads.has(lead.id) ? 'checked' : ''} 
                       onchange="app.toggleLeadSelection('${lead.id}', this.checked)">
            </td>
            <td>
                <div class="company-info">
                    <strong>${lead.company_name}</strong>
                    ${lead.industry ? `<br><small>${lead.industry}</small>` : ''}
                </div>
            </td>
            <td>${lead.domain}</td>
            <td>${lead.industry || '-'}</td>
            <td>
                <span class="score-badge ${scoreClass}">${score}</span>
            </td>
            <td>
                <span class="qualification-badge ${qualificationClass}">
                    ${lead.qualification_status || 'Unqualified'}
                </span>
            </td>
            <td>${lead.metrics?.employee_count || '-'}</td>
            <td>${lead.headquarters || '-'}</td>
            <td>
                <div class="action-buttons">
                    <button class="action-btn" onclick="app.viewLeadDetails('${lead.id}')">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button class="action-btn primary" onclick="app.generateOutreach('${lead.id}')">
                        <i class="fas fa-envelope"></i>
                    </button>
                </div>
            </td>
        `;
        
        return row;
    }
    
    toggleLeadSelection(leadId, selected) {
        if (selected) {
            this.selectedLeads.add(leadId);
        } else {
            this.selectedLeads.delete(leadId);
        }
        this.updateSelectedCount();
    }
    
    toggleSelectAll(selectAll) {
        const currentPageLeads = this.getCurrentPageLeadIds();
        
        if (selectAll) {
            currentPageLeads.forEach(id => this.selectedLeads.add(id));
        } else {
            currentPageLeads.forEach(id => this.selectedLeads.delete(id));
        }
        
        // Update checkboxes
        document.querySelectorAll('#resultsBody input[type="checkbox"]').forEach(checkbox => {
            checkbox.checked = selectAll;
        });
        
        this.updateSelectedCount();
    }
    
    getCurrentPageLeadIds() {
        const rows = document.querySelectorAll('#resultsBody tr');
        return Array.from(rows).map(row => {
            const checkbox = row.querySelector('input[type="checkbox"]');
            return checkbox.onchange.toString().match(/'([^']+)'/)[1];
        });
    }
    
    updateSelectedCount() {
        const count = this.selectedLeads.size;
        document.getElementById('selectedCount').textContent = count;
    }
    
    updatePagination(totalLeads) {
        const totalPages = Math.ceil(totalLeads / this.pageSize);
        
        document.getElementById('prevPage').disabled = this.currentPage <= 1;
        document.getElementById('nextPage').disabled = this.currentPage >= totalPages;
        document.getElementById('pageInfo').textContent = `Page ${this.currentPage} of ${totalPages}`;
    }
    
    previousPage() {
        if (this.currentPage > 1) {
            this.currentPage--;
            this.filterAndDisplayLeads();
        }
    }
    
    nextPage() {
        this.currentPage++;
        this.filterAndDisplayLeads();
    }
    
    async viewLeadDetails(leadId) {
        const lead = this.leads.find(l => l.id === leadId);
        if (!lead) return;
        
        this.showLoading('Loading lead details...');
        
        try {
            const response = await fetch(`/api/leads/${leadId}`);
            if (!response.ok) throw new Error('Failed to load lead details');
            
            const data = await response.json();
            this.showLeadDetailsModal(data.lead, data.qualification_analysis);
            
        } catch (error) {
            console.error('Error loading lead details:', error);
            this.showToast('Failed to load lead details', 'error');
        } finally {
            this.hideLoading();
        }
    }
    
    showLeadDetailsModal(lead, analysis) {
        const modal = document.getElementById('leadModal');
        const title = document.getElementById('modalTitle');
        const body = document.getElementById('modalBody');
        
        title.textContent = lead.company_name;
        
        body.innerHTML = `
            <div class="lead-details">
                <div class="detail-section">
                    <h3>Company Information</h3>
                    <div class="detail-grid">
                        <div class="detail-item">
                            <label>Domain:</label>
                            <span>${lead.domain}</span>
                        </div>
                        <div class="detail-item">
                            <label>Industry:</label>
                            <span>${lead.industry || 'Unknown'}</span>
                        </div>
                        <div class="detail-item">
                            <label>Employees:</label>
                            <span>${lead.metrics?.employee_count || 'Unknown'}</span>
                        </div>
                        <div class="detail-item">
                            <label>Location:</label>
                            <span>${lead.headquarters || 'Unknown'}</span>
                        </div>
                    </div>
                </div>
                
                <div class="detail-section">
                    <h3>Lead Score Breakdown</h3>
                    <div class="score-breakdown">
                        <div class="total-score">
                            <span class="score-value">${lead.lead_score || 0}</span>
                            <span class="score-label">Total Score</span>
                        </div>
                        <div class="category-scores">
                            ${Object.entries(lead.score_breakdown || {}).map(([category, score]) => `
                                <div class="category-score">
                                    <span class="category-name">${category.replace('_', ' ')}</span>
                                    <span class="category-value">${score}</span>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                </div>
                
                <div class="detail-section">
                    <h3>Technologies</h3>
                    <div class="tech-tags">
                        ${lead.tech_stack?.technologies?.map(tech => `
                            <span class="tech-tag">${tech}</span>
                        `).join('') || '<span>No technologies identified</span>'}
                    </div>
                </div>
                
                <div class="detail-section">
                    <h3>Contacts</h3>
                    <div class="contacts-list">
                        ${lead.contacts?.map(contact => `
                            <div class="contact-item">
                                <strong>${contact.name || 'Unknown'}</strong>
                                <span>${contact.title || ''}</span>
                                <span>${contact.email || ''}</span>
                            </div>
                        `).join('') || '<span>No contacts found</span>'}
                    </div>
                </div>
                
                ${analysis?.action_plan ? `
                    <div class="detail-section">
                        <h3>Recommended Actions</h3>
                        <ul class="action-list">
                            ${analysis.action_plan.immediate_actions?.map(action => `
                                <li>${action}</li>
                            `).join('') || ''}
                        </ul>
                    </div>
                ` : ''}
            </div>
        `;
        
        this.showModal('leadModal');
    }
    
    async generateOutreach(leadId) {
        this.showLoading('Generating outreach recommendations...');
        
        try {
            const response = await fetch(`/api/leads/${leadId}/recommendations`);
            if (!response.ok) throw new Error('Failed to generate recommendations');
            
            const recommendations = await response.json();
            this.showOutreachModal(leadId, recommendations);
            
        } catch (error) {
            console.error('Error generating outreach:', error);
            this.showToast('Failed to generate outreach recommendations', 'error');
        } finally {
            this.hideLoading();
        }
    }
    
    showOutreachModal(leadId, recommendations) {
        const lead = this.leads.find(l => l.id === leadId);
        const modal = document.getElementById('leadModal');
        const title = document.getElementById('modalTitle');
        const body = document.getElementById('modalBody');
        
        title.textContent = `Outreach Strategy - ${lead.company_name}`;
        
        body.innerHTML = `
            <div class="outreach-recommendations">
                ${recommendations.email_templates?.map((template, index) => `
                    <div class="recommendation-section">
                        <h3>Email Template ${index + 1} - ${template.type}</h3>
                        <div class="email-template">
                            <div class="email-field">
                                <label>Subject:</label>
                                <input type="text" value="${template.subject}" readonly>
                            </div>
                            <div class="email-field">
                                <label>Body:</label>
                                <textarea rows="8" readonly>${template.body}</textarea>
                            </div>
                        </div>
                    </div>
                `).join('') || '<p>No email templates available</p>'}
                
                <div class="recommendation-section">
                    <h3>Action Plan</h3>
                    <div class="action-timeline">
                        <strong>Priority:</strong> ${recommendations.action_plan?.priority || 'Medium'}<br>
                        <strong>Timeline:</strong> ${recommendations.action_plan?.timeline || 'This week'}<br>
                        <strong>Assigned to:</strong> ${recommendations.action_plan?.assigned_rep_type || 'Sales team'}
                    </div>
                </div>
                
                <div class="recommendation-section">
                    <h3>Optimal Timing</h3>
                    <p><strong>Best time to reach out:</strong> ${recommendations.optimal_timing?.recommendation || 'Business hours'}</p>
                </div>
            </div>
        `;
        
        this.showModal('leadModal');
    }
    
    showExportModal() {
        if (this.selectedLeads.size === 0) {
            this.showToast('Please select leads to export', 'warning');
            return;
        }
        
        this.showModal('exportModal');
    }
    
    async exportLeads() {
        const selectedFormat = document.querySelector('input[name="format"]:checked').value;
        const selectedDetail = document.querySelector('input[name="detail"]:checked').value;
        const selectedCRM = document.querySelector('input[name="crm"]:checked').value;
        
        if (this.selectedLeads.size === 0) {
            this.showToast('No leads selected for export', 'warning');
            return;
        }
        
        this.showLoading('Exporting leads...');
        
        try {
            const exportData = {
                lead_ids: Array.from(this.selectedLeads),
                format: selectedFormat,
                include_details: selectedDetail === 'detailed'
            };
            
            if (selectedCRM) {
                exportData.target_system = selectedCRM;
            }
            
            const response = await fetch('/api/leads/export', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(exportData)
            });
            
            if (!response.ok) throw new Error('Export failed');
            
            const result = await response.json();
            
            // Create download
            if (selectedFormat === 'csv') {
                this.downloadFile(result.data, result.filename, 'text/csv');
            } else if (selectedFormat === 'json') {
                const jsonString = JSON.stringify(result.data, null, 2);
                this.downloadFile(jsonString, result.filename, 'application/json');
            }
            
            this.hideModal('exportModal');
            this.showToast(`Successfully exported ${this.selectedLeads.size} leads`, 'success');
            
        } catch (error) {
            console.error('Export error:', error);
            this.showToast('Failed to export leads', 'error');
        } finally {
            this.hideLoading();
        }
    }
    
    downloadFile(content, filename, mimeType) {
        const blob = new Blob([content], { type: mimeType });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }
    
    showModal(modalId) {
        document.getElementById(modalId).classList.add('active');
        document.body.style.overflow = 'hidden';
    }
    
    hideModal(modalId) {
        document.getElementById(modalId).classList.remove('active');
        document.body.style.overflow = '';
    }
    
    showLoading(text = 'Loading...') {
        document.getElementById('loadingText').textContent = text;
        document.getElementById('loadingOverlay').classList.add('active');
    }
    
    hideLoading() {
        document.getElementById('loadingOverlay').classList.remove('active');
    }
    
    showToast(message, type = 'info') {
        const toast = document.getElementById('toast');
        const icon = toast.querySelector('.toast-icon');
        const messageEl = toast.querySelector('.toast-message');
        
        // Set icon based on type
        const icons = {
            success: 'fas fa-check-circle',
            error: 'fas fa-exclamation-circle',
            warning: 'fas fa-exclamation-triangle',
            info: 'fas fa-info-circle'
        };
        
        icon.className = `toast-icon ${icons[type] || icons.info}`;
        messageEl.textContent = message;
        
        toast.className = `toast ${type}`;
        toast.classList.add('active');
        
        setTimeout(() => {
            toast.classList.remove('active');
        }, 5000);
    }
    
    toggleTheme() {
        const currentTheme = document.body.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        
        document.body.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        
        const icon = document.querySelector('#themeToggle i');
        icon.className = newTheme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
    }
    
    async loadDashboardData() {
        try {
            const response = await fetch('/api/analytics/dashboard');
            if (response.ok) {
                const data = await response.json();
                this.updateDashboardFromAPI(data);
            }
        } catch (error) {
            console.error('Error loading dashboard data:', error);
        }
    }
    
    updateDashboardFromAPI(data) {
        const stats = data.summary_stats;
        
        document.getElementById('totalLeads').textContent = stats.total_leads;
        document.getElementById('averageScore').textContent = Math.round(stats.average_score);
        document.getElementById('hotLeads').textContent = stats.qualification_breakdown.Hot || 0;
        document.getElementById('warmLeads').textContent = stats.qualification_breakdown.Warm || 0;
        
        // Update chart if data available
        if (data.score_distribution) {
            this.updateChart(data.score_distribution);
        }
    }
    
    updateDashboardStats() {
        const totalLeads = this.leads.length;
        const scores = this.leads.filter(l => l.lead_score).map(l => l.lead_score);
        const avgScore = scores.length ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length) : 0;
        
        const qualificationCounts = this.leads.reduce((acc, lead) => {
            const status = lead.qualification_status || 'Unqualified';
            acc[status] = (acc[status] || 0) + 1;
            return acc;
        }, {});
        
        document.getElementById('totalLeads').textContent = totalLeads;
        document.getElementById('averageScore').textContent = avgScore;
        document.getElementById('hotLeads').textContent = qualificationCounts.Hot || 0;
        document.getElementById('warmLeads').textContent = qualificationCounts.Warm || 0;
        
        // Update chart
        const distribution = this.calculateScoreDistribution();
        this.updateChart(distribution);
    }
    
    calculateScoreDistribution() {
        const distribution = { '0-20': 0, '21-40': 0, '41-60': 0, '61-80': 0, '81-100': 0 };
        
        this.leads.forEach(lead => {
            const score = lead.lead_score || 0;
            if (score <= 20) distribution['0-20']++;
            else if (score <= 40) distribution['21-40']++;
            else if (score <= 60) distribution['41-60']++;
            else if (score <= 80) distribution['61-80']++;
            else distribution['81-100']++;
        });
        
        return distribution;
    }
    
    initChart() {
        const canvas = document.getElementById('scoreChart');
        const ctx = canvas.getContext('2d');
        
        // Simple bar chart implementation
        this.chartCtx = ctx;
        this.chartCanvas = canvas;
        
        // Initial empty chart
        this.updateChart({ '0-20': 0, '21-40': 0, '41-60': 0, '61-80': 0, '81-100': 0 });
    }
    
    updateChart(distribution) {
        if (!this.chartCtx) return;
        
        const ctx = this.chartCtx;
        const canvas = this.chartCanvas;
        
        // Clear canvas
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        const labels = Object.keys(distribution);
        const values = Object.values(distribution);
        const maxValue = Math.max(...values, 1);
        
        const padding = 40;
        const chartWidth = canvas.width - padding * 2;
        const chartHeight = canvas.height - padding * 2;
        const barWidth = chartWidth / labels.length;
        
        // Colors for each bar
        const colors = ['#EF4444', '#F59E0B', '#F59E0B', '#10B981', '#10B981'];
        
        // Draw bars
        values.forEach((value, index) => {
            const barHeight = (value / maxValue) * chartHeight;
            const x = padding + index * barWidth + barWidth * 0.1;
            const y = padding + chartHeight - barHeight;
            const width = barWidth * 0.8;
            
            // Draw bar
            ctx.fillStyle = colors[index];
            ctx.fillRect(x, y, width, barHeight);
            
            // Draw value on top
            ctx.fillStyle = '#64748B';
            ctx.font = '12px Inter';
            ctx.textAlign = 'center';
            ctx.fillText(value, x + width / 2, y - 5);
            
            // Draw label
            ctx.fillText(labels[index], x + width / 2, padding + chartHeight + 20);
        });
        
        // Draw title
        ctx.fillStyle = '#1E293B';
        ctx.font = 'bold 14px Inter';
        ctx.textAlign = 'center';
        ctx.fillText('Lead Score Distribution', canvas.width / 2, 20);
    }
    
    showResultsSection() {
        document.getElementById('resultsSection').style.display = 'block';
    }
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Load saved theme
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.body.setAttribute('data-theme', savedTheme);
    
    const themeIcon = document.querySelector('#themeToggle i');
    if (themeIcon) {
        themeIcon.className = savedTheme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
    }
    
    // Initialize app
    window.app = new LeadScorerApp();
});

// Add styles for the modal content
const additionalStyles = `
<style>
.lead-details .detail-section {
    margin-bottom: 2rem;
}

.lead-details .detail-section h3 {
    margin-bottom: 1rem;
    color: var(--text-primary);
    border-bottom: 1px solid var(--border-color);
    padding-bottom: 0.5rem;
}

.detail-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1rem;
}

.detail-item {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
}

.detail-item label {
    font-weight: 600;
    color: var(--text-secondary);
    font-size: 0.875rem;
}

.score-breakdown {
    display: flex;
    gap: 2rem;
    align-items: center;
}

.total-score {
    text-align: center;
    padding: 1rem;
    background: var(--bg-secondary);
    border-radius: var(--border-radius);
}

.score-value {
    display: block;
    font-size: 2rem;
    font-weight: 700;
    color: var(--primary-color);
}

.score-label {
    font-size: 0.875rem;
    color: var(--text-secondary);
}

.category-scores {
    flex: 1;
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 1rem;
}

.category-score {
    display: flex;
    justify-content: space-between;
    padding: 0.75rem;
    background: var(--bg-secondary);
    border-radius: var(--border-radius);
}

.category-name {
    font-size: 0.875rem;
    text-transform: capitalize;
}

.category-value {
    font-weight: 600;
    color: var(--primary-color);
}

.tech-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
}

.tech-tag {
    padding: 0.25rem 0.75rem;
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    border-radius: 9999px;
    font-size: 0.75rem;
    color: var(--text-primary);
}

.contacts-list {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
}

.contact-item {
    padding: 1rem;
    background: var(--bg-secondary);
    border-radius: var(--border-radius);
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
}

.contact-item strong {
    color: var(--text-primary);
}

.contact-item span {
    color: var(--text-secondary);
    font-size: 0.875rem;
}

.action-list {
    margin: 0;
    padding-left: 1.5rem;
}

.action-list li {
    margin-bottom: 0.5rem;
    color: var(--text-primary);
}

.outreach-recommendations .recommendation-section {
    margin-bottom: 2rem;
}

.email-template {
    background: var(--bg-secondary);
    padding: 1.5rem;
    border-radius: var(--border-radius);
}

.email-field {
    margin-bottom: 1rem;
}

.email-field label {
    display: block;
    margin-bottom: 0.5rem;
    font-weight: 600;
    color: var(--text-primary);
}

.email-field input,
.email-field textarea {
    width: 100%;
    padding: 0.75rem;
    border: 1px solid var(--border-color);
    border-radius: var(--border-radius);
    background: var(--bg-primary);
    color: var(--text-primary);
    font-family: inherit;
    resize: vertical;
}

.action-timeline {
    background: var(--bg-secondary);
    padding: 1rem;
    border-radius: var(--border-radius);
    line-height: 1.8;
}
</style>
`;

document.head.insertAdjacentHTML('beforeend', additionalStyles);