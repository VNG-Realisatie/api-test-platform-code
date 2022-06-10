import json
import uuid
import re
import time
import operator
import requests
import yaml
from functools import reduce

from tinymce.models import HTMLField

from django.forms import ValidationError
from django.conf import settings
from django.core.validators import RegexValidator
from django.core.files import File
from django.db import models
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

from ordered_model.models import OrderedModel

from filer.fields.file import FilerFileField

import vng.postman.utils as postman

from vng.accounts.models import User
from vng.postman.choices import ResultChoices
from vng.servervalidation.models import API

from ..utils import choices
from ..utils.auth import get_jwt


class SessionType(models.Model):

    name = models.CharField(_('Name'), max_length=200, unique=True, help_text=_(
        "The name of this session type"
    ))
    standard = models.CharField(_('Standard'), max_length=200, null=True)
    role = models.CharField(_('Role'), max_length=200, null=True)
    application = models.CharField(_('Application'), max_length=200, null=True, help_text=_(
        "The application for which this session type is relevant"
    ))
    version = models.CharField(_('Version'), max_length=200, null=True, help_text=_(
        "The version of this session type"
    ))
    authentication = models.CharField(
        max_length=20,
        default=choices.AuthenticationChoices.no_auth,
        choices=choices.AuthenticationChoices.choices,
        help_text=_("The type of authentication that is used for this session type")
    )
    description = HTMLField(help_text=_("The description of the session type"))
    client_id = models.TextField(default=None, null=True, blank=True, help_text=_(
        "If the authentication is set to `JWT`, this field will be used to create a JWT"
    ))
    secret = models.TextField(default=None, null=True, blank=True, help_text=_(
        "If the authentication is set to `JWT`, this field will be used to create a JWT"
    ))
    header = models.TextField(default=None, null=True, blank=True, help_text=_(
        "If the authentication is set to `Header`, the value of this field will be used to authenticate with"
    ))
    database = models.BooleanField(help_text='Check if the a postgres db is needed in the Kubernetes cluster', default=False)
    db_data = models.TextField(default=None, null=True, blank=True, help_text=_(
        "If specified for a session type using Docker, this data will be inserted into the database"
    ))
    ZGW_images = models.BooleanField(default=False, blank=True, help_text=_(
        "If enabled, the default Docker setup for the ZGW project will be used"
    ))
    active = models.BooleanField(blank=True, default=True, help_text=_(
        "Indicates whether this test scenario can be used via the web interface and the API"
    ))
    api = models.ForeignKey(API, on_delete=models.PROTECT, null=True, blank=True, help_text=_(
        "The API to which this session type belongs"
    ))

    class Meta:
        verbose_name = _('Session Type')
        verbose_name_plural = _('Sessions type')
        ordering = ('name',)

    def __str__(self):
        return self.name

    @property
    def scenario_cases(self):
        endpoints = self.vngendpoint_set.all()
        collection_ids = endpoints.values_list('scenario_collection')
        return ScenarioCase.objects.filter(collection__in=collection_ids)

    def add_auth_header(self):
        auth_header = self.injectheader_set.filter(key='Authorization').first()
        jwt_auth = get_jwt(self).credentials()['Authorization']
        if auth_header:
            auth_header.value = jwt_auth
            auth_header.save()
        else:
            InjectHeader.objects.create(
                session_type=self,
                key='Authorization',
                value=jwt_auth
            )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.ZGW_images:
            VNGEndpoint(name='ZRC', session_type=self).save()
            VNGEndpoint(name='NRC', session_type=self).save()
            VNGEndpoint(name='ZTC', session_type=self).save()
            VNGEndpoint(name='BRC', session_type=self).save()
            VNGEndpoint(name='DRC', session_type=self).save()
            VNGEndpoint(name='AC', session_type=self).save()
        if self.authentication == choices.AuthenticationChoices.jwt:
            if self.client_id and self.secret:
                self.add_auth_header()


class InjectHeader(models.Model):

    session_type = models.ForeignKey(SessionType, on_delete=models.CASCADE, help_text=_(
        "The session type in which this injected header is used"
    ))
    key = models.CharField(max_length=200, help_text=_("The name of the HTTP header to be injected"))
    value = models.TextField(help_text=_("The value of the HTTP header to be injected"))

    class Meta:
        unique_together = ('session_type', 'key')


