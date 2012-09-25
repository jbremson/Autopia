from django.contrib.auth.models import User
from django.contrib.auth.models import UserManager
from django.db import models, connection, IntegrityError
from django.db.utils import DatabaseError
from django.forms import ModelForm
from django import forms
import pdb
from datetime import *
import settings
from django.db.models import Sum, Max, get_model, Q, Avg, Min, get_app, get_models
from auto.plotkin.models import get_vehicle_fxn, f2D, get_level_fxn
from django.forms.widgets import RadioSelect
#from auto.misc.models import VehicleProduction
import random
from django.contrib import admin
import re
import logging
import sys
import os
import json
from copy import deepcopy
from cluster import *
from django.core import serializers
from django.db.models.signals import post_save,pre_save
import GChartWrapper as GC
from django.template import Template,Context
#from django.dispatch import dispatcher

from pygooglechart import Chart, SimpleLineChart,Axis,GroupedVerticalBarChart, ScatterChart


logging.basicConfig(format='%(asctime)s - %(message)s', stream=sys.stdout)






##### Misc Helper Fxns

def density_hash(kwargs):
    """From an input hash of the form { 'str':<int>,...}
        return a randomly selected key according to the weights <int>.
    """
    rnd = random.randint(1,sum(kwargs.values()))
    sum_val = 0
    for key, value in kwargs.iteritems():
        sum_val += value
        if rnd <= sum_val:
            return key
    # should never get here
    raise ValueError("density hash should have returned a key. It did not.")

# Create your models here.
# this code handles a postgres autoinc problem on mac
def id_check(obj, force=False):
    """Check to make sure id is there. If force==True then force it to use the internal id_counter as it's id.
    I'm doing this to enable selenium testing - it wants a fixed id. increment=true forces the id to be sequential."""
    if obj.id == None and force != False:
        obj.id = force
    elif obj.id == None and force == False:
        # try to find the last id and assign the next int
        try:
            max = obj.__class__.all().aggregate(Max('id'))['id__max'] + 1
        except:
            max = 1

        obj.id = max
    else:
        pass


def none_to_zero(val):
    """If input val is none, return 0. Otherwise return val."""
    if val == None:
        return 0.0
    else:
        return val

def cget(name):
    """Get a consumer."""
    return Consumer.objects.get(username=name)

def dget(name):
    """Return Drivetrain object with name <name>."""
    return Drivetrain.objects.get(name=name)

def uget(name):
    if name in ['mega','gtech','asian','euro']:
        out = VehicleProducer.objects.get(username=name)
    elif name =="admin":
        out = Admin.objects.get(username="admin")
    else:
        group = User.objects.get(username=name).groups.values()[0]['name']
        mod = get_model("app", group)
        out = mod.objects.get(username=name)
    return out

def vpall():
    """Return all of the vp's except for v_init as a QL for iteration."""
    return VehicleProducer.objects.all().exclude(username='v_init')

def buy_vehicle(buyer, vehicle, quantity, force=False):
    """A helper method to allow a quick commandline purchase of a vehicle. Args are buyer name, vehicle name, and quantity to buy."""

    if buyer.__class__ == str:
        b = uget(buyer)

    else:
        b = buyer

    if vehicle.__class__ == str:
        veh = Vehicle.objects.get(turn=Turn.last_turn, name=vehicle)
    else:
        veh = vehicle

    if (quantity * veh.price / 10 ** 6 > b.balance) and not force:
        print "buyer does not have funds"
        return False

    if quantity > veh.num_available:
        print "Not enough vehicles available"
        return False

    #veh.tax_and_licensing()

    vt = VehicleTransaction(buyer=b, seller=veh.producer, quantity=quantity, vehicle=veh\
                            , amount=(quantity * veh.price / 10 ** 6), account="buy", fees=0, turn=Turn.cur_turn(),
                            desc="cl - buy_vehicles")

    vt.save()
    vt.process(veh.licensing / 10 ** 6, quantity * veh.price * 1.0 / 10 ** 6)

    print "Vehicles purchased."

    return True


def transaction_process(sender,**kwargs):
    """Callback that runs postsave 'process' on transactions."""
    obj = kwargs['instance']
    obj.process()


def auto_pricer(sender,**kwargs):
    """Makes price changes for VPs controlled by computer."""


    obj = kwargs['instance']
    print obj.seller.username + "======="

    print settings.COMPUTER
    if obj.seller.username not in settings.COMPUTER:
        return # vp is a live player
    if obj.buyer.group != "Consumer":
        #logging.debug("Buyer was not a consumer (%s)" % obj.buyer.group)
        return True # only run this if a consumer bought the cars
    if Turn.cur_turn() < 2:
        return
    r = random.randint(0,4)
    print obj.seller.username + " === MODDDING ==="
    if r == 4:
        if obj.status != "complete" and obj.account != "distress":

            print "Sales Complete: %s percent" % Turn.veh_sales_complete()
            tvs = Turn.veh_sales_complete()
            for vp in VehicleProducer.objects.filter(first=True):
                if vp.username not in settings.COMPUTER:
                    print "SKPPING vp %s " % vp.username
                    continue
                else:
                    print "RUNNING auto_pricer for %s " % vp.username
                for veh in Vehicle.objects.filter(turn=Turn.last_turn(),producer=vp):
                    if veh.producer.username not in settings.COMPUTER:
                        print "PASSING pricing on %s" % veh.producer.username
                        next
                    print "sales percent : %s" % veh.sales_percent()
                    print "turn sales complete: %s" % tvs
                    try:
                        R =1.0 * veh.sales_percent()/ tvs
                    except ZeroDivisionError:
                        R=0
                    if R > 1.05 :
                        veh.price *= random.randint(100,102)/100.0
                        veh.price = round(veh.price/1000,1)*1000
                        veh.price = min(veh.price,3*veh.production_cost)
                        print "%s price -- %s" % (veh, veh.price)
                        veh.save()
                    if R  < 0.95 and tvs > 4.0:
                        print "%s price -- %s" % (veh, veh.price)
                        veh.price *= random.randint(98,100)/100.0
                        veh.price = round(veh.price/1000,1)*1000
                        if veh.price < 0.75 * veh.production_cost:
                            veh.price = 0.75 * veh.production_cost
                            print "Min price for %s" % veh.name
                        print "%s price -- %s" % (veh, veh.price)
                        veh.save()
        else:
            print "\nskipped: status: %s acount: %s\n" % (obj.status,obj.account)
    else:
        print "Skipping - tvs = %s" % (Turn.veh_sales_complete())

    return True


####### Class Code ######################################################################

class TurnManager(models.Manager):
    def max_turn(self):
        """Get the maximum existing turn."""
        try:
            return self.filter().order_by('-pk')[0]
        except Exception:
            raise Exception("current_turn failed.")


class Turn(models.Model):
    turn = models.IntegerField()
    year = models.IntegerField()
    status = models.CharField(default="run", max_length=40)
    veh_bought= models.BooleanField(default=False) # for autobahn - tracks if automated_buy has been run
    start_time = models.DateTimeField(auto_now=True)
    end_time = models.DateTimeField(auto_now=True)
    objects = TurnManager()

    advancing = False # turn advance variabl

    def __unicode__(self):
        return '%s' % self.turn

    @classmethod
    def max_turn(cls):
        """Returns int of the max turn."""
        out = Turn.objects.filter().aggregate(Max('turn'))['turn__max']
        return out

    @classmethod
    def reset_turn_start(cls):
        """Resets the turn start time to now()."""
        Turn.objects.filter(turn=Turn.cur_turn()).update(start_time=datetime.now())

    @classmethod
    def short_year(cls, turn):
        """Returns a 2 digit year string, given a turn int."""
        yr = str(cls.turn_to_year(turn))[2:]
        return yr

    @classmethod
    def current_turn(cls):
        """The current turn is the maximum turn number in the Turn model."""
        try:
            out = cls.objects.filter().order_by('-turn')[0]
        except IndexError:
            # initialize turn 0
            t = Turn(year=settings.YEAR_START, turn=0)
            t.save()
            out = t
        return out


    @classmethod
    def calc_next_turn_year(cls):
        """Calculate the year for setting a new turn. Turn 1 is on YEAR_START."""
        return (cls.current_turn().turn * settings.YEAR_TURN_LEN) + settings.YEAR_START

    # Filter method to get last turn in the database - for dev only.
    # For production it should grab the max, in reality these should
    # be the same.

    def update(self):
        """An explicit call to save as an update. Only callable on an object that exists."""
        o = Turn.objects.get(turn=self.turn)
        # hard fail above
        # no try / except because of that
        super(Turn, self).save()

    def save(self):
        """Turn.save(): Create a new turn, but only if it does not yet exist."""
        try:
            o = Turn.objects.get(turn=self.turn)
        except Turn.DoesNotExist:
            super(Turn, self).save()

    @classmethod
    def cur_turn(cls):
        """Return the current turn number."""
        try:
            return Turn.current_turn().turn
        except IndexError:
            return 0
        except Exception, e:
            print e
            print "Initializing system. cur_turn exception caught"
            return 0

    @classmethod
    def vehs_bought(cls):
        """Returns bool stating whether automated_buy has been run.
        """
        t = cls.objects.get(turn=Turn.cur_turn())
        return t.veh_bought

    @classmethod
    def is_processing(cls):
        """Returns true if the turn is processing into the next turn. Returns false otherwise."""

        t = cls.objects.get(turn=Turn.cur_turn())
        out = False
        if t.status == "processing":
            out = True

        return out

    @classmethod
    def last_turn(cls):
        """Return the turn number for the turn prior."""
        try:
            if Turn.objects.all().count() == 1:
                # if there only one turn, and thus no prior turn, return that.
                # this fixes an init condition
                out = Turn.objects.all()[0].turn
            else:
                out = cls.cur_turn() - 1
        except Exception, e:
            print e
            return 1
        return out

    @classmethod
    def next_turn(cls):
        """Return the turn number for the next turn."""
        return (cls.cur_turn() + 1)


    @classmethod
    def cur_year(cls):
        """Return the current year."""
        return cls.turn_to_year(cls.cur_turn())

    @classmethod
    def last_year(cls):
        """Return the last turn year."""
        return cls.turn_to_year(cls.last_turn())

    @classmethod
    def turn_to_year(cls, input):
        """Convert a turn to its year equivalent."""
        if input.__class__ == "Turn":
            input = Turn.turn

        return settings.YEAR_START + (input - 1) * settings.YEAR_TURN_LEN

    @classmethod
    def turn_diff(cls, a):
        """Return the absolute value of the turn difference between a and b.
            If no value is sent for b it defaults to the current turn."""
        out = cls.cur_turn() - a
        return out


    @classmethod
    def first(cls):
        """The number of the first turn of the game. This is the turn of the first VehicleTransaction."""
        return VehicleTransaction.objects.all().aggregate(Min('turn'))['turn__min']


    @classmethod
    def num_turns(cls):
        """Number of turns played so far starting from the first turn that a vehicle transaction occurred."""
        return Turn.cur_turn() - Turn.first()

    @classmethod
    def veh_sales_complete(cls):
        """Returns the ratio of vehicle sales: expected vehicle sales as percent (int)."""
        expected = sum([con.fleet_target *1.0 for con in Consumer.objects.all()])/4.0

        sold = 0

        for vt in VehicleTransaction.objects.filter(turn=Turn.cur_turn()):
            if vt.buyer.groups.values()[0]['name'] == "consumer":
                sold += vt.quantity
        print "============== expected:%s sales:%s =====================" % (expected, sold)
        return int(100*sold/expected)

class SetUser(object):
    """This sets the request.user to be the right user class."""

    def __init__(self, view):
        self.view = view

    def __call__(self, request, *args, **kwargs):
        u = request.user

        if u.id == None:
            #logging.debug("User does not exist.")
            kwargs['Anonymous'] = True

        try: # group is used only for subclass info - only one entry allowed (className)
        # for the user group
            group = User.objects.get(id=u.id).groups.values()[0]['name']
        except IndexError:
            print "index error"
            # user is a regular user
            return User
        except User.DoesNotExist:
            #logging.debug("User does not exist exception")
            request.user = User()
            pass
        else:
            mod = get_model("app", group)
            request.user = mod.objects.get(username=request.user.username)
            if request.user.active == False:
                loggging.debug("User is inactive: %s" % request.user.username)
                request.user = User()
            #logging.debug("user: " + request.user.username)
        return self.view(request, *args, **kwargs)


class Drivetrain(models.Model):
    name = models.CharField(max_length=40)
    fuel = models.CharField(max_length=20)
    desc = models.CharField(max_length=100,default="None")
    hev = models.BooleanField()
    phev = models.IntegerField()
    bev = models.BooleanField()
    adoption_base = models.FloatField(default=5000) # used in Vehicle.get_max() - the base for calculating how many
    # more vehicles of drivetrain type 'name' can be purchased on this turn.
    adoption_multiplier = models.FloatField(
            default=2.5) # the multiplier - how many times the current level of the drivetrain
    # can be purchased . Used in get_max. The problem that must be considered
    # is vehicle classes. Do I limit based on drivetrain or on class? I lean
    # towards class by drivetrain is easier.



    def __unicode__(self):
        return self.name

    @classmethod
    def hytrans_dts(cls):
        """Returns array of all hytrans drivetrain names."""
        return ['gas','gas hev','diesel','diesel hev','h2']

    @classmethod
    def all_dts(cls):
        """Returns array of all drivetrain names."""
        return ['gas','gas hev','gas phev10','gas phev40',
                'diesel','diesel hev','diesel phev10', 'diesel phev40',
               'h2', 'h2 phev10','h2 phev40','bev']


class AutopiaUser(User):
    group = "autopia user"
    balance = models.FloatField(default=0)
    first = models.BooleanField(default=True) # is this first visit to this user? yes - then show intro pages.
    computer = models.BooleanField(default=False) # should the computer play this character? i.e. NPC./
    objects = UserManager()
    desc = models.CharField(default=" I have no description! ", max_length=300)
    active = models.BooleanField(default=True)

    def __unicode__(self):
        return '%s' % self.username



    @classmethod
    def set_computer_players(cls):
        """Sets or unsets computer attr based on settings.COMPUTER_PLAYERS contentst"""
        for user in settings.COMPUTER_PLAYERS:
            o = uget(user) # will throw exception if the player name does not exist.
        for user in AutopiaUser.objects.all():
            if user.username in settings.COMPUTER_PLAYERS:
                user.computer=True
            else:
                user.computer=False
            user.save()


    def get_prompts(self):
        """Return the PlayPrompts for this turn for this user."""
        out = PlayPrompt.objects.filter(user=self,turn=Turn.cur_turn()).order_by('priority')
        if out.count() ==0:
            PlayPrompt.new(user=self,turn=Turn.cur_turn(),
                    message="Good work.",code=PlayPrompt.codes['good_work'])
            out = PlayPrompt.objects.filter(user=self,turn=Turn.cur_turn()).order_by('priority')
        return out


    @classmethod
    def user_list(cls, me):
        """Return a list of all active AutopiaUsers, including admin."""
        ulist = list()
        users = Transaction.transacting_users(me)
        for u in users:
            ulist.append(u)
        extra = AutopiaUser.objects.filter(Q(username="admin") | Q(username=me));
        for u in extra:
            ulist.append(u)
        return ulist

    @property
    def check_messages(self):
        """Returns boolean for if player should check their messages."""
        retval = False
        out = MessageReceiver.objects.filter(receiver=self, status="unsent").count()
        if out > 0:
            retval = True
        return retval

    @property
    def new_message_count(self):
        """Returns count of messages the player has not seen, i.e. unsent, and switch status to 'sent'."""
        out = MessageReceiver.objects.filter(receiver=self, status="unsent").count()
        return out

    def new_message_count_and_process(self):
        """Returns count of messages the player has not seen, i.e. unsent, and switch status to 'sent'."""

        out = self.new_message_count
        MessageReceiver.objects.filter(receiver=self, status="unsent").update(status="sent")
        return out

    def update_balance(self, amount):
        """"""
        try:
            self.balance = self.balance + amount
            self.save()
        except RuntimeError:
            print "update_balance failed: %s " % self

    def base_context(self):
        turn = Turn.current_turn().turn
        home = "%s/base.html" % self.template_dir
        finished = TurnComplete.objects.filter(turn=Turn.cur_turn())
        #        try:
        #            turn = Turn.objects.get(turn=Turn.cur_turn())
        #        except Turn.DoesNotExist:
        #            print "EXCEPTION CAUGHT: Setting turn to the max turn in Turn."
        #            turn = Turn.objects.max_turn()
        #            Turn.current_turn = turn.turn

        context = dict(turn=turn, user=self, template_dir=self.template_dir, home=home, year=Turn.cur_year(),
                       username=self.username, group=self.group, balance=self.balance, finished=finished)
        context['users'] = AutopiaUser.user_list(self)
        if self.username=="admin":
            context['users'].append(AutopiaUser(username="all"))
        context['AJAX_LIB']=settings.AJAX_LIB
        context['message_check_interval']=settings.MESSAGE_CHECK_INTERVAL
        return context

    def fee(self, to_user, amount, desc):
        """ Pay a fee or tax from a player to a non-player role."""
        # Ideally fees, taxes and rebates would be organized into a
        # table so they would not be spread out over the whole code base.

        seller = AutopiaUser.objects.get(username=to_user)
        t = Transaction(buyer=self, seller=seller, amount=amount, desc=desc, turn=Turn.cur_turn())

        #try:
        t.save()
        t.process()
        #except Exception:
        #    raise Exception( "Transaction.fee - save and process try block failed.")

        return True


    def vehicle_stats(self):
        """Provide stats about the users fleet. Returns dict. dict['all'] is the sum \ 
            dict['gas'] is the sum of all gas vehicles. Also dict['diesel'], dict['h2'], 
            dict['bev']"""
        indict = {'owner': self}
        dict = {}

        all = Fleet.objects.count_vehicles(**indict)
        tally_mpg = 0 # tallies are to compute average mpg for all
        tally_count = 0
        dict['all'] = all
        dict['phev_elec'] = 0
        sum_vmt = 0
        for f in settings.FUELS:
            indict = {'fuel': f, 'owner': self}
            dict[f] = Fleet.objects.count_vehicles(**indict)
            try:
                tally_count = tally_count + dict[f]
            except TypeError:
                pass

            mpg = f + "_mpg"
            vmt = f + "_vmt"
            gals = f + "_gals"

            try:
                o = self.sum_weighted_mpg(**indict)
                dict['phev_elec'] = dict['phev_elec'] + o['phev_elec']
                dict[mpg] = o['mpg']
                dict[vmt] = round(float(o['vmt']) / 10 ** 6, 1)
                try:
                    dict[gals] = int(float(o['vmt']) / float(o['mpg']))
                except ValueError:
                    dict[gals] = 0
                try:
                    tally_mpg = tally_mpg + dict[f] * dict[mpg]
                except TypeError:
                    pass
                sum_vmt = sum_vmt + o['vmt']
            except AssertionError:
                dict[mpg] = "NA"
        try:
            dict['all_mpg'] = round(tally_mpg / float(tally_count), 2)
        except ZeroDivisionError:
            dict['all_mpg'] = "NA"
        dict['total_vmt'] = round((float(sum_vmt) / 10 ** 6), 2)
        return dict

    def sum_weighted_mpg(self, **kwargs):
        """Get the sum weighted mpg for a vehicle. Age weighting includes
            both the count of the vehicle type and its age to calculate the
            average mpg. Formula is sum(count * age_vmt / vehicle.mpg)."""


        #   indict = {'fuel':f,'owner':self}
        vehs = Fleet.objects.filter(**kwargs).exclude(quantity=0)
        gals = 0
        phev_elec = 0
        sum_miles = 0
        out = {}
        for v in vehs:
            phev = v.vehicle.drivetrain.phev
            v_miles = float(v.quantity) * v.vehicle.vehicle_vmt_modifier() *\
                      float(kwargs['owner'].base_vmt) * settings.YEAR_TURN_LEN
            if phev:
                gals += v.nonev_gge(v_miles)
            else:
                gals += v_miles / v.vehicle.mpg

            # Is the vehicle a PHEV? If so we must account for electricity consumption.
            if phev > 0:
                phev_elec += v.ev_gge(v_miles)

            sum_miles = sum_miles + v_miles
        try:
            out['mpg'] = sum_miles / (gals + phev_elec)
        except ZeroDivisionError:
            # "ZeroDivisionError"
            out['mpg'] = "NA"
        out['vmt'] = sum_miles
        out['phev_elec'] = phev_elec
        return out


class PlayPrompt(models.Model):
    """A PlayPrompt is a message sent to the player to prompt game action. It consists
        of a message text, a turn on which the message will be revealed, a recipient and a
        priority code that will set the order that the messages are placed on the report screen."""

    # class variable codes
    codes = settings.PLAY_PROMPT_CODES

    user = models.ForeignKey(AutopiaUser)
    message = models.TextField(max_length=1000)
    turn = models.IntegerField()
    priority = models.IntegerField(default = 0)
    code = models.IntegerField(default=0)

    def __unicode__(self):
        return ("%s" % self.message)

    @classmethod
    def new(cls,user, message, turn=Turn.next_turn(),priority = 0,code=0):
        """ New PlayPrompt to <user> with <message> . Optional <turn> assignment and <priority>, which
        sets the position of the prompt in revelation. Higher priority means higher placement. Returns
        the object.
        """
        try:
            # see if the code has already been set.
            out = cls.objects.get(user=user,turn=turn, code=code)
        except cls.DoesNotExist:
            out = cls(user=user,message=message,turn=turn,priority=priority,code=code)
            out.save()
        return out

    @classmethod
    def vp_prompts(cls):
        for vp in VehicleProducer.objects.all():
            try:
                out = vp.market_position_data()['data']
                con_count = len(filter(lambda x: x>2, out[-1]))
                if con_count <= 1:
                    PlayPrompt.new(user=vp,message="Get more consumer groups! (See charts).  ",priority=9,
                                   code=PlayPrompt.codes["consumer_1"])
                elif con_count == 2:
                    PlayPrompt.new(user=vp,message="Try to get another consumer group in your market.", priority=6,
                                   code=PlayPrompt.codes['consumer_2'])
                con_count = len(filter(lambda x: x > 25 and x < 49,out[-1]))

                if con_count > 0:
                    PlayPrompt.new(user=vp,message="Get your market share to 50% of a consumer \
                            group for a capacity bonus.", code=PlayPrompt.codes['cap_prompt'],
                            priority = 3)
                con_count = len(filter(lambda x: x>49, out[-1]))
                if con_count == 1:
                    PlayPrompt.new(user=vp,message="You're dominating a consumer group. \
                                    You've earned a 5% capacity bonus!", priority=6,
                                   code=PlayPrompt.codes['cap_bonus_1'])
                    vp.capacity = int(1.05 * vp.capacity)
                    vp.save()
                elif con_count > 1:
                    PlayPrompt.new(user=vp,message="You're dominating multiple consumer groups. \
                        You've earned a 10% capacity bonus!", priority=6,
                        code=PlayPrompt.codes['cap_bonus_2'])
                    vp.capacity = int(1.10 * vp.capacity)
                    vp.save()

            except DatabaseError:
                # game has not started yet.
                logging.debug("Database Error caught in PlayPrompt vp_prompts. Ignoring. ")
                pass
            except IndexError:
                # early turn - not a real problem.
                logging.debug("Passing on IndexError in vp_prompts")
                pass

    @classmethod
    def fp_prompts(cls):
        """Create fp prompts."""

        for fp in FuelProducer.objects.all():
            if fp.balance < 0:
                msg = "You have a negative balance."
                prmpt = PlayPrompt(turn=Turn.cur_turn(),user=fp,message=msg,code=PlayPrompt.codes['neg_balance'],priority=1)
                prmpt.save()

    @classmethod
    def consumer_prompts(cls):
        """Create play prompts for consumers."""
        for con in Consumer.objects.all():
            score = ConsumerScore.objects.get(turn=Turn.cur_turn(),user=con)

            cut = 0
            if score.quota > 0.95:
                msg = "Your drivers are very happy with the number of cars they have."
            elif score.quota > 0.90:
                msg = "Your drivers are satisfied with the number of cars they own."
            elif score.quota > 0.80:
                msg = "Your drivers would like to own more cars."
            elif score.quota > 0.70:
                msg = "Your drivers want more cars. Your drivers are considering alternate modes."
            elif score.quota > 0.60:
                cut = 0.05
                msg = "Your lost 5% of your drivers to alternate modes. They want more cars. "
            elif score.quota > 0.50:
                cut = 0.10
                msg = "Your lost 10% of your drivers to alternate modes. They want more cars. "
            elif score.quota > 0.40:
                cut = 0.15
                msg = "You lost 15% of your drivers to alternate modes. They want more cars."
            elif score.quota > 0.20:
                cut = 0.25
                msg = "You lost 25% of your drivers to alternate modes. They want more cars."
            else:
                cut = 0.35
                msg = "You lost 35% of your drivers to alternate modes. They want more cars."

            if cut  > 0:
                # drop the fleet_target by cut * 100%
                # increase base allowance by 1/2 cut * 100%
                con.fleet_target = int((1.0-cut) * con.fleet_target)
                con.base_car_cost = int(con.base_car_cost * (1.0+cut/2.0) )
                con.save()

            PlayPrompt.new(user=con,message=msg,code=PlayPrompt.codes['con_quota'],priority=10)






class TurnComplete(models.Model):
    """An entry into the table for this player means he has finished his moves for 'turn'."""

    turn = models.IntegerField()
    user = models.ForeignKey(AutopiaUser)


class Score(models.Model):
    """Base class for scoring player actions."""

    turn = models.IntegerField()
    user = models.ForeignKey(AutopiaUser)


class Ledger():
    """Helper class for VP.ledger and VP.full_ledger."""

    def __init__(self,**kwargs):
        for key in kwargs:
            try:
                setattr(self,key,round(kwargs[key],1))
            except TypeError:
                setattr(self,key,kwargs[key])

class VehicleProducer(AutopiaUser):
    """The class for the vehicle producing player. A subclass of AutopiaUser.
        Has a group of 'Vehicle Producer'. Has rd_points (R&D points) which are
        assigned as a function of sales revenue and volume. Wjat is done with the
        rd points is stored in the RandD model. """

    rd_points = models.IntegerField(default=0)   # research and development points
    base_style_cost = models.IntegerField(default=settings.STYLE_LEVEL_COST) # starting point price for style level
    #style_cost = models.IntegerField(default=settings.STYLE_LEVEL_COST)
    style_mpg = models.FloatField(default=0.4)
    base_performance_cost = models.IntegerField(
            default=settings.PERFORMANCE_LEVEL_COST) # starting point price for perf. level
    performance_cost = models.IntegerField(default=settings.PERFORMANCE_LEVEL_COST)
    performance_mpg = models.FloatField(default=1)

    scaling_mod = models.IntegerField(default=0)# a positive or negative number adjusting the scaling price for the
    # vp. If the VP has a negative number it means that it costs him
    # more to produce his vehicles while at the same nominal level as
    # as a more efficient vp. e.g. if a vp has a -50 score than it cost
    # him to produce at 750 what a vp with a 0 score could do at 700.

    capacity = models.IntegerField(default=600) # how many vehicles the VP can produce, maximum
    #base_capacity = models.FloatField(default=0.30) # what percentage of the market the VP can support
    group = "Vehicle Producer"
    template_dir = "vp"
    nav_file = "vp/vp_nav.html"

    @classmethod
    def vp_profits(cls):
        """Return a hash of vp profit info as { data: [ [],[],...] , legend: [ <usernames>], labels: []}. """
        out = {'data':[], 'legend':[], 'axis_labels':[], 'type':'bvg','title':'Producer Funds ($M)','size':'550x160'}
        for vp in VehicleProducer.objects.all().exclude(username="v_init"):
            out['legend'].append(vp.username)
            i=0
            for val in vp.balance_history():

                try:
                    out['data'][i].append(val)
                except IndexError:
                    out['data'].append([val])
                i += 1
        year = Turn.cur_year()
        out['axis_labels'] = [year-(4*i) for i in range(0,5)]
        out['axis_labels'].reverse()
