# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey has `on_delete` set to the desired behavior.
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.contrib.postgres.fields import JSONField
from django.db import models
from django.conf import settings
#from django.core.signals import *
from django.db.models.signals import *
from django.dispatch import receiver

from django.utils import timezone

#from overview.tasks import task_cluster_init


from shutil import copyfile,copytree
import logging
import os
from crontab import CronTab
import hashlib
import math
import numpy as np
from numpy import linalg as LA
import xml.etree.ElementTree as ET
import difflib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn import manifold
import paramiko
import io
import sys
import re




logging.basicConfig(filename=os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir))+'/cluster_perf.log',level=logging.DEBUG, format='%(asctime)s - %(levelname)s: %(message)s')


def getPath(area=None, root=None):
	if root==None:
		root = settings.CP_PATH
	
	if area is "tests":
		return root + "/tests"
	if area is "core":
		return root + "/core"
	if area is "lib":
		return root + "/core/lib"
	if area is "include":
		return root + "/core/include"
	else:
		return root

class Batchsystem(models.Model):
	id = models.BigAutoField(primary_key=True)
	name = models.CharField(max_length=100)
	header = models.TextField(blank=True, null=True)
	parameters = JSONField()
	footer = models.TextField(blank=True, null=True)

	connection = None
	def __str__(self):
		return self.name

	def initNodes(self, cluster):
		if self.name == "PBS":
		    self.initPBSNodes(cluster)	
		    
		elif self.name == "SLURM":
		    self.initSLURMNodes(cluster)	
		else:
		    logging.error("Batchsystem: Cluster has unknown batchsystem '%s'", self.name)

	def initSLURMNodes(self, cluster):
		cluster.connect()
		stdin, stdout, stderr = cluster.connection.exec_command('sinfo -a -N -h')

		#		for line in stderr:
		#			print line.strip('\n')
		logging.debug("sinfo from cluster %s: %s", cluster.name, stdout)
		logging.debug("sinfo error from cluster %s: %s", cluster.name, stderr)
		prev_n = ""
		prev_p = ""
		count_p = 0
		count_n = 0
		for line in stdout:
		    #print line.strip('\n')
			m = re.search('(\w+)[ ]+1[ ]+([\w\*]+)', line.strip('\n'))
		    #print m.group(1) + ":" + m.group(2)
			if m.group(1)==prev_n:
				prev_n = m.group(1)
				prev_p = m.group(2)
				continue			
			elif prev_n!="":
		#				print prev_n + ":" + prev_p
				try:
					p = Partition.objects.get(cluster=cluster, name=prev_p)
					logging.info("Batchsystem: Partition %s already exists inside the database", prev_p)				
				except Partition.DoesNotExist:
					p = Partition(name = prev_p, cluster=cluster)
					p.save()
					count_p += 1

				try:
					nt = NodeType.objects.get(cluster=cluster, name=prev_p)
					logging.info("Batchsystem: NodeType %s already exists inside the database", prev_p)		
				except NodeType.DoesNotExist:
					nt = NodeType(name = prev_p, cluster=cluster, partition=p)
					nt.save()
				    
				try:
					n = Node.objects.get(cluster=cluster, partition = p, name=prev_n, node_type=nt)
					logging.info("Batchsystem: Node %s already exists inside the database", prev_n)
				except Node.DoesNotExist:
					n = Node(name = prev_n, cluster = cluster, partition = p, node_type=nt)
					n.save()
					count_n += 1
				prev_n = m.group(1)
				prev_p = m.group(2)
			else:				
				prev_n = m.group(1)
				prev_p = m.group(2)

		cluster.disconnect()
		logging.info("Batchsystem: %s new Nodes and %s Partitions were added to the Cluster '%s'", str(count_n), str(count_p), cluster.name)

	def initPBSNodes(self, cluster):
		stdin, stdout, stderr = cluster.connection.exec_command('pbsnodes -x')
		#		pbsnodes = subprocess.check_output(['pbsnodes', '-x'])
		pbsnodes=""	
		for line in stdout:
		    pbsnodes += line.strip('\n')
		root = ET.fromstring(pbsnodes)
		count = 0

		for child in root:
		    try:
			    n = Node.objects.get(cluster=cluster, name=child[0].text)
			    logging.info("Batchsystem: Node %s already exists inside the database", prev_n)
		    except Node.DoesNotExist:
			    n = Node(name = child[0].text, cluster = cluster)
			    n.save()
			    count = count + 1

		logging.info("Batchsystem: %s new Nodes were added to the Cluster '%s'", cluster.name, str(count))
		
	def getEnvironmentVariables(self,parameters):
		ret = ""
		if self.name=="PBS":
		    ret = "-v "
		    res=""
		    for v in parameters['env']:
			    if len(res)>0:
				    res = res +','
			    res = res + v + "=" + str(parameters['env'][v])
		    ret += res
		    
		elif self.name=="SLURM":
		    ret = "--export="
		    for v in parameters['env']:
			    if len(ret)>9:
				    ret += ','
			    ret += v + "=" + str(parameters['env'][v])
		return ret

	def getBatchsystemVariables(self, parameters):
		res = ""
		if self.name=="PBS":
			res += " -o " + parameters['bs']['output']
			#res += ["-q", "k80"]
			res += " -e " + parameters['bs']['error']
			res += " -N " + parameters['bs']['job_name']

			if 'NumNodes' in parameters['bs']:
				#TODO
				res += " -l nodes=" + parameters['bs']['NumNodes'] + ":" + parameters['bs']['nodes']
			else:
				res += " -l nodes=" + parameters['bs']['nodes']
				
			if 'TimeLimit' in parameters['bs']:
				res += " -l walltime=" + parameters['bs']['TimeLimit']

		elif self.name=="SLURM":
			res += " -e "+ parameters['bs']['error']+"/job.%J.err" 
			res += " -o "+ parameters['bs']['output']+"/job.%J.out"
			res += " -J " + parameters['bs']['job_name']
			res += " --ntasks-per-node=1"
			#			res += " -N " + str(parameters['bs']['node_count'])
			if 'TestAction' not in parameters['env']:
				res += " --nodelist=" + parameters['bs']['nodes']
			#DEBUG
			res += " --nodes=1"
			res += " --exclusive"

			if 'NumNodes' in parameters['bs']:
				#TODO
				res += " --nodes=" + parameters['bs']['NumNodes'] 
			if 'NumTasks' in parameters['bs']:
				#TODO
				res += " --ntasks=" + parameters['bs']['NumTasks'] 

			res += " -p " + parameters['bs']['partition']
			if 'TimeLimit' in parameters['bs']:
				res += " --time=" + parameters['bs']['TimeLimit']
			if 'account' in parameters['bs']:
				res += " -A "+ parameters['bs']['account']
			return res

	def getParameters(self, cluster, nodes, test, test_config, tcv, result, additional_parameter=None):
		parameters={'env':{},'bs':{}}
		if additional_parameter is not None:
			parameters.update(additional_parameter) 
		if test_config is not None and tcv is not None:
			parameter = tcv.parameter_values.all()
			for p in parameter:
				parameters[p.parameter.type][p.parameter.name]=p.value
            
		if result is not None:
			parameters['env']['TestResultId'] = result.id
		parameters['env']['ClusterId'] = nodes[0].cluster.id
		if len(nodes) is 1:
			parameters['env']['NodeId'] = nodes[0].id
			
		parameters['env']['CPERF_DIR'] = getPath(None)
		parameters['env']['CPERF_HOST'] = settings.CP_HOST
		parameters['env']['CPERF_USER'] = settings.OS_USER
		parameters['env']['CPERF_SSHKEY'] = settings.SSH_KEYFILE
		parameters['env']['TestDir'] = test.getPath('',cluster,False)
		parameters['env']['TestID'] = test.id
		parameters['env']['TestConfigID'] = test_config.id
		parameters['env']['TestConfigVersionHash'] = tcv.hash
		parameters['env']['TestConfigVersionId'] = tcv.id
		parameters['env']['TestResultsDir'] = test.getPath('results',cluster,False)
		parameters['env']['TestOutputDir'] = test.getPath('output',cluster,False)
		parameters['env']['TestScriptsDir'] = test.getPath('scripts',cluster,False)
		parameters['env']['TestConfigHash'] = tcv.hash
		if test_config is not None and test_config.needs_configfile:
			parameters['env']['Configfile'] = test.getPath('configs',cluster,False)+test_config.getConfigfileName(test)
		if result.type == "run":
			parameters['bs']['job_name'] = "RUN_"+test.name+"_" + test_config.name 
		elif result.type == "build":
			parameters['bs']['NumTasks'] = "1"
			parameters['bs']['job_name'] = "BUILD_"+test.name+"_" + test_config.name 
			
		parameters['bs']['output'] = test.getPath('output',cluster,False)
		parameters['bs']['error'] = test.getPath('error',cluster,False)
		if result.type == "run" and 'TimeLimitRun' in parameters['bs']:
			parameters['bs']['TimeLimit'] = parameters['bs']['TimeLimitRun']
		elif result.type == "build" and 'TimeLimitBuild' in parameters['bs']:
			parameters['bs']['TimeLimit'] = parameters['bs']['TimeLimitBuild']

		if self.name=="PBS":
			parameters['bs']['nodes'] = ""
			for n in nodes:
				if len(parameters['bs']['nodes'])>0:
					parameters['bs']['nodes'] += "+"
				parameters['bs']['nodes'] += n.name 
				if 'ProcessorsPerNode' in parameters['bs']:
					parameters['bs']['nodes'] += ":ppn=" + parameters['bs']['ProcessorsPerNode']
			
		
		elif self.name=="SLURM":
			if nodes[0].partition_id != 0:
				try:
					p = Partition.objects.get(id=nodes[0].partition.id)
					parameters['bs']['partition'] = p.name
				except Partition.DoesNotExist:
					logging.error("partition does not exist!")
			else:
				logging.error("Batchsystem: no SLURM partition supplied for nodes")
			parameters['bs']['node_count'] = len(nodes)
			parameters['bs']['nodes'] = ""
			for n in nodes:
				if len(parameters['bs']['nodes'])>0:
					parameters['bs']['nodes'] += ","
				parameters['bs']['nodes'] += n.name 
		return parameters
		
		
			
	def submit(self, cluster, script_path, nodes, test, test_config, tcv, result, additional_parameter=None):
		parameters = self.getParameters(cluster, nodes, test, test_config, tcv, result, additional_parameter)
		
		if self.name=="PBS":
			try:
				logging.info("executing command: " +'qsub' + self.getBatchsystemVariables(parameters) +" "+ self.getEnvironmentVariables(parameters) + " " + script_path)
				stdin, stdout, stderr = cluster.connection.exec_command('qsub' + self.getBatchsystemVariables(parameters) +" "+ self.getEnvironmentVariables(parameters) + " " + script_path)
				jobid = 0
				for line in stdout:
					jobid=line.strip('\n')
				logging.info("Batchsystem: Submited job with id %s", str(jobid))
				return jobid
			except paramiko.SSHException as e:
				logging.error("Batchsystem: submitting job to PBS failed: %s", e)
				return None
					
		elif self.name=="SLURM":
			try:
				logging.info("executing command: %s%s %s %s", 'sbatch', self.getBatchsystemVariables(parameters), self.getEnvironmentVariables(parameters), script_path)
				stdin, stdout, stderr = cluster.connection.exec_command('sbatch' + self.getBatchsystemVariables(parameters) +" "+ self.getEnvironmentVariables(parameters) + " " + script_path)
				jobid = 0
				outp = ""
				for line in stdout:
					outp += line.strip('\n')
					m = re.search('Submitted batch job (\d+)', line.strip('\n'))
					if m != None:
						jobid=m.group(1)
				if jobid != 0:
					logging.info("Batchsystem: Submited job with id " + str(jobid))
				else:
					logging.error("Batchsystem: submitting job to SLURM failed: %s", outp)
					
				return jobid
			except paramiko.SSHException as e:
				logging.error("Batchsystem: submitting job to SLURM failed: %s", e)
				return None
		
		else:
			logging.error("Batchsystem: Can not submit to unknown batchsystem")
			return None
		
	class Meta:
		managed = False
		db_table = 'batchsystem'


