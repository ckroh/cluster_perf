from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse
from django.core.paginator import Paginator
from overview.models import *
from overview.forms import *
from overview.filter import *
from overview.analysis import *
import json
from django.http import JsonResponse

from collections import OrderedDict
from django.db.models import Count, Max, Avg, F, Func
from django.db.models.expressions import RawSQL

from scipy.optimize import curve_fit
import numpy as np
from scipy import asarray as ar,exp
# Create your views here.

def index(request):
	all_clusters = Cluster.objects.order_by('id')
	return render(request,'overview/index.html',{'all_clusters': all_clusters})
	

#compare performance of nodes: test + test_config + test_config_version + node_type selected
def analysis_node(request):
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
		
			results = f.qs.values('norm_result').order_by('norm_result').annotate(count=Count('norm_result')).order_by('norm_result')
#			try:
			ax=[]
			ay=[]
			for k in results:    
				ax.append(k['norm_result'])
				ay.append(k['count'])
				
			x=np.array(ax)
			y=np.array(ay)
			gauss_x, gauss_y, gauss_popt = node_data(x,y,1)
			lognormal_x, lognormal_y, lognormal_popt = node_data(x,y,5)
#			except:
#				logging.error("error in node_data call") 
#				return render(request,'overview/analysis_nodes.html',{'filter': f})
			mean = sum(x*y) / sum(y)  
			sigma = np.sqrt(sum(y * (x - mean)**2) / sum(y))
#			mu = np.exp(popt[1])
#			dev = np.exp(popt[2])
			mu = gauss_popt[1]
			dev = gauss_popt[2]
			
			
			limmin = mu-2.576*dev
			limmax = mu+2.576*dev
			return render(request,'overview/analysis_nodes.html',{'filter': f, 'gaussy': zip(gauss_x, gauss_y), 'lognormaldat': zip(lognormal_x, lognormal_y), 'x': gauss_x, 'y': zip(x, y), 'maxy': (np.amax(y)+1), 'resultdisplay': resultdisplay, 'limmin': round(limmin,4), 'limmax': round(limmax,4), 'sigma': str(round(dev,3)), 'mean': str(round(mean,3)), 'mu': str(round(mu,3))})
			
			
	return render(request,'overview/analysis_nodes.html',{'filter': f})
		
			
