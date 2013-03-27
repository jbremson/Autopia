# <fixed section>
# Django settings for djdemo project.
# auto generated from template by fabric
import sys
import os
from random import randint

SETUP = {}


sys.path.append('/home/USER/sites/##sub##/trunk')


SETUP_DIR = '/home/USER/sites/##sub##/trunk/auto/'
DEBUG = True
TESTING = True

TEMPLATE_DEBUG = DEBUG


ADMINS = (
     ('Joel Bremson', 'USER3000@gmail.com'),
)
###### GAME SETTINGS #######


#AUTHENTICATION_BACKENDS=('auto.auth_backends.AutopiaUserModelBackend',)

MANAGERS = ADMINS
DATABASE_ENGINE = 'postgresql_psycopg2'           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': "##sub##_autopia" ,
        'OPTIONS':{"autocommit": True},
        'USER':'django',
        'PASSWORD':'pass1234'
    }
}
#DATABASE_ENGINE = 'sqlite3'           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.

# Set DATABASE_NAME and TEMPLATE_DIRS like this. TEMPLATE_DIRS is below.

HOME_DIR = SETUP_DIR
VIDEO_DIR='/home/USER/dev/media/video/'
DATABASE_NAME="##sub##_autopia"
TEMPLATE_DIRS=SETUP_DIR+"templates"

DATABASE_USER = 'django'             # Not used with sqlite3.
DATABASE_PASSWORD = 'pass1234'         # Not used with sqlite3.
DATABASE_HOST = ''             # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

RECORD_DIR = "game_sql" # the directory in HOME_DIR where game sql dumps will be made.

# <variable section>




LOCAL_AJAX="/site_media/jquery.min.js"
GOOG_AJAX="http://ajax.googleapis.com/ajax/libs/jquery/1.5.1/jquery.min.js"

AJAX_LIB=LOCAL_AJAX
RUN_TESTS= False# runs tests inside Turn.advance_turn. Turn off for performance and deployment.

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.


# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'auto.app.AdvanceTurn.AdvanceTurn'
)

ROOT_URLCONF = 'auto.urls'


#if server=="vlap":
#	TEMPLATE_DIRS = (
#		'/Users/USERFOO/.virtualenvs/a2/auto/templates',
#	)
CHECK_VALS = ['NAME','DATABASE_NAME','AJAX_LIB','SAFE_TIME','NO_BUY_TIME',\
              'CAFE_LEVELS','FUEL_MARKET','ELASTICITY','VEHICLE_MAX_PRODUCTION',\
              'VEHICLE_MAX_RUN','GAME_TYPE','SESSION_CACHE','COMPUTER','COST_ARRAYS','FEEBATES'] # vals to print out in fab settings
AUTOPIA_USER_BASE = ('app',)

GAME_TYPE="autobahn" # set to 'autobahn' for vp only fast game or 'autopia' for full game
# How much it costs to change the price of a vehicle for a vehicleproducer.

NAME="AEO High Feebate - Low Volatility - Scenario" # required!

if GAME_TYPE not in ['autopia','autobahn']:
    raise ValueError("GAME_TYPE must be either 'autopia' or 'autobahn', not ' %s  '.") % GAME_TYPE
else:
    if GAME_TYPE == 'autobahn':
        TEMPLATE_DIRS = TEMPLATE_DIRS + "/autobahn"

COMPUTER=['gtech','green','spec1_high','enthusiast','executive','family','young'] # vps controlled by computer
COST_ARRAYS = False # True = Fuel cost entered as arrays, False means fuel costs are in lambda form.

CAFE_PENALTY = 5.5 # cost per tenth of mile shortfall of cafe level
CAFE_LEVELS={ 1975:27.5, 2016:35, 2025:54.5, 2040:62} # year:mpg -

VEIL_MAX = 5 # How smart the computer VPs are. Set at 2 for a very smart VP (unbeatable)
            # and 10 for a a very dumb VP. Default of 5 is a competitive value.

