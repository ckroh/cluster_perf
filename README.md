Cluster Perf Tool


Run:

source cp_django/bin/activate
cd /home/s1428123/cluster_perf_web/

Start Django Server:
python manage.py runserver 0.0.0.0:8000


Start Celery Worker:
celery -A cluster_perf_web worker -l info

Run Redis Server:
redis-server
