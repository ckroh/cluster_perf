from django import forms
from .models import *


class RunTestForm(forms.Form):
	test_config = forms.ModelChoiceField(queryset=TestConfig.objects.all(), widget=forms.HiddenInput())
	test_config_hash = forms.ModelChoiceField(queryset=TestConfigHistory.objects.all(), label='Config Hash')
	
	nodes = forms.ModelMultipleChoiceField(queryset=Node.objects.all(), label='Run on Node(s)')
	
	
class RunTestMultiNodeForm(forms.Form):
	test_config = forms.ModelChoiceField(queryset=TestConfig.objects.all(), widget=forms.HiddenInput())
	test_config_hash = forms.ModelChoiceField(queryset=TestConfigHistory.objects.all())
	
	nodes = forms.ModelMultipleChoiceField(queryset=Node.objects.all())
	
	
class TestClusterSettings(forms.Form):
	cluster = forms.ModelChoiceField(queryset=Cluster.objects.all(), widget=forms.HiddenInput())
	