class TestSession(models.Model):

    test_result = models.FileField(settings.MEDIA_FOLDER_FILES['testsession_log'], blank=True, null=True, default=None, help_text=_(
        "The HTML log generated by Newman"
    ))
    json_result = models.TextField(blank=True, null=True, default=None, help_text=_(
        "The JSON log generated by Newman"
    ))

    class Meta:
        verbose_name = _('Test Session')
        verbose_name_plural = _('Test Sessions')

    def save_test(self, file):
        name_file = str(uuid.uuid4())
        django_file = File(file)
        self.test_result.save(name_file, django_file)

    def save_test_json(self, file):
        text = file.read().replace('\n', '')
        self.json_result = text

    def display_test_result(self):
        if self.test_result:
            with open(self.test_result.path) as fp:
                return fp.read().replace('\n', '<br>')

    def is_success_test(self):
        if self.json_result is not None:
            return postman.get_outcome_json(self.json_result) == ResultChoices.success

    def get_json_obj(self):
        return postman.get_json_obj(self.json_result)


class ScenarioCaseCollection(models.Model):
    name = models.CharField(max_length=100, help_text=_("The name of the collection"))
    oas_link = models.URLField(blank=True, null=True, help_text=_(
        "Optional field that takes a URL to an OAS3 schema, automatically generating "
        "the scenario cases from this schema. Only works if no scenario cases are set manually"
    ))

    def __str__(self):
        return self.name

    def clean(self, *args, **kwargs):
        if not self.oas_link:
            return

        try:
            response = requests.get(self.oas_link, timeout=60)
        except requests.exceptions.ConnectionError as e:
            raise ValidationError({'oas_link': _("The URL did not resolve")})

        content = response.content

        # Translate yaml to Python dict if needed
        if self.oas_link.endswith('.yaml'):
            try:
                schema = yaml.load(content, Loader=yaml.FullLoader)
            except yaml.scanner.ScannerError:
                raise ValidationError({'oas_link': _("The URL does not point to a valid YAML file")})
        else:
            try:
                if isinstance(content, bytes):
                    content = content.decode('utf-8')
                schema = json.loads(content)
            except json.decoder.JSONDecodeError:
                raise ValidationError({'oas_link': _("The URL does not point to a valid JSON file")})


def get_parameter_from_ref(schema, ref_link):
    """
    Retrieve parameter information from a reference
    """

    # Only support local references
    if ref_link.startswith('#'):
        key_list = ref_link.split('/')[1:]
        return reduce(operator.getitem, key_list, schema)
    else:
        raise NotImplementedError()

@transaction.atomic()
@receiver(post_save, sender=ScenarioCaseCollection, dispatch_uid='create_cases_from_oas')
def create_cases_from_oas(sender, instance, **kwargs):
    # Only proceed if a link to OAS is provided and if the collection does not
    # have any ScenarioCases yet
    if not instance.oas_link or instance.scenariocase_set.exists():
        return

    content = requests.get(instance.oas_link, timeout=60).content

    # Translate yaml to Python dict if needed
    if instance.oas_link.endswith('.yaml'):
        schema = yaml.load(content, Loader=yaml.FullLoader)
    else:
        if isinstance(content, bytes):
            content = content.decode('utf-8')
        schema = json.loads(content)

    for path, methods in schema['paths'].items():
        for method, details in methods.items():
            if method == 'parameters':
                continue

            # Cannot bulk create, because we need the ScenarioCase id to create
            # the QueryParamsScenario
            sc = ScenarioCase.objects.create(
                collection=instance,
                url=path,
                http_method=method.upper(),
                description=details.get('summary', ''),
            )

            for parameter in details.get('parameters') or []:
                # Retrieve parameter information from local reference
                if '$ref' in parameter:
                    parameter = get_parameter_from_ref(schema, parameter['$ref'])

                if parameter['in'] == 'query':
                    QueryParamsScenario.objects.create(
                        scenario_case=sc,
                        name=parameter['name'],
                        expected_value='*',
                    )

class VNGEndpoint(OrderedModel):

    port = models.PositiveIntegerField(default=8080, blank=True, help_text=_(
        "Specifies on which port endpoints for this service will be exposed"
    ))
    url = models.URLField(
        max_length=200,
        blank=True,
        null=True,
        default=None,
        validators=[
            RegexValidator(
                regex='/$',
                message=_('The url must not contain a final slash'),
                code='Invalid_url',
                inverse_match=True
            )
        ],
        help_text=_('Base url (host of the service). E.g. http://ref.tst.vng.cloud, without the ending slash.')
    )
    path = models.CharField(
        max_length=200,
        default='',
        validators=[
            RegexValidator(
                regex='^/',
                message=_('The path must start with a slash'),
                code='Invalid_path',
            )
        ],
        help_text=_('Path url that is appended in the front end page. The path must contain the slash at \
                            the beginning. E.g. /zrc/api/v1/'),
        blank=True
    )
    name = models.CharField(
        max_length=200,
        validators=[
            RegexValidator(
                regex='^[^ ]*$',
                message=_('The name cannot contain spaces'),
                code='Invalid_name'
            )
        ],
        help_text=_("The name of the service")
    )
    docker_image = models.CharField(max_length=200, blank=True, null=True, default=None, help_text=_(
        "The name of the Docker image that must be pulled to create a container"
    ))
    session_type = models.ForeignKey(SessionType, on_delete=models.PROTECT, help_text=_(
        "The session type to which this service belongs"
    ))
    test_file = FilerFileField(null=True, blank=True, default=None, on_delete=models.SET_NULL, help_text=_(
        "A Postman test collection that will be ran against this service upon stopping the test session"
    ))
    scenario_collection = models.ForeignKey(
        ScenarioCaseCollection, on_delete=models.SET_NULL,
        default=None, null=True, blank=True,
        help_text=_("The collection of scenario cases that must be tested for this service")
    )
    order_with_respect_to = 'session_type'

    class Meta(OrderedModel.Meta):
        pass

    def __str__(self):
        # To show the session type when adding a scenario case
        return self.name + " ({})".format(self.session_type)


