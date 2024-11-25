"""main URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from django.views.decorators.csrf import csrf_exempt

from vcelerytaskrunner.views import TaskRunAPIView, TasksAPIView, TasksView, TaskRunFormView

urlpatterns = [
    path('admin/', admin.site.urls),

    path('accounts/', include('django.contrib.auth.urls')),

    path('tasks/', TasksView.as_view(), name="vcelery-tasks"),
    path('task_run/', TaskRunFormView.as_view(), name="vcelery-task-run"),


    path('api/tasks/', TasksAPIView.as_view(), name="vcelery-api-tasks"),
    # The following are not completed yet.
    # path('api/task_run/', csrf_exempt(TaskRunAPIView.as_view()), name="vcelery-api-task-run")
]
