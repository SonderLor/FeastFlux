from django.urls import path
from . import views

app_name = "analytics"

urlpatterns = [
    path("dashboard/", views.AnalyticsDashboardView.as_view(), name="dashboard"),
    path("sales/", views.SalesReportView.as_view(), name="sales_report"),
    path("menu/", views.MenuAnalysisView.as_view(), name="menu_analysis"),
    path("staff/", views.StaffPerformanceView.as_view(), name="staff_performance"),
    path("tables/", views.TableOccupancyView.as_view(), name="table_occupancy"),
    path("nutrition/", views.NutritionalAnalyticsView.as_view(), name="nutritional_analytics"),
    path("customers/", views.CustomerSegmentationView.as_view(), name="customer_segmentation"),
]