#        out['axis_labels']=range(Turn.turn_to_year(t-5),Turn.turn_to_year(t),4)
        return json.dumps(out)

    def balance_history(self):
        """Return a list of balances since game start (Turn 3).
        """

        vps = VPSumData.objects.filter(producer=self,turn__gte=3)
        out = [v.profit for v in vps]
        retval = [15 + sum(out[0:i+1]) for i in range(0,len(out))]
        out = retval[-5:]
        return out

    @classmethod
    def global_ledger(cls, turn=Turn.cur_turn(), min_turn=1):
        """Return a full_ledger for all vps. SEe full_ledger for args."""
        ret = []
        for vp in VehicleProducer.objects.all().exclude(username="v_init"):
            out = vp.full_ledger(gl=True)
            for o in out:
                o.producer=vp.username
            ret.extend(out)
        ret = filter( lambda x: x.year < Turn.cur_year() and x.year > 2008, ret)
        return ret

    def full_ledger(self, turn=Turn.cur_turn(), min_turn=1,gl=False):
        """Return the full ledger between Turn.cur_turn() and <min_turn>.
        Calls ledger. Returns array of ledger objects."""
        out = []
        while turn >= min_turn:
            out.extend(self.ledger(turn=turn,gl=gl))
            turn -= 1
        out.reverse()
        return out # put latest dates first

    def ledger(self,turn=Turn.last_turn(),gl=False):
        """Return a ledger of activity for turn >= <turn>-1."""
        # Compile vehicle transactions.

        out = []
        year = Turn.turn_to_year(turn)
        counter=0
        for veh in Vehicle.objects.filter(producer=self,turn=(turn-1)):
            # re: turn - 1 -> veh is produced on turn n, sld on n+1 ,
            # since we are looking backwards a turn we're on turn n+2
            # since turn is last_turn we need to go back another turn
            # to get to vehicles we want, hence (turn-1).
            title="%s - style: %s perf: %s drivetrain: %s" % (veh.name,veh.style, veh.performance, veh.drivetrain.name)
            distress=0
            unsold = 0
            try:
                vts = VehicleTransaction.objects.get(vehicle=veh,account="distress")
                distress = vts.amount
                unsold = vts.quantity
                ledg =Ledger(**{'vehicle':veh.name,'amount':distress,'desc':'Cleared Stock (%s)' % (vts.quantity),'year':year})
                ledg.tr_id=int(counter)
                ledg.title=title
                counter += 1
                if not gl:
                    out.append(ledg)
            except VehicleTransaction.DoesNotExist:
                pass
            vtsA = VehicleTransaction.objects.filter(seller=self,vehicle=veh).aggregate(Sum('amount'),Sum('quantity'))
            amt = none_to_zero(vtsA['amount__sum'])
            qty = none_to_zero(vtsA['quantity__sum'])
            amt -= distress
            qty -= unsold
            try:
                price = (amt*1000000) / (qty)
            except ZeroDivisionError:
                price=veh.price # use MSRP
            ledg = Ledger(**{'vehicle':veh.name,'style':veh.style, 'performance': veh.performance, 'id':veh.id,

                             'amount':amt,'desc':'Sold (%s) ' % (int(qty)),'year':year,'price':price})
            ledg.tr_id = int(counter)
            ledg.title=title
            counter += 1
            out.append(ledg)
            if not gl:
                amt = VehicleTransaction.objects.get(buyer=self,vehicle=veh)
                ledg=Ledger(**{'title':"teset",'vehicle':veh.name,'amount':(-1*amt.amount),'desc':"Built (%s)" % (amt.quantity),'year':year})
                ledg.tr_id= int(counter)
                ledg.title=title
                out.append(ledg)
                counter +=1

        penalty=0

        try:
            trn =Transaction.objects.get(account="CAFE Penalty",turn=turn,buyer=self)
            penalty=-1.0*trn.amount
        except Transaction.DoesNotExist:
            pass

        out.append(Ledger(**{'title':None,'amount':penalty,'desc':"CAFE Penalty",'year':year}))
        out.reverse()
        return out

    @classmethod
    def vp_leader(cls, turn=Turn.cur_turn()):
        """Returns an object with attributes of proficiency areas for vp and values
        of the vp who leads in the field. The turn arg can be set which will give the leader
        values at different turns. It defaults to cur_turn."""

        class Leader():
            def __init__(cls):
                pass

        l = Leader()
        # calculate the style and performance leaders
        style_lead = None;
        lead_style_cost = 500000;
        perf_lead = None;
        lead_perf_cost = 500000;
        hev_lead = None;
        hev_mpg = 0;
        phev_lead = None;
        phev_mpg = 0;

        for vp in VehicleProducer.objects.all():
            # calculate style leader
            if vp.base_style_cost < lead_style_cost:
                lead_style_cost = vp.base_style_cost
                style_lead = vp.username

            # calculate performance leader
            if vp.base_performance_cost < lead_perf_cost:
                lead_perf_cost = vp.base_performance_cost
                perf_lead = vp.username

        setattr(l, 'style', style_lead)
        setattr(l, 'performance', perf_lead)

        for val in ['gas', 'diesel', 'h2', 'bev']:
            # look up the leader in terms of mpg
            # first get the leader
            leader = VehicleModel.objects.filter(turn=turn, drivetrain__name=val).aggregate(Max('mpg'))
            leads = VehicleModel.objects.filter(turn=turn, drivetrain__name=val, mpg__gt=0.98 * leader['mpg__max'])
            ulist = [x.producer.username.__str__() for x in leads]
            ulist = ",".join(ulist)

            setattr(l, val, ulist)
        for val in [['gas hev', 'diesel hev'], ['gas phev10', 'diesel phev10']]:
            leader = VehicleModel.objects.filter(turn=turn).filter(
                    Q(drivetrain__name=val[0]) | Q(drivetrain__name=val[1]))\
            .aggregate(Max('mpg'))
            # rather than averaging, it's just taking the bst hev from either the gas or the diesel
            leads = VehicleModel.objects.filter(turn=turn, mpg__gt=0.98 * leader['mpg__max'])\
            .filter(Q(drivetrain__name=val[0]) | Q(drivetrain__name=val[1]))
            ulist = [x.producer.username.__str__() for x in leads]
            ulist = ",".join(ulist)

            if val[0] == "gas hev":
                name = "hev"
            else:
                name = "phev"
            setattr(l, name, ulist)

        # calculate the hev and phev values


        return l

    @classmethod
    def popveh(cls):
        """Autobuild vehicles by vp who have not logged in. This ignores vp.balance
        for the moment. Also doesn't do vp rd assignment or price management."""
        TOTAL_VEHS=2 # vp count for producer (max)
        vps = VehicleProducer.objects.filter(first=True)
        vps = [vp for vp in vps if vp.username not in settings.COMPUTER]
        import time
        print vps
        time.sleep(5)

        for vp in VehicleProducer.objects.filter(first=True):
            my_vehs = [] # track vehicles created
            if Turn.cur_turn() >= 3 and vp.username=="v_init":
                continue
            count = Vehicle.objects.filter(producer=vp,turn__gte=3)
            if vp.username not in settings.COMPUTER and Turn.cur_turn() >=3:
                continue # producer is live don't make cars, even if he has made only one car

            veh_count=0
            vpss = VPSalesSummary.objects.filter(vehicle__producer=vp,turn=Turn.last_turn())
            for vps in vpss:
                #analyze what happened with the vehicle
                if vps.percent_return > 0: # made money on this vehicle
                    # see if we can improve it.
                    update={}
                    if vps.unsold == 0:
                        # make some more
                        print "Increasing run on %s" % vps.vehicle
                        update['run'] = min(vps.vehicle.run * 1.25, settings.VEHICLE_MAX_RUN)
                        update['price'] = vps.vehicle.price* (1.0 + random.randint(1,5) * .01)
                    else:
                        print "Decreasing run on %s" % vps.vehicle
                        update['run'] = max(10, vps.vehicle.run - int(vps.unsold/2))

                    print "Copying car for " + vp.username + " : " + vps.vehicle.name +"\n"
                    try:
                        veh = vp.copy_and_update_veh(vps.vehicle,update)
                        veh.save()
                        veh_count += 1
                    except AttributeError:
                        print "Could not build - lack of funds."
                        pass

            num = TOTAL_VEHS-veh_count
            custs = vp.choose_customers(num=num)
            brk = 60
            for con in custs[0:num]:
                r = random.randint(0,100)
                if r < brk:
                    print "\nTrying to imitate a successful car..."
                    goods = VPSalesSummary.objects.filter(turn=Turn.last_turn(),unsold__lte=10)
                    goods = [vps for vps in goods if vps.profit > 0]
                    if len(goods) > 0:
                        if (len(goods) + random.randint(0,2)) >= 3:
                            i = random.randint(0,len(goods)-1)
                            veh = goods[i].vehicle
                            print "Perturbing vehicle: %s" % veh
                            update = {'producer':vp,'copied':False}
                            update['style']=max(0,veh.style + random.randint(-1,1))
                            update['performance']=max(0,veh.performance + random.randint(-1,1))
                            try:
                                veh = vp.copy_and_update_veh(veh,update)
                            except ValueError:
                                r=brk
                            else:
                                try:
                                    veh.price = veh.production_cost * random.randint(101,104)/100.0
                                    veh.name += " cpy"
                                    veh.save()
                                except AttributeError:
                                    pass
                                print "Perturbed vehicle: %s\n" % veh
                        else:
                            r=brk # in this case goods list was short. don't want
                                    # a short list copied - kills diversity
                    else:
                        print "Nothing worth imitating...\n"
                        r = brk # make a random car

                if r >= brk:
                    print "\nMaking random new car for " + vp.username
                    try:
                        veh = vp.car_for_con(con)
                        veh.name="%s %s %s" % (con.username,veh.drivetrain.name,random.randint(1,100))
                        veh.save()
                        print "Made %s\n" % veh
                    except RuntimeError:
                        print "Not enough money to produce a vehicle for " + vp.username + "."
        return True


    def make_car_for_con(self,con):
        """Make a car for Consumer <con> automagically."""
        if self.balance <= 2.0:
            raise RuntimeError("Insufficient funds to build.")
        p_price = con.projected_veh_price()
        print "CON: %s p_price: %s" % ( con.username, p_price)
        vehs = []

        ratio = (con.style_weight+0.0)/(con.performance_weight+0.0)
        dict = settings.VEH_ATTR
        mpg_ratio = (dict['style']['coef'] / ( dict['style']['coef'] + dict['performance']['coef']))
        run = max( min(int(con.fleet_target/4.0),300) , 150) # put a 150 floor on run
        coef = self.__vsf__(run,self.scaling_mod)
        margin = -0.1 * run + 35.0
        style_cost = coef * self.style_cost()
        perf_cost = coef * self.performance_cost()
        for dt in Drivetrain.objects.all():
            if Turn.cur_turn() <= 3:
                # no bev,h2 or phev in first three turns.
                if dt.fuel =="h2" or dt.bev==True or dt.phev>0 or (dt.hev==True and dt.fuel=="diesel"):
                    continue
            input = {'run':run,'margin':margin,'style':0,'performance':0,'drivetrain':dt}
            vict = self.builder(**input)
            veh = Vehicle.prep(**vict)
            veh = Vehicle(**veh)
            if veh.production_cost > 1.01 * p_price and dt.name != "gas":
                print "Skipping %s for %s. Too expensive at  %s." % (dt.name,con.username, veh.production_cost)
                continue
            # now mod the vehicle to maximize s,p

            pval = int((p_price - veh.price)/(ratio*style_cost + perf_cost))
            sval = int(ratio * pval)
            check = sval * style_cost + pval * perf_cost
            diff = p_price - veh.price - check
            print "diff  = %s" % diff

            # working on this stuff.
            input['style'] = max(0,min(sval,settings.VEH_ATTR['style']['max'])) # min makes sure COMPUTER
                                                                                # can't make a better car than players.
            input['performance'] = max(0,min(pval,settings.VEH_ATTR['performance']['max']))

            if input['style']==0 and input['performance']==0:
                # don't make only 0,0 if everyone is broke, or appears to be.
                for val in ['style','performance']:
                    top=random.randint(1,4)
                    input[val]=random.randint(0,top)
            vict = self.builder(**input)
            veh = Vehicle.prep(**vict)
            veh = Vehicle(**veh)
            veh.score=con.quick_score_vehicle(veh=veh)
            #print "%s\nDiff = %s Production Cost: %s Price: %s\n" % (veh,diff,veh.production_cost,veh.price)
            # Does the car meet a minimum mpg standard
            mpg_target = Fuel.get_cafe() * 0.5
            if veh.mpg < mpg_target:
                print "veh.mpg %s < mpg_target %s" % (veh.mpg, mpg_target)
                # take away style and performance to meet the standard for
                # the consumer.

                # REVIEW THIS 7/8!!
                diff = mpg_target - veh.mpg
                print "Dropping %s mpg to make target." % diff
                amt = diff / ( dict['style']['coef'] + dict['performance']['coef'])

                input['style'] -= round(amt,0)
                input['performance'] -= round(amt,0)
                for key  in ['style','performance']:
                    if input[key] < 0: input[key]=0
                vict = self.builder(**input)
                veh = Vehicle.prep(**vict)
                veh = Vehicle(**veh)

            # check to see if the veh has used up all the p_price
            # if not readjust the style: performance ratio
            diff = p_price - veh.price
            if diff > 2*max(style_cost,perf_cost) and veh.performance > 0:
                #assume that style will always cost less than performance
                style_add = min(int((diff+0.0)/style_cost),veh.performance * dict['performance']['coef'])
                # don't add more style than there is performance to absorb it.
                style_mpg = style_add * dict['style']['coef']

                perf_subtract = 1.0 * style_mpg / dict['performance']['coef']
                input['style'] += int(style_add)
                input['performance'] -= int(perf_subtract)
                vict = self.builder(**input)
                veh = Vehicle.prep(**vict)
                veh = Vehicle(**veh)

                if veh.price * 1.05 > p_price:
                    # subtract style points off to get under p_price
                    over = veh.price - p_price
                    pts = round(1.0*over/style_cost,0)
                    input['style'] -= pts
                    input['style'] = max(0,input['style'])
                    vict = self.builder(**input)
                    veh = Vehicle.prep(**vict)
                    veh = Vehicle(**veh)

#            if (veh.price / p_price) < 0.98:
#                diff = (p_price - veh.price)/2
#                pts = round(diff/self.style_cost(),0)
#                mpg_offset = pts * dict['style']['coef']
#                perf_offset = round(mpg_offset / dict['performance']['coef'],0)
#
#                input['style'] += pts
#                input['performance'] -= perf_offset
#                input['performance'] = max(0,input['performance'])
#                vict = self.builder(**input)
#                veh = Vehicle.prep(**vict)
#                veh = Vehicle(**veh)

            veh.score = con.quick_score_vehicle(veh=veh)
            print "OK - %s: %s @ %s / s=%s / $k/s = %s " % (con.username, \
                                                            veh,veh.price,\
                                                            veh.score,\
                                                            ((veh.price+veh.op_cost)/(1000*veh.score)))
            vehs.append(veh)
        try:
            best = sorted(vehs,key=lambda x: x.score,reverse=True)[0]
            out =[[best,best.score]]
        except IndexError:
            raise RuntimeError("No vehicle built.")
        return out


    def old_make_car_for_con(self,con,input=None):
        """Make  a car for consumer con automagically."""
        if self.balance <= 1.0:
            raise RuntimeError("Insufficient funds to build.")
        if input==None:
            rs = random.randint(2,12)
            rp = random.randint(2,12)
            input = {'style':rs,'performance':rp,'margin':5}
        output = []
        p_price = con.projected_veh_price()
        print "Projected price for %s is %s" % (con.username, p_price)
        for dt in Drivetrain.objects.all():
            input['drivetrain']=dt.name
            input['run']=250
            lux = input['style'] + input['performance']
            if lux > 25:
                # cut down the run for lux vehicles.
                input['run'] -= min((lux-25)*5,150)


            dict = self.builder(**input)
            veh=Vehicle.prep(**dict)
            veh=Vehicle(**veh)

            if veh.production_cost <= p_price * 1.1 and veh.mpg > con.aggregate_mpg() * settings.MPG_GATE:
                cost = veh.production_cost * veh.run / 10.0 ** 6
                if cost <= self.balance:
                    output.append((veh,(1000.0*con.quick_score_vehicle(veh=veh)) / (veh.price+veh.op_cost)))
                else:
                    print "Cannot build this car - lacking funds. \n"
                    print vars(veh)




        if len(output) < 2 and input['style'] > 0:
            # cars are too expensive lower attrs

            for key in ['style','performance','margin']:
                input[key] = max(int(input[key] / 2.0) , 0)

            output = self.make_car_for_con(con,input=input)

        if len(output) > 9:
            for key in ['style','performance','margin']:
                input[key] += random.randint(0,4)
            output = self.make_car_for_con(con,input=input)

        best = None
        if len(output)==0:
            # if nohting is developed send this default
            rs = random.randint(2,8)
            rp = random.randint(2,8)
            input = {'run':250,'style':rs,'performance':rp,'margin':5,'drivetrain':'gas'}
            veh = self.builder(**input)
            veh = Vehicle.prep(**veh)
            best=[Vehicle(**veh),1]
        else:
            # pick  a best one to return.
            for val in output:
                if best==None:
                    best = val
                else:
                    if val[1] > best[1]:
                        best = val
            # generate some new vehs based on best
            vehs=[best[0]]
            scores=[best[1]]
            for i in range(1,6):
                #perturb best vehicle
                nst = random.randint(-5,5)
                npr = random.randint(-5,5)
                dict = {'run':vehs[0].run,'margin':vehs[0].margin,'style':vehs[0].style+nst,
                        'performance':vehs[0].performance+npr,'drivetrain':vehs[0].drivetrain.name}
                for d in ['style','performance']:
                    dict[d] = max(dict[d],0) # no negative style /perf.
                new_veh = self.builder(**dict)
                new_veh = Vehicle.prep(**new_veh)
                new_veh = Vehicle(**new_veh)
                if new_veh.price > con.projected_veh_price() * 0.6 and  \
                   new_veh.price < con.projected_veh_price() * 1.1 and new_veh.mpg > con.aggregate_mpg() * settings.MPG_GATE:
                    scores.append(1000.0*con.quick_score_vehicle(veh=new_veh)/(new_veh.price + new_veh.op_cost));
                    vehs.append(new_veh)


            #choose random from the set
            choice = random.randint(0,len(vehs)-1)
            best=(vehs[choice],scores[choice])
            #choose best
            #b = scores.index(max(scores))
            #best =(vehs[b],scores[b])

        output=[best]
        return output

    def profit_on_last_turn(self):
        """Return vp profit for last turn in M."""
        try:
            vpsd = VPSumData.objects.get(producer=self,turn=Turn.last_turn())
            out = vpsd.profit
        except VPSumData.DoesNotExist:
            out = -1000
        return out

    def car_for_con(self,con):
        """Wrapper to make_car_for_con. Returns unsaved vehicle that con will find attractive."""
        out = self.make_car_for_con(con)[0][0]
        return out

    @classmethod
    def cafe_assessment(cls):
        """Run the CAFE assessments for all VP. Run after the VPSalesSummary for the turn.
        CAFE assessment is only taken on sold vehicles, not distress."""
        std = Fuel.get_cafe()
        turn = Turn.cur_turn()
        for vp in VehicleProducer.objects.filter().exclude(username="v_init"):
            my_cafe = none_to_zero(vp.calc_cafe())
            sold = 0

            for vps in VPSalesSummary.objects.filter(vehicle__producer=vp, turn=Turn.cur_turn()):
                sold += vps.sold
            amount = max(0, (std - my_cafe) * 10 * settings.CAFE_PENALTY * sold)

            amount = round(amount / 10**6,3)
            trn = Transaction(amount=amount,buyer=vp,turn=turn,seller=uget("admin"),
                              account="CAFE Penalty", desc="Goal: %s - Achieved: %s" % (std,my_cafe))

            trn.save()
            trn.process()
            pp =PlayPrompt.new(vp,message="Your CAFE penalty was $%s M. The requirement" \
                " was %s mpg. You achieved %s mpg." % (amount,std, round(my_cafe,2)))
        return True




    def profit_loss_data(self):
        """Prepares plot data for the profit loss record plot of the vp."""
        retval={}
        retval['data']=[]
        retval['axis_labels']=[]
        for vps in VPSumData.objects.filter(producer=self).order_by('turn'):
            retval['data'].append(vps.profit)
            retval['axis_labels'].append(Turn.short_year(vps.turn))

        return retval

    def profit_loss_plot(self):
        """Sends the json for the profit_lost_plot. """

        out = self.profit_loss_data()
        axis_marks = 5 # where to put those labels
        y_min = min(out['data'])
        y_max=max(out['data'])

        y_min = y_min + axis_marks - ( y_min % axis_marks)
        y_max = y_max + axis_marks - ( y_max % axis_marks)
        y_min = y_max = max(abs(y_min),abs(y_max))
        y_min = -y_min
        chart=SimpleLineChart(300,300,y_range=[y_min,y_max])
        chart.add_data(out['data'])
        chart.set_axis_labels(Axis.BOTTOM,out['axis_labels'])
        chart.set_axis_labels(Axis.LEFT,range(y_min,y_max+5,5))

        # Set the line colour to blue
        chart.set_colours(['0000FF'])

        # Set the vertical stripes
        chart.fill_linear_stripes(Chart.CHART, 0, 'CCCCCC', 0.2, 'FFFFFF', 0.2)
        chart.set_title('Profit / Loss per Turn($M)')

        # Set the horizontal dotted lines
        chart.set_grid(0, 25, 5, 5)


        #print out['data']

        return chart.get_url()






    def market_position_data(self):
        """Returns the data set to plot the vp market position for each of the consumers per turn."""
        conn = connection.cursor()
        sql = "SELECT snap_turn, consumer, count FROM consumer_vehicle_counts"
        conn.execute(sql)
        sums = {}
        data = {}
        for row in conn:
            sums[(str(row[1]),int(row[0]))]=float(row[2]) # sums[(con,turn)] = count

        cons = [c.username for c in Consumer.objects.all()]

        # build the data structure for counts and turns
        sql ="select snap_turn, consumer, sum(sum) as count from market_breakdown \
                where vp = %s group by snap_turn, vp, consumer order by snap_turn ;"
        conn.execute(sql,[self.username])
        end = 0 # arbitrarily low
        for row in conn:
            try: # data[(con,turn)]=count
                data[(str(row[1]),int(row[0]))]=float(row[2])
            except KeyError:
                pass # can't happen

            end = max(end,int(row[0]))

        # now I can arrange the data dict into form {turn_i: [ordered consumer counts in percent form or 0],...}


        start = end - int(settings.PLOT_TURNS/2) + 1 # starting turn to show
        start = max(1,start)
        out = []
        retval={}
        retval['axis_labels']=[]

        vals =[]
        while start <= end:
            vals.append(start)
            start += 1

        # following data structure looks like this
        # [[counts],...] - counts go in order of turn range
        for turn in vals:
            tmp =[]
            retval['axis_labels'].append(Turn.turn_to_year(turn))
            for con in cons:
                try:
                    den = sums[(con,turn)]
                    num = 100 * data[(con,turn)]
                except KeyError:
                    # the con doesn't exist -> entry should be 0
                    val = 0
                else:
                    try:
                        val = round(num/den,0)
                    except ZeroDivisionError:
                        val = 0


                tmp.append(val)
            out.append(tmp)





        retval['data']=out
        retval['legend']=cons
        return retval

    def plot_market_position(self):
        """Plot the market position for the vp. Will be used for a multi-line graph showing percentage
            market share into a consumer group over time."""
        data = self.market_position_data()
        data['title'] = "My Market Share of Consumer Groups"
        data['colors']=settings.CONSUMER_COLORS
        data['size'] = "370x300"
        data['type']="bvg"
        data['bar_width']=12
        return json.dumps(data)


    @classmethod
    def drivetrain_breakdown_data(cls):
        """Assemble data for drivetrain by year breakdown chart."""
        con = connection.cursor()
        sql = "select drivetrain from drivetrain_breakdown group by drivetrain;"
        con.execute(sql)
        data={}
        dts = []
        for row in con:
            dts.append(str(row[0]))
        # build the data dir

        sql = "SELECT snap_turn, sum(sum) FROM drivetrain_breakdown WHERE drivetrain=%s GROUP BY snap_turn;"
        for dt in dts:
            con.execute(sql,[dt])
            for row in con:
                try:
                    data[int(row[0])].append(int(row[1]))
                except KeyError:
                    data[int(row[0])] = [int(row[1])]

        # now data is a dict of form {turn:[vals,...],...}
        end = max(data.keys()) + 1
        start = end - settings.PLOT_TURNS + 1
        start = max(1,start)
        retval={}
        retval['base_data']=[]
        retval['axis_labels']=[]
        retval['legend']=dts
        for idx in range(start,end):
            retval['base_data'].append(data[idx]) # data[idx] is an array
            retval['axis_labels'].append(Turn.short_year(idx))

        retval['data']=[]
        for arr in retval['base_data']:
            retval['data'].append([round((100.0*x/(sum(arr)+0.0)),0) for x in arr])

        del(retval['base_data'])
        return retval

    @classmethod
    def plot_drivetrain_data(cls):
        """Sets up the plot for drivetrain data."""
        data = cls.drivetrain_breakdown_data()
        data['title']="Drivetrains by Year (%)"
        data['type']="bvs"
        data['size']="550x240"
        data['bar_width']=25
        data['bar_spacing']=5

        return json.dumps(data)

    @classmethod
    def market_population_count(cls):
        """Returns a dict of the total market counts for all turn. key is turn, val is vehicles on the road."""

        con = connection.cursor()
        sql = "SELECT snap_turn, sum(sum) from market_breakdown group by snap_turn;"
        con.execute(sql)
        data = {}

        for row in con:
            data[int(row[0])] =int(row[1])

        con.close()
        return data

    @classmethod
    def market_data(cls):
        """Builds data structure for plotting the vp market breakdown by vehicle producer - i.e.
        how much of the market tdoes the vp own."""
        data = {}
        retval = {}
        retval['legend'] = []
        for vp in VehicleProducer.objects.all().exclude(username="v_init"):
            retval['legend'].append(vp.username)
            # keys are turns, vals are array
            out = vp.market_percent()
            for key in out.keys():
                try:
                    data[key].append(out[key])
                except KeyError:
                    data[key]=[out[key]]

        # next I need to get these in an ordered list by turns
        # i.e. [[turn 1 data],[turn 2 data],..]
        retval['data']=[]
        # make it so only 8 turns of data are returned

        try:
            end = max(data.keys()) + 1
        except ValueError:
            end = 1
        start = end - settings.PLOT_TURNS + 1
        start = max(1,start)
        retval['axis_labels']=[]
        for idx in range(start,end):
            try:
                retval['data'].append(data[idx])
                retval['axis_labels'].append(Turn.short_year(idx))
            except KeyError:
                # if idx == 1 there is a KeyError. An init problem.
                logging.debug("KeyError caught idx shold be 1. idx is %s ." % idx)
                pass

        return retval

    @classmethod
    def plot_market_data(cls):
        out = cls.market_data()
        out['type']="lc"
        out['size']='400x400'
        out['title']='VP Market Record'
        out['lines']=[]
        for val in out['legend']:
            out['lines'].append([6,4,4])

        return json.dumps(out)

    def market_percent(self):
        """Percent of the market owned by vp caller."""
        con = connection.cursor()
        sql = "SELECT snap_turn, sum(sum) from market_breakdown where vp=%s group by snap_turn;" ;
        con.execute(sql,[self.username])
        data={}
        counts = VehicleProducer.market_population_count()

        vals=con.fetchall()
        if len(vals)==0:
            data[2]=0
        else:
            for row in vals:
                data[int(row[0])] =int(row[1])

        con.close()
        turns = set(counts.keys()) & set(data.keys()) # set intersection gives overlapping turns.

        out = {}
        for turn in turns:
            out[turn] = int(100*(float(data[turn])/counts[turn]))
        return out

    def market_breakdown(self,turn_gte=None):
        """Report on the market breakdown by consumer/turn. Returns dict of form [(turn,consumer.username)]=quantity.
        This is an accumulated value. If a turn arg is sent then only vals from turn n are returned."""
        con = connection.cursor()
        array = [self.id]
        sql = "SELECT snap_turn, consumer,sum FROM market_breakdown a WHERE a.producer_id = %s "
        if turn_gte !=None:
            sql += " and a.snap_turn >= %s"
            array.append(turn_gte)
        con.execute(sql,array)
        data={}

        for row in con:
            data[(int(row[0]),str(row[1]))]=int(row[2])

        con.close()
        # to get at this data use something like this
        # list = [key for key in data.keys() if key[0]==2] --> gives you all keys where turn=2
        return data

    def customers(self,turn_gte=Turn.last_turn()):
        """Return veiled ,sorted, list of customers  for the whole game.
        in order from best to worst. Int argument is number of  consumers to return.
        turn_gte is turn greater or equal to. defaults to last_turn"""

        out =[]
        dict = {}
        try:
            for key,val in self.market_breakdown(turn_gte=turn_gte).iteritems():
                try:
                    dict[key[1]] += val
                except KeyError:
                    dict[key[1]] = val

            for key,val in dict.iteritems():
                out.append([cget(key),val])

            cons = [con[0] for con in out]
            for con in Consumer.objects.all():
                # bring in other consumers with 0's
                if con not in cons:
                    out.append([con,0])

        except DatabaseError:
            # init case
            cons = Consumer.objects.all()
            for con in cons:
                out.append([con,0])
        ret =[]
        for o in out:
           ret.append([o[0].veil(),o[1]])
        return sorted(ret,key=lambda x: x[1],reverse=True)


    def choose_customers(self,num=2):
        """Randomly choose customers based on density of purchases. Arg <num> is the number
        to choose. Choosing with replacement."""
        out =[]
        cons = Consumer.objects.all()
#        fts = [con.fleet_target for con in cons]
        picked = []
        for cntr in range(num):

            i = random.randint(0,(len(cons)-1))
            if i in picked:
                # pick again but allow it to choose same consumer
                # reduce likelihood of double build, but not impossible
                i = random.randint(0,(len(cons)-1))
#            pick = random.randint(1,sum(fts))
#            i = 0
#            val = 0
#            while val <= pick:
#                val += fts[i]
#                i += 1
#            i -= 1
            out.append(cons[i])
            print "Chose %s" % cons[i].username

        return out


#    def choose_customers(self,num=2,method=None):
#        """Choose customesr to auto build for . num is number to select.
#        methods is an arrray of callbacks that must be of len num. customer
#        i will be selected by method. I f no methods are sent
#        then default will be used. """
#
#        if num==0:
#            return []
#
#        all = self.customers()
#        if method==None:
#
#            def default(arr,num):
#                out =[]
#                # are there any above 0?
#                solds = [x for x in arr if x[1] > 0]
#                if len(solds)==0:
#                    # choose 2 randomly
#                    for i in range(0,num):
#                        r = random.randint(0,len(arr)-1)
#                        out.append(arr[r])
#                else:
#                    # take top num - this will be bad if
#                    dens = [x[1] for x in arr if x[1] > 0]
#                    for i in range(0,len(dens)):
#                        rnd = random.randint(1,sum(dens))
#                        index=0
#                        while rnd >= sum(dens[0:index+1]):
#                            index += 1
#                        out.append(solds[index])
#
#
#                    if len(out) < num:
#                        # randomly select from 0's
#                        others = [x for x in arr if x[1] == 0]
#                        for i in range(0,num - len(out)):
#                            r =random.randint(0,len(others)-1)
#                            out.append(others[r])
#
#                return out
#
#            method=default
#
#        out = method(all,2)
#        return out
#






    def plot_breakdown_data(self):
        """Put breakdown data into plottable format."""
        data = self.market_breakdown()
        start = min([key[0] for key in data.keys()]) # first turn
        end = max([key[0] for key in data.keys()]) # last turn
        cons = [con.username for con in Consumer.objects.all()]
        out = []
        axis=[]
        if end - start > settings.PLOT_TURNS:
            start = end - settings.PLOT_TURNS # control plot size to last 8 turns
        while start <= end:
            tmp = []
            axis.append(Turn.short_year(start))
            for con in cons:
                try:
                    tmp.append(data[(start,con)])
                except KeyError: # a null entry for the turn:consumer pair

                    tmp.append(0)
            out.append(tmp)
            start += 1
        retval = {}
        retval['data']=out
        retval['legend']=cons
        retval['axis_labels']=axis
        retval['colors']=settings.CONSUMER_COLORS
        return retval

    def breakdown_plot_string(self):
        """Returns the string to make the chart in jgcharts for consumer/turn breakdown by vp. Returns json."""
        out = { }

        out=self.plot_breakdown_data()
        out['type']="bvs"
        out['size']='300x300'
        out['title']="My Vehicle Count History"



        return(json.dumps(out))

    def vp_consumer_record(self):
        """Create data for a turn by turn stacked bar chart for total vehicle purchases
        per turn by which consumers."""

        end = Turn.max_turn()-1
        start = end - settings.PLOT_TURNS
        start = max(2,start)
        dict = {}
        data = []
        years =[]
        dict['legend']=[]
        while start <= end:
            tmp = []
            for con in Consumer.objects.all():
                out = VehicleTransaction.objects.filter(seller=self,turn=start,buyer=con).aggregate(Sum('quantity'))['quantity__sum']
                out = none_to_zero(out)
                tmp.append(out)
            data.append(tmp)
            years.append(Turn.short_year(start))
            start += 1

        dict['data']=data
        dict['axis_labels']=years
        return dict

    def plot_vp_consumer_record(self):
        """Plot code for vp_consumer_record."""
        dict = self.vp_consumer_record()
        dict['colors']=settings.CONSUMER_COLORS
        dict['size']="300x300"
        dict['type']="bvs"
        dict['legend']=[con.username for con in Consumer.objects.all()]

        return json.dumps(dict)

    def turn_report(self):
        """Return a text report about how the player did on the last turn."""

        # changing get to filter
        data = VPSumData.objects.filter(producer=self, turn=Turn.last_turn())[0];

        profit = round(data.profit, 3)
        verb = "lost"
        if profit > 0:
            verb = "made"
        else:
            profit = -profit # make it possitive to agree with verb

        out = """In %s you sold %s of the %s vehicles you produced. You %s
        $%s M and earned %s RD points.
        """ % (Turn.turn_to_year(data.turn), data.sold, data.produced, verb,\
               profit, (data.free_rd_points + data.assigned_rd_points));
        return out

    #        str = "In %d you sold %d of the %d vehicles you produced.",\
    #              " You %s $ %d M and earned %d rd points. " % (4,
    #              1, 2, "dfddf", 2.333, 0 )

    def all_gauges(self):
        """Return 6 gauges (gas,diesel,h2,elec,hev,roadload) for display in
        r_and_d.html page. As an array. This is js code.
        """
        out=[]
        for val in ['gas','diesel','h2','bev','hev','road_load']:
            out.append(self.rd_gauge(val))
        return out

    def rd_gauge(self,val):
        """Make an rd_gauge for 'val' on r_and_d.html. Prints out the js.
        """

        if val in  ['h2','bev','hev']:
            label= val.upper()
        elif val in ['gas','diesel']:
            label=val.capitalize()
        else:
            label="Road Load"


        pts = RandD.sum_area(val,**{'producer':self})
        ldg = VehicleProducer.rd_area_stats(val)

        t = Template(""" MY.opts['label']="{{label}}"
            MY.opts['value']={{ pts }}
            MY.opts['max']={{max}}
            MY.opts['greenFrom']={{greenFrom}}
            MY.opts['greenTo']={{max}}
            MY.opts['redTo']={{ redTo }}
            MY.opts['redFrom']=0
            MY.gs['rd_{{val}}'] = new Gauge(document.getElementById("rd_{{val}}"),MY.opts) """)

        max_val = max(ldg.max*1.2,10)

        c=Context({'val':val, 'pts':pts, 'max':max_val,'greenFrom':max_val-2,
                   'redTo':ldg.min+2,'label':label})
        return t.render(c)

    def calc_return(self, veh):
        """Calculate the gross revenue for a vehicle produced by 'self' (VP). This value is
            the sum of sales minus the sum of the initial production cost. Return value is in $ (not millions)."""

        init_cost = VehicleTransaction.objects.get(vehicle=veh, buyer=self).amount + 0.0

        sales = VehicleTransaction.objects.filter(vehicle=veh).exclude(buyer=self).aggregate(Sum('amount'))[
                'amount__sum']
        if sales == None:
            sales = 0.0
        return (sales - init_cost) * 10 ** 6

    @classmethod
    def score_turn(self):
        """Score the turn for the vehicle producer. Score is a function of market share, margin, revenues and capital. \
            Something like that."""
        if VehicleTransaction.active_turn():
            for vp in vpall():
                sc = VPScore(user=vp,turn=Turn.cur_turn())
                sc.balance = vp.balance
                try:
                    prior = VPScore.objects.get(user=vp,turn=Turn.last_turn())
                    sc.revenue = vp.balance - prior.balance
                    num_vehs = VehicleTransaction.objects.filter(buyer=vp,turn=Turn.last_turn()).aggregate(Sum('quantity'))['quantity__sum']
                    num_vehs = none_to_zero(num_vehs)
                    sc.revenue_per_vehicle = (10**6*sc.revenue+0.0)/(num_vehs + 0.0)
                    prod_cost = VehicleTransaction.objects.filter(buyer=vp,turn=Turn.last_turn()).aggregate(Sum('amount'))['amount__sum']
                    sc.profit_per_vehicle = (10**6*prod_cost + 0.0)/(num_vehs - 0.0) - sc.revenue_per_vehicle
                    sc.cap_appreciation = (vp.balance+0.0)/(prior.balance + 0.0)
                    my_vehs = Fleet.objects.count_vehicles(**{'vehicle__producer':vp})
                    all_vehs = Fleet.objects.count_vehicles()
                    sc.fleet_share =100 * (my_vehs+0.0)/(all_vehs+0.0)

                except Exception, e:
                    sc.revenue = 0
                    sc.cap_appreciation = 1
                    sc.fleet_share=0

                sc.save()

        # Q1. How much money did vp have at the beginning of the turn?
        # Q2. How much money does vp have at end of the turn?
        # Calculate the % change in this value and relative rank it.

        # Q3. What was the average profit/loss per car (including distress sales)

        # Q4. Did the player improve over the last turn? If yes, he gets a bonus that
        # increases for each turn of increasing profit measures.


