"""cluster_perf_web URL Configuration


"""
from overview.models import *
from overview.tasks import *


from django.contrib import admin
from django.urls import include,path
from rest_framework import routers, serializers, viewsets
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone

import json



# Serializers define the API representation.
   
class BatchsystemSerializer(serializers.HyperlinkedModelSerializer):
    batchsystem = models.ForeignKey(Batchsystem,  on_delete=models.DO_NOTHING)
    class Meta:
        model = Batchsystem
        fields = ('id','name','header','footer','parameters')
        
class ClusterSerializer(serializers.HyperlinkedModelSerializer):
    batchsystem = models.ForeignKey(Batchsystem,  on_delete=models.DO_NOTHING)
    class Meta:
        model = Cluster
        fields = ('id','name','description','login_node','local_path','remote_path')
        

class NodeTypeSerializer(serializers.HyperlinkedModelSerializer):
    cluster = models.ForeignKey(Cluster,  on_delete=models.DO_NOTHING)
    partition = models.ForeignKey(Partition,  on_delete=models.DO_NOTHING)
    class Meta:
        model = NodeType
        fields = ('id','name','partition','hw_info','created','cluster')
        

class NodeSerializer(serializers.HyperlinkedModelSerializer):
#    test_config = serializers.ReadOnlyField(source='test_config')
    cluster = models.ForeignKey(Cluster,  on_delete=models.DO_NOTHING)
    partition = models.ForeignKey(Partition,  on_delete=models.DO_NOTHING)
    node_type = models.ForeignKey(NodeType,  on_delete=models.DO_NOTHING)

    class Meta:
        model = Node
        fields = ('id','name','cluster','hw_info','hw_info_update','partition','node_type')


class PartitionSerializer(serializers.HyperlinkedModelSerializer):
#    test_config = serializers.ReadOnlyField(source='test_config')
    cluster = models.ForeignKey(Cluster,  on_delete=models.DO_NOTHING)

    class Meta:
        model = Partition
        fields = ('id','name','cluster','description')


class ResultSerializer(serializers.HyperlinkedModelSerializer):
#    test_config = serializers.ReadOnlyField(source='test_config')
    test_config = models.ForeignKey(TestConfig,  on_delete=models.DO_NOTHING)

    class Meta:
        model = Result
        fields = ('id','start', 'end', 'result', 'result_detail', 'test_config', 'job_id', 'test_config_version', 'submit', 'type', 'nodes', 'node_types')
        
        
        
class TestConfigSerializer(serializers.HyperlinkedModelSerializer):
    test = models.ForeignKey(Test,  on_delete=models.DO_NOTHING)
    class Meta:
        model = TestConfig
        fields = ('id','name','test','config','parameter','configfile_extension','needs_configfile','edited','node_types')

        
class TestConfigHistorySerializer(serializers.HyperlinkedModelSerializer):
    test_config = models.ForeignKey(TestConfig, on_delete=models.DO_NOTHING)
    class Meta:
        model = TestConfigHistory
        fields = ('id','test_config','config_diff','parameter_diff','hash','edited','was_built')

        
class TestSerializer(serializers.HyperlinkedModelSerializer):
	class Meta:
		model = Test
		fields = ('id','name','run_script','parameter','multi_node','analysis_script','build_script','needs_building')
     
     
class BatchsystemViewSet(viewsets.ModelViewSet):
    queryset = Batchsystem.objects.all()
    serializer_class = BatchsystemSerializer
class ClusterViewSet(viewsets.ModelViewSet):
    queryset = Cluster.objects.all()
    serializer_class = ClusterSerializer
class NodeViewSet(viewsets.ModelViewSet):
    queryset = Node.objects.all()
    serializer_class = NodeSerializer

class NodeTypeViewSet(viewsets.ModelViewSet):
    queryset = NodeType.objects.all()
    serializer_class = NodeTypeSerializer   
class PartitionViewSet(viewsets.ModelViewSet):
    queryset = Partition.objects.all()
    serializer_class = PartitionSerializer   
class ResultViewSet(viewsets.ModelViewSet):
	queryset = Result.objects.all()
	serializer_class = ResultSerializer
	# http POST http://172.22.1.104:8000/api/results/<id>/hasStarted/ 
	@action(detail=True, methods=['post'])
	def hasStarted(self, request, *args, **kwargs):
		result = self.get_object()
		result.start = timezone.now()
		result.save()
		
	# http POST http://172.22.1.104:8000/api/results/<id>/writeResult/ 
	@action(detail=True, methods=['post'])
	def writeResult(self, request, *args, **kwargs):
		result = self.get_object()
		if 'result' in request.data:
			result.result=request.data['result']
		if 'result_detail' in request.data:
			result.result_detail=json.loads(request.data['result_detail'])
		result.save()
    	
class TestConfigViewSet(viewsets.ModelViewSet):
    queryset = TestConfig.objects.all()
    serializer_class = TestConfigSerializer
    
class TestConfigHistoryViewSet(viewsets.ModelViewSet):
	queryset = TestConfigHistory.objects.all()
	serializer_class = TestConfigHistorySerializer
	
	# http POST http://172.22.1.104:8000/api/test_config_histories/<id>/wasBuilt/ 
	@action(detail=True, methods=['post'])
	def wasBuilt(self, request, *args, **kwargs):
		tcv = self.get_object()
		tcv.was_built = True
		tcv.save()

class TestViewSet(viewsets.ModelViewSet):
	queryset = Test.objects.all()
	serializer_class = TestSerializer
	
	# http POST http://172.22.1.104:8000/api/tests/2/start/ test_config=13 nodes=[6832] tcv_hash=
	@action(detail=True, methods=['post'])
	def start(self, request, *args, **kwargs):
		test = self.get_object()
		test_config = TestConfig.objects.get(id=request.data['test_config'])
		nodes = []
		snodes = json.loads(request.data['nodes'])

		logging.debug("REST API: startTest nodes defined %s" % snodes) 
		for n in snodes:
			nodes.append(Node.objects.get(id=n))
		if len(nodes)==0:
			logging.error("REST API: startTest no nodes defined %s" % request.data) 
		
		if 'tcv_hash' in request.data:
			tcv_hash=request.data['tcv_hash']
		else:
			tcv_hash=None
			
#		RUN TEST:
		task_start_test.delay(test.id, request.data)
#		test.startTest(test_config, nodes, tcv_hash)
		return Response('OK')
		
		
		
# Routers provide an easy way of automatically determining the URL conf.
router = routers.DefaultRouter()
router.register(r'results', ResultViewSet)
router.register(r'test_config_histories', TestConfigHistoryViewSet)
router.register(r'test_configs', TestConfigViewSet)
router.register(r'tests', TestViewSet)
router.register(r'node_types', NodeTypeViewSet)
router.register(r'nodes', NodeViewSet)
router.register(r'cluster', ClusterViewSet)
router.register(r'partition', PartitionViewSet)


urlpatterns = [
    path('overview/', include('overview.urls')),
    path('admin/', admin.site.urls),
    path('api-auth/', include('rest_framework.urls')),
    path('api/', include(router.urls)),

]
