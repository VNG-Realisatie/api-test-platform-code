from django.http.response import JsonResponse
from django.shortcuts import get_object_or_404

from rest_framework import mixins, permissions
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter

from vng.api_authentication.authentication import CustomTokenAuthentication
from vng.design_rules.models import DesignRuleTestSuite, DesignRuleSession, DesignRuleTestVersion
from vng.servervalidation.serializers import ServerRunResultShield

from .serializers import DesignRuleSessionSerializer, DesignRuleTestSuiteSerializer, DesignRuleTestVersionSerializer, StartSessionSerializer


START_SESSION_DESCRIPTION = "Start a new session for an existing Design rule Test suite. This will generate new results, without having to add the endpoint(s) again."


class DesignRuleTestVersionViewSet(mixins.ListModelMixin, GenericViewSet):
    """
    list:
    Get all the Design rule Test versions that are active.
    """
    authentication_classes = (CustomTokenAuthentication, SessionAuthentication)
    permission_classes = (permissions.IsAuthenticated, )
    queryset = DesignRuleTestVersion.objects.filter(is_active=True)
    serializer_class = DesignRuleTestVersionSerializer


class DesignRuleTestSuiteViewSet(mixins.CreateModelMixin, mixins.RetrieveModelMixin, mixins.ListModelMixin, GenericViewSet):
    """
    list:
    Get all the Design rule Test suites that are registered.
    create:
    Create a new Design rule Test suite.
    - This will start a Design rule session. The session is returned in the session list.
    read:
    Get a single Design rule Test suite.
    """
    authentication_classes = (CustomTokenAuthentication, SessionAuthentication)
    permission_classes = (permissions.IsAuthenticated, )
    queryset = DesignRuleTestSuite.objects.all()
    serializer_class = DesignRuleTestSuiteSerializer
    lookup_field = 'uuid'

    @extend_schema(description=START_SESSION_DESCRIPTION, request=StartSessionSerializer, responses={201: DesignRuleSessionSerializer})
    @action(detail=True, methods=['post'], description="Start a new session for the test suite")
    def start_session(self, request, uuid=None):
        serializer = StartSessionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = self.get_object()
        obj.start_session(serializer.data.get("test_version"), serializer.data.get("specification_url", ""))

        serializer = DesignRuleSessionSerializer(instance=obj.get_latest_session())
        return Response(serializer.data, status=201)


class DesignRuleSessionViewSet(mixins.RetrieveModelMixin, mixins.ListModelMixin, GenericViewSet):
    """
    list:
    Get all the Design rule sessions that are registered.
    read:
    Get a single Design rule session.
    """
    authentication_classes = (CustomTokenAuthentication, SessionAuthentication)
    permission_classes = (permissions.IsAuthenticated, )
    queryset = DesignRuleSession.objects.all()
    serializer_class = DesignRuleSessionSerializer
    lookup_field = 'uuid'


class DesignRuleSessionShieldView(APIView):
    queryset = DesignRuleSession.objects.all()
    serializer_class = DesignRuleSessionSerializer
    lookup_field = 'uuid'

    @extend_schema(description="Get the shields.io badge for a session.", responses={200: ServerRunResultShield})
    def get(self, request, uuid=None):
        """
        Get the shield badge to display on a website.
        """
        session = get_object_or_404(DesignRuleSession, uuid=uuid)

        if session.percentage_score == 100:
            color = 'green'
            is_error = False
        else:
            color = 'red'
            is_error = True

        result = {
            'schemaVersion': 1,
            'label': 'ATP Design rules',
            'message': session.percentage_score,
            'color': color,
            'isError': is_error,
        }

        return JsonResponse(result)