VEHICLE_PRICE_CHANGE_FEE = 0.5
GAS_GUZZLER = 14 # mpg for gas_guzzler fee
GAS_GUZZLER_TAX = 3000

INIT_FLEET_DTS={'gas':0.98,'diesel':0.02 } # make up, by drivetrain of player init fleets.
                                            # Needs to sum to 1. Must be legal drivetrain name strings.

QUICK_SCORE_ADJ = 0.125 # parameter to quick_score_vehicle
MPG_GATE = 0.66 # the minimum percentage of consumer's average fleet mpg that is tolerated for auto-built cars
# PLAY_PROMPT_CODES are the possible int classes associated with PlayPrompt codes.
# See PlayPrompt.new()
PLAY_PROMPT_CODES = dict(none=0,fuel_overspend=1,good_work=2,consumer_1=3,
                         consumer_2=4,cap_bonus_1=5,cap_bonus_2=6, cap_prompt=7,
                         rd_earned=8,veh_dump=9,con_quota=10,neg_balance=11)
# The CONSUMER_INIT dict sets up the init fleet per consumer. The dts entry is
# is a breakdown of drivetrain percentage. The 'style_to_perf' is the ratio
# of style to performance preference. Higher style to perf ratios will yield higher
# mpg vehicles and vice versa.
CONSUMER_INIT={'green':{'dts':{'gas':0.76,'diesel':0.18,'gas hev':0.05,'bev':0.01}, 'style_to_perf':1.4},
                'family':{'dts':INIT_FLEET_DTS,'style_to_perf':1.2},
                 'executive':{'dts':INIT_FLEET_DTS,'style_to_perf':0.9},
                 'spec1_high':{'dts':INIT_FLEET_DTS,'style_to_perf':0.9},
                 'enthusiast':{'dts':INIT_FLEET_DTS,'style_to_perf':0.9},
                 'young':{'dts':INIT_FLEET_DTS,'style_to_perf':1.0},

                }
VEHICLE_LICENSING = 0.09
CONSUMER_COLORS=['E89123','001e98','D40000','321B00','068900']
FEEBATES = True # Are Feebates in play?
FEEBATE_LEVEL = 1.0/16.0 # The feebate level in gallons-per-mile
FEEBATE_COST = 1000 # dollars per .01 GPM

VEHICLE_VMT =[ 1.25,1.03, 0.85, 0.70, 0.58, 0.48, 0.39, 0.33,0]
VEHICLE_SURVIVAL =[1, 0.93, 0.75, 0.54, 0.35, 0.20, 0.10, 0,0]
VEHICLE_DEMOGRAPHICS = [ x / sum(VEHICLE_SURVIVAL) for x in VEHICLE_SURVIVAL] # expected age profile of the fleet
                                                                            # per turn

VP_RD = {'gtech':{'bev':6,'hev':5,'h2':3,'gas':2,'diesel':1,'road_load':4},
         'mega':{'gas':6,'road_load':5,'hev':4,'bev':3,'diesel':2,'h2':1},
        'asian':{'gas':6,'hev':5,'road_load':4,'bev':3,'h2':2,'diesel':1},
        'euro':{'road_load':6,'diesel':5,'gas':4,'hev':3,'gas':2,'h2':1}
    }

SESSION_CACHE=True  # use session caching?

SAFE_TIME=80 # number of seconds that consumers must wait to buy new vehicles.
NO_BUY_TIME = 10 # number of seconds into the turn that consumers are blocked from buying cars.
#VMT_TMP_REDUCE=0.01  #percentage of vmt to reduce for one turn for a pref point
MESSAGE_CHECK_INTERVAL = 20000 # milliseconds - polling time between message checks.
#VMT_PERM_REDUCE=0.001  # percentage permanent vmt to reduce for one pref point
#
#
#VMT_PREF_REDUCE=0.01 # what percent of vmt to reduce for a pref point, of off base_vmt.


KILL_LIST=[] # list of vp names to ignore when auto-populating system. These are the ones that can be actively playes.

MIN_INIT_MPG = 18 # used in models.init_fleet as the minimum mpg for a vehicle that is automatically build in init.