#
#    @property
#    def capacity(self):
#        """The total number of vehicles that a producer can make per turn."""
#        return Consumer.market_size() * self.base_capacity


    @property
    def remaining_capacity(self):
        """How many more vehicles the VP can designate for his runs, i.e. capacity - next turns vehicle runs."""
        scheduled = Fleet.objects.count_fuel_types(owner=self, turn=Turn.cur_turn())
        return self.capacity - scheduled

    def dummy(self, **kwargs):
        """Quickly build a vehicle for testing, using given kwargs. If no kwargs a sent
        a default vehicle is created with style=10,perf=10,drivetrain=gas,margin=5. The
        **post arg can be used to force a value into the vehicle build after the builder
        method has been run."""

        car_name = "car %s" % random.randrange(0, 1000000)
        dict = {"caller": 'dummy', "style": 10, "drivetrain": "gas", "performance": 10, "margin": 5, "name": car_name,
                "run": 200}

        dict.update(kwargs)

        out = self.builder(**dict)
        out = Vehicle.prep(**out)
        veh = Vehicle(**out)
        return veh


    def rd_profile(self):
        """Prepare a data set for google charting a bar chart showing the r and d history of the caller vp."""

        dict = {}
        dict['data'] = []
        dict['labels'] = []
        rd = RandD.objects.filter(producer=self, turn=Turn.cur_turn() - 1)
        # use rd_areas in RandD to do this!
        for a in RandD.areas:
            tmp = []
            tmp.append(rd.values()[0][a])
            dict['data'].append(tmp)
            dict['labels'].append(a)

        return dict


    @classmethod
    def market_capacity(cls):
        """The total production capacity of all vehicle producers combined."""
        sum = 0
        for vp in cls.objects.all():
            sum = vp.capacity + sum
        return sum


    def __unicode__(self):
        return self.username

    def base_context(self):
        """Overrides base base_context for VP."""
        o = super(VehicleProducer, self).base_context()
        o['next_turn_commitment'] = none_to_zero(Fleet.objects.count_vehicles(owner=self, turn=Turn.cur_turn()))
        return o

    def home_context(self):
        """Add in stuff"""
        o = self.base_context()
        try:
            o['cafe'] = round(self.calc_cafe(),2) # running tally
        except TypeError:
            o['cafe'] = "NA"
        #/o['max_cafe_next_turn'] = self.max_cafe() #
        #ncs = Fuel.objects.filter(turn__gt=Turn.cur_turn(), turn__lt=Turn.cur_turn() + 3)
#        try:
#            o['next_cafes'] = "%s %s mpg - %s %s mpg" % (Turn.turn_to_year(ncs[0].turn), ncs[0].cafe,\
#                                                     Turn.turn_to_year(ncs[1].turn), ncs[1].cafe)
#        except IndexError:
#            o['next_cafes'] = "None"
        o['this_cafe'] = Fuel.get_cafe()
        o['next_cafe'] = Fuel.get_cafe(**{'turn':Turn.next_turn()})
        o['market_size'] = Consumer.expected_veh_purchases()
        o['onsale'] = Vehicle.objects.filter(producer=self, turn=Turn.last_turn())
        o['scheduled'] = Vehicle.objects.filter(producer=self, turn=Turn.cur_turn())
        o['next_turn_year'] = Turn.calc_next_turn_year()
        o['home'] = "vp/vp_home.html"



        # get all the vehicles for this turn
        #onsale= Vehicle.objects.filter(producer=self,turn=o["turn"].turn)
        #custom = {'onsale':onsale}
        #custom.update(o)
        return o

    @classmethod
    def rd_stats(cls):
        """Return the max and min rd expenditures for VPs as obj.max and obj.min.
        """
        data = []
        for vp in cls.objects.all().exclude(username="v_init"):
            data.append(vp.rd_expended())
        # abusing Ledger here  - why not?
        out = Ledger(**{'min':min(data),'max':max(data)})
        return out

    @classmethod
    def rd_area_stats(cls,area):
        """Report the min and max for an rd area <area>. Returns
        a Ledger with min and max attrs. """
        data=[]
        for vp in cls.objects.all().exclude(username="v_init"):
            data.append(RandD.sum_area(area,**{'producer':vp}))
        out = Ledger(**{'min':min(data),'max':max(data)})
        return out



    def rd_expended(self):
        """Returns total number of rd_points expended by VP that are in production.
        """
        return sum(self.randd_areas().values())

    def randd_areas(self):
        """Returns a dict of the summed level for each of the randd areas."""
        rd = {}
        for a in RandD.areas:
            rd[a] = RandD.sum_area(a, **{'producer': self})

        return rd

    def pie_randd_areas(self):
        """Returns a google chart url that is a pie chart of the r and d areas. Zero entries are eliminated.
        """
        data = self.randd_areas()
        for key in data.keys():
            if data[key]==0:
                del(data[key])
            elif key in ['style','performance']:
                del(data[key])
        vals = data.values()
        labels=data.keys()
        gc = GC.Pie(vals)
        gc.label(*labels)
        gc.size(200,140)
        gc.color('green')
        return gc.url
        



    def active_rd(self, val):
        """Returns the active r&d points for the vp. Active means that only processed r&d is counted (i.e.
            turn = Turn.cur_turn()-1 , when counting r&d activity. The argument, val, is the name of the rd area."""
        return  RandD.sum_area(val, **{'producer': self, 'turn': Turn.cur_turn() - 1})


    def process_randd(self):
        """Take rd_points from player acct and increase tech level
            according to the get_level_fxns in plotkin/models.py."""
        # make sure this hasn't been done already for this turn.

        c = VPDrivetrainLevel.objects.filter(producer=self, turn=Turn.cur_turn()).count()
        if c > 0:
            # this has already been run
            raise AssertionError("VehicleProducer.process_randd has been run already for this turn. ")


        # Take RandD levels for the VP and translate them to VPDrivetrain Levels
        rd = self.randd_areas()
        for dt in Drivetrain.objects.all():
            o = get_level_fxn(dt.name)
            v = VPDrivetrainLevel(drivetrain=dt, producer=self, turn=Turn.cur_turn(),
                                  level=o(rd))
            v.save()
            # update the levels for style_cost, style_mpg, performance_cost and performance_mpg.


    @classmethod
    def global_mpg(cls):
        """Calculate the global average fuel economy for all vehicles sold on this turn."""
        vp = vpall()[0] # calling an instance method so need an instance.

        return vp.calc_cafe(**{'turn': Turn.cur_turn()}) #

    @property
    def max_cafe(self):
        """Calculates the Max CAFE possible for the vp given that
        he sells all of his vehicles."""
        turn=Turn.cur_turn()
        vehs = Vehicle.objects.filter(turn=turn,producer=self)
        out = "NA"
        if not vehs==None:
            num = sum([x.run for x in vehs])
            den = sum([((x.run+0.0)/x.mpg) for x in vehs])
            try:
                out = num/den
                out = round(out,2)
            except ZeroDivisionError:
                pass
        return out

    def calc_cafe(self, *args, **kwargs):
        """Calculate the CAFE for the VP using the harmonic mean. Returns None if no vehicles sold by the vp that turn."""
        if len(kwargs) == 0:
            kwargs = {'turn': Turn.cur_turn(), 'seller': self}
        vals = VehicleTransaction.objects.filter(**kwargs).exclude(account="initial vehicle build")

        num, den = 0.0, 0.0
        for vt in vals:
            num = num + vt.quantity
            den = den + (vt.quantity + 0.0) / (vt.vehicle.mpg + 0.0)

        try:
            out = (num + 0.0) / (den + 0.0)
        except ZeroDivisionError:
            out = None
        return out

    def style_cost(self):
        """Returns current cost for a style level (10**0 units)."""
        return self.get_level_cost('style',(settings.VEH_ATTR['style']['base'] + 1))

    def performance_cost(self):
        """Returns current cost for a style level (10**0 units)."""
        return self.get_level_cost('performance',(settings.VEH_ATTR['performance']['base'] + 1))

    def get_level_cost(self, attr, level):
        """Takes an input attr of 'style' or 'performance' and int(level) and returns the cost for that style or perf. level."""
        core = int(level) - int(settings.VEH_ATTR[attr]['base'])
        if attr == "style":
            cost = self.base_style_cost - 2 * self.active_rd('style')
            return core * cost
        elif attr == "performance": # alllow a different function for performance
            cost = self.base_performance_cost - 2 * self.active_rd('performance')
            return core * cost
        else:
            raise Exception("No attr attr: %s" % attr)


    def get_level_mpg(self, attr, level):
        """Takes an input attr of 'style' or 'performance' and return the level cost"""
        core = int(level) - int(settings.VEH_ATTR[attr]['base'])
        if attr == "style":
            coef = settings.VEH_ATTR[attr]['coef']
            return -core * coef
        elif attr == "performance": # alllow a different function for performance
            coef = settings.VEH_ATTR[attr]['coef']
            return -core * coef
        else:
            raise Exception("No attr attr: %s" % attr)


    def __vsf__(self,num,scaling_mod): # this curve is a linear descent followed by a flat.
        out = settings.MIN_MULT # best multiplier
        quantity = num + scaling_mod
        if num <= settings.VEHICLE_MAX_PRODUCTION:
            slope = (settings.MIN_MULT - settings.MAX_MULT) / (settings.VEHICLE_MAX_PRODUCTION + 0.0)  # slope is negative
            quantity = num + scaling_mod
            out = slope * quantity + settings.MAX_MULT
        return out

    def get_total_cost(self, *args, **kwargs):
        """Returns the total cost of the vehicle after scaling."""
        run = args[0]
        coef = self.__vsf__(run, self.scaling_mod)
        return coef * (kwargs['style_cost'] + kwargs['performance_cost'] + kwargs['cost'])



    def get_total_mpg(self, **kwargs):
        """Returns the total cost of the vehicle after scaling."""
        return kwargs['style_mpg'] + kwargs['performance_mpg'] + kwargs['base_mpg']

    def copy_and_update_veh(self,veh,update={}):
        """Copies and updates <veh> for next turn. Send a dict <update> to update vehicle vals."""
        vals = serializers.serialize('python',[veh])
        vals[0]['fields'].update(update)
        return self.copy_and_update_vehs(vals)


    def copy_and_update_vehs(self,vals=None):
        """Copy and update teh vehicle slate for vp ."""

        vp = self
        if vals == None:
            vals = serializers.serialize('python',Vehicle.objects.filter(producer=vp,turn=Turn.last_turn()))
        out = "OK"


        for veh in vals:
            if vp.balance < 0:
                raise ValueError("Producer does not have funds: %s." % self.username)
            if veh['fields']['copied']==True:
                raise AttributeError("Vehicle has already been copied.")
            Vehicle.objects.filter(id=veh['pk']).update(copied=True)
            data = veh['fields']
            data['turn']=Turn.cur_turn()
            nuveh = vp.builder(**data)
            nuveh = Vehicle.prep(**nuveh)
            nuveh = Vehicle(**nuveh)
            nuveh.save()
            if vp.balance < 0: # Don't let a vehicle be built if vp doesn't have enough money
                vt = VehicleTransaction.objects.get(vehicle=nuveh)
                vt.reverse(force=True)
                nuveh = None
        return nuveh


    def builder(self, *args, **kwargs):
        """Creates a vehicle dict based on vp,drivetrain,perf,style,run,name and margin. Returns \
        Vehicle ref, which must be saved on the caller's side."""

#        if int(kwargs['run']) > settings.VEHICLE_MAX_RUN:
#            try: # caller check is used to allow init_fleet to use larger runs than VEHICLE_MAX_PRODUCTION
#                caller = kwargs['caller']
#                if caller != "dummy":
#                    raise ValueError("Run size is too large. Was %s. Max allowed is %s" % (
#                    kwargs['run'], settings.VEHICLE_MAX_RUN))
#            except KeyError:
#                raise ValueError(
#                        "Run size is too large. Was %s. Max allowed is %s" % (kwargs['run'], settings.VEHICLE_MAX_RUN))

        try:
            kwargs['drivetrain'] = int(kwargs['drivetrain'])
        except (TypeError,ValueError):
            kwargs['drivetrain'] = Drivetrain.objects.get(name=kwargs['drivetrain'])

        try:
            vm = VehicleModel.objects.get(drivetrain=kwargs['drivetrain'],
                                          producer=self, turn=Turn.cur_turn())
        except VehicleModel.DoesNotExist, e:
            # this can happen in init_fleet without a ValueError. I'm not sure exactly how to handle this
            # in a more elegant manner

            vm = VehicleModel.objects.get(drivetrain=kwargs['drivetrain'],
                                          producer=self)
        dict = {'drivetrain_name': vm.drivetrain.name, 'cost': vm.cost, 'base_mpg': vm.mpg}
        dict['run'] = kwargs['run']
        u = self
        for attr in ['style', 'performance']:
            dict[attr] = kwargs[attr]
            dict["%s_cost" % attr] = u.get_level_cost(attr, kwargs[attr])
            dict["%s_mpg" % attr] = u.get_level_mpg(attr, kwargs[attr])

        dict['production_cost'] = int(u.get_total_cost(int(kwargs['run']), **dict))
        #dict['mpg'] = max(u.get_total_mpg(**dict), 0)
        dict['mpg'] = u.get_total_mpg(**dict)

        if settings.FEEBATES:
            try:
                dict['feebate']= int(settings.FEEBATE_COST * -(Fuel.get_cafe_feebate() - (1.0/dict['mpg']))/0.01)
            except ZeroDivisionError:
                dict['feebate']=10000
            dict['production_cost'] += dict['feebate']
        if dict['mpg'] < settings.GAS_GUZZLER:
            dict['mpg_msg'] = " * GAS GUZZLER *"
        else:
            dict['mpg_msg'] = ""
        try:
            dict['price'] = (float(kwargs['margin']) / 100 + 1 ) * dict['production_cost']
        except ValueError:
            # margin is empty - is this what we want?

            logging.debug("kwargs['margin'] is empty. Setting to 0. hm?.")
            dict['price'] = dict['production_cost']
        try:
            dict['turn'] = kwargs['turn']
        except KeyError:
            dict['turn'] = Turn.cur_turn()
        dict['producer'] = self
        dict['drivetrain'] = vm.drivetrain
        try:
            dict['name'] = kwargs['name']
        except KeyError:
            dict['name'] = "NA"

        return dict


class VPDrivetrainLevel(models.Model):
    drivetrain = models.ForeignKey(Drivetrain)
    producer = models.ForeignKey(VehicleProducer)
    turn = models.IntegerField()
    level = models.FloatField()


class NewVehicleForm(forms.Form):
    """Form for view new_vehicle - vehicle creation screen."""
    drivetrain = forms.IntegerField()

class Vehicle(models.Model):
    name = models.CharField(max_length=40)
    drivetrain = models.ForeignKey(Drivetrain)
    producer = models.ForeignKey(VehicleProducer, default=-1)
    mpg = models.FloatField()
    production_cost = models.IntegerField()
    price = models.IntegerField()
    turn = models.IntegerField(default=-1000)
    performance = models.IntegerField()
    style = models.IntegerField()
    run = models.IntegerField()
    feebate = models.IntegerField(default=0)
    #parent = models.IntegerField(null=True)
    copied = models.BooleanField(default=False)
    margin = models.FloatField(default=5.0)

    def compare(self,veh):
        """Compares if two vehicles, caller and veh, have the same drivetrrain, performance and style.
        Returns bool. True if the same, False if different."""
        out = False
        if self.style==veh.style and self.performance==veh.performance and self.drivetrain.name==veh.drivetrain.name:
            return True
        return out

    def nonev_mpg(self):
        """Get the HEV mpg for a PHEV to be used in the CS mode mpg calculation."""
        if not self.drivetrain.phev > 0:
            raise ValueError("Called on a non-PHEV")
        v = self.producer.builder(style=self.style,performance=self.performance, run=100, margin=5,
                                  drivetrain="%s hev" % self.drivetrain.fuel)
        return v['mpg']

#    def nonev_mpg(self):
#        """Returns the non-ev mpg (gas,diesel,h2) for a phev. Raises ValueError if called on non-phev. """
#        if not self.drivetrain.phev > 0:
#            raise ValueError("Called on a non-PHEV")
#        out = self.mpg / ( (settings.PHEV_SCALAR - 1) * settings.PHEV[str(self.drivetrain.phev)]  + 1 )
#        return out

    def ev_mpg(self):
        """EV mpg of a PHEV. """
        u = settings.PHEV[str(self.drivetrain.phev)]
        return (self.mpg  - (1.0-u)* self.nonev_mpg())/u

    def elec_vmt(self,vmt):
        """Returns electric vmt based on <vmt> input for PHEV"""
        return settings.PHEV[str(self.drivetrain.phev)] * vmt

    def nonev_vmt(self,vmt):
        """NON-EV vmt for PHEV."""
        return vmt - self.elec_vmt(vmt)

    def ev_gge(self,vmt):
        """GGE for EV portion of PHEV."""
        return self.elec_vmt(vmt) / self.ev_mpg()

    def nonev_gge(self,vmt):
        """GGE for non-EV portion of PHEV."""
        return self.nonev_vmt(vmt)/self.nonev_mpg()

    def sales_percent(self):
        """What percentage of these vehicles sold? Returns (int). Returns 0 if fails. This
        may be confusing??"""
        try:
            built = VehicleTransaction.objects.get(vehicle=self,buyer=self.producer)
        except VehicleTransaction.DoesNotExist:
            return 0
        sold = 0
        for vt in VehicleTransaction.objects.filter(vehicle=self).exclude(buyer=self.producer):
            if vt.buyer.groups.values()[0]['name']=="admin":
                # don't include the distress sale
                continue
            sold += vt.quantity
            if sold > built.quantity:
                print vt
        return int( 100.0 * sold/built.quantity)



    @property
    def op_cost(self):
        """The fuel operational cost for the vehicle. """
        base_vmt = 15000.0
        fuel = self.drivetrain.fuel
        if self.is_phev:
            # add in electricity expense
            price = FuelRecord.last('elec')
            expense = price * self.ev_gge(base_vmt)
            expense += FuelRecord.last(fuel) * self.nonev_gge(base_vmt)
        else:
            gals_bought = base_vmt / self.mpg
            price = FuelRecord.last(fuel)
            expense = gals_bought * price
        return 4 * expense


    @classmethod
    def prep(cls, *args, **kwargs):
        """Integrates the dict into the vehicle model design."""
        o = get_model('app', 'Vehicle')
        dict = {}
        dict['drivetrain'] = kwargs['drivetrain']
        dict['producer'] = kwargs['producer']
        for att in o._meta.fields:
            if kwargs.has_key(att.attname):
                dict[att.attname] = kwargs[att.attname]

        #super(Vehicle,self).__init__(*args,**dict)
        return dict


    def __unicode__(self):
        out = self.name + " " + self.drivetrain.name + " " + self.producer.username
        for val in ['style','performance','mpg']:
            out += " " + val + ": " + str(getattr(self,val))
        return out

    def update(self, *args, **kwargs):
        """Call a save on an existing vehicle without adding it to the database, i.e. Vehicle object edit."""
        super(Vehicle, self).save(self, *args, **kwargs)

    def similarity(self,veh):
        """Compare the vehicle to vehicle <veh> and on mpg, style and performance and produce a score. REturns
         0 if vehicles are identical. Returns positive value for differeent
         vehicles."""

        out = 0
        out += sum([(getattr(self,val) - getattr(veh,val))**2 for val in ['style','performance']])
        out += (self.mpg ** 0.5 - veh.mpg ** 0.5) ** 2

        return round(out ** 0.5,1)

    def save(self):
    #def save(self, *args, **kwargs):
        if self.id == None:
            if self.mpg <= 0:
                raise ValueError("MPG must be positive (is %s)" % self.mpg)
            try:
                super(Vehicle, self).save()
            except IntegrityError:
                try:
                    veh = Vehicle.objects.get(name=self.name)
                except Vehicle.DoesNotExist:
                    id_check(self)
                    super(Vehicle,self).save()
            #This code only happens if the objects is
            #not in the database yet. Otherwise it would
            #have pk
            # ##### Do the vehicle transaction here
            cost = float(float(self.run) * float(self.production_cost)) / 10 ** 6
            # make the VP buy the vehicles and put them in his fleet

            a = Admin.get_admin()
            # TODO : make the buyer an account other than admin
            vt = VehicleTransaction(buyer=self.producer, seller=a,
                                    amount=cost, desc="build - %s" % (self.name),
                                    account="initial vehicle build",
                                    fees=0, vehicle=self,
                                    quantity=self.run,
                                    turn=Turn.cur_turn())

            vt.save()
            #vt.process(0, cost, sold=False)

        else:
            super(Vehicle, self).save()


    @property
    def model(self):
        """Returns the vehicleModel from which vehicle was generated."""
        try:
            out = VehicleModel.objects.get(drivetrain=self.drivetrain, turn=self.turn,\
                                           producer=self.producer)
        except Exception:
            out = 0

        return out

    def __prior_bot__(self, user, **dict):
        """Input: User object, dict of Fleet descriptors. Output - a dict with keys 'prior'
        and 'bot'. The 'prior' value is the number of vehicles the 'user' bought in turns prior
        to the current. The 'bot' value is the number of vehicles of this dict defined set bought
        this turn by the user."""
        out = {}
        base_dict = {'owner': user}
        dict.update(base_dict)
        dict['turn__lt'] = Turn.cur_turn()

        out['prior'] = none_to_zero(Fleet.objects.count_vehicles(**dict))

        dict.__delitem__('turn__lt')
        dict['turn'] = Turn.cur_turn()

        out['bot'] = none_to_zero(Fleet.objects.count_vehicles(**dict))

        return out

    def __ag_query__(self, desc):
        """Run the aggregation avg query for get_max. Returns a dict with two keys: mult and base.
        Mult is the multiplier describing how fast consumer adoption can grow between turns and base
        is the minimum level that consumers will be able to buy of a drivetrain if they have never
        bought before."""

        out = {}

        dts = settings.DRIVETRAIN_CLASSES[desc]
        qs = Q(name=dts[0])

        for dt in dts[1:len(dts)]:
            qs |= Q(name=dt)
        dat = Drivetrain.objects.filter(qs).aggregate(Avg('vehicle__drivetrain__adoption_multiplier'),
                                                      Avg('vehicle__drivetrain__adoption_base'))

        out['mult'] = dat['vehicle__drivetrain__adoption_multiplier__avg']
        out['base'] = dat['vehicle__drivetrain__adoption_base__avg']

        return out


    def __get_quant__(self, user, qry, prior_vehs, bot, desc):
        """Gives the number of vehicles of the type(s) specified by the query qry
        that 'user' is able to buy. This is a helper function for get_max."""

        num = int(user.balance * 10 ** 6 / self.final_cost)

        if qry == False or desc == 'cv':
            return num

        out = self.__ag_query__(desc)
        hev_avg_mult = out['mult']
        hev_avg_base = out['base']
        can_buy = ((prior_vehs + 0.0) * hev_avg_mult) - bot

        hev_avg_base = max(hev_avg_base - bot, 0) # don't allow a negative purchase level

        calc_max = max(can_buy, hev_avg_base) # take the greater of the actual or base seed (base seed
        # is required to break deadlock of 0 vehicles purchasable.
        return min(calc_max, num)

    def __simple_qry__(self, user, **dict):
        """Return a qry for a simple scenario when there is only one fuel type (i.e. no cv). Helper
        to get_max. Returns a dict with keys: qry, prior_vehs and bot."""

        base = deepcopy(dict)
        out = self.__prior_bot__(user, **dict)
        qry = Fleet.objects.filter(**base)

        return {'qry': Fleet.objects.filter(**base), 'prior_vehs': out['prior'], 'bot': out['bot']}

    def cur_buyers(self):
        """Return a list of consumers who have bought this vehicle on this turn."""
        vehs = Fleet.objects.filter(vehicle=self, sold=True, turn=Turn.cur_turn())
        buyers = set()
        for veh in vehs:
           buyers.add(veh.owner.username)
        return list(buyers)

    @classmethod
    def vp_sale_status(cls):
        """Returns the status string for the vp sales throttling as 'status'.
        Returns the ratio key as 'ratio'. This is a helper function to Vehicle.get_max mostly
        but it can be called directly by the cls method."""

        dict = {}
        turn = Turn.objects.get(turn=Turn.cur_turn())

        turn_start = turn.start_time
        mynow = datetime.now()

        delta = mynow - turn_start
        diff = delta.seconds
        diff = diff - settings.NO_BUY_TIME  # buys are blocked for this many seconds
        diff = max(diff, 0) # make sure this in not negative
        if diff == 0:
            dict['status'] = "No Purchasing"

            # players can buy up to 40% of their cars
            # difference between 3.4 * fleet_target/4 and fleet_size
            # is allowed.

            # make this a function of time. Over the course of 6 minutes
            # full capacity is allowed, but it goes gradually
        ratio = min(1.0, ((diff + 0.0) / settings.SAFE_TIME))
        dict['ratio'] = ratio
        if ratio == 1.0:
            dict['status'] = "Open Purchasing"
        elif ratio > 0 and ratio < 1:
            dict['status'] = "Constrained Purchasing %s%s complete" % (int(ratio * 100.0), '%');
        return dict


    def get_max(self, user):
        """Returns the maximum number of vehicles this user can buy. Returns dict with
        val key as the number available and status key as a text string describing the
        throttle state with values 'No Buy','Constrained Purchase' and 'Open Purchase'."""

        # first, has the user met his quota. User cannot exceed his quota.
        # check how many seconds since the start of the turn
        dict = {}
        out = Vehicle.vp_sale_status()
        ratio = out['ratio']
        dict['status'] = out['status']
        try:
            # use limit instead of fleet_size in game_limited
            # because of fleet_size is too far oof from the fleet_target
            # it lets game_limited be too large.
            limit = max((3*user.fleet_target)/4.0, user.fleet_size )
            game_limited = max(0, int((3 + ratio) * user.fleet_target / 4.0 - limit))
        # now see how many of the cars are actually left
            dict['val'] = min(self.num_available, game_limited)
        except AttributeError: # only consumer has a fleet_target
            #print "attribute error in get_max"
            dict['val']=self.num_available
        return dict
        # starting point, the most he can buy



    @property
    def revenue(self):
        """The total revenue associated with the vehicle, i.e. how much has been spent/earned since production."""

        vt = VehicleTransaction.objects.get(vehicle=self, account="initial vehicle build")
        cost = vt.amount
        # I want the above line to fail hard if it does, that shouldn't happen.
        profit = VehicleTransaction.objects.filter(vehicle=self).exclude(account="initial vehicle build").aggregate(
                Sum('amount'))['amount__sum']
        #convert a none to a 0
        profit = none_to_zero(profit)

        return (profit - cost)


    def revenue_test(self):
        """The total revenue minus production cost."""

        vt = VehicleTransaction.objects.get(vehicle=self, account="initial vehicle build")
        orig_cost = vt.amount
        # I want the above line to fail hard if it does, that shouldn't happen.
        rev_and_orig_cost = VehicleTransaction.objects.filter(vehicle=self).aggregate(Sum('amount'))['amount__sum']
        net_revenue = rev_and_orig_cost - orig_cost # this is how much money has come in from outside buyers
        #convert a none to a 0
        net_revenue = none_to_zero(net_revenue)

        return (net_revenue - orig_cost)

    @property
    def updated_model(self):
        """Returns the VehicleModel of the same drivetrain as self for the current turn."""
        try:
            out = VehicleModel.objects.get(drivetrain=self.drivetrain, turn=Turn.cur_turn(),\
                                           producer=self.producer)
        except Vehicle.DoesNotExist:
            raise("VehicleModel.populate has not been called for the next turn().")

        return out

    @property
    def renewed(self):
        """Returns True if the vehicle has a child that will be sold on the next turn.
            Returns False otherwise."""
        v = Vehicle.objects.filter(turn=Turn.cur_turn(), parent=self)
        if v.count() == 0:
            return False
        elif v.count() == 1:
            return True
        raise Exception("Wrong length returned (not 0 or 1) from Vehicle.renewed (%s)" % v.count())


    @property
    def num_sold(self):
        """Return the number of these vehicles sold."""
        # Look up the quantity in Fleet for the vehicle for all users.
        #sold = Fleet.objects.count_vehicles(vehicle=self, sold=True)
        sold = 0
        for vt in VehicleTransaction.objects.filter(vehicle=self).exclude(buyer=self.producer).\
            exclude(buyer__username="admin"):
            sold += vt.quantity
        return sold

    @property
    def num_available(self):
        """Returns the number of vehicles remaining for purchase for this vehicle model."""
        # num_available = capacity - sold
        out = self.run - self.num_sold
        if out <= 0:
            out = 0
        return out

    @classmethod
    def available_vehs(cls):
        vehs = Vehicle.objects.filter(turn=Turn.last_turn())
        return filter(lambda x: x.num_available > 0, vehs)

    @classmethod
    def grade_vehicle(self, vehs):
        """Change the vehicle score into a vehicle grade for a vehicle queryset that has been\
            scored."""
        data = []
        for i in range(0, len(vehs)):
            data.append(vehs[i].score)

        cl = HierarchicalClustering(data, lambda x, y: abs(x - y))
        cl.setLinkageMethod('complete')

        grades = cl.getlevel(3)
        grades.sort(reverse=True)

        lookup = {}
        # sort the grades into lookup dict of this form:

        # lookup[<score>] = <grades index>
        # that means low score = low grade
        # high score = high grade
        for i in range(0, len(grades)):
            try:
                for j in range(0, len([grades[i]])):
                    lookup[grades[i][j]] = i + 1
            except TypeError:
                # in this case there is only one entry in grades
                # so treat it as 1d array
                lookup[grades[i]] = i + 1
        for veh in vehs:
            try:
                veh.score = lookup[veh.score]
            except KeyError:
                # sometimes this breaks. I don't know why.
                # search the keys of the lookup.
                # subtract the score from the keys, put it in the group with the lowest
                # difference
                gkeys = lookup.keys()
                gkeys.sort(reverse=True)
                out = [abs(x - veh.score) for x in gkeys]
                # find the smallest abs number and add it to the veh.score, if it exists in
                # lookup keys then that is the grade, otherwise subtract it from veh.score,
                # and that should be the grade. If not, bad.
                test_val = veh.score + min(out)
                if lookup.has_key(test_val):
                    veh.score = lookup[test_val]
                else:
                    veh.score = lookup[(veh.score - min(out))]

                #print out

        return vehs


    # change legalName to save() override
    @classmethod
    def legal_name(self, producer, name):
        """ Checks to make sure the producer has rights to the name (i.e.
        no other producer has used it) and that he is not creating a duplicate name."""
        retval = {'status': "True", 'msg': ""}
        query = Vehicle.objects.filter(name=name, producer=producer)
        exquery = Vehicle.objects.filter(name=name).exclude(producer=producer)
        if len(name) > 20:
            retval['status'] = "False"
            retval['msg'] = "Name must be under 20 characters."
        elif re.match(r'[\d\w]', name) == None:
            retval['status'] = "False"
            retval[
            'msg'] = "Name must start with a letter or number."#            dict['total_mpg']=u.get_total_mpg(**dict)

        # case 1 - make sure name is not in use by another producer

        elif exquery.count() > 0:
            retval['status'] = "False"
            retval['msg'] = "Name reserved by another vehicle producer. Choose a different one."

        # case 2 - vehicle name exists and is in use by the producer, on this turn

        elif query.filter(turn=Turn.cur_turn()).count() > 0:
            retval['status'] = "False"
            retval['msg'] = "Name is already used this turn. Choose another."

        # case 3 - name is legal - send default retval

        return retval


    @property
    def final_cost(self):
        """Cost of the vehicle with all fees included."""
        return int(self.price + self.gas_guzzler + self.licensing)


    def tax_and_licensing(self):
        #### GET RID OF THIS ####
        """OLD - GET RID OF THIS - .Sets gas_guzzler and licensing attributes for the vehicle."""
        self.gas_guzzler = 0
        if self.is_gas_guzzler:
            self.gas_guzzler = self.gas_guzzler_tax()

    @property
    def licensing(self):
        """The licensing fee for the vehicle. This is a place where policy can enter."""
        return  float(settings.VEHICLE_LICENSING) * self.price

    @property
    def gas_guzzler(self):
        """Return the gas guzzler fee (if any). Returns 0 if none."""
        out = 0
        if self.is_gas_guzzler:
            out = settings.GAS_GUZZLER_TAX
        return out

    @property
    def is_phev(self):
        """Returns 'True' is the vehicle is a PHEV."""
        if self.drivetrain.phev > 0:
            return True
        else:
            return False

    @property
    def is_h2(self):
        """Returns 'True' (bool) if the vehicle is a hfcv."""
        if self.drivetrain.fuel == "h2":
            return True
        else:
            return False

    @property
    def is_hev(self):
        """Returns 'True' (bool) if the vehicle is a bev."""
        if self.drivetrain.hev == True:
            return True
        else:
            return False

    @property
    def is_cv_hev(self):
        """Returns 'True' (bool) is the vehicle is a conventional hev (gas or diesel - no phev,h2)."""
        if self.drivetrain.name in set(settings.DRIVETRAIN_CLASSES['cv_hev']):
            return True
        else:
            return False

    @property
    def is_h2_phev(self):
        """Returns 'True' (bool) is the vehicle is a h2 hev (no h2 phevs). H2 vehicles are assumd to be hevs at a minimum."""
        if self.drivetrain.name in set(settings.DRIVETRAIN_CLASSES['h2_phev']):
            return True
        else:
            return False

    @property
    def is_cv(self):
        """Returns 'True' (bool) is the vehicle is a gas or diesel cv (no hev,phev)."""
        if self.drivetrain.name in set(settings.DRIVETRAIN_CLASSES['cv']):
            return True
        else:
            return False


    @property
    def is_cv_phev(self):
        """Returns 'True' (bool) is the vehicle is a gas or diesel cv phev."""
        if self.drivetrain.name in set(settings.DRIVETRAIN_CLASSES['cv_phev']):
            return True
        else:
            return False

    @property
    def is_h2_hev(self):
        """Returns 'True' (bool) is the vehicle is a h2 hev (no h2 phevs). H2 vehicles are assumd to be hevs at a minimum."""
        if self.drivetrain.name in set(settings.DRIVETRAIN_CLASSES['h2']):
            return True
        else:
            return False

    @property
    def is_bev(self):
        """Returns 'True' (bool) if the vehicle is a bev."""
        if self.drivetrain.name in set(settings.DRIVETRAIN_CLASSES['bev']):
            return True
        else:
            return False

    @property
    def is_gas(self):
        """Returns 'True' (bool) if the vehicle is gas fueled."""
        if self.drivetrain.fuel == 'gas':
            return True
        else:
            return False

    @property
    def is_diesel(self):
        """Returns 'True' (bool) if the vehicle is diesel fueled."""
        if self.drivetrain.fuel == 'diesel':
            return True
        else:
            return False

    @property
    def is_gas_guzzler(self):
        if self.mpg < settings.GAS_GUZZLER:
            return True
        else:
            return False

    def gas_guzzler_tax(self):
        """Returns the value GAS_GUZZLER_TAX from settings. Needs to be updated with a better system. This is a stub. 10/19/10"""
        return settings.GAS_GUZZLER_TAX

    def get_vehicle_costs(self):
        """Returns the product of quantity (purchased) and price (base)."""
        return round(float(self.quantity) * float(self.price), 0)

    def get_vehicle_fees(self):
        """Returns the product of quantity(purchased) and tax licensing costs."""
        self.tax_and_licensing()
        return round(float(self.quantity) * float(self.licensing), 0)

    def vehicle_vmt_modifier(self):
        """Get the vehicle VMT percentage modifier. This is used to model vmt as it relates to vehicle age."""
        index = Turn.turn_diff(self.turn) - 1 # subtract one because new vehicles are one turn behind Turn.cur_turn()
        return settings.VEHICLE_VMT[index]

    def vehicle_survival_rate(self):
        """Returns the vehicle attrition value for the vehicle. This is multiplied by the number of
        existing vehicles to yield the surviving vehicles in the next turn."""
        index = Turn.turn_diff(self.turn)
        return settings.VEHICLE_SURVIVAL[index]

    def annual_fuel_usage(self, user):
        out = user.base_vmt * self.vehicle_vmt_modifier() / self.mpg

        return round(out, 1)

    def annual_vmt(self, user):
        return (self.vehicle_vmt_modifier() * user.base_vmt)

    def age(self):
        """Vehicle.age(): The vehicle's age in years."""
        out = Turn.cur_year() - Turn.turn_to_year(self.turn)
        return (Turn.cur_year() - Turn.turn_to_year(self.turn))


