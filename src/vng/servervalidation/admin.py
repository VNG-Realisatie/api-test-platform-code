from django.contrib import admin
from django import forms
import vng.servervalidation.models as model

from ordered_model.admin import OrderedModelAdmin
from django_admin_relation_links import AdminChangeLinksMixin
from guardian.admin import GuardedModelAdmin

from vng.testsession.models import SessionType

from .forms import CustomAdminUserObjectPermissionsForm, CustomAdminGroupObjectPermissionsForm

def get_all_fields(mo):
    l = [field.name for field in mo._meta.fields]
    l.remove('id')
    return l


class EndpointInline(admin.TabularInline):
    model = model.Endpoint
    raw_id_fields = ('server_run',)

class ServerHeaderInline(admin.TabularInline):
    model = model.ServerHeader

    raw_id_fields = ('server_run', )

class TestScenarioUrlInline(admin.TabularInline):
    model = model.TestScenarioUrl


class PostmanTestInline(admin.TabularInline):
    model = model.PostmanTest


class APIForm(forms.ModelForm):
    class Meta:
        model = model.API
        fields = '__all__'

    test_scenarios = forms.ModelMultipleChoiceField(queryset=model.TestScenario.objects.all(), required=False)
    session_types = forms.ModelMultipleChoiceField(queryset=SessionType.objects.all(), required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance:
            self.fields['test_scenarios'].initial = self.instance.testscenario_set.all()
            self.fields['session_types'].initial = self.instance.sessiontype_set.all()

    def save(self, *args, **kwargs):
        instance = super().save(commit=False)
        self.fields['test_scenarios'].initial.update(api=None)
        self.fields['session_types'].initial.update(api=None)

        instance.save()
        self.cleaned_data['test_scenarios'].update(api=instance)
        self.cleaned_data['session_types'].update(api=instance)
        return instance


@admin.register(model.API)
class APIAdmin(GuardedModelAdmin):
    list_display = ['name']

    form = APIForm

    def get_obj_perms_base_context(self, request, obj):
        context = super().get_obj_perms_base_context(request, obj)
        permission_codes = [code for code, _ in obj._meta.permissions]
        context["model_perms"] = context["model_perms"].filter(codename__in=permission_codes)
        return context

    def get_obj_perms_manage_group_form(self, request):
        return CustomAdminGroupObjectPermissionsForm

    def get_obj_perms_manage_user_form(self, request):
        return CustomAdminGroupObjectPermissionsForm


@admin.register(model.PostmanTest)
class PostmanTestAdmin(AdminChangeLinksMixin, OrderedModelAdmin):
    list_display = ['name', 'version', 'test_scenario', 'move_up_down_links',
                    'published_url', 'validation_file']


@admin.register(model.PostmanTestResult)
class PostmanTestResultAdmin(admin.ModelAdmin):
    list_display = ['id', 'postman_test', 'log', 'server_run', 'log_json']


@admin.register(model.Endpoint)
class EndpointAdmin(admin.ModelAdmin):
    list_display = ['test_scenario_url', 'environment', 'jwt', 'server_run', 'url']
    list_filter = ['test_scenario_url', 'environment', 'server_run', 'url']
    search_fields = ['test_scenario_url__name', 'server_run__id', 'url']


@admin.register(model.ScheduledTestScenario)
class ScheduledTestScenarioAdmin(admin.ModelAdmin):
    list_display = ['environment']
    list_filter = ['environment']


@admin.register(model.Environment)
class EnvironmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'test_scenario']
    list_filter = ['test_scenario',]

    inlines = [EndpointInline, ServerHeaderInline]
    raw_id_fields = ('server_run', )

@admin.register(model.ServerRun)
class ServerRunAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'uuid',
        'test_scenario',
        'started',
        'stopped',
        'user',
        'status',
        'client_id',
        'secret',
        'percentage_exec',
        'status_exec',
        'scheduled'
    ]
    list_filter = ['user']
    search_fields = ['user__username']

    inlines = [EndpointInline]


@admin.register(model.TestScenario)
class TestScenarioAdmin(admin.ModelAdmin):
    list_display = ['name', 'active', 'public_logs']
    list_filter = ['name']
    list_editable = ('active', 'public_logs')
    search_fields = ['name']

    inlines = [TestScenarioUrlInline, PostmanTestInline]


@admin.register(model.TestScenarioUrl)
class TestScenarioUrlAdmin(admin.ModelAdmin):
    list_display = ['name', 'test_scenario']
    list_filter = ['name', 'test_scenario']
    search_fields = ['name', 'test_scenario__name']
