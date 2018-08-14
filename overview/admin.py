from django.contrib import admin
from django.contrib.postgres.fields import JSONField

from overview.models import *
# Register your models here.






class ResultAdmin(admin.ModelAdmin):
	fieldsets = [(None, 	{'fields': ['start','end','test_config','test_config_version','result','norm_result','result_detail', 'type', 'submit']}),]
	list_filter = ['start','end', 'submit', 'type','test_config','test_config_version']
	list_display = ('start','end','type','result','norm_result')
	actions = ['update_norm_result']

	def update_norm_result(self, request, queryset):
	#    queryset.update(status='p')
		for r in queryset.all():
			if r.result is not None and r.result > 0.0:
				try:
					nr = Result.objects.order_by('start').exclude(result=None, end=None).filter(test_config=r.test_config, type=r.type)[0]
				except Result.DoesNotExist:
					r.norm_result = 1.0
				else:
					r.norm_result = round(nr.result/r.result, 2)
				
				r.save()
	update_norm_result.short_description = "Update Normalized Result of Selected Results"
    
class TestconfigNodetypeAdmin(admin.ModelAdmin):
    pass
    
class TestConfigHistoryParameterValueInline(admin.StackedInline):
	model = TestConfigHistory.parameter_values.through
#	filter_horizontal = ('parameter_values',)
	extra = 0
    
class TestConfigInline(admin.StackedInline):
	model = TestConfig
	filter_horizontal = ('node_types',)
	extra = 0
	
class ParameterValueInline(admin.StackedInline):
	model = ParameterValue
	extra = 0
	
class ParameterAdmin(admin.ModelAdmin):
	fieldsets = [(None, 	{'fields': ['name', 'type']}),
	]
	extra = 0
	inlines = [ParameterValueInline]
    
class TestConfigHistoryAdmin(admin.ModelAdmin):
	list_display = ('hash', 'test_config', 'was_built','edited')
	fieldsets = [(None, 	{'fields': ['hash','test_config', 'was_built']}),
	]
	inlines = [TestConfigHistoryParameterValueInline]
    
    
class TestAdmin(admin.ModelAdmin):
	fieldsets = [(None, 	{'fields': ['name', 'run_script', 'analysis_script', 'build_script', 'needs_building', 'multi_node']}),
	]
	inlines = [TestConfigInline]
    
    
class NodeTypeInline(admin.StackedInline):
    model = NodeType
    extra = 0
    
class PartitionInline(admin.StackedInline):
    model = Partition
    extra = 0


    
class ClusterAdmin(admin.ModelAdmin):
	list_display = ('name', 'login_node', 'batchsystem')
	fields = ['name', 'login_node', 'description', 'batchsystem', 'remote_path', 'local_path']
	inlines = [PartitionInline, NodeTypeInline]
	actions = ['init_nodes']
	
	def init_nodes(self, request, queryset):
	#    queryset.update(status='p')
		for c in queryset:
			c.batchsystem.initNodes(c)
	init_nodes.short_description = "Search for Nodes and Partitions on selected Clusters"

class NodeAdmin(admin.ModelAdmin):
	fieldsets = [(None, 	{'fields': ['name', 'cluster', 'hw_info', 'partition', 'node_type']}),]
	list_filter = ['cluster__name', 'partition__name', 'node_type__name']
 	


#class ResultAdmin(admin.ModelAdmin):
#	fieldsets = [(None, 	{'fields': ['name', 'cluster', 'hw_info', 'partition', 'node_types']}),]
#	list_filter = ['start','end','type','cluster__name', 'partition__name', 'node_type__name']
 	
 	
admin.site.register(TestConfigHistory, TestConfigHistoryAdmin)
admin.site.register(Result, ResultAdmin)
admin.site.register(Test, TestAdmin)
admin.site.register(Parameter, ParameterAdmin)
admin.site.register(Cluster, ClusterAdmin)
admin.site.register(Node, NodeAdmin)
admin.site.register(TestconfigNodetype, TestconfigNodetypeAdmin)
