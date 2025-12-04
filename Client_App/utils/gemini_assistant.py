# utils/gemini_assistant.py - Gemini AI Integration (Updated for latest API)
import os
import json
import logging
from datetime import datetime
from config import Config

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    logging.error("Google GenAI library not installed. Please run: pip install google-genai")

class GeminiAssistant:
    def __init__(self):
        self.config = Config()
        self.client = None
        self.model = "gemini-2.0-flash"
        self.initialized = False
        
        if GENAI_AVAILABLE:
            try:
                self.client = genai.Client(
                    api_key=self.config.GEMINI_API_KEY
                )
                self.initialized = True
                logging.info("Gemini AI initialized successfully")
            except Exception as e:
                logging.error(f"Failed to initialize Gemini AI: {str(e)}")
                self.initialized = False
        else:
            logging.error("Google GenAI library not available")
    
    def get_response(self, user_message, error_code, conversation_history):
        """Get AI response from Gemini using the latest API"""
        try:
            if not self.initialized:
                return {
                    'content': "AI assistant is currently unavailable. Please contact support for assistance.",
                    'escalate': True,
                    'escalation_reason': 'ai_unavailable'
                }
            
            # Build conversation context
            context = self._build_context(error_code, conversation_history)
            
            # Create the complete prompt
            full_prompt = f"""
{context}

User message: {user_message}

Please respond as a helpful technical support assistant. If the user is having trouble with solution steps, provide detailed guidance. If the solution didn't work, ask clarifying questions and suggest alternatives. If the issue seems too complex or you cannot help further, recommend escalation to human support.

Response format should be conversational and helpful. If escalation is needed, end your response with [ESCALATE: reason].
"""
            
            # Prepare contents for the API
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=full_prompt),
                    ],
                ),
            ]
            
            # Optional: Add tools if needed (Google Search can be useful for technical issues)
            tools = [
                types.Tool(googleSearch=types.GoogleSearch()),
            ]
            
            # Generate content configuration
            generate_content_config = types.GenerateContentConfig(
                tools=tools,
                temperature=self.config.GEMINI_TEMPERATURE,
                max_output_tokens=self.config.GEMINI_MAX_TOKENS,
            )
            
            # Generate response
            response_text = ""
            for chunk in self.client.models.generate_content_stream(
                model=self.model,
                contents=contents,
                config=generate_content_config,
            ):
                if chunk.text:
                    response_text += chunk.text
            
            # Check if escalation is needed
            escalate = False
            escalation_reason = ''
            if '[ESCALATE:' in response_text:
                escalate = True
                escalation_reason = self._extract_escalation_reason(response_text)
                response_text = response_text.split('[ESCALATE:')[0].strip()
            
            logging.info(f"AI response generated for error {error_code}")
            
            return {
                'content': response_text,
                'escalate': escalate,
                'escalation_reason': escalation_reason
            }
            
        except Exception as e:
            logging.error(f"Error getting AI response: {str(e)}")
            return {
                'content': "I'm having trouble processing your request right now. Let me connect you with human support.",
                'escalate': True,
                'escalation_reason': 'ai_error'
            }
    
    def get_non_streaming_response(self, user_message, error_code, conversation_history):
        """Get AI response without streaming (alternative method)"""
        try:
            if not self.initialized:
                return {
                    'content': "AI assistant is currently unavailable. Please contact support for assistance.",
                    'escalate': True,
                    'escalation_reason': 'ai_unavailable'
                }
            
            # Build conversation context
            context = self._build_context(error_code, conversation_history)
            
            # Create the complete prompt
            full_prompt = f"""
{context}

User message: {user_message}

Please respond as a helpful technical support assistant. If the user is having trouble with solution steps, provide detailed guidance. If the solution didn't work, ask clarifying questions and suggest alternatives. If the issue seems too complex or you cannot help further, recommend escalation to human support.

Response format should be conversational and helpful. If escalation is needed, end your response with [ESCALATE: reason].
"""
            
            # Prepare contents for the API
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=full_prompt),
                    ],
                ),
            ]
            
            # Generate content configuration
            generate_content_config = types.GenerateContentConfig(
                temperature=self.config.GEMINI_TEMPERATURE,
                max_output_tokens=self.config.GEMINI_MAX_TOKENS,
            )
            
            # Generate response (non-streaming)
            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config=generate_content_config,
            )
            
            response_text = response.text if response.text else "I apologize, but I couldn't generate a response. Please try again or contact support."
            
            # Check if escalation is needed
            escalate = False
            escalation_reason = ''
            if '[ESCALATE:' in response_text:
                escalate = True
                escalation_reason = self._extract_escalation_reason(response_text)
                response_text = response_text.split('[ESCALATE:')[0].strip()
            
            logging.info(f"AI response generated for error {error_code}")
            
            return {
                'content': response_text,
                'escalate': escalate,
                'escalation_reason': escalation_reason
            }
            
        except Exception as e:
            logging.error(f"Error getting AI response: {str(e)}")
            return {
                'content': "I'm having trouble processing your request right now. Let me connect you with human support.",
                'escalate': True,
                'escalation_reason': 'ai_error'
            }
    
    def _build_context(self, error_code, conversation_history):
        """Build context for AI conversation"""
        context = f"""
You are a Windows technical support chatbot helping users with dump file errors.

Current Error: {error_code}

Previous conversation:
"""
        
        # Add conversation history (limit to last 10 messages for context window)
        for msg in conversation_history[-10:]:
            role = "User" if msg['role'] == 'user' else "Assistant"
            context += f"{role}: {msg['content']}\n"
        
        context += """
Guidelines:
1. Be helpful and patient
2. Provide step-by-step instructions when needed
3. Ask clarifying questions if solution didn't work
4. Escalate complex issues to human support
5. Use simple, non-technical language when possible
6. If you determine human support is needed, end your response with [ESCALATE: reason]

Common escalation reasons:
- complexity: Issue is too complex for automated assistance
- solution_failed: Multiple solutions have failed
- user_request: User explicitly requests human support
- hardware_issue: Physical hardware problems requiring hands-on assistance
- system_corruption: Severe system damage requiring advanced recovery
"""
        
        return context
    
    def _extract_escalation_reason(self, content):
        """Extract escalation reason from AI response"""
        try:
            escalate_marker = '[ESCALATE:'
            start = content.find(escalate_marker) + len(escalate_marker)
            end = content.find(']', start)
            if end == -1:
                return 'unknown'
            return content[start:end].strip()
        except Exception:
            return 'unknown'
    
    def generate_support_summary(self, conversation_history, error_code):
        """Generate summary for support ticket"""
        try:
            if not self.initialized:
                return "AI summary unavailable - please review conversation history manually"
            
            # Build conversation text
            conv_text = "\n".join([
                f"{msg['role']}: {msg['content']}" 
                for msg in conversation_history
            ])
            
            prompt = f"""
Summarize this technical support conversation for a human support agent:

Error Code: {error_code}

Conversation:
{conv_text}

Please provide a concise summary including:
1. The main issue
2. Solutions attempted
3. User's specific difficulties
4. Recommended next steps

Keep it professional and technical for support staff.
"""
            
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=prompt),
                    ],
                ),
            ]
            
            generate_content_config = types.GenerateContentConfig(
                temperature=0.3,  # Lower temperature for more focused summaries
                max_output_tokens=500,
            )
            
            # Generate summary
            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config=generate_content_config,
            )
            
            return response.text if response.text else "Error generating AI summary"
            
        except Exception as e:
            logging.error(f"Error generating support summary: {str(e)}")
            return f"Error generating AI summary: {str(e)}"
    
    def test_connection(self):
        """Test if the AI connection is working"""
        try:
            if not self.initialized:
                return False, "AI not initialized"
            
            # Simple test request
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text="Hello, please respond with 'AI connection test successful'"),
                    ],
                ),
            ]
            
            generate_content_config = types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=50,
            )
            
            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config=generate_content_config,
            )
            
            if response.text and "successful" in response.text.lower():
                return True, "AI connection test successful"
            else:
                return False, f"Unexpected response: {response.text}"
                
        except Exception as e:
            return False, f"Connection test failed: {str(e)}"