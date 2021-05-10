import collections
import re
import json
import jwt
import copy
import unittest

import mock
import factory

from django.utils.http import urlencode
from django.conf import settings
from django.test import override_settings, tag
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext
from subdomains.utils import reverse as reverse_sub

from django_webtest import WebTest

from vng.accounts.models import User

from ..task import run_tests, align_sessions_data, purge_sessions
from vng.api.v1.testsession.views import RunTest
from ..models import (
    Session, SessionType, SessionLog, Report,
    ScenarioCase, VNGEndpoint, ExposedUrl, TestSession, InjectHeader
)
from ..permission import IsOwner

from .factories import (
    SessionFactory, SessionTypeFactory, VNGEndpointDockerFactory, ExposedUrlEchoFactory, VNGEndpointEchoFactory,
    ScenarioCaseFactory, ExposedUrlFactory, SessionLogFactory, VNGEndpointFactory, QueryParamsScenarioFactory,
    HeaderInjectionFactory, FilerField, ScenarioCaseCollectionFactory
)
from ...servervalidation.tests.factories import APIFactory
from ...utils import choices
from ...utils.factories import UserFactory


def get_object(r):
    return json.loads(r.decode('utf-8'))


settings.ALLOWED_HOSTS += ['*']


def get_username():
    if len(User.objects.all()) == 0:
        UserFactory()
    return User.objects.all().first().username


def get_subdomain(url):
    return re.search('[\w]{8}(-[\w]{4}){3}-[\w]{12}', url).group()


@override_settings(SUBDOMAIN_SEPARATOR='-')
class RetrieveSessionType(WebTest):

    def setUp(self):
        SessionTypeFactory()

    def test_retrieve_single_session_types(self):
        call = self.app.get(reverse('apiv1session:session_types-list'), user='admin')
        t = get_object(call.body)
        self.assertTrue(t[0]['id'] > 0)

    def test_retrieve_multiple_session_types(self):
        SessionTypeFactory.create_batch(size = 10)
        call = self.app.get(reverse('apiv1session:session_types-list'), user='admin')
        t = json.loads(call.text)
        self.assertTrue(t[9]['id'] > 0)


class SessionListTests(WebTest):

    def setUp(self):
        self.user = UserFactory.create()
        self.api1, self.api2 = APIFactory.create_batch(2)
        self.sessiontype1 = SessionTypeFactory.create(api=self.api1, name='type1')
        self.sessiontype2 = SessionTypeFactory.create(api=self.api2, name='type2')
        SessionFactory.create(session_type=self.sessiontype1, user=self.user)
        SessionFactory.create(session_type=self.sessiontype2, user=self.user)

    def test_create_session_filters_by_api(self):
        response = self.app.get(reverse('testsession:session_create', kwargs={
            'api_id': self.api1.id
        }), user=self.user)

        self.assertIn('type1', response.text)
        self.assertNotIn('type2', response.text)

    def test_list_filters_by_api(self):
        response = self.app.get(reverse('testsession:sessions', kwargs={
            'api_id': self.api1.id
        }), user=self.user)

        self.assertIn('type1', response.text)
        self.assertNotIn('type2', response.text)


@override_settings(SUBDOMAIN_SEPARATOR='-')
class AuthorizationTests(WebTest):

    def setUp(self):
        self.user = UserFactory()

    def test_check_unauthenticated_testsessions(self):
        self.app.get(reverse('apiv1session:session_types-list'), expect_errors = True)

    def test_right_login(self):
        call=self.app.post(reverse('apiv1_auth:rest_login'), params = collections.OrderedDict([
            ('username', self.user.username),
            ('password', 'password')]))
        self.assertIsNotNone(call.json.get('key'))

    def test_wrong_login(self):
        call=self.app.post(reverse('apiv1_auth:rest_login'), {
            'username': self.user.username,
            'password': 'wrong'
        }, status = 400)

        self.assertEqual(call.json, {"non_field_errors": [gettext("Unable to log in with provided credentials.")]})

    def test_session_creation_authentication(self):
        Session.objects.all().delete()
        session={
            'session_type': 1,
            'started': str(timezone.now()),
            'status': choices.StatusChoices.running,
            'api_endpoint': 'http://google.com',
        }
        call = self.app.post(reverse('apiv1session:test_session-list'), session, status=[401, 302])

