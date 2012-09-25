import os
import sys
import site

site.addsitedir('/<your path>/sites/dev/trunk/venv/lib/python2.6/site-packages')
 
#Calculate the path based on the location of the WSGI script.
apache_configuration = os.path.dirname(__file__)
project = os.path.dirname(apache_configuration)
workspace = os.path.dirname(project)
sys.path.append(workspace)

sys.path.append('/<your path>/sites/dev/trunk/')
sys.path.append('/<your path>/sites/dev/trunk/auto')


os.environ['DJANGO_SETTINGS_MODULE'] = 'auto.settings'
os.environ['PYTHON_EGG_CACHE']="/<your path>/sites/dev/trunk/auto/apache/egg-cache"

 
import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()

