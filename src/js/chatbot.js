/**
 * UTS Handbook Chatbot Widget
 * A foldable chat popup that appears in the bottom right corner
 * Ready for backend integration
 */

// Chatbot state
let isOpen = false;
let messageHistory = [];
let currentCourseCode = null;  // Optional: filter by course code
let currentCourseName = null;  // Optional: filter by course name

/**
 * Fetch available courses from backend and populate dropdown (optional)
 */
async function loadAvailableCourses() {
    try {
        // Get API endpoint base URL
        const apiEndpoint = getApiEndpoint();
        const baseUrl = apiEndpoint.replace('/api/chatbot/chat/', '');
        const coursesUrl = `${baseUrl}/api/chatbot/courses/`;
        
        console.log('📡 Fetching available courses from:', coursesUrl);
        
        const response = await fetch(coursesUrl);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.success && data.courses && data.courses.length > 0) {
            console.log('✅ Available courses:', data.courses.length);
            
            // Optional: Populate a course selector if you add one to the UI
            // For now, we'll just log the courses
            return data.courses;
        } else {
            console.warn('⚠️ No courses returned from backend');
            return [];
        }
    } catch (error) {
        console.error('❌ Error loading courses:', error);
        return [];
    }
}

// Load message history from localStorage on initialization
function loadMessageHistory() {
    try {
        const saved = localStorage.getItem('chatbot_history');
        if (saved) {
            messageHistory = JSON.parse(saved);
            // Restore messages in the UI
            restoreMessages();
        }
    } catch (e) {
        console.error('Error loading message history:', e);
        messageHistory = [];
    }
}

// Save message history to localStorage
function saveMessageHistory() {
    try {
        localStorage.setItem('chatbot_history', JSON.stringify(messageHistory));
    } catch (e) {
        console.error('Error saving message history:', e);
    }
}

// Restore messages from history to the UI
function restoreMessages() {
    const messagesContainer = document.getElementById('chatbot-messages');
    // Clear existing messages (except welcome message if it's the only one)
    const existingMessages = messagesContainer.querySelectorAll('.chatbot-message');
    if (existingMessages.length === 1 && messageHistory.length > 0) {
        // Remove the welcome message if we have saved history
        existingMessages[0].remove();
    } else if (existingMessages.length > 1) {
        existingMessages.forEach(msg => msg.remove());
    }
    
    // Restore all messages from history
    messageHistory.forEach(msg => {
        addMessageToUI(msg.text, msg.type, false); // false = don't save to history again
    });
}

// DOM elements
const chatbotContainer = document.getElementById('chatbot-container');
const chatbotButton = document.getElementById('chatbot-button');
const chatbotWindow = document.getElementById('chatbot-window');
const chatbotMessages = document.getElementById('chatbot-messages');
const chatbotForm = document.getElementById('chatbot-form');
const chatbotInput = document.getElementById('chatbot-input');
const chatbotLoading = document.getElementById('chatbot-loading');

/**
 * Minimize chat window (show button, hide window)
 */
function minimizeChat() {
    isOpen = false;
    chatbotWindow.classList.add('hidden');
    chatbotButton.classList.remove('hidden');
}

/**
 * Close chat window and clear conversation memory
 */
function closeChat() {
    isOpen = false;
    chatbotWindow.classList.add('hidden');
    chatbotButton.classList.remove('hidden');
    // Clear conversation memory when closing
    clearConversationMemory();
}

/**
 * Toggle chat window open/closed
 */
function toggleChat() {
    isOpen = !isOpen;
    
    if (isOpen) {
        chatbotButton.classList.add('hidden');
        chatbotWindow.classList.remove('hidden');
        chatbotInput.focus();
    } else {
        minimizeChat();
    }
}

/**
 * Clear conversation (UI and memory)
 */
function clearConversation() {
    // Clear memory first
    clearConversationMemory();
    
    // Clear UI and show welcome message
    const messagesContainer = document.getElementById('chatbot-messages');
    messagesContainer.innerHTML = '<div class="chatbot-message chatbot-message-bot"><div class="chatbot-message-content"><p>Hello! I\'m your UTS Handbook assistant. Ask me about courses, admission requirements, career options, and more!</p></div></div>';
    
    // Don't show confirmation message - just clear silently
}