@tag('kubernetes')
@override_settings(SUBDOMAIN_SEPARATOR='-')
class CreationAndDeletion(WebTest):
    csrf_checks = False

    def setUp(self):
        self.session_type = SessionTypeFactory()
        self.user = UserFactory()
        self.session_type_docker = VNGEndpointDockerFactory().session_type
        call = self.app.post(reverse('apiv1_auth:rest_login'), params=collections.OrderedDict([
            ('username', self.user.username),
            ('password', 'password')]))
        key = get_object(call.body)['key']
        self.head = {'Authorization': 'Token {}'.format(key)}
        self.vng_endpoint = VNGEndpointFactory()

    def test_session_creation(self):
        session = {
            'session_type': self.session_type.name,
            'api_endpoint': 'http://google.com'
        }

        call = self.app.post(reverse('apiv1session:test_session-list'), session, headers=self.head)

    def test_report_postman(self):

        session = {
            'session_type': self.vng_endpoint.session_type.name,
            'api_endpoint': 'http://google.com'
        }

        call = self.app.post(reverse('apiv1session:test_session-list'), session, headers=self.head)

        session = Session.objects.all().order_by('-id').first()
        self.app.post(reverse('testsession:stop_session', kwargs={
            'api_id': self.vng_endpoint.session_type.api.id,
            'uuid': session.uuid
        }), user=session.user)

        self.app.get(reverse('testsession:session_log', kwargs={
            'api_id': self.vng_endpoint.session_type.api.id,
            'uuid': session.uuid
        }), user=session.user)

    def test_deploy_docker_via_api(self):
        url = reverse('apiv1session:test_session-list')
        data = {'session_type': self.session_type_docker.name}
        response = self.app.post_json(url, data, headers=self.head)
        session_uuid = response.json['uuid']
        if settings.ENVIRONMENT != 'jenkins':
            self.app.post(reverse('testsession:stop_session', kwargs={
                'api_id': self.session_type_docker.api.id,
                'uuid': session_uuid
            }), headers=self.head)

    def test_session_creation_permission(self):
        Session.objects.all().delete()
        session = {
            'session_type': self.session_type.name,
            'started': str(timezone.now()),
            'status': choices.StatusChoices.running,
            'api_endpoint': 'http://google.com',
            'user': self.user.id,
        }

        call = self.app.post(reverse('apiv1_auth:rest_login'), params=collections.OrderedDict([
            ('username', self.user.username),
            ('password', 'password')]))
        key = get_object(call.body)['key']
        head = {'Authorization': 'Token {}'.format(key)}
        call = self.app.post(reverse('apiv1session:test_session-list'), session, headers=head)
        response_parsed = get_object(call.body)
        session = Session.objects.filter(uuid=response_parsed['uuid'])[0]
        self.assertEqual(session.user.pk, self.user.pk)

    def test_stop_session_no_auth(self):
        session = SessionFactory()
        call = self.app.post(reverse('testsession:stop_session', kwargs={
            'api_id': session.session_type.api.id,
            'uuid': session.uuid
        }), status=302)