class EnvironmentalVariables(models.Model):

    vng_endpoint = models.ForeignKey(VNGEndpoint, on_delete=models.CASCADE, help_text=_(
        "The service for which this environment variable is defined"
    ))
    key = models.CharField(max_length=50)
    value = models.CharField(max_length=100)


class ScenarioCase(OrderedModel):
    collection = models.ForeignKey(ScenarioCaseCollection, on_delete=models.CASCADE, help_text=_(
        "The collection of scenario cases to which this scenario case belongs"
    ))
    url = models.CharField(max_length=200, help_text='''
    URL pattern that will be compared
    with the request and eventually matched.
    Wildcards can be added, e.g. '/test/{uuid}/stop'
    will match the URL '/test/c5429dcc-6955-4e22-9832-08d52205f633/stop'.
    ''')
    http_method = models.CharField(max_length=20, choices=choices.HTTPMethodChoices.choices, default=choices.HTTPMethodChoices.GET, help_text=_(
        "The HTTP method that must be tested for this scenario case"
    ))
    order_with_respect_to = 'collection'
    description = models.TextField(default='', null=True, blank=True)

    class Meta(OrderedModel.Meta):
        pass

    def __str__(self):
        return '{} - {}'.format(self.http_method, self.url)

    def query_params(self):
        return [qp.name for qp in self.queryparamsscenario_set.all()]


class QueryParamsScenario(models.Model):

    scenario_case = models.ForeignKey(ScenarioCase, on_delete=models.PROTECT, help_text=_(
        "The scenario case to which this query parameter test belongs"
    ))
    name = models.CharField(max_length=100, help_text=_("The name of the query parameter"))
    expected_value = models.CharField(max_length=50, default='*', help_text=_("The expected value of the query parameter"))

    def __str__(self):
        if self.expected_value:
            return '{} - {}: {}'.format(self.scenario_case, self.name, self.expected_value)
        else:
            return '{} {}'.format(self.scenario_case, self.name)


class Session(models.Model):

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, help_text=_(
        "The universally unique identifier of this session, needed to retrieve the badge"
    ))
    name = models.CharField(_('Name'), max_length=30, unique=True, null=True, help_text=_(
        "The unique name of this session"
    ))
    session_type = models.ForeignKey(SessionType, verbose_name=_('Session type'), on_delete=models.PROTECT, help_text=_(
        "The session type of this session"
    ))
    started = models.DateTimeField(_('Started at'), default=timezone.now, help_text=_(
        "The time at which the session was started"
    ))
    stopped = models.DateTimeField(_('Stopped at'), null=True, blank=True, help_text=_(
        "The time at which the session was stopped"
    ))
    status = models.CharField(max_length=20, choices=choices.StatusChoices.choices, default=choices.StatusChoices.starting, help_text=_(
        "Indicates the status of this session"
    ))
    user = models.ForeignKey(User, verbose_name=_('User'), on_delete=models.SET_NULL, null=True, help_text=_(
        "The user that started this session"
    ))
    build_version = models.TextField(blank=True, null=True, default=None)
    error_message = models.TextField(blank=True, null=True, default=None, help_text=_(
        "Contains the error message, if an error occurred during the starting of the session"
    ))
    deploy_status = models.TextField(blank=True, null=True, default=None, help_text=_(
        "Indicates the status of deployment of the session"
    ))
    deploy_percentage = models.IntegerField(default=None, null=True, blank=True, help_text=_(
        "Indicates what percentage of the deployment is finished"
    ))
    sandbox = models.BooleanField(default=False, help_text=_(
        "If enabled, whenever multiple calls are made to the same path, the result of the call is overridden every time"
    ))
    supplier_name = models.CharField(max_length=100, blank=True, null=True, help_text=_(
        "The name of the supplier of the services"
    ))
    software_product = models.CharField(max_length=100, blank=True, null=True, help_text=_(
        "The name of the software tested by this session"
    ))
    product_role = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        verbose_name = _('Session')
        verbose_name_plural = _('Sessions')

    @staticmethod
    def assign_name(id):
        return "s{}{}".format(str(id), str(time.time()).replace('.', '-'))

    def __str__(self):
        if self.user:
            return "{} - {} - #{}".format(self.session_type, self.user.username, str(self.id))
        else:
            return "{} - #{}".format(self.session_type, str(self.id))

    def get_absolute_request_url(self, request):
        test_session_url = 'https://{}{}'.format(request.get_host(),
                                                 reverse('testsession:session_log', args=[self.session_type.api.id, self.uuid]))
        return test_session_url

    def is_stopped(self):
        return self.status == choices.StatusChoices.stopped

    def is_running(self):
        return self.status == choices.StatusChoices.running

    def is_starting(self):
        return self.status == choices.StatusChoices.starting

    def is_shutting_down(self):
        return self.status == choices.StatusChoices.shutting_down

    def get_report_stats(self):
        success, failed, not_called = 0, 0, 0
        reports = Report.objects.filter(session_log__in=self.sessionlog_set.all())
        for report in reports:
            if report.is_success():
                success += 1
            elif report.is_failed():
                failed += 1
            elif report.is_not_called():
                not_called += 1
        return success, failed, not_called + (self.session_type.scenario_cases.count() - reports.count())

