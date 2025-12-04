/* static/js/chatbot.js - Chatbot Functionality */

class Chatbot {
    constructor(options) {
        this.conversationId = options.conversationId;
        this.errorCode = options.errorCode;
        this.chatEndpoint = options.chatEndpoint;
        this.supportEndpoint = options.supportEndpoint;
        
        this.messageContainer = document.getElementById('chatMessages');
        this.messageInput = document.getElementById('messageInput');
        this.chatForm = document.getElementById('chatForm');
        this.sendButton = document.getElementById('sendButton');
        this.typingIndicator = document.getElementById('typingIndicator');
        
        this.isWaitingForResponse = false;
        this.messageHistory = [];
        
        this.init();
    }
    
    init() {
        // Bind events
        this.chatForm.addEventListener('submit', (e) => this.handleFormSubmit(e));
        this.messageInput.addEventListener('keypress', (e) => this.handleKeyPress(e));
        this.messageInput.addEventListener('input', () => this.handleInput());
        
        // Focus on input
        this.messageInput.focus();
        
        // Scroll to bottom
        this.scrollToBottom();
        
        console.log('Chatbot initialized');
    }
    
    handleFormSubmit(e) {
        e.preventDefault();
        const message = this.messageInput.value.trim();
        if (message && !this.isWaitingForResponse) {
            this.sendMessage(message);
        }
    }
    
