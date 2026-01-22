import json
from datetime import datetime

from django.core.exceptions import ObjectDoesNotExist
from django_celery_beat.models import IntervalSchedule, CrontabSchedule
from rest_framework import serializers

from apidetails.models import APIDetail
from core.models import IOT_Type, IOT_Device
from eventmanagement.models import Event_Rule, Event_Rule_Params, Event_Rule_IOT_Device
from iotlimsintegrator import settings
from masterdata.models import Event_Type, Event_Type_IOT_Type_Map, Unit, Param
from task.models import CustomPeriodicTask
from userauthentication.models import User


class EventRuleParamsSerializer(serializers.ModelSerializer):
    unit_name = serializers.SlugRelatedField(
        slug_field='unit_name',
        queryset=Unit.objects.all(),
        required=False,
        allow_null=True
    )

    param_id = serializers.SlugRelatedField(
        slug_field='param_name',
        queryset=Param.objects.all(),
        required=True,
        allow_null=False
    )

    class Meta:
        model = Event_Rule_Params
        exclude = ('event_rule_id',)


class EventRuleIOTDeviceSerializer(serializers.ModelSerializer):
    device_id = serializers.SlugRelatedField(
        slug_field='uuid',
        queryset=IOT_Device.objects.all(),
        required=False,
        allow_null=True
    )

    class Meta:
        model = Event_Rule_IOT_Device
        exclude = ('event_rule_id',)


class EventRuleSerializer(serializers.ModelSerializer):
    params = EventRuleParamsSerializer(many=True, source='event_rule_params_set', required=False)
    devices = EventRuleIOTDeviceSerializer(many=True, source='event_rule_iot_device_set', required=False)
    task_name = serializers.CharField(write_only=True, required=False)
    interval_period = serializers.CharField(write_only=True, required=False)
    interval_every = serializers.IntegerField(write_only=True, required=False)
    crontab_pattern = serializers.CharField(write_only=True, required=False)
    start_datetime = serializers.DateTimeField(write_only=True, default=datetime.now)
    iot_type_id = serializers.SlugRelatedField(
        slug_field='model_name',
        queryset=IOT_Type.objects.all(),
        allow_null=True
    )
    event_type_id = serializers.SlugRelatedField(
        slug_field='event_name',
        queryset=Event_Type.objects.all(),
        allow_null=True
    )
    created_by = serializers.SlugRelatedField(
        slug_field='username',
        queryset=User.objects.all(),
        allow_null=True,
        required=False
    )
    inbound_api = serializers.SlugRelatedField(
        slug_field='name',
        queryset=APIDetail.objects.filter(type='inbound'),
        allow_null=False
    )
    outbound_api = serializers.SlugRelatedField(
        slug_field='name',
        queryset=APIDetail.objects.filter(type__in=['outbound', 'outbound_patch', 'outbound_put']),
        allow_null=False
    )

    class Meta:
        model = Event_Rule
        fields = '__all__'

    def validate(self, attrs):
        # Get the associated models from validated data
        iot_type = attrs.get('iot_type_id')
        event_type = attrs.get('event_type_id')

        # Try to fetch the Event_Type_IOT_Type_Map record
        try:
            event_iot_map = Event_Type_IOT_Type_Map.objects.get(iot_type_id=iot_type, event_type_id=event_type)
        except Event_Type_IOT_Type_Map.DoesNotExist:
            raise serializers.ValidationError("No valid mapping found for provided IOT Type and Event Type.")
        interval_period = attrs.get('interval_period')
        interval_every = attrs.get('interval_every')
        crontab_pattern = attrs.get('crontab_pattern')

        if interval_period and crontab_pattern:
            raise serializers.ValidationError("Provide either an interval schedule or a crontab schedule, not both.")
        if (interval_period and not interval_every) or (not interval_period and interval_every):
            raise serializers.ValidationError("Both 'interval_period' and 'interval_every' must be provided together.")
        if crontab_pattern and (interval_period or interval_every):
            raise serializers.ValidationError("Crontab pattern cannot be combined with interval schedule settings.")

        # Set the event_iot_map_id before saving
        attrs['event_iot_map_id'] = event_iot_map
        return super().validate(attrs)

    def create_schedule(self, interval_period=None, interval_every=None, crontab_pattern=None):
        if interval_period and interval_every:
            return IntervalSchedule.objects.get_or_create(every=interval_every, period=interval_period)[0]
        elif crontab_pattern:
            minute, hour, day_of_month, month_of_year, day_of_week = crontab_pattern.split()
            return CrontabSchedule.objects.get_or_create(
                minute=minute, hour=hour, day_of_month=day_of_month,
                month_of_year=month_of_year, day_of_week=day_of_week)[0]
        return None

    def create(self, validated_data):
        request = self.context.get('request')
        params_data = validated_data.pop('event_rule_params_set', [])
        devices_data = validated_data.pop('event_rule_iot_device_set', [])

        task_name = validated_data.pop('task_name', f"Task for {validated_data.get('name', 'No name')}")
        interval_period = validated_data.pop('interval_period', None)
        interval_every = validated_data.pop('interval_every', None)
        crontab_pattern = validated_data.pop('crontab_pattern', None)
        start_datetime = validated_data.pop('start_datetime', datetime.now())

        if 'created_by' not in validated_data or not validated_data['created_by']:
            validated_data['created_by'] = request.user

        event_rule = Event_Rule.objects.create(**validated_data)

        if params_data:
            for param_data in params_data:
                Event_Rule_Params.objects.create(event_rule_id=event_rule, **param_data)

        if devices_data:
            for device_data in devices_data:
                Event_Rule_IOT_Device.objects.create(event_rule_id=event_rule, **device_data)

        if task_name:
            # Schedule creation based on input
            schedule = self.create_schedule(
                interval_period=interval_period,
                interval_every=interval_every,
                crontab_pattern=crontab_pattern
            )

            # Creating the periodic task
            CustomPeriodicTask.objects.create(
                name=task_name,
                start_time=start_datetime,
                task=getattr(settings, 'APPLICATION_TASK_HANDLER'),
                args=json.dumps([event_rule.event_rule_id, task_name]),
                event_rule_id=event_rule,
                enabled=True,
                interval=schedule if isinstance(schedule, IntervalSchedule) else None,
                crontab=schedule if isinstance(schedule, CrontabSchedule) else None
            )

        return event_rule

    def update(self, instance, validated_data):
        params_data = validated_data.pop('event_rule_params_set', [])
        devices_data = validated_data.pop('event_rule_iot_device_set', [])

        # Pop task-related fields
        task_name = validated_data.pop('task_name', f"Task for {validated_data.get('name', 'No name')}")
        interval_period = validated_data.pop('interval_period', None)
        interval_every = validated_data.pop('interval_every', None)
        crontab_pattern = validated_data.pop('crontab_pattern', None)
        start_datetime = validated_data.pop('start_datetime', datetime.now())

        # Update Event_Rule fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        if params_data:
            # Update or create Params
            for param_data in params_data:
                param_id = param_data.get('param_id', None)
                if param_id:
                    param = Event_Rule_Params.objects.filter(param_id=param_id, event_rule_id=instance).first()
                    if param:
                        for attr, value in param_data.items():
                            setattr(param, attr, value)
                        param.save()
                else:
                    Event_Rule_Params.objects.create(event_rule_id=instance, **param_data)

        if devices_data:
            # Update or create Devices
            for device_data in devices_data:
                device_id = device_data.get('device_id', None)
                if device_id:
                    device = Event_Rule_IOT_Device.objects.filter(device_id=device_id, event_rule_id=instance).first()
                    if device:
                        for attr, value in device_data.items():
                            setattr(device, attr, value)
                        device.save()
                else:
                    Event_Rule_IOT_Device.objects.create(event_rule_id=instance, **device_data)

        if task_name:
            # Handle schedule updates or creation
            schedule = self.create_schedule(
                interval_period=interval_period,
                interval_every=interval_every,
                crontab_pattern=crontab_pattern
            )

            try:
                task = CustomPeriodicTask.objects.get(name=task_name)

                # Task exists, check if it's connected to the same event_rule
                if task.event_rule_id != instance:
                    raise ValueError(f"Task named '{task_name}' is already associated with a different event rule.")

                # Update the task's properties as it is associated with the current event_rule
                task.start_time = start_datetime
                task.task = getattr(settings, 'APPLICATION_TASK_HANDLER')
                task.args = json.dumps([instance.event_rule_id, task_name])
                task.enabled = True
                task.interval = schedule if isinstance(schedule, IntervalSchedule) else None
                task.crontab = schedule if isinstance(schedule, CrontabSchedule) else None
                task.save()

            except ObjectDoesNotExist:
                # The task does not exist, so create a new one
                CustomPeriodicTask.objects.create(
                    name=task_name,
                    event_rule_id=instance,
                    start_time=start_datetime,
                    task=getattr(settings, 'APPLICATION_TASK_HANDLER'),
                    args=json.dumps([instance.id, task_name]),
                    enabled=True,
                    interval=schedule if isinstance(schedule, IntervalSchedule) else None,
                    crontab=schedule if isinstance(schedule, CrontabSchedule) else None
                )

        return instance