VP_TEST_VEHS = {'mega':[{'name':'mega 1','style':10,'performance':10,'run':250,'drivetrain':'gas'},
                    {'name':'mega lux','style':20,'performance':18,'run':100,'drivetrain':'gas'},
                    {'name':'mega volt','turn':4,'style':12,'performance':14,'run':200,'drivetrain':'gas phev40'},
                    {'name':'mega 2','style':15,'performance':15,'run':200,'drivetrain':'gas'}],

                'gtech':[{'name':'gt 1','style':2,'performance':2,'run':250,'drivetrain':'gas hev'},
                             {  'name':'gt d','style':5,'performance':5,'run':250,'drivetrain':'diesel'},
                             {  'name':'gt h2','style':2,'performance':2,'margin':0,'run':250,'drivetrain':'h2','turn':4},
                                 {  'name':'gt BEV','style':2,'performance':0,'margin':0,'run':100,'drivetrain':'bev'}],
                'euro':[{'name':'euro a','style':12,'performance':8,'run':250,'drivetrain':'diesel'},
                             {  'name':'euro b','style':8,'performance':5,'run':250,'drivetrain':'diesel'},
                             {  'name':'euro b.h2','style':8,'performance':4,'margin':-5,'run':250,'drivetrain':'h2','turn':3},
                                 {  'name':'euro hev','style':5,'performance':3,'margin':0,'run':250,'drivetrain':'gas hev'},
                ],
                'asian':[{'name':'asian x1','style':8,'performance':8,'run':250,'drivetrain':'gas','margin':2},
                        {  'name':'asian x2','style':2,'performance':2,'run':250,'drivetrain':'gas','margin':2},
                        {  'name':'asian gas hev','style':12,'performance':12,'margin':3,'run':250,'drivetrain':'gas hev'},
                ]
}

VP_TEST_RD = {'mega':{'gas':2,'diesel':1,'hev':1,'style':1,'performance':2},
                'gtech':{'gas':1,'bev':2,'style':2,'road_load':2,'h2':2,'hev':1},
                'asian':{'road_load':2,'style':2,'performance':2,'gas':2,'hev':2},
                'euro':{'road_load':3,'diesel':2,'h2':1,'performance':2,'style':2,'gas':1,'hev':1}}


DRIVETRAIN_CLASSES = {'cv_hev':['gas hev','diesel hev'],
                    'cv':['diesel','gas'],
                    'cv_phev':['diesel phev10','diesel phev40','gas phev10','gas phev40'],
                    'h2':['h2'],
                    'h2_phev':['h2 phev10','h2 phev40'],
                    'bev':['bev']}

VP_START_BALANCES = {'mega':15,'asian':15,'gtech':15,'euro':15,'v_init':0} # starting balance for each vp.

STYLE_LEVEL_COST=500 # how much it costs to add a point of style to a vehicle
STYLE_INC=2 # how much reductino in level cost a point of style r&d gets you. 
PERFORMANCE_LEVEL_COST=500 # how much it costs to add a point of performance
PERFORMANCE_INC=2 # how much reduction in cost a point of performance rd gets
EMISSIONS_LEVEL_COST=100 # how much it costs to add an emissions level

RD_MIN = 4 # The number of RD points a VP automatically receives in a turn
RD_PROFIT_COST = 100000 # The amount of profit required to get an RD point
RD_MAX = 12 # The maximum number of RD points the user can earn in a turn.
RD_PROFIT_BONUS = 2 # extra rd points for making any profit at all (i.e. > 0)

PLOT_TURNS = 12 # the number of turns to plot in aggregate data graphs
PLOT_SIZE= "400x400" # plot size string . Default is 400x400
#### RULE POINTS DEFINED HERE #####

#STYLELEADER=2 # for style leader of turn
#PERFORMANCELEADER=2
#STYLELAGGARD=-2 # for worst style
#PERFORMANCELAGGARD=-2
#FIRSTBEV=4 # points given for selling first bev
#FIRSTH2=4 # points given for selling first h2
#
#
## divs - increment based awards
#HEVDIV=400 # hev point given for every x sold
#H2DIV=100 # "     "
#GASDIV=400
#DIESELDIV=400
#BEVDIV=100
#PHEVDIV=200