class VehicleForm(ModelForm):
    class Meta:
        model = Vehicle
        exclude = ['producer', 'turn']


class VehiclePriceChangeForm(forms.Form):
    price = forms.IntegerField()


    # Add a Turn model - vehicles are purchased on a given turn.

class FuelProducer(AutopiaUser):
    group = "Fuel Producer"
    template_dir = "fp"
    nav_file = "fp/fp_nav.html"

    utility = models.BooleanField(default=False)# is player designated utility

    def home_context(self):
        """Basic fuel producer information used on every page."""
        o = super(FuelProducer, self).base_context()
        o['last_income'] = self.fuel_income()
        o['game_income'] = self.multi_fuel_income()
        o['assets'] = Asset.objects.filter(owner=self, activation_turn__lte=Turn.cur_turn(), status_code__gt=0)
        o['building'] = Asset.objects.filter(owner=self, activation_turn__gt=Turn.cur_turn())
        o['oil_fuels'] = ['gas', 'diesel']
        for f in Fuel.fuel_names():
            str = "%s_cap" % f
            o[str] = self.get_cap(f)
            str = "active_%s" % str
            o[str] = self.get_active_cap(f)
            str = "%s_margin" % f
            o[str] = self.get_margin(f)
        return o

    def get_cap(self, fuel):
        """Return the total capacity of 'fuel' that the fp can produce in a turn."""
        out = Asset.objects.filter(refinery__fuel=fuel,
                                   owner=self,
                                   status_code__gte=1,
                                   activation_turn__lte=Turn.cur_turn()).aggregate(Sum('refinery__capacity'))[
              'refinery__capacity__sum']
        if out == None:
            out = 0
        return out * 1000 * settings.YEAR_TURN_LEN

    def get_active_cap(self, fuel):
        """Get the active capacity for this FP / fuel."""
        out = Asset.objects.filter(refinery__fuel=fuel,
                                   owner=self,
                                   status_code=2,
                                   activation_turn__lte=Turn.cur_turn()).aggregate(Sum('refinery__capacity'))[
              'refinery__capacity__sum']
        if out == None:
            out = 0

        return out * 1000.0 * settings.YEAR_TURN_LEN

    def asset_summary_data(self):
        """Data collector for plot_asset_summary - shows active/total fuel resources for fp."""


    @classmethod
    def market_active_cap(cls, fuel):
        """Class method. Returns total active capacity for the entire market for 'fuel'."""
        sum = 0
        for fp in FuelProducer.objects.all():
            sum = sum + fp.get_active_cap(fuel)

        return sum

    @classmethod
    def market_cap(cls, fuel):
        """Class method. Returns total capacity for the entire market for 'fuel'."""
        sum = 0
        for fp in FuelProducer.objects.all():
            sum = sum + fp.get_cap(fuel)

        return sum

    def get_margin(self, fuel):
        """Calculates the margin level for active fuel, by FP using a weighted average."""
        cursor = connection.cursor()
        cursor.execute("SELECT sum(r.margin*r.capacity)/sum(r.capacity) FROM app_refinerymodel r,\
                       app_asset a WHERE a.refinery_id=r.id AND r.fuel=%s AND a.owner_id=%s AND a.status_code=2",
                       [fuel, self.id])
        out = cursor.fetchone()[0]
        if out == None:
            return 0

        return out

    def get_op_cost(self, fuel):
        """Return the operating cost for refineries producing 'fuel'."""
        # first do the active, then inactive costs
        kwargs = {'refinery__fuel': fuel, 'owner': self, 'status_code': 2,
                  'activation_turn__lte': Turn.cur_turn()}

        active = Asset.objects.filter(**kwargs).aggregate(Sum('refinery__active_cost'))['refinery__active_cost__sum']
        if active == None:
            active = 0
        kwargs['status_code'] = 1
        inactive = Asset.objects.filter(**kwargs).aggregate(Sum('refinery__inactive_cost'))[
                   'refinery__inactive_cost__sum']
        if inactive == None:
            inactive = 0

        return active + inactive

    def fuel_income(self, fuel=None, turn=Turn.last_turn(), turn__lte=None):
        """Calculates the gross fuel income for fuel 'fuel' on 'turn.' If no
        fuel is sent it calculates it for all fuels on the turn. The turn defaults
        to the last turn. It the turn__lte arg is sent then it calculates for
        the turn less than or equal to the arg. The turn__lte functionality shold
        be accessed from multi_fuel_income. If a turn and and a turn__lte arg
        are sent then an Exception will be thrown."""

        if not turn == None and not turn__lte == None:
            raise ValueError("A turn arg and a turn__lte arg were sent. Only one is allowed.")

        kwargs = {}

        if not fuel == None:
            if not fuel in ['gas', 'diesel', 'h2', 'elec']:
                raise ValueError("Non-existent fuel lookup on: %s" % fuel)
            kwargs['fuel'] = fuel

        if not turn == None:
            kwargs['turn'] = turn

        if not turn__lte == None:
            kwargs['turn__lte'] = turn__lte

        kwargs['seller'] = self

        out = FuelTransaction.objects.filter(**kwargs).aggregate(Sum('amount'))['amount__sum']
        out = none_to_zero(out)

        try:
            out = round(out, 3)
        except TypeError:
            out = 0
        return out


    def multi_fuel_income(self, fuel=None, turn=Turn.cur_turn()):
        """Multiple fuel income. A wrapper for fuel_income that allows the look up of the aggregate fuel_income
        across multiple turns. If a 'fuel' arg is sent then it looks for a particular fuel.
        If not then all fuels are aggregated . If a turn is not sent as an arg ('turn')  then
        it uses cur_turn as the default. """

        return self.fuel_income(fuel=fuel, turn__lte=turn, turn=None)


class ConsumerScore(Score):
    """The consumer score record. Works on a per turn basis. Stores a statistic value, based on scoring calcs."""
    mpg = models.FloatField(default=0)
    balance = models.FloatField(default=0)
    style = models.FloatField(default=0)
    performance = models.FloatField(default=0)
    quota = models.FloatField(default=0)
    final = models.IntegerField(default=0)

    def __unicode__(self):
        return "user: %s mpg: %s balance: %s style: %s performance %s quota: %s final %s" %\
               (self.user.username, self.mpg, self.balance, self.style, self.performance, self.quota, self.final)

    def set_style_performance(self, **kwargs):
        """Sets the sum of the style and performance attributes for the consumerScore for the turn. """
        class retval(object):
            1

        out = retval()
        out.performance = 0
        out.style = 0
        kwargs.update({'turn': Turn.cur_turn()})
        for f in Fleet.objects.filter(**kwargs):
            out.performance = out.performance + f.quantity * f.vehicle.performance
            out.style = out.style + f.quantity * f.vehicle.style

        return out


class VPSumData(models.Model):
    """A summary set of the VPSalesSummary, for the whole turn."""
    producer = models.ForeignKey(VehicleProducer)
    turn = models.IntegerField(default=0)
    produced = models.IntegerField(default=0)
    sold = models.IntegerField(default=0)
    unsold = models.IntegerField(default=0)
    profit = models.FloatField(default=0.0)
    cafe_penalty = models.FloatField(default=0.0)
    free_rd_points = models.IntegerField(default=0)
    assigned_rd_points = models.IntegerField(default=0)

    def __unicode__(self):
        return "VPSumData %s produced: %s sold: %s unsold: %s profit: %s cafe penalty: %s" % (
        self.producer, self.produced, self.sold, self.unsold,\
        self.profit, self.cafe_penalty)

    @classmethod
    def tally(cls):
        """Tally up the data for the turn. This is a summary of VPSalesSummary at the global level."""
        for vp in VehicleProducer.objects.all().exclude(username="v_init"):
            try:
                trn = Transaction.objects.get(buyer=vp, turn=Turn.cur_turn(), account="CAFE Penalty")
                cafe_pen = trn.amount
            except Transaction.DoesNotExist:
                cafe_pen = 0.0

            rec = cls(turn=Turn.cur_turn(), producer=vp, cafe_penalty=cafe_pen)
            for vps in VPSalesSummary.objects.filter(vehicle__producer=vp, turn=Turn.cur_turn()):
                rec.sold = vps.sold + rec.sold
                rec.unsold = vps.unsold + rec.unsold
                rec.profit = vps.profit + rec.profit
                rec.produced = vps.produced + rec.produced

            free = RandDPointRecord.objects.filter(rule__area="Free", producer=vp, turn=Turn.cur_turn()).\
                   aggregate(Sum('points'))['points__sum']
            assigned = RandDPointRecord.objects.filter(producer=vp, turn=Turn.cur_turn()).\
                       exclude(rule__area="Free").aggregate(Sum('points'))['points__sum']

            rec.free_rd_points = none_to_zero(free)
            rec.assigned_rd_points = none_to_zero(assigned)
            rec.save()


class VPScore(Score):
    """The VP score record. Balance field records the balance for the turn.\
        profit_per_vehicle is the average profit per vehicle. revenue_per_vehicle\
        is the average revenue per vehicle. revenue is the difference between this balance\
        and last turn's balance. The cap_appreciation is a measure of how much the VP's\
        capital has changed in percentage since last turn. Fleet_share is the percentage\
        of the fleet on the road that was produced by this producer. """
    balance = models.FloatField(default=0)
    profit_per_vehicle = models.IntegerField(default=0)
    revenue_per_vehicle = models.IntegerField(default=0)
    revenue = models.FloatField(default=0)
    cap_appreciation = models.FloatField(default=0)
    fleet_share = models.IntegerField(default=0)
    points = models.IntegerField(default=0)

    def __unicode__(self):
        return "VPScore - user %s points %s balance %s" % (self.user, self.point, self.balance)




class Consumer(AutopiaUser):
    template_dir = "consumer"
    nav_file = "consumer/consumer_nav.html"
    objects = UserManager()
    fleet_target = models.IntegerField(default=2000) # veh_per_capita * 10
    # weights are percentage of 100
    style_weight = models.IntegerField(default=15)

    performance_weight = models.IntegerField(default=15)

    mpg_weight = models.IntegerField(default=10)
    balance_weight = models.IntegerField(default=10)

    base_vmt = models.IntegerField(default=12000) # per year
    #allowance = models.FloatField(default=8)
    winner = models.BooleanField(default=False)
    # across the entirety of his fleet.
    base_car_cost = models.IntegerField(
            default=25000) # what the ideal car would cost for this consumer - used to determine allowances

    group = "Consumer"
    ##### NEW CONSUMER SCORE METHODS


    def save(self):
        try:
            if self.veiled==True:
                logging.debug("Cannot save a veiled consumer.")
                return None
        except AttributeError:
            super(Consumer,self).save()

    class Meta:
        pass


    def aggregate_mpg(self,last_only=True):
        """Returns the aggregate_mpg of the consumer's fleet without rgard to
        VMT (It's a dumb measurement. If last_only is set to True (default) then
        a scalar is returned, representing the mpg average for the last turn.
        If last_only is set to False then a dict is returned with format { turn:
        mpg} for all turns. Mpg value is aggregated across all drivetrains."""

        kwargs = {'fleet__owner':self}
        if last_only:
            kwargs['snap_turn']=Turn.last_turn()

        out = {}
        turn = 0
        for row in FleetSnapshot.objects.filter(**kwargs):
            try:

                out[row.snap_turn]['count'] += row.snap_quantity
                out[row.snap_turn]['mpg_sum'] += row.snap_quantity * row.fleet.vehicle.mpg
            except KeyError,e:
                out[row.snap_turn]={}
                out[row.snap_turn]['count'] = row.snap_quantity
                out[row.snap_turn]['mpg_sum'] = row.snap_quantity * row.fleet.vehicle.mpg
            turn = row.snap_turn

        for val in out:
            out[val]['avg']= round((out[val]['mpg_sum'] + 0.0) / (out[val]['count'] + 0.0),2)

        if last_only:
            try:
                out = out[turn]['avg']
            except KeyError:
                if turn==0:
                    out = 25 # reasonable guess
                else:
                    raise KeyError("Something happened. Not sure why.")
        return out

    @property
    def last_agg_mpg(self):
        """The mpg across the consumers entire fleet for last turn."""
        return self.aggregate_mpg()

    def agg_mpg_data(self):
        """Returns dict of format {turn: avg_mpg,...} for all turns for the consumer."""
        out = {}
        data = self.aggregate_mpg(last_only=False)
        for key in data:
            out[key]=data[key]['avg']
        return out


    @classmethod
    def give_allowances(cls, reset=False, no_fuel=False):
        """Gives the consumers their allowances. If reset arg (bool) is set to True the consumer
         gets his balance set to allowance + FUEL_ALLOWANCE_PERCENT*allowance, the old balance is ignored.
         The no_fuel arg, if set to True, makes the consumer not receive his fuel allowance. It defaults
         to false."""

        for o in Consumer.objects.all():
            if reset == True:
                AllowanceTransaction.objects.get(seller=o, turn=Turn.cur_turn(), desc="turn allowance").delete()
                o.balance = 0
                o.save()

            allowance = o.allowance

            #print "give allowances:  %s - %s" % (o.username, allowance)
            #print "pre allowance balance %s - %s" % (o.username, o.balance)
            # calculate the fuel allowance
            # fuel allowance = 25% of allowance * consumer.fleet_size / consumer.fleet_target
            # i.e. don't give the players a fuel allowance for vehicles they don't actually own.

            if no_fuel == False:
                allowance = allowance + settings.FUEL_ALLOWANCE_PERCENT * allowance

            turn = Turn.next_turn()
            trans = AllowanceTransaction(seller=o, buyer=uget("admin"), amount=allowance, ex_turn=Turn.cur_turn(),
                                account="consumer allowance", desc="turn allowance", turn=turn)
            trans.save()
            trans.process()
            print "post allowance balance %s - %s" % (o.username, o.balance)

    def base_price_average(self):
        """Returns, in actual dollars (10**0), the average price of a car for consumer
        at the strat of the turn. Ignores fuel costs."""
        return 10.0**6 * (self.balance + self.allowance)/self.turn_target

    def dynamic_average(self):
        """Provides the average cost of vehicles the consumer should seek to meet her quota."""
        try:
            out= int((self.balance * 10.0 ** 3) / (self.turn_vehicle_goal + 0.0))
        except ZeroDivisionError:
            out = 0
        return out



    def last_turn_price_average(self,turn=Turn.last_turn()):
        """Returns the average price paid per vehicle last turn by consumer. If there is no record
        it returns dynamic_average value."""
        vts = VehicleTransaction.objects.filter(buyer=self,turn=turn)
        out = 0
        try:
            vals = [(vt.amount,vt.quantity) for vt in vts]
            num = sum([x[0] * 10.0**6 for x in vals])
            den = sum([x[1]*1.0 for x in vals])
            out = int (round(num/(1000*den),1) *1000)
        except (VehicleTransaction.DoesNotExist, ZeroDivisionError):
            out= self.dynamic_average() * 1000
        return out


    def linear_projected_price(self):
        """Project an average price for cur_turn based on two last turns
        in linear projection."""
        t2 = self.last_turn_price_average(turn=Turn.cur_turn())
        t1 = self.last_turn_price_average()
        if t1 == 0:
            out = t2
        else:
            out = 2*t2 - t1
        return out

    def fuel_amount(self,turn=Turn.last_turn()):
        """How much money did consumer spend on fuel last turn? Optionally , send a <turn> arg
         to check the amount purchased on turn n."""
        fuel_amt = FuelTransaction.objects.filter(turn=turn, buyer=self).aggregate(Sum('amount'))[ 'amount__sum']
        if fuel_amt == None:
            #raise FuelTransaction.DoesNotExist("None returned by fuel_amount()")
            fuel_amt = 0
        return round(fuel_amt+0.0, 2)


    def projected_fuel_costs(self):
        """Returns a projected cost for fuel next turn by consumer."""
        t=Turn.last_turn()
        costs=[]
        for i in [(t-1),t]:
            try:
                costs.append(self.fuel_amount(turn=i))
            except FuelTransaction.DoesNotExist:
                fap = settings.FUEL_ALLOWANCE_PERCENT
                costs.append(fap/(1.0+fap) * self.allowance)
        return round(costs[1]**2 / costs[0],1)
#    def projected_fuel_costs(self):
#        """Returns the last fuel cost. No projection. """
#        try:
#            out = self.fuel_amount()
#        except FuelTransaction.DoesNotExist:
#            fap = settings.FUEL_ALLOWANCE_PERCENT
#            out = (1.0 + fap) * self.allowance
#        return out

    def projected_veh_price(self):
        """Return a projected vehicle price for the next turn by consumer. This is the price that
        the consumer will want to pay on average. Formula is (allowance - fuel costs)/(quantity of vehicles
        (expected). """
        if Turn.cur_turn() <= 2:
            out= self.base_car_cost
        else:
            try:
                out = (self.allowance - self.projected_fuel_costs() + self.balance)/self.turn_target
            except ZeroDivisionError:
                out = 0
            out *= 10 ** 6
#        out = max(self.base_price_average(),out)
        return out

    @property
    def fuel_percent(self):
        """Returns the percentage of funds consumer spent on fuel last turn."""
        all = Transaction.objects.get(seller=self, desc="turn allowance", turn=Turn.last_turn()).amount
        return int((100 * self.fuel_amount() + 0.0) / (all + 0.0))

    @property
    def turn_report(self):
        """Returns a report string for the Consumer. For display on the home page."""
        all = Transaction.objects.get(seller=self, desc="turn allowance", turn=Turn.last_turn()).amount
        str = "Last turn you received an allowance of $%s M." % all

        veh_amt = VehicleTransaction.objects.filter(turn=Turn.last_turn(), buyer=self).aggregate(Sum('amount'))[
                  'amount__sum']
        if veh_amt == None:
            veh_amt = 0
        veh_amt = round(veh_amt, 2)
        veh_percent = int((100 * veh_amt + 0.0) / (all + 0.0))
        rem_amt = all - self.fuel_amount() - veh_amt
        rem_percent = int(100 * rem_amt + 0.0) / (all + 0.0)
        str = str + " Of this, $%s M (%s%s) went towards fuel and $%s M (%s%s) went to vehicles." % (
        self.fuel_amount(), self.fuel_percent, '%', veh_amt, veh_percent, '%')
        #        str = str + " Of this, $%s M (%s%s) went towards fuel and $%s M (%s%s) went towards vehicles." + \
        #            " The remainder, $%s M (%s%s) , was saved for use on this turn." % (fuel_amt, fuel_percent,'%',\
        #                veh_amt, veh_percent,"%", rem_amt, rem_percent, "%")
        return str


    def percent_attr(self, attr):
        """Get percent weighting value for attr."""
        weight = self.__getattribute__("%s_weight" % attr)
        percent = (weight + 0.0) / (self.style_weight + self.performance_weight + self.mpg_weight + 0.0)
        return percent

    def score_attr(self, attr):
        """Score attr performance for turn score calculation."""
        percent = self.percent_attr(attr)
        fleet = Fleet.objects.filter(turn=Turn.last_turn(), owner=self)
        sum = 0;
        for row in fleet:
            sum = sum + row.quantity * row.vehicle.__getattribute__(
                    attr) + 10 # +10 gets the pts/$ curve off of the steep part.
            # More fair to lower income players.
        try:
            num = percent * ((sum + 0.0) / self.allowance) # allowance is in millions
            den = Consumer.global_turn_average(attr)
            out = num / den
            # multiply by ratio of how many bought versuse how many you were supposed to buy for this turn.
            #
            # multiply by ratio of how many bought versuse how many you were supposed to buy for last turn.
        except ZeroDivisionError:
            out = 0
        return out

    @classmethod
    def global_turn_average(cls, attr):
        """Calculates the last turn average for sold vehicles of feature 'attr'."""
        fleet = Fleet.objects.filter(turn=Turn.last_turn(), sold=True)
        sum = 0
        count = 0
        for row in fleet:
            count = count + row.quantity
            sum = sum + row.quantity * row.vehicle.__getattribute__(attr) + 10
        try:
            out = (sum + 0.0) / (count + 0.0)
            out = out / (cls.average_allowance() + 0.0)
        except ZeroDivisionError:
            out = 0
        return out


    def init_quick_score_vehicle(self, vehs):
        """This is quick_score_vehicle algorithm used for fleet init selection. vehs is array of saved vehicles."""
        # give each vehicle a score relative to the other vehicles for this consumer.
        data = {} # -> veh:score
        avgs = {'style':0,'performance':0,'mpg':0}
        for val in avgs:
            avgs[val]=sum([veh.__getattribute__(val) for veh in vehs])/len(vehs)

        for veh in vehs:
            out = 0
            for val in ['style','performance','mpg']:
                percent = self.percent_attr(val)
                avg_score = avgs[val]
                score = veh.__getattribute__(val)
                try:
                    out = int(out + ((score + 0.0) / (avg_score + 0.0)) * percent * 100)
                except ZeroDivisionError:
                    out=0

            data[veh]=out
        return data


    def veil(self):
        """ RAndomly munge the weights for the consumer. Used by VehicleProducer auto
        builder so it doesn't have direct acces to consumer weight stats. Returns the sum
        of the value changes (int) for testing. """

        for attr in ['style','mpg','performance']:
            rand = random.randint(1,settings.VEIL_MAX)
            setattr(self,attr+'_weight',getattr(self,attr+'_weight')+rand)
        self.veiled=True  # don't allow a save of a veiled Consumer
        return self

    def quick_score_vehicle(self,vid=None,veh=None):
        """Score vehicle relative to what consumer saw last turn (or turns?). It is a normalizatino
        with (X - mu)/sigma being the core function."""

        if vid == veh == None:
            raise ValueError("Must send a vid (int) or veh (Vehicle) to quickk_score_vehicle.")

        if veh == None:
            veh = Vehicle.objects.get(id = vid)

        dict = {}
        attrs =['style','performance','mpg']
        for attr in attrs:
            dict[attr]=0
            dict[attr+"_sd"]=0

        flts = FleetReport.objects.filter(owner=self,turn__gte=Turn.cur_turn()-2)

        for flt in flts:
            for attr in attrs:
                dict[attr] += none_to_zero(getattr(flt,attr))
                dict[attr+'_sd'] += none_to_zero(getattr(flt,attr+'_sd'))

        for key in dict.keys():
            try:
                dict[key] = dict[key]/len(flts)
            except ZeroDivisionError:
                dict[key]=0
        # dict now has a list of average values for meand and sd for the player.

        val = 0
        for attr in attrs:
            percent = self.percent_attr(attr)
            try:
                if attr != 'mpg':
                    val += 10.0 * percent * (getattr(veh,attr) - dict[attr]) / dict[attr+'_sd']
                else:
                    val += 10.0 * percent ** 2  * (getattr(veh,attr) - dict[attr]) / dict[attr+'_sd']
            except ZeroDivisionError:
                # want this to be small so there aren't huge points
                # for early vehicles and much lower for later.
                val += 2.5 * percent * (getattr(veh,attr) + 0.0) # init case - dumb - just distinguish vehicles.


        # adjust score for style/performance ratio preferrence
        mod = -1.0 * settings.QUICK_SCORE_ADJ * ((veh.performance+1.0)/(veh.style+1.0) - (self.performance_weight+1.0)/(self.style_weight+1.0))**2 +1
        mod = max(0.10,mod)
        out = int(mod*val)
        if out == 0: out=1
        return out











