from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse
from .models import *
from .forms import *

# Create your views here.

def index(request):
	all_clusters = Cluster.objects.order_by('id')
	return render(request,'overview/index.html',{'all_clusters': all_clusters})
	
def cluster_detail(request, cluster_id):
	cluster = get_object_or_404(Cluster, id=cluster_id)
	nodes = Node.objects.filter(cluster_id=cluster_id)
	node_types = NodeType.objects.filter(cluster_id=cluster_id)
	if cluster.batchsystem.name == "SLURM":
		partitions = Partition.objects.filter(cluster_id=cluster_id)
	else:
		partitions = None
	
	if request.method == 'POST':
		
		testform = TestClusterSettings(request.POST)
		try:
			cluster.connect()
			if cluster.connection == None:
				ssh_status = 'FAILED'
				remote_path_status = 'Can not check'
			else:
				ssh_status = 'SUCCESS'
				stdin, stdout, stderr = cluster.connection.exec_command('[ ! -d '+cluster.remote_path+' ] && echo \'Directory not found\'')
				remote_path_status = None
				for line in stdout:
					remote_path_status = line.strip('\n')
				if remote_path_status == None:
					remote_path_status = "EXISTS"
			
				cluster.disconnect()	
		except:
			ssh_status = 'FAILED'
		
		if not os.path.exists(cluster.local_path):
			local_path_status = "DOES NOT EXIST"
		else:
			local_path_status = "EXISTS"
			
		
		return render(request,'overview/cluster_check.html',{'cluster': cluster, 'ssh_status': ssh_status, 'remote_path_status': remote_path_status, 'local_path_status': local_path_status})
#		
	else:
		testform = TestClusterSettings(initial={'cluster': cluster_id})
		return render(request,'overview/cluster.html',{'cluster': cluster, 'nodes': nodes, 'node_types': node_types, 'partitions': partitions})
	
def node_type_detail(request, node_type_id):
	node_type = get_object_or_404(NodeType, id=node_type_id)
	return render(request,'overview/cluster.html',{'cluster': cluster, 'nodes': nodes})

def partition_detail(request, partition_id):
	partition = get_object_or_404(Partition, id=partition_id)
	return render(request,'overview/cluster.html',{'cluster': cluster, 'nodes': nodes})
  
def node_detail(request, node_id):
	cluster = get_object_or_404(Cluster, id=cluster_id)
	nodes= Node.objects.filter(cluster_id=cluster_id)
	return render(request,'overview/cluster.html',{'cluster': cluster, 'nodes': nodes})
  
def test_list(request):
	tests = Test.objects.all()
	return render(request,'overview/test.html',{'tests': tests})


def test_detail(request, test_id):
	test = get_object_or_404(Test, id=test_id)
	testconfigs = TestConfig.objects.filter(test_id=test_id)
	return render(request,'overview/test_detail.html',{'test': test,'testconfigs': testconfigs})
	
	

def test_config(request, test_id, test_config_id):
	test = get_object_or_404(Test, id=test_id)
	if request.method == 'POST':
		# create a form instance and populate it with data from the request:
		if test.multi_node == True:
			runform = RunTestMultiNodeForm(request.POST)			
		else:
			runform = RunTestForm(request.POST)
		# check whether it's valid:
		if runform.is_valid():
			# process the data in form.cleaned_data as required
			# ...
			# redirect to a new URL:
			return HttpResponseRedirect('/run_test/')

	# if a GET (or any other method) we'll create a blank form
	else:
		config = get_object_or_404(TestConfig, id=test_config_id)
		if test.multi_node == True:
			runform = RunTestMultiNodeForm(initial={'test_config': test_config_id})			
		else:
			runform = RunTestForm(initial={'test_config': test_config_id})
	
		testconfigversions = TestConfigHistory.objects.filter(test_config_id=test_config_id)
		return render(request,'overview/test_config.html',{'config': config, 'testconfigversions': testconfigversions, 'runform': runform})
	
