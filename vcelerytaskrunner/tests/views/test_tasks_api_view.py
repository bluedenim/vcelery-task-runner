from typing import Any, Optional
from vcelerytaskrunner.tests.views.test_task_runs import RunTaskTestCase


class TasksAPIViewTests(RunTaskTestCase):

    def test_get_tasks_with_parameters_count_for_me(self):
        response = self.client.get("/api/tasks/")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('tasks', data)
        self.assertIn('total_count', data)
        
        # The "count_for_me" task should be returned with its parameters
        task_name = "vcelerydev.tasks.count_for_me"
        count_for_me: Optional[dict[str, Any]] = next(
            (task for task in data['tasks'] if task['name'] == task_name),
            None
        )
        self.assertIsNotNone(count_for_me)

        assert count_for_me is not None        
        self.assertEqual(count_for_me["name"], task_name)
        self.assertTrue(count_for_me["runnable"])
        self.assertIsNotNone(count_for_me["task_run_url"])
        
        # Expect the 3 parameters: my_name, count_to, step
        parameters: list[dict[str, Any]] = count_for_me["parameters"]
        
        for param in parameters:
            if param["name"] == "my_name":
                self.assertEqual(param["type_info"], "str")
                self.assertFalse(param["is_base_model"])
                self.assertIsNone(param["json_schema"])
                self.assertIsNone(param["default"])
            elif param["name"] == "count_to":
                self.assertEqual(param["type_info"], "int")
                self.assertFalse(param["is_base_model"])
                self.assertIsNone(param["json_schema"])
                self.assertIsNone(param["default"])
            elif param["name"] == "step":
                self.assertEqual(param["type_info"], "int")
                self.assertFalse(param["is_base_model"])
                self.assertIsNone(param["json_schema"])
                self.assertEqual(param["default"], 1)
            else:
                self.fail(f"Unexpected parameter: {param['name']}")

    def test_get_tasks_with_parameters_process_incoming_payment(self):
        response = self.client.get("/api/tasks/")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('tasks', data)
        self.assertIn('total_count', data)
        
        # The "process_incoming_payment" task should be returned with its parameters
        task_name = "vcelerydev.tasks.process_incoming_payment"
        process_incoming_payment_task: Optional[dict[str, Any]] = next(
            (task for task in data['tasks'] if task['name'] == task_name),
            None
        )
        self.assertIsNotNone(process_incoming_payment_task)

        assert process_incoming_payment_task is not None        
        self.assertEqual(process_incoming_payment_task["name"], task_name)
        self.assertTrue(process_incoming_payment_task["runnable"])
        self.assertIsNotNone(process_incoming_payment_task["task_run_url"])
        
        # Expect the 2 parameters: payer, payment
        parameters: list[dict[str, Any]] = process_incoming_payment_task["parameters"]
        
        for param in parameters:
            if param["name"] == "payer":
                self.assertEqual(param["type_info"], "str")
                self.assertFalse(param["is_base_model"])
                self.assertIsNone(param["json_schema"])
                self.assertIsNone(param["default"])
            elif param["name"] == "payment":
                self.assertEqual(param["type_info"], "Payment")
                self.assertTrue(param["is_base_model"])
                
                json_schema = param["json_schema"]
                # {
                #  '$defs': {
                #    'PaymentMethod': {
                #      'description': 'Different payment methods we support',
                #      'enum': ['CASH', 'CREDIT_CARD', 'DEBIT_CARD', 'COMP'], 
                #      'title': 'PaymentMethod',
                #      'type': 'string'
                #    }
                #  }, 
                #  'description': 'A payment DTO', 
                #  'properties': {
                #    'amount': {'exclusiveMinimum': 0, 'title': 'Amount', 'type': 'integer'}, 
                #    'method': {'$ref': '#/$defs/PaymentMethod'}, 
                #    'payment_dt': {'format': 'date-time', 'title': 'Payment Dt', 'type': 'string'}
                #  }, 
                #  'required': ['amount', 'method', 'payment_dt'], 
                #  'title': 'Payment', 'type': 'object'
                # }
                self.assertIsNotNone(json_schema)

                self.assertIsNone(param["default"])
            else:
                self.fail(f"Unexpected parameter: {param['name']}")