@override_settings(SUBDOMAIN_SEPARATOR='-')
class TestLog(WebTest):

    def setUp(self):
        self.user = UserFactory.create()
        self.scenarioCase = ScenarioCaseFactory()
        self.exp_url = ExposedUrlFactory()
        self.session = self.exp_url.session
        self.exp_url.vng_endpoint.session_type = self.session.session_type
        self.exp_url.vng_endpoint.url = 'https://postman-echo.com/'
        self.exp_url.vng_endpoint.scenario_collection = self.scenarioCase.collection
        self.exp_url.vng_endpoint.save()
        self.scenarioCase_hard = copy.copy(self.scenarioCase)
        self.scenarioCase_hard.url = 'test/{uuid}/t'
        self.scenarioCase_hard.pk += 1

        self.scenarioCase_hard.save()
        self.scenarioCase.save()
        self.exp_url.vng_endpoint.save()
        self.exp_url.save()
        self.session_log = SessionLogFactory()
        self.endpoint_echo_e = ExposedUrlEchoFactory()
        self.endpoint_echo_e.session.session_type = self.endpoint_echo_e.vng_endpoint.session_type
        self.endpoint_echo_e.session.save()
        self.endpoint_echo_e.vng_endpoint.scenario_collection = ScenarioCaseCollectionFactory()
        self.endpoint_echo_e.vng_endpoint.save()
        self.endpoint_echo_e.save()

        self.endpoint_echo_h = ExposedUrlEchoFactory()
        self.endpoint_echo_h.session.session_type = self.endpoint_echo_h.vng_endpoint.session_type
        self.endpoint_echo_h.vng_endpoint.url = 'https://postman-echo.com/headers'
        self.endpoint_echo_h.vng_endpoint.scenario_collection = ScenarioCaseCollectionFactory()
        self.endpoint_echo_h.vng_endpoint.save()
        self.endpoint_echo_h.session.session_type.authentication = choices.AuthenticationChoices.jwt
        self.endpoint_echo_h.session.session_type.save()
        self.endpoint_echo_h.session.save()
        self.endpoint_echo_h.save()

    def test_retrieve_no_entries(self):
        call = self.app.get(reverse('testsession:session_log', kwargs={
            'api_id': self.session.session_type.api.id, 'uuid': self.session.uuid
        }), user=self.session.user)
        self.assertTrue('No requests have yet been received.' in call.text)

    def test_retrieve_no_entry(self):
        url = reverse_sub('run_test', self.exp_url.subdomain, kwargs={
            'relative_url': ''
        })
        call = self.app.get(url, extra_environ={'HTTP_HOST': '{}-example.com'.format(self.exp_url.subdomain)}, user=self.session.user)
        call2 = self.app.get(reverse('testsession:session_log', kwargs={
            'api_id': self.session.session_type.api.id, 'uuid': self.session.uuid
        }), user=self.session.user)
        self.assertTrue(url in call2.text)

    def test_log_report(self):
        self.test_retrieve_no_entry()
        call = self.app.get(reverse('testsession:session_report', kwargs={
            'api_id': self.session.session_type.api.id, 'uuid': self.session.uuid
        }), user=self.session.user)

    def test_log_report_pdf(self):
        self.test_retrieve_no_entry()
        call = self.app.get(reverse('testsession:session_report-pdf', kwargs={
            'api_id': self.session.session_type.api.id, 'uuid': self.session.uuid
        }), user=self.session.user)

    def test_log_detail_view(self):
        sl = self.session_log
        call = self.app.get(reverse('testsession:session_log-detail',
                                    kwargs={
                                        'api_id': sl.session.session_type.api.id,
                                        'uuid': sl.session.uuid,
                                        'log_uuid': sl.uuid}),
                            user=sl.session.user)

    def test_log_detail_view_no_authorized(self):
        sl = self.session_log
        call = self.app.get(reverse('testsession:session_log-detail',
                                    kwargs={
                                        'api_id': sl.session.session_type.api.id,
                                        'uuid': sl.session.uuid,
                                        'log_uuid': sl.uuid}),
                            status=[302, 401, 403, 404])

    def test_api_session(self):
        session_type = SessionTypeFactory.create()
        vng_endpoint = VNGEndpointFactory.create(session_type=session_type)

        call = self.app.post(reverse('apiv1_auth:rest_login'), params=collections.OrderedDict([
            ('username', self.user.username),
            ('password', 'password')]))
        key = get_object(call.body)['key']
        head = {'Authorization': 'Token {}'.format(key)}
        call = self.app.post(reverse("apiv1session:test_session-list"), params=collections.OrderedDict([
            ('session_type', session_type.name),
        ]), headers=head)
        call = get_object(call.body)
        url = call['exposedurl_set'][0]['subdomain']
        session_uuid = call['uuid']
        http_host = get_subdomain(url)
        call = self.app.get(url, extra_environ={'HTTP_HOST': '{}-example.com'.format(http_host)})
        call = self.app.get(reverse('apiv1session:stop_session', kwargs={'uuid': session_uuid}))
        call = get_object(call.body)
        self.assertEqual(call, [])
        session = Session.objects.get(uuid=session_uuid)
        self.assertEqual(session.status, choices.StatusChoices.stopped)

        call = self.app.get(reverse('apiv1session:result_session', kwargs={'uuid': session_uuid}))
        call = get_object(call.body)
        self.assertEqual(call['result'], 'No scenario cases available')

    def test_hard_matching(self):
        url = reverse_sub('run_test', self.exp_url.subdomain, kwargs={
            'relative_url': 'test/xxx/t'
        })
        call = self.app.get(url, extra_environ={'HTTP_HOST': '{}-example.com'.format(self.exp_url.subdomain)}, user=self.session.user, status=[404])
        rp = Report.objects.filter(scenario_case=self.scenarioCase_hard)
        self.assertTrue(len(rp) != 0)

    def test_exposed_urls(self):
        call = self.app.get(reverse("apiv1session:test_session-list"), user=self.session.user)
        res = call.json
        session = Session.objects.get(uuid=res[0]['uuid'])
        endpoint = VNGEndpoint.objects.get(name=res[0]['exposedurl_set'][0]['vng_endpoint'])
        self.assertEqual(endpoint.session_type, session.session_type)

    def test_ordered_report(self):
        url = reverse('testsession:session_report', kwargs={
            'api_id': self.session.session_type.api.id,
            'uuid': self.session.uuid
        })
        scenario_case = ScenarioCase.objects.all().order_by('order')
        call = self.app.get(url, user=self.session.user)

        scenario1 = scenario_case[0]
        scenario2 = scenario_case[1]
        scenario1_index = call.text.index(scenario1.url)
        scenario2_index = call.text.index(scenario2.url)
        self.assertLess(scenario1_index, scenario2_index)

    @unittest.expectedFailure
    @mock.patch('vng.api.v1.testsession.views.logger')
    def test_rewrite_body(self, mock_logger):
        url = reverse_sub('run_test', self.endpoint_echo_e.subdomain, kwargs={
            'relative_url': 'post/'
        })
        call = self.app.post(url, url, extra_environ={'HTTP_HOST': '{}-example.com'.format(self.endpoint_echo_e.subdomain)}, user=self.endpoint_echo_e.session.user)
        self.assertIn('Rewriting request body:', mock_logger.info.call_args_list[-7][0][0])
        self.assertIn(url, call.text)

    def test_no_rewrite_header(self):
        url = reverse_sub('run_test', self.endpoint_echo_h.subdomain, kwargs={
            'relative_url': ''
        })
        headers = {'authorization': 'dummy'}
        call = self.app.get(url, extra_environ={'HTTP_HOST': '{}-example.com'.format(self.endpoint_echo_h.subdomain)},
                            headers=headers, user=self.endpoint_echo_h.session.user)
        self.assertEqual(call.json['headers']['authorization'], headers['authorization'])


