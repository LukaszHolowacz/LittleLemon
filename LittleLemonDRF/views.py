from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User, Group
from .models import MenuItem, Cart, Order, OrderItem
from .serializers import MenuItemSerializer, CartSerializer, OrderSerializer, OrderItemSerializer

class IsManager(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.groups.filter(name='Manager').exists()
    
    
class IsDeliveryCrew(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.groups.filter(name='Delivery Crew').exists()
    

class MenuItemListView(generics.ListCreateAPIView):
    queryset = MenuItem.objects.all()
    serializer_class = MenuItemSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsManager()]  
        return [permissions.AllowAny()] 

class MenuItemDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = MenuItem.objects.all()
    serializer_class = MenuItemSerializer

    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [IsAuthenticated(), IsManager()]
        return [permissions.AllowAny()] 

class UserGroupListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsManager]

    def get_queryset(self):
        group_name = self.kwargs['group_name']
        return User.objects.filter(groups__name=group_name)

    def list(self, request, *args, **kwargs):
        users = self.get_queryset()
        return Response([{"id": user.id, "username": user.username} for user in users])

class AddUserToGroupView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated, IsManager]

    def post(self, request, group_name):
        user_id = request.data.get("user_id")
        try:
            user = User.objects.get(id=user_id)
            group, created = Group.objects.get_or_create(name=group_name)
            user.groups.add(group)
            return Response({"message": f"User {user.username} added to {group_name} group"}, status=status.HTTP_201_CREATED)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

class RemoveUserFromGroupView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated, IsManager]

    def delete(self, request, group_name, user_id):
        try:
            user = User.objects.get(id=user_id)
            group = Group.objects.get(name=group_name)
            user.groups.remove(group)
            return Response({"message": f"User {user.username} removed from {group_name} group"}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        except Group.DoesNotExist:
            return Response({"error": "Group not found"}, status=status.HTTP_404_NOT_FOUND)


class CartListView(generics.ListCreateAPIView):
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        menu_item_id = self.request.data.get("menuitem_id")  

        menu_item = get_object_or_404(MenuItem, id=menu_item_id)

        serializer.save(
            user=self.request.user, 
            menuitem=menu_item, 
            unit_price=menu_item.price, 
            price=menu_item.price * int(self.request.data.get("quantity", 1))
        )


class CartDeleteView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, *args, **kwargs):
        Cart.objects.filter(user=request.user).delete()
        return Response({"message": "Cart cleared successfully"}, status=status.HTTP_204_NO_CONTENT)
    

class OrderListView(generics.ListCreateAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.groups.filter(name='Manager').exists():
            return Order.objects.all()  
        elif self.request.user.groups.filter(name='Delivery Crew').exists():
            return Order.objects.filter(delivery_crew=self.request.user) 
        return Order.objects.filter(user=self.request.user)  

    def perform_create(self, serializer):
        cart_items = Cart.objects.filter(user=self.request.user)
        if not cart_items.exists():
            return Response({"error": "Cart is empty"}, status=status.HTTP_400_BAD_REQUEST)

        total_price = sum(item.price for item in cart_items)
        order = serializer.save(user=self.request.user, total=total_price)

        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                menuitem=item.menuitem,
                quantity=item.quantity,
                unit_price=item.unit_price,
                price=item.price
            )

        cart_items.delete() 
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


class OrderDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.groups.filter(name='Manager').exists():
            return Order.objects.all()
        elif self.request.user.groups.filter(name='Delivery Crew').exists():
            return Order.objects.filter(delivery_crew=self.request.user)
        return Order.objects.filter(user=self.request.user)

    def update(self, request, *args, **kwargs):
        order = get_object_or_404(Order, id=kwargs['pk'])
        
        if self.request.user.groups.filter(name='Manager').exists():
            serializer = self.get_serializer(order, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
        
        if self.request.user.groups.filter(name='Delivery Crew').exists():
            if 'status' in request.data:
                order.status = request.data['status']
                order.save()
                return Response(OrderSerializer(order).data)
            return Response({"error": "Only status update allowed"}, status=status.HTTP_403_FORBIDDEN)

        return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        if self.request.user.groups.filter(name='Manager').exists():
            order = get_object_or_404(Order, id=kwargs['pk'])
            order.delete()
            return Response({"message": "Order deleted"}, status=status.HTTP_204_NO_CONTENT)
        return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)