def analysis_test(request):
	cluster = Cluster.objects.all()
	tests = Test.objects.all()
	
	f = ResultTestFilter(request.GET, queryset=Result.objects.exclude(end=None).exclude(result=None).exclude(result=0.0).exclude(result=-1.0).exclude(type='build'))
	
	if ('test_config' in request.GET) and len(f.qs)>0:
		test_config=TestConfig.objects.get(id=request.GET['test_config'])
		#compare test_config_version: test + test_config selected
		tcvs = {}
		test_config_versions=[]
		ntss = {}
		test_config_versions = f.qs.order_by('-test_config_version').distinct('test_config_version')
		results = f.qs.values('node_types__name', 'test_config_version__hash').annotate(avg_result=Max('norm_result')).order_by()
		result_max = f.qs.order_by('-norm_result')[0]
		
		paramsv={}
		for t in test_config_versions:
			paramsv[t.test_config_version.hash]=[]
			for p in t.test_config_version.parameter_values.all():
				paramsv[t.test_config_version.hash].append(p)
		
		par={}
		for t,k in paramsv.items():
			par[t]=[]
			for a,g in paramsv.items():
				if t is not a:
					par[t]=set(par[t]) | (set(k) - set(g))
			
		
		
		paramst={}
		for t,k in par.items():
			paramst[t]=""
			for p in k:
				if paramst[t] is not "":
					paramst[t]+=", " 
				paramst[t]+=str(p.parameter.name)+":"+str(p.value)
		
		
		
		tcvs={}
		labels = []
		nts = []
		for tcv in results:
			if tcv['test_config_version__hash'] not in labels:
				labels.append(str(tcv['test_config_version__hash']))
			if tcv['node_types__name'] not in nts:
				nts.append(str(tcv['node_types__name']))
		nts.sort()
		for tcv in results:
			if str(tcv['test_config_version__hash']) not in tcvs:
				tcvs[str(tcv['test_config_version__hash'])]=OrderedDict()
				for l in nts:
					tcvs[str(tcv['test_config_version__hash'])][str(l)]=0
				
			tcvs[str(tcv['test_config_version__hash'])][str(tcv['node_types__name'])] = round(tcv['avg_result'], 2)
		
		bench_choices=[('empty','None')]
		for r,v in f.qs[0].result_detail.items():
			bench_choices.append((str(r),str(r)))
					
		benchform=ResultBenchSelectForm(request.POST, choices=bench_choices)
		results_bench=[]
		bench_tcvs={}
		bench_max=0
		if 'benchmark' in request.POST and request.POST['benchmark'] is not 'empty':
			bench=request.POST['benchmark'] 
			bench_norm = Result.objects.order_by('end').exclude(result=None, end=None).filter(test_config=test_config, type='run')[0]
			bench_nr_res=bench_norm.result_detail[bench]['time']
			results_bench = f.qs.annotate(val=RawSQL("((result_detail->%s->>%s)::numeric)", (bench,"time",))).values('node_types__name', 'test_config_version__hash').annotate(avg_result=Max('val')).order_by()
			
			
			for tcv in results_bench:
				if str(tcv['test_config_version__hash']) not in bench_tcvs:
					bench_tcvs[str(tcv['test_config_version__hash'])]=OrderedDict()
					for l in nts:
						bench_tcvs[str(tcv['test_config_version__hash'])][str(l)]=0		
				bench_tcvs[str(tcv['test_config_version__hash'])][str(tcv['node_types__name'])] = round(float(bench_nr_res)/float(tcv['avg_result']), 2)
				if bench_tcvs[str(tcv['test_config_version__hash'])][str(tcv['node_types__name'])]>bench_max:
					bench_max=bench_tcvs[str(tcv['test_config_version__hash'])][str(tcv['node_types__name'])]
			#values('node_types__name', 'test_config_version__hash').annotate(benchmark_result=F('result_detail__371.applu331__time')).annotate(avg_result=Avg('benchmark_result'))
			
#		if request.method == 'POST':
#			benchform = ResultBenchSelectForm(request.POST)
		
#		fb = ResultBenchFilter(request.GET, queryset=f.qs)

		return render(request,'overview/analysis_test.html',{'cluster': cluster, 'tests': tests, 'filter_bench': benchform, 'filter': f, 'tcvs':tcvs, 'labels': labels, 'nts':nts, 'test_config_versions': test_config_versions, 'max': result_max.norm_result, 'ress': results, 'rb': results_bench, 'bench_tcvs': bench_tcvs, 'bench_max':bench_max, 'paramst': paramst})
		
		
	return render(request,'overview/analysis_test.html',{'cluster': cluster, 'tests': tests, 'filter': f})

def cluster_detail(request, cluster_id):
	cluster = get_object_or_404(Cluster, id=cluster_id)
	nodes = Node.objects.filter(cluster_id=cluster_id).order_by('-id')
	pagin = Paginator(nodes, 100)
	page = request.GET.get('page')
	nodesdisplay = pagin.get_page(page)
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
		return render(request,'overview/cluster.html',{'cluster': cluster, 'nodes': nodesdisplay, 'node_types': node_types, 'partitions': partitions})
	
def node_type_detail(request, node_type_id):
	node_type = get_object_or_404(NodeType, id=node_type_id)
	return render(request,'overview/cluster.html',{'cluster': cluster, 'nodes': nodes})

def partition_detail(request, partition_id):
	partition = get_object_or_404(Partition, id=partition_id)
	return render(request,'overview/cluster.html',{'cluster': cluster, 'nodes': nodes})
  
def node_detail(request, node_id, cluster_id):
#	cluster = get_object_or_404(Cluster, id=cluster_id)
	node= get_object_or_404(Node, id=node_id)
	result_list = Result.objects.filter(nodes__in=[node]).order_by('-result')
	pagin = Paginator(result_list, 200)
	page = request.GET.get('page')
	resultdisplay = pagin.get_page(page)
	return render(request,'overview/node_detail.html',{'node': node, 'resultdisplay': resultdisplay, 'page': page})
  
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
	
