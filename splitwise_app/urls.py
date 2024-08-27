from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('add_user/', views.add_user, name='add_user'),
    path('add_expense/', views.add_expense, name='add_expense'),
    path('show_balances/', views.show_balances, name='show_balances'),
    path('calculate_owe_details/', views.calculate_owe_details, name='calculate_owe_details'),
    path('show_expense_details/', views.show_expense_details, name='show_expense_details'),
    path('show_totals_for_user/', views.show_totals_for_user, name='show_totals_for_user'),
    path('clear_all_dues/', views.clear_all_dues, name='clear_all_dues'),
]