@override_settings(SUBDOMAIN_SEPARATOR='-')
class TestUrlParam(WebTest):

    def setUp(self):
        self.qp = QueryParamsScenarioFactory()
        self.scenario_case = self.qp.scenario_case
        self.collection = self.scenario_case.collection
        self.vng_endpoint = VNGEndpointFactory(scenario_collection=self.collection)
        self.session = SessionFactory(session_type=self.vng_endpoint.session_type)
        self.exposed_url = ExposedUrlFactory(session=self.session, vng_endpoint=self.vng_endpoint)

        self.qp_p = QueryParamsScenarioFactory()
        self.scenario_case_p = self.qp_p.scenario_case
        self.scenario_case_p.http_method = choices.HTTPMethodChoices.PUT
        self.scenario_case_p.save()
        self.collection_p = self.scenario_case_p.collection
        self.vng_endpoint_p = VNGEndpointFactory(scenario_collection=self.collection_p)
        self.session_p = SessionFactory(session_type=self.vng_endpoint_p.session_type)
        self.exposed_url_p = ExposedUrlFactory(session=self.session_p, vng_endpoint=self.vng_endpoint_p)

        self.vng_endpoint.url = 'https://postman-echo.com/'
        self.vng_endpoint_p.url = 'https://postman-echo.com/'
        self.vng_endpoint.save()
        self.vng_endpoint_p.save()

    def test_permissions(self):
        permissions = IsOwner()
        res = permissions.has_object_permission(
            type('req',(object,),{'user':self.session.user})(),
            type('view',(object,),{'user_path':['user']})(),
            self.session
        )
        self.assertEqual(res, True)
        res = permissions.has_object_permission(
            type('req',(object,),{'user':UserFactory()})(),
            type('view',(object,),{'user_path':['user']})(),
            self.session
        )
        self.assertEqual(res, False)

    def test_query_params_post_request_match(self):
        qp = QueryParamsScenarioFactory(name='someparam')
        scenario_case = qp.scenario_case
        scenario_case.collection = self.collection
        scenario_case.http_method = 'POST'
        scenario_case.save()

        url = reverse_sub('run_test', self.exposed_url.subdomain, kwargs={
            'relative_url': scenario_case.url
        })
        url = url + '?' + urlencode({qp.name: 'bla'})
        call = self.app.post(url, extra_environ={'HTTP_HOST': '{}-example.com'.format(self.exposed_url.subdomain)},
                            user=self.session.user, status=[404])

        self.assertEqual(len(Report.objects.filter(scenario_case=scenario_case)), 1)

    def test_query_params_no_match(self):
        report = len(Report.objects.filter(scenario_case=self.scenario_case))
        url = reverse_sub('run_test', self.exposed_url.subdomain, kwargs={
            'relative_url': self.scenario_case.url
        })
        call = self.app.get(url, extra_environ={'HTTP_HOST': '{}-example.com'.format(self.exposed_url.subdomain)},
                            user=self.session.user, status=[404])
        self.assertEqual(report, len(Report.objects.filter(scenario_case=self.scenario_case)))

    def test_query_params_match_wild(self):
        report = len(Report.objects.filter(scenario_case=self.scenario_case))
        url = reverse_sub('run_test', self.exposed_url.subdomain, kwargs={
            'relative_url': self.scenario_case.url
        })
        call = self.app.get(url,
                            {self.qp.name: 'dummy'},
                            extra_environ={'HTTP_HOST': '{}-example.com'.format(self.exposed_url.subdomain)},
                            user=self.session.user, status=[404]
                            )
        self.assertEqual(report + 1, len(Report.objects.filter(scenario_case=self.scenario_case)))

    def test_query_params_match(self):
        qp = QueryParamsScenarioFactory(scenario_case=self.scenario_case, expected_value='dummy', name='strict')
        report = len(Report.objects.filter(scenario_case=self.scenario_case))
        url = reverse_sub('run_test', self.exposed_url.subdomain, kwargs={
            'relative_url': self.scenario_case.url
        })
        call = self.app.get(url,
                            {'strict': 'dummy', self.qp.name: 'dummy'},
                            extra_environ={'HTTP_HOST': '{}-example.com'.format(self.exposed_url.subdomain)},
                            user=self.session.user, status=[404]
                            )
        self.assertEqual(report + 1, len(Report.objects.filter(scenario_case=self.scenario_case)))

    def test_query_params_put(self):
        report = len(Report.objects.filter(scenario_case=self.scenario_case_p))
        url = reverse_sub('run_test', self.exposed_url_p.subdomain, kwargs={
            'relative_url': self.scenario_case_p.url
        })
        call = self.app.put(url + '?{}=dummy'.format(self.qp_p.name),
                            extra_environ={'HTTP_HOST': '{}-example.com'.format(self.exposed_url_p.subdomain)},
                            user=self.session_p.user, status=[404]
                            )
        self.assertEqual(report + 1, len(Report.objects.filter(scenario_case=self.scenario_case_p)))


@override_settings(SUBDOMAIN_SEPARATOR='-')
class TestUrlMatchingPatterns(WebTest):

    def setUp(self):
        self.scenario_case = ScenarioCaseFactory(url='test')
        self.vng_endpoint = VNGEndpointFactory(
            scenario_collection=self.scenario_case.collection
        )
        self.user = UserFactory.create()
        call = self.app.post(reverse('apiv1_auth:rest_login'), params=collections.OrderedDict([
            ('username', self.user.username),
            ('password', 'password')]))
        key = get_object(call.body)['key']
        self.head = {'Authorization': 'Token {}'.format(key)}

    def test_create_session(self):
        # Save the report list
        report_list = Report.objects.all()
        resp = self.app.post_json(reverse('apiv1session:test_session-list'), {
            'session_type': self.vng_endpoint.session_type.name
        }, headers=self.head)

        # Call the url with additional padding
        http_host = get_subdomain(resp.json['exposedurl_set'][0]['subdomain'])
        self.app.get(resp.json['exposedurl_set'][0]['subdomain'] + 'test' + '/dummy',
                     extra_environ={'HTTP_HOST': '{}-example.com'.format(http_host)}, expect_errors=True)
        # Check that the report has not been crated
        self.assertEqual(len(report_list), len(Report.objects.all()))

        # Call the url without further padding
        print(resp.json['exposedurl_set'][0]['subdomain'] + 'test')
        self.app.get(resp.json['exposedurl_set'][0]['subdomain'] + 'test',
                     extra_environ={'HTTP_HOST': '{}-example.com'.format(http_host)}, expect_errors=True)
        # Check if the report has been created
        self.assertEqual(len(report_list) + 1, len(Report.objects.all()))

        last_report = Report.objects.latest('id')
        self.assertEqual(last_report.scenario_case, self.scenario_case)


