import os
import sys
import site

site.addsitedir('/home/USER/sites/##sub##/trunk/venv/lib/python2.6/site-packages')
 
#Calculate the path based on the location of the WSGI script.
apache_configuration = os.path.dirname(__file__)
project = os.path.dirname(apache_configuration)
workspace = os.path.dirname(project)
sys.path.append(workspace)

sys.path.append('/home/USER/sites/##sub##/trunk/')
sys.path.append('/home/USER/sites/##sub##/trunk/auto')


os.environ['DJANGO_SETTINGS_MODULE'] = 'auto.settings'
os.environ['PYTHON_EGG_CACHE']="/home/USER/sites/##sub##/trunk/auto/apache/egg-cache"

 
import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()

