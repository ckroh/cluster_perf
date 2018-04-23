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


from shutil import copyfile
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

logging.basicConfig(filename=os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir))+'/cluster_perf.log',level=logging.DEBUG, format='%(asctime)s - %(levelname)s: %(message)s')

class Batchsystem(models.Model):
	name = models.CharField(max_length=100)
	header = models.TextField(blank=True, null=True)
	id = models.BigAutoField(primary_key=True)
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
		cluster.disconnect()
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
		#				
				except Entry.DoesNotExist:
					p = Partition(name = prev_p, cluster=cluster)
					p.save()
					count_p += 1
					
				try:
					n = Node.objects.get(cluster=cluster, name=prev_n)
					logging.info("Batchsystem: Node %s already exists inside the database", prev_n)
				except Entry.DoesNotExist:
					n = Node(name = prev_n, cluster = cluster, parition = p)
					n.save()
					count_n += 1
				prev_n = m.group(1)
				prev_p = m.group(2)
			else:				
				prev_n = m.group(1)
				prev_p = m.group(2)
	
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
			except Entry.DoesNotExist:
				n = Node(name = child[0].text, cluster = cluster)
				n.save()
				count = count + 1
		
		logging.info("Batchsystem: %s new Nodes were added to the Cluster '%s'", cluster.name, str(count))
		
	def getEnvironmentVariables(self,parameters):
		ret = ""
		if self.name=="PBS":
			ret = "-v "
			res=""
			for v in parameters['env'].iterkeys():
				if len(res)>0:
					res = res +','
				res = res + v + "=" + str(parameters['env'][v])
			ret += res
			
		elif self.name=="SLURM":
			ret = "--export="
			for v in parameters['env'].iterkeys():
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
			res += " -w --nodelist=" + parameters['bs']['nodes']
			
			if 'NumNodes' in parameters['bs']:
				#TODO
				res += " --nodes=" + parameters['bs']['NumNodes'] 

			res += " -p " + parameters['bs']['partition']
			if 'TimeLimit' in parameters['bs']:
				res += " --time=" + parameters['bs']['TimeLimit']
			if 'account' in parameters['bs']:
				res += " -A "+ parameters['bs']['account']
			
		return res
	
	def getParameters(self, cluster, nodes, test, test_config, tcv, result):
		parameters={'env':{},'bs':{}}
		parameters.update(cluster.parameter)
		if test_config is not None:
			parameters.update(test_config.parameter) 
		if result is not None:
			parameters['env']['TestResultId'] = result.id
		parameters['env']['ClusterId'] = nodes[0].cluster.id
		if len(nodes) is 1:
			parameters['env']['NodeId'] = nodes[0].id
			
		parameters['env']['CPERF_DIR'] = cfg.getPath(None)
		parameters['env']['CPERF_HOST'] = cfg.cfg.get('general','cp_host')
		parameters['env']['CPERF_USER'] = cfg.cfg.get('general','os_user')
		parameters['env']['CPERF_SSHKEY'] = cfg.cfg.get('general','ssh_keyfile')
		parameters['env']['TestDir'] = test.getPath()
		parameters['env']['TestID'] = test.id
		parameters['env']['TestConfigID'] = test_config.id
		parameters['env']['TestConfigVersionHash'] = tcv.hash
		parameters['env']['TestResultsDir'] = test.getPath('results')
		parameters['env']['TestOutputDir'] = test.getPath('output')
		parameters['env']['TestScriptsDir'] = test.getPath('scripts')
		parameters['env']['TestConfigHash'] = tcv.hash
		if test_config is not None and test_config.needs_configfile:
			parameters['env']['Configfile'] = test_config.getConfigfileName(test,tcv)
		if result.type == "run":
			parameters['bs']['job_name'] = "RUN_"+test.name+"_" + test_config.name 
		elif result.type == "build":
			parameters['bs']['job_name'] = "BUILD_"+test.name+"_" + test_config.name 
			
		parameters['bs']['output'] = test.getPath('output')
		parameters['bs']['error'] = test.getPath('error')
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
				except Entry.DoesNotExist:
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
		
		
			
	def submit(self, cluster, script_path, nodes, test, test_config, tcv, result):
		parameters = self.getParameters(cluster, nodes, test, test_config, tcv, result)
		
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
				logging.info("executing command: " +'sbatch' + self.getBatchsystemVariables(parameters) +" "+ self.getEnvironmentVariables(parameters) + " " + script_path)
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
	batchsystem = models.ForeignKey(Batchsystem, models.DO_NOTHING, blank=True)
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

	class Meta:
		managed = False
		db_table = 'cluster'