@override_settings(SUBDOMAIN_SEPARATOR='-')
class TestSandboxMode(WebTest):

    def setUp(self):
        self.user = UserFactory()
        self.sc = ScenarioCaseFactory(url='status/{code}')
        self.endpoint = VNGEndpointFactory(
            scenario_collection=self.sc.collection,
            url='https://postman-echo.com/'
        )
        self.session_type = self.endpoint.session_type

    def test_sandbox(self):
        call = self.app.get(reverse('testsession:session_create', kwargs={
            'api_id': self.session_type.api.id
        }), user=self.user)
        form = call.forms[1]
        form['session_type'].select(form['session_type'].options[-1][0])
        form['sandbox'] = True
        form.submit()
        session = Session.objects.all().order_by('-pk')[0]
        eu = ExposedUrl.objects.get(session=session)

        all_rep = Report.objects.all()
        url = reverse_sub('run_test', eu.subdomain, kwargs={
            'relative_url': 'status/404'
        })
        call = self.app.get(url, extra_environ={'HTTP_HOST': '{}-example.com'.format(eu.subdomain)}, user=session.user, status=[404])
        report = Report.objects.get(scenario_case=self.sc)

        self.assertEqual(choices.HTTPCallChoices.failed, report.result)
        url = reverse_sub('run_test', eu.subdomain, kwargs={
            'relative_url': 'status/200'
        })
        call = self.app.get(url, extra_environ={'HTTP_HOST': '{}-example.com'.format(eu.subdomain)}, user=session.user)
        report = Report.objects.get(scenario_case=self.sc)
        self.assertEqual(choices.HTTPCallChoices.success, report.result)

    def test_no_sandbox(self):
        call = self.app.get(reverse('testsession:session_create', kwargs={
            'api_id': self.session_type.api.id
        }), user=self.user)
        form = call.forms[1]
        form['session_type'].select(form['session_type'].options[-1][0])
        form['sandbox'] = False
        form.submit()
        session = Session.objects.all().order_by('-pk')[0]
        eu = ExposedUrl.objects.get(session=session)

        all_rep = Report.objects.all()
        url = reverse_sub('run_test', eu.subdomain, kwargs={
            'relative_url': 'status/404'
        })
        call = self.app.get(url, extra_environ={'HTTP_HOST': '{}-example.com'.format(eu.subdomain)}, user=session.user, status=[404])
        report = Report.objects.get(scenario_case=self.sc)

        self.assertEqual(choices.HTTPCallChoices.failed, report.result)
        url = reverse_sub('run_test', eu.subdomain, kwargs={
            'relative_url': 'status/200'
        })
        call = self.app.get(url, extra_environ={'HTTP_HOST': '{}-example.com'.format(eu.subdomain)}, user=session.user)
        report = Report.objects.get(scenario_case=self.sc)
        self.assertEqual(choices.HTTPCallChoices.failed, report.result)

    def test_create_sandbox_default(self):
        session = {
            'session_type': self.session_type.name,
            'started': str(timezone.now()),
            'status': choices.StatusChoices.running,
            'api_endpoint': 'http://google.com',
            'user': self.user.id,
        }

        call = self.app.post(reverse('apiv1_auth:rest_login'), params=collections.OrderedDict([
            ('username', self.user.username),
            ('password', 'password')]))
        key = get_object(call.body)['key']
        head = {'Authorization': 'Token {}'.format(key)}
        call = self.app.post(reverse('apiv1session:test_session-list'), session, headers=head)
        response_parsed = get_object(call.body)
        session = Session.objects.latest('id')
        self.assertEqual(session.sandbox, False)

    def test_create_sandbox(self):
        session = {
            'session_type': self.session_type.name,
            'started': str(timezone.now()),
            'status': choices.StatusChoices.running,
            'api_endpoint': 'http://google.com',
            'user': self.user.id,
            'sandbox': True

        }

        call = self.app.post(reverse('apiv1_auth:rest_login'), params=collections.OrderedDict([
            ('username', self.user.username),
            ('password', 'password')]))
        key = get_object(call.body)['key']
        head = {'Authorization': 'Token {}'.format(key)}
        call = self.app.post(reverse('apiv1session:test_session-list'), session, headers=head)
        response_parsed = get_object(call.body)
        session = Session.objects.latest('id')
        self.assertEqual(session.sandbox, True)


