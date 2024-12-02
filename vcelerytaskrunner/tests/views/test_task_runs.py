import json

from django.test import TestCase

from django.contrib.auth.models import User
from django.http.response import HttpResponse
from django.test import Client
from django.urls import reverse


TASK_RUN_URL = reverse("vcelery-task-run")


# Run tests here by:
#     python manage.py test --settings=main.test_settings vcelerytaskrunner


class RunTaskTestCase(TestCase):

    def setUp(self):
        self.user = User.objects.create(
            username="testuser", email="testuser@therealvan.com", is_superuser=True)

        self.client = Client()
        self.client.force_login(self.user)

    def _run_task(self, task_name: str, **params) -> HttpResponse:
        data = {}
        data.update(**params)
        data["task"] = task_name

        return self.client.post(
            TASK_RUN_URL,
            data,
        )

class CountForMeTests(RunTaskTestCase):

    def setUp(self):
        super().setUp()
        self.my_name = "Alan Smithee"
        self.count_to = 10

    def test_default_step(self):
        response = self._run_task(
            "vcelerydev.tasks.count_for_me",
            my_name=self.my_name,
            count_to=self.count_to
        )
        self.assertTrue("task_id" in response.cookies)

    def test_explicit_step(self):
        response = self._run_task(
            "vcelerydev.tasks.count_for_me",
            my_name=self.my_name,
            count_to=self.count_to,
            step=2,
        )
        self.assertTrue("task_id" in response.cookies)


class LegacyTaskTests(RunTaskTestCase):

    def test_call(self):
        response = self._run_task("vcelerydev.tasks.legacy_task", a_name="Alan Smithee", an_integer=6)
        self.assertTrue("task_id" in response.cookies)

    def test_call_with_str(self):
        # Since the params don't have type hints, the params will be passed as str
        response = self._run_task("vcelerydev.tasks.legacy_task", a_name="Alan Smithee", an_integer="six")
        self.assertTrue("task_id" in response.cookies)


class ProcessDictsTests(RunTaskTestCase):

    def test_call(self):
        items_json = json.dumps({
            "items": {
                "one": [1, 3, 5],
                "two": [2, 4, 6],
            }
        })
        response = self._run_task("vcelerydev.tasks.process_dicts", items=items_json)
        self.assertTrue("task_id" in response.cookies)


class ProcessIncomingPaymentTests(RunTaskTestCase):

    def test_call(self):

        # This should pass the Payment.model_validate_json(...) processing
        payment_json = json.dumps({
            "amount": 446,
            "method": "CASH",
            "payment_dt": "2024-11-30T23:17:00-08:00",
        })
        response = self._run_task(
            "vcelerydev.tasks.process_incoming_payment",
            payer="Alan Smithee",
            payment=payment_json,
        )
        self.assertTrue("task_id" in response.cookies)


class ProcessListsTests(RunTaskTestCase):

    def test_call(self):
        integers = json.dumps([1, 2, 3, 4, 5])
        strings = json.dumps(["one", "two", "three"])
        response = self._run_task(
            "vcelerydev.tasks.process_lists",
            integers=integers,
            strings=strings,
        )
        self.assertTrue("task_id" in response.cookies)


class SayHelloTests(RunTaskTestCase):

    def test_default_name(self):
        response = self._run_task("vcelerydev.tasks.say_hello")
        self.assertTrue("task_id" in response.cookies)


    def test_explicit_name(self):
        response = self._run_task("vcelerydev.tasks.say_hello", to_name="Alan Smithee")
        self.assertTrue("task_id" in response.cookies)


class TaskWithAnnotatedParamTests(RunTaskTestCase):

    def test_call(self):
        response = self._run_task("vcelerydev.tasks.task_with_annotated_param", annotated_var=45)
        self.assertTrue("task_id" in response.cookies)


class ToTimezoneTests(RunTaskTestCase):

    def test_default_tz(self):
        dt = "2024-11-30T23:28:15-00:00"
        response = self._run_task("vcelerydev.tasks.to_timezone", dt=dt)
        self.assertTrue("task_id" in response.cookies)

    def test_explicit_tz(self):
        dt = "2024-11-30T23:28:15-00:00"
        to_tz = "America/New_York"
        response = self._run_task("vcelerydev.tasks.to_timezone", dt=dt, to_tz=to_tz)
        self.assertTrue("task_id" in response.cookies)

    def test_explicit_utc_tz(self):
        dt = "2024-11-30T23:28:15Z"
        to_tz = "America/New_York"
        response = self._run_task("vcelerydev.tasks.to_timezone", dt=dt, to_tz=to_tz)
        self.assertTrue("task_id" in response.cookies)