#    def quick_score_vehicle(self, vid):
#        """Create a relative score guide for the vehicle. It is the sum of the normalized values
#        times the consumer weights."""
#
#        out = 0
#        for val in ['style', 'performance', 'mpg']:
#            percent = self.percent_attr(val)
#            avg_score = Vehicle.objects.filter(turn=Turn.last_turn()).aggregate(Avg(val))['%s__avg' % val]
#            veh = Vehicle.objects.get(pk=vid)
#            score = veh.__getattribute__(val)
#            try:
#                out = int(out + ((score + 0.0) / (avg_score + 0.0)) * percent * 100)
#            except TypeError:
#                out = "NA"
#
#        return out

    def quick_quota(self):
        """How many vehicles do you have divided by your fleet_target."""

        #out = (count + 0.0) / (self.fleet_target + 0.0)
        ## STOPPED HERE 3/17 - Something is wrong with turn_vehicle_goal in this
        # case. Why should it drop to 0 in advance_turn if just before it is not?
        # Could there be a buy_veh interceding?
        out = 1.0 - ((self.turn_vehicle_goal+0.0)/(self.fleet_target+0.0))
        return out

    @classmethod
    def score_turn(cls):
        """Assign each consumer a turn score and save in ConsumerScore."""
        for con in cls.objects.all():
            # this should come before the new turn switches over.
            kwargs = {}
            final = 0

            for val in ['style', 'performance', 'mpg']:
                kwargs[val] = con.score_attr(val)
                final = final + kwargs[val]

            kwargs['quota'] = con.quick_quota()
            final = final * kwargs['quota']

            try:
                last_quota = ConsumerScore.objects.get(user=con, turn=Turn.last_turn()).quota
            except ConsumerScore.DoesNotExist:
                last_quota = 1

            kwargs['user'] = con
            kwargs['final'] = final * last_quota
            kwargs['turn'] = Turn.cur_turn()
            cs = ConsumerScore(**kwargs)
            cs.save()


    ##### END NEW CONSUMER SCORING SECTION

    @classmethod
    def automated_buy(cls, var_price=True,budget=True,quick=False):
        """Make automated vehicle purchases for all consumers. Uses scoring algorithm to rate cars.
        Args are var_price (bool) which allows for vps to vary prices and budget(bool) which, if True,
        forces the consumer to stick within his budget."""
        import string


        turn = Turn.objects.get(turn=Turn.cur_turn())
        if turn.vehs_bought() == True:
            raise ValueError("Vehicle purchase has been run already")
        if quick:
            cons = Consumer.objects.all()
        else:
            cons = Consumer.objects.filter(username__in=settings.COMPUTER)
            

        buys = dict((con,0) for con in Consumer.objects.all())
        completes = []
        go = True
        while go:
            sum = 0
            sold_vehs = {}

            for con in cons:
                print "%s - balance: %s" % (con.username, con.balance)
                if con.balance < 0.5 and budget :
                    if con not in completes:
                        name= string.capitalize(con.username)
                        message = "%s is out of money for the turn. %s bought %s cars this turn." \
                            % (name, name, buys[con])
                        Admin.mass_mail(message,VehicleProducer.objects.all())
                        completes.append(con)

                    continue
                goal = con.turn_vehicle_goal

                if goal > 0: # player has not purchased all of his vehicles.

                    try:
                        veh = con.best_vehicle()
                        if veh == None:
                            print "\n%s could not find vehicle\n " % con
                            continue
                            #veh.fees = veh.licensing + veh.gas_guzzler + 0
                        veh.fees = 0
                        if quick:
                            quantity = settings.AUTOMATED_BUY_MAX
                        else:
                            quantity = min(veh.get_max(con)['val'],
                                       settings.AUTOMATED_BUY_MAX) # max purchasable by consumer or max available on market


                        quantity = min(quantity, con.turn_vehicle_goal,veh.num_available) # reach goal exactly, do not overshoot.
                        buys[con] += quantity
                        vt = VehicleTransaction(buyer=con, seller=veh.producer, quantity=quantity,
                                                amount=quantity * veh.price / 10.0 ** 6,
                                                comment="Buy %s %s" % (quantity, veh.name),
                                                vehicle=veh,
                                                account="buy",
                                                fees=0,
                                                turn=Turn.cur_turn())
                        vt.save(force=True)
                        vt.process()
                        vt.do_choice_sets(veh)
                        sum = sum + goal # make it go another round because one consumer bought cars this turn.
                        if sold_vehs.has_key(veh):
                            sold_vehs[veh] = sold_vehs[veh] + quantity
                        else:
                            sold_vehs[veh] = quantity

                    except ValueError, e:
                        # no vehicles purchaseable by consumer
                        print e
                        pass

            if sum == 0:
                go = False

            if var_price == False: # let the VPs vary price to affect rankings.
                for veh in sold_vehs.keys():
                    rank = (sold_vehs[veh] + 0.0) / (settings.AUTOMATED_BUY_MAX + 0.0)
                    veh.price = int((veh.price + 0.0) * (1.0 + (rank * 0.005)))
                    print "raising price on %s by %s percent" % (veh.name, rank)
                    super(Vehicle, veh).save()

                vehs = Vehicle.objects.filter(turn=Turn.last_turn())

                for veh in vehs:
                    if veh not in sold_vehs.keys():
                        veh.price = int((veh.price + 0.0) * 0.999)
                        print "lowering price on %s by 1 percent." % veh.name
                        super(Vehicle, veh).save()
        if settings.GAME_TYPE=="autobahn":
            Fleet.distress_sale()
            turn.veh_bought=True
            turn.save()
        return True



    def best_vehicle(self):
        """Find the best_vehicle to buy automatically. Look at the average vehicle cost/quota
        value (dynamic average). Filter based on it. If can't find anything below that value
        take the cheapest above it. Then add together the op_cost + price and divide into S*.
        Take the highest val of that, as many as possible while balance remains."""

        count = 0
        mult = 1.0
        step = 0.1
        mult_limit = 2.0
        base = self.base_car_cost # * (1.0 - settings.FUEL_ALLOWANCE_PERCENT)
        # first get your vehicle candidate list
        while count == 0:
            vehs = Vehicle.objects.filter(turn=Turn.last_turn(), price__lt=base * mult)
            zeroes = 0
            for veh in vehs:
                if veh.num_available == 0:
                    zeroes = zeroes + 1

            count = vehs.count() - zeroes
            mult = mult + step
            step = step + 0.1
            if mult > mult_limit:
                return None # I give up

        best_veh = None
        best_score = None
        for veh in vehs:
            if veh.num_available == 0:
                continue
                # most points per dollar of summed veh.price and veh.op_cost is considered the best
            score = self.quick_score_vehicle(veh.id) / (veh.price + veh.op_cost)
            if score > best_score or best_score == None:
                best_score = score
                best_veh = veh

        return best_veh



    def stationary_elec(self):
        """Calculates the demand for stationary electricity for the consumer class. Stationary elec is not
        charged to the consumer but money does go to FP's who have utilities."""

        # The stationary elec consumption is bsed on drivers times per capita usage.


        return float(self.fleet_target * settings.ELEC_CONSUMPTION)

    def init_veh_change(self, dt, **kwargs):
        """Change an init_fleet created vehicle for this consumer. Args are drivetrain 'dt',
        (str) and a kwargs dict of attrs to change. Will change all vehicles with name '<username> <dt>'."""
        name = "%s %s" % (self.username, dt)
        for veh in Vehicle.objects.filter(name=name):
            for key, val in kwargs.iteritems():
                setattr(veh, key, val)
            veh.save()

    def __wfv__(self,dt,num=30):
        """Wrapper to find_veh for internal use."""

        sm = 5 + int(self.base_car_cost/5000) + random.randint(-5,5)
        sp = sm + random.randint(-5,5)
        dev = 5
        return self.find_veh(dts=dt,num=num,style_dev=dev,performance_dev=dev,
                             style_mean=sm,performance_mean=sp)

    def select_veh(self,dt=None):
        """Calls find_veh and filter feeds it to manage the genetic algorithm. If
        a drivetrain name is sent it will use that drivetrain. If left blank it
        will cycle through all drivetrain possibilities. """
        vehs = self.init_veh() # vehs is an array of unsaved Vehicles
        goods = []
        good_dict = {}
        i = 0

        while True:
            i += 1

            goods = filter(lambda x: x.mpg > 10 + self.mpg_weight, vehs)
            goods = filter(lambda x: x.price < self.base_car_cost * 1.0, goods)
            #goods = filter(lambda x: x.price > self.base_car_cost * 0.85, goods)
            goods = filter(lambda x: abs(x.style - x.performance) < 6 , goods)
            for veh in vehs:
                if veh not in goods:
                    try:
                        veh.delete()
                    except AssertionError:
                        pass
            if i > 10:
                print "Too many loops. Breaking."
                break
            if len(goods) < 3:
                vehs = self.__wfv__(dt=dt,num=30)
            else:
                good_dict.update(self.init_quick_score_vehicle(goods))
                score_avg = sum([good_dict[val] for val in good_dict])/len(good_dict)
                dels = [key for key in good_dict if good_dict[key] < score_avg]
                for val in dels:
                    del good_dict[val]
                    try:
                        val.delete()
                    except AssertionError:
                        pass

                style_mean = sum([v.style for v in good_dict])/len(good_dict) + random.randint(-2,2)
                perf_mean = sum([v.performance for v in good_dict])/len(good_dict) + random.randint(-2,2)
                style_dev = sum([(v.style-style_mean)**2 for v in good_dict])/len(good_dict)
                perf_dev = sum([(v.performance-perf_mean)**2 for v in good_dict])/len(good_dict)
                if len(good_dict) > 5:
                   break
                dts = [veh.drivetrain.name for veh in good_dict]
                vehs = self.find_veh(dts=dts,style_mean=style_mean,performance_mean=perf_mean,
                                     style_dev=style_dev,performance_dev=perf_dev,num=20)

        try:
            best = max(good_dict,key=good_dict.get)
        except ValueError:
            vp = uget("v_init")
            best = vp.dummy(drivetrain=dt,style=10,performance=10,run=10,name="foople")
            best.save()
        else:
            del good_dict[best]
            for v in good_dict:
                try:
                    v.delete()
                except AssertionError:
                    pass
        return best



    def init_veh(self,dt=None,num=20, start=0, end=20, inc=2):
        """Make a init set of vehicles with s=p from start to end at inc."""
        vp =uget("v_init")
        vehs=[]
        if dt == None:
            dts = ['gas','diesel','gas hev','diesel hev']
        for dt in dts:
            for i in range(start,end,inc):
                pi = i + random.randint(-2,2)
                veh = vp.dummy(style=i,performance=pi,run=250,drivetrain=dt)
                try:
                    veh.save() # is this save necessary? yes.
                    vehs.append(veh)
                except ValueError:
                    pass
        return vehs





    def find_veh(self,dts=None,style_mean=10,performance_mean=10,
                 style_dev=10,performance_dev=10, num=15):
        """Find a good vehicle for the buyer. style_mean is the mean to vary the style random vals around
        and performance_mean is the same for performance. The dev values are the random range to shoot
        around."""
        vehs = []
        vp = uget("v_init")
        for i in range(0,num):
            # fix this to align with fxn header
            style=max(1,style_mean+random.randint(-(style_dev),style_dev))
            performance=max(1,performance_mean+random.randint(-(performance_dev),performance_dev))
            dt = dts[random.randint(0,len(dts)-1)]
            try:
                veh = vp.dummy(style=style,performance=performance,drivetrain=dt,run=250)
                veh.save()
            except ValueError:
                pass
            else:
                vehs.append(veh)

        return vehs





            # now score the vehicle

            


    def old_find_veh(self, dt, mod=1):
        """Iteratively search for the right attr levels (style,perf) for vehicle based
        on consumer attrs. Used by init_fleet to find right type of car to give consumer
        based on base_car_cost."""

        inc = 8 # should be a power of 2
        vp = uget("v_init")
        attr = inc
        flag = True

        count = 0
        while True: # what up

            s = int(max(0, attr * mod))
            p = int(max(0, attr / mod))

            veh = vp.dummy(**{'style': s, 'performance': p, 'drivetrain': dt, 'run': 250})
            if veh.mpg < settings.MIN_INIT_MPG:
                mod = mod + 0.1
                print "increasing mod - now %s " % mod
            if abs(self.base_car_cost - veh.price) < 1000:
                return veh
            elif self.base_car_cost > veh.price:
                attr = attr + inc
            elif self.base_car_cost < veh.price:
                inc = inc / 2
                attr = attr - inc
                attr = min(attr, 1)
            count = count + 1
            if count % 10 == 0:
                print "count = %s" % count
            if count > 90:
                logging.debug("Giving up after 90 iters. Returning last veh. Check it.")
                return veh
                break


    def init_fleet(self, veh=None, vp=None, quantity=None, turn=None, **kwargs):
        """Init the consumer fleets to align correctly with the attrition curve. Fleet is 98% gas,
        2% diesel by default. If only a consumer is sent in a default vehicle will be assigned
        for all turns, if a vehicle is sent then that vehicle will be assigned. If quantity
        and turn are sent those will be assigned too and the vehicle is a specific build."""

        #import copy

        if quantity != None and turn != None:
            print "Not implemented"
        elif veh == None and quantity == None and turn == None:
            # main loop
            dts = settings.CONSUMER_INIT[self.username]['dts']
            mod = settings.CONSUMER_INIT[self.username]['style_to_perf']
            den = sum(settings.VEHICLE_SURVIVAL)
            if vp == None:
                vp = uget("v_init") # doesn't really matter for now
                print "running %s" % self.username
                for dt, val in dts.iteritems():
                    base_veh = self.select_veh(dt=dt)
                    for i in range(1, len(settings.VEHICLE_SURVIVAL)):
                        percent = settings.VEHICLE_SURVIVAL[i] / den
                        turn_vehs = int(percent * (self.fleet_target + 0.0) * val)
                        veh = vp.dummy(drivetrain=base_veh.drivetrain.name, style=base_veh.style,
                                       performance = base_veh.performance, run=base_veh.run)

                        veh.name = "%s %s" % (self.username, dt)
                        veh.run = turn_vehs
                        t = Turn.cur_turn() - i
                        veh.turn = t
                        veh.save()
                        #print "Added account='buy' here. This might create weird problems !!! Remove if it does!!"
                        vt = VehicleTransaction(buyer=self, seller=vp, vehicle=veh, quantity=turn_vehs
                                                , amount=0, fees=0, account="buy")
                        vt.turn = t
                        # bypass the normal procedure for vt.save with force=True
                        vt.save(force=True)
#                        fl = Fleet(vehicle=veh, owner=self, quantity=turn_vehs, fuel=dt,
#                                  transaction=vt, sold=True, points=0, turn=t)
#                        fl.save()
        print "done"

    @property
    def sum_score(self):
        """Returns the sum of all this consumer's score. This is his game accumulated score."""

        try:
            sum = ConsumerScore.objects.filter(user=self).aggregate(Sum('final'))['final__sum']
        except ConsumerScore.DoesNotExist:
            sum = 0

        return sum

    @property
    def num_to_buy(self):
        """The number of vehicles to buy to get to the consumer's desired vehicle count."""
        out = Turn.num_turns() * self.turn_target - self.num_vehs_acquired
        return out

    @property
    def quota_ratio(self):
        """The number of vehicles acquired over the game divided by the number of vehicles that should
        be acquired by the end of the current turn."""
        try:
            out = round((self.num_vehs_acquired + 0.0) / (Turn.last_turn() * self.turn_target * 1.0), 2)
        except Exception:
            out = 0
        return out

    @property
    def num_vehs_acquired(self):
        """The total number of vehicles the consumer has purchased across the entirety of the game."""
        try:
            out = VehicleTransaction.objects.filter(buyer=self).aggregate(Sum('quantity'))['quantity__sum']
            if out == None:
                out = 0
        except NoneType:
            out = 0

        return out

    @classmethod
    def expected_veh_purchases(cls):
        """Returns a dumb estimate of how many vehicles will be purchased in the market. Dumb, because it never changes\
        . I can make it smarter to account for under/over buys by consumers later, but this is just to help vps figure\
        out how many vehicles to bring to market."""

        return int(Consumer.objects.all().aggregate(Sum('fleet_target'))['fleet_target__sum'] / 4)

    @classmethod
    def average_allowance(cls):
        """Average allowance for all consumers."""
        sum = 0
        count = 0
        for con in Consumer.objects.all():
            count = count + 1
            sum = con.allowance + sum
        out = (sum + 0.0) / (count + 0.0)
        return out

    @property
    def allowance(self):
        """Formula for setting the annual player allowance."""
        return round(self.fleet_target * self.base_car_cost * 0.25 / 10 ** 6, 2)

    @classmethod
    def market_size(cls):
        """The expected number of vehicles purchased per turn. Sum the fleet_target for all consumers
        and divide by 4. """
        sum = 0
        for con in cls.objects.all():
            sum = con.fleet_target + sum

        return (sum / 4)

    # consumer score = weight * 100*(my value /max value ) * 100*(my N/ N)
    # max value is the highest value for the attribute
    # these properties should be cached.


    @property
    def average_vehicle_price(self):
        """Returns the average vehicle price based on current allowance and fleet target purchase.

        Assumes 75% of transport allowance goes to fuel."""
        return (.75 * self.allowance * 10 ** 6) / (self.fleet_target / 4)

    @property
    def fleet_size(self):
        """returns count of the current fleet size for the consumer"""
        return Fleet.objects.count_fuel_types(owner=self)

    @property
    def style_average(self):
        """Returns the non-weighted average style for the consumer's fleet."""
        return Fleet.objects.average("style", owner=self)


    @property
    def performance_average(self):
        """Returns the non-weighted average performance for the consumer's fleet."""
        return Fleet.objects.average("performance", owner=self)

    @property
    def turn_target(self):
        """A dumb estimate of how many vehicles the player will buy on any given turn. Essentially fleet_target/4."""
        return int((self.fleet_target + 0.0) / 4)

    @property
    def turn_vehicle_goal(self):
        """How many vehicles the Consumer would buy this turn to reach fleet target over time.
            This is a moving figure. It will decrease during the turn as the consumer buys more vehicles."""
        # check how many cars C owns now
        owned = Fleet.objects.count_fuel_types(owner=self)
        turn_goal = self.fleet_target - owned

        turn_goal = max(turn_goal, 0) # don't show a negative goal

        return turn_goal

    @property
    def last_turn_vehicle_count(self):
        """Returns how many vehicles the consumer had at the end of last turn."""

    def score_vehicle(self, veh, avgs=None ):
        """A simple rating algorithm to describe the relative attractiveness of a vehicle to the consumer.
            Score = sum(weight * val / avg(val)) - weight * price/avg(price) where vals are style, performance and mpg.
            . Input is the vehicle object. avgs is the average of performance, style, price and mpg for last turn (current cars).
            It can be passed in to save multiple calculations."""
        if avgs == None:
            avgs = Vehicle.objects.filter(turn=Turn.last_turn()).aggregate(Avg('performance'),
                                                                           Avg('style'), Avg('price'), Avg('mpg'))
            # size scalar accounts for the impact on the players ability to meet his fleet size target
        try:
            size_scalar = -2 * ((self.turn_vehicle_goal + 0.0) / (veh.max + 0.0) - 1) ** 2 + 1.0
        except ZeroDivisionError:
            size_scalar = -10

        score = (self.performance_weight + 0.0) * ((veh.performance + 0.0) / avgs['performance__avg']) +\
                (self.style_weight + 0.0) * ((veh.style + 0.0) / avgs['style__avg']) +\
                (self.mpg_weight + 0.0) * ((veh.mpg + 0.0) / avgs['mpg__avg']) -\
                (self.balance_weight + 0.0) * ((veh.mpg + 0.0) / avgs['price__avg'])

        out = int(size_scalar * score) + 100
        if (out == 0):
            out = 1 # this prevents a 0 from showing up in the score column, which screws up tablesort sorting.

        return out


    def home_context(self):
        """Add in stuff"""

        c = super(Consumer, self).base_context()
        c['home'] = "consumer/new_home.html"
        c['vehicle_stats'] = self.vehicle_stats()
        #c['veh_progress'] = self.vehicle_progress() # number of vehicles purchased since game start.

        prof_data = []
        prof_labels = []
        sum = 0.0
        for val in ['style', 'performance', 'mpg']:
            val = val + "_weight"
            sum = sum + self.__getattribute__(val) * 100.0

        for val in ['style', 'performance', 'mpg']:
            tmp = val
            tmp = tmp + "_weight"
            score = self.__getattribute__(tmp) * 100.0

            prof_labels.append("%s (%s%s)" % (val, int(100.0 * score / sum), "%"))
            prof_data.append(score)

        c['profile_data'] = prof_data
        c['profile_labels'] = prof_labels
        # TODO: see if these 3 lines are necessary. I think they are not used now.
        #prog = self.attr_scores()
        #c['performance_progress']=prog['performance'] # this is the sum of the performance bought by player
        #c['style_progress']=prog['style'] # this is the sum of the style bought
        my_scores = ConsumerScore.objects.filter(user=self)
        for m in my_scores:
            #there should be a way to do this automatically! TODO
            m.year = Turn.turn_to_year(m.turn)

        c['my_scores'] = my_scores
        #c['win_score']=settings.WIN_SCORE # the goal to reach in order for the consumer to win. Should be by code.
        #c['vmt_percent'] = self.current_vmt_goal

        #o = self.calc_score(c)
        #c.update(o) # c has score (game), progress (% points of goal) and vmt_score now.
        return c


    def fuel_volume_data(self):
        """Returns a fuel data volume string as 'data' attr for jqBarGraph. Format is: [[gas,diesel,h2,elec],year],...
        for all years, where gas,diesel,h2, elec are volumes of fuel purchased that year.  Also returns
        a legend attr ."""
        dict = {}
        dict['data'] = []
        dict['cost'] = []
        dict['labels'] = []
        dict['legend'] = ['gas', 'diesel', 'h2', 'elec.']
        max = Turn.objects.all().aggregate(Max('turn'))['turn__max'] #don't read for the current turn

        for turn in Turn.objects.filter(turn__lt=max):
            tmp_list = []
            cost_list = []
            for fuel in ['gas', 'diesel', 'h2', 'elec']:
                try:
                    #out = FuelTransaction.objects.get(turn=turn.turn, fuel=fuel, buyer=self)
                    out = FuelTransaction.objects.get(turn=turn.turn, fuel=fuel, buyer=self)
                    quant = out.quantity / 1000
                    cost = out.amount * 1000
                except (FuelTransaction.DoesNotExist, TypeError):
                    quant = 0
                    cost = 0

                tmp_list.append(quant)
                cost_list.append(cost)

            yr = Turn.short_year(turn.turn)
            dict['labels'].append(yr)
            dict['data'].append(tmp_list)
            dict['cost'].append(cost_list)

        return dict


    @property
    def fleet_size(self):
        """The current size of the consumer's fleet."""
        out = Fleet.objects.count_fuel_types(owner=self);
        if out == None:
            out = 0
        return out

    def __unicode__(self):
        return 'Consumer %s perf w: %s style w: %s mpg w: %s balance w: %s ' %\
               (self.username, self.performance_weight, self.style_weight, self.mpg_weight,
                self.balance_weight)


class FleetReport(models.Model):
        """A simple data collection returned by Consumer.fleet_report."""

        owner = models.ForeignKey(Consumer)
        name = models.CharField(max_length=40)
        turn = models.IntegerField(max_length=2)
        mpg = models.FloatField(null=True) # average perf. of all vehicles build
        mpg_sd = models.FloatField(null=True) # sd of mpg  of all vehicles build
        performance = models.FloatField(null=True) # average perf. of all vehicles build
        performance_sd = models.FloatField(null=True) # sd perf. of all vehicles build
        style = models.FloatField(null=True) # average style of all vehicles
        style_sd = models.FloatField(null=True) # sd style of all vehicles
        price = models.IntegerField(max_length=6,null=True) # avg purchase price
        total = models.IntegerField(max_length=4,default=0)
        dts = models.CharField(max_length=250,null=True,blank=True) # json of drivetrain hash

        def save(self):
            self.dts = json.dumps(self.dts)
            for attr in vars(self):
                if getattr(self,attr)=="NA":
                    setattr(self,attr,None)
            self.owner_id = self.owner.id
            super(FleetReport,self).save()

        def __unicode__(self):
            str = ''
            for attr in vars(self):
                str += "%s : %s\n" % (attr,getattr(self,attr))
            return str

        def printer(self):
            """Make a nice human readable report on this object. Returns a string."""
            out = "Name: %s\nTurn: %s \nAvg MPG: %s \n"  \
                 "Avg performance: %s\nAvg style: %s \n"  \
                 "Avg price: %s \nDrivetrains (counts): %s\n" \
                % (self.username, self.turn, self.mpg, self.performance, self.style,
                self.price, self.dts)
            return out

        @classmethod
        def run_fleet_reports(cls):
            """Run the stock fleet report for all consumers."""
            for con in Consumer.objects.all():
                cls.fleet_report(con)

        @classmethod
        def fleet_report(cls,*args, **kwargs):
            """Create a summary data set on the consumer's fleet. Send the
            filter variables in kwargs['dict']. By default it looks up current turn and
            seller is self. Send kwargs['exclude'] to modify the exclude set. Returns
            a Report object."""



            out = FleetReport()
            out.name = args[0].username
            out.owner = args[0]
            exclude = {}
            try:
                exclude.update(kwargs['exclude'])
            except KeyError:
                pass
            dict = {'turn':Turn.cur_turn(),'buyer':args[0]}
            try:
                dict.update(kwargs['dict'])
            except KeyError:
                pass
            vts = VehicleTransaction.objects.filter(**dict).exclude(**exclude)
            vehs = [v.vehicle for v in vts]

            s={}
            for k in ['amount','quantity','performance','style','mpg']:
                s[k]=0

            out.turn = dict['turn']
            out.dts = {}
            for v in vts:
                s['quantity'] += v.quantity
                s['amount'] += v.amount
                name = str(v.vehicle.drivetrain.name)
                if not out.dts.has_key(name):
                    out.dts[name]=0
                out.dts[name] += v.quantity
                for t in ['performance','style','mpg']:
                    s[t] += v.quantity * getattr(v.vehicle,t)

            out.total = s['quantity']
            try:
                out.price=round((s['amount']/s['quantity']) * 10**6,0)
                for t in ['performance','style','mpg']:
                    setattr(out,t,round(s[t]/(s['quantity']*1.0),2))
            except ZeroDivisionError:
                for t in ['price','style','performance','mpg']:
                    setattr(out,t,"NA")


            vs = {}
            if len(vts) > 0:
                for v in vts:
                    for attr in ['performance','style','mpg']:
                        if not vs.has_key(attr):
                            vs[attr]=0
                        vs[attr] += v.quantity  * ( 1.0 * getattr(v.vehicle,attr) - 1.0* getattr(out,attr) ) ** 2

                #why are sds so high?

                sds = {'performance':0,'style':0,'mpg':0}
                for attr in ['performance','style','mpg']:
                    val = ((vs[attr]/(out.total + 0.0))) ** 0.5
                    setattr(out,"%s_sd" % attr, val)

            out.save()
            return out

class Admin(AutopiaUser):
    template_dir = "autopia_admin"
    group = "Admin"
    nav_file = "autopia_admin/admin_nav.html"

    @classmethod
    def mass_mail(cls,text,receivers=None):
        """Send all players a message from 'admin' with message of 'txt'. The receivers
        arg is a QueryList of all users who should receive the message. Default is
        all AutopiaUsers."""
        msg=Message(text=text,turn=Turn.cur_turn(),sender=uget("admin"))
        msg.save()
        if receivers == None:
            receivers = AutopiaUser.objects.all()

        for rec in AutopiaUser.objects.all():
            try:
                mr = MessageReceiver(message=msg,receiver=rec,status="unsent")
                mr.save()
            except Exception,e:
                print e


    def reset_game(self):
        """Set the game back to the first turn, in this case the top of 2012. This
        needs to be done with database truncation."""
        app_models = get_app('app')
        # need to restore player balances
        # consumers should go to 0.
        # vps should go to their starting balance - that's the hard part. - I guess I could total
        # up all the money that vps spent and just give it back to them. Not too hard...

        for vp in vpall():
            spent = VehicleTransaction.objects.filter(buyer=vp).aggregate(Sum('amount'))['amount__sum']
            earned = Transaction.objects.filter(seller=vp).aggregate(Sum('amount'))['amount__sum']

            val = 0
            try:
                val = vp.balance + spent
            except TypeError:
                val = vp.balance

            try:
                val = val - earned
            except TypeError:
                pass
            vp.balance = val
            vp.save()

        for con in Consumer.objects.all():
            con.balance = 0

        for m in get_models(app_models):
            if m.__name__ not in ["Fuel", "VehicleProducer", "Consumer", "Admin"]:
                try:
                    m.objects.filter(turn__gt=1).delete()
                except Exception:
                    print "No turn - %s " % m
                    pass

        self.advance_turn()

    def home_context(self):
        """Add in stuff"""
        c = super(Admin, self).base_context()
        return c

    @classmethod
    def autoturn(cls, record=True):
        """Automatically advance a turn. No need to create a admin user. Record arg (bool) tells
        system whether or not to record the run with a db dump. Default is True."""
        a = uget("admin")
        a.advance_turn(**{'record': record})

    @classmethod
    def get_admin(self):
        a = Admin.objects.get(username="admin")
        return a

    def test_advance_turn(self):
        """The advance_turn to be used from the test module. It is the same as advance_turn, but does not
        record to the database with pg_dumps."""
        self.advance_turn(**{'record': False})

    def archive_db(self, name):
        """Archive the db to RECORD_DIR. Title with 'name' arg. Will include turn also in name."""
        logging.debug("Running a pg_dump for the turn.")

        try:
            cmd = "pg_dump -Ujoel %s > %s%s/bottom%s.sql" % (settings.DATABASE_NAME,\
                                                             settings.HOME_DIR, settings.RECORD_DIR, Turn.cur_year())
            logging.debug(cmd)
            os.system(cmd)
        except Exception, e:
            logging.debug("pg_dump failed: %s" % e)
            pass


    def advance_turn(self, *args, **kwargs):
        """An admin tool. Triggers all the things that need to happen before and after a turn.
            1. Advance year
            2. Do fleet attrition.
            3. Run R&D - make new vehicle models for each VP
            4. Give consumers allowance.
            5. Set current vmt_goal to vmt_goal.


            kwargs:
                vp_penalty - if vp_penalty is set to false, do not run the verify_sales for the vp

            """
        #AutopiaUser.set_computer_players()

        if settings.GAME_TYPE=="autobahn" and Turn.cur_turn()>=3:
            VehicleProducer.popveh()

        if settings.RUN_TESTS:
            print "****************************************************************************************"
            print "*       RUNNING TESTS - set settings.RUN_TESTS to False to stop this for deployment.   *"
            print "****************************************************************************************"
            for con in Consumer.objects.all():
                for f in Fleet.objects.filter(owner=con,turn__gt=1):
                    out = f.test_attrition()
                    if out==False:
                        raise ValueError("Error Fleet.test_attrition failed.")


        turn = Turn.objects.get(turn=Turn.cur_turn())
        turn.status = "processing"
        turn.update()
        try:
            if kwargs['record'] == False:
                logging.debug("NO pg_dump run.")
                pass
            else:
                self.archive_db('bottom')
        except KeyError:
            self.archive_db('bottom')

            # give consumer his allowance for the turn

            # assign rd_points to vps
        RandD.automatic_rd()


        RuleBase.allocate() # assign RD points
        PlayPrompt.vp_prompts() # prompts aimed at vps
        PlayPrompt.fp_prompts() # prompts aimed at vps
        Consumer.score_turn()
        PlayPrompt.consumer_prompts()

        # save off info about consumers with negative balances prior to give_allowances.
        # This will be a factor in Fleet.attrit(penalty)
        penalty = {}
        for con in Consumer.objects.all():
            if con.balance < 0:
                val = round(min(100.0, abs(con.balance)),0)
                if val > 5:
                    penalty[con.username]=val
