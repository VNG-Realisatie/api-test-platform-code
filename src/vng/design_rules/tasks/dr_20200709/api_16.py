from django.utils.translation import ugettext_lazy as _

from ...choices import DesignRuleChoices


def run_20200709_api_16(session):
    """
    https://publicatie.centrumvoorstandaarden.nl/api/adr/#api-16
    """
    from ...models import DesignRuleResult

    # We do not want double results for the same design rule
    base_qs = session.results.filter(rule_type=DesignRuleChoices.api_16_20200709)
    if base_qs.exists():
        return base_qs.first()

    result = DesignRuleResult(design_rule=session, rule_type=DesignRuleChoices.api_16_20200709)

    # Only execute when there is a JSON response
    if not session.json_result:
        result.success = False
        result.errors = [_("The API did not give a valid JSON output.")]
        result.save()
        return result

    version = session.json_result.get("openapi", session.json_result.get("swagger"))
    if not version:
        result.success = False
        result.errors = [_("There is no openapi version found.")]
        result.save()
        return result

    try:
        split_version = version.split('.')
        major_int = int(split_version[0])
        _minor_int = int(split_version[1])
        _bug_int = int(split_version[2])

        if major_int >= 3:
            result.success = True
        else:
            result.success = False
            result.errors = [_("The version ({}) is not higher than or equal to OAS 3.0.0").format(version)]
    except Exception as e:
        result.success = False
        result.errors = [_("{} is not a valid OAS api version.").format(version)]
    finally:
        result.save()
        return result