##### END RULE POINTS

#### VP Scaling Function ####
VEHICLE_DISTRESS_SALE=0.75 #The penalty per unit (%) for VP who does not meet the min sales

VEHICLE_SCALING_STEP=10 # The steps size for vehicle production, i.e. VP can produce VEHICLE_SCALING_STEP*n
VEHICLE_MAX_PRODUCTION=250 # Point at which efficiency multiplier is best (min).
VEHICLE_MAX_RUN = 300  # total number VP can create of the vehicle

                                                            # increase costs.
# old SCALING_FXN
#def VEHICLE_SCALING_FXN(num,scaling_mod):
#    return 2*((num+scaling_mod+0.0)/VEHICLE_MAX_PRODUCTION)**2 - 4.5*((num+scaling_mod+0.0)/VEHICLE_MAX_PRODUCTION) + 4




MIN_MULT=1.5 # min (best) multiplier for VP production
MAX_MULT=4.0 # max mult at 0 units produced = y intercept

# new system 11/27/10 jb
# Below moved to models.py __vsf__ 4/26/11 jb
#def VEHICLE_SCALING_FXN(num,scaling_mod): # this curve is a linear descent followed by a flat.
#    out = MIN_MULT # best multiplier
#    quantity = num + scaling_mod
#    if quantity <= VEHICLE_MAX_PRODUCTION:
#        slope = (MIN_MULT - MAX_MULT) / (VEHICLE_MAX_PRODUCTION + 0.0)  # slope is negative
#        out = slope * quantity + MAX_MULT
#    return out




VEHICLE_RUNS={'min':10,'max':VEHICLE_MAX_PRODUCTION,'step':VEHICLE_SCALING_STEP}# this fills the runs select box in new_vehicle.html
#VEHICLE_SCALING_FXN="2*Math.pow(((x+scaling_mod)/%s),2) - 4.5*((x+scaling_mod)/%s) + 4" % (VEHICLE_MAX_PRODUCTION, VEHICLE_MAX_PRODUCTION)## The multiplier function for
YEAR_START=2004
YEAR_TURN_LEN=4
FUEL_ALLOWANCE_PERCENT = 0.45  # This is the percent of the consumer allowance added on to account for fuel consumption. 1.0 = 100%

FUELS = ['gas','diesel','bev','h2'] # System symbols for the fuel types

FUEL_MARKET=False # Set to 'True' to use supply/demand/elasticity in setting fuel price.
                        # SEt to 'False' to use the direct values set in GAS_COST,DIESEL_COST,H2_COST,ELEC_COST
ATTRIT_REFINERIES = FUEL_MARKET # Turn off refinery attrition. Usually want this to be the same as FUEL_MARKET.

# TO IMPLEMENT! 5/9/11
#ATTRIT_ELEC = True # Do you want electric power plants to be attrited? Turn this to False if there
                    # is a utility player

REFINERY_LIFE = 6; # How many turns a refinery lasts for.
LINK_DIESEL = True # link diesel base price to gas price (ignore DIESEL_COST settings).

ELASTICITY=0.2 # Elasticity of consumers


FUEL_BACK_HISTORY = 2 # Offset to current_turn for fuel COST arrays so that fuel price history
                 # can be shown
# VEH_ATTR is used to in the new_vehicle/build_vehicle process.
# coef is mpg multiplier. low coef (close to zero) means low impact on mpg for this attr and vice versa
# base is the default value for the attr, at which it's cost and mpg effect is 0
# min is the minimum value that the attr can hold
# max is the max value that the attr can hold
VEH_ATTR={'style':{'coef':0.4, 'base':10,'min':0,'max':30},
          'performance':{'coef':1, 'base':10,'min':0,'max':30},}
GAME_YEARS = []
# FUEL_YEARS starts at YEAR_START - FUEL_BACK_HISTORY*YEAR_TURN_LEN and then
# progress out from there by increments of YEAR_TURN_LEN

