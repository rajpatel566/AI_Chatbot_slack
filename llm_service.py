import os
import json
from google import genai

class LLMService:
    """Handles LLM interactions with Google Gemini API."""

    def __init__(self):
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = "gemini-2.0-flash"

    def generate_response(self, prompt):
        """Generates an AI response while ensuring it's under 3000 characters."""
        try:
            response = self.client.models.generate_content(model=self.model, contents=prompt)
            if response and response.candidates:
                for candidate in response.candidates:
                    if candidate.content and candidate.content.parts:
                        ai_text = candidate.content.parts[0].text.strip()
                        return ai_text
            return "⚠️ AI Response is empty."
        except Exception as e:
            print(f"⚠️ LLM Error: {e}")
            return "⚠️ Error processing your request."

    def generate_prompts(self, base_prompt, num_prompts=3):
        """Generic function to generate initial or follow-up prompts."""
        prompt = f"{base_prompt} Generate {num_prompts} prompts. Only return the prompts, nothing else."
        try:
            response = self.generate_response(prompt)
            return [q.strip() for q in response.split("\n") if q.strip()]
        except Exception as e:
            print(f"⚠️ Error generating prompts: {e}")
            return []

    def generate_blockkit_body(self, user_query):
        """
        Uses the LLM to generate only the Block Kit body as a JSON array of blocks.
        This excludes footer (like/dislike buttons and followups).
        """
        prompt = f"""
You are a Slack bot that creates JSON for Slack Block Kit messages.

Based on the user message: "{user_query}", return only a valid JSON array of Slack Block Kit blocks.
Use markdown formatting in 'section' blocks. You can include 'section', 'context', 'image' blocks as needed.
Do not include any buttons, footers, feedback, or follow-up elements.

Only return a valid JSON list. Do not include any explanation or extra text.
"""
        try:
            raw_json = self.generate_response(prompt)
            print(f"⚠️ Raw LLM Response for Block Kit Body: '{raw_json}'") # Keep this for debugging

            # Remove Markdown code blocks if present
            raw_json = raw_json.strip()
            if raw_json.startswith("```json"):
                raw_json = raw_json[len("```json"):].strip()
            if raw_json.endswith("```"):
                raw_json = raw_json[:-len("```")].strip()

            return json.loads(raw_json)
        except json.JSONDecodeError as e:
            print(f"⚠️ Error decoding LLM response as JSON in generate_blockkit_body: {e} - Raw: '{raw_json}'")
            return [{
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"⚠️ Unable to generate response layout: {e}"
                }
            }]
        except Exception as e:
            print(f"⚠️ Error generating blockkit body: {e}")
            return [{
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "⚠️ Unable to generate response layout."
                }
            }]


# import os
# from google import genai
# import json

# class LLMService:
#     """Handles LLM interactions with Google Gemini API."""

#     def __init__(self):
#         self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
#         self.model = "gemini-2.0-flash" # Or any other suitable Gemini model

#     def generate_response(self, prompt):
#         """Generates an AI response."""
#         try:
#             response = self.client.models.generate_content(model=self.model, contents=prompt)
#             if response and response.candidates:
#                 for candidate in response.candidates:
#                     if candidate.content and candidate.content.parts:
#                         ai_text = candidate.content.parts[0].text.strip()
#                         return ai_text
#             return "⚠️ AI Response is empty."
#         except Exception as e:
#             print(f"⚠️ LLM Error: {e}")
#             return "⚠️ Error processing your request."

#     def generate_prompts(self, base_prompt, num_prompts=3):
#         """Generic function to generate initial or follow-up prompts as a JSON list."""
#         prompt = f"{base_prompt} Generate {num_prompts} concise prompts specifically for Slack as a JSON list of strings. Only return the JSON, nothing else."
#         try:
#             response = self.generate_response(prompt)
#             try:
#                 prompts_list = json.loads(response)
#                 if isinstance(prompts_list, list) and all(isinstance(p, str) for p in prompts_list):
#                     return json.dumps(prompts_list)
#                 else:
#                     print(f"⚠️ LLM did not return a JSON list of strings for prompts: {response}")
#                     return json.dumps([])
#             except json.JSONDecodeError:
#                 print(f"⚠️ Error decoding LLM response as JSON for prompts: {response}")
#                 return json.dumps([])
#         except Exception as e:
#             print(f"⚠️ Error generating prompts: {e}")
#             return json.dumps([])

# # Example of a function to generate Block Kit JSON directly
#     def generate_block_kit_json(self, prompt):
#         """Generates AI response directly as a JSON string for Slack Block Kit."""
#         block_kit_prompt = f"You are a helpful assistant designed to respond in Slack Block Kit JSON format as a list of block objects to the following user query: {prompt}. Ensure the JSON is valid and includes at least one 'section' block with your answer. Do not include any action blocks for feedback or follow-ups."
#         try:
#             response_text = self.generate_response(block_kit_prompt)
#             try:
#                 blocks = json.loads(response_text)
#                 if isinstance(blocks, list):
#                     return json.dumps(blocks)
#                 else:
#                     print(f"⚠️ LLM did not return a JSON list of blocks: {response_text}")
#                     return json.dumps([{"type": "section", "text": {"type": "mrkdwn", "text": "⚠️ There was an issue generating the response."}}])
#             except json.JSONDecodeError:
#                 print(f"⚠️ Error decoding LLM response as JSON for Block Kit: {response_text}")
#                 return json.dumps([{"type": "section", "text": {"type": "mrkdwn", "text": "⚠️ There was an issue with the AI's response format."}}])
#         except Exception as e:
#             print(f"⚠️ LLM Error during Block Kit generation: {e}")
#             return json.dumps([{"type": "section", "text": {"type": "mrkdwn", "text": "⚠️ Error processing your request."}}])