from json import JSONDecodeError
from decimal import Decimal

import requests
import yaml
from celery.utils.log import get_task_logger
from requests.exceptions import SSLError
from yaml.parser import ParserError
from yaml.scanner import ScannerError
from yaml.reader import ReaderError

from ..choices import DesignRuleChoices
from .dr_20200117 import run_20200117_api_09, run_20200117_api_51
from .dr_20200709 import (
    run_20200709_api_03, run_20200709_api_16, run_20200709_api_20, run_20200709_api_48,
    run_20200709_api_51, run_20200709_api_56, run_20200709_api_57
)

logger = get_task_logger(__name__)


def _get_endpoint(enpoint):
    try:
        response = requests.get(enpoint, verify=False, timeout=60)
    except SSLError:
        response = None
    except Exception:
        response = None
    return response


def _get_response(session, json_endpoint, yaml_endpoint, is_json):
    response = _get_endpoint(json_endpoint)
    print("json_endpoint", json_endpoint, response)
    if response and response.ok:
        try:
            session.json_result = response.json()
            is_json = True
        except JSONDecodeError:
            pass

    if not session.json_result:
        response = _get_endpoint(yaml_endpoint)
        print("yaml_endpoint", yaml_endpoint, response)
        if response and response.ok:
            try:
                yaml_dict = yaml.safe_load(response.text)
                if isinstance(yaml_dict, dict):
                    session.json_result = yaml_dict
            except ScannerError:
                pass
            except ParserError:
                pass
            except ReaderError:
                pass
            except Exception as e:
                logger.exception(e)

    return session, response, is_json


def run_tests(session, api_endpoint, specification_url=""):
    json_endpoint = "{}/openapi.json".format(api_endpoint)
    yaml_endpoint = "{}/openapi.yaml".format(api_endpoint)
    is_json = False
    correct_location = True

    session, response, is_json = _get_response(session, json_endpoint, yaml_endpoint, is_json)

    # If specification_url was provided, try that
    if not session.json_result and specification_url:
        correct_location = False
        session, response, is_json = _get_response(session, specification_url, specification_url, is_json)

    # Failback for getting the base endpoint
    if not session.json_result:
        correct_location = False
        session, response, is_json = _get_response(session, api_endpoint, api_endpoint, is_json)

    success_count = 0
    for test_option in session.test_version.test_rules.all():
        if test_option.rule_type == DesignRuleChoices.api_03_20200709:
            result = run_20200709_api_03(session=session)
            if result.success:
                success_count += 1
        if test_option.rule_type == DesignRuleChoices.api_09_20200117:
            result = run_20200117_api_09(session=session)
            if result.success:
                success_count += 1
        if test_option.rule_type == DesignRuleChoices.api_16_20200709:
            result = run_20200709_api_16(session=session)
            if result.success:
                success_count += 1
        if test_option.rule_type == DesignRuleChoices.api_20_20200709:
            result = run_20200709_api_20(session=session, api_endpoint=api_endpoint)
            if result.success:
                success_count += 1
        if test_option.rule_type == DesignRuleChoices.api_48_20200709:
            result = run_20200709_api_48(session=session, api_endpoint=api_endpoint)
            if result.success:
                success_count += 1
        if test_option.rule_type == DesignRuleChoices.api_51_20200117:
            result = run_20200117_api_51(session=session, api_endpoint=api_endpoint, is_json=is_json)
            if result.success:
                success_count += 1
        if test_option.rule_type == DesignRuleChoices.api_51_20200709:
            result = run_20200709_api_51(session=session, response=response, correct_location=correct_location, is_json=is_json)
            if result.success:
                success_count += 1
        if test_option.rule_type == DesignRuleChoices.api_56_20200709:
            result = run_20200709_api_56(session=session)
            if result.success:
                success_count += 1
        if test_option.rule_type == DesignRuleChoices.api_57_20200709:
            result = run_20200709_api_57(session=session, response=response)
            if result.success:
                success_count += 1

    max_score = Decimal(session.test_version.test_rules.count())
    session.percentage_score = Decimal(100) / max_score * success_count
    session.save()
