import pandas as pd
import csv
import io
import json
from datetime import datetime, timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView, ListView, DetailView
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Sum, Avg, Count, F, Q, ExpressionWrapper, FloatField
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.core.serializers.json import DjangoJSONEncoder

from .models import (
    DailySales,
    PopularItem,
    StaffPerformance,
    TableOccupancy,
    NutritionalAnalytics,
    CustomerSegment,
    CustomerInsight,
)
from .forms import (
    DateRangeForm,
    SalesReportForm,
    MenuAnalysisForm,
    StaffPerformanceForm,
    TableOccupancyForm,
    NutritionalAnalyticsForm,
    CustomerSegmentationForm,
)
from orders.models import Order, OrderItem


class AnalyticsDashboardView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Главная аналитическая панель со сводными метриками"""

    template_name = "analytics/dashboard.html"
    permission_required = "analytics.view_analytics_dashboard"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        form = DateRangeForm(self.request.GET, user=user)
        context["form"] = form

        restaurant = None
        start_date = (timezone.now() - timedelta(days=30)).date()
        end_date = timezone.now().date()

        if form.is_valid():
            if form.cleaned_data["restaurant"]:
                restaurant = form.cleaned_data["restaurant"]
            if form.cleaned_data["start_date"]:
                start_date = form.cleaned_data["start_date"]
            if form.cleaned_data["end_date"]:
                end_date = form.cleaned_data["end_date"]

        sales_query = DailySales.objects.filter(date__gte=start_date, date__lte=end_date)

        if restaurant:
            sales_query = sales_query.filter(restaurant=restaurant)

        daily_sales = list(
            sales_query.order_by("date").values(
                "date", "gross_sales", "net_sales", "completed_orders", "average_order_value"
            )
        )

        total_sales = sales_query.aggregate(
            total_revenue=Sum("net_sales"),
            total_orders=Sum("completed_orders"),
            avg_order_value=Avg("average_order_value"),
        )

        popular_items_query = PopularItem.objects.filter(
            date_period__gte=start_date.strftime("%Y-%m"),
            date_period__lte=end_date.strftime("%Y-%m"),
        )

        if restaurant:
            popular_items_query = popular_items_query.filter(restaurant=restaurant)

        top_items = popular_items_query.order_by("-total_orders")[:10]

        occupancy_query = TableOccupancy.objects.filter(date__gte=start_date, date__lte=end_date)

        if restaurant:
            occupancy_query = occupancy_query.filter(restaurant=restaurant)

        table_occupancy = (
            occupancy_query.values("table__number")
            .annotate(
                avg_occupancy=ExpressionWrapper(
                    F("usage_minutes") * 100.0 / (24 * 60), output_field=FloatField()
                ),
                total_revenue=Sum("total_revenue"),
            )
            .order_by("-avg_occupancy")[:10]
        )

        sales_data = {
            "labels": [item["date"].strftime("%d.%m") for item in daily_sales],
            "gross_sales": [float(item["gross_sales"]) for item in daily_sales],
            "net_sales": [float(item["net_sales"]) for item in daily_sales],
            "orders": [item["completed_orders"] for item in daily_sales],
        }

        context.update(
            {
                "daily_sales": daily_sales,
                "total_sales": total_sales,
                "top_items": top_items,
                "table_occupancy": table_occupancy,
                "sales_data": json.dumps(sales_data, cls=DjangoJSONEncoder),
                "start_date": start_date,
                "end_date": end_date,
                "selected_restaurant": restaurant,
            }
        )

        return context


class SalesReportView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Детальный отчет по продажам"""

    template_name = "analytics/sales_report.html"
    permission_required = "analytics.view_sales_report"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        form = SalesReportForm(self.request.GET, user=user)
        context["form"] = form

        if form.is_valid():
            restaurant = form.cleaned_data["restaurant"]
            start_date = (
                form.cleaned_data["start_date"] or (timezone.now() - timedelta(days=30)).date()
            )
            end_date = form.cleaned_data["end_date"] or timezone.now().date()
            category = form.cleaned_data["category"]
            payment_method = form.cleaned_data["payment_method"]
            order_type = form.cleaned_data["order_type"]
            group_by = form.cleaned_data["group_by"] or "day"
            export_format = form.cleaned_data["export_format"]

            orders_query = Order.objects.filter(
                created_at__date__gte=start_date,
                created_at__date__lte=end_date,
                status=Order.OrderStatus.COMPLETED,
            )

            if restaurant:
                orders_query = orders_query.filter(restaurant=restaurant)
            if payment_method:
                orders_query = orders_query.filter(payment_method=payment_method)
            if order_type:
                orders_query = orders_query.filter(order_type=order_type)

            order_items_query = OrderItem.objects.filter(order__in=orders_query)
            if category:
                order_items_query = order_items_query.filter(menu_item__category=category)
                orders_query = orders_query.filter(items__in=order_items_query)

            if group_by == "day":
                sales_data = (
                    orders_query.values("created_at__date")
                    .annotate(
                        total_orders=Count("id"),
                        gross_sales=Sum("subtotal"),
                        discounts=Sum("discount_amount"),
                        net_sales=Sum("total_amount"),
                        avg_check=Avg("total_amount"),
                    )
                    .order_by("created_at__date")
                )

                chart_data = {
                    "labels": [
                        item["created_at__date"].strftime("%d.%m.%Y") for item in sales_data
                    ],
                    "net_sales": [float(item["net_sales"]) for item in sales_data],
                    "orders": [item["total_orders"] for item in sales_data],
                }

            elif group_by == "week":
                from django.db.models.functions import TruncWeek

                sales_data = (
                    orders_query.annotate(week=TruncWeek("created_at"))
                    .values("week")
                    .annotate(
                        total_orders=Count("id"),
                        gross_sales=Sum("subtotal"),
                        discounts=Sum("discount_amount"),
                        net_sales=Sum("total_amount"),
                        avg_check=Avg("total_amount"),
                    )
                    .order_by("week")
                )

                chart_data = {
                    "labels": [item["week"].strftime("%d.%m.%Y") for item in sales_data],
                    "net_sales": [float(item["net_sales"]) for item in sales_data],
                    "orders": [item["total_orders"] for item in sales_data],
                }

            elif group_by == "month":
                from django.db.models.functions import TruncMonth

                sales_data = (
                    orders_query.annotate(month=TruncMonth("created_at"))
                    .values("month")
                    .annotate(
                        total_orders=Count("id"),
                        gross_sales=Sum("subtotal"),
                        discounts=Sum("discount_amount"),
                        net_sales=Sum("total_amount"),
                        avg_check=Avg("total_amount"),
                    )
                    .order_by("month")
                )

                chart_data = {
                    "labels": [item["month"].strftime("%m.%Y") for item in sales_data],
                    "net_sales": [float(item["net_sales"]) for item in sales_data],
                    "orders": [item["total_orders"] for item in sales_data],
                }

            elif group_by == "category":
                sales_data = (
                    order_items_query.values("menu_item__category__name")
                    .annotate(
                        total_orders=Count("order", distinct=True),
                        gross_sales=Sum(F("price") * F("quantity")),
                        net_sales=Sum(F("price") * F("quantity")),
                        total_quantity=Sum("quantity"),
                    )
                    .order_by("-net_sales")
                )

                chart_data = {
                    "labels": [item["menu_item__category__name"] for item in sales_data],
                    "net_sales": [float(item["net_sales"]) for item in sales_data],
                    "orders": [item["total_orders"] for item in sales_data],
                }

            elif group_by == "item":
                sales_data = (
                    order_items_query.values("menu_item__name", "menu_item__category__name")
                    .annotate(
                        total_orders=Count("order", distinct=True),
                        gross_sales=Sum(F("price") * F("quantity")),
                        net_sales=Sum(F("price") * F("quantity")),
                        total_quantity=Sum("quantity"),
                    )
                    .order_by("-total_quantity")
                )

                chart_data = {
                    "labels": [
                        item["menu_item__name"] for item in sales_data[:15]
                    ],  # Ограничиваем для графика
                    "net_sales": [float(item["net_sales"]) for item in sales_data[:15]],
                    "quantity": [item["total_quantity"] for item in sales_data[:15]],
                }

            totals = {
                "total_orders": orders_query.count(),
                "gross_sales": orders_query.aggregate(sum=Sum("subtotal"))["sum"] or 0,
                "discounts": orders_query.aggregate(sum=Sum("discount_amount"))["sum"] or 0,
                "net_sales": orders_query.aggregate(sum=Sum("total_amount"))["sum"] or 0,
                "avg_check": orders_query.aggregate(avg=Avg("total_amount"))["avg"] or 0,
            }

            context.update(
                {
                    "sales_data": sales_data,
                    "chart_data": json.dumps(chart_data, cls=DjangoJSONEncoder),
                    "totals": totals,
                    "group_by": group_by,
                }
            )

            if export_format:
                return self.export_data(sales_data, export_format, group_by)

        return context

    def export_data(self, data, format, group_by):
        """Экспорт данных в выбранном формате"""
        if format == "csv":
            response = HttpResponse(content_type="text/csv")
            response["Content-Disposition"] = 'attachment; filename="sales_report.csv"'

            writer = csv.writer(response)

            if group_by == "day":
                writer.writerow(
                    [
                        "Дата",
                        "Заказов",
                        "Валовые продажи",
                        "Скидки",
                        "Чистые продажи",
                        "Средний чек",
                    ]
                )
                for item in data:
                    writer.writerow(
                        [
                            item["created_at__date"].strftime("%d.%m.%Y"),
                            item["total_orders"],
                            item["gross_sales"],
                            item["discounts"],
                            item["net_sales"],
                            item["avg_check"],
                        ]
                    )

            elif group_by in ["week", "month"]:
                date_field = "week" if group_by == "week" else "month"
                writer.writerow(
                    [
                        "Период",
                        "Заказов",
                        "Валовые продажи",
                        "Скидки",
                        "Чистые продажи",
                        "Средний чек",
                    ]
                )
                for item in data:
                    writer.writerow(
                        [
                            item[date_field].strftime(
                                "%d.%m.%Y" if group_by == "week" else "%m.%Y"
                            ),
                            item["total_orders"],
                            item["gross_sales"],
                            item["discounts"],
                            item["net_sales"],
                            item["avg_check"],
                        ]
                    )

            elif group_by == "category":
                writer.writerow(
                    ["Категория", "Заказов", "Валовые продажи", "Чистые продажи", "Количество"]
                )
                for item in data:
                    writer.writerow(
                        [
                            item["menu_item__category__name"],
                            item["total_orders"],
                            item["gross_sales"],
                            item["net_sales"],
                            item["total_quantity"],
                        ]
                    )

            elif group_by == "item":
                writer.writerow(
                    [
                        "Блюдо",
                        "Категория",
                        "Заказов",
                        "Валовые продажи",
                        "Чистые продажи",
                        "Количество",
                    ]
                )
                for item in data:
                    writer.writerow(
                        [
                            item["menu_item__name"],
                            item["menu_item__category__name"],
                            item["total_orders"],
                            item["gross_sales"],
                            item["net_sales"],
                            item["total_quantity"],
                        ]
                    )

            return response

        elif format == "excel":
            import pandas as pd
            from django.http import HttpResponse

            response = HttpResponse(content_type="application/vnd.ms-excel")
            response["Content-Disposition"] = 'attachment; filename="sales_report.xlsx"'

            df = pd.DataFrame(list(data))

            if group_by == "day":
                df = df.rename(
                    columns={
                        "created_at__date": "Дата",
                        "total_orders": "Заказов",
                        "gross_sales": "Валовые продажи",
                        "discounts": "Скидки",
                        "net_sales": "Чистые продажи",
                        "avg_check": "Средний чек",
                    }
                )

            with pd.ExcelWriter(io.BytesIO()) as writer:
                df.to_excel(writer, index=False)
                writer.save()
                response.write(writer.getvalue())

            return response

        elif format == "pdf":
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter, landscape
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
            from reportlab.lib.styles import getSampleStyleSheet

            response = HttpResponse(content_type="application/pdf")
            response["Content-Disposition"] = 'attachment; filename="sales_report.pdf"'

            doc = SimpleDocTemplate(response, pagesize=landscape(letter))
            elements = []

            styles = getSampleStyleSheet()
            title_style = styles["Heading1"]

            elements.append(Paragraph("Отчет по продажам", title_style))

            if group_by == "day":
                table_data = [
                    [
                        "Дата",
                        "Заказов",
                        "Валовые продажи",
                        "Скидки",
                        "Чистые продажи",
                        "Средний чек",
                    ]
                ]
                for item in data:
                    table_data.append(
                        [
                            item["created_at__date"].strftime("%d.%m.%Y"),
                            str(item["total_orders"]),
                            str(item["gross_sales"]),
                            str(item["discounts"]),
                            str(item["net_sales"]),
                            str(item["avg_check"]),
                        ]
                    )

            table = Table(table_data)
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 14),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ]
                )
            )

            elements.append(table)

            doc.build(elements)

            return response

        return None


