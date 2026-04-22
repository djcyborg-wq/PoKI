const API_BASE = '/api';

class DocumentChatApp {
    constructor() {
        this.chatHistory = [];
        this.selectedFolders = [];
        this.allFolders = [];
        
        this.init();
    }
    
    async init() {
        this.bindElements();
        this.bindEvents();
        await this.checkHealth();
        await this.loadFolders();
        await this.loadStats();
    }
    
    bindElements() {
        this.elements = {
            statusIndicator: document.getElementById('status-indicator'),
            statusText: document.getElementById('status-text'),
            chatHistory: document.getElementById('chat-history'),
            questionInput: document.getElementById('question-input'),
            sendBtn: document.getElementById('send-btn'),
            folderCheckboxes: document.getElementById('folder-checkboxes'),
            foldersList: document.getElementById('folders-list'),
            statsDisplay: document.getElementById('stats-display'),
            reindexBtn: document.getElementById('reindex-btn'),
            refreshBtn: document.getElementById('refresh-stats-btn'),
            loadingOverlay: document.getElementById('loading-overlay'),
            loadingText: document.getElementById('loading-text')
        };
    }
    
    bindEvents() {
        this.elements.sendBtn.addEventListener('click', () => this.sendQuestion());
        
        this.elements.questionInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendQuestion();
            }
        });
        
        this.elements.reindexBtn.addEventListener('click', () => this.reindexAll());
        this.elements.refreshBtn.addEventListener('click', () => this.refreshAll());
    }
    
    async checkHealth() {
        try {
            const response = await fetch(`${API_BASE}/health`);
            const data = await response.json();
            
            this.updateStatus(
                data.ollama === 'connected' ? 'connected' : 'unavailable',
                `Ollama: ${data.ollama} | ${data.model || 'unknown'}`
            );
        } catch (error) {
            this.updateStatus('unavailable', 'Systemfehler');
        }
    }
    
    updateStatus(status, text) {
        this.elements.statusIndicator.className = `status-indicator status-${status}`;
        this.elements.statusText.textContent = text;
    }
    
    async loadFolders() {
        try {
            const response = await fetch(`${API_BASE}/folders`);
            const data = await response.json();
            
            this.allFolders = data.folders.map(f => ({
                id: f.id,
                path: f.path,
                name: f.path.split(/[/\\]/).pop(),
                enabled: f.enabled,
                documentCount: f.document_count,
                totalChunks: f.total_chunks
            }));
            
            this.renderFolderCheckboxes();
            this.renderFoldersList();
        } catch (error) {
            console.error('Error loading folders:', error);
        }
    }
    
    renderFolderCheckboxes() {
        this.elements.folderCheckboxes.innerHTML = this.allFolders.map(folder => `
            <label class="folder-checkbox">
                <input type="checkbox" value="${folder.path}" data-folder-path="${folder.path}">
                ${folder.name}
            </label>
        `).join('');
        
        this.elements.folderCheckboxes.querySelectorAll('input').forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                if (e.target.checked) {
                    if (!this.selectedFolders.includes(e.target.value)) {
                        this.selectedFolders.push(e.target.value);
                    }
                } else {
                    this.selectedFolders = this.selectedFolders.filter(f => f !== e.target.value);
                }
            });
        });
    }
    
    renderFoldersList() {
        this.elements.foldersList.innerHTML = this.allFolders.map(folder => `
            <div class="folder-item">
                <div class="folder-name">${folder.path}</div>
                <div class="folder-stats">
                    ${folder.documentCount || 0} Dokumente | ${folder.totalChunks || 0} Chunks
                </div>
            </div>
        `).join('');
    }
    
    async loadStats() {
        try {
            const response = await fetch(`${API_BASE}/stats`);
            const data = await response.json();
            
            let html = `
                <p>Chunks gesamt: <span class="stat-value">${data.total_chunks || 0}</span></p>
                <p>Ordner: <span class="stat-value">${data.configured_folders || 0}</span></p>
            `;
            
            if (data.folder_counts) {
                html += '<h4 style="margin-top:12px;font-size:0.875rem;">Pro Ordner:</h4>';
                for (const [folder, count] of Object.entries(data.folder_counts)) {
                    const folderName = folder.split(/[/\\]/).pop();
                    html += `<p>${folderName}: <span class="stat-value">${count}</span></p>`;
                }
            }
            
            this.elements.statsDisplay.innerHTML = html;
        } catch (error) {
            console.error('Error loading stats:', error);
            this.elements.statsDisplay.innerHTML = '<p>Fehler beim Laden</p>';
        }
    }
    
    async sendQuestion() {
        const question = this.elements.questionInput.value.trim();
        if (!question) return;
        
        this.showLoading('Frage wird bearbeitet...');
        
        this.addMessage('user', question);
        this.elements.questionInput.value = '';
        
        try {
            const response = await fetch(`${API_BASE}/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    question: question,
                    history: [],
                    top_k: 10,
                    folders: this.selectedFolders.length > 0 ? this.selectedFolders : null
                })
            });
            
            if (!response.ok) {
                throw new Error('Anfrage fehlgeschlagen');
            }
            
            const data = await response.json();
            
            this.addMessage('assistant', data.answer, data.sources, data.query_time_ms);
            
            this.chatHistory.push({ role: 'user', content: question });
            this.chatHistory.push({ role: 'assistant', content: data.answer });
            
        } catch (error) {
            this.addMessage('assistant', 'Entschuldigung, es ist ein Fehler aufgetreten.');
            console.error('Chat error:', error);
        }
        
        this.hideLoading();
    }
    
    addMessage(role, content, sources = [], queryTime = 0) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;
        
        let html = `<div class="content">${this.escapeHtml(content)}</div>`;
        
        if (sources && sources.length > 0) {
            html += `
                <div class="sources">
                    <h4>Quellen:</h4>
                    ${sources.map(s => {
                        const fileUrl = 'file:///' + s.file.replace(/\\/g, '/');
                        return `
                        <div class="source-item">
                            <a href="${fileUrl}" target="_blank" class="source-link">${s.file}</a>
                            <span class="source-folder">(${s.folder})</span>
                            <br><small>${this.escapeHtml(s.snippet)}</small>
                        </div>
                    `}).join('')}
                </div>
            `;
        }
        
        if (queryTime > 0) {
            html += `<div class="query-time">Antwortzeit: ${queryTime}ms</div>`;
        }
        
        messageDiv.innerHTML = html;
        this.elements.chatHistory.appendChild(messageDiv);
        this.elements.chatHistory.scrollTop = this.elements.chatHistory.scrollHeight;
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    async reindexAll() {
        if (!confirm('Wirklich alle Dokumente neu indizieren?')) return;
        
        this.showLoading('Neuindizierung läuft...');
        
        try {
            await fetch(`${API_BASE}/reindex`, { method: 'POST' });
            await this.delay(2000);
            await this.loadStats();
            await this.loadFolders();
        } catch (error) {
            console.error('Reindex error:', error);
        }
        
        this.hideLoading();
    }
    
    async refreshAll() {
        this.showLoading('Aktualisiere...');
        await this.checkHealth();
        await this.loadFolders();
        await this.loadStats();
        this.hideLoading();
    }
    
    showLoading(text) {
        this.elements.loadingText.textContent = text;
        this.elements.loadingOverlay.classList.remove('hidden');
    }
    
    hideLoading() {
        this.elements.loadingOverlay.classList.add('hidden');
    }
    
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.app = new DocumentChatApp();
});