@override_settings(SUBDOMAIN_SEPARATOR='-')
class TestAllProcedure(WebTest):
    csrf_checks = False

    def setUp(self):
        self.user = UserFactory()
        self.session = SessionFactory()
        self.session_type = VNGEndpointFactory(name='demo-api').session_type

    def _test_create_session(self):
        call = self.app.get(reverse('testsession:session_create', kwargs={
            'api_id': self.session_type.api.id
        }), user=self.user)
        form = call.forms[1]
        form['session_type'].select(str(self.session_type.id))
        form.submit()

        call = self.app.get(reverse('testsession:sessions', kwargs={
            'api_id': self.session_type.api.id
        }), user=self.user)
        self.assertIn(self.session_type.name, call.text)

    def _test_stop_session(self):
        self.session = Session.objects.filter(user=self.user).filter(status=choices.StatusChoices.running)[0]
        url = reverse('testsession:stop_session', kwargs={
            'api_id': self.session.session_type.api.id,
            'uuid': self.session.uuid,
        })
        call = self.app.post(url, user=self.session.user).follow()
        self.assertIn('Stopped', call.text)


    def test_get_report_stats(self):
        call = self.app.get(reverse('testsession:session_log',kwargs={
            'api_id': self.session.session_type.api.id,
            'uuid': self.session.uuid
        }))
        self.assertEqual(call.status, '200 OK')

    def test_report(self):
        self._test_create_session()
        self._test_stop_session()
        session = Session.objects.get(pk=self.session.pk)
        url = reverse('testsession:session_report', kwargs={
            'api_id': session.session_type.api.id,
            'uuid': self.session.uuid,
        })
        call = self.app.get(url, user=self.session.user)

        url = reverse('testsession:session_report-pdf', kwargs={
            'api_id': self.session.session_type.api.id,
            'uuid': self.session.uuid,
        })
        call = self.app.get(url, user=self.session.user)

    def test_postman(self):
        self._test_create_session()
        self.session = Session.objects.filter(user=self.user).filter(status=choices.StatusChoices.running)[0]
        url = reverse('testsession:stop_session', kwargs={
            'api_id': self.session.session_type.api.id,
            'uuid': self.session.uuid,
        })
        call = self.app.post(url, user=self.session.user).follow()
        call = self.app.get(reverse('testsession:session_log', kwargs={
            'api_id': self.session.session_type.api.id,
            'uuid': self.session.uuid
        }))
        self.assertIn('200 OK', call.text)

    def test_url_slash(self):
        from uuid import uuid4
        url = reverse('testsession:session_log', kwargs={
            'api_id': self.session.session_type.api.id,
            'uuid': uuid4()
        })

        call = self.app.get(url[:-1], user=self.user)
        self.assertIn('301', call.status)
        call = self.app.get(url, user=self.user, status=[404])
        self.assertIn('404', call.status)

    def test_update_session(self):
        self._test_create_session()
        session = Session.objects.latest('id')
        call = self.app.get(
            reverse(
                'testsession:session_update',
                kwargs={'api_id': session.session_type.api.id, 'uuid': session.uuid}),
            user=self.user
        )
        form = call.forms[1]
        form['supplier_name'] = 'test_name'
        form['software_product'] = 'test_software'
        form['product_role'] = 'test_product'
        res = form.submit().follow()
        session = Session.objects.latest('id')
        self.assertEqual(session.product_role, 'test_product')


    def test_get_schema(self):
        call = self.app.get(reverse('schema-redoc'))
        self.assertEqual(call.status, '200 OK')
        call = self.app.get(reverse('api-schema'))
        self.assertEqual(call.status, '200 OK')


@override_settings(SUBDOMAIN_SEPARATOR='-')
class TestLogNewman(WebTest):

    def setUp(self):
        self.user = UserFactory.create()
        self.scenario_case = ScenarioCaseFactory()
        self.scenario_case1 = ScenarioCaseFactory(collection=self.scenario_case.collection)
        self.vng_endpoint = VNGEndpointFactory(scenario_collection=self.scenario_case.collection)

        call = self.app.post(reverse('apiv1_auth:rest_login'), params=collections.OrderedDict([
            ('username', self.user.username),
            ('password', 'password')]))
        key = get_object(call.body)['key']
        self.head = {'Authorization': 'Token {}'.format(key)}

    def test_run(self):
        call = self.app.post(reverse("apiv1session:test_session-list"), params=collections.OrderedDict([
            ('session_type', self.vng_endpoint.session_type.name),
        ]), headers=self.head)
        call = get_object(call.body)
        session_uuid = call['uuid']
        url = call['exposedurl_set'][0]['subdomain']

        http_host = get_subdomain(call['exposedurl_set'][0]['subdomain'])
        call = self.app.get(url, extra_environ={'HTTP_HOST': '{}-example.com'.format(http_host)})

        call = self.app.get(reverse('apiv1session:stop_session', kwargs={'uuid': session_uuid}))
        call = get_object(call.body)
        self.assertEqual(len(call), 2)

        call = self.app.get(reverse('apiv1session:result_session', kwargs={'uuid': session_uuid}))
        call = get_object(call.body)
        self.assertEqual(call['result'], 'Geen oproep uitgevoerd')