class Cluster(models.Model):
	id = models.BigAutoField(primary_key=True)
	name = models.CharField(max_length=100)
	description = models.TextField(blank=True, null=True)
	batchsystem = models.ForeignKey(Batchsystem, models.PROTECT, blank=True)
	login_node = models.CharField(max_length=120, blank=True, null=True)
	local_path = models.CharField(max_length=170, blank=True, null=True)
	remote_path = models.CharField(max_length=170, blank=True, null=True)
	
	connection=None
	
	def __str__(self):
		return self.name
        
	def connect(self):
		try:
			logging.info("cp_ssh: Trying to connect to host %s via ssh", self.login_node)
			self.connection = paramiko.SSHClient()
			self.connection.set_missing_host_key_policy(paramiko.AutoAddPolicy())
			self.connection.connect(self.login_node, username=settings.OS_USER, key_filename=settings.SSH_KEYFILE)
		except paramiko.BadAuthenticationType as e: 
			logging.error("cp_ssh: Could not connect to host %s: %s",self.login_node,e)
			self.connection=None
		except paramiko.BadHostKeyException as e: 
			logging.error("cp_ssh: Could not connect to host %s: %s",self.login_node,e)
			self.connection=None
		except paramiko.AuthenticationException as e: 
			logging.error("cp_ssh: Could not connect to host %s: %s",self.login_node,e)
			self.connection=None
		except:
			logging.error("cp_ssh: Could not connect to host %s",self.login_node)
			self.connection=None
		else:
			logging.info("cp_ssh: Connection to host %s established.", self.login_node)
			
	def disconnect(self):
		try:
			self.connection.close()
		except:
			
			logging.error("cp_ssh: Could not disconnect from host ")
		
		else:
			logging.info("cp_ssh: Disconnect from host ")
			self.connection=None
			
	@staticmethod
	def post_save(sender, instance=None, created=None, update_fields=None, **kwargs):
		if created is True:
			instance.batchsystem.initNodes(instance)