class MenuAnalysisView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Анализ меню и популярности блюд"""

    template_name = "analytics/menu_analysis.html"
    permission_required = "analytics.view_menu_analysis"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        form = MenuAnalysisForm(self.request.GET, user=user)
        context["form"] = form

        if form.is_valid():
            restaurant = form.cleaned_data["restaurant"]
            start_date = (
                form.cleaned_data["start_date"] or (timezone.now() - timedelta(days=90)).date()
            )
            end_date = form.cleaned_data["end_date"] or timezone.now().date()
            category = form.cleaned_data["category"]
            analysis_type = form.cleaned_data["analysis_type"]

            start_period = start_date.strftime("%Y-%m")
            end_period = end_date.strftime("%Y-%m")

            popular_items_query = PopularItem.objects.filter(
                date_period__gte=start_period, date_period__lte=end_period
            )

            if restaurant:
                popular_items_query = popular_items_query.filter(restaurant=restaurant)

            if category:
                popular_items_query = popular_items_query.filter(menu_item__category=category)

            items_data = {}
            for item in popular_items_query:
                if item.menu_item_id not in items_data:
                    items_data[item.menu_item_id] = {
                        "menu_item": item.menu_item,
                        "total_orders": 0,
                        "total_quantity": 0,
                        "total_revenue": 0,
                        "average_rating": item.average_rating,
                        "category": item.menu_item.category,
                    }

                data = items_data[item.menu_item_id]
                data["total_orders"] += item.total_orders
                data["total_quantity"] += item.total_quantity
                data["total_revenue"] += float(item.total_revenue)

            items_list = list(items_data.values())

            if analysis_type == "popularity":
                items_list.sort(key=lambda x: x["total_orders"], reverse=True)
                chart_title = "Популярность блюд по количеству заказов"
                chart_data = {
                    "labels": [item["menu_item"].name for item in items_list[:15]],
                    "values": [item["total_orders"] for item in items_list[:15]],
                }

            elif analysis_type == "revenue":
                items_list.sort(key=lambda x: x["total_revenue"], reverse=True)
                chart_title = "Блюда по выручке"
                chart_data = {
                    "labels": [item["menu_item"].name for item in items_list[:15]],
                    "values": [item["total_revenue"] for item in items_list[:15]],
                }

            elif analysis_type == "profitability":
                for item in items_list:
                    cost = item["menu_item"].price * 0.4
                    profit = item["total_revenue"] - (cost * item["total_quantity"])
                    profit_margin = (
                        profit / item["total_revenue"] if item["total_revenue"] > 0 else 0
                    )
                    item["profit"] = profit
                    item["profit_margin"] = profit_margin

                items_list.sort(key=lambda x: x["profit"], reverse=True)
                chart_title = "Прибыльность блюд"
                chart_data = {
                    "labels": [item["menu_item"].name for item in items_list[:15]],
                    "values": [item["profit"] for item in items_list[:15]],
                    "margins": [round(item["profit_margin"] * 100, 2) for item in items_list[:15]],
                }

            elif analysis_type == "abc":
                items_list.sort(key=lambda x: x["total_revenue"], reverse=True)

                total_revenue = sum(item["total_revenue"] for item in items_list)
                cumulative_percent = 0

                for item in items_list:
                    item_percent = item["total_revenue"] / total_revenue if total_revenue > 0 else 0
                    cumulative_percent += item_percent
                    item["revenue_percent"] = item_percent * 100
                    item["cumulative_percent"] = cumulative_percent * 100

                    if cumulative_percent <= 0.8:
                        item["abc_category"] = "A"
                    elif cumulative_percent <= 0.95:
                        item["abc_category"] = "B"
                    else:
                        item["abc_category"] = "C"

                abc_categories = {"A": [], "B": [], "C": []}
                for item in items_list:
                    abc_categories[item["abc_category"]].append(item)

                chart_title = "ABC-анализ блюд по выручке"
                chart_data = {
                    "categories": ["A", "B", "C"],
                    "item_counts": [
                        len(abc_categories["A"]),
                        len(abc_categories["B"]),
                        len(abc_categories["C"]),
                    ],
                    "revenue_percents": [
                        sum(item["revenue_percent"] for item in abc_categories["A"]),
                        sum(item["revenue_percent"] for item in abc_categories["B"]),
                        sum(item["revenue_percent"] for item in abc_categories["C"]),
                    ],
                }

                context["abc_categories"] = abc_categories

            context.update(
                {
                    "items_list": items_list,
                    "analysis_type": analysis_type,
                    "chart_title": chart_title,
                    "chart_data": json.dumps(chart_data, cls=DjangoJSONEncoder),
                    "total_items": len(items_list),
                    "total_orders": sum(item["total_orders"] for item in items_list),
                    "total_revenue": sum(item["total_revenue"] for item in items_list),
                }
            )

        return context


class StaffPerformanceView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Анализ эффективности персонала"""

    template_name = "analytics/staff_performance.html"
    permission_required = "analytics.view_staff_performance"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        form = StaffPerformanceForm(self.request.GET, user=user)
        context["form"] = form

        if form.is_valid():
            restaurant = form.cleaned_data["restaurant"]
            start_date = (
                form.cleaned_data["start_date"] or (timezone.now() - timedelta(days=30)).date()
            )
            end_date = form.cleaned_data["end_date"] or timezone.now().date()
            staff_member = form.cleaned_data["staff_member"]
            staff_role = form.cleaned_data["staff_role"]
            metrics = form.cleaned_data["metrics"]

            start_period = start_date.strftime("%Y-%m")
            end_period = end_date.strftime("%Y-%m")

            performance_query = StaffPerformance.objects.filter(
                date_period__gte=start_period, date_period__lte=end_period
            )

            if restaurant:
                performance_query = performance_query.filter(restaurant=restaurant)

            if staff_member:
                performance_query = performance_query.filter(staff=staff_member)

            if staff_role:
                if staff_role == "waiter":
                    staff_role_filter = Q(staff__waiter_profile__isnull=False)
                elif staff_role == "chef":
                    staff_role_filter = Q(staff__chef_profile__isnull=False)
                elif staff_role == "bartender":
                    staff_role_filter = Q(staff__bartender_profile__isnull=False)
                elif staff_role == "manager":
                    staff_role_filter = Q(staff__restaurant_manager__isnull=False)
                else:
                    staff_role_filter = Q()

                performance_query = performance_query.filter(staff_role_filter)

            staff_data = {}
            for perf in performance_query:
                if perf.staff_id not in staff_data:
                    staff_data[perf.staff_id] = {
                        "staff": perf.staff,
                        "total_orders": 0,
                        "completed_orders": 0,
                        "cancelled_orders": 0,
                        "total_sales": 0,
                        "average_order_value": 0,
                        "items_prepared": 0,
                        "average_preparation_time": 0,
                        "hours_worked": 0,
                        "periods_count": 0,
                    }

                data = staff_data[perf.staff_id]
                data["total_orders"] += perf.total_orders
                data["completed_orders"] += perf.completed_orders
                data["cancelled_orders"] += perf.cancelled_orders
                data["total_sales"] += float(perf.total_sales)
                data["average_order_value"] += float(perf.average_order_value)
                data["items_prepared"] += perf.items_prepared
                data["average_preparation_time"] += perf.average_preparation_time
                data["hours_worked"] += float(perf.hours_worked)
                data["periods_count"] += 1

            for staff_id, data in staff_data.items():
                if data["periods_count"] > 0:
                    data["average_order_value"] = (
                        data["average_order_value"] / data["periods_count"]
                    )
                    data["average_preparation_time"] = (
                        data["average_preparation_time"] / data["periods_count"]
                    )

                if data["hours_worked"] > 0:
                    data["sales_per_hour"] = data["total_sales"] / data["hours_worked"]
                    data["orders_per_hour"] = data["total_orders"] / data["hours_worked"]
                else:
                    data["sales_per_hour"] = 0
                    data["orders_per_hour"] = 0

                if data["total_orders"] > 0:
                    data["completion_rate"] = (
                        data["completed_orders"] / data["total_orders"]
                    ) * 100
                else:
                    data["completion_rate"] = 0

            staff_list = list(staff_data.values())
            staff_list.sort(key=lambda x: x["total_sales"], reverse=True)

            chart_data = {
                "staff_names": [
                    f"{s['staff'].first_name} {s['staff'].last_name}" for s in staff_list[:10]
                ]
            }

            for metric in metrics:
                if metric == "orders":
                    chart_data["orders"] = [s["total_orders"] for s in staff_list[:10]]
                elif metric == "sales":
                    chart_data["sales"] = [s["total_sales"] for s in staff_list[:10]]
                elif metric == "avg_time":
                    chart_data["avg_time"] = [
                        s["average_preparation_time"] for s in staff_list[:10]
                    ]
                elif metric == "avg_check":
                    chart_data["avg_check"] = [s["average_order_value"] for s in staff_list[:10]]

            context.update(
                {
                    "staff_list": staff_list,
                    "chart_data": json.dumps(chart_data, cls=DjangoJSONEncoder),
                    "selected_metrics": metrics,
                    "total_staff": len(staff_list),
                    "total_sales": sum(s["total_sales"] for s in staff_list),
                    "total_orders": sum(s["total_orders"] for s in staff_list),
                    "total_hours": sum(s["hours_worked"] for s in staff_list),
                }
            )

        return context


