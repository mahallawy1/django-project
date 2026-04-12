from django.urls import path

from .views import regenerate_all_doctors_next_7_days_slots

urlpatterns = [
	path(
		'slots/regenerate-next-7-days',
		regenerate_all_doctors_next_7_days_slots,
		name='regenerate_all_doctors_next_7_days_slots',
	),
]
