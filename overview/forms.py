from django import forms
from .models import *


class RunTestForm(forms.Form):
	test_config = forms.ModelChoiceField(queryset=TestConfig.objects.all(), widget=forms.HiddenInput())
	test_config_hash = forms.ModelChoiceField(queryset=TestConfigHistory.objects.all(), label='Config Hash')
	
	nodes = forms.ModelMultipleChoiceField(queryset=Node.objects.all(), label='Run on Node(s)')
	
	def __init__(self, *args, **kwargs):
		test_config_id = kwargs.pop('test_config_id', None)
		super(RunTestForm, self).__init__(*args, **kwargs)

		if test_config_id:
			self.fields['test_config_hash'].queryset = TestConfigHistory.objects.filter(test_config__id=test_config_id)

	
	
class RunTestMultiNodeForm(forms.Form):
	test_config = forms.ModelChoiceField(queryset=TestConfig.objects.all(), widget=forms.HiddenInput())
	test_config_hash = forms.ModelChoiceField(queryset=TestConfigHistory.objects.all())
	
	nodes = forms.ModelMultipleChoiceField(queryset=Node.objects.all())
	
	
class TestClusterSettings(forms.Form):
	cluster = forms.ModelChoiceField(queryset=Cluster.objects.all(), widget=forms.HiddenInput())
	
	
	
class ResultBenchSelectForm(forms.Form):
	benchmark = forms.CharField(label='Select Detail to Display', widget=forms.Select(choices=[('empty','Empty')]))
	
	def __init__(self, *args, **kwargs):
		choices=kwargs.pop('choices', None)
		super(ResultBenchSelectForm, self).__init__(*args, **kwargs)
		self.fields['benchmark']=forms.CharField(label='Select Detail to Display', widget=forms.Select(choices=choices))
	