/**
 * Clear conversation memory (localStorage and state)
 */
function clearConversationMemory() {
    messageHistory = [];
    localStorage.removeItem('chatbot_history');
    
    // Keep only welcome message
    const welcomeText = "Hello! I'm your UTS Handbook assistant. Ask me about courses, admission requirements, career options, and more!";
    messageHistory.push({
        text: welcomeText,
        type: 'bot',
        timestamp: new Date()
    });
    saveMessageHistory();
}

/**
 * Set course filter (optional)
 */
function setCourseFilter(courseCode, courseName) {
    currentCourseCode = courseCode;
    currentCourseName = courseName;
    console.log('✅ Course filter set:', { courseCode, courseName });
}

/**
 * Clear course filter
 */
function clearCourseFilter() {
    currentCourseCode = null;
    currentCourseName = null;
    console.log('✅ Course filter cleared');
}

/**
 * Add a message to the UI (internal function)
 * @param {string} text - Message text
 * @param {string} type - 'user' or 'bot'
 * @param {boolean} saveToHistory - Whether to save to history (default: true)
 */
function addMessageToUI(text, type = 'bot', saveToHistory = true) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `chatbot-message chatbot-message-${type}`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'chatbot-message-content';
    
    const p = document.createElement('p');
    p.textContent = text;
    
    contentDiv.appendChild(p);
    messageDiv.appendChild(contentDiv);
    chatbotMessages.appendChild(messageDiv);
    
    // Scroll to bottom
    chatbotMessages.scrollTop = chatbotMessages.scrollHeight;
    
    // Store in history if requested
    if (saveToHistory) {
        messageHistory.push({ text, type, timestamp: new Date() });
        saveMessageHistory(); // Persist to localStorage
    }
}

/**
 * Add a message to the chat (public API)
 * @param {string} text - Message text
 * @param {string} type - 'user' or 'bot'
 */
function addMessage(text, type = 'bot') {
    addMessageToUI(text, type, true);
}

/**
 * Show loading indicator
 */
function showLoading() {
    chatbotLoading.style.display = 'flex';
    chatbotMessages.scrollTop = chatbotMessages.scrollHeight;
}

/**
 * Hide loading indicator
 */
function hideLoading() {
    chatbotLoading.style.display = 'none';
}

/**
 * Send message to backend
 * @param {string} message - User message
 */
async function sendToBackend(message) {
    // API endpoint configuration
    let API_ENDPOINT = localStorage.getItem('chatbot_api_endpoint');
    if (!API_ENDPOINT) {
        API_ENDPOINT = 'http://localhost:8000/api/chatbot/chat/';
    }
    
    // Configuration
    const USE_CONCISE = true;  // Set to false for longer, more detailed answers
    
    // Debug logging
    console.log('📤 Sending message');
    if (currentCourseCode) {
        console.log('📤 Course filter - Code:', currentCourseCode);
    }
    if (currentCourseName) {
        console.log('📤 Course filter - Name:', currentCourseName);
    }
    
    try {
        showLoading();
        
        const requestBody = {
            message: message,
            course_code: currentCourseCode || null,
            course_name: currentCourseName || null,
            concise: USE_CONCISE,
            use_preprocessing: true,  // Use the full preprocessing pipeline
            history: messageHistory.slice(-10) // Send last 10 messages for context (optional)
        };
        
        // Remove null values
        if (!requestBody.course_code) delete requestBody.course_code;
        if (!requestBody.course_name) delete requestBody.course_name;
        
        console.log('📤 Request body:', JSON.stringify(requestBody, null, 2));
        
        const response = await fetch(API_ENDPOINT, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestBody)
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ error: 'Unknown error' }));
            throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Handle response - the API returns { response: "...", success: true }
        if (data.success && data.response) {
            addMessage(data.response, 'bot');
        } else if (data.response) {
            // Fallback if success field is missing
            addMessage(data.response, 'bot');
        } else {
            throw new Error(data.error || 'No response received');
        }
        
        // Ensure messages are visible after adding response
        chatbotMessages.scrollTop = chatbotMessages.scrollHeight;
        
    } catch (error) {
        console.error('Error sending message:', error);
        console.error('Attempted endpoint:', API_ENDPOINT);
        
        // Show user-friendly error message with more details
        let errorMessage = 'Sorry, there was an error processing your request. ';
        
        if (error.message.includes('fetch') || error.message.includes('Failed to fetch') || error.name === 'TypeError' || error.message.includes('NetworkError')) {
            errorMessage += `Could not connect to the server at ${API_ENDPOINT}.\n\n`;
            errorMessage += 'This is likely a CORS (Cross-Origin) issue. Try:\n';
            errorMessage += '1. Make sure backend is running: curl http://localhost:8000/health\n';
            errorMessage += '2. Restart the backend server (to apply CORS changes)\n';
            errorMessage += '3. Try accessing frontend via http://localhost:8080 instead of http://0.0.0.0:8080\n';
            errorMessage += '4. Check browser console for CORS errors\n';
            errorMessage += `\nCurrent endpoint: ${API_ENDPOINT}`;
        } else {
            errorMessage += error.message || 'Please try again.';
        }
        
        addMessage(errorMessage, 'bot');
    } finally {
        hideLoading();
    }
}

