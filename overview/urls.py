from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('tests/', views.test_list, name='test_list'),
    path('tests/<int:test_id>', views.test_detail, name='test_detail'),
    path('tests/<int:test_id>/config/<int:test_config_id>', views.test_config, name='test_config'),
    path('cluster/<int:cluster_id>', views.cluster_detail, name='cluster_detail'),
    path('cluster/<int:cluster_id>/node/<int:node_id>', views.node_detail, name='node_detail'),
    path('cluster/<int:cluster_id>/node_type/<int:node_type_id>', views.node_type_detail, name='node_type_detail'),
    path('cluster/<int:cluster_id>/partition/<int:partition_id>', views.partition_detail, name='partition_detail'),
    path('analysis/test', views.analysis_test, name='analysis_test'),
    path('analysis/node', views.analysis_node, name='analysis_node'),
#    path('<int:cluster_id>/nodes', views.node_list, name='node_list'),
]