#                    PlayPrompt.new(user=con,priority=7,turn=Turn.cur_turn(),message="Your consumers dumped " \
#                            " an extra %s percent of their [  %s  ]vehicles "\
#                           " because they cannot afford fuel." % (val,",".join(Fuel.expensive())), code=PlayPrompt.codes['veh_dump'])

        Consumer.give_allowances()
        Fuel.buy_fuels()
        FleetReport.run_fleet_reports()

        # calculate the cafe penalties

        if settings.GAME_TYPE=="autopia":
            Fleet.distress_sale() # get rid of unsold vp fleet - must happen after turn score

        # CAFE Section #############################
        #        cafe = Fuel.objects.get(turn=Turn.cur_turn()).cafe
        #        for vp in vpall():
        #            # CALCULATING CAFE PENALTY HERE. THIS SHOULD BE A METHOD.
        #            my_cafe = vp.calc_cafe()
        #            if my_cafe==None:
        #                continue
        #
        #            if my_cafe < cafe:
        #                # do a penalty transaction
        #
        #                #get # of vehicles sold by this vp this turn.
        #
        #                ### FIX HERE - cafe penalty is only applied to vehicles sold to C - THIS SHOULD GO AFTER distress)sale
        #                vehs = VehicleTransaction.objects.filter(seller=vp,turn=Turn.cur_turn()).aggregate(Sum('quantity'))['quantity__sum']
        #
        #                vehs = none_to_zero(vehs)
        #                penalty = (cafe - my_cafe) * vehs * 10 * settings.CAFE_PENALTY / 10**6
        #                trans = Transaction(buyer=vp,seller=uget("admin"),turn=Turn.cur_turn(),
        #                            amount=penalty,account="CAFE penalty",desc="CAFE penalty assessed.")
        #                trans.save()
        #                trans.process()

        # END CAFE Section ##########################




        #        if kwargs.has_key('vp_penalty'):
        #            if kwargs['vp_penalty'] != False:
        #                VehicleProducer.verify_sales() # make sure VPs met their sales targets. Penalize if failure occured.
        #        else:   # kwargs doesn't have vp_penalty so just proceed as normal
        #            VehicleProducer.verify_sales()

        VehicleProducer.score_turn()

        VPSalesSummary.summarize()

        if Turn.cur_turn() > 2: # don't tax init
            VehicleProducer.cafe_assessment()

        VPSumData.tally()

        year = Turn.calc_next_turn_year()
        new_turn = Turn.cur_turn() + 1
        T = Turn(turn=new_turn, year=year, status="processing")
        T.save()

        turn = Turn.objects.get(turn=Turn.last_turn())
        turn.status = "complete"
        turn.update()
        # remove vehicles from consumer fleet due to age

        FleetSnapshot.process() # data collection and management routines
        #FleetSnapshot.snap()

        # consumers with negative balance experience greater fleet attrition
        # as consumers sell off vehicles.




        Fleet.attrit(penalty)
        Asset.attrit()

        VehicleModel.populate(demo=False)
        # copy_and_update needs to come right after populate
        #if Turn.cur_turn() > 2:
        #    VehicleProducer.copy_and_update_vehs()
        try:
            if kwargs['record'] == True:
                logging.debug("NO pg_dump run.")
                pass
            else:
                self.archive_db('top')
        except KeyError:
            self.archive_db('top')

        turn = Turn.objects.get(turn=Turn.cur_turn())
        turn.status = "run"
        turn.update()
        try:
            print "It is now turn %s, year %s. GAS_COST array has length of %s" % \
            (Turn.cur_turn(),Turn.turn_to_year(Turn.cur_turn()), len(settings.GAS_COST))
        except TypeError:
            # len(settings.GAS_COST) doesn't make sense because i t is a fxn
            # if we get here
            print "It is now turn %s, year %s. GAS_COST is %s ." %\
                  (Turn.cur_turn(),Turn.turn_to_year(Turn.cur_turn()), round(settings.GAS_COST([turn.turn]),2))

        return True

    def vehicle_turn_rollback(self):
        """Rolls back the vehicle turn so that I can setup vehicles without advancing the turn for game init."""
        for veh in Vehicle.objects.all():
            print "rolling back veh %s" % veh
            veh.turn = veh.turn - 1
            super(Vehicle, veh).save()

        return

class Transaction(models.Model):



    buyer = models.ForeignKey(AutopiaUser, related_name="from user", default=-1)
    seller = models.ForeignKey(AutopiaUser, related_name="to user")
    amount = models.FloatField()
    fees = models.FloatField(default=0)
    desc = models.CharField(max_length=200, default="none")
    status = models.CharField(max_length=20, default="unprocessed")
    account = models.CharField(max_length=40, default="none")
    comment = models.CharField(max_length=1000, default="No comment.")
    turn = models.IntegerField(default=-1000)

    def __unicode__(self):
        return 'from: %s to: %s amount: %s' % (self.buyer, self.seller, self.amount)

    @classmethod
    def transacting_users(self, me):
        """Return a list of all players that can do a transaction except for me (AutopiaUser)."""
        try:
            name = me.username
        except AttributeError:
            # a string has been sent (or unicode, instead of an object.
            name = me.__str__()

        start = True
        for val in ['Consumer', 'FuelProducer', 'VehicleProducer']:
            mod = get_model('app', val)
            for m in mod.objects.all():
                if m.username not in settings.NON_TRANSACTING and m.username != name:
                    qs = AutopiaUser.objects.filter(username=m.username)
                    if start:
                        users = qs
                        start = False
                    else:
                        users = users | qs
        return users

    def process(self,**kwargs):
        # process both ends of the transaction
        # first deduct from the buyer then add to the seller

        if self.status == "completed":
            #logging.debug("Attempting to process complete transaction. Ignored.")
            return True

        if self.status != "unprocessed":
            raise AssertionError("status must be unprocessed (%s)" % self.status)
        try:
            self.buyer.update_balance(-1 * (self.amount + self.fees))
            self.seller.update_balance(self.amount)
        except RuntimeError:
            self.status = "failed"
            raise RunTimeError("ERROR: transaction failed")

        self.status = "completed"
        # I think this save should really be a super call
        # I think it's evaluating self as VehicleTransaction when it's passing through there.
        super(Transaction, self).save()

post_save.connect(transaction_process, sender=Transaction)

class TransactionForm(ModelForm):
    """Form to allow inter-user transactions."""
    # find all the possible users that are live players

    def __init__(self, me, *args, **kwargs):
        super(TransactionForm, self).__init__(*args, **kwargs)

        users = Transaction.transacting_users(me)

        self.fields['seller'] = forms.ModelChoiceField(users, label="Pay To")

        self.fields['amount'] = forms.IntegerField(min_value=0, help_text='(in thousands)')
        self.fields['comment'] = forms.CharField(widget=forms.Textarea(attrs={'cols': 60, 'rows': 4}))

    class Meta:
        model = Transaction
        exclude = ['fees', 'turn', 'buyer', 'status', 'desc', 'account']

class AllowanceTransaction(Transaction):
    """Test class to register when allowance transactions are made."""
    ex_turn = models.IntegerField()





class VehicleTransaction(Transaction):
    quantity = models.IntegerField()
    vehicle = models.ForeignKey(Vehicle)
    sold=models.BooleanField(default=False)
    buyer_avg_price = models.IntegerField(default=0) # how much the buyer had to spend per vehicle at purchase time

    def do_choice_sets(self,veh):
        """Create VehicleTransactionChoiceSets accompanying a VEhicleTransaction. Input args are VehicleTransaction and selected vehicle."""
        orig_veh = veh
        for veh in Vehicle.available_vehs():
            chosen=0
            if orig_veh.id == veh.id:
                chosen = 1
            self.vehicle_transaction_choices.create(vehicle=veh, selected=chosen, price=veh.price,\
                           op_cost=veh.op_cost,score=self.buyer.quick_score_vehicle(veh.id))

    @classmethod
    def points_since_last_turn(cls, div, **kwargs):
        """Given an increment 'div', counts how many divs have been generated
           since last turn for a vehicle set defined by kwargs. For example if div=100
           and there were 150 vehicles in that set last turn and on the following turn
           another 50 vehicles of that description were sold, the method would return
           1 point,because the sum value of 200 had been reached. It's an accumulation
           based count, it's crossing the div marker that counts . This keeps crdit
           for all vehicles sold that meet the criteria, even if that credit is missed
           on the current turn.

           The VP gets credit for vehicls sold in distress sale; he paid for them why
           shouldn't he? Even though he sold them at a loss it does not matter.
           """

        kwargs['turn__lt'] = Turn.cur_turn()

        prior = cls.objects.filter(**kwargs).aggregate(Sum('quantity'))['quantity__sum']
        prior = none_to_zero(prior)

        del kwargs['turn__lt']
        kwargs['turn'] = Turn.cur_turn()
        cur = cls.objects.filter(**kwargs).aggregate(Sum('quantity'))['quantity__sum']
        cur = none_to_zero(cur)

        out = int((cur + 0.0) / (div + 0.0)) - int((prior + 0.0) / (div + 0.0))
        return out


    @classmethod
    def active_turn(cls):
        """Check to see if any sales of vehicles have been made to Consumers on this turn.
            If so, it is an active turn. Returns boolean."""
        retVal = False
        for vt in VehicleTransaction.objects.filter(turn=Turn.cur_turn()):
            # check to see if vt.buyer.id is in Consumer table
            try:
                o = Consumer.objects.get(id=vt.buyer.id)

                if o != None:
                    retVal = True
                    break
            except Consumer.DoesNotExist:
                pass

        return retVal


    def __unicode__(self):
        return str(
                "{0!s} prod: {1!s} q: {2!s} seller: {3!s} buyer: {4!s} desc: {5!s} account: {6!s}".format(
                        self.vehicle.name,
                        self.vehicle.producer,
                        self.quantity, self.seller,
                        self.buyer, self.desc,
                        self.account)
                )

    def reverse(self,force=False):
        """Reverse a vehicle transaction. Limited to initial build. Credit back the amount
        as a Transaction and delete the vehicle. This can only be done for vehicles that are
        scheduled for production, not for live vehicles."""

        # check to see if the transaction reverse is legal.
        if not self.vehicle.turn == Turn.cur_turn() and not force:
            raise ValueError("This vehicle cannot be reversed. It has been released.")

        tr = Transaction(seller=self.vehicle.producer, buyer=uget("admin"), amount=self.amount,
                         turn=Turn.cur_turn(), desc="Reversing Build")
        tr.save()
        #tr.process()
        Vehicle.objects.get(pk=self.vehicle.id).delete()
        return True

    def process(self, *args, **kwargs):
        """Move the vehicles into the purchasers fleet and the modney out. Vehicle Producer   \
            should have a fleet too. Move the vehicles out of that fleet unless the VP has sold    \
            the minimum. Send tax and licensing monies to the proper account(s).    \
            Also, update the consumer's scores.  """

        # add vehicles to buyers fleet
        if self.status =="completed":
            #logging.debug("VehicleTransaction.process is complete. Ignoring.")
            return True

        if self.account == "distress": #  transfer vehicle out of vp fleet.
            #
            try:
                vpf = Fleet.objects.get(owner=self.vehicle.producer, sold=False, vehicle=self.vehicle)
                vpf.quantity = vpf.quantity - self.quantity
            except Fleet.DoesNotExist:
                print "Figure out why the object doesn't exist - Fleet.DoesNotExist"
                print "vehicle: " + str(self.vehicle) + "  self " + str(self.seller) + "\n"
                raise Exception(" I don't knwo!!")

            if vpf.quantity < 0:
                raise ValueError("VP has a negative fleet size for " + self.vehicle.name + " : " + str(vpf.quantity))
            super(Fleet, vpf).save()


        elif self.account == "buy" or self.account == "none":
            # this is a consumer buying the vehicle - transfer it to his fleet
            # Note that for a distress sale the admin pays for the vehicles, but
            # never receives them.
            try:
                f = Fleet.objects.get(owner=self.buyer, vehicle=self.vehicle)
                # if we get here it means the C has already bought this vehicle. Add
                # it to his fleet and subtract from the Vp.
                f.quantity = f.quantity + self.quantity

                # removing the Fleet.points column
                #f.points = f.points + kwargs['points']
            except Fleet.DoesNotExist:
                # there is no entry in the fleet table for this vehicle and owner
                f = Fleet(vehicle=self.vehicle, owner=self.buyer, quantity=self.quantity,
                          turn=Turn.cur_turn(), transaction=self, sold=True) #,points = kwargs['points'])

            f.save()
            vf = Fleet.objects.get(owner=self.vehicle.producer, vehicle=self.vehicle)
            vf.quantity = vf.quantity - self.quantity
            vf.save()
            # deduct from the VP's fleet stock:


        elif self.account == "initial vehicle build":
            # this is the vp receiving vehicle stock
            f = Fleet(vehicle=self.vehicle, owner=self.buyer, quantity=self.quantity,
                      turn=Turn.cur_turn(), transaction=self, sold=False)

            f.save()

        else:
            raise Exception("This shouldn't ever happen. Account is " + str(self.account))


        # do vehicle purchase
        # jlksdjf slfj dlsk


        super(VehicleTransaction, self).process()
        # do fee transaction

    def save(self, force=False):
        if not force: # force is used by init_fleet to override
        # this function. Normal save must be defeated.
            last_turn = Turn.cur_turn() - 1
            if not self.vehicle.turn == last_turn and not self.buyer.group == "Vehicle Producer":
                # if the buyer is not a vehicle producer then the transacation can only go through
                # if the vehicle was produced on the last turn.
                msg = "This vehicle , " + str(self.vehicle.name) + " , not availalble this turn."
                raise Exception(msg)
            if self.turn == -1000:
                self.turn = Turn.cur_turn()

        super(VehicleTransaction, self).save()



    @classmethod
    def first_sale(cls, **kwargs):
        """Check to see if this is the first turn on which a sale of vehicle meeting the criteria of kwargs
        has been sold. Returns boolean."""
        # first check if any were sold in this turn.
        kwargs['turn'] = Turn.cur_turn()
        cur = VehicleTransaction.objects.filter(**kwargs).exclude(buyer=uget("admin")).aggregate(Sum('quantity'))[
              'quantity__sum']
        if cur == None or cur == 0:
            return False
        del kwargs['turn']
        # 1 or more were sold
        # now check to see how many were sold in all prior turns
        kwargs['turn__lte'] = Turn.cur_turn() - 1
        prior = VehicleTransaction.objects.filter(**kwargs).exclude(buyer=uget("admin")).aggregate(Sum('quantity'))[
                'quantity__sum']
        if prior == None or prior == 0:
            return True # cur_turn is the first turn on which this drivetrain was sold by criteria of kwargs
        else:
            return False

    @classmethod
    def avg_attr_and_quantity(self, vp, attr):
        """Return the average value of some attr (e.g. style, performance) and the quantity of vehicles sold."""

        attr_str = "vehicle__%s" % attr
        out = VehicleTransaction.objects.filter(quantity__gt=0,
                                                vehicle__producer=vp,
                                                turn=Turn.cur_turn()).exclude(buyer=vp).exclude(
                buyer=uget("admin")).aggregate(Avg(attr_str),
                                               Sum('quantity'))
        avg = none_to_zero(out['vehicle__%s__avg' % attr])
        quantity = none_to_zero(out['quantity__sum'])
        return (avg, quantity)

post_save.connect(transaction_process,sender=VehicleTransaction)
pre_save.connect(auto_pricer,sender=VehicleTransaction)

class VehicleTransactionChoice(models.Model):
    """Object to track available vehicles for a VehicleTransaction for DCM.
    To access values: vt.vehicle_transaction_choices.all()"""
    vehicle_transaction = models.ForeignKey(VehicleTransaction,related_name="vehicle_transaction_choices")
    vehicle = models.ForeignKey(Vehicle)
    op_cost = models.IntegerField()
    selected = models.IntegerField(default=0)
    price = models.IntegerField()
    score = models.IntegerField()



class FuelTransaction(Transaction):
    """The base class for running a fuel transaction. Extends transaction with the\
        quantity field. Quantity is gals of gasoline equivalent i.e. gge."""

    quantity = models.IntegerField()
    market_share = models.FloatField(default=-1.0) # percentage of market for this FP on this turn.
    op_costs = models.FloatField(default=0.0) # how much it costs to run the refineries for this fuel for this fp.
    gross = models.FloatField(default=0.0) # the gross revenue related to the fuel, 'amount' is the net income.
    margin = models.FloatField(default=0.0) # stores the margin profits were calculated with
    fuel = models.CharField(max_length=20)

    def __unicode__(self):
        return str(
                "{0!s}  ${1!s} {2!s} gal.E. seller: {3!s} buyer: {4!s} desc: {5!s} account: {6!s}".format(self.fuel,
                                                                                                          self.amount,
                                                                                                          self.quantity,
                                                                                                          self.seller,
                                                                                                          self.buyer,
                                                                                                          self.desc,
                                                                                                          self.account)
                )

    def process(self):
        super(FuelTransaction, self).process()

post_save.connect(transaction_process,sender=FuelTransaction)
#
class VehicleModel(models.Model):
    producer = models.ForeignKey(AutopiaUser)
    drivetrain = models.ForeignKey(Drivetrain)
    mpg = models.FloatField()
    cost = models.IntegerField()
    turn = models.IntegerField()

    def __unicode__(self):
        return "VehicleModel __unicode__ stub"

    @classmethod
    def populate(cls, force=False, demo=False):
        """Fill in the vehicle models for the turn. This method should only be
            run once per turn. It should check before running."""

        # check to see if this has already been run for the turn.

        if force == True:
            cls.objects.filter(turn=Turn.cur_turn()).delete()

        # for all vehicle producers

        max = cls.objects.all().aggregate(Max('turn'))
        if max['turn__max'] == Turn.cur_turn():
            raise AssertionError("populate has already been run this turn\
                Set force=True to force another run.")

        vps = VehicleProducer.objects.all()
        dts = Drivetrain.objects.all()
        import copy

        if demo == True:
            raise ValueError("populate is in demo mode. Uncomment the block if you really want that. ")
            # remove this code !!!

        #            # advance all the levels by turn_length (4 years)
        #            print "Demo version of populate is running."
        #            for lev in VPDrivetrainLevel.objects.filter(turn=Turn.last_turn()):
        #                new_lev = copy.copy(lev)
        #                new_lev.turn = Turn.cur_turn()
        #                new_lev.level = new_lev.level+4
        #                new_lev.save()

        else: # this is the real version of populate using the RandD model
            for v in vps:
                # for each vp
                # collect all the info about the v from RandD table

                rd = {}

                for a in RandD.areas:
                    rd[a] = RandD.sum_area(a, **{'producer': v})

                # update the style and performance advance variables
                # for each vp here

                v.style_cost = v.base_style_cost - settings.STYLE_INC * rd['style']
                v.performance_cost = v.base_performance_cost - settings.PERFORMANCE_INC * rd['performance']
                v.save()

                for dt in dts:
                    fxn = get_level_fxn(dt.name)
                    lev = fxn(rd)
                    vpd = VPDrivetrainLevel(turn=Turn.cur_turn(), level=lev, producer=v, drivetrain=dt)
                    #id_check(vpd)
                    vpd.save()

                    fxn = get_vehicle_fxn(dt.name) # now we calculate the mpg and cost given the new levels
                    if lev == 0:
                        lev = 1 # so the fxn doesn't throw a zero error. This shouldn't happen in
                        # the course of a real game.
                    out = fxn(lev)
                    out['cost'] = int(out['cost'] / 10) * 10
                    out['mpg'] = round(out['mpg'], 0)
                    vm = VehicleModel(producer=v, drivetrain=dt, mpg=float(out['mpg']),
                                      cost=out['cost'], turn=Turn.cur_turn())
                    #id_check(vm)
                    vm.save()

                    # we are calculating the drivetrain level from the RandD table
                    # so we don't neen to copy the level info.

                    # for the d, look up the formula  to calculate the level


class VehicleModelInspectForm(forms.Form):
    id = forms.IntegerField()


class FleetManager(models.Manager):
    """FleetManager: Manager for the Fleet object"""

    def count_vehicles(self, **kwargs):
        """count_vehicles: returns a sum of the vehicle count as defined in **kwargs."""
        fleet = Fleet.objects.filter(**kwargs).aggregate(Sum('quantity'))
        return fleet['quantity__sum']

    def count_fuel_types(self, **kwargs):
        """Count the number of vehicles in the fleet by fuel type, or any set of kwargs."""
        o = Fleet.objects.filter(**kwargs).aggregate(Sum('quantity'))
        out = o.values()[0]
        if out == None:
            out = 0
        return out


    def average(self, *args, **kwargs):
        """Average value  arg[0] for some kwarg set. The sold value is automatically set to True unless sold=False is
        explicity. If you want all of the fleet's average attribute regardless of whehter it is sold or not set
        'all=True' as a kwarg. That will override the sold parameter."""
        if not kwargs.has_key("sold"):
            kwargs['sold'] = True

        if kwargs.has_key("all"):
            if kwargs['all'] == True:
                del(kwargs['sold'])

        val = "vehicle__" + args[0]
        o = Fleet.objects.filter(**kwargs).aggregate(Avg(val))
        out = o.values()[0]
        if out == None:
            out = 0
        return out




class Fleet(models.Model):
    vehicle = models.ForeignKey(Vehicle)
    owner = models.ForeignKey(AutopiaUser)
    quantity = models.IntegerField()
    turn = models.IntegerField()
    transaction = models.ForeignKey(VehicleTransaction)
    fuel = models.CharField(default="None", max_length=20)
    hev = models.BooleanField(default=False)
    phev = models.IntegerField(default=False)
    bev = models.BooleanField(default=False)
    sold = models.BooleanField(default=False)# has this vehicle been sold to a consumer
    points = models.FloatField(default=0) # I think this isn't used. Check.
    objects = FleetManager()

    @classmethod
    def distress_sale(cls):
        """This also handles disposal of vp fleet that is unsold."""
        try:
            fleet = cls.objects.filter(quantity__gt=0, sold=False)
        except IndexError:
            return

        for f in fleet:
            # look up vehicle


            # look up age
            # update the fleet row by multiplying agains VEHICLE_SURVIVAL[age]

            # done

            if Turn.cur_turn() == f.vehicle.turn + 1:
                # TODO: Test vehicle distress sale
                # this is a vps old stock. Need to distress sell it.

                # 1) sell the vehicles to admin at a disccount of settings.VEHICLE_DISTRESS_SALE
                vt = VehicleTransaction(buyer=uget("admin"), seller=f.owner, quantity=f.quantity,
                                        amount=float(
                                                f.vehicle.production_cost * settings.VEHICLE_DISTRESS_SALE * f.quantity) / 10 ** 6
                                        ,
                                        desc="Distress sale - %s" % (f.vehicle.name), account="distress",
                                        vehicle=f.vehicle, turn=Turn.cur_turn())
                f.sold = False
                f.save()
                vt.save()
                #vt.process()


    @classmethod
    def style_average(self):
        """Returns the style average for the consumers."""
        return Fleet.objects.average("style")


    @classmethod
    def performance_average(self):
        """Returns the performance average for all the consumers."""
        return Fleet.objects.average("performance")



    @classmethod
    def attrit(cls,penalty={}):
        """When turn advances attrit vehicles. An optional penalty dict can be
        sent. The penalty dict has the format { con_username_name: penalty_percent,...}.
        For a 5% penalty (additional attrition of 5%) of young: penalty=dict(young=5)."""
        expensive = Fuel.expensive()
        fleet = cls.objects.exclude(quantity=0).select_related()
        extra_attrit = {} # count vehicle that attrited due to penalty (-> high fuel prices)
        for f in fleet:
            # look up vehicle
            index = Turn.turn_diff(f.vehicle.turn) - 1 # first advance doesn't cause attrition
            # look up age
            # update the fleet row by multiplying agains VEHICLE_SURVIVAL[age]

            # done
            pre_attrit = f.quantity
            try:
                # this next line is clever. by multiplying by the inverse of the prior index (index-1)
                # it returns the original quantity  (100 * i * 1/i * i+1 = 100 * (i+1))
                f.quantity = float(f.quantity * (1.0 / settings.VEHICLE_SURVIVAL[max(index - 1, 0 )])) *\
                                   settings.VEHICLE_SURVIVAL[index]

            except (IndexError, ZeroDivisionError):
                print "Fleet.attrit IndexError. Seeting fleet quantity to 0."
                f.quantity = 0
            attrit = pre_attrit - f.quantity
            if penalty.has_key(f.owner.username) and (f.vehicle.drivetrain.fuel in expensive):
                # this is a pretty crude system. Should be more refined.
                pre = attrit
                delta = attrit * (1.0+(penalty[f.owner.username]+0.0)/100.0)
                attrit = min(pre-1.0, delta) # take at least one vehicle
                attrit = round(attrit,0)
                change = pre - attrit
                try:
                    extra_attrit[f.owner.username] += change
                except KeyError:
                    extra_attrit[f.owner.username] = change# number of vehs subject to penalty attrition.

            fa = FleetAttrition(fleet=f,quantity=attrit,turn=Turn.cur_turn())
            fa.save()
            f.quantity = int(f.quantity)
            super(Fleet, f).save() # using the super because the override adds to the fleet

        for con,val in extra_attrit.items():
            con = uget(con)
            income = round(val*con.base_car_cost*0.5/1000000.0,2)
            PlayPrompt.new(user=con,message="An additional %s cars were sold off due to high \
                                        fuel costs. Sales income of $%s M." % (round(val,0), income),
                                        code=PlayPrompt.codes['veh_dump'],priority=5)

            # give the con a bonus based on the number of cars he sold off
            tr = Transaction(buyer=uget("admin"),seller=con,amount=income, \
                        desc="Extra vehicles sold.", account="sales",turn=Turn.cur_turn())
            tr.save()
            #tr.process()

                            



    def __unicode__(self):
        return "Producer: %s Name: %s Owner: %s Quantity: %s Sold: %s Points: %s" % (
        self.vehicle.producer, self.vehicle.name,
        self.owner, self.quantity, self.sold, self.points)

    def count_attrit(self):
        """Return the sum of vehicle attrition for this vehicle."""
        sum = FleetAttrition.objects.filter(fleet=self).aggregate(Sum('quantity'))['quantity__sum']
        if sum == None:
            sum = 0
        return sum

    @classmethod
    def carpark_count(cls,drivetrain,turn=Turn.cur_turn()):
        """Count the carpark for 'drivetrain' through (inclusive) 'turn'. The 'drivetrain'
        can be sent as an object or as a name string."""

        fwargs = {}
        if not drivetrain.__class__()==Drivetrain():
            # drivetrain has been sent as a string
            drivetrain = Drivetrain.objects.get(name=drivetrain)

        fwargs['vehicle__drivetrain']=drivetrain
        fwargs['turn__lte']=turn
        fwargs['sold']=True

        bought = 0
        elim = 0
        for fleet in Fleet.objects.filter(**fwargs):
            veh = fleet.vehicle
            orig = VehicleTransaction.objects.filter(vehicle=veh, account="buy").aggregate(Sum('quantity'))['quantity__sum']
            orig = none_to_zero(orig)
            bought = bought+ orig

            attrit = FleetAttrition.objects.filter(fleet=fleet,turn__lte=turn).aggregate(Sum('quantity'))['quantity__sum']
            attrit = none_to_zero(attrit)
            elim = elim + attrit


        return bought - elim


    def test_attrition(self):
        """Run a test to make sure the Fleet.quantity is equal to the VehicleTransaction.quantity - Fleet.count_attrit."""

        vt_sum = VehicleTransaction.objects.filter(buyer=self.owner, vehicle=self.vehicle).aggregate(Sum('quantity'))['quantity__sum']
        fleet_val = vt_sum - self.count_attrit()
        if abs(fleet_val - self.quantity) < 7:
            return True
        else:
            print "Test failed. Fleet has a quanity of %s. The fleet_val is %s. " % (self.quantity, fleet_val)
            return False


    def save(self):
        """Overriding save to denormalize fuel. This saves a lot of SQL pain and
            should not hurt too much. First check to see if the owner already has the vehicle
            if so, just increase the quantity. THIS IS FOR ADDING VEHICLES ONLY. Call the super
            for attrit."""

        try:
            # updating existing fleet vehicle
            f = Fleet.objects.get(owner=self.owner, vehicle=self.vehicle)
            #f.quantity = f.quantity + int(self.quantity)
            super(Fleet, self).save()
        except Fleet.MultipleObjectsReturned:
            # happens during init
            super(Fleet, self).save()
        except Fleet.DoesNotExist:
            #  creating new fleet object entry
            self.fuel = self.vehicle.drivetrain.fuel
            self.hev = self.vehicle.drivetrain.hev
            self.phev = self.vehicle.drivetrain.phev
            self.bev = self.vehicle.drivetrain.bev
            super(Fleet, self).save()

    @classmethod
    def fleet_data(cls):
        """Return fleet data for display."""

        #all drivetrains

        out = {}
        out['quantity'] = []
        out['drivetrain'] = []
        out['years'] = []
        out['drivetrain_by_fuel'] = []
        out['fuel_labels'] = Fuel.fuel_names()


        # count by drivetrain
        for dt in Drivetrain.objects.all():
            q = cls.objects.count_fuel_types(vehicle__drivetrain=dt, sold=True)
            if q > 0:
                out['drivetrain'].append(str(dt.name) + "  ( " + str(q) + " )")

                out['quantity'].append(q)

        for turn in Turn.objects.all():
            # drivetrain counts by fuel
            tmp_list = []
            for f in Fuel.fuel_names():
                q = cls.objects.count_fuel_types(fuel=f, turn=turn.turn, sold=True)
                if q == None:
                    q = 0

                tmp_list.append(q)
            out['drivetrain_by_fuel'].append(tmp_list)
            out['years'].append(Turn.turn_to_year(turn.turn))

        out['vps'] = []
        out['vps_counts'] = []

        for vp in vpall():
            q = cls.objects.count_fuel_types(vehicle__producer=vp, sold=True)
            if q > 0:
                out['vps_counts'].append(q)
                out['vps'].append(str(vp.username) + " ( " + str(q) + " )")

        return out


