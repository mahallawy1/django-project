from rest_framework import serializers

from receptionist.models import Slot
from users.models import User

from .models import Doctor, DoctorException, DoctorSchedule

WEEKDAY_DAYS = {1, 2, 3, 4, 5}


def _extract_time_range(data):
    return data.get('start_time', data.get('start')), data.get('end_time', data.get('end'))


class DoctorSerializer(serializers.ModelSerializer):
    username = serializers.CharField(max_length=150, write_only=True)
    email = serializers.EmailField(write_only=True)
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(max_length=150, write_only=True, default='')
    last_name = serializers.CharField(max_length=150, write_only=True, default='')

    class Meta:
        model = Doctor
        fields = ['id', 'user_id', 'specialization', 'session_duration', 'buffer_time',
                  'username', 'email', 'password', 'first_name', 'last_name']

        read_only_fields = ['id', 'user_id']
        write_only_fields = ['password']

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('A user with this username already exists.')
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return value

    def create(self, validated_data):
        from django.db import transaction
        user_fields = ('username', 'email', 'password', 'first_name', 'last_name')
        
        user_data = {}
        for key in user_fields:
            if key in validated_data:
                user_data[key] = validated_data.pop(key)
     
        with transaction.atomic():
            user = User(
                username=user_data['username'],
                email=user_data['email'],
                first_name=user_data.get('first_name', ''),
                last_name=user_data.get('last_name', ''),
                role=User.Role.DOCTOR,
            )
            user.set_password(user_data['password'])
            user.save()
            return Doctor.objects.create(user_id=user, **validated_data)


class DoctorScheduleSerializer(serializers.ModelSerializer):
    day_of_week_display = serializers.CharField(source='get_day_of_week_display', read_only=True)

    class Meta:
        model = DoctorSchedule
        fields = '__all__'

    def validate(self, data):
        start = data.get('start_time', getattr(self.instance, 'start_time', None))
        end = data.get('end_time', getattr(self.instance, 'end_time', None))
        if start and end and end <= start:
            raise serializers.ValidationError(
                {'end_time': 'End time must be after start time.'}
            )

        doctor = data.get('doctor', getattr(self.instance, 'doctor', None))
        day = data.get('day_of_week', getattr(self.instance, 'day_of_week', None))
        qs = DoctorSchedule.objects.filter(doctor=doctor, day_of_week=day)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                {'day_of_week': 'A schedule for this doctor on this day already exists.'}
            )
        return data


class DoctorExceptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorException
        fields = '__all__'

    def validate(self, data):
        start = data.get('start_time', getattr(self.instance, 'start_time', None))
        end = data.get('end_time', getattr(self.instance, 'end_time', None))
        if start and end and end <= start:
            raise serializers.ValidationError(
                {'end_time': 'End time must be after start time.'}
            )
        return data


class SlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = Slot
        fields = '__all__'
        read_only_fields = ['is_booked']

    def validate(self, data):
        start = data.get('start_datetime', getattr(self.instance, 'start_datetime', None))
        end = data.get('end_datetime', getattr(self.instance, 'end_datetime', None))
        if start and end and end <= start:
            raise serializers.ValidationError(
                {'end_datetime': 'End datetime must be after start datetime.'}
            )
        return data


class AvailabilityItemInputSerializer(serializers.Serializer):
    day_of_week = serializers.IntegerField(required=False)
    start_time = serializers.TimeField(required=False)
    end_time = serializers.TimeField(required=False)
    start = serializers.TimeField(required=False, write_only=True)
    end = serializers.TimeField(required=False, write_only=True)

    def validate(self, data):
        start_time, end_time = _extract_time_range(data)
        if start_time is None or end_time is None:
            raise serializers.ValidationError('start_time and end_time are required.')
        if start_time >= end_time:
            raise serializers.ValidationError('start_time must be earlier than end_time.')
        data['start_time'] = start_time
        data['end_time'] = end_time
        return data


