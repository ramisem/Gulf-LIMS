import json
import uuid
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

PENDING = {}

@csrf_exempt
def start_scan(request):
    """
    Browser → Django → Agent (via WebSocket)
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=400)

    payload = json.loads(request.body.decode("utf-8")) if request.body else {}
    agent_id = payload.get("agent_id", "agent1")

    # Unique tracking ID
    request_id = str(uuid.uuid4())
    PENDING[request_id] = {"status": "pending"}

    # Send WebSocket event to agent group
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"agent_{agent_id}",                         # FIXED
        {
            "type": "start_scan",                   # FIXED
            "request_id": request_id
        }
    )

    return JsonResponse({"status": "scan_requested", "request_id": request_id})


@csrf_exempt
def upload_scan(request):
    """
    Agent → upload scanned PNG → notify admin via WS
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=400)

    request_id = request.POST.get("request_id")
    if not request_id:
        return JsonResponse({"error": "request_id missing"}, status=400)

    if "file" not in request.FILES:
        return JsonResponse({"error": "no file uploaded"}, status=400)

    file = request.FILES["file"]

    # Save to /media/scans/{uuid}.png
    save_path = default_storage.save(
        f"scans/{request_id}.png",
        ContentFile(file.read())
    )
    file_url = default_storage.url(save_path)

    PENDING[request_id] = {"status": "done", "file_url": file_url}

    # Notify admin browser group
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "notify_admin",                                # FIXED
        {
            "type": "scan_completed",                  # FIXED
            "request_id": request_id,
            "file_url": file_url
        }
    )

    return JsonResponse({"status": "uploaded", "file_url": file_url})
