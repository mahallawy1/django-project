from rest_framework import serializers

from .models import (
    Appointment,
    AppointmentAudit,
    ConsultationRecord,
    Invoice,
    PrescriptionItem,
    RequestedTest,
    Waitlist,
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


class RequestedTestSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequestedTest
        fields = '__all__'


class PrescriptionItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrescriptionItem
        fields = '__all__'


class ConsultationRecordSerializer(serializers.ModelSerializer):
    requested_tests = RequestedTestSerializer(many=True, read_only=True)
    prescription_items = PrescriptionItemSerializer(many=True, read_only=True)

    class Meta:
        model = ConsultationRecord
        fields = '__all__'
        read_only_fields = ['created_at']


class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = '__all__'

    def validate_amount(self, value):
        if value < 0:
            raise serializers.ValidationError('Amount must be non-negative.')
        return value


class WaitlistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Waitlist
        fields = '__all__'
        read_only_fields = ['created_at']

    def validate(self, data):
        # Prevent duplicate waitlist entry on create
        if self.instance is None:
            doctor = data.get('doctor')
            patient = data.get('patient')
            preferred_date = data.get('preferred_date')
            if Waitlist.objects.filter(
                doctor=doctor, patient=patient, preferred_date=preferred_date
            ).exists():
                raise serializers.ValidationError(
                    'This patient is already on the waitlist for this doctor on that date.'
                )
        return data
