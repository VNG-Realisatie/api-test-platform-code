import factory
from factory.django import DjangoModelFactory as Dmf
from django.utils import timezone
from django.conf import settings
from filer.models import File

from vng.accounts.models import User

from ..models import (
    SessionType, Session, ScenarioCaseCollection, ScenarioCase, VNGEndpoint, ExposedUrl,
    SessionLog, TestSession, QueryParamsScenario, InjectHeader
)
from ...servervalidation.tests.factories import APIFactory
from ...utils import choices
from ...utils.factories import UserFactory


class SessionTypeFactory(Dmf):

    class Meta:
        model = SessionType

    name = factory.sequence(lambda n: 'testype {}'.format(n))
    standard = 'Stardard'
    role = 'Role'
    application = 'Application'
    version = '1.2.4'
    api = factory.SubFactory(APIFactory)


class TestSessionFactory(Dmf):

    class Meta:
        model = TestSession

    test_result = factory.django.FileField(filename='testsession')
    json_result = factory.django.FileField(filename='testsession')


class FilerField(Dmf):
    class Meta:
        model = File

    file = factory.django.FileField(from_path=settings.POSTMAN_ROOT + '/google-variable.postman_collection.json')


class ScenarioCaseCollectionFactory(Dmf):

    class Meta:
        model = ScenarioCaseCollection

    name = 'test collection'


class VNGEndpointFactory(Dmf):

    class Meta:
        model = VNGEndpoint

    name = factory.Sequence(lambda n: 'name{}'.format(n))
    url = 'https://test.openzaak.nl/documenten/api/v1'
    session_type = factory.SubFactory(SessionTypeFactory)
    test_file = factory.SubFactory(FilerField)
    scenario_collection = factory.SubFactory(ScenarioCaseCollectionFactory)


class VNGEndpointEchoFactory(Dmf):

    class Meta:
        model = VNGEndpoint

    name = factory.Sequence(lambda n: 'nameecho{}'.format(n))
    url = 'https://postman-echo.com/'
    session_type = factory.SubFactory(SessionTypeFactory)
    test_file = factory.SubFactory(FilerField)


class HeaderInjectionFactory(Dmf):

    class Meta:
        model = InjectHeader

    key = 'key'
    value = 'dummy'
    session_type = factory.SubFactory(SessionTypeFactory)


class VNGEndpointDockerFactory(Dmf):

    class Meta:
        model = VNGEndpoint

    name = factory.Sequence(lambda n: 'name_docker{}'.format(n))
    docker_image = 'maykinmedia/vng-demo-api:latest.db'
    session_type = factory.SubFactory(SessionTypeFactory)
    test_file = factory.SubFactory(FilerField)


class ScenarioCaseFactory(Dmf):

    class Meta:
        model = ScenarioCase

    url = 'unknown/23'
    http_method = choices.HTTPMethodChoices.GET
    collection = factory.SubFactory(ScenarioCaseCollectionFactory)


class QueryParamsScenarioFactory(Dmf):

    class Meta:
        model = QueryParamsScenario

    scenario_case = factory.SubFactory(ScenarioCaseFactory)
    name = 'tparam'
    expected_value = '*'


class SessionFactory(Dmf):

    class Meta:
        model = Session

    session_type = factory.SubFactory(SessionTypeFactory)
    started = timezone.now()
    status = choices.StatusChoices.starting
    user = factory.SubFactory(UserFactory)
    session_type = factory.SubFactory(SessionTypeFactory)
    name = factory.Sequence(lambda n: 'name{}'.format(n))


class ExposedUrlEchoFactory(Dmf):

    class Meta:
        model = ExposedUrl

    test_session = factory.SubFactory(TestSessionFactory)
    session = factory.SubFactory(SessionFactory)
    vng_endpoint = factory.SubFactory(VNGEndpointEchoFactory)
    subdomain = factory.Sequence(lambda n: 'tstecho{}'.format(n))


class ExposedUrlFactory(Dmf):

    class Meta:
        model = ExposedUrl

    test_session = factory.SubFactory(TestSessionFactory)
    session = factory.SubFactory(SessionFactory)
    vng_endpoint = factory.SubFactory(VNGEndpointFactory)
    subdomain = factory.Sequence(lambda n: 'tst{}'.format(n))


class SessionLogFactory(Dmf):

    class Meta:
        model = SessionLog

    date = timezone.now()
    session = factory.SubFactory(SessionFactory)
    request = '{"request": {"path": "GET http://localhost:8000/runtest/154513515134/", "body": "", "header":"header"}}'
    response = '{"response": {"status_code": 404, "body": "{}", "path": "{} http://localhost:8000/runtest/tst/unknown/23"}}'
    response_status = 404
