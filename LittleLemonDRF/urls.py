from django.urls import path
from . import views

urlpatterns = [
    path('menu-items/', views.MenuItemListView.as_view(), name='menu-items'),
    path('menu-items/<int:pk>/', views.MenuItemDetailView.as_view(), name='menu-item-detail'),
    path('groups/<str:group_name>/users/', views.UserGroupListView.as_view(), name='group-users'),
    path('groups/<str:group_name>/users/add/', views.AddUserToGroupView.as_view(), name='add-user-to-group'),
    path('groups/<str:group_name>/users/<int:user_id>/', views.RemoveUserFromGroupView.as_view(), name='remove-user-from-group'),
    path('cart/menu-items/', views.CartListView.as_view(), name='cart-menu-items'),
    path('cart/menu-items/clear/', views.CartDeleteView.as_view(), name='cart-clear'),
    path('orders/', views.OrderListView.as_view(), name='order-list'),
    path('orders/<int:pk>/', views.OrderDetailView.as_view(), name='order-detail'),
]
