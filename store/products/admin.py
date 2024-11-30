from django.contrib import admin
from .models import UserProfile 
from .models import Category, Product, Order, OrderItem, Cart, CartItem

# Enregistrement des modèles de ton application
admin.site.register(Category)
admin.site.register(Product)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(Cart)
admin.site.register(CartItem)
admin.site.register(UserProfile)