#			task_cluster_init.delay(instance.id, None)
#			if 'config' in update_fields or 'configfile_extension' in update_fields:	
#				cs=Cluster.objects.all()
#				for c in cs:
#					f = instance.generateConfigfile(instance.test, c)
#				tcvs = TestConfigHistory.objects.filter(test_config=instance)
#				for t in tcvs:
#					t.was_built=False
#					t.save()
					

	class Meta:
		managed = False
		db_table = 'cluster'


class NodeType(models.Model):
	id = models.BigAutoField(primary_key=True)
	name = models.CharField(max_length=100, blank=True, null=True)
	name.short_description = "Node Type name"
	partition = models.ForeignKey('Partition', models.DO_NOTHING, blank=True, null=True)
	hw_info = models.TextField(blank=True, null=True)
	created = models.DateField(auto_now_add=True)
	cpu = models.CharField(max_length=150, blank=True, null=True)
	cpu_cores = models.IntegerField(blank=True, null=True)
	cpu_sockets = models.IntegerField(blank=True, null=True)
	accelerator = models.CharField(max_length=250, blank=True, null=True)
	accelerator_type = models.CharField(max_length=50, blank=True, null=True)
	memory = models.IntegerField(blank=True, null=True)
	memory_modules = models.IntegerField(blank=True, null=True)
	hdd_size = models.IntegerField(blank=True, null=True)
	hdd = models.CharField(max_length=200, blank=True, null=True)
	cluster = models.ForeignKey(Cluster, models.CASCADE)
	parent_id = models.IntegerField(blank=True, null=True)

	def __str__(self):
		return self.name
		
        
	def getDiff(self, hw1, hw2):
		return difflib.unified_diff(hw1.splitlines(1), hw2.splitlines(1), lineterm='\n', n=0)
		
		
	def getPercDiff(self, hw1, hw2):
		m = difflib.SequenceMatcher(None, hw1.splitlines(1), hw2.splitlines(1))
		return m.ratio()
				
	def compareHWInfo(self, hw1, hw2):
		diff = self.getDiff(hw1,hw2)
		for l in diff:		
			if re.search("Table at", l):
				 continue	
			if re.search("structures occupying", l):
				 continue	
			if re.search("--- ", l):
				 continue	
			if re.search("\+\+\+", l):
				 continue			
			if re.search("@@ ", l):
				 continue				
			if re.search("Serial Number:", l):
				 continue			
			if re.search("UUID:", l):
				 continue
			return False
		
		return True
	
#	def merge(self, nt):
#			TODO
#		try:
#			dbcursor.callproc('merge_node_type',(self.id, nt.id,))
#			cluster_id = dbcursor.fetchone()
#		except psycopg2.Error as e:	
#			logging.error("NodeType: Can not merge Node Types into database: %s", e)
#			
	class Meta:
		managed = False
		db_table = 'node_types'