class NodeType(models.Model):
	id = models.BigAutoField(primary_key=True)
	name = models.CharField(max_length=100, blank=True, null=True)
	name.short_description = "Node Type name"
	partition = models.ForeignKey('Partition', models.DO_NOTHING, blank=True, null=True)
	hw_info = models.TextField()
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
	cluster = models.ForeignKey(Cluster, models.DO_NOTHING)
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
	cluster = models.ForeignKey(Cluster, models.DO_NOTHING)
	hw_info = models.TextField(blank=True, null=True)
	hw_info_update = models.DateField(auto_now_add=True)
	partition = models.ForeignKey('Partition', models.DO_NOTHING, blank=True, null=True)
	node_type = models.ForeignKey(NodeType, models.DO_NOTHING, blank=True, null=True)

	def __str__(self):
		return self.name
    
	def writeHWinfo(self):
		logging.info("Node: writing new HW info for node '%s'", self.id)
		
		try:
			test = Test.objects.get(id=1)
		except Entry.DoesNotExist:
			logging.error("test does not exist!")
			return
	
		filename = test.getPath('results') + "/" + str(self.cluster.id) + "_" + str(self.id) + ".log"
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
		except Entry.DoesNotExist:
			logging.error("partition does not exist!")
			nt = None
	
		if fnt is None:
			nt = NodeType(
				name = self.name,
				hw_info = self.hw_info,
				cluster= self.cluster
			)
			nt.save()
			
			fnt = nt
	
		self.node_type = fnt
		self.save()		
    
	class Meta:
		managed = False
		db_table = 'nodes'


#class NormalizedResult(models.Model):
#    id = models.BigAutoField(primary_key=True)
#    test_config = models.ForeignKey('TestConfig', models.DO_NOTHING, blank=True, null=True)
#    node_type = models.ForeignKey(NodeType, models.DO_NOTHING, blank=True, null=True)
#    result = models.FloatField(blank=True, null=True)
#    created = models.DateField(blank=True, null=True)

#    class Meta:
#        managed = False
#        db_table = 'normalized_results'


class Partition(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=100)
    cluster = models.ForeignKey(Cluster, models.DO_NOTHING)
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
	test_config = models.ForeignKey('TestConfig', models.DO_NOTHING, blank=True, null=True)
	job_id = models.CharField(max_length=150, blank=True, null=True)
	result_detail = JSONField()
	result = models.FloatField(blank=True, null=True)
	#test_config_version_hash = models.CharField(max_length=150, blank=True, null=True)
	test_config_version_hash = models.ForeignKey('TestConfigHistory', models.DO_NOTHING, blank=True, null=True)
	submit = models.DateTimeField(blank=True, null=True)
	type = models.CharField(max_length=20, blank=True, null=True)
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
	def __str__(self):
		return "%s - %s: %s %s ", self.start, self.end, self.type, self.test_config.test.name

	def getNorm(self, target, node_type_id):
		if self.id == 0:
			logging.error("Result: normalize has no result defined")
			return None
		
		#TODO
		norm=Result()
		if target=="ALL":
			#pick first result with this config on any node
			db.dbcursor.execute("SELECT id from results WHERE test_config_id=%s AND result>0.0 ORDER BY 'end' ASC LIMIT 1;", (self.test_config_id,))
			res = db.dbcursor.fetchone()
			norm.readDB(db.dbcursor,res[0])
		elif target=="NODE_TYPE":
			#pick first result by any node of the same type
			db.dbcursor.execute("SELECT r.id from results r, results_nodes t2n WHERE t2n.node_type_id=%s AND t2n.result_id=r.id AND r.test_config_id=%s AND result>0.0 ORDER BY 'end' ASC LIMIT 1;", (node_type_id, self.test_config_id,))
			res = db.dbcursor.fetchone()
			norm.readDB(db.dbcursor,res[0])
		return norm
		
	def normalize(self, norm):
		return float(self.result)/float(norm.result)
	
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



class TestConfig(models.Model):
	id = models.BigAutoField(primary_key=True)
	name = models.CharField(max_length=150)
	test = models.ForeignKey('Test', models.DO_NOTHING)
	config = models.TextField(blank=True, null=True)
	parameter = JSONField()
	configfile_ending = models.CharField(max_length=10, blank=True, null=True)
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


