import openai
from app.rag_engine import CompanyRAG, NavigationRAG
from app.model_manager import ModelManager

# Initialize model manager for dynamic model selection
model_manager = ModelManager()
MAX_CONTEXT_MESSAGES = 15

system_instructions = (
    "You are Aarvasa's AI assistant. Your main focus is to assist with real estate-related questions and company-specific information. "
    "For anything not related to real estate or Aarvasa, politely let the user know that you can only help with real estate or company matters. "
    "Do not answer questions outside of this scope (e.g., coding, general knowledge). "
    "If a question is unrelated, reply with: 'Sorry, I can only assist with real estate and Aarvasa-related topics.' "
    "Use the company context file to answer questions when possible. "
    "Keep responses concise and under 3 lines for company-related inquiries. "
    "For property listings, always direct users to the listings page."
)

class MCPOrchestrator:
    def __init__(self, company_rag: CompanyRAG, nav_rag: NavigationRAG):
        self.company_rag = company_rag
        self.nav_rag = nav_rag

    def route(self, user_message, history=None):
        """Handles normal (non-streaming) responses."""
        # Company-related query
        if self._is_company_query(user_message):
            response = self._handle_company_info(user_message, history)
            if response:
                return response

        # Navigation-related query
        if self._is_navigation_query(user_message):
            nav_response = self._handle_navigation(user_message)
            if nav_response:
                return nav_response

        # Fallback to company context again
        response = self._handle_company_info(user_message, history)
        if response:
            return response

        # Final fallback
        return "Hey! I'm Aarvasa's assistant. Let me know how I can help with your company-related or website-related queries. 😊"

    def route_stream(self, user_message, history=None):
        """Handles streaming responses using OpenAI's streaming API."""
        # Determine type of question
        if self._is_navigation_query(user_message):
            nav_response = self._handle_navigation(user_message)
            if nav_response:
                yield nav_response
                return

        context = self.company_rag.retrieve_relevant_chunks(user_message)
        if not context.strip():
            yield "Hey! I couldn’t find relevant company info. Let me know how else I can help. 😊"
            return

        messages = [{"role": "system", "content": f"{system_instructions}\n\n{context}"}]

        if history and isinstance(history, list):
            trimmed = history[-MAX_CONTEXT_MESSAGES:]
            for user_msg, bot_msg in trimmed:
                messages.append({"role": "user", "content": user_msg})
                messages.append({"role": "assistant", "content": bot_msg})

        messages.append({"role": "user", "content": user_message})

        # Get best available model dynamically
        current_model = model_manager.get_best_model()
        available_models = model_manager.get_available_models()

        # Try streaming with fallback logic
        for attempt, model_to_use in enumerate(available_models):
            try:
                stream = openai.ChatCompletion.create(
                    model=model_to_use,
                    messages=messages,
                    temperature=0.5,
                    stream=True
                )

                for chunk in stream:
                    if "choices" in chunk and chunk.choices[0].delta.get("content"):
                        yield chunk.choices[0].delta.content
                
                return  # Successfully completed, exit

            except Exception as e:
                error_msg = str(e).lower()
                if ("model" in error_msg or "not found" in error_msg) and attempt < len(available_models) - 1:
                    print(f"⚠️ Model {model_to_use} failed in streaming, trying next model...")
                    model_manager.clear_cache()  # Clear cache to get fresh models
                    continue
                else:
                    yield f"\n[Error] {str(e)}"
                    return

    def _handle_company_info(self, message, history):
        context = self.company_rag.retrieve_relevant_chunks(message)
        if not context.strip():
            return None

        messages = [{"role": "system", "content": f"{system_instructions}\n\n{context}"}]

        if history and isinstance(history, list):
            trimmed = history[-MAX_CONTEXT_MESSAGES:]
            for user_msg, bot_msg in trimmed:
                messages.append({"role": "user", "content": user_msg})
                messages.append({"role": "assistant", "content": bot_msg})

        messages.append({"role": "user", "content": message})

        # Get best available model dynamically
        current_model = model_manager.get_best_model()
        available_models = model_manager.get_available_models()
        
        # Try with fallback logic
        for attempt, model_to_use in enumerate(available_models):
            try:
                response = openai.ChatCompletion.create(
                    model=model_to_use,
                    messages=messages,
                    temperature=0.5,
                )
                return response.choices[0].message["content"].strip()
                
            except Exception as e:
                error_msg = str(e).lower()
                if ("model" in error_msg or "not found" in error_msg) and attempt < len(available_models) - 1:
                    print(f"⚠️ Model {model_to_use} failed, trying next model...")
                    model_manager.clear_cache()  # Clear cache to get fresh models
                    continue
                else:
                    raise e
        
        return None

    def _handle_navigation(self, message):
        nav_result = self.nav_rag.retrieve_navigation_info(message, top_k=1)
        if nav_result:
            match = nav_result[0]
            return f"{match['description']} 👉 [Go to {match['name']} Page]({match['path']})"
        return None

    def _is_company_query(self, msg):
        keywords = [
            "aarvasa", "founder", "startup", "mission", "vision",
            "services", "ai", "blockchain", "real estate", "team",
            "values", "goal", "company"
        ]
        return any(word in msg.lower() for word in keywords)

    def _is_navigation_query(self, msg):
        keywords = [
            "where", "navigate", "page", "link", "reset", "forgot",
            "sign in", "sign up", "login", "logout", "agent", "contact",
            "listings", "search", "how do I", "find"
        ]
        return any(word in msg.lower() for word in keywords)
