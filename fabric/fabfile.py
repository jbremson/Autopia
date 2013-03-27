from fabric.api import local,cd, settings,run,env
import os
import pdb
from app.misc import buyveh, adt

# User and host data redacted. 3/27/2013. JB

ARCHIVE_DIR = "/home/USER/db_archive"
SITES_DIR = "/home/USER/sites/"
USER = "nobody"
QUICK_FILE="quick_game.sql" # db dump to quickly restart game from the top

def set_hosts():
    env.hosts = ['USER@HOST.com:90210']

def aftr(instance):
    """Advance the turn with popveh and buyveh on host -instance-."""
    input = raw_input("This will run a full turn advance on %s including popveh and buyveh. Is this what you want?" % instance).strip()
    if input == "Y" or input=="y":
    	run("go%s; cdaa; python misc.py turn" % instance)
    else:
        print "Canceled."
	
def push_up():
    """Push the code through main. Following the commit. First does the push
    to main, and then pushes to abt."""
    local("bzr push; gomain; cd dev; bzr push")
    
def view_settings():
    """Print a list of interesting settings values."""
    import settings
    vals = [] # for extra stuff
    vals.extend(list(settings.CHECK_VALS))
    print  "\nSome Settings of Interest\n============================\n"
    for val in vals:
        try:
            print val + " - " + str(getattr(settings,val))
        except AttributeError:
            print val + " - !!! Missing !!!"

def venv_path(arg):
    """Make a base path to the venv. Returns path to /dev/ for the venv."""
    global SITES_DIR
    path = SITES_DIR + arg + "/trunk/"
    return path

def kill_base_sql(arg):
    """Gets rid of the troublesome base.sql file. I need to fix this for real. Hack for now.
       <arg> is the venv name."""
    with cd( venv_path(arg) + "auto/game_sql"):
        local("rm base.sql*")
        local("bzr resolve base.sql")
    
def egg_prep(arg):  
    """Make egg-cache and python-eggs dirs."""
    server()
    with cd(SITES_DIR +  arg + "/trunk/auto/apache"):
        local("mkdir egg-cache",capture=False)
        local("mkdir python-eggs")
        local("sudo chown www-data python-eggs egg-cache") 

def server():
    name = os.uname()[1]
    if name == "USER-LNAMEs-macbook.local" or name=="autopia-2.local":
            raise ValueError("Function not available on this machine.")

def devbox():
    global USER
    name = os.uname()[1]
    print name
    if name == "USER-LNAMEs-macbook.local":
	USER = "USERLNAME"
    elif name=="autopia-2.local":
	USER = "NAME"
    else:
        if name=="abt":
            # stupid way to do this - change later.
            raise ValueError("Function not available on this machine.")
        define = raw_input("Not a known devbox, is this one? (Y,N) ").strip()
        if not define in["Y","y"]:
            raise ValueError("Function not available on this machine.")
        else:
	    USER = "USERLNAME"
            return True

def make_venv(arg):
    """Make a virtual-env on the server in directory arg, under SITES_DIR."""
    global SITES_DIR
    server()
    dir = SITES_DIR+"/"+arg + "/trunk"
    with cd(dir):
        local("virtualenv --no-site-packages venv")
        local("echo 'venv' >> .bzrignore")
        local("./venv/bin/easy_install django")
        local("./venv/bin/easy_install ipython Psycopg2")
        local("./venv/bin/easy_install pygooglechart")
        local("./venv/bin/easy_install django-extensions")
        #local("./venv/bin/easy_install python-memcached")
        
    dir = SITES_DIR+"/"+arg + "/trunk/src"
    with cd(dir):
        local("tar zxvf cluster-1.1.1b3.tar.gz")
        with cd(dir + "/cluster-1.1.1b3"):
            local("python setup.py install")
        local("rm -rf ./cluster-1.1.1b3")
	print "!!! Need to add GoogleChartWrapper (or whatever) here!!!"
        



def make_host(arg):
    """Helper function. Appends subdomain name to domain and returns the string."""
    return arg + ".HOST.com"

def make_rule(tech,div):
    """Make a RuleBase subclass that creates text for drivetrain Award rules.
    Input: tech(str), div(int)."""
    with open("./templates/rule_base.py") as f:
        out = f.read()
        f.close()
        out=out.replace("##first_tech##",tech.capitalize())
        out=out.replace("##up_tech##",tech.upper())
        out=out.replace("##lc_tech##",tech.lower())
        out=out.replace("##div##",div)
        print out



