from celery.decorators import task
from celery.utils.log import get_task_logger
import time
from datetime import datetime, timedelta

#from feedback.emails import send_feedback_email
from django.db import models
from django.db.models.signals import *
import json
from overview.models import *

logger = get_task_logger(__name__)

@task(name="task_cluster_init")
def task_cluster_init(cluster_id, request_data):
	try:
		cluster = Cluster.objects.get(id=cluster_id)
	except Cluster.DoesNotExist:
		logging.error("Celery Task: task_cluster_init no cluster defined for id %s" % cluster_id) 
		return
	logging.debug("Init Cluster %s" % cluster.name) 
	cluster.connect()
	if cluster.connection is not None:
		cluster.batchsystem.initNodes(cluster)
	cluster.disconnect()
	

@task(name="task_results_clean")
def task_results_clean():
	Result.objects.filter(result=-1.0).delete()
	time_threshold = datetime.now() - timedelta(days=1)

	Result.objects.filter(end=None).filter(submit__lt=time_threshold).delete()


@task(name="task_start_test")
def task_start_test(test_id, request_data):
	try:
		test = Test.objects.get(id=test_id)
	except Test.DoesNotExist:
		logging.error("REST API: startTest no test defined for id %s" % test_id) 
		return
	try:
		test_config = TestConfig.objects.get(id=request_data['test_config'])
	except TestConfig.DoesNotExist:
		logging.error("REST API: startTest no test config defined for id %s" % request_data['test_config']) 
		return
	nodes = []
	snodes = json.loads(request_data['nodes'])
	
	
	logging.debug("REST API: startTest nodes defined %s" % snodes) 
	for n in snodes:
		nodes.append(Node.objects.get(id=n))
	if len(nodes)==0:
		logging.error("REST API: startTest no nodes defined %s" % request_data) 
		return
	
	cluster = nodes[0].cluster
	cluster.connect()
	if 'hash' in request_data:
		hash_list=json.loads(request_data['hash'])
		parameter = None
		for h in hash_list:
			test.startTest(cluster, test_config, nodes, h, parameter)
	else:
		sparameter = json.loads(request_data['parameter'])
		
		hash=None
		for n in sparameter:
			parameter = []
			for s in n:
				parameter.append(ParameterValue.objects.get(id=s))			
			
			test.startTest(cluster, test_config, nodes, hash, parameter)
			time.sleep(1)
	cluster.disconnect()
   
@task(name="task_start_test_array")
def task_start_test_array(test_id, request_data):
	test = Test.objects.get(id=test_id)
	test_config = TestConfig.objects.get(id=request_data['test_config'])
	nodes = []
	
	#if node_type is set configuration will be tested on every node
	if 'node_type' in request_data:
		snodes=[]
		nss=Node.objects.filter(node_type=request_data['node_type'])
		cluster=nss[0].cluster
		for n in nss:		
			snodes.append([n.id])
	else:
		snodes = json.loads(request_data['nodes'])
		nnt=Node.objects.get(nodes[0][0])
		cluster=nnt.cluster
	
	
	
	cluster.connect()
	for ns in snodes:
		nodes = []
		for n in ns:
			nodes.append(Node.objects.get(id=n))
		if len(nodes)==0:
			logging.error("REST API: startTest no nodes defined %s" % request_data) 			
		if 'hash' in request_data:
			hash_list = json.loads(request_data['hash'])
			parameter = None
			for h in hash_list:
				test.startTest(cluster, test_config, nodes, h, parameter)
				time.sleep(1)
		else:
			sparameter = json.loads(request_data['parameter'])
			
			hash=None
			for n in sparameter:
				parameter = []
				for s in n:
					parameter.append(ParameterValue.objects.get(id=s))			
				test.startTest(cluster, test_config, nodes, hash, parameter)
				time.sleep(1)
	cluster.disconnect()
#		return

#	logging.debug("REST API: startTest nodes defined %s" % snodes) 
#	for ns in snodes:
#		nodes = []
#		for n in ns:
#			nodes.append(Node.objects.get(id=n))
#		if len(nodes)==0:
#			logging.error("REST API: startTest no nodes defined %s" % request_data) 

#		if 'tcv_hash' in request_data:
#			tcv_hash=request_data['tcv_hash']
#		else:
#			tcv_hash=None
#		test.startTest(test_config, nodes, tcv_hash)
   
