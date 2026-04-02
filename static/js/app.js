/**
 * File Transfer Mobile-Friendly App
 * Core Logic for chunked uploads, management, and UI rendering
 */

const CONFIG = {
    CHUNK_SIZE: 5 * 1024 * 1024, // 5MB
    PARALLEL_UPLOADS: 4,
    AUTH_TOKEN: localStorage.getItem('AUTH_TOKEN') || '',
};

class FileTransferApp {
    constructor() {
        this.files = [];
        this.activeUploads = new Map(); // uploadId -> { name, progress, bytesSent }
        this.selectedFiles = new Set();
        this.searchTerm = '';
        this.sortBy = 'mtime'; // name, size, mtime
        this.sortOrder = -1; // -1 for desc, 1 for asc (default mtime desc)

        this.initElements();
        this.initEventListeners();
        this.refreshFileList();
    }

    initElements() {
        this.dropZone = document.getElementById('drop-zone');
        this.fileInput = document.getElementById('file-input');
        this.fileGrid = document.getElementById('file-grid');
        this.searchInput = document.getElementById('search-input');
        this.sortSelect = document.getElementById('sort-select');
        this.activeUploadsContainer = document.getElementById('active-uploads');
        this.downloadSelectedBtn = document.getElementById('download-selected-btn');
        this.deleteSelectedBtn = document.getElementById('delete-selected-btn');
        this.toastContainer = document.getElementById('toast-container');
    }