def sub_template(arg,template):
    """Change the tag ##sub## to -arg- in template file (in templates dir). Return string with \
        replaced value."""
    with open("./templates/" + template) as f:
        out = f.read()
        f.close()
        if template=="settings.py":
            print out.count("LOCAL_AJAX")
            out = out.replace("LOCAL_AJAX","GOOG_AJAX")
            print out.count("LOCAL_AJAX")
        return out.replace("##sub##",arg)

def nginx(arg):
    server()
    """Make a virtual host for nginx"""
    # first read in the template
    str = sub_template(arg,"nginx_vhost")
    host = make_host(arg)
    with open("./templates/"+host,"w") as file:
            file.write(str)

            file.close()
    with settings(warn_only=True):
        result = local("mkdir /home/USER/logs/"+arg,capture=False)
    local("sudo mv -f ./templates/" + host + " /etc/nginx/sites-enabled/" + host)
    local("sudo /etc/init.d/nginx stop",capture=False)
    local("sudo /etc/init.d/nginx start",capture=False)

def apache(arg):
    """Make a virtual host file for apache."""
    # first read in the template
    server()
    str = sub_template(arg,"apache_vhost")
    host = make_host(arg)
    with open("./templates/"+host,"w") as file:
        file.write(str)
        file.close()
    with settings(warn_only=True):
        result = local("mkdir /home/USER/logs/"+arg,capture=False)
    local("sudo mv -f ./templates/" + host + " /etc/apache2/sites-enabled/" + host)
    local("sudo /etc/init.d/apache2 stop",capture=False)
    local("sudo /etc/init.d/apache2 start",capture=False)

def cleaners(str):
    """Helper method for clean_code. Do not call directly, use clean_code."""
    return str.replace("pdb.set_trace()","")
   
def clean_code(arg):
    """Remove bad stuff, like pdb.set_trace() from the server code base."""
    server()
    files = ["views.py","models.py"]
    base_dir = SITES_DIR  + arg + "/trunk/auto/app/"
    
    for f in files:
        file = base_dir + f

        local("perl -pi -e 's/pdb.set_trace()//' " + file)

    return True

def swap_settings(arg=None):
    """Swap in the settings file <arg> for settings.py and run update_settings_template."""
    import filecmp
    backfile = ".back_settings.py"
    set_dir = os.environ['AUTO'] + "/set_files"
    print set_dir
    if arg==None:
        print "\nAvailable settings.py files: \n==========================\n"
        print local("ls %s" % set_dir,capture=False)
    else:
        with cd(set_dir):
            print "Copying back current settings into set_file/."
            local("cp ../settings.py %s/%s" % (set_dir,backfile))
            # check to see if this file exists as the exact same
            # if it does then stop -
            # if it does not then ask use if he wants to save this file with a name.
            files = os.listdir(set_dir)
            out = False
            for file in files:
                if file == backfile:
                    pass
                else:
                    out = filecmp.cmp(set_dir+"/"+file,set_dir+"/" + backfile)
                    if out == True:
                        print "This is identical to file: %s. Not saving it again." % file
                        break

            if out == False:
                # we did not find a similar file ask if user wants to save it
                over = False
                term = raw_input("This file does not exist enter a save name: ").strip()
                if term in files:
                    response = raw_input("This file exists (in name). Overwrite it?").strip()
                    if response in ['y','Y']:
                        local("cp %s %s" % (backfile,term))
                else:
                    local("cp %s %s" % (backfile,term))
            print "Copying file %s to settings.py and running update_settings_template(). " % arg
            if arg in files:
                local("cp %s/%s ../settings.py" % (set_dir,arg))
                update_settings_template()
            else:
                print "File %s does not exist." % arg


def archive_db(arg):
    """Push db into an archive of the form arg/date/name.sql"""
    if arg=="":
        arg = "unnamed"
    instance = os.environ['INSTANCE']
    date = local('date "+%Y-%m-%d.%H:%M"')
    loc = ARCHIVE_DIR + "/" + date
    settings_loc = SITES_DIR +  os.environ['INSTANCE'] + "/trunk/auto/settings.py"
    print "settings_loc = " + settings_loc
    setup_loc = SITES_DIR +  os.environ['INSTANCE'] + "/trunk/auto/app/game_setup.py"
    if os.path.isdir(loc):
        raise Exception("Quitting: This directory already exists. Why? : %s" % loc)
    local("mkdir -p %s" % loc)
    with cd(loc):
        result = local('pg_dump -UUSER ' + os.environ['INSTANCE'] + "_autopia > " + arg+".sql")
        local("cp " + settings_loc + " .",capture=False)
        local("cp " + setup_loc +  " .",capture=False)
    print "cd %s" % loc
 