class FleetSnapshot(models.Model):
    """This is the fleet table with a column snap_turn added that states which turn
    the snapshot was taken. It is used for data reconstruction."""

    fleet = models.ForeignKey(Fleet)
    drivetrain = models.CharField(max_length=40)
    snap_turn = models.IntegerField(null=True,blank=True)
    snap_quantity = models.IntegerField()

    @classmethod
    def process(cls):
        """Run all of the FleetSnapshot routines. Returns True."""
        cls.snap()
        for table in ['market_breakdown','drivetrain_breakdown','consumer_vehicle_counts']:
            cls.__tablefy_view(table)
        return True

    @classmethod
    def snap(cls):
        """Take a snapshot of the current Fleet table and add the snap_turn column to it
        to track the turn on which the snapshot was taken. Only do it for sold vehicles."""
        max_turn = FleetSnapshot.objects.all().aggregate(Max('snap_turn'))['snap_turn__max']
        if max_turn == Turn.cur_turn():
            raise ValueError("The snapshot has already been run for this turn. Quitting.")

        con = connection.cursor()
        for f in Fleet.objects.all():
            if f.sold==True:
                sql = "INSERT INTO app_fleetsnapshot (fleet_id, drivetrain, snap_turn, snap_quantity) " \
                    " VALUES (%s, %s, %s,%s)"
                con.execute(sql, [f.id,f.vehicle.drivetrain.name, Turn.last_turn(), f.quantity])
        con.close()
        return True



    @classmethod
    def report(cls,csv=False,start=3,db="default"):
        """Report on the snapshot, a fine lot of statistics . Send 'csv=True' for csv output.
        Send 'start=n' (int) to choose starting snap_turn. Default is 3. Set <db> to the name
        of the database for the report."""

        # monkey patching
        cons=Consumer.objects.using(db).all()
        out = {}

        max_snap = cls.objects.using(db).all().aggregate(Max('snap_turn'))['snap_turn__max']
        print "max_snap=%s" % max_snap
        for con in cons:
            out[con]={}
            for i in range(start,max_snap+1):
                out[con][i]={}
                out[con][i]['count']=[]
                out[con][i]['style']=[]
                out[con][i]['performance']=[]
                out[con][i]['mpg']=[]
                out[con][i]['price']=[]
        num = start
        attrs = ['style','performance','mpg','price']
        while num <= max_snap:
            for con in cons:
                rows = cls.objects.using(db).filter(fleet__owner=con,snap_turn=num)
                for row in rows:
                    try:
                        out[con][num]['total'] += row.snap_quantity
                    except KeyError:
                        out[con][num]['total'] = row.snap_quantity
                    for var in attrs:
                        out[con][num][var].append(getattr(row.fleet.vehicle,var))
                    out[con][num]['count'].append(row.snap_quantity)



            num += 1



        for i in range(start,max_snap+1):
            for con in cons:
                print "    %s \n" % con.username
                for var in attrs:
                    stat = sum(map(lambda x,y: x*y, out[con][i][var],out[con][i]['count']))/(out[con][i]['total']*1.0)
                    try:
                        out[con][var].append(round(stat,2))
                    except KeyError:
                        out[con][var]=[round(stat,2)]

        head = "consumer," + ",".join([str(4*i + 2000) for i in range(start,max_snap+1)]) + "\n"
        for attr in attrs:
            csv = head
            print "\n" + attr.capitalize()
            for con in cons:
                row = con.username + "," + ",".join([str(i) for i in out[con][attr]]) + "\n"
                csv += row
            print csv + "\n\n"

    @classmethod
    def __tablefy_view(cls, table):
        """Turn a view called <foo>_view into a table <foo>. Arg is table tname.
        This is done on turn_advance. Not web safe. INternal use only."""

        con = connection.cursor()
        sql = "DROP TABLE IF EXISTS %s;" % table
        con.execute(sql)
        sql = "CREATE TABLE %s as SELECT * from  %s_view;" % (table,table)
        con.execute(sql)
        con.close()
        return True






class FleetAttrition(models.Model):
    """Tracks what Fleet.attrit does so that drivetrain statistics can be published."""

    fleet=models.ForeignKey(Fleet)
    turn = models.IntegerField()
    quantity = models.FloatField()




class AddToFleetForm(forms.Form):
    quantity = forms.IntegerField()
    vehicle_id = forms.IntegerField()


class Fuel(models.Model):
    turn = models.IntegerField()
    cafe = models.FloatField()
    gas = models.FloatField(default=0)
    diesel = models.FloatField(default=0)
    elec = models.FloatField(default=0)
    h2 = models.FloatField(default=0)

    @classmethod
    def get_cafe(cls,*args,**kwargs):
        """Returns the CAFE for the turn. If a kwarg['turn'] value is sent it
        will use that as the turn."""
        if kwargs.has_key('turn'):
            turn = kwargs['turn']
        else:
            turn = Turn.cur_turn()
        year = Turn.turn_to_year(turn)
        try:
            max_year = max(filter(lambda x: x <= year, settings.CAFE_LEVELS.keys()))
            cafe=settings.CAFE_LEVELS[max_year]
        except ValueError: # empty array from filter fails max
            cafe = settings.CAFE_LEVELS[max(CAFE_LEVELS.keys())] # use the last one

        return cafe

    @classmethod
    def get_cafe_feebate(cls):
        """Return current CAFE as GPM (gallons per mile) for feebate. Uses Fuel.get_cafe."""
        return (1.0/cls.get_cafe())


    def save(self):
        o = Fuel.objects.filter(turn=self.turn)
        if o.count() > 0:
            print "Turn value already assigned."
            pass
        super(Fuel, self).save()

    #def __init__(self):
    #    self.i = self.fuel_turn_index() # fuel array index for current turn


    @classmethod
    def costs(cls):
        """Returns a dict of current fuel costs [ fuel: price ] ."""
        self = cls()
        costs = {"gas": self.gas_cost,
                 "diesel": self.diesel_cost,
                 "h2": self.h2_cost,
                 "bev": self.elec_cost
        }
        return costs

    @staticmethod
    def fuel_names():
        """Returns an array of fuel names."""
        return ["gas", "diesel", "h2", "elec"]

    @property
    def gas_cost(self):
        """Returns the preset price of gas for the current turn."""
        #return round(settings.GAS_COST[Fuel.fuel_turn_index()], 2)
        return Fuel.fuel_price_lookup('gas',Fuel.fuel_turn_index())

    @property
    def diesel_cost(self):
        """Returns the preset price of diesel for the current turn."""
        #return round(settings.DIESEL_COST[Fuel.fuel_turn_index()], 2)
        return Fuel.fuel_price_lookup('diesel',Fuel.fuel_turn_index())

    @property
    def h2_cost(self):
        """Returns the preset price of h2 for the current turn."""
#        return round(settings.H2_COST[Fuel.fuel_turn_index()], 2)
        return Fuel.fuel_price_lookup('h2',Fuel.fuel_turn_index())

    @property
    def elec_cost(self):
        """Returns the preset price of electricity for the current turn."""
        #return round(settings.ELEC_COST[Fuel.fuel_turn_index()], 2)
        return Fuel.fuel_price_lookup('elec',Fuel.fuel_turn_index())


    @classmethod
    def fuel_price_lookup(cls, fuel, turn):
        """Return the price of fuel f on turn n."""
        if fuel == "bev":
            fuel = "elec"
	turn += 0.0
        string = "settings." + fuel.upper() + "_COST[" + str(turn) + "]"
        try:
            out = eval(string)

        except IndexError:
            return "Index(turn) out of range."
        except TypeError:
            # this is a function form, in theory.
            string = string.replace("[","([")
            string = string.replace("]","])")
            if fuel.upper()=="H2":
                # this is the special case to handle hytrans comparison!
                # WARING!!! SPECIAL CASE CODE!!! hehe
                gas_cars = (Fleet.carpark_count("gas") + 1) # prevent 0
                h2_cars =  (Fleet.carpark_count("h2"))
                if h2_cars > gas_cars:
                    h2_cars = gas_cars
                #string=string.replace(str(turn), str(turn)+",%s,%s" % (gas_cars,h2_cars))
                string = "settings.H2_COST([%s,%s,%s])" % (str(turn),gas_cars,h2_cars)
            print string
            out = eval(string)
        return round(out, 2)

    @classmethod
    def expensive(cls):
        """Return an array of the names of the expensive fuels based on relative
        ratios of the prices."""

        costs=cls.costs()
        total = sum(costs.values())
        out=[]

        for fuel,cost in costs.items():

            if (cost/total - 0.20) > 0 and not fuel=="bev":
                out.append(fuel)
                # higher standard for bev
            elif (cost/total - 0.45) > 0 and fuel =="bev":
                out.append(fuel)

        print out
        return out



            



    @classmethod
    def buy_fuels(cls):
        """Do the fuel buys for the consumers for all fuels. Part of the Turn.advance_turn()\"""
            sequence."""
        # Calculate fuel usage for all fuels (gas, diesel, h2 and electricity)
        # and charge players for the fuel used.
        # This is simple except for the phevs. Phevs must be charged
        # for gge of tank stored fuel and also a premium for the electricity
        # used.


        # Fuels are bought based on VMT. VMT is calculated on a yearly basis.

        # Are refineries producing per year or per turn?

        fuel_account = AutopiaUser.objects.get(username="gas_account")
        dict = {} # keys are consumer usernames - vehicle_stats are stored here
        demand = {} # keys are fuel names - sum of demand for each fuel

        stationary = 0 # stationary elec demand

        for con in Consumer.objects.all():
            stats = con.vehicle_stats()

            for val in ('gas_gals', 'diesel_gals', 'h2_gals', 'bev_gals'):
                str = re.sub("_gals$", "", val)
                if str == "bev":
                    str = "elec"
                try:
                    demand[str] = demand[str] + stats[val]
                except KeyError: # first time through throws KeyError
                    demand[str] = stats[val]

            st = con.stationary_elec()
            stationary = stationary + st
            demand['elec'] = demand['elec'] + stats['phev_elec'] + st

            dict[con.username] = stats

        supply = {}
        for fp in FuelProducer.objects.all():
            # calculate the sum of what fuel producers are putting online
            for f in Fuel.fuel_names():
                try:
                    supply[f] = fp.get_active_cap(f) + supply[f]
                except KeyError:
                    supply[f] = fp.get_active_cap(f) + 0.0

        shares = {} # percentage of market for each fp
        for f in Fuel.fuel_names():
            shares[f] = {}
            for fp in FuelProducer.objects.all():
                try:
                    shares[f][fp.username] = fp.get_active_cap(f) / supply[f]
                except ZeroDivisionError:
                    shares[f][fp.username] = 0

        prices = {}
        # I think the supply is calculated on a per turn basis and the
        # demand is calculated on a per year basis.

        for f in Fuel.fuel_names():
            # we have supply, demand, and fuel. Let's get the actual price
            prices[f] = Fuel.actual_price(supply[f], demand[f], fuel=f)
            fr = FuelRecord(turn=Turn.cur_turn(), fuel=f, supply=supply[f], demand=demand[f],
                            base_price=Fuel.fuel_price_lookup(f, Turn.cur_turn()),
                            actual_price=prices[f], capacity=FuelProducer.market_cap(f))

            fr.save()
            for fp in FuelProducer.objects.all():
                # sell their market shares to the admin for this f (fuel)

                try:
                    ratio = supply[f] / demand[f]
                except ZeroDivisionError:
                    ratio = 0

                share = shares[f][fp.username]
                op_costs = fp.get_op_cost(f) / 10.0 ** 3
                if demand[f]==0:
                    revenue = 0
                    quantity = 0
                elif ratio >= 1:
                    # supply is higher than demand - FP's supply all fuel
                    revenue = share * prices[f] * demand[f]
                    quantity = share * demand[f]
                else:
                    # supply is lower than demand - outside suppliers enter the game
                    # FP's only supply 'supply'
                    revenue = share * prices[f] * supply[f]
                    quantity = share * supply[f]

                profit = revenue * fp.get_margin(f)
                amount = profit / 10.0 ** 6 - op_costs
                ft = FuelTransaction(buyer=uget("admin"), seller=fp, fuel=f, amount=amount,
                                     quantity=quantity, account="Fuel Profit",
                                     margin=fp.get_margin(f),
                                     market_share=share,
                                     turn=Turn.cur_turn(),
                                     gross=profit / 10.0 ** 6,
                                     op_costs=op_costs,
                                     desc="Profits - Op. Costs")
                ft.save()
                ft.process()
                # the fuel producers have been paid. Now charge the consumers.




        # now we charge teh consumers.
        # The consumers pay for their demand times the actual price of the fuel
        for key in dict.keys():
            # key is con.username
            prompt = None # the playprompt - track if used so it isn't repeated
            stats = dict[key]

            con = uget(key)
            # buy phev electricity


            elec = stats['phev_elec'] # gge of electricity bought by consumer for phevs.

            try:
                cost = round(float(elec * prices['elec']) / 10 ** 6, 2)

                quantity = elec
            except TypeError:
                cost = 0
                quantity = 0

            # adding a no-debt constraint on consumer fuel purchase.
            # consumer can only spend money he has. 1/16/11

            # REMOVED THE NO-DEBT constratint 3/3/11. This was a bad idea!!!
            #if cost > con.balance:
            #    cost = con.balance
            f = FuelTransaction(buyer=con, seller=uget("admin"), fuel="bev",
                                amount=cost, account="Consumer Fuel Purchase", turn=Turn.cur_turn(), quantity=quantity,
                                desc="phev electricity")

            f.save()
            f.process()
            for val in ('gas_gals', 'diesel_gals', 'h2_gals', 'bev_gals'):
                fuel = re.sub("_gals$", "", val)

                if fuel == "bev":
                    fuel = "elec"
                    #

                try:
                    cost = float(stats[val] * prices[fuel]) / 10 ** 6

                    quantity = stats[val]
                except TypeError:
                    cost = 0
                    quantity = 0

                # adding a no-debt constraint on consumer fuel purchase.
                # consumer can only spend money he has. 1/16/11

                # Removed it.
                if cost > con.balance:
                    prompt = PlayPrompt.new(con,"You're spending too much on fuel. You have a negative balance.",
                                            code=PlayPrompt.codes['fuel_overspend'])

                f = FuelTransaction(buyer=con, seller=fuel_account, fuel=fuel,
                                    amount=cost, account="fuel", turn=Turn.cur_turn(), quantity=quantity)
                f.save()
                f.process()

                #do a Fuel transaction here. If value is NA do a 0 transaction
                # for the fuel so it can be tracked.

                # Make sure to use next turns price.

    @classmethod
    def base_price(self, fuel, turn=None):
        """Returns the base set price for 'fuel'. This is the seed price that is used by 'actual_price'."""
        if turn == None:
            turn = Turn.cur_turn()

        return Fuel.fuel_price_lookup(fuel,turn)

#        if fuel == "bev":
#            fuel = "elec"
#        string = "settings." + fuel.upper() + "_COST[" + str(turn) + "]"
#        try:
#            out = eval(string)
#
#        except IndexError:
#            return "Index(turn) out of range."
#
#        else:
#            return round(out, 2)


    @classmethod
    def actual_price(cls, supply, demand, P=None, e=settings.ELASTICITY, fuel=None):
        """Take the seed price for the fuel (str), supply(int), demand(int), elasticity(float) and return
            the computed price (float)."""

        if P == None and fuel == None:
            raise Exception("P and fuel are both set to None. Not allowed.")

        if P == None:
            P = Fuel.base_price(fuel)
        if demand == 0 or not settings.FUEL_MARKET:
            out = P
        else:
            try:
                out = P * (1 + e * ((demand / supply) - 1))
            except ZeroDivisionError:
                out = P * P # square the base price if there is no supply

        return out


    @classmethod
    def fuel_turn_index(self):
        """Returns the array into the fuel index for getting the fuel price for the turn."""
        return Turn.cur_turn() + settings.FUEL_BACK_HISTORY - 1

    @classmethod
    def elec_market_data(cls):
        """Returns data for a line graph on electricity usage. The lines are: market capacity, active market capacity
        and usage. These are in order by level (descending). """

        dict = {}
        dict['data'] = []
        dict['labels'] = []
        dict['legend'] = ['Total Cap.', 'Active Cap.', 'Demand']

        for rec in FuelRecord.objects.filter(fuel="elec").exclude(turn=Turn.cur_turn()).order_by('turn'):
            tmp_list = []

            if rec.supply == rec.capacity:
                rec.supply = rec.supply * 0.98
            tmp_list.append((rec.capacity + 0.0) / 10 ** 3)
            tmp_list.append((rec.supply + 0.0) / 10 ** 3)
            tmp_list.append((rec.demand + 0.0) / 10 ** 3)
            yr = Turn.short_year(rec.turn)
            dict['labels'].append(yr)
            dict['data'].append(tmp_list)

        return dict


    @classmethod
    def fuel_market_data(cls):
        """Returns a fuel data volume string as 'data' attr for jqBarGraph. Format is: [[gas,diesel,h2,elec],year],...
       for all years, where gas,diesel,h2, elec are volumes of fuel purchased that year.  Also returns
       a legend attr ."""
        dict = {}
        dict['data'] = []
        dict['cost'] = []
        dict['labels'] = []
        dict['price'] = []
        dict['legend'] = ['gas', 'diesel', 'h2', 'elec.']
        max = Turn.objects.all().aggregate(Max('turn'))['turn__max'] #don't read for the current turn

        for turn in Turn.objects.filter(turn__lt=max):
            tmp_list = []
            cost_list = []
            price_list = []
            for fuel in ['gas', 'diesel', 'h2', 'elec']:
                try:
                    out = FuelTransaction.objects.filter(turn=turn.turn, fuel=fuel).aggregate(Sum('quantity'),
                                                                                              Sum('amount'))
                    quant = out['quantity__sum'] / 1000
                    cost = out['amount__sum'] * 1000# / 1000
                    price = FuelRecord.last(fuel, turn=turn.turn)
                    #price = .fuel_price_lookup(fuel,turn.turn)

                except (FuelTransaction.DoesNotExist, TypeError, ZeroDivisionError):
                    quant = 0
                    cost = 0
                    pr
                tmp_list.append(quant)
                cost_list.append(cost)
                price_list.append(price)
            yr = Turn.short_year(turn.turn)
            dict['labels'].append(yr)
            dict['data'].append(tmp_list)
            dict['cost'].append(cost_list)
            dict['price'].append(price_list)

        dict['long_labels'] = dict['labels']
        dict['long_labels'].append(
                Turn.cur_year()) # long labels is used for price history to incorporate the current turn data
        return dict


class RandD(models.Model):
    """This model tracks the R&D level for 7 attributes (gas, diesel,
        h2, bev, road_load, performance and style, for each VP across turns."""

    producer = models.ForeignKey(VehicleProducer, default=-1)
    turn = models.IntegerField(default=-1)
    gas = models.IntegerField(default=0)
    diesel = models.IntegerField(default=0)
    h2 = models.IntegerField(default=0)
    bev = models.IntegerField(default=0)
    road_load = models.IntegerField(default=0)
    performance = models.IntegerField(default=0)
    style = models.IntegerField(default=0)
    hev = models.IntegerField(default=0)

    areas = ['gas', 'diesel', 'h2', 'bev', 'style','performance','road_load','hev']


    @classmethod
    def automatic_rd(cls):
        """Assign automatic rd for computer players.
        """
        for vp in vpall():
            # did the vp make an RandD entry this turn, if not do it for him
            try:
                rd = RandD.objects.filter(producer=vp, turn=Turn.cur_turn())
                print "Randomly assigning %s RD points." % vp.rd_points
                if vp.username in settings.COMPUTER: #
                    rdp = vp.rd_points
                    while rdp > 0:
                        num = random.randint(1,rdp)
                        if num > 5: num = 5
                        rdp -= num
                        key = density_hash(settings.VP_RD[vp.username])
                        kwargs = {'producer':vp,key:num}
                        print "kwargs: %s " % kwargs
                        rd = RandD(**kwargs)
                        rd.save()
                        vp.rd_points -= num
                        vp.save()

            except RandD.DoesNotExist:

                logging.debug("vp: %s did not do an rd allocation this turn. " % vp.username)
                rd = RandD(turn=Turn.cur_turn(), producer=vp)
                rd.save()
            logging.debug("running dumb rd assignment. Replace with better system.")
        return True

    @classmethod
    def sum_area(cls, *args, **kwargs):
        """Provides the sum of the given RD area across all turns.
            Args: 1st argument is the area name (from RandD.areas), second arg
            is producer in a dict {'producer':<vp object>} e.g.
            r.sum_area('gas',{'producer':vp1})."""
        out = cls.objects.filter(**kwargs).aggregate(Sum(args[0]))
        val = args[0] + "__sum"
        if out[val] == None:
            out[val] = 0
        return out[val]




class RandDForm(forms.Form):
    """Enter R and D points for the vehicle producer."""
    producer = forms.IntegerField(required=False)
    turn = forms.IntegerField()
    gas = forms.IntegerField()
    diesel = forms.IntegerField()
    h2 = forms.IntegerField()
    bev = forms.IntegerField()
    road_load = forms.IntegerField()
    performance = forms.IntegerField()
    style = forms.IntegerField()
    hev = forms.IntegerField()
    points = forms.IntegerField()

    class Meta:
        model = RandD

class Comment(models.Model):
    """Enter a comment about the game with this object."""
    comment = models.CharField(max_length=2048)
    user = models.ForeignKey(AutopiaUser)
    turn = models.IntegerField(default=0)
    date = models.DateField(auto_now=True)


class CommentForm(forms.Form):
    """The form for the Comment object."""
    comment = forms.CharField(max_length=2048)

    class Meta:
        model = Comment


class Email(models.Model):
    """Enter a comment about the game with this object."""
    email = models.EmailField()
    user = models.ForeignKey(AutopiaUser, related_name="user_for_email")
    date = models.DateField(auto_now=True)


class EmailForm(forms.Form):
    """The form for the Comment object."""
    email = forms.CharField(max_length=75)

    class Meta:
        model = Email

class RefineryModel(models.Model):
    """This object describes the refineries available for purchase by the FP."""
    RM_SIZES = ((1, "micro"), (2, "small"), (3, "medium"), (4, "large"))

    size = models.IntegerField(max_length=1, choices=RM_SIZES) # micro, small, medium ,large
    fuel = models.CharField(max_length=30) # gas, diesel, elec, h2
    capacity = models.IntegerField()       # '000s of gge
    base_cost = models.IntegerField()           # $ '000
    build_time = models.IntegerField()     # number of turns it takes to build (1=next turn...)
    margin = models.FloatField()           # percent return on fuel from this refinery
    active_cost = models.FloatField()    # $'000's to activate plant for a turn
    inactive_cost = models.FloatField()  # $'000 to keep plant mothballed for a turn
    elim_cost = models.FloatField()      # cost to eliminate plant

    # to see size name:
    # a = RefineryModel.objects.get(...)
    # name = a.get_size_display()

    def payback(self, user):
        """Payback time in years based on best case scenario. Includes operating costs."""
        num = self.get_cost(user) + 0.0
        den = Fuel.fuel_price_lookup(self.fuel, Turn.last_turn()) * self.margin * self.capacity - self.active_cost + 0.0
        try:
            out = (num / den) * settings.YEAR_TURN_LEN + self.build_time
            out = int(out)
        except:
            out = "NA"
        return out

    def total_payback_turns(self,user):
        """Return payback time (in operation) + build time in turns."""
        out=self.payback(user)/4.0 + self.build_time
        return(round(out,2))


    @property
    def name(self):
        """Returns the display name for the object size attribute."""
        return self.get_size_display()

    def get_cost(self, user):
        """Get the cost of building a refinery of type self for user -user-."""
        n = Asset.objects.filter(builder=user, activation_turn__lte=Turn.cur_turn()).aggregate(Sum('refinery__size'))[
            'refinery__size__sum']
        if n == None:
            n = 0
        return self.base_cost + int((1.0 / (n + 1.0)) * (self.base_cost + 0.0))

    def create_refinery_for(self, user, turn=0):
        """Build a refinery of type self for user with an activation turn of 'turn'. This is an admin
        tool, not intended for real play."""
        a = Asset(refinery=self, status_code=1,
                  activation_turn=turn,
                  owner=user,
                  builder=user)
        # create the Asset!
        a.save()
        amount = round((self.get_cost(user) + 0.0) / 10.0 ** 3, 3)
        tr = AssetTransaction(asset=a, buyer=user, seller=uget("admin"),
                              amount=amount, turn=Turn.cur_turn(),
                              comment="Build Refinery",
                              account="build refinery")
        tr.save()
        tr.process()
        return a

    def __unicode__(self):
        return "%s %s (%s k gge/turn) cost: %s" % (self.name,self.fuel,self.capacity,self.base_cost)

class Asset(models.Model):
    """Tracking object for FP refinery ownership."""

    STATUS_CHOICES = ( (2, "active"), (1, "inactive"), (0, "eliminated") )

    refinery = models.ForeignKey(RefineryModel, related_name="refinery_model")
    status_code = models.IntegerField(max_length=1, choices=STATUS_CHOICES)
    activation_turn = models.IntegerField(default=-10)#start base set all activated
    for_sale = models.BooleanField(default=False)
    sale_price = models.IntegerField(default=0)
    owner = models.ForeignKey(AutopiaUser, related_name="autopia_user")
    builder = models.ForeignKey(AutopiaUser, related_name="autopia_user_builder")
    replaced= models.BooleanField(default=False)

    @classmethod
    def capacity_data(cls):
        """Returns data for asset capacity plot."""
        min_turn = Turn.objects.all().aggregate(Min('turn'))['turn__min']
        max_turn = max(Asset.objects.all().aggregate(Max('activation_turn'))['activation_turn__max'],Turn.cur_turn())
        max_turn += settings.REFINERY_LIFE
        data={'turn':[],'gas':[],'diesel':[],'h2':[],'elec':[]}
        data['turn']=[i for i in range(min_turn,max_turn+1)]
        for turn in range(min_turn,max_turn+1):
            for fuel in Fuel.fuel_names():
                if turn < Turn.cur_turn():
                    cap = FuelRecord.objects.get(fuel=fuel,turn=turn).capacity
                    data[fuel].append(cap)
                    # look up the capacity in the fuel record
                elif turn == Turn.cur_turn():
                    # calculate active cls.objects
                    cap_cur = cls.objects.filter(status_code__in=[1,2],refinery__fuel=fuel).aggregate(Sum('refinery__capacity'))['refinery__capacity__sum']

                    cap_cur=none_to_zero(cap_cur)
                    data[fuel].append(cap_cur*4000)
                    #data[fuel].append(.filter)
                elif turn > Turn.cur_turn(): # turn is greater than cur_turn
                    cap = 0
                    for asset in Asset.objects.filter(activation_turn__lte=turn,refinery__fuel=fuel,status_code__in=[1,2]):
                        if not asset.attrit_test(turn):
                            # if asset not attrited on turn n then
                            cap += asset.refinery.capacity
                    data[fuel].append(cap*4000)

                    # check for assets activated on turn <turn> and add them up.
        return data

    @classmethod
    def plot_capacity(cls):
        """Make a refinery capacity plot using pygooglechart. Returns an url."""
        data = cls.capacity_data()
        years = [ Turn.short_year(x) for x in data['turn'] ]
        max_val = max([max(x) for x in [data[key] for key in data.keys()]])
        # above will use data['turn'] but data turn is so small that it will not
        # matter
        chart=SimpleLineChart(600,300,y_range=(0,max_val))
        chart.set_axis_labels(Axis.BOTTOM,years)
        chart.set_title("Combined Fuel Producer Capacity Chart (as of %s)" % Turn.turn_to_year(Turn.last_turn()))
        chart.set_legend(Fuel.fuel_names())
        chart.set_axis_labels(Axis.LEFT,[int((i/10.0)*(max_val/1000) ) for i in range(0,11)])
        chart.set_colours(["FF0000","00FF00","0000FF","AAAA00"])
        for fuel in Fuel.fuel_names():
            chart.add_data(data[fuel])

        return chart.get_url()


    @property
    def status(self):
        """Returns the descriptor string attached to the status code."""
        return self.get_status_code_display()


    @classmethod
    def capacity(self, **kwargs):
        """Return the summed capacity for the current_turn based on kwargs. Typical kwargs={owner:FP,fuel:foo}."""
        return False

    @property
    def is_oil_plant(self):
        """Is the asset a gas or diesel plant? Returns boolean"""
        if self.refinery.fuel == "gas" or self.refinery.fuel == "diesel":
            return True
        else:
            return False

    @property
    def cost(self):
        """Returns the price paid for the asset."""
        try:
            out = AssetTransaction.objects.filter(asset=self).order_by('-id')[0]
            out = int(float(out.amount) * 1000.0)
        except IndexError:
            out = "NA"
        return out

    def convert_to_gas(self):
        """Convert a diesel refinery to gas."""
        return False


    def convert_to_diesel(self):
        """Convert a gas refinery to diesel."""
        return False

    def activate(self):
        """Activate a deactivated asset for next turn. Make the change in the asset table.
        This only works if the asset is inactive, it cannot bring back an eliminated asset."""

        if self.status_code == 1:
            self.status_code = 2
            self.save()
        return True

    def deactivate(self):
        """Deactivate an activated asset for next turn. Make the change in the asset table."""
        if self.status_code == 2:
            self.status_code = 1
            self.save()
        return True

    def eliminate(self):
        """Eliminate an asset from the game. Changes status_code to 0."""
        self.status_code = 0
        self.save()
        return True

    def attrit_test(self, turn=Turn.cur_turn()):
        """The test to see whether a refinery is attrited. Returns Bool. True if refinery
        is to be eliminated. False otherwise."""
        #print "turn %s - activation_turn %s - diff %s" % (turn, self.activation_turn, (turn - self.activation_turn))
        return ((turn - self.activation_turn) > settings.REFINERY_LIFE)

    @classmethod
    def attrit(cls,attrit=settings.ATTRIT_REFINERIES):
        """Eliminate refineries that are older than settings.REFINERY_LIFE. The
        attrit arg can be set to true or false."""
        for ref in Asset.objects.all():
            if ref.attrit_test(Turn.cur_turn()):
                ref.eliminate()

    def __unicode__(self):
        return self.refinery.name


class AssetTransaction(Transaction):
    """Transfer an asset(refinery) from a seller to a buyer."""

    asset = models.ForeignKey(Asset)

    def __unicode__(self):
        return str("holder")


    def process(self, *args, **kwargs):
        """Transfers the asset from the seller to the buyer."""
        if self.status=="completed":
            return True
        o = self.asset
        o.owner = self.buyer
        o.for_sale = False
        o.save()
        super(AssetTransaction, self).process()
        # do fee transaction

post_save.connect(transaction_process,sender=AssetTransaction)