    initEventListeners() {
        // Upload Events
        this.dropZone.addEventListener('click', () => this.fileInput.click());
        this.dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            this.dropZone.classList.add('drag-over');
        });
        this.dropZone.addEventListener('dragleave', () => this.dropZone.classList.remove('drag-over'));
        this.dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            this.dropZone.classList.remove('drag-over');
            this.handleFiles(e.dataTransfer.files);
        });
        this.fileInput.addEventListener('change', () => this.handleFiles(this.fileInput.files));

        // Filter Events
        this.searchInput.addEventListener('input', (e) => {
            this.searchTerm = e.target.value.toLowerCase();
            this.render();
        });
        this.sortSelect.addEventListener('change', (e) => {
            this.sortBy = e.target.value;
            this.render();
        });

        // Bulk Actions
        this.downloadSelectedBtn.addEventListener('click', () => this.downloadSelected());
        this.deleteSelectedBtn.addEventListener('click', () => this.deleteSelected());
    }

    // --- Core Logic ---

    async refreshFileList() {
        try {
            const res = await fetch('/files', { headers: this.authHeaders() });
            if (!res.ok) throw new Error('Failed to fetch files');
            const data = await res.json();
            this.files = data.files || [];
            this.render();
        } catch (e) {
            this.notify('Error fetching files', 'error');
        }
    }

    handleFiles(fileList) {
        Array.from(fileList).forEach(file => this.uploadFile(file));
    }

    async uploadFile(file) {
        const uploadId = `up-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        const totalChunks = Math.ceil(file.size / CONFIG.CHUNK_SIZE);

        this.activeUploads.set(uploadId, { name: file.name, progress: 0, status: 'uploading' });
        this.renderUploads();

        try {
            // Get existing chunks (resumability check)
            const statusRes = await fetch(`/upload-status?upload_id=${encodeURIComponent(uploadId)}`, { headers: this.authHeaders() });
            let presentSet = new Set();
            if (statusRes.ok) {
                const statusData = await statusRes.json();
                presentSet = new Set(statusData.present || []);
            }

            const queue = [];
            for (let i = 0; i < totalChunks; i++) {
                if (!presentSet.has(i)) queue.push(i);
            }

            let completedChunks = presentSet.size;

            const worker = async () => {
                while (queue.length > 0) {
                    const idx = queue.shift();
                    const start = idx * CONFIG.CHUNK_SIZE;
                    const end = Math.min(start + CONFIG.CHUNK_SIZE, file.size);
                    const chunk = file.slice(start, end);

                    const res = await fetch('/upload-chunk', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/octet-stream',
                            'X-Upload-ID': uploadId,
                            'X-File-Name': file.name,
                            'X-Chunk-Index': idx,
                            'X-Total-Chunks': totalChunks,
                            ...this.authHeaders()
                        },
                        body: chunk
                    });

                    if (!res.ok) throw new Error('Chunk upload failed');
                    
                    completedChunks++;
                    const progress = Math.round((completedChunks / totalChunks) * 100);
                    this.activeUploads.get(uploadId).progress = progress;
                    this.updateUploadUI(uploadId);
                }
            };

            const workers = Array(CONFIG.PARALLEL_UPLOADS).fill(0).map(() => worker());
            await Promise.all(workers);

            this.notify(`Uploaded ${file.name}`, 'success');
            setTimeout(() => {
                this.activeUploads.delete(uploadId);
                this.renderUploads();
                this.refreshFileList();
            }, 1000);

        } catch (e) {
            console.error(e);
            this.activeUploads.get(uploadId).status = 'error';
            this.updateUploadUI(uploadId);
            this.notify(`Failed to upload ${file.name}`, 'error');
        }
    }

    async deleteFile(filename) {
        if (!confirm(`Are you sure you want to delete ${filename}?`)) return;
        try {
            const res = await fetch('/delete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', ...this.authHeaders() },
                body: JSON.stringify({ filename })
            });
            if (!res.ok) throw new Error('Delete failed');
            this.notify(`Deleted ${filename}`, 'success');
            this.refreshFileList();
        } catch (e) {
            this.notify('Failed to delete file', 'error');
        }
    }

    async deleteSelected() {
        const selected = Array.from(this.selectedFiles);
        if (selected.length === 0) return;
        if (!confirm(`Delete ${selected.length} files?`)) return;

        for (const filename of selected) {
            await fetch('/delete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', ...this.authHeaders() },
                body: JSON.stringify({ filename })
            });
        }
        this.selectedFiles.clear();
        this.refreshFileList();
        this.notify('Batch delete complete', 'success');
    }

    downloadSelected() {
        const selected = Array.from(this.selectedFiles);
        if (selected.length === 0) return;

        if (selected.length === 1) {
            window.location.href = this.tokenizeUrl(`/uploads/${encodeURIComponent(selected[0])}`);
            return;
        }

        const form = document.createElement('form');
        form.method = 'POST';
        form.action = this.tokenizeUrl('/download-zip');
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'filenames';
        input.value = JSON.stringify(selected);
        form.appendChild(input);
        document.body.appendChild(form);
        form.submit();
        form.remove();
    }

    // --- UI Rendering ---

    render() {
        // Filter and Sort
        let filtered = this.files.filter(f => f.name.toLowerCase().includes(this.searchTerm));
        
        filtered.sort((a, b) => {
            let valA = a[this.sortBy];
            let valB = b[this.sortBy];
            if (typeof valA === 'string') {
                return valA.localeCompare(valB) * this.sortOrder;
            }
            return (valA - valB) * this.sortOrder;
        });

        // If sorting by mtime, it defaults to desc
        if (this.sortBy === 'mtime') {
            filtered.sort((a, b) => (b.mtime - a.mtime));
        }

        this.fileGrid.innerHTML = '';
        if (filtered.length === 0) {
            this.fileGrid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 3rem;">No files found</div>';
        } else {
            filtered.forEach(file => {
                const card = this.createFileCard(file);
                this.fileGrid.appendChild(card);
            });
        }

        this.updateSelectionUI();
    }

    createFileCard(file) {
        const isSelected = this.selectedFiles.has(file.name);
        const card = document.createElement('div');
        card.className = `file-card ${isSelected ? 'selected' : ''}`;
        
        const ext = file.name.split('.').pop().toLowerCase();
        let icon = '📄';
        if (['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(ext)) icon = '🖼️';
        if (['mp4', 'mkv', 'mov'].includes(ext)) icon = '🎬';
        if (['zip', 'rar', '7z'].includes(ext)) icon = '📦';
        if (['pdf'].includes(ext)) icon = '📕';

        card.innerHTML = `
            <input type="checkbox" class="selection-checkbox" ${isSelected ? 'checked' : ''}>
            <div class="file-icon-wrapper">${icon}</div>
            <div class="file-info-main">
                <div class="file-name" title="${file.name}">${file.name}</div>
                <div class="file-meta">${this.formatSize(file.size)} • ${this.formatDate(file.mtime)}</div>
            </div>
            <div class="file-actions">
                <a href="${this.tokenizeUrl('/uploads/' + encodeURIComponent(file.name))}" download class="btn btn-primary btn-icon" title="Download">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
                </a>
                <button class="btn btn-danger-ghost btn-icon delete-btn" title="Delete">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
                </button>
            </div>
        `;

        card.querySelector('.selection-checkbox').addEventListener('change', (e) => {
            if (e.target.checked) this.selectedFiles.add(file.name);
            else this.selectedFiles.delete(file.name);
            this.render();
        });

        card.querySelector('.delete-btn').addEventListener('click', (e) => {
            e.stopPropagation();
            this.deleteFile(file.name);
        });

        return card;
    }

    renderUploads() {
        this.activeUploadsContainer.innerHTML = '';
        this.activeUploads.forEach((data, id) => {
            const div = document.createElement('div');
            div.id = id;
            div.className = 'upload-card';
            div.innerHTML = `
                <div class="upload-info">
                    <span class="file-name">${data.name}</span>
                    <span class="progress-text">${data.progress}%</span>
                </div>
                <div class="progress-container">
                    <div class="progress-bar" style="width: ${data.progress}%"></div>
                </div>
            `;
            this.activeUploadsContainer.appendChild(div);
        });
    }

    updateUploadUI(id) {
        const data = this.activeUploads.get(id);
        const card = document.getElementById(id);
        if (card && data) {
            card.querySelector('.progress-text').textContent = `${data.progress}%`;
            card.querySelector('.progress-bar').style.width = `${data.progress}%`;
        }
    }

    updateSelectionUI() {
        const count = this.selectedFiles.size;
        this.downloadSelectedBtn.style.display = count > 0 ? 'inline-flex' : 'none';
        this.deleteSelectedBtn.style.display = count > 0 ? 'inline-flex' : 'none';
        if (count > 0) {
            this.downloadSelectedBtn.innerHTML = `
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
                Download (${count})
            `;
        }
    }

    // --- Helpers ---

    authHeaders() {
        return CONFIG.AUTH_TOKEN ? { 'X-Auth-Token': CONFIG.AUTH_TOKEN } : {};
    }

    tokenizeUrl(url) {
        if (!CONFIG.AUTH_TOKEN) return url;
        const u = new URL(url, window.location.origin);
        u.searchParams.set('token', CONFIG.AUTH_TOKEN);
        return u.toString();
    }

    formatSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    formatDate(timestamp) {
        const date = new Date(timestamp * 1000);
        return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    }

    notify(msg, type = 'success') {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = msg;
        this.toastContainer.appendChild(toast);
        setTimeout(() => toast.remove(), 4000);
    }
}

// Start the app
window.addEventListener('DOMContentLoaded', () => {
    window.appState = new FileTransferApp();
});