@override_settings(SUBDOMAIN_SEPARATOR='-')
class TestHeaderInjection(WebTest):

    def setUp(self):
        self.collection = ScenarioCaseCollectionFactory()
        self.endpoint = VNGEndpointEchoFactory(scenario_collection=self.collection)
        self.hi = HeaderInjectionFactory(session_type=self.endpoint.session_type)
        self.user = UserFactory.create()
        call = self.app.post(reverse('apiv1_auth:rest_login'), params=collections.OrderedDict([
            ('username', self.user.username),
            ('password', 'password')]))
        key = get_object(call.body)['key']
        self.head = {'Authorization': 'Token {}'.format(key)}

    def test_run(self):
        call = self.app.post(reverse("apiv1session:test_session-list"), params=collections.OrderedDict([
            ('session_type', self.endpoint.session_type.name),
        ]), headers=self.head)
        call = get_object(call.body)
        session_uuid = call['uuid']
        url = call['exposedurl_set'][0]['subdomain']

        http_host = get_subdomain(call['exposedurl_set'][0]['subdomain'])
        call = self.app.get(url + 'headers', extra_environ={'HTTP_HOST': '{}-example.com'.format(http_host)})
        self.assertIn('key', call.json['headers'])
        self.assertIn('dummy', call.json['headers']['key'])

    def test_create_jwt_auth_inject_header_from_client_credentials(self):
        sessiontype = SessionTypeFactory(
            client_id='username',
            secret='bla',
            authentication=choices.AuthenticationChoices.jwt
        )

        auth_headers = InjectHeader.objects.filter(session_type=sessiontype)
        self.assertEqual(auth_headers.count(), 1)

        auth_header = auth_headers.first()
        self.assertEqual(auth_header.key, 'Authorization')

        token = auth_header.value
        decoded = jwt.decode(token.split()[-1], 'bla', algorithms=['HS256'])
        self.assertEqual(decoded['client_id'], 'username')


@override_settings(SUBDOMAIN_SEPARATOR='-')
class TestAuthProxy(WebTest):

    def setUp(self):
        self.user = UserFactory()
        self.vng_no_auth = VNGEndpointEchoFactory()
        self.vng_auth = VNGEndpointEchoFactory()
        self.vng_header = VNGEndpointEchoFactory()
        self.vng_auth.session_type.authentication = choices.AuthenticationChoices.jwt
        self.vng_auth.session_type.save()
        self.vng_header.session_type.authentication = choices.AuthenticationChoices.header
        self.vng_header.session_type.header = 'test'
        self.vng_header.session_type.save()

        call = self.app.post(reverse('apiv1_auth:rest_login'), params=collections.OrderedDict([
            ('username', self.user.username),
            ('password', 'password')]))
        key = get_object(call.body)['key']
        self.head = {'Authorization': 'Token {}'.format(key)}

        self.url_no_auth = self.app.post(reverse("apiv1session:test_session-list"), params=collections.OrderedDict([
            ('session_type', self.vng_no_auth.session_type.name),
        ]), headers=self.head).json['exposedurl_set'][0]['subdomain']

        self.url_auth = self.app.post(reverse("apiv1session:test_session-list"), params=collections.OrderedDict([
            ('session_type', self.vng_auth.session_type.name),
        ]), headers=self.head).json['exposedurl_set'][0]['subdomain']

        self.url_head = self.app.post(reverse("apiv1session:test_session-list"), params=collections.OrderedDict([
            ('session_type', self.vng_header.session_type.name),
        ]), headers=self.head).json['exposedurl_set'][0]['subdomain']

    def test_no_auth(self):
        http_host = get_subdomain(self.url_no_auth)
        resp = self.app.post(self.url_no_auth + 'post', extra_environ={'HTTP_HOST': '{}-example.com'.format(http_host)})
        self.assertNotIn('authorization', resp.json['headers'])

    def test_auth(self):
        http_host = get_subdomain(self.url_auth)
        resp = self.app.post(self.url_auth + 'post', extra_environ={'HTTP_HOST': '{}-example.com'.format(http_host)})
        self.assertIn('authorization', resp.json['headers'])

    def test_header(self):
        http_host = get_subdomain(self.url_head)
        resp = self.app.post(self.url_head + 'post', extra_environ={'HTTP_HOST': '{}-example.com'.format(http_host)})
        self.assertEqual('test', resp.json['headers']['authorization'])


@override_settings(SUBDOMAIN_SEPARATOR='-')
class TestRewriteBody(WebTest):

    def setUp(self):
        self.euv = RunTest()
        self.ep = ExposedUrlFactory()
        self.ep_docker = VNGEndpointDockerFactory()
        self.ep_d = ExposedUrlFactory(vng_endpoint=self.ep_docker, docker_url='127.0.0.1')
        self.host = 'example.com'

        self.ep_s = ExposedUrlFactory()
        self.ep_s.vng_endpoint.subdomain = 'sub'
        self.ep_s.vng_endpoint.save()
        self.host_sub = 'sub.example.com'

    def test_request(self):
        content = 'dummy{}/dummy'.format(self.host)
        res = self.euv.sub_url_request(content, self.host, self.ep)
        self.assertEqual('dummy{}/dummy'.format(self.ep.vng_endpoint.url), res)

    def test_request_subdomain(self):
        content = 'dummy{}/dummy'.format(self.host_sub)
        res = self.euv.sub_url_request(content, self.host_sub, self.ep_s)
        self.assertEqual('dummy{}/dummy'.format(self.ep_s.vng_endpoint.url), res)

    def test_response(self):
        content = 'dummy{}/dummy'.format(self.ep.vng_endpoint.url)
        res = self.euv.sub_url_response(content, self.host, self.ep)
        self.assertEqual('dummy{}/dummy'.format(self.host), res)

    def test_request_docker(self):
        content = 'dummy{}/dummy'.format(self.host)
        res = self.euv.sub_url_request(content, self.host, self.ep_d)
        self.assertEqual('dummy://{}:8080/dummy'.format(self.ep_d.docker_url), res)

    def test_response_docker(self):
        content = 'dummy://{}:8080/dummy'.format(self.ep_d.docker_url)
        res = self.euv.sub_url_response(content, self.host, self.ep_d)
        self.assertEqual('dummy{}/dummy'.format(self.host), res)