class FuelRecord(models.Model):
    """Stores GLOBAL information on fuel prices, sales volume and demand."""

    # I think op_costs and profit are not used.
    fuel = models.CharField(max_length=40)
    turn = models.IntegerField()
    demand = models.IntegerField()
    capacity = models.IntegerField(default=0) # total capacity for the fuel
    supply = models.IntegerField() # active capacity for the fuel
    base_price = models.FloatField() # the seeded value
    actual_price = models.FloatField() # price after supply and demand are taken into account

    @classmethod
    def revenue_data(cls):
        """Data to compare actual revenue to theoretical max revenue. For plotting."""
        if settings.ELASTICITY > 1:
            raise ValueError("revenue_data method is only sensible for settings.ELASTICITY <=1")
        data = {'data':[]}
        for val in Fuel.fuel_names():
            data[val]=[]
        for fuel in Fuel.fuel_names():
            # value is difference between theoretical max and actual demand
            for turn in range(1,Turn.cur_turn()):
                rec = cls.objects.get(fuel=fuel,turn=turn)
                try:
                    val = round((min(rec.supply,rec.demand) * rec.actual_price * 100.0)/(rec.demand * rec.base_price * 1.0),1)
                except ZeroDivisionError:
                    val = 0

                data[fuel].append(val)
        return data

    @classmethod
    def short_plot_price_data(cls):
        """No arg version of plot_price_data for home."""
        return cls.plot_price_data(min_turn=Turn.cur_turn()-3)

    @classmethod
    def plot_price_data(cls,min_turn=1,max_turn=Turn.last_turn()):
        """Plot fuel volume data from <min_turn> (default=1) to <max_turn> (default=last_turn).
        """

        fd = {}
        for fuel in Fuel.fuel_names():
            fd[fuel]=[]
        for fuel in Fuel.fuel_names():
            vals = cls.objects.filter(turn__lte=max_turn,turn__gte=min_turn, fuel=fuel)
            for val in vals:
                fd[fuel].append(val.actual_price)
        flist=[]
        for fuel in Fuel.fuel_names(): flist.extend(fd[fuel])
        chart=SimpleLineChart(200,150,y_range=[min(flist)-1,max(flist)+1])
        chart.set_legend(Fuel.fuel_names())
        chart.set_colours(['FF0000','00FF00','0000FF','AAAA00'])
        chart.set_title("Fuel Prices")
        for fuel in Fuel.fuel_names():
            chart.add_data(fd[fuel])
        years = [ Turn.turn_to_year(x) for x in range(min_turn,Turn.cur_turn()) ]
        chart.set_axis_labels(Axis.BOTTOM,years)
        chart.set_axis_labels(Axis.LEFT,range(min(flist)-1,max(flist)+1,2))
        return chart.get_url()


    @classmethod
    def plot_revenue_data(cls):
        """Revenue % attained data plotter. Uses pygooglechart. """
        data = cls.revenue_data()
        years = [ Turn.short_year(x) for x in range(1,Turn.cur_turn()) ]
        chart = SimpleLineChart(400,200,y_range=(0,100))
        chart.set_title("Revenue Maximization by Fuel Producers (%)")
        chart.set_axis_labels(Axis.LEFT,[int((i/10.0)*(100.0) ) for i in range(0,11)])
        chart.set_axis_labels(Axis.BOTTOM,years)
        chart.set_legend(Fuel.fuel_names())
        chart.set_colours(['FF0000','00FF00','0000FF','AAAA00'])
        chart.fill_solid(Chart.BACKGROUND, 'EEEEEE')
        for key in Fuel.fuel_names():
           chart.add_data(data[key])

        return chart.get_url()






    @classmethod
    def last(cls, fuel, turn=None):
        """Returns the actual price of 'fuel' on the last turn no turn is sent as an arg.
        If a turn is sent, gets the turn price for 'fuel'. This is bad method name. """

        if turn == None:
            turn = Turn.last_turn()

        if fuel == "bev":
            fuel = "elec"

        try:
            out = cls.objects.get(fuel=fuel, turn=turn)
            retval = out.actual_price
        except FuelRecord.DoesNotExist, e:
            logging.debug("Error -- %s\n turn: l: %s %s" % (e, turn, fuel))
            retval = 0

        return retval

    @classmethod
    def plot_data(cls, start_index =1):
        """Returns dict with fuelrecord data for plotting. Dict has
        format { <fuel>: { 'demand': [ demand vol]; 'supply': [supply vol]
        'capacity':[capacity vol] }, ...}. The arg start_index is the turn
        number to start the data at. Default is 1. """

        out = {}
        out['start_index']=start_index
        for fuel in Fuel.fuel_names():
            out[fuel]={'capacity':[],'demand':[],'supply':[]}
            data = FuelRecord.objects.filter(turn__gte=start_index,fuel=fuel).order_by(*['turn'])
            for row in data:
                for attr in ['capacity','demand','supply']:
                    out[fuel][attr].append(getattr(row,attr))

        return out

    @classmethod
    def fuel_volume_charts(cls):
        """Prepare the pyggoogle charts for display. These are of fuel capacity, demand and supply.
        Returns a dict with a key for each fuel that is google chart url."""

        data = cls.plot_data()
        years = [ Turn.short_year(x) for x in range(data['start_index'],Turn.cur_turn()) ]
        o ={}
        attrs = ['capacity','demand','supply']
        for key in Fuel.fuel_names():
            max_val = round(max([max(x) for x in [ data[key][y] for y in attrs]]),0)
            chart=SimpleLineChart(300,300,y_range=(0,max_val))

            for attr in attrs:
                chart.add_data(data[key][attr])
            chart.set_title("%s Market ('000s GGEs)" %  key.title())
            chart.set_axis_labels(Axis.BOTTOM,years)

            chart.set_axis_labels(Axis.LEFT,[int((i/10.0)*(max_val/1000) ) for i in range(0,11)])
            chart.set_legend(attrs)
            chart.set_colours(['FF0000','00FF00','0000FF'])

            o[key] = chart.get_url()
        
        return o


class VPSalesSummary(models.Model):
    """A summary table of info about vehicles sold by the VP."""

    vehicle = models.ForeignKey(Vehicle)
    sold = models.IntegerField(default=0)
    turn = models.IntegerField(default=0)
    unsold = models.IntegerField(default=0)
    build_cost = models.FloatField(default=0.0)
    sales = models.FloatField(default=0.0)
    buyer = models.CharField(max_length=250) # a json string of the hash {consumer:quantity,...}

    @property
    def profit(self):
        """Difference between sales and costs."""
        return self.sales - self.build_cost

    @property
    def avg_sold_price(self):
        """Returns average price of a <sold> vehicle, i.e. num sold/sales. Rounded to 100s.
        """
        print vars(self)
        try:
            return  (self.sales * 10.0**6) / self.sold
        except ZeroDivisionError:
            return 0

    @property
    def percent_return(self):
        """Returns percent return on the vehicle in % form (i.e. 3.6
        not 0.36)."""
        try:
            out = round(self.sales * 100.0/self.build_cost,1)-100.0
        except ZeroDivisionError:
            out = -111
        return out

    @property
    def produced(self):
        """The total number of the vehicle produced."""
        return self.sold + self.unsold

    @classmethod
    def aggregate(cls):
        """Print aggregate stats in csv format."""
        print "Turn,sold,MPG,Performance,Style,Price"
        start = VPSalesSummary.objects.all().aggregate(Min('turn'))['turn__min']
        end = VPSalesSummary.objects.all().aggregate(Max('turn'))['turn__max']
        end += 1
        for turn in range(start,end):
            sums = {}
            for attr in ['mpg','performance','style','price']:
                sums[attr]=0
            sum = cls.objects.filter(turn=turn).aggregate(Sum('sold'))['sold__sum']
            for veh in cls.objects.filter(turn=turn):
                for attr in ['mpg','performance','style','price']:
                    sums[attr] += round(float(veh.sold * getattr(veh.vehicle,attr)) / (sum+0.0),3)
            print "%s,%s,%s,%s,%s,%s" % (turn,sum,sums['mpg'],sums['performance'],sums['style'],sums['price'])

    @classmethod
    def price_plot(cls,turn=Turn.last_turn(),bins=[x*5 for x in range(0,40)]):
        """Make a price plot histogram for turn <turn> with bins [] <bins>.
        <bins> are in thousands. Returns google chart url. """
        # make a list of bin boundaries for sorting
        if turn==2:
            bins=[0,10,20,30,40,50,60]
        alt_bins=map(lambda x,y: (x+y)/2, bins[0:(len(bins)-2)],bins[1:(len(bins)-1)])
        vpss = cls.objects.filter(turn=turn)
        data = {}
        for vps in vpss:
            for i in range(0,len(alt_bins)):
                if vps.avg_sold_price/1000 < alt_bins[i] and vps.sold > 0:
                    try:
                        data[i] += vps.sold
                    except KeyError:
                        data[i] = vps.sold
                    break
                elif vps.avg_sold_price/1000 > max(bins):
                    try:
                        data[10000] += vps.sold
                    except KeyError:
                        data[10000] = vps.sold
                    break

        # push the overage in to the last bin
        try:
            tmp = data[10000]
            del data[10000]
            data[max(data.keys())] += tmp

        except KeyError:
            pass

#        print  "sum(data) = %s" % sum(data)
#        if sum(data) > 0:
#            # collapse the data set to get rid of 0 entries
#            zeroes = data.count(0)
#            for z in range(0,zeroes):
#                i = data.index(0)
#                del(data[i])
#                del(bins[i])
#            try:
#                percents = [ 100.0 * d/sum(data) for d in data]
#            except ZeroDivisonError:
#                percents = [0 for d in data]
#        else:
#            percents = [0 for d in data]
        arr =  [(k,data[k]) for k in data.keys()]
        arr = sorted(arr,key = lambda x: x[0])
        vals = [x[1] for x in arr]
        keys = [x[0] for x in arr]
        percents = [100.0 *d/sum(vals) for d in vals]
        if 10000 in keys:
            print "Overrrun - fix this!!"
        bins = [bins[d] for d in keys] # select the bins that have non-zero data

        out = {}
        out['price_dist_data']=[[p] for p in percents]
        try:
            out['bar_width']=int(120/len(percents))
        except ZeroDivisionError:
            out['bar_width']=10
#        chart = GC.VerticalBarGroup(percents,encoding="text")
#        chart.scale(0,100)
#        chart.axes.type('xy')
        vals = []
        vals.extend(["%sk" % b for b in bins])
#        chart.axes.label(*vals)
        out['x_labels']=vals
        vals = [0]
        vals.extend(["%s%s" % (x*25,'%') for x in range(1,5)])
        out['y_labels']=vals
#        chart.title("Sales Distribution %s" % Turn.last_year())
#        chart.size(200,150)

#        try:
#            chart.bar(120/len(percents))
#            return chart.url
#        except ZeroDivisionError:
#            pass
        return out


#    @classmethod
#    def price_plot(cls,min_turn=Turn.last_turn(),max_turn=Turn.last_turn(), max_k=7):
#        """Makes a plot of vehicle prices sold last turn. Args are <min_turn> and
#        <max_turn> which both default to last_turn. <max_k> (default 7) is the max 10k price
#        step to use. It will be max_k-1 because it's in a range call."""
#        x_vals=[]
#        y_vals=[]
#        while min_turn <= max_turn:
#            vpss = cls.objects.filter(turn=min_turn)
#            for vps in vpss:
#                if vps.avg_sold_price > 0:
#                    x_vals.append(vps.avg_sold_price/1000)
#                    y_vals.append(vps.sold)
#            min_turn +=1
#
#        chart=ScatterChart(180,150,y_range=[0,max(y_vals)],x_range=[0,max(x_vals)])
#        chart.add_data(x_vals)
#        chart.set_axis_labels(Axis.BOTTOM,range(0,max(x_vals),20))
#        chart.set_axis_labels(Axis.LEFT,range(0,max(y_vals)+100,100))
#        chart.add_data(y_vals)
#        chart.add_data(y_vals)
#        chart.set_title("Price vs Sales")
#        chart.set_colours(["FF0000"])
#
#        return chart.get_url()






    @classmethod
    def sold_plot_data(cls,min_turn=Turn.last_turn(),max_turn=Turn.last_turn()):
        """Prefer plot data for a sold vs produced plot. <min_turn> is the first turn
        to collect data for <max_turn> is the last turn to collect data for. Both are set tto
        last_turn by default. """
        retval={}
        sold=[]
        produced=[]
        axis_labels=[]
        while min_turn <= max_turn:
            sold_val = cls.num_sold(turn=min_turn)
            prod_val = cls.num_produced(turn=min_turn)
            if sold_val == prod_val and sold_val == 0:
                pass
            else:
                sold.append(sold_val)
                produced.append(prod_val)
                #axis_labels.append(Turn.turn_to_year(min_turn))
            min_turn += 1


        try:
            if max(produced)>4000: #and min_turn==3:
            # fix an init_fleet 'feature'
                sold=[1800]
                produced=[2500]
        except ValueError:
            sold=[1800]
            produced=[2500]



        chart=GC.VerticalBarGroup([sold,produced],encoding="text")
        try:
            top = max(produced)
            chart.scale(0,top)
            chart.axes.type('y')
            axis=[0]
            axis.extend([0,top/2,top])
            chart.axes.label(*axis)
            chart.color(*["FF0000","0000FF"])
            chart.legend("sold %s" % sold[0],"produced %s" % produced[0])
            chart.title("Global Sales %s" % Turn.turn_to_year(Turn.last_turn()))
            chart.size(190,150)
    #        chart=HorizontalBarChart(190,150,y_range=[0,max(produced)])
    #        chart.add_data(sold)
    #        chart.add_data(produced)
    #        chart.set_axis_labels(Axis.BOTTOM,axis_labels)
    #        chart.set_axis_labels(Axis.LEFT,range(0,min(3000,max(produced))+500,500))
    #        chart.set_legend(["sold (%s)" % (sold),"produced (%s)" % (produced)])
    #        chart.set_colours(["FF0000",'0000FF'])
    #        chart.set_title("Global Production")
            return chart.url
        except ValueError:
            return None

            


    @classmethod
    def num_sold(cls,turn=Turn.last_turn()):
        """Return num sold on <turn> (default=last_turn) for all vehicles."""

        out = cls.objects.filter(turn=turn).aggregate(Sum('sold'))['sold__sum']
        
        return none_to_zero(out)


    @classmethod
    def num_produced(cls,turn=Turn.last_turn()):
        """Return the number of vehicles produced on <turn> (default = last_turn)
        but not necesarily sold. """
        unsold = cls.objects.filter(turn=turn).aggregate(Sum('unsold'))['unsold__sum']
        return none_to_zero(unsold) + none_to_zero(cls.num_sold(turn))
                

    @classmethod
    def summarize(cls):
        """Fill in the VPSalesSummary table for vehicles on a turn by turn basis. Works
        off of the prior turns vehicle build records in VT table and deduces the rest of the
        data from there."""

        for vp in VehicleProducer.objects.all():
            for vt in VehicleTransaction.objects.filter(turn=Turn.last_turn(), buyer=vp):
                # start with the vehicle builds on last turn. There is one for each vehicle
                veh = vt.vehicle
                vss = cls(turn=Turn.cur_turn(), vehicle=veh)
                vss.build_cost = vt.amount
                # now look at vehicle transactions on this turn, get sum of sold vehicles and income
                vss.sold = none_to_zero(VehicleTransaction.objects.filter(vehicle=veh, turn=Turn.cur_turn()).\
                                        exclude(buyer=uget("admin")).aggregate(Sum('quantity'))['quantity__sum'])
                vss.unsold = vt.quantity - vss.sold
                vss.sales = none_to_zero(VehicleTransaction.objects.filter(vehicle=veh, turn=Turn.cur_turn()).\
                                         aggregate(Sum('amount'))['amount__sum'])
                # build a json list of buyers
                dict = {}
                trans = VehicleTransaction.objects.filter(vehicle=veh, turn=Turn.cur_turn()).exclude(
                        Q(buyer=veh.producer) | Q(buyer=uget("admin")))
                for tran in trans:
                    dict[tran.buyer.username] = VehicleTransaction.objects.filter(vehicle=veh,
                                                                                  buyer=tran.buyer).aggregate(
                            Sum('quantity'))['quantity__sum']

                vss.buyer = json.dumps(dict)
                vss.save()

#    @classmethod
#    def summarize(cls):
#        """Fill in the table for all vehicles, for all turns up to Turn.last_turn()."""
#
#        # how do we handle the fact that the vehicles have the same id in the init process?
#
#        #done_vehs = [vss.vehicle.id for vss in cls.objects.all()]
#        vehs = {}
#        for vt in VehicleTransaction.objects.filter(turn=Turn.cur_turn()): # get all the vehicles by looking up the vehicle transactions
#            vehs[vt.vehicle]=vt.vehicle.id # val doesn't mattter - just making unique list of objects
#            # have to do this this way instead more straightforward way because v_init vehicles
#            # "cleverly" reuse vehicles in multiple turns
#
#
#        for veh in vehs.keys():
#            # create an entry for each one
#            # don't process duplicates
#            try:
#                out = cls.objects.get(vehicle=veh,turn=Turn.cur_turn()).count()
#                if out == 1:
#                    continue
#                elif out > 1:
#                    raise ValueError("Error: should have been 1 or 0 was: %s" % out)
#            except VPSalesSummary.DoesNotExist:
#                vss = cls(turn=veh.turn,vehicle=veh)
#                out =VehicleTransaction.objects.get(vehicle=veh,buyer=veh.producer)
#                vss.build_cost = out.amount
#                total_built = out.quantity
#                vss.sold=none_to_zero(VehicleTransaction.objects.filter(vehicle=veh,seller=veh.producer).\
#                        exclude(buyer=uget("admin")).aggregate(Sum('quantity'))['quantity__sum'])
#
#
#                vss.sales=none_to_zero(VehicleTransaction.objects.filter(vehicle=veh,seller=veh.producer).\
#                         aggregate(Sum('amount'))['amount__sum'])
#
#                try:
#                    vss.unsold=total_built - vss.sold
#                except TypeError:
#                    vss.unsold = total_built
#                dict = {}
#                trans = VehicleTransaction.objects.filter(vehicle=veh).exclude(Q(buyer=veh.producer)|Q(buyer=uget("admin")))
#                for tran in trans:
#                    dict[tran.buyer.username]=VehicleTransaction.objects.filter(vehicle=veh,
#                                        buyer=tran.buyer).aggregate(Sum('quantity'))['quantity__sum']
#
#                vss.buyer=json.dumps(dict)
#                vss.save()


class RuleBase(models.Model):
    """The Rule base class. This is self documenting. Creates a RuleBase table that
        describes all the rules for getting RD points. Also used to run the rules
        during advance turn."""

    name = models.CharField(max_length=40)
    desc = models.CharField(max_length=400)
    area = models.CharField(max_length=40)
    points = models.CharField(max_length=20)

    def __unicode__(self):
        return self.name

    @classmethod
    def allocate(cls):
        """Execute all the rules (and thus allocate rd points)."""
        # check first to see if there were any vehicleTransactions
        # in which consumers bought vehicles, if not, bail.
        if VehicleTransaction.active_turn():
            for cs in cls.__subclasses__():
                try:
                    print "running %s" % cs.name
                    cs.run_rule()
                except AttributeError, e:
                    print e
                    print "look at cs"

        else:
            logging.debug("RuleBase.allocate called on an inactive turn - i.e. no vehicles were purchased.")

    @classmethod
    def generate_entries(cls):
        """Generate entries into the RuleDisplay model by inspecting subclasses"""
        for cs in cls.__subclasses__():
            try:
                print cs.name
            except AttributeError:
                # I don't know why this is happening
                # is it doing any harm - let it pass for now
                # need to inspect this more closely
                print cs
                print "AttributeError exception caught"
                continue

            entry = cls(name=cs.name, desc=cs.desc, area=cs.area, points=cs.points)
            entry.save()
            # we need to do this so that the models can be instantiated
            print "Creating dummy class for %s" % cs.name
            o = cs(name="dummy", desc="NA", area="none", points=0)
            o.save()

    @classmethod
    def run_rule(self, *args, **kwargs):
        """Execute the rule code here. Also, record the r*d allocation for vps so they know where it came from."""
        abstract

class RandDPointRecord(models.Model):
    """Store information about RD point allocation for vps."""
    rule = models.ForeignKey(RuleBase)
    turn = models.IntegerField()
    producer = models.ForeignKey(VehicleProducer)
    points = models.IntegerField()


    @classmethod
    def record(cls, name, vp, points, area=None, cleared=None):
        """Create a record for the RD award for the vp."""

        if cleared == False:
            return
        if area == None: # these are free points to be spent as VP chooses
            vp.rd_points = vp.rd_points + points
            vp.save()
        else: # these are set area points - no player discretion
            rd = RandD(producer=vp, turn=Turn.cur_turn())
            setattr(rd, area, points)
            rd.save()

        obj = RuleBase.objects.get(name=name) # dummy entry
        rpr = cls(rule=obj, turn=Turn.cur_turn(), points=points, producer=vp)
        rpr.save()


class RevenueRule(RuleBase):
    """Allocates free points (points that can be used for anything) based
    on profits."""

    name = "Revenue Points"
    desc = "General use points based on: ((revenue * margin) /100,000)"
    area = "Free"
    points = "Variable"

    @classmethod
    def run_rule(cls, *args, **kwargs):
        profit = 0
        for vp in vpall():
            profit = 0
            for veh in Vehicle.objects.filter(producer=vp, turn=Turn.last_turn()):
                profit = profit + vp.calc_return(veh)

            try:
                points = round((profit + 0.0) / settings.RD_PROFIT_COST, 0)
            except Exception, e:
                print e
                points = 0

            if profit > 0:
                points = points + settings.RD_PROFIT_BONUS
            points = max(settings.RD_MIN, points) # don't let negative points be given here
            points = min(settings.RD_MAX, points) # limit rd points
            PlayPrompt.new(user=vp,message="You earned %s RD points." % points, priority=8,
                           code=PlayPrompt.codes['rd_earned'])
            RandDPointRecord.record(cls.name, vp, points)


#class StyleLeaderRule(RuleBase):
#    """Points for having the highest average style level for sold vehicles this turn. In the
#    event of a tie the points go the producer with the higher volume of vehicles sold. """
#
#    int_points = settings.STYLELEADER # internal points - set the number of points here
#    name = "Style Leader"
#    desc = "Points for the producer with the highest average style/peformance for sold vehicles. "
#    area = "style"
#    points = str(int_points)
#
#    @classmethod
#    def run_rule(cls,*args,**kwargs):
#        leader=None
#        max=0
#        cleared = False # check to see if the tests have run through to make sure we
#                        # don't penalize the first vp just because he is first in the list
#                        # and it never gets past him.
#
#        for vp in vpall():
#            if leader==None:
#                leader=vp
#            (avg,quantity) = VehicleTransaction.avg_attr_and_quantity(vp,'style')
#            if quantity == 0:
#                continue
#            #
#            cleared=True
#            val = avg + ((quantity+0.0)/1000)
#            print "Style val - %s " % val
#
#            if val > max:
#               max = val
#               leader=vp
#
#
#        RandDPointRecord.record(cls.name,leader,points=cls.int_points,area='style',cleared=cleared)
#
#class PerformanceLeaderRule(RuleBase):
#    """Points for having the highest average style performance level for sold vehicles this turn."""
#
#    int_points = settings.PERFORMANCELEADER # set points here
#    name = "Performance Leader"
#    desc = "Points for the producer with the highest average peformance for sold vehicles. "
#    area = "performance"
#    points = str(int_points)
#    cleared=False
#
#    @classmethod
#    def run_rule(cls,*args,**kwargs):
#        leader=None
#        max=0
#
#        for vp in vpall():
#            if leader==None:
#                leader=vp
#            (avg,quantity) = VehicleTransaction.avg_attr_and_quantity(vp,'performance')
#            if quantity == 0:
#                continue
#            #
#            cls.cleared = True
#            val = avg + ((quantity+0.0)/1000)
#            print "Performance val - %s " % val
#
#            if val > max:
#               max = val
#               leader=vp
#
#        RandDPointRecord.record(cls.name,leader,points=cls.int_points,area="performance",cleared=cls.cleared)
#
#
#class BadStyleRule(RuleBase):
#    """Negative points for having the lowest average style level for sold vehicles this turn. In the
#    event of a tie the points go the producer with the higher volume of vehicles sold. """
#
#    int_points = settings.STYLELAGGARD# internal points - set the number of points here
#    name = "Style Laggard"
#    desc = "Penalty for the producer with the lowest average style for sold vehicles. "
#    area = "style"
#    points = str(int_points)
#    cleared = False
#
#    @classmethod
#    def run_rule(cls,*args,**kwargs):
#        worst=None
#        min=1000 # arbitrarily large number
#
#        for vp in vpall():
#            if worst==None:
#                worst=vp
#            (avg,quantity) = VehicleTransaction.avg_attr_and_quantity(vp,'style')
#            if quantity == 0:
#                continue
#            #
#            cls.cleared = True
#            val = avg + ((quantity+0.0)/1000)
#            print "Style val - %s " % val
#
#            if val < min:
#               min = val
#               worst=vp
#
#        RandDPointRecord.record(cls.name,worst,points=cls.int_points,area='style',cleared=cls.cleared)
#
#class BadPerfRule(RuleBase):
#    """Negative points for having the lowest average performance level for sold vehicles this turn. In the
#    event of a tie the points go the producer with the higher volume of vehicles sold. """
#
#    int_points = settings.PERFORMANCELAGGARD # set points here
#    name = "Performance Laggard"
#    desc = "Points for the producer with the lowest average peformance for sold vehicles. "
#    area = "performance"
#    points = str(int_points)
#    cleared = False
#
#    @classmethod
#    def run_rule(cls,*args,**kwargs):
#        worst=None
#        min=1000 # arbitrarily large number
#        cleared = False
#
#        for vp in vpall():
#            if worst==None:
#                worst=vp
#
#            (avg,quantity) = VehicleTransaction.avg_attr_and_quantity(vp,'performance')
#            if quantity==0:
#                continue
#
#            cls.cleared = True
#            val = avg + ((quantity+0.0)/1000)
#            print "Performance val - %s " % val
#
#            if val < min:
#               min = val
#               worst=vp
#
#
#        RandDPointRecord.record(cls.name,worst,points=cls.int_points,area='performance',cleared=cls.cleared)
#
#class FirstBEV(RuleBase):
#    """An award for selling vp's first BEV vehicle. Available to all vp's."""
#
#    int_points=settings.FIRSTBEV
#    name="My First BEV Sale"
#    desc="Points awarded to the vehicle producer for putting his first BEV on the market and selling them (at least 1)."
#    area="bev"
#    points=str(int_points)
#
#    @classmethod
#    def run_rule(cls,*args,**kwargs):
#
#        for vp in vpall():
#
#            val = VehicleTransaction.first_sale(**{'seller':vp,'vehicle__drivetrain__bev':True})
#
#            if val==True:
#                RandDPointRecord.record(cls.name,vp,cls.int_points,area="bev")
#            elif val==False:
#                pass
#            else:
#                raise ValueError("Strange value returned from first_sale: %s" % val)
#        return
#
#class FirstH2(RuleBase):
#    """An award for selling vp's first H2 vehicle. Available to all vp's."""
#
#    int_points=settings.FIRSTH2
#    name="My First H2 Sale"
#    desc="Points awarded to the vehicle producer for putting his first H2 on the market and selling them (at least 1)."
#    area="h2"
#    points=str(int_points)
#
#    @classmethod
#    def run_rule(cls,*args,**kwargs):
#
#        for vp in vpall():
#
#            val = VehicleTransaction.first_sale(**{'seller':vp,'vehicle__drivetrain__fuel':'h2'})
#
#            if val==True:
#                RandDPointRecord.record(cls.name,vp,cls.int_points,area="h2")
#            elif val==False:
#                pass
#            else:
#                raise ValueError("Strange value returned from first_sale: %s" % val)
#
#        return
#
#class AwardHev(RuleBase):
#
#    div = settings.HEVDIV
#    name="HEV R&D Award"
#    desc="A point is awarded for each %s HEV vehicles (includes: BEV, H2, PHEV, HEV) sold." % div
#    area="hev"
#    points="variable"
#
#    @classmethod
#    def run_rule(cls):
#        for vp in vpall():
#
#            kwargs={'seller':vp,'vehicle__drivetrain__hev':True}
#
#            points=VehicleTransaction.points_since_last_turn(cls.div, **kwargs)
#
#            if points > 0:
#                RandDPointRecord.record(cls.name,vp,points,area="hev")
#
#
#
#class AwardH2(RuleBase):
#
#    div = settings.H2DIV
#    name="H2 R&D Award"
#    desc="A point is awarded for each %s H2 vehicles sold." % div
#    area="h2"
#    points="variable"
#
#    @classmethod
#    def run_rule(cls):
#        for vp in vpall():
#
#            kwargs={'seller':vp,'vehicle__drivetrain__fuel':'h2'}
#
#            points=VehicleTransaction.points_since_last_turn(cls.div, **kwargs)
#
#            if points > 0:
#                RandDPointRecord.record(cls.name,vp,points,area=cls.area)
#
#class AwardGas(RuleBase):
#
#    div = settings.GASDIV
#    name="Gas R&D Award"
#    desc="A point is awarded for each %s gas vehicles sold." % div
#    area="gas"
#    points="variable"
#
#    @classmethod
#    def run_rule(cls):
#        for vp in vpall():
#
#            kwargs={'seller':vp,'vehicle__drivetrain__fuel':'gas'}
#
#            points=VehicleTransaction.points_since_last_turn(cls.div, **kwargs)
#
#            if points > 0:
#                RandDPointRecord.record(cls.name,vp,points,area=cls.area)
#
#
#
#
#class AwardDiesel(RuleBase):
#
#    div = settings.DIESELDIV
#    name="Diesel R&D Award"
#    desc="A point is awarded for each %s diesel vehicles sold." % div
#    area="diesel"
#    points="variable"
#
#    @classmethod
#    def run_rule(cls):
#        for vp in vpall():
#
#            kwargs={'seller':vp,'vehicle__drivetrain__fuel':'diesel'}
#
#            points=VehicleTransaction.points_since_last_turn(cls.div, **kwargs)
#
#            if points > 0:
#                RandDPointRecord.record(cls.name,vp,points,area=cls.area)
#
#class AwardBev(RuleBase):
#
#    div = settings.BEVDIV
#    name="BEV R&D Award"
#    desc="A point is awarded for each %s BEV vehicles sold." % div
#    area="bev"
#    points="variable"
#
#    @classmethod
#    def run_rule(cls):
#        for vp in vpall():
#
#            kwargs={'seller':vp,'vehicle__drivetrain__bev':True}
#
#            points=VehicleTransaction.points_since_last_turn(cls.div, **kwargs)
#
#            if points > 0:
#                RandDPointRecord.record(cls.name,vp,points,area=cls.area)
#
#class AwardPhev(RuleBase):
#
#    div = settings.PHEVDIV
#    name="PHEV R&D Award"
#    desc="A point is awarded for each %s PHEV vehicles sold for both BEV and HEV." % div
#    area="bev/hev"
#    points="variable"
#
#
#    @classmethod
#    def run_rule(cls):
#        for vp in vpall():
#
#            kwargs={'seller':vp,'vehicle__drivetrain__phev__gt':0}
#
#            points=VehicleTransaction.points_since_last_turn(cls.div, **kwargs)
#
#            if points > 0:
#                RandDPointRecord.record(cls.name,vp,points,area='bev')
#                RandDPointRecord.record(cls.name,vp,points,area='hev')
#            else:
#                pass


class Message(models.Model):
    """A chat message store."""

    sender = models.ForeignKey(AutopiaUser)
    text = models.TextField(max_length=1000)
    turn = models.IntegerField()
    time = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return "sender: %s  message: %s turn: %s time: %s" % (self.sender.username, self.text,\
                                                              self.turn, self.time)


class MessageReceiver(models.Model):
    """A user who is to receive the message."""
    message = models.ForeignKey(Message)
    receiver = models.ForeignKey(AutopiaUser)
    status = models.CharField(max_length=20, default="unsent")

    def __unicode__(self):
        return "messageReceiver - %s  - %s " % (self.receiver, self.status)








