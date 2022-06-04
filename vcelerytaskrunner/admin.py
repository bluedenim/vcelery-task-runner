from django.contrib import admin

from vcelerytaskrunner.models import TaskRunRecord


class TaskRunRecordAdmin(admin.ModelAdmin):
    readonly_fields = ('task_name', 'task_id', 'run_by', 'run_with')
    list_display  = ('id', 'task_name', 'task_id', 'run_by', 'created_at')
    search_fields = ['=task_name', '=run_by__username']

    def has_add_permission(self, request, obj=None):
        return False


admin.site.register(TaskRunRecord, TaskRunRecordAdmin)

