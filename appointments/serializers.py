from rest_framework import serializers

from .models import (
    Appointment,
    AppointmentAudit,
    Consultation,
    Invoice,
)


class AppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = '__all__'
        read_only_fields = ['created_at']

    def validate(self, data):
        # Support partial updates by falling back to instance values
        start = data.get('start_datetime', getattr(self.instance, 'start_datetime', None))
        end = data.get('end_datetime', getattr(self.instance, 'end_datetime', None))

        if start and end and end <= start:
            raise serializers.ValidationError(
                {'end_datetime': 'End datetime must be after start datetime.'}
            )

        check_in = data.get('check_in_time', getattr(self.instance, 'check_in_time', None))
        if check_in and start and check_in < start:
            raise serializers.ValidationError(
                {'check_in_time': 'Check-in time cannot be before appointment start.'}
            )
        return data


class AppointmentAuditSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppointmentAudit
        fields = '__all__'
        read_only_fields = ['timestamp']

    def validate(self, data):
        old_dt = data.get('old_start_datetime')
        new_dt = data.get('new_start_datetime')
        if old_dt and new_dt and old_dt == new_dt:
            raise serializers.ValidationError(
                {'new_start_datetime': 'New start datetime must differ from old start datetime.'}
            )
        return data


class ConsultationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Consultation
        fields = '__all__'


class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = '__all__'

    def validate_amount(self, value):
        if value < 0:
            raise serializers.ValidationError('Amount must be non-negative.')
        return value
