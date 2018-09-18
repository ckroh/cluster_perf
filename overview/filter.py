from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from overview.models import *

#@receiver(pre_save, sender=Result)
#def submit_batchsystem(sender, instance, **kwargs):
#    instance.profile.save()

import django_filters
	
	
	
	
class ResultFilter(django_filters.FilterSet):
	node_types = django_filters.ModelMultipleChoiceFilter(
		
		queryset=NodeType.objects.all()
	)
	class Meta:
		model = Result
		fields = {
			'test_config__test': ['exact'],
			'test_config': ['exact'],
			'test_config_version': ['exact'],
			'test_config_version__parameter_values': ['contains'],
			'nodes': ['exact'],
			'node_types': ['exact'],
			}
	

class ResultBenchFilter(django_filters.FilterSet):	
	result_detail = django_filters.CharFilter(name='result_detail', lookup_expr='has_key')

	class Meta:
		model = Result
		fields = {
			'result_detail': ['exact'],
		}
			
class ResultTestFilter(django_filters.FilterSet):
	node_types = django_filters.ModelMultipleChoiceFilter(		
		queryset=NodeType.objects.all()
	)
	class Meta:
		model = Result
		fields = {
			'test_config': ['exact'],
#			'test_config_version': ['exact'],
#			'test_config_version__parameter_values': ['contains'],
			'node_types': ['exact'],
			}
