"""cluster_perf_web URL Configuration
	defining rest api viewsets, serializers and routers

"""
from overview.models import *
from overview.tasks import *


from django.contrib import admin
from django.urls import include,path
from rest_framework import routers, serializers, viewsets, permissions
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser

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
        fields = ('id','name','test','config','configfile_extension','needs_configfile','edited','node_types')

        
class TestConfigHistorySerializer(serializers.HyperlinkedModelSerializer):
    test_config = models.ForeignKey(TestConfig, on_delete=models.DO_NOTHING)
    class Meta:
        model = TestConfigHistory
        fields = ('id','test_config','hash','edited','was_built')

        
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
    
    def get_queryset(self):
	    queryset = Node.objects.all()
	    node_type = self.request.query_params.get('node_type', None)
	    partition = self.request.query_params.get('partition', None)
	    if node_type is not None:
		    queryset = queryset.filter(node_type__id=node_type)
	    if partition is not None:
		    queryset = queryset.filter(partition__id=partition)
	    return queryset

class NodeTypeViewSet(viewsets.ModelViewSet):
    queryset = NodeType.objects.all()
    serializer_class = NodeTypeSerializer   
class PartitionViewSet(viewsets.ModelViewSet):
    queryset = Partition.objects.all()
    serializer_class = PartitionSerializer   
class ResultViewSet(viewsets.ModelViewSet):
	queryset = Result.objects.all()
	serializer_class = ResultSerializer
	# http -a system:manual_3034 POST http://172.22.1.104:8000/api/results/<id>/hasStarted/ 
	@action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
	def hasStarted(self, request, *args, **kwargs):
		result = self.get_object()
		result.start = timezone.now()
		result.save()
		return Response('OK')
	# http -a system:manual_3034 POST http://172.22.1.104:8000/api/results/<id>/setNode/ 
	@action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
	def setNode(self, request, *args, **kwargs):
		result = self.get_object()
		try:
			logging.debug("detting node '%s' for result %s", request.data['node_name'], result.id)
			n=Node.objects.get(name=request.data['node_name'])
		except Node.DoesNotExist:
			logging.error("Node does not exist: '%s'", request.data['node_name']) 
			return Response('OK')
			
		res_node=ResultNode(node=n, result=result, node_type=n.node_type)
		res_node.save()
		return Response('OK')
		
	# http -a system:manual_3034 POST http://172.22.1.104:8000/api/results/<id>/writeResult/ 
	@action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
	def writeResult(self, request, *args, **kwargs):
		result = self.get_object()
		if 'result' in request.data:
			logging.debug("result ID %s from request: '%s'", result.id, request.data['result'])
			if request.data['result'] is not '':
				try:
					result.result = float(request.data['result'])
				except:
					result.result = -1.0
			else:
				result.result = -1.0
				

		if 'result_detail' in request.data:
			result.result_detail=request.data['result_detail']
		result.end = timezone.now()
		result.save()
		return Response('OK')
    	
class TestConfigViewSet(viewsets.ModelViewSet):
    queryset = TestConfig.objects.all()
    serializer_class = TestConfigSerializer
    
class TestConfigHistoryViewSet(viewsets.ModelViewSet):
	queryset = TestConfigHistory.objects.all()
	serializer_class = TestConfigHistorySerializer
	
	# http -a system:manual_3034 POST http://172.22.1.104:8000/api/test_config_histories/<id>/wasBuilt/ 
	@action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
	def wasBuilt(self, request, *args, **kwargs):
		tcv = self.get_object()
		tcv.was_built = True
		tcv.save()
		return Response('OK')

class TestViewSet(viewsets.ModelViewSet):
	queryset = Test.objects.all()
	serializer_class = TestSerializer
	

	
	# http -a system:manual_3034 POST http://172.22.1.104:8000/api/tests/2/start/ test_config=13 nodes=[6832] parameter=[] hash=[]
	@action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
	def start(self, request, *args, **kwargs):
		logging.debug("REST API: startTest task in celery") 
		test = self.get_object()
#		RUN TEST through celery:
		task_start_test.delay(test.id, request.data)
		return Response('OK')
	
	# http -a system:manual_3034 POST http://172.22.1.104:8000/api/tests/2/startArray/ test_config=13 nodes=[6832] parameter=[] hash=
	@action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
	def startArray(self, request, *args, **kwargs):
		logging.debug("REST API: startTest task in celery") 
		test = self.get_object()
#		RUN TEST:
		task_start_test_array.delay(test.id, request.data)
		return Response('OK')
		
		
		
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
