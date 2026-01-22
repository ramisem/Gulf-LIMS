import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.layers import get_channel_layer


class AgentConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.agent_id = self.scope["url_route"]["kwargs"]["agent_id"]
        self.group_name = f"agent_{self.agent_id}"   # FIXED

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        await self.send(json.dumps({
            "type": "connected",
            "agent_id": self.agent_id
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    # Django instructs agent to begin scanning
    async def start_scan(self, event):
        await self.send(json.dumps({
            "action": "start_scan",
            "request_id": event["request_id"]
        }))

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return

        try:
            data = json.loads(text_data)
        except Exception:
            return

        channel_layer = get_channel_layer()

        # Agent -> Server : Scan Completed
        if data.get("type") == "scan_complete":
            await channel_layer.group_send(
                "notify_admin",           # FIXED
                {
                    "type": "scan_completed",   # FIXED
                    "request_id": data["request_id"],
                    "file_url": data["file_url"],
                }
            )

        # Agent -> Server : Scan Error
        elif data.get("type") == "scan_error":
            await channel_layer.group_send(
                "notify_admin",
                {
                    "type": "scan_completed",
                    "request_id": data["request_id"],
                    "file_url": None,
                    "error": data.get("error"),
                }
            )


class NotifyConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.client_id = self.scope["url_route"]["kwargs"]["client_id"]
        self.group_name = "notify_admin"   # FIXED — single admin group

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    # Django -> Admin browser client
    async def scan_completed(self, event):   # FIXED: matches event type above
        await self.send(json.dumps({
            "action": "scan_completed",
            "request_id": event["request_id"],
            "file_url": event["file_url"],
            "error": event.get("error")
        }))
