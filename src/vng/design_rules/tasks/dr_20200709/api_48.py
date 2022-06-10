from django.utils.translation import ugettext_lazy as _

import requests

from ...choices import DesignRuleChoices

VALID_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE"]
SKIPPED_METHODS = ["PARAMETERS"]


def run_20200709_api_48(session, api_endpoint):
    """
    https://publicatie.centrumvoorstandaarden.nl/api/adr/#api-48
    """
    from ...models import DesignRuleResult

    # We do not want double results for the same design rule
    base_qs = session.results.filter(rule_type=DesignRuleChoices.api_48_20200709)
    if base_qs.exists():
        return base_qs.first()

    result = DesignRuleResult(design_rule=session, rule_type=DesignRuleChoices.api_48_20200709)

    # Only execute when there is a JSON response
    if not session.json_result:
        result.success = False
        result.errors = [_("The API did not give a valid JSON output.")]
        result.save()
        return result

    paths = session.json_result.get("paths", {})
    paths_found = False
    errors = []
    for path, _methods in paths.items():
        paths_found = True
        if path.endswith('/'):
            errors.append(_("Path: {} ends with a slash").format(path))
        else:
            for method, _oparations in _methods.items():
                # print(method)
                if method == "get":
                    response = requests.get("{}{}/".format(api_endpoint, path), verify=False, timeout=60)
                elif method == "post":
                    response = requests.post("{}{}/".format(api_endpoint, path), verify=False, timeout=60)
                elif method == "put":
                    response = requests.put("{}{}/".format(api_endpoint, path), verify=False, timeout=60)
                elif method == "delete":
                    response = requests.delete("{}{}/".format(api_endpoint, path), verify=False, timeout=60)
                else:
                    response = None

                if response and response.status_code != 404:
                    errors.append(_("Path: {}/ with a slash at the end did not result in a 404. it resulted in a {}").format(path, response.status_code))

    if not paths_found:
        result.success = False
        result.errors = [_("There are no paths found")]
    elif errors:
        result.success = False
        result.errors = errors
    else:
        result.success = True
    result.save()
    return result