class TestConfigHistory(models.Model):
    id = models.BigAutoField(primary_key=True)
    test_config = models.ForeignKey(TestConfig, models.DO_NOTHING)
    config_diff = models.TextField(blank=True, null=True)
    parameter_diff = models.TextField(blank=True, null=True)
    hash = models.CharField(unique=True, max_length=150)
    edited = models.DateTimeField(auto_now_add=True)
    was_built = models.NullBooleanField()

    def __str__(self):
        return self.hash
    class Meta:
        managed = False
        db_table = 'test_config_history'


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


	def getPath(self, area=None, cluster=None, local=True):
		if self.id is not 0:
			if cluster == None:
				#TODO
				if area == 'results':
					return settings.getPath('tests') + '/' + self.name +'/results' 
				elif area == 'configs':
					return settings.getPath('tests') + '/' + self.name +'/configs' 
				elif area == 'scripts':
					return settings.getPath('tests') + '/' + self.name +'/scripts' 
				elif area == 'output':
					return settings.getPath('tests') + '/' + self.name +'/output' 
				elif area == 'error':
					return settings.getPath('tests') + '/' + self.name +'/error' 
				else:			
					return settings.getPath('tests') + '/' + self.name 
			else:
				if local is True:
					if area == 'results':
						return settings.getPath('tests', cluster.local_path) + '/' + self.name +'/results' 
					elif area == 'configs':
						return settings.getPath('tests', cluster.local_path) + '/' + self.name +'/configs' 
					elif area == 'scripts':
						return settings.getPath('tests', cluster.local_path) + '/' + self.name +'/scripts' 
					elif area == 'output':
						return settings.getPath('tests', cluster.local_path) + '/' + self.name +'/output' 
					elif area == 'error':
						return settings.getPath('tests', cluster.local_path) + '/' + self.name +'/error' 
					else:			
						return settings.getPath('tests', cluster.local_path) + '/' + self.name 
				else:
					if area == 'results':
						return settings.getPath('tests', cluster.remote_path) + '/' + self.name +'/results' 
					elif area == 'configs':
						return settings.getPath('tests', cluster.remote_path) + '/' + self.name +'/configs' 
					elif area == 'scripts':
						return settings.getPath('tests', cluster.remote_path) + '/' + self.name +'/scripts' 
					elif area == 'output':
						return settings.getPath('tests', cluster.remote_path) + '/' + self.name +'/output' 
					elif area == 'error':
						return settings.getPath('tests', cluster.remote_path) + '/' + self.name +'/error' 
					else:			
						return settings.getPath('tests', cluster.remote_path) + '/' + self.name 
		else:
			return None

	def createTestDirectory(self, cluster):
		directories = [None, 'results','configs','output','scripts']
		#create local directories
		for d in directories:
			if self.getPath(d) is not None:
				if not os.path.exists(self.getPath(d)):
					try:
						os.makedirs(self.getPath(d))					
					except OSError as e:
						logging.error("Test: Can not create directories for test %s",e)
						raise
		#create directories in locally mounted cluster fs 
		for d in directories:
			if self.getPath(d, cluster) is not None:
				if not os.path.exists(self.getPath(d, cluster)):
					try:
						os.makedirs(self.getPath(d, cluster))					
					except OSError as e:
						logging.error("Test: Can not create directories for test %s",e)
						raise
				
						
	def generateRunScript(self, cluster):
		#ensure that directories exist
		self.createTestDirectory(cluster)
		
		local_filename = self.getPath('scripts') + '/run_' + cluster.name + '_' + cluster.batchsystem.name +'.sh'
		remote_filename = self.getPath('scripts', cluster, False) + '/run_' + cluster.name + '_' + cluster.batchsystem.name +'.sh'
		
		try:
			with io.FileIO(local_filename, "w") as file:
				if cluster.batchsystem.header is not None and len(cluster.batchsystem.header) > 0:
					file.write(cluster.batchsystem.header)

				if self.run_script is not None and len(self.run_script) > 0:
					file.write("\n\n#-----TEST RUN SCRIPT------\n")	
					file.write("\n\n")								
					#TODO rewrite as curl call to REST API
					file.write("ssh ${CPERF_USER}@${CPERF_HOST} -i ${CPERF_SSHKEY} ${CPERF_DIR}/bin/cp_result.sh --hasStarted=$TestResultId\n")
					file.write(self.run_script)
								
				if self.analysis_script is not None and len(self.analysis_script) > 0:
					file.write("\n\n#-----TEST ANALYSIS SCRIPT------\n")	
					file.write(self.analysis_script)
					file.write("\nssh ${CPERF_USER}@${CPERF_HOST} -i ${CPERF_SSHKEY} $CPERF_DIR/bin/cp_result.sh --writeResult=$TestResultId --result=$Result --details=$ResultDetails\n")
				if cluster.batchsystem.footer is not None and len(cluster.batchsystem.footer) > 0:
					file.write("\n\n#-----BATCHSYSTEM FOOTER-----\n")
					file.write(cluster.batchsystem.footer)
				file.close()
				#copy run script into cluster fs
				try:
					copyfile(local_filename, self.getPath('scripts', cluster))
				# eg. src and dest are the same file
				except shutil.Error as e:
					logging.error('Test: could not copy build script to cluster: %s' % e)
					return None
				# eg. source or destination doesn't exist
				except IOError as e:
					logging.error('Test: could not copy build script to cluster: %s' % e.strerror)
					return None
				return remote_filename
		except IOError as e:
			logging.error("Test: could not create run script in " + self.getPath('scripts') + filename+ "\n" + e)
			return None

							
	def generateBuildScript(self, cluster):
		#ensure that directories exist
		self.createTestDirectory(cluster)
		
		local_filename = self.getPath('scripts') + '/build_' + cluster.name + '_' + cluster.batchsystem.name +'.sh'
		remote_filename = self.getPath('scripts', cluster, False) + '/build_' + cluster.name + '_' + cluster.batchsystem.name +'.sh'
		
		try:
			with io.FileIO(local_filename, "w") as file:
				if cluster.batchsystem.header is not None and len(cluster.batchsystem.header) > 0:
					file.write(cluster.batchsystem.header)
				file.write("\n\n")		
				file.write("ssh ${CPERF_USER}@${CPERF_HOST} -i ${CPERF_SSHKEY} ${CPERF_DIR}/bin/cp_result.sh --hasStarted=$TestResultId\n")	
				if self.build_script is not None and len(self.build_script) > 0:
					file.write("\n\n#-----TEST BUILD SCRIPT------\n")	
					file.write(self.build_script)								
				file.write("\n\ncd $CPERF_DIR\n")							
				file.write('if [ "$built" = true ] ; then\n')		
				file.write("\tssh ${CPERF_USER}@${CPERF_HOST} -i ${CPERF_SSHKEY} << EOF ${CPERF_DIR}/bin/cp_result.sh --built=$TestConfigHash\n")
				file.write('\tssh ${CPERF_USER}@${CPERF_HOST} -i ${CPERF_SSHKEY} $CPERF_DIR/bin/cp_result.sh --writeResult=$TestResultId --result=1.0 --details={"build": "success"}\n')
				file.write("\t${CPERF_DIR}/bin/cp_test.sh --$TestType=$TestID --test_config=$TestConfigID --nodes=$RUN_NODES --hash=$TestConfigHash\nEOF\n")
				file.write("else\n")
				file.write('\tssh ${CPERF_USER}@${CPERF_HOST} -i ${CPERF_SSHKEY} $CPERF_DIR/bin/cp_result.sh --writeResult=$TestResultId --result=-1.0 --details={"build": "failed"}\n')
				file.write("fi")
				if cluster.batchsystem.footer is not None and len(cluster.batchsystem.footer) > 0:
					file.write("\n\n#-----BATCHSYSTEM FOOTER-----\n")
					file.write(cluster.batchsystem.footer)
				file.close()
				#copy run script into cluster fs
				try:
					copyfile(local_filename, self.getPath('scripts', cluster))
				# eg. src and dest are the same file
				except shutil.Error as e:
					logging.error('Test: could not copy build script to cluster: %s' % e)
					return None
				# eg. source or destination doesn't exist
				except IOError as e:
					logging.error('Test: could not copy build script to cluster: %s' % e.strerror)
					return None
				return remote_filename
		except:
			logging.error("Test: could not create build script in " + self.getPath('scripts'))
			return None

	def buildTest(self, test_config, nodes, tcv, test_type):
		if test_type == 'TEST':
			test_type_start="startTest"
			#node=nodes[0]
			run_nodes=[]
			for n in nodes:
				run_nodes.append(n.id)
		elif test_type == 'TEST_ARRAY':
			test_type_start="startTestArray"
			#node = nodes[0][0]
			run_nodes=[]
			for t in nodes:
				temp = []
				for n in t:
					temp.append(n.id)
				run_nodes.append(temp)
				
		cluster = node.cluster
		cluster.connect()
		if cluster.connection is None:
			logging.error("No SSH connection to cluster login node")
			return
			
		

		if test_config is not None:
			node_types = test_config.getAllNodeTypeIDs()
			
			if len(node_types)>0 and node.node_type_id not in node_types:
				logging.error("Test: Node of wrong type '%s' assinged to test '%s' with config '%s'",node.node_type_id, self.name, test_config.name)
				return		

		buildscript_file = self.generateBuildScript(cluster)
		
		res = Result()
		res.type="build"
		res.test_config_id = test_config.id
		res.test_config_version_hash = tcv.hash
		
		res.insertDB(db.dbcursor)
		
		rtn = Result2Node()
		rtn.result_id = res.id
		rtn.node_id = node.id
		rtn.node_type_id=node.node_type_id
		rtn.insertDB(db.dbcursor)
		
		test_config.parameter['env']['RUN_NODES']=str("[{}]".format(",".join(map(repr, run_nodes))))
		test_config.parameter['bs']['num_nodes']=1
		logging.debug("RUN_NODES: %s", test_config.parameter['env']['RUN_NODES'])
		test_config.parameter['env']['TestType']=test_type_start
		
		res.job_id = cluster.batchsystem.submit(cluster, buildscript_file, nodes, self, test_config, tcv, res)
		
		cluster.disconnect()
		if res.job_id is not None:
			res.save()
			
		else:
			res.result = -1
			res.result_detail['error']="Could not start build due to batchsystem"
			res.setResult(db.dbcursor)
			logging.error("Test: Could not start build due to batchsystem")

	def startTest(self, test_config, nodes, tcv_hash=None):
		if test_config==None:
			test_config=TestConfig()
			test_config.getDefaultConfig(db.dbcursor, self.id)
		if test_config.id==0:
			logging.error("Test: could not get default test config for test '%s'", self.id)
			return 
			
		tcv=TestConfigVersion()
		if tcv_hash==None:
			tcv.getCurrentVersion(db.dbcursor, test_config.id)
		else:
			tcv.getVersionByHash(db.dbcursor, tcv_hash)
			test_config.getConfigByVersion(tcv.id)
			
		if tcv.id==0:
			logging.error("Test - startTest: Invalid test config version supplied, hash: '%s'", tcv_hash)
			return
			
		if self.needs_building is True and tcv.was_built is False:
			logging.info("Building Test %s for Config %s before running", self.id, test_config.id)
			
			self.buildTest(test_config, nodes, tcv, 'TEST')
			return
		
		cluster = nodes[0].cluster
		
		cluster.connect()
		if cluster.connection is None:
			logging.error("No SSH connection to cluster login node")
			return
		
		
		#nodes must be of the same node type as defined in test config -> check
		if test_config is not None:
			node_types = test_config.getAllNodeTypeIDs()
			for n in nodes: 
				
				if len(node_types)>0 and n.node_type_id not in node_types:
					logging.error("Test: Node of wrong type '%s' assinged to test '%s' with config '%s'",n.node_type_id, self.name, test_config.name)
					return		
		
		run_path = self.generateRunScript(cluster)
		
		res = Result()
		res.type="run"
		res.test_config = test_config
		res.test_config_version_hash = tcv.hash
		
		res.save()
		
		for n in nodes:
			res.nodes.add(n)
			
		res.job_id = cluster.batchsystem.submit(cluster,run_path, nodes, self, test_config, tcv, res)
		
		cluster.disconnect()
		
		if res.job_id is not None:
			res.save()
			
		else:
			res.result = -1
			res.result_detail['error']="Could not start test due to batchsystem"
			res.save()
			logging.error("Test: Could not start test due to batchsystem")
		

	def startTestArray(self, test_config, nodes, tcv_hash=None):
		if db.dbcursor is None:
			db.dbConnect()
		if test_config==None:
			test_config=TestConfig()
			test_config.getDefaultConfig(db.dbcursor, self.id)
		if test_config.id==0:
			logging.error("Test: could not get default test config for test '%s'", self.id)
			return 
			
		tcv=TestConfigVersion()
		if tcv_hash==None:
			tcv.getCurrentVersion(db.dbcursor, test_config.id)
		else:
			tcv.getVersionByHash(db.dbcursor, tcv_hash)
			test_config.getConfigByVersion(tcv.id)
			
		if tcv.id==0:
			logging.error("Test - startTest: Invalid test config version supplied, hash: '%s'", tcv_hash)
			return
		if self.needs_building is True and tcv.was_built is False:
			#TODO build and 
			logging.info("Building Test %s for Config %s before running", self.id, test_config.id)
			
			self.buildTest(test_config, nodes, tcv, 'TEST_ARRAY')
		else:
			#nodes = [[n1,n2],[n3,n4]]	
			for ns in nodes:
				self.startTest(test_config, ns, tcv_hash)
		

	def __str__(self):
		return self.name
	class Meta:
		managed = False
		db_table = 'tests'
        
        
        
