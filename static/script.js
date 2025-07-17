class PDFEditorApp {
    constructor() {
        this.sessionId = this.generateSessionId();
        this.files = [];
        this.draggedElement = null;
        this.dragPlaceholder = null;
        
        this.initializeElements();
        this.setupEventListeners();
        this.loadExistingFiles();
    }
    
    generateSessionId() {
        return 'session_' + Math.random().toString(36).substr(2, 9) + Date.now().toString(36);
    }
    
    initializeElements() {
        this.dropZone = document.getElementById('drop-zone');
        this.fileInput = document.getElementById('file-input');
        this.filesContainer = document.getElementById('files-container');
        this.filesGrid = document.getElementById('files-grid');
        this.combineBtn = document.getElementById('combine-btn');
        this.clearAllBtn = document.getElementById('clear-all');
        this.progressModal = document.getElementById('progress-modal');
        this.successModal = document.getElementById('success-modal');
        this.progressText = document.getElementById('progress-text');
        this.downloadBtn = document.getElementById('download-btn');
        this.closeSuccessBtn = document.getElementById('close-success');
    }
    
    setupEventListeners() {
        // File input
        this.fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
        
        // Drop zone
        this.dropZone.addEventListener('dragover', (e) => this.handleDragOver(e));
        this.dropZone.addEventListener('drop', (e) => this.handleDrop(e));
        this.dropZone.addEventListener('dragenter', (e) => this.handleDragEnter(e));
        this.dropZone.addEventListener('dragleave', (e) => this.handleDragLeave(e));
        
        // Buttons
        this.combineBtn.addEventListener('click', () => this.combineFiles());
        this.clearAllBtn.addEventListener('click', () => this.clearAllFiles());
        this.downloadBtn.addEventListener('click', () => this.downloadPDF());
        this.closeSuccessBtn.addEventListener('click', () => this.hideModal(this.successModal));
        
        // Files grid drag and drop
        this.filesGrid.addEventListener('dragover', (e) => this.handleGridDragOver(e));
        this.filesGrid.addEventListener('drop', (e) => this.handleGridDrop(e));
    }
    
    async loadExistingFiles() {
        try {
            const response = await fetch(`/files/${this.sessionId}`);
            const data = await response.json();
            
            if (data.files && data.files.length > 0) {
                this.files = data.files;
                this.renderFiles();
                this.updateUI();
            }
        } catch (error) {
            console.error('Error loading existing files:', error);
        }
    }
    
    handleDragOver(e) {
        e.preventDefault();
        this.dropZone.classList.add('dragover');
    }
    
    handleDragEnter(e) {
        e.preventDefault();
        this.dropZone.classList.add('dragover');
    }
    
    handleDragLeave(e) {
        e.preventDefault();
        if (!this.dropZone.contains(e.relatedTarget)) {
            this.dropZone.classList.remove('dragover');
        }
    }
    
    handleDrop(e) {
        e.preventDefault();
        this.dropZone.classList.remove('dragover');
        
        const files = Array.from(e.dataTransfer.files);
        this.uploadFiles(files);
    }
    
    handleFileSelect(e) {
        const files = Array.from(e.target.files);
        this.uploadFiles(files);
        e.target.value = ''; // Reset input
    }
    
    async uploadFiles(files) {
        if (files.length === 0) return;
        
        this.showModal(this.progressModal);
        this.progressText.textContent = 'Uploading files...';
        
        const formData = new FormData();
        files.forEach(file => formData.append('files', file));
        formData.append('session_id', this.sessionId);
        
        try {
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (data.files) {
                this.files.push(...data.files);
                this.renderFiles();
                this.updateUI();
            }
            
            this.hideModal(this.progressModal);
        } catch (error) {
            console.error('Upload error:', error);
            this.hideModal(this.progressModal);
            alert('Error uploading files. Please try again.');
        }
    }
    
    renderFiles() {
        this.filesGrid.innerHTML = '';
        
        this.files.forEach((file, index) => {
            const fileElement = this.createFileElement(file, index);
            this.filesGrid.appendChild(fileElement);
        });
    }
    
    createFileElement(file, index) {
        const div = document.createElement('div');
        div.className = 'file-item';
        div.draggable = true;
        div.dataset.fileId = file.id;
        div.dataset.index = index;
        
        const thumbnail = document.createElement('div');
        thumbnail.className = 'file-thumbnail';
        
        if (file.thumbnail) {
            const img = document.createElement('img');
            img.src = `data:image/png;base64,${file.thumbnail}`;
            img.alt = file.filename;
            thumbnail.appendChild(img);
        } else {
            const icon = document.createElement('i');
            icon.className = file.type === 'pdf' ? 'fas fa-file-pdf' : 'fas fa-image';
            thumbnail.appendChild(icon);
        }
        
        const fileName = document.createElement('div');
        fileName.className = 'file-name';
        fileName.textContent = file.filename;
        
        const fileType = document.createElement('div');
        fileType.className = 'file-type';
        fileType.textContent = file.type.toUpperCase();
        
        const removeBtn = document.createElement('button');
        removeBtn.className = 'remove-btn';
        removeBtn.innerHTML = '<i class="fas fa-times"></i>';
        removeBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.removeFile(file.id);
        });
        
        div.appendChild(thumbnail);
        div.appendChild(fileName);
        div.appendChild(fileType);
        div.appendChild(removeBtn);
        
        // Drag events
        div.addEventListener('dragstart', (e) => this.handleFileDragStart(e));
        div.addEventListener('dragend', (e) => this.handleFileDragEnd(e));
        div.addEventListener('dragover', (e) => this.handleFileDragOver(e));
        div.addEventListener('dragenter', (e) => this.handleFileDragEnter(e));
        div.addEventListener('dragleave', (e) => this.handleFileDragLeave(e));
        
        return div;
    }
    
    handleFileDragStart(e) {
        this.draggedElement = e.target;
        e.target.classList.add('dragging');
        
        // Create placeholder
        this.dragPlaceholder = document.createElement('div');
        this.dragPlaceholder.className = 'file-item drag-placeholder';
        this.dragPlaceholder.innerHTML = '<i class="fas fa-arrows-alt"></i> Drop here';
        
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/html', e.target.outerHTML);
    }
    
    handleFileDragEnd(e) {
        e.target.classList.remove('dragging');
        this.draggedElement = null;
        
        // Remove placeholder
        if (this.dragPlaceholder && this.dragPlaceholder.parentNode) {
            this.dragPlaceholder.parentNode.removeChild(this.dragPlaceholder);
        }
        this.dragPlaceholder = null;
        
        // Remove drag-over classes
        document.querySelectorAll('.file-item.drag-over').forEach(el => {
            el.classList.remove('drag-over');
        });
    }
    
    handleFileDragOver(e) {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
    }
    
    handleFileDragEnter(e) {
        e.preventDefault();
        if (e.target.classList.contains('file-item') && e.target !== this.draggedElement) {
            e.target.classList.add('drag-over');
        }
    }
    
    handleFileDragLeave(e) {
        e.preventDefault();
        if (e.target.classList.contains('file-item')) {
            e.target.classList.remove('drag-over');
        }
    }
    
    handleGridDragOver(e) {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        
        const afterElement = this.getDragAfterElement(this.filesGrid, e.clientY);
        
        if (this.dragPlaceholder) {
            if (afterElement == null) {
                this.filesGrid.appendChild(this.dragPlaceholder);
            } else {
                this.filesGrid.insertBefore(this.dragPlaceholder, afterElement);
            }
        }
    }
    
    handleGridDrop(e) {
        e.preventDefault();
        
        if (!this.draggedElement) return;
        
        const afterElement = this.getDragAfterElement(this.filesGrid, e.clientY);
        const draggedIndex = parseInt(this.draggedElement.dataset.index);
        
        let newIndex;
        if (afterElement == null) {
            newIndex = this.files.length - 1;
        } else {
            newIndex = parseInt(afterElement.dataset.index);
            if (draggedIndex < newIndex) newIndex--;
        }
        
        if (draggedIndex !== newIndex) {
            // Reorder files array
            const [movedFile] = this.files.splice(draggedIndex, 1);
            this.files.splice(newIndex, 0, movedFile);
            
            // Update server
            this.updateFileOrder();
            
            // Re-render
            this.renderFiles();
        }
    }
    
    getDragAfterElement(container, y) {
        const draggableElements = [...container.querySelectorAll('.file-item:not(.dragging)')];
        
        return draggableElements.reduce((closest, child) => {
            const box = child.getBoundingClientRect();
            const offset = y - box.top - box.height / 2;
            
            if (offset < 0 && offset > closest.offset) {
                return { offset: offset, element: child };
            } else {
                return closest;
            }
        }, { offset: Number.NEGATIVE_INFINITY }).element;
    }
    
    async updateFileOrder() {
        const order = this.files.map(file => file.id);
        
        const formData = new FormData();
        formData.append('session_id', this.sessionId);
        formData.append('order', JSON.stringify(order));
        
        try {
            await fetch('/reorder', {
                method: 'POST',
                body: formData
            });
        } catch (error) {
            console.error('Error updating file order:', error);
        }
    }
    
    async removeFile(fileId) {
        const formData = new FormData();
        formData.append('session_id', this.sessionId);
        formData.append('file_id', fileId);
        
        try {
            const response = await fetch('/remove', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.files = this.files.filter(file => file.id !== fileId);
                this.renderFiles();
                this.updateUI();
            }
        } catch (error) {
            console.error('Error removing file:', error);
        }
    }
    
    async clearAllFiles() {
        if (this.files.length === 0) return;
        
        if (confirm('Are you sure you want to remove all files?')) {
            // Remove all files one by one
            for (const file of this.files) {
                await this.removeFile(file.id);
            }
        }
    }
    
    async combineFiles() {
        if (this.files.length === 0) {
            alert('Please add some files first!');
            return;
        }
        
        this.showModal(this.progressModal);
        this.progressText.textContent = 'Combining files...';
        
        const formData = new FormData();
        formData.append('session_id', this.sessionId);
        
        try {
            const response = await fetch('/combine', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            this.hideModal(this.progressModal);
            
            if (data.download_url) {
                this.downloadUrl = data.download_url;
                this.showModal(this.successModal);
            } else {
                alert('Error combining files: ' + (data.error || 'Unknown error'));
            }
        } catch (error) {
            this.hideModal(this.progressModal);
            console.error('Error combining files:', error);
            alert('Error combining files. Please try again.');
        }
    }
    
    downloadPDF() {
        if (this.downloadUrl) {
            window.open(this.downloadUrl, '_blank');
            this.hideModal(this.successModal);
        }
    }
    
    updateUI() {
        const hasFiles = this.files.length > 0;
        
        if (hasFiles) {
            this.dropZone.style.display = 'none';
            this.filesContainer.style.display = 'block';
            this.combineBtn.disabled = false;
        } else {
            this.dropZone.style.display = 'block';
            this.filesContainer.style.display = 'none';
            this.combineBtn.disabled = true;
        }
    }
    
    showModal(modal) {
        modal.classList.add('show');
    }
    
    hideModal(modal) {
        modal.classList.remove('show');
    }
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new PDFEditorApp();
});