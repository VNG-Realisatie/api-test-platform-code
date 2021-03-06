import os
import json

from django.test import TestCase
from django.utils.translation import ugettext_lazy as _

from vng.design_rules.tasks.dr_20200709 import run_20200709_api_03

from ...factories import DesignRuleResultFactory, DesignRuleSessionFactory
from ....choices import DesignRuleChoices
from ....models import DesignRuleResult


class Api03Tests(TestCase):
    def test_design_rule_already_exists(self):
        session = DesignRuleSessionFactory(test_suite__api_endpoint="https://maykinmedia.nl/")
        pre_result = DesignRuleResultFactory(design_rule=session, rule_type=DesignRuleChoices.api_03_20200709)

        result = run_20200709_api_03(session)
        self.assertEqual(DesignRuleResult.objects.count(), 1)
        self.assertEqual(pre_result.pk, result.pk)

    def test_no_json_provided(self):
        session = DesignRuleSessionFactory(test_suite__api_endpoint="https://maykinmedia.nl/")

        result = run_20200709_api_03(session)
        self.assertEqual(DesignRuleResult.objects.count(), 1)
        self.assertFalse(result.success)
        self.assertEqual(result.errors, [_("The API did not give a valid JSON output.")])

    def test_successful_methods(self):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(dir_path, "..", "files", "good.json")) as json_file:
            session = DesignRuleSessionFactory(test_suite__api_endpoint="https://maykinmedia.nl/", json_result=json.loads(json_file.read()))

        result = run_20200709_api_03(session)
        self.assertEqual(DesignRuleResult.objects.count(), 1)
        self.assertTrue(result.success)
        self.assertEqual(result.errors, None)

    def test_wrong_method(self):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(dir_path, "..", "files", "wrong_method.json")) as json_file:
            session = DesignRuleSessionFactory(test_suite__api_endpoint="https://maykinmedia.nl/", json_result=json.loads(json_file.read()))

        result = run_20200709_api_03(session)
        errors = [
            _("not supported method, {}, found for path {}").format("method", "/designrule-session"),
            _("not supported method, {}, found for path {}").format("getget", "/designrule-session/{id}"),
        ]
        self.assertEqual(DesignRuleResult.objects.count(), 1)
        self.assertFalse(result.success)
        self.assertEqual(result.errors, errors)

    def test_no_methods(self):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(dir_path, "..", "files", "no_paths.json")) as json_file:
            session = DesignRuleSessionFactory(test_suite__api_endpoint="https://maykinmedia.nl/", json_result=json.loads(json_file.read()))

        result = run_20200709_api_03(session)
        self.assertEqual(DesignRuleResult.objects.count(), 1)
        self.assertFalse(result.success)
        self.assertEqual(result.errors, [_("There are no methods found.")])