/**
 * Handle form submission
 * @param {Event} event - Form submit event
 */
function sendMessage(event) {
    event.preventDefault();
    
    const message = chatbotInput.value.trim();
    
    if (!message) {
        return;
    }
    
    // Add user message to chat
    addMessage(message, 'user');
    
    // Clear input
    chatbotInput.value = '';
    
    // Send to backend
    sendToBackend(message);
}

// Initialize chatbot
document.addEventListener('DOMContentLoaded', function() {
    // Load saved message history
    loadMessageHistory();
    
    // Load available courses from backend (optional - for future course selector)
    loadAvailableCourses();
    
    // Start with chat window closed
    chatbotWindow.classList.add('hidden');
    
    // Add welcome message if history is empty
    if (messageHistory.length === 0) {
        const welcomeText = "Hello! I'm your UTS Handbook assistant. Ask me about courses, admission requirements, career options, and more!";
        messageHistory.push({
            text: welcomeText,
            type: 'bot',
            timestamp: new Date()
        });
        saveMessageHistory();
        // The welcome message is already in HTML, so we don't need to add it again
    } else {
        // If we have saved history, restore all messages including welcome
        restoreMessages();
    }
    
    // Focus input when chat opens
    chatbotButton.addEventListener('click', function() {
        setTimeout(() => chatbotInput.focus(), 100);
    });
    
    // Handle Enter key in input
    chatbotInput.addEventListener('keydown', function(event) {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            // Use trusted event instead of creating new Event
            chatbotForm.requestSubmit();
        }
    });
});

// Helper functions for API endpoint
function setApiEndpoint(endpoint) {
    localStorage.setItem('chatbot_api_endpoint', endpoint);
    console.log('✅ API endpoint updated to:', endpoint);
    return endpoint;
}

function getApiEndpoint() {
    return localStorage.getItem('chatbot_api_endpoint') || 'http://localhost:8000/api/chatbot/chat/';
}

// Export functions for external use if needed
window.ChatbotWidget = {
    toggle: toggleChat,
    minimize: minimizeChat,
    sendMessage: sendToBackend,
    addMessage: addMessage,
    isOpen: () => isOpen,
    setApiEndpoint: setApiEndpoint,
    getApiEndpoint: getApiEndpoint,
    clearHistory: clearConversation,
    clearMemory: clearConversationMemory,
    setCourseFilter: setCourseFilter,
    clearCourseFilter: clearCourseFilter,
    getCourseCode: () => currentCourseCode,
    getCourseName: () => currentCourseName
};

// Also make functions globally available for easier access
window.setApiEndpoint = setApiEndpoint;
window.getApiEndpoint = getApiEndpoint;