class Node(models.Model):
	id = models.BigAutoField(primary_key=True)
	name = models.CharField(max_length=150)
	name.short_description = "Node name"
	cluster = models.ForeignKey(Cluster, models.CASCADE)
	hw_info = models.TextField(blank=True, null=True)
	hw_info_update = models.DateField(auto_now_add=True)
	partition = models.ForeignKey('Partition', models.CASCADE, blank=True, null=True)
	node_type = models.ForeignKey(NodeType, models.CASCADE, blank=True, null=True)

	def __str__(self):
		return self.name
    
	def writeHWinfo(self):
		logging.info("Node: writing new HW info for node '%s'", self.id)
		
		try:
			test = Test.objects.get(id=1)
		except Test.DoesNotExist:
			logging.error("test does not exist!")
			return
	
		filename = test.getPath('results', cluster) + "/" + str(self.cluster.id) + "_" + str(self.id) + ".log"
		dmi = ""
		try:
			file = open(filename, "r")
			for line in file:
				if not re.search("UUID:", line) and not re.search("Serial Number:", line) and not re.search("structures occupying", line) and not re.search("Table at", line):
					dmi += line
				
			file.close()
		except re.error as d:
			logging.error("Node: parsing HWinfo regex error(%s): %s",d.msg, d.pattern)		
		except IOError as e:
			logging.error("Node: reading HWinfo I/O error(%s): %s", e.errno, e.strerror)
		except:
			logging.error("Node: could not read from file " + filename)
			return None
		logging.info("Node: writing new HW info for node into db '%s'", self.id)
		self.hw_info = dmi
		self.save()
		logging.info("Node: compare hwinfo with current node types %s", self.id)
		self.compareHWinfo()
		
	def compareHWinfo(self):
		try:
			nt = NodeType.objects.get(cluster=self.cluster, hw_info=self.hwinfo)
		except NodeType.DoesNotExist:
			logging.error("partition does not exist!")
			nt = None
	
		if nt is None:
			nt = NodeType(
				name = self.name,
				hw_info = self.hw_info,
				cluster= self.cluster
			)
			nt.save()
			
			
	
		self.node_type = nt
		self.save()		
    
	class Meta:
		managed = False
		db_table = 'nodes'


class Partition(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=100)
    cluster = models.ForeignKey(Cluster, models.CASCADE)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name
    class Meta:
        managed = False
        db_table = 'partitions'


class Result(models.Model):
	id = models.BigAutoField(primary_key=True)
	start = models.DateTimeField(blank=True, null=True)
	end = models.DateTimeField(blank=True, null=True)
	#test_config_id = models.IntegerField(blank=True, null=True)
	test_config = models.ForeignKey('TestConfig', blank=True, null=True, on_delete=models.CASCADE)
	job_id = models.CharField(max_length=150, blank=True, null=True)
	result_detail = JSONField()
	result = models.FloatField(blank=True, null=True)
	norm_result = models.FloatField(blank=True, null=True)
	#test_config_version_hash = models.CharField(max_length=150, blank=True, null=True)
	test_config_version = models.ForeignKey('TestConfigHistory', on_delete=models.CASCADE, blank=True, null=True)
	submit = models.DateTimeField(blank=True, null=True)
	type = models.CharField(max_length=20, blank=True, null=True, choices=(("run", "Run Test"),("build", "Build Test")))
	nodes = models.ManyToManyField(
		Node,
		through='ResultNode',
		through_fields=('result', 'node'),
	)
	node_types = models.ManyToManyField(
		NodeType,
		through='ResultNode',
		through_fields=('result', 'node_type'),
	)
	
	
	@staticmethod
	def post_save(sender, instance=None, created=None, update_fields=None, **kwargs):
		if update_fields is not None and  'result' in update_fields:
			try:
				nr = Result.objects.order_by('start').exclude(result=None, end=None).filter(test_config=instance.test_config, type=instance.type)[0]
			except Result.DoesNotExist:
				instance.norm_result = 1.0
			else:
				instance.norm_result = round(nr.result/instance.result, 2)
			instance.save()
			
#	@property
#	def norm_result(self):
#		if self.id is not None and self.result is not None:
#			try:
#				nr = Result.objects.order_by('start').exclude(result=None, end=None).filter(test_config=self.test_config, type=self.type)[0]
#			except Result.DoesNotExist:
#				return 1.0
#			if self.result==0.0:
#				return 0.0
#			else:
#				return round(nr.result/self.result, 2)
#		else:
#			return 0.0	
			
			
	def __str__(self):
		return "ID: "+ str(self.id)
		
		
	"""Compare results of multiple Test config versions for node_type
	Provides: Geometric mean and gaussian for each result set"""
	def compareTestConfigVersion(self, cluster, test_config, test_config_versions, node_type, date, date_maxoffset):
		results = []
		for tcv in test_config_versions:
			results.append(Result.objects.filter(cluster=cluster, test_config=test_config, test_config_version=tcv, node_types__in=[node_type], submit__range=[date, date+date_maxoffset]))
			#TODO get geometric mean of results
			#TODO create gaussian
		
	def overviewNodeType(self,  cluster, test_config, test_config_version, node_type, date, date_maxoffset):
		results = Result.objects.filter(cluster=cluster, test_config=test_config, test_config_version=test_config_version, node_types__in=[node_type], submit__range=[date, date+date_maxoffset])
		#TODO create gaussian

	
	
	class Meta:
		managed = False
		db_table = 'results'