    handleKeyPress(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            this.handleFormSubmit(e);
        }
    }
    
    handleInput() {
        // Enable/disable send button based on input
        const hasText = this.messageInput.value.trim().length > 0;
        this.sendButton.disabled = !hasText || this.isWaitingForResponse;
    }
    
    sendMessage(message) {
        if (this.isWaitingForResponse) return;
        
        // Add user message to UI
        this.addMessageToUI(message, 'user');
        
        // Clear input
        this.messageInput.value = '';
        this.sendButton.disabled = true;
        
        // Set waiting state
        this.isWaitingForResponse = true;
        this.showTypingIndicator();
        
        // Send to server
        this.sendToServer(message);
    }
    
    sendToServer(message) {
        $.ajax({
            url: this.chatEndpoint,
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                conversation_id: this.conversationId,
                message: message
            }),
            success: (response) => this.handleServerResponse(response),
            error: (xhr, status, error) => this.handleServerError(xhr, status, error)
        });
    }
    
    handleServerResponse(response) {
        this.hideTypingIndicator();
        this.isWaitingForResponse = false;
        this.sendButton.disabled = false;
        
        // Add AI response to UI
        this.addMessageToUI(response.response, 'assistant');
        
        // Handle escalation if needed
        if (response.escalate) {
            setTimeout(() => {
                this.handleEscalation(response.escalation_reason);
            }, 1000);
        }
        
        // Focus back on input
        this.messageInput.focus();
    }
    
    handleServerError(xhr, status, error) {
        this.hideTypingIndicator();
        this.isWaitingForResponse = false;
        this.sendButton.disabled = false;
        
        console.error('Chat error:', error);
        
        let errorMessage = 'Sorry, I\'m having trouble processing your message. Please try again.';
        if (xhr.status === 0) {
            errorMessage = 'Connection error. Please check your internet connection.';
        } else if (xhr.status === 500) {
            errorMessage = 'Server error occurred. Let me connect you with human support.';
            setTimeout(() => this.handleEscalation('server_error'), 1000);
        }
        
        this.addMessageToUI(errorMessage, 'assistant', true);
        this.messageInput.focus();
    }
    
    addMessageToUI(message, role, isError = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message-bubble ${role}-message mb-3 fade-in`;
        
        const timestamp = new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
        
        if (role === 'user') {
            messageDiv.innerHTML = `
                <div class="d-flex justify-content-end">
                    <div class="message-content" style="max-width: 70%;">
                        <div class="bg-primary text-white p-3 rounded">
                            <p class="mb-0">${this.escapeHtml(message)}</p>
                        </div>
                        <small class="text-muted mt-1 d-block text-end">${timestamp}</small>
                    </div>
                    <div class="avatar bg-secondary text-white rounded-circle ms-2 d-flex align-items-center justify-content-center" style="width: 32px; height: 32px; font-size: 14px;">
                        <i class="fas fa-user"></i>
                    </div>
                </div>
            `;
        } else {
            const bgClass = isError ? 'bg-danger text-white' : 'bg-light';
            const iconClass = isError ? 'fa-exclamation-triangle' : 'fa-robot';
            const avatarBg = isError ? 'bg-danger' : 'bg-primary';
            
            messageDiv.innerHTML = `
                <div class="d-flex align-items-start">
                    <div class="avatar ${avatarBg} text-white rounded-circle me-2 d-flex align-items-center justify-content-center" style="width: 32px; height: 32px; font-size: 14px;">
                        <i class="fas ${iconClass}"></i>
                    </div>
                    <div class="message-content">
                        <div class="${bgClass} p-3 rounded">
                            <p class="mb-0">${this.formatMessage(message)}</p>
                        </div>
                        <small class="text-muted mt-1 d-block">${timestamp}</small>
                    </div>
                </div>
            `;
        }
        
        this.messageContainer.appendChild(messageDiv);
        this.scrollToBottom();
        
        // Store in message history
        this.messageHistory.push({
            role: role,
            content: message,
            timestamp: new Date().toISOString(),
            isError: isError
        });
    }
    
    showTypingIndicator() {
        this.typingIndicator.style.display = 'block';
        this.scrollToBottom();
    }
    
    hideTypingIndicator() {
        this.typingIndicator.style.display = 'none';
    }
    
    scrollToBottom() {
        setTimeout(() => {
            this.messageContainer.scrollTop = this.messageContainer.scrollHeight;
        }, 100);
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    formatMessage(message) {
        // Convert line breaks to <br>
        let formatted = this.escapeHtml(message);
        formatted = formatted.replace(/\n/g, '<br>');
        
        // Make URLs clickable
        const urlRegex = /(https?:\/\/[^\s]+)/g;
        formatted = formatted.replace(urlRegex, '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>');
        
        return formatted;
    }
    
    handleEscalation(reason) {
        console.log('Escalating to support:', reason);
        
        // Show escalation modal
        const modal = new bootstrap.Modal(document.getElementById('escalationModal'));
        modal.show();
        
        // Add system message
        const escalationMessage = this.getEscalationMessage(reason);
        this.addMessageToUI(escalationMessage, 'assistant');
    }
    
    getEscalationMessage(reason) {
        const messages = {
            'ai_unavailable': 'I\'m currently unavailable. Let me connect you with human support who can help you better.',
            'complexity': 'This issue seems complex and requires human expertise. I\'ll connect you with our technical support team.',
            'user_request': 'I understand you\'d like to speak with human support. Let me set that up for you.',
            'solution_failed': 'Since the previous solutions didn\'t work, our human support team can provide more advanced troubleshooting.',
            'server_error': 'I\'m experiencing technical difficulties. Let me connect you with human support.',
            'unknown': 'Let me connect you with human support for further assistance.'
        };
        
        return messages[reason] || messages['unknown'];
    }
    
    exportConversation() {
        return {
            conversationId: this.conversationId,
            errorCode: this.errorCode,
            messages: this.messageHistory,
            timestamp: new Date().toISOString()
        };
    }
}

// Utility functions for chatbot
function sendQuickMessage(message) {
    if (window.chatbotInstance) {
        window.chatbotInstance.sendMessage(message);
    }
}

function clearChat() {
    if (confirm('Are you sure you want to clear the chat history?')) {
        const messagesContainer = document.getElementById('chatMessages');
        // Keep only the initial AI message
        const initialMessage = messagesContainer.querySelector('.ai-message');
        messagesContainer.innerHTML = '';
        if (initialMessage) {
            messagesContainer.appendChild(initialMessage.cloneNode(true));
        }
        
        if (window.chatbotInstance) {
            window.chatbotInstance.messageHistory = [];
        }
    }
}

function downloadChatHistory() {
    if (window.chatbotInstance) {
        const conversation = window.chatbotInstance.exportConversation();
        const dataStr = JSON.stringify(conversation, null, 2);
        const dataBlob = new Blob([dataStr], {type: 'application/json'});
        
        const link = document.createElement('a');
        link.href = URL.createObjectURL(dataBlob);
        link.download = `chat_history_${conversation.conversationId}.json`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
}

// Initialize chatbot when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // This will be called from the template script tag
    console.log('Chatbot script loaded');
});