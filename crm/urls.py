from django.urls import path
from . import views

app_name = "crm"

urlpatterns = [
    path("", views.ClientListView.as_view(), name="client_list"),
    path("new/", views.ClientCreateView.as_view(), name="client_create"),
    path("<int:pk>/", views.ClientDetailView.as_view(), name="client_detail"),
    path("<int:pk>/edit/", views.ClientUpdateView.as_view(), name="client_update"),
    path("pipeline/", views.PipelineView.as_view(), name="pipeline"),
    path("leads/new/", views.LeadCreateView.as_view(), name="lead_create"),
    path("briefs/new/", views.DesignBriefCreateView.as_view(), name="brief_create"),
    path("briefs/<int:pk>/approve/", views.DesignBriefApproveView.as_view(), name="brief_approve"),
    path("interactions/new/", views.InteractionCreateView.as_view(), name="interaction_create"),
]
