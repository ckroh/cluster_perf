from celery.decorators import task
from celery.utils.log import get_task_logger

#from feedback.emails import send_feedback_email
from overview.models import *
import json

logger = get_task_logger(__name__)



@task(name="task_start_test")
def task_start_test(test_id, request_data):
	test = Test.objects.get(id=test_id)
	test_config = TestConfig.objects.get(id=request_data['test_config'])
	nodes = []
	snodes = json.loads(request_data['nodes'])

	logging.debug("REST API: startTest nodes defined %s" % snodes) 
	for n in snodes:
		nodes.append(Node.objects.get(id=n))
	if len(nodes)==0:
		logging.error("REST API: startTest no nodes defined %s" % request_data) 

	if 'tcv_hash' in request_data:
		tcv_hash=request_data['tcv_hash']
	else:
		tcv_hash=None
	test.startTest(test_config, nodes, tcv_hash)
   