class TableOccupancyView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Анализ загруженности столиков"""

    template_name = "analytics/table_occupancy.html"
    permission_required = "analytics.view_table_occupancy"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        form = TableOccupancyForm(self.request.GET, user=user)
        context["form"] = form

        if form.is_valid():
            restaurant = form.cleaned_data["restaurant"]
            start_date = (
                form.cleaned_data["start_date"] or (timezone.now() - timedelta(days=30)).date()
            )
            end_date = form.cleaned_data["end_date"] or timezone.now().date()
            view_mode = form.cleaned_data["view_mode"]
            display_by = form.cleaned_data["display_by"]

            occupancy_query = TableOccupancy.objects.filter(
                date__gte=start_date, date__lte=end_date
            )

            if restaurant:
                occupancy_query = occupancy_query.filter(restaurant=restaurant)

            if view_mode == "heatmap":
                if display_by == "hour":
                    tables = (
                        occupancy_query.values("table__number").distinct().order_by("table__number")
                    )
                    table_numbers = [t["table__number"] for t in tables]

                    hours = list(range(24))
                    heatmap_data = []

                    for hour in hours:
                        hour_data = []
                        for table_num in table_numbers:
                            count = occupancy_query.filter(
                                table__number=table_num, peak_usage_hour=hour
                            ).count()

                            hour_data.append(count)

                        heatmap_data.append(hour_data)

                    heatmap_config = {
                        "x_labels": table_numbers,
                        "y_labels": [f"{h}:00" for h in hours],
                        "data": heatmap_data,
                    }

                    context["heatmap_config"] = json.dumps(heatmap_config, cls=DjangoJSONEncoder)

                elif display_by == "day":
                    days = (end_date - start_date).days + 1
                    date_range = [start_date + timedelta(days=d) for d in range(days)]

                    tables = (
                        occupancy_query.values("table__number").distinct().order_by("table__number")
                    )
                    table_numbers = [t["table__number"] for t in tables]

                    heatmap_data = []

                    for date in date_range:
                        day_data = []
                        for table_num in table_numbers:
                            try:
                                occupancy = occupancy_query.get(
                                    table__number=table_num, date=date
                                ).occupancy_rate
                            except TableOccupancy.DoesNotExist:
                                occupancy = 0

                            day_data.append(occupancy)

                        heatmap_data.append(day_data)

                    heatmap_config = {
                        "x_labels": table_numbers,
                        "y_labels": [d.strftime("%d.%m") for d in date_range],
                        "data": heatmap_data,
                    }

                    context["heatmap_config"] = json.dumps(heatmap_config, cls=DjangoJSONEncoder)

                elif display_by == "week":
                    weekdays = [
                        "Понедельник",
                        "Вторник",
                        "Среда",
                        "Четверг",
                        "Пятница",
                        "Суббота",
                        "Воскресенье",
                    ]

                    tables = (
                        occupancy_query.values("table__number").distinct().order_by("table__number")
                    )
                    table_numbers = [t["table__number"] for t in tables]

                    heatmap_data = []

                    for weekday_idx in range(7):
                        weekday_data = []
                        for table_num in table_numbers:
                            day_occupancy = (
                                occupancy_query.filter(
                                    table__number=table_num, date__week_day=weekday_idx + 1
                                ).aggregate(
                                    avg=Avg(
                                        ExpressionWrapper(
                                            F("usage_minutes") * 100.0 / (24 * 60),
                                            output_field=FloatField(),
                                        )
                                    )
                                )[
                                    "avg"
                                ]
                                or 0
                            )

                            weekday_data.append(day_occupancy)

                        heatmap_data.append(weekday_data)

                    heatmap_config = {
                        "x_labels": table_numbers,
                        "y_labels": weekdays,
                        "data": heatmap_data,
                    }

                    context["heatmap_config"] = json.dumps(heatmap_config, cls=DjangoJSONEncoder)

            elif view_mode == "chart":
                if display_by == "hour":
                    hour_data = []
                    for hour in range(24):
                        avg_occupancy = (
                            occupancy_query.filter(peak_usage_hour=hour).aggregate(
                                avg=Avg(
                                    ExpressionWrapper(
                                        F("usage_minutes") * 100.0 / (24 * 60),
                                        output_field=FloatField(),
                                    )
                                )
                            )["avg"]
                            or 0
                        )

                        hour_data.append(
                            {"hour": hour, "occupancy": avg_occupancy, "label": f"{hour}:00"}
                        )

                    chart_data = {
                        "labels": [d["label"] for d in hour_data],
                        "occupancy": [d["occupancy"] for d in hour_data],
                    }

                elif display_by == "day":
                    days = (end_date - start_date).days + 1
                    date_range = [start_date + timedelta(days=d) for d in range(days)]

                    day_data = []
                    for date in date_range:
                        avg_occupancy = (
                            occupancy_query.filter(date=date).aggregate(
                                avg=Avg(
                                    ExpressionWrapper(
                                        F("usage_minutes") * 100.0 / (24 * 60),
                                        output_field=FloatField(),
                                    )
                                )
                            )["avg"]
                            or 0
                        )

                        day_data.append(
                            {
                                "date": date,
                                "occupancy": avg_occupancy,
                                "label": date.strftime("%d.%m"),
                            }
                        )

                    chart_data = {
                        "labels": [d["label"] for d in day_data],
                        "occupancy": [d["occupancy"] for d in day_data],
                    }

                elif display_by == "week":
                    weekdays = [
                        "Понедельник",
                        "Вторник",
                        "Среда",
                        "Четверг",
                        "Пятница",
                        "Суббота",
                        "Воскресенье",
                    ]

                    weekday_data = []
                    for weekday_idx in range(7):
                        avg_occupancy = (
                            occupancy_query.filter(date__week_day=weekday_idx + 1).aggregate(
                                avg=Avg(
                                    ExpressionWrapper(
                                        F("usage_minutes") * 100.0 / (24 * 60),
                                        output_field=FloatField(),
                                    )
                                )
                            )["avg"]
                            or 0
                        )

                        weekday_data.append(
                            {
                                "weekday": weekday_idx,
                                "occupancy": avg_occupancy,
                                "label": weekdays[weekday_idx],
                            }
                        )

                    chart_data = {
                        "labels": [d["label"] for d in weekday_data],
                        "occupancy": [d["occupancy"] for d in weekday_data],
                    }

                context["chart_data"] = json.dumps(chart_data, cls=DjangoJSONEncoder)

            elif view_mode == "table":
                table_data = (
                    occupancy_query.values("table__number")
                    .annotate(
                        avg_occupancy=Avg(
                            ExpressionWrapper(
                                F("usage_minutes") * 100.0 / (24 * 60), output_field=FloatField()
                            )
                        ),
                        avg_revenue=Avg("total_revenue"),
                        avg_guests=Avg("total_guests"),
                        total_usage=Sum("usage_minutes"),
                        total_revenue=Sum("total_revenue"),
                        total_orders=Sum("total_orders"),
                    )
                    .order_by("-avg_occupancy")
                )

                for table in table_data:
                    table["revenue_per_hour"] = (
                        table["total_revenue"] / (table["total_usage"] / 60)
                        if table["total_usage"] > 0
                        else 0
                    )
                    table["revenue_per_guest"] = (
                        table["total_revenue"] / table["avg_guests"]
                        if table["avg_guests"] > 0
                        else 0
                    )

                context["table_data"] = table_data

            summary = {
                "avg_occupancy": occupancy_query.aggregate(
                    avg=Avg(
                        ExpressionWrapper(
                            F("usage_minutes") * 100.0 / (24 * 60), output_field=FloatField()
                        )
                    )
                )["avg"]
                or 0,
                "total_revenue": occupancy_query.aggregate(sum=Sum("total_revenue"))["sum"] or 0,
                "total_orders": occupancy_query.aggregate(sum=Sum("total_orders"))["sum"] or 0,
                "total_guests": occupancy_query.aggregate(sum=Sum("total_guests"))["sum"] or 0,
                "total_minutes": occupancy_query.aggregate(sum=Sum("usage_minutes"))["sum"] or 0,
            }

            if summary["total_minutes"] > 0:
                summary["revenue_per_hour"] = summary["total_revenue"] / (
                    summary["total_minutes"] / 60
                )
            else:
                summary["revenue_per_hour"] = 0

            if summary["total_guests"] > 0:
                summary["revenue_per_guest"] = summary["total_revenue"] / summary["total_guests"]
            else:
                summary["revenue_per_guest"] = 0

            context.update(
                {
                    "view_mode": view_mode,
                    "display_by": display_by,
                    "summary": summary,
                }
            )

        return context


class NutritionalAnalyticsView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Анализ КБЖУ и диетических предпочтений клиентов"""

    template_name = "analytics/nutritional_analytics.html"
    permission_required = "analytics.view_nutritional_analytics"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        form = NutritionalAnalyticsForm(self.request.GET, user=user)
        context["form"] = form

        if form.is_valid():
            restaurant = form.cleaned_data["restaurant"]
            start_date = (
                form.cleaned_data["start_date"] or (timezone.now() - timedelta(days=90)).date()
            )
            end_date = form.cleaned_data["end_date"] or timezone.now().date()
            chart_type = form.cleaned_data["chart_type"]

            start_period = start_date.strftime("%Y-%m")
            end_period = end_date.strftime("%Y-%m")

            nutrition_query = NutritionalAnalytics.objects.filter(
                date_period__gte=start_period, date_period__lte=end_period
            )

            if restaurant:
                nutrition_query = nutrition_query.filter(restaurant=restaurant)

            total_orders = 0
            avg_calories = 0
            avg_protein = 0
            avg_fat = 0
            avg_carbs = 0
            vegetarian_orders = 0
            vegan_orders = 0
            gluten_free_orders = 0
            lactose_free_orders = 0
            allergens_count = {}

            for nutrition in nutrition_query:
                total_orders += nutrition.total_orders
                avg_calories += nutrition.avg_calories_per_order * nutrition.total_orders
                avg_protein += nutrition.avg_protein_per_order * nutrition.total_orders
                avg_fat += nutrition.avg_fat_per_order * nutrition.total_orders
                avg_carbs += nutrition.avg_carbs_per_order * nutrition.total_orders
                vegetarian_orders += nutrition.vegetarian_orders
                vegan_orders += nutrition.vegan_orders
                gluten_free_orders += nutrition.gluten_free_orders
                lactose_free_orders += nutrition.lactose_free_orders

                # Объединяем данные об аллергенах
                for allergen, count in nutrition.common_allergens.items():
                    allergens_count[allergen] = allergens_count.get(allergen, 0) + count

            if total_orders > 0:
                avg_calories = avg_calories / total_orders
                avg_protein = avg_protein / total_orders
                avg_fat = avg_fat / total_orders
                avg_carbs = avg_carbs / total_orders

            if chart_type == "nutrients":
                chart_data = {
                    "labels": ["Белки", "Жиры", "Углеводы"],
                    "values": [float(avg_protein), float(avg_fat), float(avg_carbs)],
                    "calories": float(avg_calories),
                }

            elif chart_type == "dietary":
                chart_data = {
                    "labels": ["Вегетарианские", "Веганские", "Безглютеновые", "Безлактозные"],
                    "values": [
                        vegetarian_orders,
                        vegan_orders,
                        gluten_free_orders,
                        lactose_free_orders,
                    ],
                    "percents": [
                        round(vegetarian_orders / total_orders * 100, 2) if total_orders > 0 else 0,
                        round(vegan_orders / total_orders * 100, 2) if total_orders > 0 else 0,
                        (
                            round(gluten_free_orders / total_orders * 100, 2)
                            if total_orders > 0
                            else 0
                        ),
                        (
                            round(lactose_free_orders / total_orders * 100, 2)
                            if total_orders > 0
                            else 0
                        ),
                    ],
                }

            elif chart_type == "allergens":
                sorted_allergens = sorted(
                    allergens_count.items(), key=lambda x: x[1], reverse=True
                )[:10]

                chart_data = {
                    "labels": [allergen for allergen, _ in sorted_allergens],
                    "values": [count for _, count in sorted_allergens],
                }

            context.update(
                {
                    "chart_type": chart_type,
                    "chart_data": json.dumps(chart_data, cls=DjangoJSONEncoder),
                    "total_orders": total_orders,
                    "avg_calories": avg_calories,
                    "avg_protein": avg_protein,
                    "avg_fat": avg_fat,
                    "avg_carbs": avg_carbs,
                    "vegetarian_orders": vegetarian_orders,
                    "vegan_orders": vegan_orders,
                    "gluten_free_orders": gluten_free_orders,
                    "lactose_free_orders": lactose_free_orders,
                    "allergens": sorted(allergens_count.items(), key=lambda x: x[1], reverse=True)[
                        :20
                    ],
                }
            )

        return context


