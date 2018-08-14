#!/bin/sh
ClusterPerf_Django=/home/s1428123/cluster_perf_web
PythonVirtEnv=/home/s1428123/cp_django/bin/activate

. $PythonVirtEnv
#service_django=python manage.py runserver 0.0.0.0:8000
case "$1" in
  start)
	cd $ClusterPerf_Django
	python manage.py runserver 0.0.0.0:8000 > $ClusterPerf_Django/django_server.log 2>&1 &
	celery -A cluster_perf_web worker -l info -E > $ClusterPerf_Django/celery_worker.log 2>&1 &
	celery -A cluster_perf_web beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler > $ClusterPerf_Django/celery_beat.log 2>&1 &
	;;
  stop)
	pkill -f 'python manage.py runserver 0.0.0.0:8000'
	pkill -f 'celery -A cluster_perf_web worker -l info'
	pkill -f 'celery -A cluster_perf_web beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler'
	;;

  

  restart)
	pkill -f 'python manage.py runserver 0.0.0.0:8000'
	pkill -f 'celery -A cluster_perf_web worker -l info'
	pkill -f 'celery -A cluster_perf_web beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler'
	cd $ClusterPerf_Django
	python manage.py runserver 0.0.0.0:8000 > $ClusterPerf_Django/django_server.log 2>&1 &
	celery -A cluster_perf_web worker -l info -E > $ClusterPerf_Django/celery_worker.log 2>&1 &
	celery -A cluster_perf_web beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler > $ClusterPerf_Django/celery_beat.log 2>&1 &
	;;

  

  status)
	;;

  *)
	
	exit 1
esac

exit 0