def undo_host(arg):
    """Remove a subdomain - arg.autopia2010.com, removes the file directory too."""
    server()
    host = make_host(arg)
    local("sudo rm -f /etc/nginx/sites-enabled/"+host,capture=False)
    local("sudo rm -f /etc/apache2/sites-enabled/"+host,capture=False)
    local("rm -rf /home/USER/sites/"+arg,capture=False)
    with settings(warn_only=True):
    # dump and drop the db, if it exists
#        result = local('pg_dump -UUSER ' + arg + "_autopia > " + SITES_DIR + " " + arg + "_data_safety.sql")
        archive_db(arg)
	
	with settings(warn_only=True):
        	result = local('dropdb -UUSER ' + arg + "_autopia")

def bzr_co(arg):
    """Check out from bzr into /home/USER/sites/<arg>/."""
    server()
    with settings(warn_only=True):
        local("mkdir /home/USER/sites/"+arg,capture=False)
    with cd("/home/USER/sites/"+arg):
        with settings(warn_only=True):
            local("bzr co /home/USER/bzr_home/trunk/",capture=False)

def update_clones(arg='all'):
    """Update all the clone apps in /sites to the latest version level."""
    server()
    if arg=="all":
        out = local('ls '+SITES_DIR).split('\n')
    else:
        out = [arg]
    first = True
    for o in out:
        print "Working on %s" % o
        str = sub_template(o,"settings.py")
        with open("/home/USER/sites/" + o + "/trunk/auto/settings.py","w") as file:
            file.write(str)
            file.close()
        
        with cd(SITES_DIR + o + "/trunk"):
            local ('bzr update',capture=False)
            print "bzr update <" + o +">"
            if first:
                print "Moving over media directory."
                first=False
                local("rm -rf /home/USER/dev/media" ,capture=False)
                local("cp -R ./media /home/USER/dev/media" ,capture=False)
		with cd("/home/USER/dev/media"):
		    local("bzr co /home/USER/bzr_home/video")
            
        
def make_db(arg,file="top2012.sql"):
    """Make a postgres db with the form <arg>_autopia. \
        The arg <file> must be a file in game_sql."""
    global QUICK_FILE
    sql_dir = "%s/game_sql" % os.environ['AUTO']
    if models_updated()==False:
        input = raw_input("models.py has not been updated. Reuse current db setup? (y/n) ")
        if input.lower() == 'y':
            # try to reuse the QUICK_FILE
            try:
                loc = "%s/%s" % (sql_dir,QUICK_FILE)
                file = open(loc,"r")
                local("psql -UUSER " + arg + "_autopia  < " + loc)
            except IOError:
                print "No QUICK_FILE. Taking the long way."
            else:
                raise SystemExit("game_start is complete.")

    global SITES_DIR
    file = arg + "_" + file
    if arg != os.environ['INSTANCE']:
        raise IntegrityError("Input arg: %s does not match INSTANCE env var: %s. Set venv for this instance." % (arg, os.environ['INSTANCE']))
    server()
    with cd("/home/USER/sites/"+arg+"/trunk/auto/game_sql"):
        with settings(warn_only=True):
            # dump and drop the db, if it exists
            result = local('pg_dump -UUSER ' + arg + "_autopia > old_data_safety.sql")
            with settings(warn_only=True):
                print "New code right here 5/31/12"
                out = local('psql -l | grep ' + arg + '_autopia | wc -l')
                if int(out) == 1:
            	    result = local('dropdb -UUSER ' + arg + "_autopia")
        local("createdb -UUSER -Odjango " + arg + "_autopia",capture=False)
        local("python " +  SITES_DIR+arg+"/trunk/auto/manage.py syncdb --noinput",capture=False)
        local("python " +  SITES_DIR+arg+"/trunk/auto/app/game_setup.py full",capture=False)

def fix_app(arg):
    """Correct the settings.py and auto.wsgi for the app - make sure files align correctly."""

    server()
    str = sub_template(arg,"settings.py")
    with open("/home/USER/sites/" + arg + "/trunk/auto/settings.py","w") as file:
        file.write(str)
        file.close()
    str = sub_template(arg,"auto.wsgi")
    with open("/home/USER/sites/" + arg + "/trunk/auto/apache/auto.wsgi","w") as file:
        file.write(str)
        file.close()
    str = sub_template(arg,"apache_django_wsgi.conf")
    with open("/home/USER/sites/" + arg + "/trunk/auto/apache/apache_django_wsgi.conf","w") as file:
        file.write(str)
        file.close()
    str = sub_template(arg,"server.env.sh") # write python path and other important env vars
    with open("/home/USER/sites/" + arg + "/trunk/env.sh","w") as file:
        file.write(str)
        file.close()
    view_settings()


