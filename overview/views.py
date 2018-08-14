from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse
from django.core.paginator import Paginator
from overview.models import *
from overview.forms import *
from overview.filter import *
import json
from django.http import JsonResponse
from django.db.models import Count

from scipy.optimize import curve_fit
import numpy as np
from scipy import asarray as ar,exp

# Create your views here.

def index(request):
	all_clusters = Cluster.objects.order_by('id')
	return render(request,'overview/index.html',{'all_clusters': all_clusters})
	

#compare performance of nodes: test + test_config + test_config_version + node_type selected
def analysis_node(request):
	cluster = Cluster.objects.all()
	tests = Test.objects.all()
	
	f = ResultFilter(request.GET, queryset=Result.objects.exclude(end=None).exclude(result=0.0).exclude(result=-1.0).exclude(result=None).exclude(type='build'))
	
	result_list = f.qs.order_by('-result')
	pagin = Paginator(result_list, 200)
	page = request.GET.get('page')
	resultdisplay = pagin.get_page(page)

	
	if ('test_config__test' in request.GET) and ('test_config' in request.GET) and ('test_config_version' in request.GET) and ('node_types' in request.GET):
		#compare test_config_version: test + test_config selected
		logging.debug("analysis_node request valid")
		results = {}
		
		test_config_versions=[]
		if len(f.qs)>0:
		
			results = f.qs.values('norm_result').order_by('norm_result').annotate(count=Count('norm_result'))
			aa=[]
			aaa=[]
			for k in results:
				aa.append((float(k['norm_result']), k['count']))
			aaa=sorted(aa, key=lambda x: x[0])
			ax=[]
			ay=[]
			maxx=0
			maxy=0
			end=0
			for k,v in aaa:
				if len(ax) ==0:
					maxx=k	
				if v>maxy:
					maxy=v
				end=k
				ax.append(k)
				ay.append(v)
			
			x=np.array(ax)
			y=np.array(ay)
			n = len(x)                         
			mean = sum(x*y) / sum(y)                
			sigma = np.sqrt(sum(y * (x - mean)**2) / sum(y))

			def gauss(x,a,x0,sigma):
				return a * np.exp(-(x - x0)**2 / (2 * sigma**2))

			lim = mean-2*sigma
			try:
				popt,pcov = curve_fit(gauss,x,y,p0=[max(y),mean,sigma], maxfev=7000)
			except:				
				logging.error("node analysis curve fit overflow") 
				return render(request,'overview/analysis_nodes.html',{'cluster': cluster, 'tests': tests, 'filter': f, 'resultdisplay': resultdisplay})
			gaussy = []
			for i in x:
				gaussy.append(gauss(i,*popt))
			return render(request,'overview/analysis_nodes.html',{'cluster': cluster, 'tests': tests, 'filter': f, 'gaussy':gaussy, 'x': x, 'y': y, 'maxy': (maxy+1), 'resultdisplay': resultdisplay, 'lim': str(round(lim,2)), 'sigma': str(round(sigma,2)), 'mean': str(round(mean,2))})
	return render(request,'overview/analysis_nodes.html',{'cluster': cluster, 'tests': tests, 'filter': f})
		
			
def analysis_test(request):
	cluster = Cluster.objects.all()
	tests = Test.objects.all()
	
	f = ResultFilter(request.GET, queryset=Result.objects.exclude(end=None).exclude(result=None).exclude(result=0.0).exclude(result=-1.0).exclude(type='build'))
	
	if ('test_config__test' in request.GET) and ('test_config' in request.GET):
		#compare test_config_version: test + test_config selected
		tcvs = {}
		test_config_versions=[]
		ntss = {}
		for r in f.qs:
			if r.test_config_version.hash not in tcvs:
				test_config_versions.append(r.test_config_version)
				tcvs[r.test_config_version.hash]={}
			for nt in r.node_types.all():
				if nt.name not in ntss:
					ntss[nt.name]=0
				if nt.name in tcvs[r.test_config_version.hash]:
					tcvs[r.test_config_version.hash][nt.name]['sum'] += float(r.result)
					tcvs[r.test_config_version.hash][nt.name]['count'] += 1
				else:	
					tcvs[r.test_config_version.hash][nt.name]={}
					tcvs[r.test_config_version.hash][nt.name]['sum'] = r.result
					tcvs[r.test_config_version.hash][nt.name]['count'] = 1
			
		
		for tcv in tcvs:
			for nt in ntss:
				if nt not in tcvs[tcv]:
					tcvs[tcv][nt]={}
					tcvs[tcv][nt]['sum'] = 0
					tcvs[tcv][nt]['count'] = 0
					tcvs[tcv][nt]['mean'] = 0
		nts = {}
		tcvnts = {}
		m=0
		for tcv in tcvs:
			for nt in tcvs[tcv]:
				if nt not in nts:
					nts[nt]=[]
					ntss[nt]=[]
				if tcvs[tcv][nt]['count']>0:
					tcvs[tcv][nt]['mean'] = round(tcvs[tcv][nt]['sum']/tcvs[tcv][nt]['count'])
				else: 
					tcvs[tcv][nt]['mean'] = 0
				nts[nt].append(tcvs[tcv][nt]['mean'])
				if max(nts[nt])>m:
					m =max(nts[nt])
				ntss[nt]=max(nts[nt])
			
				
		labels = []
		for tcv in tcvs:
			labels.append(str(tcv))

		return render(request,'overview/analysis_test.html',{'cluster': cluster, 'tests': tests, 'filter': f, 'tcvs':tcvs, 'labels': labels, 'nts':ntss, 'test_config_versions': test_config_versions, 'max':m})
	return render(request,'overview/analysis_test.html',{'cluster': cluster, 'tests': tests, 'filter': f})

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
			runform = RunTestForm(test_config_id=test_config_id, initial={'test_config': test_config_id})
	
		testconfigversions = TestConfigHistory.objects.filter(test_config_id=test_config_id)
		return render(request,'overview/test_config.html',{'config': config, 'testconfigversions': testconfigversions, 'runform': runform})
	
