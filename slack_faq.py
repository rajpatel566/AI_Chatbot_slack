import os
import re
import json
import uvicorn
from fastapi import FastAPI, Request
from slack_bolt import App
from slack_bolt.adapter.fastapi import SlackRequestHandler
from llm_service import LLMService

app = FastAPI()

class SlackBot:
    LOADING_IMAGE_URL = "https://media4.giphy.com/media/ioCNNt0RJfICFLXaoD/giphy.gif?cid=6c09b952goxv5nm5pd4q5nb5onv1kpfc1un6qzfxhgb7rw98&ep=v1_internal_gif_by_id&rid=giphy.gif&ct=g"
    SLACK_BOT_TOKEN = "xoxb-..."
    SLACK_APP_TOKEN = "xapp-..."
    SLACK_SIGNING_SECRET = ""

    def __init__(self):
        self.app = App(token=self.SLACK_BOT_TOKEN ,signing_secret=self.SLACK_SIGNING_SECRET)
        response = self.app.client.auth_test()
        self.bot_user_id = response["user_id"]
        self.llm = LLMService()
        self.setup_event_listeners()

    def get_initial_prompts(self):
        base_prompt = "Generate engaging chatbot conversation starters."
        return self.llm.generate_prompts(base_prompt)

    def get_dynamic_follow_ups(self, ai_response_json):
        base_prompt = f"Based on this Slack Block Kit JSON response: ```{ai_response_json}```, suggest 3 meaningful follow-up questions as a plain list of text, with each question on a new line. Do not include any JSON formatting or markdown."
        llm_response = self.llm.generate_response(base_prompt)
        return [prompt.strip() for prompt in llm_response.strip().split('\n') if prompt.strip()]

    def format_for_slack(self, text):
        """Formats text for Slack."""
        return text.replace("**", "*").replace("__", "_").replace("\n- ", "\n• ").replace("\n1. ", "\n1️ ")

    def get_ai_response(self, prompt):
        """Generate AI response using generate_blockkit_body."""
        llm_prompt = f"Respond to the following user input in a helpful and engaging way using Slack Block Kit JSON format: '{prompt}'"
        ai_response_blocks = self.llm.generate_blockkit_body(llm_prompt)
        return json.dumps(ai_response_blocks)

    def get_follow_up_prompts(self, ai_response):
        base_prompt = f"Based on this response, suggest meaningful follow-up questions:\n\n{ai_response}"
        return self.llm.generate_prompts(base_prompt)

    def format_prompts(self, prompts_list, max_length=75):
        """Formats follow-up prompts to fit within a specified maximum length."""
        formatted_prompts = []
        for prompt in prompts_list:
            if len(prompt) <= max_length:
                formatted_prompts.append(prompt)
            else:
                words = prompt.split()
                truncated_prompt = ""
                for word in words:
                    if len(truncated_prompt) + len(word) + 1 <= max_length:
                        truncated_prompt += (" " if truncated_prompt else "") + word
                    else:
                        break
                formatted_prompts.append(truncated_prompt)
        return formatted_prompts

    def send_message_with_buttons(self, say, body_blocks, follow_up_prompts, thread_ts):
        """Send AI response with Like/Dislike buttons and follow-up prompts."""
        formatted_follow_ups = self.format_prompts(follow_up_prompts)
        follow_up_buttons = [
            {"type": "button", "text": {"type": "plain_text", "text": prompt[:75]}, "value": prompt, "action_id": f"follow_up_{index}_{thread_ts}"}
            for index, prompt in enumerate(formatted_follow_ups)
        ]

        feedback_buttons = [
            {"type": "button", "text": {"type": "plain_text", "text": "👍 Like"}, "style": "primary", "value": "like", "action_id": f"feedback_like_{thread_ts}"},
            {"type": "button", "text": {"type": "plain_text", "text": "👎 Dislike"}, "style": "danger", "value": "dislike", "action_id": f"feedback_dislike_{thread_ts}"}
        ]

        actions_block = []
        if feedback_buttons:
            actions_block.append({"type": "actions", "elements": feedback_buttons})
        if follow_up_buttons:
            actions_block.append({"type": "actions", "elements": follow_up_buttons})

        say(
            thread_ts=thread_ts,
            blocks=body_blocks + actions_block
        )

    def handle_message_events(self, body, say):
        """Handles messages and generates AI responses."""
        event = body["event"]
        user = event.get("user")
        text = event.get("text", "").strip()
        channel_id = event.get("channel")
        thread_ts = event.get("thread_ts", event["ts"])

        if user == self.bot_user_id:
            return

        if f"<@{self.bot_user_id}>" not in text and thread_ts == event["ts"]:
            return

        text = text.replace(f"<@{self.bot_user_id}>", "").strip()
        response_msg = say(thread_ts=thread_ts, blocks=[{"type": "image", "image_url": self.LOADING_IMAGE_URL,"alt_text": "Loading..."}])

        ai_response_json = self.get_ai_response(text)
        try:
            ai_response_blocks = json.loads(ai_response_json)
        except json.JSONDecodeError:
            ai_response_blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": "⚠️ Error processing AI response."}}]

        follow_up_prompts = self.get_dynamic_follow_ups(ai_response_json) # Removed json.loads() here
        self.send_message_with_buttons(say, ai_response_blocks, follow_up_prompts, thread_ts)
        self.app.client.chat_delete(channel=channel_id, ts=response_msg["ts"])

    async def handle_app_home_opened(self, event, client, logger):
        user_id = event["user"]
        try:
            await client.views_publish(
                user_id=user_id,
                view={
                    "type": "home",
                    "blocks": [
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"👋 Welcome to your AI assistant, <@{user_id}>!\nAsk me anything or try one of the suggested prompts below:"
                            }
                        },
                        {
                            "type": "image",
                            "image_url": "https://i.ytimg.com/vi/OF0FkzsDkVU/hqdefault.jpg",
                            "alt_text": "Welcome Video"
                        },
                        {
                            "type": "actions",
                            "elements": [
                                {
                                    "type": "button",
                                    "text": {"type": "plain_text", "text": "▶️ Watch Welcome Video"},
                                    "url": "https://www.youtube.com/watch?v=OF0FkzsDkVU",
                                    "action_id": "watch_welcome_video"
                                }
                            ]
                        },
                        {
                            "type": "actions",
                            "elements": [
                                {
                                    "type": "button",
                                    "text": {"type": "plain_text", "text": "Summarize a document"},
                                    "value": "Summarize a document",
                                    "action_id": "followup_home_1"
                                },
                                {
                                    "type": "button",
                                    "text": {"type": "plain_text", "text": "Answer FAQs"},
                                    "value": "Answer FAQs",
                                    "action_id": "followup_home_2"
                                }
                            ]
                        }
                    ]
                }
            )
        except Exception as e:
            logger.error(f"Error publishing App Home: {e}")

    def handle_assistant_thread_started(self,event, say):
        """Handles the assistant_thread_started event and sends dynamic initial prompts."""
        user_id = event.get('assistant_thread', {}).get('user_id')
        channel_id = event.get('assistant_thread', {}).get('channel_id')
        thread_ts = event.get('assistant_thread', {}).get('thread_ts')

        initial_prompts = self.get_initial_prompts()

        buttons = [
            {
                "type": "button",
                "text": {"type": "plain_text", "text": prompt[:75]},
                "value": prompt,
                "action_id": f"initial_prompt_{index}"
            }
            for index, prompt in enumerate(initial_prompts) if prompt.strip()
        ]

        if not buttons:
            buttons = [{
                "type": "button",
                "text": {"type": "plain_text", "text": "Start a conversation"},
                "value": "default",
                "action_id": "default_prompt"
            }]

        if user_id and channel_id and thread_ts:
            response_text = f"Hello <@{user_id}>, how can I assist you today? Choose a prompt to get started!"
            say(
                channel=channel_id,
                thread_ts=thread_ts,
                text=response_text,
                blocks=[
                    {"type": "section", "text": {"type": "mrkdwn", "text": response_text}},
                    {"type": "section", "text": {"type": "mrkdwn", "text": "*Choose a prompt below to get started:*"}},
                    {"type": "actions", "elements": buttons}
                ]
            )

    def handle_feedback(self, ack, body, say):
        """Handles feedback from users."""
        ack()

        user_id = body["user"]["id"]
        channel_id = body["channel"]["id"]
        thread_ts = body["message"]["ts"]
        feedback = body["actions"][0]["value"]

        say(text=f"✅ *Feedback received:* {feedback.capitalize()}", thread_ts=thread_ts)

    def handle_follow_up_click(self,ack, body, say):
        """Handles follow-up button clicks."""
        ack()
        selected_prompt = body["actions"][0]["value"]
        user_id = body["user"]["id"]
        channel_id = body["channel"]["id"]
        thread_ts = body["message"]["ts"]

        user_message = self.app.client.chat_postMessage(channel=channel_id, text=selected_prompt, thread_ts=thread_ts, as_user=True)
        new_thread_ts = user_message["ts"]

        response_msg = self.app.client.chat_postMessage(channel=channel_id, thread_ts=new_thread_ts, text="Generating...", blocks=[{"type": "image", "image_url": self.LOADING_IMAGE_URL, "alt_text": "Generating..."}])

        ai_response_json = self.get_ai_response(selected_prompt)
        try:
            ai_response_blocks = json.loads(ai_response_json)
        except json.JSONDecodeError:
            ai_response_blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": "⚠️ Error processing AI response."}}]

        follow_up_prompts_json = self.get_dynamic_follow_ups(ai_response_json)
        self.send_message_with_buttons(say, ai_response_blocks, follow_up_prompts_json, new_thread_ts)

        self.app.client.chat_delete(channel=channel_id, ts=response_msg["ts"])

    def handle_initial_prompt_click(self,ack, body, say):
        """Handles initial prompt selection."""
        ack()
        selected_prompt = body["actions"][0]["value"]
        user_id = body["user"]["id"]
        channel_id = body["channel"]["id"]
        thread_ts = body["message"]["ts"]

        user_msg = self.app.client.chat_postMessage(channel=channel_id, text=f"*{selected_prompt}*", thread_ts=thread_ts, username="User")

        response_msg = say(thread_ts=thread_ts, blocks=[{"type": "image", "image_url": self.LOADING_IMAGE_URL, "alt_text": "Loading..."}])

        ai_response_json = self.get_ai_response(selected_prompt) # Use selected_prompt to get AI response
        try:
            ai_response_blocks = json.loads(ai_response_json)
        except json.JSONDecodeError:
            ai_response_blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": "⚠️ Error processing AI response."}}]

        follow_up_prompts_json = self.get_dynamic_follow_ups(ai_response_json)
        self.send_message_with_buttons(say, ai_response_blocks, follow_up_prompts_json, user_msg["ts"]) # Use user_msg["ts"] for the new thread

        self.app.client.chat_delete(channel=channel_id, ts=response_msg["ts"])

    def setup_event_listeners(self):
        """Setup Slack event listeners."""
        self.app.event("message")(self.handle_message_events)
        self.app.event("app_home")(self.handle_app_home_opened)
        self.app.event("assistant_thread_started")(self.handle_assistant_thread_started)
        self.app.action(re.compile(r"initial_prompt_\d+"))(self.handle_initial_prompt_click)
        self.app.action(re.compile(r"follow_up_.*"))(self.handle_follow_up_click)
        self.app.action(re.compile(r"feedback_like_.*"))(self.handle_feedback)
        self.app.action(re.compile(r"feedback_dislike_.*"))(self.handle_feedback)

bot = SlackBot()
slack_handler = SlackRequestHandler(bot.app)

@app.post("/slack/events")
async def slack_events(request: Request):
    return await slack_handler.handle(request)

if __name__ == "__main__":
    uvicorn.run("slack_faq:app", host="0.0.0.0", port=3000, reload=True)
