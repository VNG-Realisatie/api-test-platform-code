from django import forms

from .models import DesignRuleTestSuite, DesignRuleTestVersion


class DesignRuleTestSuiteForm(forms.ModelForm):
    class Meta:
        model = DesignRuleTestSuite
        fields = ("api_endpoint", )


class DesignRuleSessionStart(forms.Form):
    test_version = forms.ModelChoiceField(queryset=DesignRuleTestVersion.objects.filter(is_active=True))
    specification_url = forms.URLField(required=None)