class Schedule(models.Model):
	id = models.BigAutoField(primary_key=True)
	begin = models.DateTimeField()
	repeat = JSONField()
	#    test_id = models.IntegerField(blank=True, null=True)
	test = models.ForeignKey(Test, models.DO_NOTHING)
	#    test_config_id = models.IntegerField(blank=True, null=True)
	test_config = models.ForeignKey(TestConfig, models.DO_NOTHING)
	nodes = JSONField()
	test_type = models.CharField(max_length=50, blank=True, null=True)
	# cluster_id = models.IntegerField(blank=True, null=True)
	cluster = models.ForeignKey(Cluster, models.DO_NOTHING)
	
	def updateCronTab(self):
		try:
			my_cron = CronTab(user=settings.OS_USER)
		except:
			logging.error("Schedule: can not open crontab on '%s'", self.cluster.id)
		if self.nodes == []:
			return
				
		for job in my_cron:
			if job.comment == 'cluster_perf_' + self.test.id + "_" + self.test_config.id + "_" + self.begin:
				#TODO details of job config
				job.hour.on(self.repeat['hour'])
				job.day.on(self.repeat['day'])
				job.dow.on(self.repeat['dow'])
				job.month.during(self.repeat['month'])
				if self.test_type == "TEST":
					starttesttype = "--startTest"
				elif self.test_type == "TEST_ARRAY":
					starttesttype = "--startTestArray"