for i in range(-FUEL_BACK_HISTORY,20): # 20 is chosen as an arbitrarily long number, i.e. we won't get there.
    GAME_YEARS.append(YEAR_START+i*YEAR_TURN_LEN)


if COST_ARRAYS==True:
    # FUEL SEED PRICES
    GAS_COST=[ 1.25,1.25,2.4,3.1,4.05,5.2,4.3, 5.2, 5.9, 8.6,7.8, 9 ,9.6,9.9, 9.8, 10.4 ,11,11.5]
    #DIESEL_COST=[ 1.15,1.15,2.6,3.2,3.9,5.1,7.3,7.4,8,8.4,8.4,8.7,8.5,9,10,11,12,14]
    H2_COST=[ 9,8,8,7.7,7.5,6.4,6.3,6.2,6,5.9,6.7,6.8,7,7,7.5,8,8.6,9]
    ELEC_COST=[ 2.5,2.8,2,4.2,3,3.8,4.1,4.7,4.8,4.8,5,5.3,5.7,6,6.2,6.4,6.8,7.2]

    if LINK_DIESEL:
        DIESEL_COST=[x*(1+randint(-3,10)*0.01) for x in GAS_COST]
else:
    import math
    #this is proper AEO High - Verified.
    # function based fuel price model. turn is argument.
    sf = lambda x: math.sin(100*x) * 0.5 # rf = random factor - but must be state specific
    cf = lambda x: math.cos(100*x) * 0.5 # rf = random factor - but must be state specific
    GAS_COST = lambda x: 1.5873 * math.log(x[0])+0.2633 + sf(x[0])
    DIESEL_COST = lambda x: 1.4236*math.log(x[0])+0.6808 + cf(x[0])
    ELEC_COST = lambda x: 0.8703*math.log(x[0])+1.5669 + sf(x[0])
    H2_COST = lambda x: 0.4021*math.log(x[0]) + 3.8525 + cf(x[0])


PHEV = {'10':0.25, '40':0.75} # The amount of electricity (as percentage of gasoline usage) a PHEVx consumes.

ELEC_CONSUMPTION = 2250 # GGE - based on 10,000 kwh per capita - transportation energy (25%)
#ELEC_CONSUMPTION=0
# default is the value for any unspecified consumer
# the arrayrs refer to turn. The array repeats once the end is reached.

#OLD_CONSUMER_ALLOWANCES={'default':8, 'c1':[8,8.5,8,7.2,8],'c2':[12,12.5,13,12,11,12],'c3':[15,14,15,14.5,15,14.3],
#                     'executive':[20],'green':[18],'family':[14],'enthusiast':[10],'young':[10]}

# CONSUMER_SAVING_LIMIT is how much the consumer can save per turn in M.
CONSUMER_SAVING_LIMIT = 1 # M (10^6)

COMPUTER_PLAYERS=['family','executive','young'] # player usernames operated by the computer/

REF_COST_MOD = 0.5 # Refinery base cost modifier. Used in selenium_setup. For init only, will not impact a live game.
AUTOMATED_BUY_MAX = 50 # the max vehicle purchase increment of the automated_buy method. Used in a non-player
                # consumer game

# The CONSUMER_LIKERT_SCALE is the qualitative descriptive model for the consumers. The numbers
# the modeling weights for the categories: Style, Performance, Price, MPG
#CONSUMER_LIKERT_SCALE={'Very High':45, 'High':35, 'Moderate':25,'Low':15,'Very Low':5, 'None':0}

NON_TRANSACTING=['v_init','v1','v2','v3'] # players that should not show up on transaction screen as possible receivers. 
#WIN_SCORE = 1000000 # The consumer goal to win the game.
INSTALLED_APPS = (

    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'auto.app',
    'auto.plotkin',
    'auto.misc',
    'django_extensions',
)

if DATABASES == 'django.db.backends.postgresql_psycopg2':

	DATABASE_OPTIONS = {
    	"autocommit": True,
	}