def build_host(arg):
    """Creates virtual host files, checks out app from bzr and sets up .wsgi files."""

    server()
    if arg=="all":
        abort("The arg 'all' is not allowed. Use a different subdomain name.")

    bzr_co(arg)
    fix_app(arg)
    make_db(arg)
    egg_prep(arg)
    nginx(arg)
    apache(arg)
    print("Next run make_venv for this arg...")

def models_updated():
    """Has models.py been updated since last check?"""
    import string
    import os.path
    dir = "%s/app" % os.environ['AUTO']
    out = False
    last_mod = os.path.getmtime(dir + "/models.py")
    try:
        foo = open(dir + "/.models_modtime","r")
        modtime = string.atof(foo.read().strip())
        if last_mod > modtime:
            print "models.py has changed"
            out = True # cannot use old file

    except IOError:
        print ".models_modtime doesn't exist"
        out = True # cannot use old file - do it again full

    local ("echo %s > %s/.models_modtime" % (last_mod,dir))
    str = " were "
    print "Models updated: " + out.__str__()
    return out



def local_reset(arg='',force_quick=False):
    """Drop the local db and rebuild it. To use a premade database send no arg. To rebuild the db and save it send arg 'full' - dropdb, createdb, syncdb..."""
    global QUICK_FILE
    global USER
    dir = "%s/app" % os.environ['AUTO']
    sql_dir = "%s/game_sql" % os.environ['AUTO']
    instance = os.environ['INSTANCE']
    devbox()

    if models_updated()==False or force_quick:
        input = raw_input("models.py has not been updated. Reuse current db setup? (y/n) ")
        if input.lower() == 'y':
            # try to reuse the QUICK_FILE
            try:
                loc = "%s/%s" % (sql_dir,QUICK_FILE)
                file = open(loc,"r")
                db = instance + "_db"
		
		with settings(warn_only=True):
                	local("dropdb -UUSER " + db)
                local("createdb -UUSER -Odjango " + db)
                local("psql -UUSER " + db + " < " + loc)
            except IOError:
                print "No QUICK_FILE. Taking the long way."
            else:
                raise SystemExit("Completed game_start.")


    db = "%s_db" % os.environ['INSTANCE']
    with settings(warn_only=True):
    	local("dropdb -UUSER %s" % db, capture=False)
    local("createdb -UUSER -Odjango %s" % (db))
    out = local("python %s/auto/manage.py syncdb --noinput" % os.environ['SITE_DIR'])
    out = local("python %s/auto/app/game_setup.py %s" % (os.environ['SITE_DIR'],arg), capture=False)
    print "This script has been run with SELENIUM test file."

def update_settings_template():
    """Update the settings.py template for fabric when changes have been made to settings.py"""
    import filecmp
    devbox()

    file = "%s/auto/settings.py" % os.environ['SITE_DIR']
    template = "%s/templates/settings.py" % os.environ['FAB']
    out = local(" grep -n '<variable section>' %s" % file)
    start = int(out.split(":")[0])+1
    end = local(" wc -l %s " % file)
    end = end.split(" ")[0]
    out = local("sed -n '%s,%sp' %s" % (start,end,file))

    # get the fixed section of the template
    fixed = local("grep -n '<variable section>' %s" % template)
    fixed_start=fixed.split(":")[0]
    new_head = local("head -%s %s" % (fixed_start,template))
    final = new_head + "\n\n\n\n\n" + out
    with cd("%s/templates/" % os.environ['FAB']):
        local('cp settings.py settings.bak')
        with open(template,"w") as file:
            file.write(final)
            file.close()
    template = "%s/templates/settings.py" % os.environ['FAB']
    bak = "%s/templates/settings.bak" % os.environ['FAB']
    if filecmp.cmp(template,bak):
        print "No changes registered in settings.py. No need to commit."
    else:
        print "Done. Settings template updated. Not committed."