class ExceptionInputSerializer(serializers.Serializer):
    date = serializers.DateField()
    type = serializers.ChoiceField(
        choices=[
            'VACATION_DAY',
            'EXTRA_WORKING_DAY',
        ]
    )
    start_time = serializers.TimeField(required=False, allow_null=True)
    end_time = serializers.TimeField(required=False, allow_null=True)
    start = serializers.TimeField(required=False, allow_null=True, write_only=True)
    end = serializers.TimeField(required=False, allow_null=True, write_only=True)

    def to_internal_value(self, data):
        # Accept empty strings for optional time fields and normalize them to null.
        if isinstance(data, dict):
            data = data.copy()
            for field in ('start_time', 'end_time', 'start', 'end'):
                if data.get(field) == '':
                    data[field] = None
        return super().to_internal_value(data)

    def validate(self, data):
        start_time, end_time = _extract_time_range(data)
        exception_type = data['type']

        if exception_type == 'EXTRA_WORKING_DAY':
            if start_time is None or end_time is None:
                raise serializers.ValidationError('EXTRA_WORKING_DAY requires start_time and end_time.')
            if start_time >= end_time:
                raise serializers.ValidationError('start_time must be earlier than end_time.')
        elif start_time is not None and end_time is not None and start_time >= end_time:
                raise serializers.ValidationError('start_time must be earlier than end_time.')

        data['type'] = exception_type
        data['start_time'] = start_time
        data['end_time'] = end_time
        return data


class CreateAvailabilityRequestSerializer(serializers.Serializer):
    similar_weekdays = serializers.BooleanField()
    availability = AvailabilityItemInputSerializer(many=True)

    def validate(self, data):
        availability = data.get('availability', [])
        similar_weekdays = data.get('similar_weekdays')

        if similar_weekdays:
            if len(availability) != 1:
                raise serializers.ValidationError(
                    {'availability': 'When similar_weekdays is true, provide exactly one availability item.'}
                )
        else:
            if len(availability) != 5:
                raise serializers.ValidationError(
                    {'availability': 'When similar_weekdays is false, provide exactly 5 weekday entries.'}
                )

            days = []
            for item in availability:
                if 'day_of_week' not in item:
                    raise serializers.ValidationError({'availability': 'day_of_week is required for each item.'})
                if item['day_of_week'] not in WEEKDAY_DAYS:
                    raise serializers.ValidationError({'availability': 'day_of_week must be one of 1,2,3,4,5.'})
                days.append(item['day_of_week'])

            if len(set(days)) != 5:
                raise serializers.ValidationError({'availability': 'Each weekday (1..5) must be provided once.'})
        return data


class PatchAvailabilityRequestSerializer(serializers.Serializer):
    similar_weekdays = serializers.BooleanField(required=False)
    availability = AvailabilityItemInputSerializer(many=True, required=False)
    day_of_week = serializers.IntegerField(required=False)
    start_time = serializers.TimeField(required=False)
    end_time = serializers.TimeField(required=False)
    start = serializers.TimeField(required=False, write_only=True)
    end = serializers.TimeField(required=False, write_only=True)

    def validate(self, data):
        has_availability = 'availability' in data
        has_similar = 'similar_weekdays' in data
        has_direct = any(field in data for field in ('start_time', 'end_time', 'start', 'end'))

        if not (has_availability or has_similar or has_direct):
            raise serializers.ValidationError('Provide at least one field to update.')

        if has_similar and not has_availability:
            raise serializers.ValidationError({'availability': 'availability is required when similar_weekdays is provided.'})

        if has_availability:
            availability = data['availability']
            similar_weekdays = data.get('similar_weekdays', False)
            if similar_weekdays:
                if len(availability) != 1:
                    raise serializers.ValidationError(
                        {'availability': 'When similar_weekdays is true, provide exactly one availability item.'}
                    )
            else:
                if len(availability) == 1 and 'day_of_week' not in availability[0]:
                    # For availability detail PATCH, allow updating only start/end for the selected availability id.
                    data['start_time'] = availability[0]['start_time']
                    data['end_time'] = availability[0]['end_time']
                    data.pop('availability', None)
                else:
                    for item in availability:
                        if 'day_of_week' not in item:
                            raise serializers.ValidationError({'availability': 'day_of_week is required for each item.'})
                        if item['day_of_week'] not in WEEKDAY_DAYS:
                            raise serializers.ValidationError({'availability': 'day_of_week must be one of 1,2,3,4,5.'})

        if 'day_of_week' in data:
            raise serializers.ValidationError({'day_of_week': 'day_of_week cannot be updated for this endpoint. You can only update start_time and end_time.'})

        direct_start, direct_end = _extract_time_range(data)
        if direct_start is not None:
            data['start_time'] = direct_start
        if direct_end is not None:
            data['end_time'] = direct_end
        if direct_start is not None and direct_end is not None and direct_start >= direct_end:
            raise serializers.ValidationError({'end_time': 'end_time must be after start_time.'})

        return data