class ExposedUrl(models.Model):

    port = models.PositiveIntegerField(default=8080, help_text=_(
        "The port under which the service has been exposed"
    ))
    subdomain = models.CharField(max_length=200, unique=True, null=True, help_text=_(
        "The subdomain under which the service has been exposed"
    ))
    session = models.ForeignKey(Session, on_delete=models.CASCADE, help_text=_(
        "The session to which this exposed URL belongs"
    ))
    vng_endpoint = models.ForeignKey(VNGEndpoint, on_delete=models.CASCADE, help_text=_(
        "The service to which this exposed URL points"
    ))
    test_session = models.ForeignKey(TestSession, blank=True, null=True, default=None, on_delete=models.CASCADE, help_text=_(
        "The test session to which this exposed URL belongs"
    ))
    docker_url = models.CharField(max_length=200, blank=True, null=True, default=None, help_text=_(
        "The address under which the Docker containers are deployed"
    ))

    def __str__(self):
        return '{} {}'.format(self.session, self.vng_endpoint)


class SessionLog(models.Model):

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, help_text=_(
        "The universally unique identifier of this session log"
    ))
    date = models.DateTimeField(default=timezone.now, help_text=_(
        "The time at which the request was done"
    ))
    session = models.ForeignKey(Session, on_delete=models.SET_NULL, null=True, help_text=_(
        "The session to which this log belongs"
    ))
    request = models.TextField(blank=True, null=True, default=None, help_text=_(
        "The request that was done"
    ))
    response = models.TextField(blank=True, null=True, default=None, help_text=_(
        "The response that was returned to the user"
    ))
    response_status = models.PositiveIntegerField(blank=True, null=True, default=None, help_text=_(
        "The HTTP status code of the response"
    ))

    def __str__(self):
        return '{} - {} - {}'.format(str(self.date), str(self.session),
                                     str(self.response_status))

    def request_path(self):
        return json.loads(self.request)['request']['path']

    def request_headers(self):
        return json.loads(self.request)['request']['header']

    def request_body(self):
        try:
            return json.loads(self.request)['request']['body']
        except:
            return ""

    def response_body(self):
        try:
            return json.loads(self.response)['response']['body']
        except:
            return ""


class Report(models.Model):

    class Meta:
        unique_together = ('scenario_case', 'session_log')

    scenario_case = models.ForeignKey(ScenarioCase, on_delete=models.CASCADE, help_text=_(
        "The scenario case to which this report belongs"
    ))
    session_log = models.ForeignKey(SessionLog, on_delete=models.CASCADE, help_text=_(
        "The session log containing the details of this report"
    ))
    result = models.CharField(max_length=20, choices=choices.HTTPCallChoices.choices, default=choices.HTTPCallChoices.not_called, help_text=_(
        "Indicates the whether the call specified in the scenario case has been called yet, and if it has succeeded or not"
    ))

    def is_success(self):
        return self.result == choices.HTTPCallChoices.success

    def is_failed(self):
        return self.result == choices.HTTPCallChoices.failed

    def is_not_called(self):
        return self.result == choices.HTTPCallChoices.not_called

    def __str__(self):
        return 'Case: {} - Log: {} - Result: {}'.format(self.scenario_case, self.session_log, self.result)