class ResultNode(models.Model):
    id = models.BigAutoField(primary_key=True)
    node = models.ForeignKey(Node, models.DO_NOTHING)
    result = models.ForeignKey(Result, models.DO_NOTHING)
    node_type = models.ForeignKey(NodeType, models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'results_nodes'

class Parameter(models.Model):
    id = models.BigAutoField(primary_key=True)
    #config = models.ForeignKey('TestConfig', models.DO_NOTHING)
    name = models.CharField(max_length=150)
    type = models.CharField(choices=(("env", "Environment Variable"),("bs", "Batchsystem Variable"),("config", "Configfile Variable")), max_length=150)
    class Meta:
        managed = False
        db_table = 'test_config_parameter'
	
	
    def __str__(self):
	    return self.type + ': ' + self.name

class ParameterValue(models.Model):
    id = models.BigAutoField(primary_key=True)
    parameter = models.ForeignKey('Parameter', models.DO_NOTHING)
    value = models.CharField(max_length=150)
    class Meta:
        managed = False
        db_table = 'test_config_parameter_values'
    def __str__(self):
	    return 'ID: '+ str(self.id) + ': ' + self.parameter.name + '=' + str(self.value)

        
class TestConfig(models.Model):
	id = models.BigAutoField(primary_key=True)
	name = models.CharField(max_length=150)
	test = models.ForeignKey('Test', models.DO_NOTHING)
	config = models.TextField(blank=True, null=True)
	configfile_extension = models.CharField(max_length=10, blank=True, null=True)
	needs_configfile = models.NullBooleanField()
	edited = models.DateTimeField(auto_now_add=True)
	node_types = models.ManyToManyField(
		NodeType,
		through='TestconfigNodetype',
		through_fields=('test_config', 'node_type'),
	)
	
	def __str__(self):
		return self.name
	class Meta:
		managed = False
		db_table = 'test_config'
		
	@staticmethod
	def post_save(sender, instance=None, created=None, update_fields=None, **kwargs):
#		if update_fields is not None:
#			if 'name' in update_fields or 'config' in update_fields or 'configfile_extension' in update_fields:	
		cs=Cluster.objects.all()
		for c in cs:
			logging.debug("create new configfile %s for cluster %s", instance.name, c.name)
			f = instance.generateConfigfile(instance.test, c)
		tcvs = TestConfigHistory.objects.filter(test_config=instance)
		for t in tcvs:
			t.was_built=False
			t.save()
#		else:
#			logging.debug("post_save test config %s: no update_fields", instance.name)
			
	
	def getConfigfileName(self, test):
		filename =  '/'+ test.name + "_" + self.name + self.configfile_extension
		return filename
		
	def generateConfigfile(self, test, cluster):	
	#ensure that directories exist
		test.createTestDirectory(cluster)
		filename =  '/'+ test.name + "_" + self.name+ self.configfile_extension
		
		local_filename = test.getPath('configs') + filename
		remote_filename = test.getPath('configs', cluster, True) + filename
		remote_local_filename = test.getPath('configs', cluster, False) + filename
		
		try:
			file = open(local_filename, "w+")
			#with io.FileIO(test.getPath('configs') + filename, "w") as file:
			file.write(self.config)
			file.close()
			logging.info("TestConfig: created configfile for config '%s' in file '%s'",self.id,test.getPath('configs') + filename)
		except IOError as e:
			logging.error("TestConfig: could not create configfile " + filename + " \nin " + test.getPath('configs')+"\n"+e)
			return None
		#copy run script into cluster fs
		try:
			copyfile(local_filename, remote_filename)
		
		# eg. source or destination doesn't exist
		except IOError as e:
			logging.error('TestConfig: could not copy configfile to cluster: %s' % e.strerror)
			return None
		return filename
    
	def getParameterHash(self, parameter):
		pids=[]
		for p in parameter:
			pids.append(p.id)
		ps = sorted(pids)
		pss=",".join(str(x) for x in ps)
		logging.info("TestConfig: hash this '%s' ", str(','.join(str(x) for x in ps)))
		return hashlib.md5(str(pss).encode('utf-8')+str(self.id).encode('utf-8')).hexdigest()
		


class TestConfigHistory(models.Model):
	id = models.BigAutoField(primary_key=True)
	test_config = models.ForeignKey(TestConfig, models.DO_NOTHING, blank=True, null=True)
	hash = models.CharField(unique=True, max_length=150)
	edited = models.DateTimeField(auto_now_add=True)
	was_built = models.NullBooleanField()
	parameter_values = models.ManyToManyField(
		ParameterValue,
		through='HistoryParameterValue',
		through_fields=('history', 'parameter_value'),
	)
	def __str__(self):
		return self.hash
	class Meta:
		managed = False
		db_table = 'test_config_history'

class HistoryParameterValue(models.Model):
    id = models.BigAutoField(primary_key=True)
    parameter_value = models.ForeignKey(ParameterValue, on_delete=models.PROTECT)
    history = models.ForeignKey(TestConfigHistory, on_delete=models.CASCADE)

    class Meta:
        managed = False
        db_table = 'history_values'


class TestconfigNodetype(models.Model):
    id = models.BigAutoField(primary_key=True)
    test_config = models.ForeignKey(TestConfig, models.DO_NOTHING, blank=True, null=True)
    node_type = models.ForeignKey(NodeType, models.DO_NOTHING, blank=True, null=True)

	
    def __str__(self):
        return self.test_config.name + " - " + self.node_type.name

    class Meta:
        managed = False
        db_table = 'testconfig_nodetypes'


class Test(models.Model):
	id = models.BigAutoField(primary_key=True)
	name = models.CharField(max_length=200)
	run_script = models.TextField(blank=True, null=True)
	parameter = JSONField()
	multi_node = models.BooleanField()
	analysis_script = models.TextField(blank=True, null=True)
	build_script = models.TextField(blank=True, null=True)
	needs_building = models.NullBooleanField()
	
	@staticmethod
	def post_save(sender, instance=None, created=None, update_fields=None, **kwargs):
		if update_fields is not None:
			if 'run_script' in update_fields or ('build_script' in update_fields and instance.needs_building):
				cs=Cluster.objects.all()
				for c in cs:
					instance.generateRunScript(c)
					instance.generateBuildScript(c)
					
				tcvs = TestConfigHistory.objects.filter(test_config__test=instance)
				for t in tcvs:
					t.was_built=False
					t.save()
			


	def getPath(self, area=None, cluster=None, local=True):
		if self.id is not 0:
			if cluster == None:
				#TODO
				if area == 'results':
					return getPath('tests') + '/' + self.name +'/results' 
				elif area == 'configs':
					return getPath('tests') + '/' + self.name +'/configs' 
				elif area == 'scripts':
					return getPath('tests') + '/' + self.name +'/scripts' 
				elif area == 'output':
					return getPath('tests') + '/' + self.name +'/output' 
				elif area == 'error':
					return getPath('tests') + '/' + self.name +'/error' 
				elif area == 'sources':
					return getPath('tests') + '/' + self.name +'/sources' 
				else:			
					return getPath('tests') + '/' + self.name 
			else:
				if local is True:
					if area == 'results':
						return getPath('tests', cluster.local_path) + '/' + self.name +'/results' 
					elif area == 'configs':
						return getPath('tests', cluster.local_path) + '/' + self.name +'/configs' 
					elif area == 'scripts':
						return getPath('tests', cluster.local_path) + '/' + self.name +'/scripts' 
					elif area == 'output':
						return getPath('tests', cluster.local_path) + '/' + self.name +'/output' 
					elif area == 'error':
						return getPath('tests', cluster.local_path) + '/' + self.name +'/error'  
					elif area == 'sources':
						return getPath('tests', cluster.local_path) + '/' + self.name +'/sources' 
					else:			
						return getPath('tests', cluster.local_path) + '/' + self.name 
				else:
					if area == 'results':
						return getPath('tests', cluster.remote_path) + '/' + self.name +'/results' 
					elif area == 'configs':
						return getPath('tests', cluster.remote_path) + '/' + self.name +'/configs' 
					elif area == 'scripts':
						return getPath('tests', cluster.remote_path) + '/' + self.name +'/scripts' 
					elif area == 'output':
						return getPath('tests', cluster.remote_path) + '/' + self.name +'/output' 
					elif area == 'error':
						return getPath('tests', cluster.remote_path) + '/' + self.name +'/error'
					elif area == 'sources':
						return getPath('tests', cluster.remote_path) + '/' + self.name +'/sources' 
					else:			
						return getPath('tests', cluster.remote_path) + '/' + self.name 
		else:
			return None

	def createTestDirectory(self, cluster=None):
		directories = [None, 'results','configs','output','scripts','sources']
		#create local directories
		for d in directories:
			if self.getPath(d) is not None:
				if not os.path.exists(self.getPath(d)):
					try:
						os.makedirs(self.getPath(d))					
					except OSError as e:
						logging.error("Test: Can not create directories for test %s",e)
						raise
		if cluster != None and not os.path.exists(self.getPath('', cluster)):
			try:
				copytree(self.getPath(''), self.getPath('', cluster))
			except IOError as e:
				logging.error("Test: could not copy sources dir '%s' to cluster '%s': %s",self.getPath(''), self.getPath('', cluster),  e)
						
	def generateRunScript(self, cluster):
		#ensure that directories exist
		self.createTestDirectory(cluster)
		
		local_filename = self.getPath('scripts') + '/run_' + cluster.name + '_' + cluster.batchsystem.name +'.sh'
		remote_filename = self.getPath('scripts', cluster, True) + '/run_' + cluster.name + '_' + cluster.batchsystem.name +'.sh'
		remote_local_filename = self.getPath('scripts', cluster, False) + '/run_' + cluster.name + '_' + cluster.batchsystem.name +'.sh'
		try:
			file = open(local_filename, "w+")
			if cluster.batchsystem.header is not None and len(cluster.batchsystem.header) > 0:
				file.write(cluster.batchsystem.header)

			if self.run_script is not None and len(self.run_script) > 0:
				file.write("\n\n#-----TEST RUN SCRIPT------\n")	
				file.write("\n\n")						
#					file.write("ssh ${CPERF_USER}@${CPERF_HOST} -i ${CPERF_SSHKEY} ${CPERF_DIR}/bin/cp_result.sh --hasStarted=$TestResultId\n")
				file.write("curl -u system:manual_3034 --header \"Content-Type: application/json\" --request POST http://${CPERF_HOST}:8000/api/results/$TestResultId/hasStarted/\n")
				file.write('\tNode_data=`printf \'{"node_name":"%s"}\' "$SLURM_NODELIST"`;\n')
				file.write("curl -u system:manual_3034 --header \"Content-Type: application/json\" --request POST --data $Node_data http://${CPERF_HOST}:8000/api/results/$TestResultId/setNode/\n")
				#TODO: Remove DOS linebreaks
				newrun_script = self.run_script.replace("\r\n", "\n")
				file.write(newrun_script)
				file.write("\n\n")
							
			if self.analysis_script is not None and len(self.analysis_script) > 0:
				file.write("\n\n#-----TEST ANALYSIS SCRIPT------\n")	
				newanalysis_script = self.analysis_script.replace("\r\n", "\n")
				file.write(newanalysis_script)
				#file.write("\nssh ${CPERF_USER}@${CPERF_HOST} -i ${CPERF_SSHKEY} $CPERF_DIR/bin/cp_result.sh --writeResult=$TestResultId --result=$Result --details=$ResultDetails\n")
				file.write('\n\nData=`printf \'{"result":"%s","result_detail":%s}\' "$Result" "$ResultDetails"`;\n')
				file.write("echo $Data\n")
				file.write("curl -u system:manual_3034 --header \"Content-Type: application/json\" --request POST --data $Data http://${CPERF_HOST}:8000/api/results/$TestResultId/writeResult/\n")
			if cluster.batchsystem.footer is not None and len(cluster.batchsystem.footer) > 0:
				file.write("\n\n#-----BATCHSYSTEM FOOTER-----\n")
				file.write(cluster.batchsystem.footer)
			file.close()
			
		except IOError as e:
			logging.error("Test: could not create run script in " + self.getPath('scripts') + filename+ "\n" + e)
			return None
		#copy run script into cluster fs
		try:
			copyfile(local_filename, remote_filename)
			# eg. src and dest are the same file
#				except shutil.Error as e:
#					logging.error('Test: could not copy build script to cluster: %s' % e)
#					return None
		# eg. source or destination doesn't exist
		except IOError as e:
			logging.error('Test: could not copy build script to cluster: %s' % e.strerror)
			return None
		return remote_local_filename

							
	def generateBuildScript(self, cluster):
		logging.debug("Test - generateBuildScript: cluster: %s", cluster.name)
		#ensure that directories exist
		self.createTestDirectory(cluster)
		
		local_filename = self.getPath('scripts') + '/build_' + cluster.name + '_' + cluster.batchsystem.name +'.sh'
		remote_filename = self.getPath('scripts', cluster, True) + '/build_' + cluster.name + '_' + cluster.batchsystem.name +'.sh'
		remote_local_filename = self.getPath('scripts', cluster, False) + '/build_' + cluster.name + '_' + cluster.batchsystem.name +'.sh'
		
		logging.debug("Test - generateBuildScript: local_path: %s", local_filename)
		logging.debug("Test - generateBuildScript: remote_path for cluster %s: %s", cluster.name, remote_filename)
		try:
			file = open(local_filename, "w+", newline="\n")
#			with io.FileIO(local_filename, "w") as file:
			if cluster.batchsystem.header is not None and len(cluster.batchsystem.header) > 0:
				file.write(cluster.batchsystem.header)
			file.write("\n\n")		
			#file.write("ssh ${CPERF_USER}@${CPERF_HOST} -i ${CPERF_SSHKEY} ${CPERF_DIR}/bin/cp_result.sh --hasStarted=$TestResultId\n")	
			
			file.write("curl -u system:manual_3034 --header \"Content-Type: application/json\" --request POST http://${CPERF_HOST}:8000/api/results/$TestResultId/hasStarted/\n")
			file.write('\tNode_data=`printf \'{"node_name":"%s"}\' "$SLURM_NODELIST"`;\n')
			file.write("curl -u system:manual_3034 --header \"Content-Type: application/json\" --request POST --data $Node_data http://${CPERF_HOST}:8000/api/results/$TestResultId/setNode/\n")
			if self.build_script is not None and len(self.build_script) > 0:
				file.write("\n\n#-----TEST BUILD SCRIPT------\n")	
				#TODO: Remove DOS linebreaks
				newdata = self.build_script.replace("\r\n", "\n")
				file.write(newdata)				
			file.write("\n\ncd $CPERF_DIR\n")							
			file.write('if [ "$Built" = true ]; then\n')		
			
#			file.write("\tssh ${CPERF_USER}@${CPERF_HOST} -i ${CPERF_SSHKEY} << EOF ${CPERF_DIR}/bin/cp_result.sh --built=$TestConfigHash\n")
			file.write("\tcurl -u system:manual_3034 --header \"Content-Type: application/json\" --request POST --data '{\"wasbuilt\":\"true\"}' http://${CPERF_HOST}:8000/api/test_config_histories/$TestConfigVersionId/wasBuilt/\n\n")
			#file.write('\tssh ${CPERF_USER}@${CPERF_HOST} -i ${CPERF_SSHKEY} $CPERF_DIR/bin/cp_result.sh --writeResult=$TestResultId --result=1.0 --details={"build": "success"}\n')
			file.write("\tcurl -u system:manual_3034 --header \"Content-Type: application/json\" --request POST --data '{\"result\":\"1.0\",\"result_detail\":{\"build\":\"success\"}}' http://${CPERF_HOST}:8000/api/results/$TestResultId/writeResult/\n\n")
			
			#file.write("\t${CPERF_DIR}/bin/cp_test.sh --$TestType=$TestID --test_config=$TestConfigID --nodes=$RUN_NODES --hash=$TestConfigHash\nEOF\n")
			file.write('\tTest_data=`printf \'{"test_config":"%s","nodes":"%s","hash":["%s"]}\' "$TestConfigID" "$RUN_NODES" "$TestConfigHash"`;\n')
			file.write("\tcurl -u system:manual_3034 --header \"Content-Type: application/json\" --request POST --data $Test_data http://${CPERF_HOST}:8000/api/tests/$TestID/start/\n\n")
			file.write("else\n")
			#file.write('\tssh ${CPERF_USER}@${CPERF_HOST} -i ${CPERF_SSHKEY} $CPERF_DIR/bin/cp_result.sh --writeResult=$TestResultId --result=-1.0 --details={"build": "failed"}\n')
			file.write("\tcurl -u system:manual_3034 --header \"Content-Type: application/json\" --request POST --data '{\"result\":\"-1.0\",\"result_detail\":{\"build\":\"failed\"}}' http://${CPERF_HOST}:8000/api/results/$TestResultId/writeResult/\n")
			file.write("fi\n")
			if cluster.batchsystem.footer is not None and len(cluster.batchsystem.footer) > 0:
				file.write("\n\n#-----BATCHSYSTEM FOOTER-----\n")
				file.write(cluster.batchsystem.footer)
			file.close()
		except IOError as e:
			logging.error("Test: IOError could not create build script in '%s': %s", self.getPath('scripts'), e)
			return None
		except:
			logging.error("Test: could not create build script in '%s': %s", local_filename, sys.exc_info()[0])
			return None
			
		#copy run script into cluster fs
		try:
			copyfile(local_filename, remote_filename)
#			self.getPath('scripts', cluster))
		# eg. src and dest are the same file
#		except shutil.Error as e:
#			logging.error('Test: could not copy build script to cluster: %s' % e)
#			return None
		# eg. source or destination doesn't exist
		except IOError as e:
			logging.error('Test: could not copy build script to cluster: %s: %s -> %s', e.strerror, local_filename, remote_filename)
			return None
		return remote_local_filename

	def buildTest(self, cluster, test_config, nodes, hash, parameter, test_type):
		if test_type == 'TEST':
			test_type_start="startTest"
			node=nodes[0]
			run_nodes=[]
			for n in nodes:
				run_nodes.append(n.id)
		elif test_type == 'TEST_ARRAY':
			test_type_start="startTestArray"
			node = nodes[0][0]
			run_nodes=[]
			for t in nodes:
				temp = []
				for n in t:
					temp.append(n.id)
				run_nodes.append(temp)
		if hash==None:
			hash=test_config.getParameterHash(parameter)	
			try:
				tcv = TestConfigHistory.objects.get(hash=hash)
			except TestConfigHistory.DoesNotExist:
				tcv = TestConfigHistory(hash=hash, test_config=test_config, was_built=False)
				tcv.save()
				for p in parameter:
					tcv_p = HistoryParameterValue(history=tcv, parameter_value=p)
					tcv_p.save()
		else:
			try:
				tcv = TestConfigHistory.objects.get(hash=hash)
			except TestConfigHistory.DoesNotExist:
				logging.error("TCV not found: %s", hash)
				return
				

#		cluster = node.cluster
#		cluster.connect()
		if cluster.connection is None:
			logging.error("No SSH connection to cluster login node")
			return
			
		

		if test_config is not None:
			try:
				test_nt = test_config.node_types.get(id=node.node_type.id)
			except NodeType.DoesNotExist:
				logging.error("Test: Node of wrong type '%s' assinged to test '%s' with config '%s'",node.node_type.id, self.name, test_config.name)
				return
		
	
		buildscript_file = self.getPath('scripts', cluster, False) + '/build_' + cluster.name + '_' + cluster.batchsystem.name +'.sh'
		if not os.path.exists(self.getPath('scripts', cluster, True) + '/build_' + cluster.name + '_' + cluster.batchsystem.name +'.sh'):
			f=self.generateBuildScript(cluster)
		if buildscript_file==None:
			return
			
			
		res = Result(type="build", test_config = test_config, test_config_version=tcv)
		res.save()
#		res_node=ResultNode(node=node, result=res, node_type=node.node_type)
#		res_node.save()
		
		additional_parameter={'env':{}, 'bs':{}}
		additional_parameter['env']['RUN_NODES']=str("[{}]".format(",".join(map(repr, run_nodes))))
		additional_parameter['bs']['num_nodes']=1
		logging.debug("RUN_NODES: %s", additional_parameter['env']['RUN_NODES'])
		additional_parameter['env']['TestType']=test_type_start
		additional_parameter['env']['TestAction']='build'
		
		res.job_id = cluster.batchsystem.submit(cluster, buildscript_file, nodes, self, test_config, tcv, res, additional_parameter)
		
#		cluster.disconnect()
		if res.job_id is not None:
			res.submit=timezone.now()
			res.save()
			
		else:
			res.result = -1
			res.result_detail['error']="Could not start build due to batchsystem"
			res.save()
			logging.error("Test: Could not start build due to batchsystem")

	def startTest(self, cluster, test_config, nodes, hash, parameter=None):
		if test_config==None:
			test_config = TestConfig.objects.filter(test=self).order_by('-id')[0]
		if test_config.id==0:
			logging.error("Test: could not get default test config for test '%s'", self.id)
			return 
		if hash==None:
			hash=test_config.getParameterHash(parameter)	
			try:
				tcv = TestConfigHistory.objects.get(hash=hash)
			except TestConfigHistory.DoesNotExist:
				tcv = TestConfigHistory(hash=hash, test_config=test_config, was_built=False)
				tcv.save()
				for p in parameter:
					tcv_p = HistoryParameterValue(history=tcv, parameter_value=p)
					tcv_p.save()
		else:
			try:
				tcv = TestConfigHistory.objects.get(hash=hash)
			except TestConfigHistory.DoesNotExist:
				logging.error("TCV not found: %s", hash)
				return
#			parameter = tcv.parameter_values.all()
			
		
#		cluster = nodes[0].cluster
		
		
		if self.needs_building is True and tcv.was_built is False:
			confpath = self.getPath('configs',cluster,True)+test_config.getConfigfileName(self)
			if test_config.needs_configfile == True and not os.path.exists(confpath):
				if test_config.generateConfigfile(self, cluster)==None:
					logging.error("Test: could not create configfile")	
			logging.info("Building Test %s for Config %s before running", self.id, test_config.id)
			
			self.buildTest(cluster, test_config, nodes, hash, parameter, 'TEST')
			return
		
		
		if cluster.connection is None:
			logging.error("No SSH connection to cluster login node")
			return
		
		
		#nodes must be of the same node type as defined in test config -> check
		if test_config is not None:
			for n in nodes: 
				if test_config.node_types.count()>0 and n.node_type not in test_config.node_types.all():
					logging.error("Test: Node of wrong type '%s' assinged to test '%s' with config '%s'",n.node_type.id, self.name, test_config.name)
					return		
		
		run_path = self.getPath('scripts', cluster, False) + '/run_' + cluster.name + '_' + cluster.batchsystem.name +'.sh'
		if not os.path.exists(self.getPath('scripts', cluster, True) + '/run_' + cluster.name + '_' + cluster.batchsystem.name +'.sh'):
			self.generateRunScript(cluster)
		
		res = Result(type="run", test_config = test_config, test_config_version=tcv)
		res.save()
		
#		for n in nodes:	
#			res_node=ResultNode(node=n, result=res, node_type=n.node_type)
#			res_node.save()
			
		res.job_id = cluster.batchsystem.submit(cluster,run_path, nodes, self, test_config, tcv, res)
		
		
		if res.job_id is not None:
			res.submit=timezone.now()
			res.save()
			
		else:
			res.result = -1
			res.result_detail['error']="Could not start test due to batchsystem"
			res.save()
			logging.error("Test: Could not start test due to batchsystem")
		
#TODO: parameter
	def startTestArray(self, test_config, nodes, parameter):
		
		if test_config==None:
			test_config = TestConfig.objects.filter(test=self).order_by('-id')[0]
		if test_config.id==0:
			logging.error("Test: could not get default test config for test '%s'", self.id)
			return 
			
			
		param_hash=test_config.getParameterHash(parameter)	
		try:
			tcv = TestConfigHistory.objects.get(hash=param_hash)
		except TestConfigHistory.DoesNotExist:
			tcv = TestConfigHistory(hash=param_hash, test_config=test_config, was_built=False)
			tcv.save()
            
		if self.needs_building is True and tcv.was_built is False:
			#TODO build and 
			logging.info("Building Test %s for Config %s before running", self.id, test_config.id)
			
			self.buildTest(test_config, nodes, tcv, 'TEST_ARRAY')
		else:
			#nodes = [[n1,n2],[n3,n4]]	
			for ns in nodes:
				self.startTest(test_config, ns, parameter)
		

	def __str__(self):
		return self.name
	class Meta:
		managed = False
		db_table = 'tests'
        
		
post_save.connect(Test.post_save, sender=Test)
post_save.connect(TestConfig.post_save, sender=TestConfig)
post_save.connect(Cluster.post_save, sender=Cluster)
post_save.connect(Result.post_save, sender=Result)


