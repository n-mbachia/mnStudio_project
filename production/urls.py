from django.urls import path
from . import views

app_name = "production"

urlpatterns = [
    path("", views.JobCardListView.as_view(), name="jobcard_list"),
    path("jobs/<int:job_pk>/card/", views.JobCardDetailView.as_view(), name="jobcard_detail"),
    path("jobs/<int:job_pk>/card/unlock/", views.JobCardUnlockView.as_view(), name="jobcard_unlock"),
    path("jobs/<int:job_pk>/card/complete/", views.JobCardCompleteView.as_view(), name="jobcard_complete"),
    path("jobs/<int:job_pk>/card/print/", views.JobCardPrintView.as_view(), name="jobcard_print"),
    path("jobs/<int:job_pk>/timber/add/", views.TimberEntryCreateView.as_view(), name="timber_add"),
    path("timber/<int:pk>/edit/", views.TimberEntryUpdateView.as_view(), name="timber_edit"),
    path("timber/<int:pk>/delete/", views.TimberEntryDeleteView.as_view(), name="timber_delete"),
    path("jobs/<int:job_pk>/hardware/add/", views.HardwareEntryCreateView.as_view(), name="hardware_add"),
    path("hardware/<int:pk>/edit/", views.HardwareEntryUpdateView.as_view(), name="hardware_edit"),
    path("hardware/<int:pk>/delete/", views.HardwareEntryDeleteView.as_view(), name="hardware_delete"),
    path("jobs/<int:job_pk>/labor/add/", views.LaborEntryCreateView.as_view(), name="labor_add"),
    path("labor/<int:pk>/edit/", views.LaborEntryUpdateView.as_view(), name="labor_edit"),
    path("labor/<int:pk>/delete/", views.LaborEntryDeleteView.as_view(), name="labor_delete"),
]