@override_settings(SUBDOMAIN_SEPARATOR='-')
class TestRewriteUrl(WebTest):

    def setUp(self):
        self.endpoint = VNGEndpointFactory(url='http://www.dummy.com', path='/path/sub')
        self.eu = ExposedUrlFactory(vng_endpoint=self.endpoint)

    def test_url(self):
        rt = RunTest()
        rt.kwargs = {
            'relative_url': ''
        }
        url = rt.build_url(self.eu, '')
        self.assertEqual(url, self.endpoint.url + '/')

    def test_url_sub(self):
        rt = RunTest()
        rt.kwargs = {
            'relative_url': 'path/'
        }
        url = rt.build_url(self.eu, '')
        self.assertEqual(url, 'http://www.dummy.com/path/')

    def test_url_sub_sub(self):
        rt = RunTest()
        rt.kwargs = {
            'relative_url': 'path/sub/a'
        }
        url = rt.build_url(self.eu, '')
        self.assertEqual(url, 'http://www.dummy.com/path/sub/a')


@override_settings(SUBDOMAIN_SEPARATOR='-')
class TestPostmanRun(WebTest):

    def setUp(self):
        self.endpoint = VNGEndpointDockerFactory(name='name', url='www.google.com')
        self.endpoint.test_file = FilerField(
            file=factory.django.FileField(
                from_path=settings.POSTMAN_ROOT + '/test_name.postman_collection.json'
            ))
        self.endpoint.save()
        self.session = SessionFactory(session_type=self.endpoint.session_type)
        self.eu = ExposedUrlFactory(session=self.session, vng_endpoint=self.endpoint)

    def test_rewrite(self):
        run_tests(self.session.uuid)
        self.assertTrue(ExposedUrl.objects.get(id=self.eu.id).test_session.is_success_test())


@override_settings(SUBDOMAIN_SEPARATOR='-')
class TestActiveSessionType(WebTest):

    def setUp(self):
        self.api = APIFactory.create()
        self.stypes = [SessionTypeFactory(active = i%2==0, api=self.api) for i in range(10)]
        self.user = UserFactory()

    def test_active_stypes(self):
        call = self.app.get(reverse('testsession:session_create', kwargs={
            'api_id': self.api.id
        }), user=self.user)
        for st in self.stypes:
            if st.active:
                self.assertIn(st.name, call.text)
            else:
                self.assertNotIn(st.name, call.text)


@override_settings(SUBDOMAIN_SEPARATOR='-')
class TestMultipleParams(WebTest):
    csrf_checks = False

    def setUp(self):
        self.user = UserFactory()
        self.collection = ScenarioCaseCollectionFactory()
        self.ep = VNGEndpointFactory(scenario_collection=self.collection)
        self.sc1 = ScenarioCaseFactory(collection=self.collection)
        self.sc2 = ScenarioCaseFactory(collection=self.collection)
        QueryParamsScenarioFactory(scenario_case=self.sc1, name='tparam1')
        QueryParamsScenarioFactory(scenario_case=self.sc2, name='tparam1')
        QueryParamsScenarioFactory(scenario_case=self.sc2, name='tparam2')

    def test(self):
        resp = self.app.post_json(reverse('apiv1session:test_session-list'), {
            'session_type': self.ep.session_type.name
        }, user=self.user)

        http_host = get_subdomain(resp.json['exposedurl_set'][0]['subdomain'])
        self.app.get(resp.json['exposedurl_set'][0]['subdomain'] + 'unknown/23?tparam1=test&tparam2=test',
                     extra_environ={'HTTP_HOST': '{}-example.com'.format(http_host)}, expect_errors=True)
        report1 = Report.objects.filter(scenario_case=self.sc1).count()
        report2 = Report.objects.filter(scenario_case=self.sc2).count()
        self.assertEqual(report1, 0)
        self.assertEqual(report2, 1)

        self.app.get(resp.json['exposedurl_set'][0]['subdomain'] + 'unknown/23?tparam1=test&',
                     extra_environ={'HTTP_HOST': '{}-example.com'.format(http_host)}, expect_errors=True)
        report1 = Report.objects.filter(scenario_case=self.sc1).count()
        report2 = Report.objects.filter(scenario_case=self.sc2).count()
        self.assertEqual(report1, 1)
        self.assertEqual(report2, 1)

    def test2(self):
        self.test()
        session = Session.objects.all()[0]
        reports = Report.objects.filter(session_log__session=session)
        collection = ScenarioCaseCollectionFactory()
        endpoint = VNGEndpointFactory(scenario_collection=collection)
        scenario_case = ScenarioCase.objects.filter(collection=collection)
        for r in reports:
            r.result = choices.HTTPCallChoices.not_called
            r.save()

        call = self.app.get(reverse('apiv1session:testsession-shield',
            kwargs={
                'uuid': session.uuid
            }
        ))
        self.assertEqual(call.json['message'], 'Not completed')

        reports[0].result = choices.HTTPCallChoices.failed
        reports[0].save()

        call = self.app.get(reverse('apiv1session:testsession-shield',
            kwargs={
                'uuid': session.uuid
            }
        ))
        self.assertEqual(call.json['message'], 'Failed')

        for r in reports:
            r.result = choices.HTTPCallChoices.success
            r.save()

        call = self.app.get(reverse('apiv1session:testsession-shield',
            kwargs={
                'uuid': session.uuid
            }
        ))
        self.assertEqual(call.json['message'], 'Success')
