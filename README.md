# Van's Celery Task Runner

This set of tools will present a UI to:
- search Celery tasks.
- start Celery tasks with parameters.
- Journaling of who ran what tasks.

## Autodiscovery of Runnable Tasks
<img width="915" alt="tasks_list" src="https://github.com/user-attachments/assets/9f3fa308-8b50-4412-a172-f813348107df">

## Task Running Form
<img width="1110" alt="task_run_form" src="https://github.com/user-attachments/assets/57c6c6f4-c72d-4c21-8a04-8975caa976c3">


Optional controls:

- Whitelisting task names to only surface a subset of the tasks
- Django permission control around who can see and run tasks

## Run Result
![run_result_task_id](https://github.com/user-attachments/assets/5e4f0091-b109-4d55-b780-c3919d8fd5af)


## Demo
### Set Up for Demo
- Install Docker & Compose
- Build:
  ```
  docker compose build
  ...
  ```
- Initialize DB
  ```
  docker compose run --rm --service-ports app /bin/bash
  ...
  python manage.py migrate
  ```
- Create a user to test with
  ```
  docker compose run --rm --service-ports app /bin/bash
  ...
  python manage.py createsuperuser
  ...
  ```

  Write down the credentials. You will use them in the following steps.

### See Tasks
- Start the `app` service. This is the Web app with UI to see and invoke Celery tasks.
  ```
  docker compose run --rm --service-ports app /bin/bash
  ...
  python manage.py runserver 0.0.0.0:8000
  ```
- Go to http://localhost:8000/tasks. Sign in with the credentials created above.

- This will show the known Celery tasks. BUT to run them, proceed with the step below.

### Run Tasks
- Start a new Terminal.
- To run tasks, start the `celery` service in the new terminal:
  ```
  docker compose up celery
  ...
  ```
  ** NOTE: **both** `app` and `celery` services need to be running.

- Now you can use the UI (http://localhost:8000/tasks) to run tasks. You should be able to see the task logs in the `celery` app.

## Installation (into Your Project)

- Install the package: `pip install vcelery-task-runner`
- Add into your project's `settings.py`:
  ```
  INSTALLED_APPS = [
      ...
      'rest_framework',
      'vcelerytaskrunner.apps.AppConfig',
  ]
  ```
  vcelery-task-runner uses the Django REST Library
- Run migration for the vcelerytaskrunner app:
  ```
  python manage.py migrate vcelerytaskrunner
  ```
- In `settings.py`, let **vcelery-task-runner** know your Celery app:
  ```
  # For example: from proj.celery import app as celery_app
  from celery import Celery
  
  from ... import app as celery_app
  
  assert isinstance(celery_app, Celery)
  
  # celery_app is a reference to your project's Celery app instance
  VCELERY_TASKRUN_CELERY_APP = celery_app
  ```
- Optionally in `settings.py`, set the maximum age of run records to keep around (more about this [below](#taskrunrecords)).
  ```
  VCELERY_TASK_RUN_RECORD_LONGEVITY = timedelta(weeks=52)  # Or however long you want to keep records of task runs
  ```

## Configuration

### Runnable Tasks

#### VCELERY_TASKRUN_RUNNABLE_TASKS
By default, all tasks are "runnable" in the UI. However, if you wan to restrict
visibility to only a subset of the tasks, add into the project's `settings.py`:

```
VCELERY_TASKRUN_RUNNABLE_TASKS = {
    "vcelerydev.tasks.say_hello",  # full name of task
}
```

If you set up an empty set, NOTHING will be runnable (quick way to disable the run operation):

```
VCELERY_TASKRUN_RUNNABLE_TASKS = {
}
```

#### VCELERY_SHOW_ONLY_RUNNABLE_TASKS
Also by default, tasks not included in `VCELERY_TASKRUN_RUNNABLE_TASKS` will not be runnable but will be displayed in
the list of tasks. If that is undesired, set the `VCELERY_SHOW_ONLY_RUNNABLE_TASKS` to `True`:

If set, then only runnable tasks are shown in the UI:
```
# Tasks not in VCELERY_TASKRUN_RUNNABLE_TASKS will not be displayed in the task list
VCELERY_SHOW_ONLY_RUNNABLE_TASKS = True
```

### UI

There is a set of pages ready to list/search task by name and to run tasks. To add them
to you app, add these entries into your main `urls.py`:

```
from django.urls import path
...
from vcelerytaskrunner.views import TasksAPIView, TasksView, TaskRunFormView

...

urlpatterns = [
    ...
    path('tasks/', TasksView.as_view(), name="vcelery-tasks"),
    path('task_run/', TaskRunFormView.as_view(), name="vcelery-task-run"),

    path('api/tasks/', TasksAPIView.as_view(), name="vcelery-api-tasks"),
    ....
]
```

The actual URL paths may vary according to your project's / app's needs. However, the names MUST be as shown because
there are code that look up the views by name (e.g. `django.urls.reverse("vcelery-task-run")`), and they will fail 
if you don't use the names shown here.

The view classes obviously have to be the ones shown. Although if you looked at the code and have done so carefully,
you may derive from the views to specialize them as needed.


### Permissions

By default, only staff users have access to the UI. To add more users to the UI:

- Add the permission `vcelerytaskrunner.view_taskrunrecord` to allow a user to view the initial page (listing of tasks).
- Add ALSO the permission `vcelerytaskrunner.add_taskrunrecord` to allow a user to run a runnable task.

You are free to use groups to set this up.

## TaskRunRecords

Each run of a task through the UI is recorded into the model `vcelerytaskrunner.models.TaskRunRecord`:

![task_run_record_list](https://github.com/user-attachments/assets/8ecf1e9b-b30e-4538-997a-c2e528283b24)

![task_run_record](https://github.com/user-attachments/assets/94d2620d-d990-46c6-9592-b10ef9383955)



### Pruning old records

Since each run is recorded, over time this table will grow large. Therefore, the `VCELERY_TASK_RUN_RECORD_LONGEVITY`
setting is used to define the longevity of these records. 

Each time the **vcelerytaskrunner** app is initialized:
- a query is made to find `TaskRunRecord`s created before `datetime.utcnow() - VCELERY_TASK_RUN_RECORD_LONGEVITY`
- records older than this datetime **will be removed**.

If you don't explicitly define `VCELERY_TASK_RUN_RECORD_LONGEVITY` in your settings, the default value 
`timedelta(weeks=4)` will be used, meaning entries older than 4 weeks will be removed.

#### Permanent records

If you want to keep TaskRunRecords forever (or clean them up manually), then set `VCELERY_TASK_RUN_RECORD_LONGEVITY` to 
`"PERMANENT"`:

```
# Don't try to prune old TaskRunRecords
VCELERY_TASK_RUN_RECORD_LONGEVITY = "PERMANENT"
```

## TaskRunSignal

To be notified when a task is run, subscribe to the `TaskRunSignal` signal from `TaskRunner` from the module
`vcelerytaskrunner.services.task_runner`:

```
from vcelerytaskrunner.services.task_runner import TaskRunSignal, TaskRunner

...

@receiver(TaskRunSignal, sender=TaskRunner)
def task_run_listener(sender, **kwargs):
    """
    Example of a signal handler for task run events.
    """
    task_name = kwargs['task_name']
    task_id = kwargs['task_id']
    task_run_args = kwargs['args']
    task_run_kwargs = kwargs['kwargs']
    user = kwargs.get('user')

    logger.info(
        f"task_run_listener: task {task_name} (ID {task_id}) run by {user}"
        f" with args={task_run_args}, kwargs={task_run_kwargs}"
    )
```
