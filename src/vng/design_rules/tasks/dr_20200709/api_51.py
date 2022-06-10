from urllib.parse import urlparse

from django.utils.translation import ugettext_lazy as _

from ...choices import DesignRuleChoices

VALID_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE"]
SKIPPED_METHODS = ["PARAMETERS"]


def run_20200709_api_51(session, response, correct_location=False, is_json=False):
    """
    https://publicatie.centrumvoorstandaarden.nl/api/adr/#api-51
    """
    from ...models import DesignRuleResult

    # We do not want double results for the same design rule
    base_qs = session.results.filter(rule_type=DesignRuleChoices.api_51_20200709)
    if base_qs.exists():
        return base_qs.first()

    result = DesignRuleResult(design_rule=session, rule_type=DesignRuleChoices.api_51_20200709)

    # Only execute when there is a JSON response
    if not session.json_result:
        result.success = False
        result.errors = [_("The API did not give a valid JSON output.")]
        result.save()
        return result

    errors = []
    if not correct_location:
        errors.append(_("The OAS file was not found at /openapi.json or at /openapi.yaml"))

    if not is_json:
        errors.append(_("The API did not give a valid JSON output. It most likely was YAML"))

    cors_headers = response.headers.get("Access-Control-Allow-Origin")
    if cors_headers:
        parsed_url = urlparse(response.url)
        host = "{}://{}".format(parsed_url.scheme, parsed_url.netloc)
        if cors_headers in [host, "{}/".format(host)]:
            errors.append(_("The CORS headers only allow the requested domain. Please make sure that it can be loaded from outside the domain"))

    result.success = True

    if errors:
        result.success = False
        result.errors = errors

    result.save()
    return result
