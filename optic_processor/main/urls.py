from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name= 'home'),
    path('logout/', views.logout_user, name= 'logout_user'),
    path('register/', views.register_user, name= 'register'),
    path('serve-image/', views.serve_image, name='serve_image'),
    path('process_image/', views.process_image, name='process_image'),
    path('image_process_results/', views.image_process_results, name='image_process_results'),

]