from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from eventmanagement.models import Event_Rule
from task.models import CustomPeriodicTask
from .serializers import EventRuleSerializer, CustomPeriodicTaskSerializer


class EventRuleCreate(GenericAPIView):
    serializer_class = EventRuleSerializer

    def post(self, request):
        serializer = EventRuleSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EventRuleUpdate(GenericAPIView):
    serializer_class = EventRuleSerializer

    def put(self, request, name):
        # Using get_object_or_404 to simplify object retrieval and 404 handling
        event_rule = get_object_or_404(Event_Rule, name=name)

        serializer = EventRuleSerializer(event_rule, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, name):
        return self.put(request, name)


class CustomPeriodicTaskUpdateAPIView(GenericAPIView):
    serializer_class = CustomPeriodicTaskSerializer

    def put(self, request, name):
        try:
            task = get_object_or_404(CustomPeriodicTask, name=name)
        except CustomPeriodicTask.DoesNotExist:
            return Response({'error': 'CustomPeriodicTask not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = CustomPeriodicTaskSerializer(task, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, name):
        return self.put(request, name)