class CustomerSegmentationView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Анализ клиентских сегментов"""

    template_name = "analytics/customer_segmentation.html"
    permission_required = "analytics.view_customer_segmentation"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        form = CustomerSegmentationForm(self.request.GET, user=user)
        context["form"] = form

        if form.is_valid():
            restaurant = form.cleaned_data["restaurant"]
            segment_id = form.cleaned_data["segment"]
            period_days = form.cleaned_data["period"]

            if period_days != "all":
                start_date = timezone.now() - timedelta(days=int(period_days))
            else:
                start_date = None

            segments_query = CustomerSegment.objects.all()

            if restaurant:
                segments_query = segments_query.filter(
                    Q(restaurant=restaurant) | Q(restaurant__isnull=True)
                )

            if segment_id:
                segments_query = segments_query.filter(id=segment_id)

            segments = list(segments_query)

            for segment in segments:
                customers = segment.customers.all()

                segment.customer_count = customers.count()

                if start_date:
                    orders = Order.objects.filter(
                        customer__in=customers,
                        created_at__gte=start_date,
                        status=Order.OrderStatus.COMPLETED,
                    )
                else:
                    orders = Order.objects.filter(
                        customer__in=customers, status=Order.OrderStatus.COMPLETED
                    )

                segment.total_orders = orders.count()
                segment.total_revenue = orders.aggregate(sum=Sum("total_amount"))["sum"] or 0

                if segment.customer_count > 0:
                    segment.avg_orders_per_customer = segment.total_orders / segment.customer_count
                    segment.avg_revenue_per_customer = (
                        segment.total_revenue / segment.customer_count
                    )
                else:
                    segment.avg_orders_per_customer = 0
                    segment.avg_revenue_per_customer = 0

                if segment.total_orders > 0:
                    segment.avg_check = segment.total_revenue / segment.total_orders
                else:
                    segment.avg_check = 0

                segment.category_stats = {}

                order_items = OrderItem.objects.filter(order__in=orders).select_related(
                    "menu_item__category"
                )

                for item in order_items:
                    category_name = item.menu_item.category.name
                    if category_name not in segment.category_stats:
                        segment.category_stats[category_name] = {"count": 0, "revenue": 0}

                    segment.category_stats[category_name]["count"] += item.quantity
                    segment.category_stats[category_name]["revenue"] += float(
                        item.price * item.quantity
                    )

                segment.sorted_categories = sorted(
                    segment.category_stats.items(), key=lambda x: x[1]["count"], reverse=True
                )

            if segment_id and segments:
                selected_segment = segments[0]

                customer_insights = CustomerInsight.objects.filter(segment=selected_segment)

                dietary_prefs = {"vegetarian": 0, "vegan": 0, "gluten_free": 0, "lactose_free": 0}

                for insight in customer_insights:
                    if insight.dietary_preferences:
                        for pref, value in insight.dietary_preferences.items():
                            if value and pref in dietary_prefs:
                                dietary_prefs[pref] += 1

                for pref in dietary_prefs:
                    if customer_insights.count() > 0:
                        dietary_prefs[pref] = (
                            dietary_prefs[pref] / customer_insights.count()
                        ) * 100

                visit_frequency = {}
                for insight in customer_insights:
                    if insight.purchase_patterns and "weekdays" in insight.purchase_patterns:
                        for day, count in insight.purchase_patterns["weekdays"].items():
                            visit_frequency[day] = visit_frequency.get(day, 0) + count

                visit_time = {}
                for insight in customer_insights:
                    if insight.purchase_patterns and "hours" in insight.purchase_patterns:
                        for hour, count in insight.purchase_patterns["hours"].items():
                            visit_time[hour] = visit_time.get(hour, 0) + count

                sorted_weekdays = sorted(visit_frequency.items(), key=lambda x: int(x[0]))
                sorted_hours = sorted(visit_time.items(), key=lambda x: int(x[0]))

                segment_charts = {
                    "dietary": {
                        "labels": list(dietary_prefs.keys()),
                        "values": list(dietary_prefs.values()),
                    },
                    "weekdays": {
                        "labels": [day[0] for day in sorted_weekdays],
                        "values": [day[1] for day in sorted_weekdays],
                    },
                    "hours": {
                        "labels": [f"{hour[0]}:00" for hour in sorted_hours],
                        "values": [hour[1] for hour in sorted_hours],
                    },
                    "categories": {
                        "labels": [cat[0] for cat in selected_segment.sorted_categories[:10]],
                        "values": [
                            cat[1]["count"] for cat in selected_segment.sorted_categories[:10]
                        ],
                    },
                }

                context.update(
                    {
                        "selected_segment": selected_segment,
                        "customer_insights": customer_insights[:100],
                        "dietary_prefs": dietary_prefs,
                        "segment_charts": json.dumps(segment_charts, cls=DjangoJSONEncoder),
                    }
                )

            segments_comparison = {
                "labels": [segment.name for segment in segments],
                "customer_counts": [segment.customer_count for segment in segments],
                "avg_orders": [segment.avg_orders_per_customer for segment in segments],
                "avg_revenue": [float(segment.avg_revenue_per_customer) for segment in segments],
                "avg_check": [float(segment.avg_check) for segment in segments],
                "loyalty": [segment.loyalty_index for segment in segments],
                "churn_risk": [segment.churn_risk * 100 for segment in segments],
            }

            context.update(
                {
                    "segments": segments,
                    "segments_comparison": json.dumps(segments_comparison, cls=DjangoJSONEncoder),
                }
            )

        return context
