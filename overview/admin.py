from django.contrib import admin
from django.contrib.postgres.fields import JSONField

from .models import *
# Register your models here.


class TestconfigNodetypeAdmin(admin.ModelAdmin):
    pass
    
class TestConfigInline(admin.StackedInline):
	model = TestConfig
	filter_horizontal = ('node_types',)
	extra = 0
    
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
 	

class NodeAdmin(admin.ModelAdmin):
	fieldsets = [(None, 	{'fields': ['name', 'cluster', 'hw_info', 'partition', 'node_type']}),]
	list_filter = ['cluster__name', 'partition__name', 'node_type__name']
 	


class ResultAdmin(admin.ModelAdmin):
	fieldsets = [(None, 	{'fields': ['name', 'cluster', 'hw_info', 'partition', 'node_type']}),]
	list_filter = ['cluster__name', 'partition__name', 'node_type__name']
 	
 	
admin.site.register(Test, TestAdmin)
admin.site.register(Cluster, ClusterAdmin)
admin.site.register(Node, NodeAdmin)
admin.site.register(TestconfigNodetype, TestconfigNodetypeAdmin)