#				TODO
				job.command = cfg.getPath() + '/bin/cp_test.sh ' + starttesttype + "="+self.test.id + " --test_config="+self.test_config.id+" --nodes="+json.dumps(self.nodes)
				try:
					my_cron.write()
				except:
					logging.error("Schedule: can not write crontab on '%s'", self.cluster.id)
				logging.info('Schedule: Cron job modified successfully')
		
		my_cron.write()
		
	def insertCronTab(self):
		try:
			my_cron = CronTab(user=settings.OS_USER)
		except:
			logging.error("Schedule: can not open crontab on '%s'", self.cluster.id)
			
		if self.nodes == []:
			return
			
		job = my_cron.new()
		job.hour.on(self.repeat['hour'])
		job.day.on(self.repeat['day'])
		job.dow.on(self.repeat['dow'])
		job.month.during(self.repeat['month'])
		if self.test_type == "TEST":
			starttesttype = "--startTest"
		elif self.test_type == "TEST_ARRAY":
			starttesttype = "--startTestArray"
		job.command = cfg.getPath() + '/bin/cp_test.sh ' + starttesttype + "="+self.test.id + " --test_config="+self.test_config.id+" --nodes="+json.dumps(self.nodes)
		try:
			my_cron.write()
		except:
			logging.error("Schedule: can not write crontab on '%s'", self.cluster.id)
		logging.info('Schedule: Cron job inserted successfully')
		
		
	def removeCronTab(self):
		try:
			my_cron = CronTab(user=settings.OS_USER)
		except:
			logging.error("Schedule: can not open crontab on '%s'", self.cluster.id)
			
		for job in my_cron:
			if job.comment == 'cluster_perf_' + self.test.id + "_" + self.test_config.id + "_" + self.begin:
				my_cron.remove(job)
				try:
					my_cron.write()
				except:
					logging.error("Schedule: can not write crontab on '%s'", self.cluster.id)
				logging.info('Schedule: Cron job removed successfully')
				return
		logging.warn("Schedule: Could not find matching CRONTAB entry to remove")	
		
	
	class Meta:
		managed = False
		db_table = 'schedule'

