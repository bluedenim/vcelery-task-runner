from django.contrib import admin

from vcelerytaskrunner.models import TaskRunRecord


class TaskRunRecordAdmin(admin.ModelAdmin):
    readonly_fields = ('task_name', 'task_id', 'run_by', 'run_with')
    list_display  = ('id', 'task_name', 'task_id', 'run_by', 'created_at')
    search_fields = ['=task_name', '=run_by__username']

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions


admin.site.register(TaskRunRecord, TaskRunRecordAdmin)
