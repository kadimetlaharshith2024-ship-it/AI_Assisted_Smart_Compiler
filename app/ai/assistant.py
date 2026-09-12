import os
import requests
from app.ai.prompts import AI_ERROR_EXPLANATION_PROMPT

class AIAssistant:
    def __init__(self):
        # Can read from environment variables if an API key is provided
        self.api_key = os.environ.get("OPENAI_API_KEY", "")
        self.api_url = "https://api.openai.com/v1/chat/completions"

    def explain_error(self, source_code: str, error_message: str) -> str:
        # Fallback if no API key is configured or offline during demo
        if not self.api_key:
            return (
                f"**AI Assistant Suggestion (Offline Mode):**\n\n"
                f"**Error Detected:** `{error_message}`\n\n"
                f"**Tip:** Check your variable declarations, types, or scopes around the error line in your Lumen code. "
                f"Make sure all variables are declared with `let` and match their expected types (`int`, `float`, `string`, `bool`, or arrays)[cite: 2]."
            )

        prompt = AI_ERROR_EXPLANATION_PROMPT.format(source_code=source_code, error_message=error_message)
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "gpt-3.5-turbo",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 300
            }
            response = requests.post(self.api_url, json=payload, headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"]
            else:
                return f"AI Service returned status code {response.status_code}. Please verify your API setup."
        except Exception as e:
            return f"Could not reach AI Assistant service due to network error: {str(e)}"