class CustomPeriodicTaskSerializer(serializers.ModelSerializer):
    interval_period = serializers.CharField(write_only=True, required=False)
    interval_every = serializers.IntegerField(write_only=True, required=False)
    crontab_pattern = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = CustomPeriodicTask
        fields = ['interval_period', 'interval_every', 'crontab_pattern', 'enabled', 'start_time']

    def create_schedule(self, interval_period=None, interval_every=None, crontab_pattern=None):
        if interval_period and interval_every:
            return IntervalSchedule.objects.get_or_create(every=interval_every, period=interval_period)[0]
        elif crontab_pattern:
            minute, hour, day_of_month, month_of_year, day_of_week = crontab_pattern.split()
            return CrontabSchedule.objects.get_or_create(
                minute=minute, hour=hour, day_of_month=day_of_month,
                month_of_year=month_of_year, day_of_week=day_of_week)[0]
        return None

    def update(self, instance, validated_data):
        interval_period = validated_data.pop('interval_period', None)
        interval_every = validated_data.pop('interval_every', None)
        crontab_pattern = validated_data.pop('crontab_pattern', None)
        schedule = self.create_schedule(
            interval_period=interval_period,
            interval_every=interval_every,
            crontab_pattern=crontab_pattern
        )
        # Update the instance fields with validated data
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.interval = schedule if isinstance(schedule, IntervalSchedule) else None
        instance.crontab = schedule if isinstance(schedule, CrontabSchedule) else None
        instance.save()
        return instance
