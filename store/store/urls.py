from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path
from products import views
from django.contrib.auth import views as auth_views
from products.views import CustomPasswordResetView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('profile/', views.profile_view, name='profile'),
    path('deleteUser/', views.deleteUser_View, name='deleteUser'),
    path('confirm_deleteUser/', views.confirm_deleteUser_View, name='confirm_deleteUser'),
    path('updateAccount/', views.updateAccount_view, name='updateAccount'),
    path('', views.index, name='index'),
    path('product/<int:id>/', views.page_detail, name='page_detail'),
    path('about/', views.about, name='about'),
    path('base/', views.base, name='base'),
    path('listProducts/', views.listProducts, name='listProducts'),
    path('search_results/', views.search_results, name='search_results'),
    path('cart/', views.cart, name='cart'),
    path('add_to_cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('delete_product_of_cart/<int:product_id>/', views.delete_product_of_cart, name='delete_product_of_cart'), 
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('update_cart_quantity/<int:product_id>/', views.update_cart_quantity, name='update_cart_quantity'),
    path('my_orders/', views.user_orders, name='user_orders'),
    path('order_details/<int:order_id>/', views.order_details, name='order_details'),
    path('order/', views.order, name='order'),
    path('password_change/', auth_views.PasswordChangeView.as_view(), name='password_change'),
    path('password_change/done/', auth_views.PasswordChangeDoneView.as_view(), name='password_change_done'),
    path('register/', views.register, name='register'),
    path('category/<int:category_id>/', views.products_by_category, name='products_by_category'),
    path('sales_statistics/', views.sales_statistics, name='sales_statistics'),
    path('update_profile_picture/', views.update_profile_picture, name='update_profile_picture'),
    path('edit_order/<int:order_id>/edit/', views.edit_order, name='edit_order'),
    path('order/delete_item/<int:product_id>/', views.delete_order_item, name='delete_order_item'),
    path('order/delete/<int:order_id>/', views.delete_order, name='delete_order'),
    path('password_reset/', CustomPasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    path('chatbot/response/', views.retrieve_response, name='retrieve_response'),
    path('chatbot/', views.chatbot_view, name='chatbot'),
    path('update_delivery_address/', views.update_delivery_address, name='update_delivery_address'),
    path('payment_success/', views.payment_success, name='payment_success'),
]

# Configuration pour servir les fichiers médias en mode DEBUG
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