def import_video():
    """Move the video file out of the video work directory into the deployment directory
    and create the meta.txt file."""
    devbox()
    import fileinput
    vidir ='/Users/USERLNAME/Desktop/Videos/Final'
    print "Files Available: \n"
    dirs = []
    i = 0
    for dir in os.listdir(vidir):
        print "%s. %s" % (i,dir)
        dirs.append(dir)
        i=i+1

    val = input("Enter number to transfer: ")
    group = raw_input("Enter heading group: ").strip()
    link = raw_input("Enter link text: ").strip()

    loc = os.path.join(vidir,dirs[val],'meta.txt')
    local("echo '#meta.txt file built by fab import_video' > %s" % loc )
    local("echo class = %s >> %s" % (group,loc))
    local("echo link = %s >> %s" % (link,loc))

    # fix up the title for the index.html


    title = raw_input("Enter a short page title: ").strip()
    loc = os.path.join(vidir,dirs[val],'index.html')

    local("perl -p -i.bak -e 's/Created by Camtasia/%s/g' %s" % (title,loc))




    loc = os.path.join(vidir,dirs[val])
    target = '/Users/NAME/Dropbox/tmp_work/dev/media/video'

    local("cp -R %s %s" % (loc,target),capture=False)

def make_gloss_entry():
    """Send a formatted glossary.html entry to STDOUT based on prompting at the command line. """
    term = raw_input("Enter term: ").strip()
    define = raw_input("Enter definition: ").strip()
    print "<p><span class='gloss'>%s</span> - %s </p>" % (term,define)

def revno():
    """Return the bzr rev number."""
    out = local("bzr log | head -2 | tail -1")
    print out

def start_game(instance,force_quick=False):
    """Rebuild the database and advance two turns. This puts the game in start mode."""
    global QUICK_FILE
    postfix = "_db"
    pdb.set_trace()
    try:
        devbox()
        local_reset(arg='',force_quick=force_quick) # no arg is a quick build, send 'full' if you want db rebuilt
                    # from bottom up
    except ValueError:# this is the server
        server()
        make_db(instance)
    with cd("%s/app" % os.environ['AUTO'] ):
	print "first quick_turn"
        local("python misc.py turn_quick",capture=False)
	print "second quick_turn"
        local("python misc.py turn_quick",capture=False)
        local("python misc.py mass_passwd",capture=False)
        local("python misc.py prep_game",capture=False)

    with cd("%s/game_sql" % os.environ['AUTO'] ):
        result = local('pg_dump -UUSER ' + instance + postfix + " > " + QUICK_FILE)

    view_settings()


def sg():
    """Quick start_game."""
    import settings
    instance = os.environ['INSTANCE']
    try:
        len(settings.NAME)
    except AttributeError:
        raise AttributeError("*** settings.NAME is not set! ***")
    start_game(instance,True)


archive_tables=['auth_user']

def make_archive_db():
    """Create the archive db and tables."""
    local("createdb -UUSER -Odjango main_archive",capture=False)
    sql = """CREATE TABLE meta
        (
          "name" character(40) NOT NULL,
          date date,
          "desc" text,
          computer_players character(200),
          id SERIAL,
          CONSTRAINT meta_pkey PRIMARY KEY (id)
        )
        WITH (
          OIDS=FALSE
        );
        ALTER TABLE meta OWNER TO django;"""

    sql = sql.replace("\n"," ")
    local("psql -UUSER -Odjango -dmain_archive -c < '%s' " % sql)

def sleeper(n, counter=1, beeps=0):
    """Sleep n seconds with counter of <counter> seconds. Default
        of counter is 1. <beeps> (=0) sets count of warning beeps run before        the sleep.  Not a precise counter. Approximate n  only."""
    import time
    import sys
    total = 0
    print "Sleeping %s secs." % n
    for i in range(0,beeps):
        print('\a')
    while total <= n:
        time.sleep(counter)
        total += counter
        print "%s of %s" % (total,n) 
        sys.stdout.flush()

def run_turn():
    """Run a turn. This waits 30 seconds then runs buyveh then waits 600 seconds then runs adt."""
    sleeper(5)
    print "Running buyveh now..."
    buyveh()
    print "advancing turn in  60 seconds!"
    sleeper(20,beeps=4)
    sleeper(10,beeps=10)
    print "Running adt"
    adt()
    print "==================== Turn Completed ===========================\n"

def adt():
    """Run advance_turn from misc.py --> python misc.py adt. No buyveh. No popveh.
    Just a straight turn advance."""
    import app
    app.misc.adt()

def buyveh():
    """Run a buyveh --> python misc.py buyveh. """
    import app
    app.misc.buyveh()
