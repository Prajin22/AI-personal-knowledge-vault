// Modern AI Study Assistant - Interactive JavaScript

class ModernUI {
    constructor() {
        this.chatOpen = false;
        this.notifications = [];
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupNavigation();
        this.setupChatWidget();
        this.setupUploadModal();
        this.setupNotifications();
        this.setupAnimations();
        this.setupAuthForms();
    }

    setupEventListeners() {
        // Mobile menu toggle
        const navToggle = document.querySelector('.nav-toggle');
        if (navToggle) {
            navToggle.addEventListener('click', () => this.toggleMobileMenu());
        }

        // Hero buttons
        const startChatBtn = document.getElementById('start-chat');
        const uploadNotesBtn = document.getElementById('upload-notes');

        if (startChatBtn) {
            startChatBtn.addEventListener('click', () => this.openChat());
        }

        if (uploadNotesBtn) {
            uploadNotesBtn.addEventListener('click', () => this.openUploadModal());
        }

        // Chat widget
        const chatToggle = document.getElementById('chat-toggle');
        const chatClose = document.getElementById('chat-close');

        if (chatToggle) {
            chatToggle.addEventListener('click', () => this.toggleChat());
        }

        if (chatClose) {
            chatClose.addEventListener('click', () => this.closeChat());
        }

        // Chat input
        const chatInput = document.getElementById('chat-input');
        const sendButton = document.getElementById('send-button');

        if (chatInput) {
            chatInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.sendMessage();
                }
            });
        }

        if (sendButton) {
            sendButton.addEventListener('click', () => this.sendMessage());
        }

        // Upload modal
        const addFirstNoteBtn = document.getElementById('add-first-note');
        const modalClose = document.getElementById('modal-close');
        const cancelUpload = document.getElementById('cancel-upload');

        if (addFirstNoteBtn) {
            addFirstNoteBtn.addEventListener('click', () => this.openUploadModal());
        }

        if (modalClose) {
            modalClose.addEventListener('click', () => this.closeUploadModal());
        }

        if (cancelUpload) {
            cancelUpload.addEventListener('click', () => this.closeUploadModal());
        }

        // Upload form
        const uploadForm = document.getElementById('upload-form');
        if (uploadForm) {
            uploadForm.addEventListener('submit', (e) => this.handleFileUpload(e));
        }

        // Click outside modal to close
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal')) {
                this.closeUploadModal();
            }
        });

        // Window resize for responsive design
        window.addEventListener('resize', () => this.handleResize());
    }

    updateNavigation() {
        // Highlight current page in navigation
        const currentPath = window.location.pathname;

        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.remove('active');
            if (link.getAttribute('href') === currentPath) {
                link.classList.add('active');
            }
        });
    }

    toggleMobileMenu() {
        const navLinks = document.querySelector('.nav-links');
        const navToggle = document.querySelector('.nav-toggle');

        navLinks.classList.toggle('mobile-open');
        navToggle.classList.toggle('active');
    }

    closeMobileMenu() {
        const navLinks = document.querySelector('.nav-links');
        const navToggle = document.querySelector('.nav-toggle');

        navLinks.classList.remove('mobile-open');
        navToggle.classList.remove('active');
    }

    // ===== NAVIGATION =====
    switchSection(sectionName) {
        // Update navigation
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.remove('active');
        });

        const activeLink = document.querySelector(`[data-section="${sectionName}"]`);
        if (activeLink) {
            activeLink.classList.add('active');
        }

        // Update content sections
        document.querySelectorAll('.content-section').forEach(section => {
            section.classList.remove('active');
        });

        const targetSection = document.getElementById(`${sectionName}-section`);
        if (targetSection) {
            targetSection.classList.add('active');
        }

        this.currentSection = sectionName;

        // Close mobile menu if open
        this.closeMobileMenu();
    }

    toggleMobileMenu() {
        const navLinks = document.querySelector('.nav-links');
        const navToggle = document.querySelector('.nav-toggle');

        navLinks.classList.toggle('mobile-open');
        navToggle.classList.toggle('active');
    }

    closeMobileMenu() {
        const navLinks = document.querySelector('.nav-links');
        const navToggle = document.querySelector('.nav-toggle');

        navLinks.classList.remove('mobile-open');
        navToggle.classList.remove('active');
    }

    // ===== CHAT SYSTEM =====
    initializeChat() {
        // Chat is already initialized in HTML with welcome message
        this.updateChatIndicator();
    }

    toggleChat() {
        const chatContainer = document.getElementById('chat-container');

        if (this.chatOpen) {
            this.closeChat();
        } else {
            this.openChat();
        }
    }

    openChat() {
        const chatContainer = document.getElementById('chat-container');

        if (chatContainer) {
            chatContainer.style.display = 'flex';
            this.chatOpen = true;
            this.updateChatIndicator();

            // Focus on input
            const chatInput = document.getElementById('chat-input');
            if (chatInput) {
                setTimeout(() => chatInput.focus(), 300);
            }
        }
    }

    closeChat() {
        const chatContainer = document.getElementById('chat-container');

        if (chatContainer) {
            chatContainer.style.display = 'none';
            this.chatOpen = false;
            this.updateChatIndicator();
        }
    }

    updateChatIndicator() {
        const indicator = document.getElementById('chat-indicator');

        if (indicator) {
            if (this.chatOpen) {
                indicator.style.display = 'none';
            } else {
                indicator.style.display = 'flex';
            }
        }
    }

    async sendMessage() {
        const chatInput = document.getElementById('chat-input');
        const message = chatInput.value.trim();

        if (!message) return;

        // Add user message
        this.addMessage('user', message);
        chatInput.value = '';

        // Show typing indicator
        this.showTypingIndicator();

        try {
            // Send to backend API
            const response = await this.sendToAPI(message);
            this.hideTypingIndicator();

            // Add AI response
            this.addMessage('ai', response);

        } catch (error) {
            this.hideTypingIndicator();
            this.addMessage('ai', 'Sorry, I encountered an error. Please try again.');

            console.error('Chat API error:', error);
        }
    }

    async sendToAPI(message) {
        // This would connect to your Flask backend
        const response = await fetch('/ask', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: message,
                limit: 5,
                max_length: 150
            })
        });

        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }

        const data = await response.json();
        return data.answer || 'I apologize, but I couldn\'t generate a response.';
    }

    addMessage(type, content) {
        const chatMessages = document.getElementById('chat-messages');
        if (!chatMessages) return;

        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}-message`;

        messageDiv.innerHTML = `
            <div class="message-avatar">
                <i class="fas fa-${type === 'ai' ? 'robot' : 'user'}"></i>
            </div>
            <div class="message-content">
                <p>${this.escapeHtml(content)}</p>
            </div>
        `;

        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;

        // Add entrance animation
        setTimeout(() => {
            messageDiv.style.opacity = '1';
            messageDiv.style.transform = 'translateY(0)';
        }, 10);
    }

    showTypingIndicator() {
        const typingDiv = document.getElementById('chat-typing');
        if (typingDiv) {
            typingDiv.style.display = 'flex';
        }
    }

    hideTypingIndicator() {
        const typingDiv = document.getElementById('chat-typing');
        if (typingDiv) {
            typingDiv.style.display = 'none';
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // ===== UPLOAD SYSTEM =====
    openUploadModal() {
        const modal = document.getElementById('upload-modal');
        if (modal) {
            modal.classList.add('show');
            document.body.style.overflow = 'hidden';
        }
    }

    closeUploadModal() {
        const modal = document.getElementById('upload-modal');
        if (modal) {
            modal.classList.remove('show');
            document.body.style.overflow = '';
        }

        // Reset form
        const uploadForm = document.getElementById('upload-form');
        if (uploadForm) {
            uploadForm.reset();
        }

        // Reset progress
        this.resetUploadProgress();
    }

    async handleFileUpload(event) {
        event.preventDefault();

        const formData = new FormData(event.target);
        const fileInput = document.getElementById('file-input');
        const files = fileInput.files;

        if (!files || files.length === 0) {
            this.showNotification('Please select at least one file.', 'warning');
            return;
        }

        // Show progress
        this.showUploadProgress();

        try {
            // This would connect to your Flask upload endpoint
            // For now, we'll simulate the upload
            await this.simulateFileUpload(files);

            this.showNotification('Files uploaded successfully!', 'success');
            this.closeUploadModal();

            // Refresh notes section
            this.loadNotes();

        } catch (error) {
            this.showNotification('Upload failed. Please try again.', 'error');
            console.error('Upload error:', error);
        } finally {
            this.resetUploadProgress();
        }
    }

    async simulateFileUpload(files) {
        // Simulate upload progress
        const progressFill = document.getElementById('progress-fill');
        const progressText = document.getElementById('progress-text');

        for (let i = 0; i <= 100; i += 10) {
            if (progressFill) progressFill.style.width = `${i}%`;
            if (progressText) progressText.textContent = `Uploading... ${i}%`;

            await new Promise(resolve => setTimeout(resolve, 200));
        }
    }

    showUploadProgress() {
        const progressDiv = document.getElementById('upload-progress');
        if (progressDiv) {
            progressDiv.style.display = 'block';
        }
    }

    resetUploadProgress() {
        const progressDiv = document.getElementById('upload-progress');
        const progressFill = document.getElementById('progress-fill');
        const progressText = document.getElementById('progress-text');

        if (progressDiv) progressDiv.style.display = 'none';
        if (progressFill) progressFill.style.width = '0%';
        if (progressText) progressText.textContent = 'Uploading...';
    }

    // ===== DATA MANAGEMENT =====
    async loadUserData() {
        try {
            // This would load user stats from your Flask backend
            const stats = await this.fetchUserStats();

            this.updateUserStats(stats);
        } catch (error) {
            console.error('Failed to load user data:', error);
        }
    }

    async fetchUserStats() {
        // Simulate API call
        return {
            sessionCount: 12,
            notesCount: 8,
            studyTime: 45 // hours
        };
    }

    updateUserStats(stats) {
        const sessionCount = document.getElementById('session-count');
        const notesCount = document.getElementById('notes-count');
        const studyTime = document.getElementById('study-time');

        if (sessionCount) sessionCount.textContent = stats.sessionCount;
        if (notesCount) notesCount.textContent = stats.notesCount;
        if (studyTime) studyTime.textContent = `${stats.studyTime}h`;
    }

    async loadNotes() {
        try {
            // This would load notes from your Flask backend
            const notes = await this.fetchNotes();

            this.renderNotes(notes);
        } catch (error) {
            console.error('Failed to load notes:', error);
        }
    }

    async fetchNotes() {
        // Simulate API call
        return [
            // Notes would be loaded from backend
        ];
    }

    renderNotes(notes) {
        const notesGrid = document.getElementById('notes-grid');
        if (!notesGrid) return;

        if (notes.length === 0) {
            // Keep empty state
            return;
        }

        // Render actual notes
        notesGrid.innerHTML = notes.map(note => `
            <div class="note-card">
                <h3>${this.escapeHtml(note.title)}</h3>
                <p>${this.escapeHtml(note.preview)}</p>
                <small>${this.formatDate(note.created_at)}</small>
            </div>
        `).join('');
    }

    // ===== ANIMATIONS & EFFECTS =====
    initializeParticles() {
        // Add subtle particle effects around the flame
        const heroSection = document.querySelector('.hero-section');

        for (let i = 0; i < 20; i++) {
            const particle = document.createElement('div');
            particle.className = 'background-particle';
            particle.style.left = Math.random() * 100 + '%';
            particle.style.top = Math.random() * 100 + '%';
            particle.style.animationDelay = Math.random() * 20 + 's';
            particle.style.animationDuration = (Math.random() * 10 + 10) + 's';

            heroSection.appendChild(particle);
        }
    }

    startFlameAnimation() {
        // Add dynamic flame effects
        const flameCore = document.querySelector('.flame-core');
        if (flameCore) {
            setInterval(() => {
                const intensity = Math.random() * 0.3 + 0.7;
                flameCore.style.opacity = intensity;
            }, 100);
        }
    }

    // ===== UTILITIES =====
    showNotification(message, type = 'info') {
        const notifications = document.getElementById('notifications');
        if (!notifications) return;

        const notification = document.createElement('div');
        notification.className = `notification ${type}`;

        const icon = this.getNotificationIcon(type);

        notification.innerHTML = `
            <i class="fas fa-${icon}"></i>
            <span>${message}</span>
        `;

        notifications.appendChild(notification);

        // Show notification
        setTimeout(() => notification.classList.add('show'), 10);

        // Auto remove after 5 seconds
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 300);
        }, 5000);

        // Store for management
        this.notifications.push(notification);
    }

    getNotificationIcon(type) {
        const icons = {
            success: 'check-circle',
            error: 'exclamation-circle',
            warning: 'exclamation-triangle',
            info: 'info-circle'
        };
        return icons[type] || 'info-circle';
    }

    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    }

    handleResize() {
        // Handle responsive adjustments
        if (window.innerWidth <= 768) {
            this.closeChat(); // Close chat on mobile
        }
    }

    // ===== LIFECYCLE =====
    destroy() {
        // Clean up event listeners and intervals
        this.notifications.forEach(notification => notification.remove());
        this.closeChat();
        this.closeUploadModal();
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.modernUI = new ModernUI();
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.modernUI) {
        window.modernUI.destroy();
    }
});

// Add some CSS for background particles
const style = document.createElement('style');
style.textContent = `
    .background-particle {
        position: absolute;
        width: 2px;
        height: 2px;
        background: rgba(0, 212, 255, 0.1);
        border-radius: 50%;
        pointer-events: none;
        animation: float-particle linear infinite;
    }

    @keyframes float-particle {
        0% {
            transform: translateY(100vh) rotate(0deg);
            opacity: 0;
        }
        10% {
            opacity: 0.5;
        }
        90% {
            opacity: 0.5;
        }
        100% {
            transform: translateY(-100px) rotate(360deg);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// Authentication Form Functions
ModernUI.prototype.setupAuthForms = function() {
    // Password toggle functionality
    const passwordToggles = document.querySelectorAll('.password-toggle');
    passwordToggles.forEach(toggle => {
        toggle.addEventListener('click', (e) => {
            const input = toggle.previousElementSibling;
            const icon = toggle.querySelector('i');
            
            if (input.type === 'password') {
                input.type = 'text';
                icon.classList.remove('fa-eye');
                icon.classList.add('fa-eye-slash');
            } else {
                input.type = 'password';
                icon.classList.remove('fa-eye-slash');
                icon.classList.add('fa-eye');
            }
        });
    });

    // Password strength indicator
    const passwordInput = document.getElementById('password-input');
    const strengthFill = document.getElementById('strength-fill');
    const strengthText = document.getElementById('strength-text');
    
    if (passwordInput && strengthFill && strengthText) {
        passwordInput.addEventListener('input', (e) => {
            const password = e.target.value;
            const strength = this.calculatePasswordStrength(password);
            
            // Update strength bar
            strengthFill.className = 'strength-fill ' + strength.level;
            
            // Update strength text
            strengthText.className = 'strength-text ' + strength.level;
            strengthText.textContent = strength.text;
        });
    }

    // Form validation
    const authForms = document.querySelectorAll('.auth-form');
    authForms.forEach(form => {
        form.addEventListener('submit', (e) => {
            const submitBtn = form.querySelector('button[type="submit"]');
            
            // Add loading state
            submitBtn.classList.add('loading');
            submitBtn.disabled = true;
            
            // Simulate form submission (remove this in production)
            setTimeout(() => {
                submitBtn.classList.remove('loading');
                submitBtn.disabled = false;
            }, 2000);
        });
    });

    // Input validation feedback
    const inputs = document.querySelectorAll('.form-input');
    inputs.forEach(input => {
        input.addEventListener('blur', () => {
            this.validateInput(input);
        });
        
        input.addEventListener('input', () => {
            if (input.classList.contains('invalid')) {
                this.validateInput(input);
            }
        });
    });

    // Social login buttons
    const socialButtons = document.querySelectorAll('.btn-social');
    socialButtons.forEach(button => {
        button.addEventListener('click', (e) => {
            e.preventDefault();
            const provider = button.classList.contains('btn-google') ? 'Google' : 'GitHub';
            
            // Show OAuth setup message
            this.showNotification(`${provider} OAuth is not configured yet. To enable ${provider} login:

1. Create an OAuth app on ${provider}
2. Get Client ID and Client Secret
3. Add to environment variables:
   - ${provider.toUpperCase()}_CLIENT_ID
   - ${provider.toUpperCase()}_CLIENT_SECRET
4. Restart the Flask app

Check OAUTH_SETUP.md for detailed instructions!`, 'warning', 10000);
            
            // Add visual feedback
            button.style.opacity = '0.7';
            setTimeout(() => {
                button.style.opacity = '1';
            }, 200);
        });
    });
};

ModernUI.prototype.calculatePasswordStrength = function(password) {
    let score = 0;
    let level = 'weak';
    let text = 'Weak password';
    
    if (password.length >= 8) score++;
    if (password.length >= 12) score++;
    if (/[a-z]/.test(password) && /[A-Z]/.test(password)) score++;
    if (/\d/.test(password)) score++;
    if (/[^a-zA-Z\d]/.test(password)) score++;
    
    if (score <= 2) {
        level = 'weak';
        text = 'Weak password';
    } else if (score <= 4) {
        level = 'medium';
        text = 'Medium strength';
    } else {
        level = 'strong';
        text = 'Strong password';
    }
    
    return { level, text, score };
};

ModernUI.prototype.validateInput = function(input) {
    const isValid = input.checkValidity();
    const wrapper = input.closest('.input-wrapper');
    const icon = wrapper.querySelector('.input-icon');
    
    if (isValid) {
        input.classList.remove('invalid');
        input.classList.add('valid');
        if (icon) icon.classList.add('show');
    } else {
        input.classList.remove('valid');
        input.classList.add('invalid');
        if (icon) icon.classList.remove('show');
    }
};
