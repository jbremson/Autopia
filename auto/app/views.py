# Create your views here.
from auto.app.models import *
from auto.misc.models import VehicleProductionForm
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect,HttpResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import render_to_response as r2r
import pdb
import settings
from django.db.models.query import QuerySet
import time
import json
from os import listdir,path
from django import forms
from app.models import Fuel, SetUser,RandDForm,Vehicle
from django.db import transaction as dtrans
import re
import csv
import math



import logging
import sys


logging.basicConfig(level=logging.DEBUG,format='%(asctime)s - %(message)s',stream=sys.stdout)

logging.debug("Starting...")

def render_to_response(template,dict,request):
    """Wrapper for handling the RequestContext requirement for 1.2 template rendering."""
    return r2r(template,dict,context_instance=RequestContext(request))

def session_mng(key,fxn,request,cache=settings.SESSION_CACHE):
    """Session management helper. Send the *key, fxn (fxn must have no args) for the value if key does not exist and the request.
    Returns the val if key exists. Sets the key to fxn and returns the val otherwise.

    If key is compound of form (int, string,...) it will be expired when turn is greater than int.

    If cache is set to False then caching is not used.

    """


    if len(key)>1:
        if key[0] < Turn.cur_turn():
            try:
                del request.session[key]
            except KeyError:
                logging.debug("Trying to remove key that doesn't exist: %s " % key)
                pass
    out = False
    if cache: # we're using caching
        out = request.session.get(key,False)

    if out == False:
        try:
            out = fxn()
        except TypeError:
            # fxn is not callable - it's a string.
            out = fxn
        request.session[key]=out
    return out

def front_door(request,*args,**kwargs):
    """If SetUser finds an Anonymous user send them back to the front_door, ie the login page."""
    return HttpResponseRedirect("/")

@SetUser
@login_required
def guide(request,role):
    """Take user to the guide page for <role> (vp, consumer, fp)."""
    context=request.user.home_context()
    template = "%s/guide.html" % role
    return render_to_response(template,context,request)

@SetUser
@login_required
def ajax_server(request):
    """General function ajax server. Uses the 'fxn' argument to assign the action.
    Check status in ajax on return. Returns 1 for success -1 for failure. Failure will return a msg."""
    get_fxns = ['check_messages','replace_refinery']
    post_fxns = ['rd_update','hide_message','copy slate','replace_refinery']

    data ={}
    if request.method=="GET" and request.is_ajax():
        data['status']=1
        fxn = str(request.GET['fxn'])
        if fxn in get_fxns:
            try:
                if fxn == 'check_messages':
                    try:
                        count = request.user.new_message_count_and_process()
                    except Exception,e: # catch any error as this is ajax and we want to know what happened.
                        logging.debug(e)
                        data['status']=-1
                        data['msg']=e
                    else:
                        data['status']=1
                        data['messages']=count

                elif fxn == 'replace_refinery':
                    rm_id = request.GET['arg'] # refinery model id
                    rm = RefineryModel.objects.get(id=rm_id)
                    data['ref_cost'] = rm.get_cost(request.user)
                    data['payback']=rm.payback(request.user)
                    data['build_time'] = rm.build_time
                    aid=request.GET['asset_id']
                    asset = Asset.objects.get(id=aid)
                    asset.replaced=True
                    asset.save()
            except Exception,e:
                # catch error message to send back - so ajax doesn't bury in a 500.
                data['msg']=e
                data['status']=-1

        else:
            data['msg']="The fxn %s is not defined." % fxn
            data['status']=-1
        return HttpResponse(json.dumps(data))

    elif request.method=="POST" and request.is_ajax():
        data['status']=1
        fxn = str(request.POST['fxn'])
        if fxn in post_fxns:
            if fxn == 'hide_message':
                id = int(request.POST['arg'])
                try:
                    mr = MessageReceiver.objects.get(id=id)
                    mr.status="hide"
                    mr.save()
                except Exception,e:
                    data['status']=-1
                    data['msg']=e
            elif fxn=="copy slate":
                try:
                    request.user.copy_and_update_vehs()
                    data['msg'] = "Successful slate copy."
                except AttributeError:
                    data['status']=-1
                    data['msg']="Slate has been copied."
                except Exception,e:
                    logging.debug("ajax_server call to vp.copy_and_update_vehs - " + e)
                    data['status']=-2
                    data['msg']="Something bad happened."

            elif fxn=="rd_update":
                try:
                    rd_area=str(request.POST['id'])
                    if request.user.rd_points > 0:
                        request.user.rd_points -= 1
                        request.user.save()
                        data['points_available']=request.user.rd_points
                        data['rd_expended']=request.user.rd_expended()
                        rd = RandD(producer=request.user)
                        setattr(rd,rd_area,1)
                        rd.save()
                        data['val']=RandD.sum_area(rd_area, **{'producer':request.user})
                    else:
                        data['points_available']=0
                except Exception,e:
                    data['status']==-1
                    data['msg']=e

            elif fxn=="replace_refinery":
                try:
                    rm_id = request.POST['arg'] # refinery model id
                    rm = RefineryModel.objects.get(id=rm_id)
                    asset = Asset(builder=request.user,owner=request.user,refinery=rm,\
                                  activation_turn=Turn.cur_turn()+rm.build_time, status_code=2)
                    asset.save()
                    at = AssetTransaction(asset=asset, buyer=request.user, seller=uget("admin"),amount=(rm.get_cost(request.user)/1000.0),
                                          turn=Turn.cur_turn(),desc="Replace Refinery",comment="Replace Refinery")
                    at.save()
                    at.process()
                    data['msg']="Built"

                except Exception,e:
                    # display the ajax error as an alert
                    data['msg']=e
                    data['status']=-1

        return HttpResponse(json.dumps(data))

    else:
        data['status']=-1
        data['msg'] = "No fxn call was caught by ajax_server."
        return HttpResponse(json.dumps(data))


@SetUser
@login_required
def home(request, *args,**kwargs):
    #capture and rediretc the user who didn't login but ends up hereanyway
    if kwargs.has_key("Anonymous"):
        if kwargs['Anonymous'] ==True:
            logging.debug("Anonymous user. Redirecting back.")
            logging.debug(request)
            return HttpResponseRedirect("/")
    context = request.user.home_context()
    if request.user.username in ["admin"]:
        context['operator']=True # can see operation controls
        context['vehs_bought']=Turn.vehs_bought()

    else:
        context['operator']=False

    t = Turn.cur_turn()
    # rewrite this to something more maintainable!
    # All of the fuel price stuff should be encapsulized into something
    # more abstract.
    # this should be a helper function
    i=Fuel.fuel_turn_index()

    try:
        context['gas_price']=round(settings.GAS_COST[i],2)
        context['diesel_price']=round(settings.DIESEL_COST[i],2)
        context['elec_price']=round(settings.ELEC_COST[i],2)
        context['h2_price']=round(settings.H2_COST[i],2)
    except TypeError:
        i=[i]
        context['gas_price']=round(settings.GAS_COST(i),2)
        context['diesel_price']=round(settings.DIESEL_COST(i),2)
        context['elec_price']=round(settings.ELEC_COST(i),2)
        context['h2_price']=round(settings.H2_COST(i),2)

    except IndexError:
        for f in Fuel.fuel_names():
            context["%s_price" % f] = "NA"

    if request.user.group =="Vehicle Producer":

        fuel_data = session_mng((Turn.cur_turn(),'fuel_market_data'),Fuel.fuel_market_data,request)

        #context['fuel_history'] = fuel_data['data']
        val = min(t,4)
        context['price_history']=fuel_data['price'][-4:]
        context['long_labels'] = fuel_data['long_labels'][-4:]
        context['history_legend']=fuel_data['legend']

        tally = VPSumData.objects.filter(producer=request.user)
        context['tally']=session_mng((Turn.cur_turn(),'tally'),tally,request)
        #context['ledger'] = session_mng((Turn.cur_turn(),'ledger'),request.user.ledger,request)
        context['ledger'] = request.user.ledger(turn=Turn.last_turn())
        summary= VPSalesSummary.objects.filter(vehicle__producer=request.user).order_by("turn")

        context['summary'] = session_mng((Turn.cur_turn(),'summary'),summary,request)
#        context['price_plot']=session_mng((Turn.cur_turn(),'price_plot'), VPSalesSummary.price_plot,request) # put this is a session_mng
#        sc =  VPScore.objects.filter(user=request.user)
#        for oo in sc:
#            oo.year = Turn.turn_to_year(oo.turn)
                    # changing get to filter

        context['earned_rd']= VPSumData.objects.filter(producer=request.user, turn=Turn.last_turn())[0].assigned_rd_points

#        context['my_score']=sc

        #context['breakdown_plot'] = session_mng((Turn.cur_turn(),'breakdown_plot_string'), request.user.breakdown_plot_string,request)
        if settings.GAME_TYPE=="autopia":
            context['profit_loss']=session_mng((Turn.cur_turn(),'profit_loss'), request.user.profit_loss_plot,request)
            context['breakdown_plot'] = session_mng((Turn.cur_turn(),'breakdown_plot_string'),
                                                    request.user.plot_vp_consumer_record,request)
            context['market_position'] = session_mng((Turn.cur_turn(),'plot_market_position'), request.user.plot_market_position,request)
            context['vps']= session_mng((Turn.cur_turn(),'plot_market_data'),request.user.plot_market_data,request)
        else: # autobahn
            #fxn=VPSalesSummary.sold_plot_data(min_turn=Turn.last_turn())
            #context['global_production']=session_mng((Turn.cur_turn(),'global_production'),fxn, request)
            #context['price_data']=session_mng((Turn.cur_turn(),'price_data'),FuelRecord.short_plot_price_data,request)
            #fxn = VPSalesSummary.price_plot(turn=t) # put this is a session_mng
            out= VPSalesSummary.price_plot(turn=t-1)
            context.update(out)
            if Turn.cur_turn() <= 3:
                context['sold']=1800
                context['produced']=2500
            else:
                context['sold']=VPSalesSummary.num_sold(turn=t-1)
                context['produced']=VPSalesSummary.num_produced(turn=t-1)

        context['prompts']= session_mng((t,'get_prompts'),request.user.get_prompts,request)

        context['cur_cafe'] = none_to_zero(request.user.calc_cafe())


    if request.user.group == "Fuel Producer":
        context['charts'] = session_mng((t,'charts'),FuelRecord.fuel_volume_charts,request)
        context['capacity_chart']=session_mng((t,'capacity_chart'),Asset.plot_capacity,request)
        context['revenue_chart']=session_mng((t,'revenue_chart'),FuelRecord.plot_revenue_data,request)

    if request.user.group == "Consumer":
        for fuel in ['gas','diesel','h2','elec']:

            try:
                context['vehicle_stats'][fuel + '_cost']=float(FuelRecord.last(fuel))*float(context['vehicle_stats'][fuel +'_gals'])
            except KeyError:
                if fuel == "elec":
                    context['vehicle_stats'][fuel + '_cost']=float(FuelRecord.last(fuel))*float(context['vehicle_stats']['bev_gals'])
            except ValueError:
                context['vehicle_stats'][fuel + '_cost']="NA"
            context['vehicle_stats']['elec_cost']="NA"


        fuel_data = session_mng((Turn.cur_turn(),'fuel_volume_data'),request.user.fuel_volume_data,request)
        context['turn_report']=session_mng((Turn.cur_turn(),'turn_report'),request.user.turn_report,request)
        context['fuel_history'] = fuel_data['data']
        context['history_labels'] = fuel_data['labels']
        context['history_legend']=fuel_data['legend']
        context['fuel_cost']=fuel_data['cost']


    if context.has_key('vehicle_stats'): # vp = VehicleProducer.objects.get(username="v1")
        for o in context['vehicle_stats'].keys():
            try:
                # check the type of the key by looking at the value at the end
                # round according to the key end, but this doesn't matter that much for now.
                context['vehicle_stats'][o]=round(context['vehicle_stats'][o],2)
            except (TypeError,ValueError):
                pass

    loc = context['home']
#    if request.user.first==True and not request.user.group == "Admin":
#        request.user.first=False
#        loc = "%s/guide.html" % request.user.template_dir
#        request.user.save()
    context['prompts']= session_mng((Turn.cur_turn(),'get_prompts'),request.user.get_prompts,request)
    return render_to_response(loc, context, request)

@SetUser
@login_required
def chat_frame(request):
    context = {}
    return render_to_response("chat/chat_frames.html",context,request)

@SetUser
@login_required
def chat_log(request):
    """Shows all messages sent and received by the user, that have status sent."""
    context={}
    context['AJAX_LIB']=settings.AJAX_LIB

    context['messages']=MessageReceiver.objects.filter(Q(receiver=request.user)|Q(message__sender=request.user)).exclude(status="hide")
    MessageReceiver.objects.filter(Q(receiver=request.user)|Q(message__sender=request.user),status="unsent").update(status="sent")
    ulist = AutopiaUser.user_list(request.user.username)

    context['users']=ulist

    return render_to_response("chat/chat_log.html",context,request)



@SetUser
@login_required
def chat_read(request):

    context = {}
    context['username']=request.user.username

    if request.method=="GET" and request.is_ajax():
        dict = {}
        # are there any unsent messages for this user?
        # if so get one and send it back to user,
        # make sure to mark it sent
        try:
            mr = MessageReceiver.objects.filter(receiver=request.user,status="unsent").order_by('message__time')[0]
        except IndexError, MessageReceiver.DoesNotExist:
            dict['count']=0
        else:
            dict['count']=1
            dict['message']=mr.message.text
            dict['uname']= mr.message.sender.username
            dict['to']= mr.receiver.username
            dict['id']=mr.pk
            mr.status = "sent"
            mr.save()
            if dict['uname']==dict['to']: # either message to self or another player
                # look up any other receiver of that message that is not my self
                # and set 'to' to that .
                try:
                    chk = MessageReceiver.objects.filter(message=mr.message).exclude(receiver=request.user)
                except MessageReceiver.DoesNotExist:
                    pass

                if len(chk)==0:
                    pass
                else:
                    out = []
                    for mr  in chk:
                        out.append(mr.receiver.username)

                    dict['to']=",".join(out)



        data = json.dumps(dict)
        return HttpResponse(data)
    else:
        context['chat_read']=True
        return render_to_response("chat/chat_read.html",context,request)

@SetUser
@login_required
def buyveh(request):
    if request.user.username != "admin":
        return HttpResponse("Failed: User does not have permission.")
    Consumer.automated_buy()
    return HttpResponseRedirect('/home')

@SetUser
@login_required
def chat_write(request):
    """Write a message to the server for distributionn by the reader code."""

    context = {}
    if request.method=="POST" and request.is_ajax():
        # make a Message and recipients
        # msg = Message(...)
        recip_list = list()
        str = request.POST['str']
        recip = request.POST['receiver'].__str__()
        try:
            if not recip == "al":
                user = AutopiaUser.objects.get(username=recip)
                recip_list.append(user)
            else:
                recip_list = AutopiaUser.objects.all()
        except User.DoesNotExist,e:
            dict = {'status':'fail','msg':'User named %s does not exist.' % rec.strip()}
            return HttpResponse(json.dumps(dict))

        me = AutopiaUser.objects.get(username=request.user.username)
        #recip_list.append(me)
        recip_list = list(set(recip_list))

        txt = str.__str__().strip()
        if len(txt)==0:
            return HttpResponse(1)
        msg = Message(text=txt, turn=Turn.cur_turn(), sender=me )
        msg.save()

        for rec in recip_list:
            try:
                mr = MessageReceiver(message=msg,receiver=rec,status="unsent")
                mr.save()
            except Exception,e:
                print e

        # msg.save()
        # MessageReceiver.create_recipients(msg,[autopiausers])
        dict = {"status":"ok"}
        return HttpResponse(json.dumps(dict))

    else:
        ulist = AutopiaUser.user_list(request.user.username)
        context['users']=ulist
        return render_to_response("chat/chat_write.html",context,request)

@SetUser
@login_required
def veh_buy_data(request):
    if request.method == "GET" and request.is_ajax():
        try:
            if request.GET.has_key('arg'):
                vid = request.GET['arg']
                veh = Vehicle.objects.get(id=vid)
                dict = {}
                if request.GET['caller']=="buy_screen":
                    dict['price']=veh.price
                    dict['count']=min(veh.num_available,veh.get_max(request.user)['val'])
                    dict['name']=veh.name
                elif request.GET['caller']=="vp_home":
                    dict['num_sold'] = veh.num_sold
                    dict['revenue'] = "%s" % round(veh.revenue,2)
                    dict['balance'] = request.user.balance
                    dict['cur_cafe'] = request.user.calc_cafe()
                    dict['rd_points'] = request.user.rd_points
                else:
                    raise ValueError("Non-existent value sent for caller arg to views.veh_buy_data: %s" % request.GET['caller'])
            elif request.GET['caller']=="update_max_vals":
                # get all the ids of vehicles currently for sale and their max values per user
                dict = {}

                try:
                    for veh in Vehicle.objects.filter(turn=Turn.last_turn()):
                        #if request.user.group == "Consumer":
                        if settings.GAME_TYPE=="autobahn":
                            out=veh.num_sold
                            dict['#get_max_%s' % veh.id] = out
                        else:
                            out = veh.get_max(request.user)
                            dict['#get_max_%s' % veh.id] = out['val']
                        dict['#price_%s' % veh.id] = veh.price
                        if not request.user.group == "Consumer":
                            dict['#buyers_%s' % veh.id] = ",".join(veh.cur_buyers())
                    dict['#status']=Vehicle.vp_sale_status()['status']
                    if request.user.group=="Consumer":
                        dict["#turn_vehicle_goal"] = request.user.turn_vehicle_goal
                        dict["#balance"]=round(request.user.balance,2)
                        dict["#dynamic_average"]=request.user.dynamic_average()
                except Exception,e:
                    dict['#status']=e
            data = json.dumps(dict)
            return HttpResponse(data)
        except Exception,e:
            print e
            return HttpResponse(-1)
    else:
        print "veh_buy_data called with uncovered request."
        return HttpResponse(-1)

@SetUser
@login_required
def buy_vehicle(request):
    """Ajax code to validate and handle vehicle purchase. Current."""
    if request.method=="POST" and request.is_ajax() and not Turn.is_processing():
        try:
            dict={'msg':'* Error: Invalid characters. *','status':-1}
            vid = request.POST['arg']
            quantity = int(request.POST['to_buy'])
            veh = Vehicle.objects.get(id=vid)
            amount = float(veh.price * quantity)/10**6
            #fees = float(quantity*(veh.licensing + veh.gas_guzzler))/10**6
            fees = 0 # not in use in this game

            if request.user.balance <= 0:
                dict['msg']="You have no money. :("

            elif amount > request.user.balance:
                dict['msg'] = "* Insufficient funds for this purchase. *"
                dict['status']=-1
            elif quantity > veh.get_max(request.user)['val']:
                dict['msg'] = " Illegal purchase quantity."
                dict['status']=-1

            elif quantity > 0 and quantity <= min(veh.num_available,veh.get_max(request.user)):
                dict['msg']="* Successful transaction. *"
                dict['status']=1
                vt = VehicleTransaction(buyer=request.user,seller=veh.producer,
                                        amount=amount,desc="Vehicle transaction",
                                        fees=fees,quantity=quantity,vehicle=veh,
                                        turn=Turn.cur_turn())
                if request.user.group == "Consumer":
                    vt.buyer_avg_price = request.user.dynamic_average()
                    vt.sold = True
                try:
                    vt.save()
                    vt.process(fees,amount)
                   
                except Exception, e:
                    dict['msg']=" * Error in transaction save: %s" % e
                    dict['status']=-1

                if request.user.group == "Consumer":
                    vt.do_choice_sets(veh)



            else:
                dict['msg']="* Error: Invalid purchase quantity. *"
                dict['status']=-1

        except Exception,e:
            print e
            pass
        data = json.dumps(dict)
        return HttpResponse(data)


@SetUser
@login_required
@user_passes_test(lambda u: u.group == "Vehicle Producer")
def vehicle(request):
    context = request.user.home_context()
    if request.method == "POST":
        form = VehicleForm(request.POST)
        if form.is_valid():

            v = form.save(commit=False)
            # if there has already been a vehicle created with
            # same name  on this turn - disallow

            # check to see if the vehicle is a gas_guzzler
            # v.is_gas_guzzler - notify user if so.
            # There will need to be a confirm screen.
            v.turn = Turn.cur_turn()

            v.producer = request.user # VP owns vehicle at first
            legal = v.legalName()
            if legal['status'] == True:
                context['message'] = "Vehicle Created"
                v.save()
            else:
                context['message'] = "Vehicle name not allowed: %s" % legal['msg']

            return render_to_response(context['home'], context, request)
    else:
        #form = VehicleForm()
        onsale = Vehicle.objects.filter(producer=request.user, turn=Turn.cur_turn())
        #o = {"form":form,"onsale":onsale}
        o = {"onsale":onsale}
        context.update(o)
        return render_to_response(context['home'], context, request)


@SetUser
@login_required
def vehicle_price_change(request):
    if request.method=="POST" and request.is_ajax():
        vid = int(request.POST['id'].__str__())
        try:
            price = int(request.POST['price'])
            veh = Vehicle.objects.filter(pk=vid).update(price=price)
            return HttpResponse(1)
        except Vehicle.DoesNotExist,e:
            print e
            return HttpResponse(-1)
    else:
        return HttpResponse(-1)


@SetUser 
@login_required
@user_passes_test(lambda u: u.group == "Vehicle Producer")  
def price(request, id):
    # make sure that it is the vehicle producer making the price change!
    vehicle = Vehicle.objects.get(pk=id)
    fee = settings.VEHICLE_PRICE_CHANGE_FEE
    if request.method == "POST":

        form = VehiclePriceChangeForm(request.POST)
        try:
            bool = form.is_valid() and int(request.POST['price']) > 0
        except ValueError:
            bool = False


        if bool == True:
            context = request.user.home_context()
            price = form.cleaned_data['price']
            old_price = vehicle.price

            desc = "Change id:%s from %s to %s" % (id, old_price, price)
            #try:

            #request.user.fee("vehicle_price_change", 0, desc)
            #except Exception:
            #    context['message']="Vehicle price changed failed at fee."

            #    return render_to_response(context['home'],context)

            vehicle.price = price
            super(Vehicle,vehicle).save()
            context['message'] = "Vehicle price changed for %s." % vehicle.name
            return render_to_response(context['home'], context, request)
        else:
            context = request.user.base_context()
            try:
                if int(request.POST['price']) < 0:
                    context['message'] = "Negative price not permitted."
            except ValueError:
                context['message'] = "Invalid entry for price."
            context['form'] = VehiclePriceChangeForm(initial={'price':request.POST['price']})
            return render_to_response(context['home'], context, request)
    else:
        form = VehiclePriceChangeForm()
        context = request.user.base_context()

        context['form'] = form
        context['form_message'] = "Set new vehicle price.Old price: %s."\
        % (vehicle.price)
        return render_to_response('vp/vp_home.html', context, request)

@SetUser
@login_required
def transaction(request):
    # form needs buyer (executer), seller(receiver) and amount
    context = request.user.home_context()

    if request.method == "POST":
        form = TransactionForm(request.user,request.POST)
        if form.is_valid():
            t = form.save(commit=False)
            #t.buyer = request.user
            t.turn = Turn.cur_turn()
            t.buyer = request.user
            t.desc = "player transfer"
            t.amount = (t.amount+0.0) /10**3
            t.save()
            # try block
            #t.process()
            # if process fails do something about it. 
            # it shouldn't fail, and it doesn't matter that much if it does
            # It should warn the admin mostly so that the accounts can be manually fixed.
            # The catch should redirect to a transaction failed page.
            context['message'] = "Successful transaction."
            return HttpResponseRedirect("/home")
        else:
            context['form'] = TransactionForm(request.user,request.POST)
            return render_to_response('global/do_transaction.html', context, request)
    else:
        form = TransactionForm(request.user)

        context['form'] = form
        return render_to_response('global/do_transaction.html', context, request)
    # create transaction

    # process it
    #return render_to_response('mpg/content/consumer_transaction_form.html',request.user.base_context())


@SetUser
@login_required
def new_vehicle_market(request):
    """A market place for all vehicles for all users. Anyone can make an offer on any vehicle.
    Acceptance of that offer is not required. Only new vehicles can be purchased for now.
    """
    # show all vehicles in a sortable table except for the users own
    template = "game/%s.html" % (request.user.group)
    context = request.user.base_context()
    #context['leader']=VehicleProducer.vp_leader()
    if request.user.group=="Consumer":
        try:
            context['dynamic_avg'] = request.user.dynamic_average()
        except ZeroDivisionError:
            context['dynamic_avg'] = "NA "
        context['consumer']=True


    elif request.user.group=="VehicleProducer":
        context['vp']=True
    if request.method == "POST":
        form = AddToFleetForm(request.POST)
        if form.is_valid():

            redir = "/confirm_vehicle_purchase/%s/%s" % (form.cleaned_data['vehicle_id'], form.cleaned_data['quantity'])
            return HttpResponseRedirect(redir)
        else:
            context['message'] = "form is not valid"
        return render_to_response('global/vehicle_market.html', context, request)

    else:
        for val in ['gas','diesel','elec','h2']:
            context["%s_price" % val]=FuelRecord.last(val)
        vehicle_market = Vehicle.objects.filter(turn=Turn.last_turn()).exclude(producer=uget('v_init'))
        avgs=None
        if request.user.group=="Consumer":
            # for some reason I get a pyindent error when I try to move this into the loop below. So just doing it here.
            avgs = Vehicle.objects.filter(turn=Turn.last_turn()).aggregate(Avg('performance'),Avg('style'),Avg('price'),Avg('mpg'))
        if request.user.group=="Consumer":
            # calculating this here so we don't have to do it repeatedly
            for vm in vehicle_market:
                #vm.max =  int(request.user.balance*10**6/vm.final_cost)
                vm.max = vm.get_max(request.user)
                # the score_vehicle must happen with the unadjusted vm.max!
                if request.user.group=="Consumer":
                    vm.quick_score = request.user.quick_score_vehicle(vm.id)
                    #vm.score = request.user.score_vehicle(vm,avgs)


                # adjust vm.max
                if vm.max < 0:
                    vm.max = 0
                if vm.max > vm.num_available:
                    vm.max = vm.num_available
                #if vm.num_available==0:
                #    vm.num_available=
                vm.price = int(vm.price)

            #vehicle_market = Vehicle.grade_vehicle(vehicle_market) # change score to grade
        context['vehicle_market'] = vehicle_market
        return render_to_response('global/vehicle_market.html', context, request)

@SetUser
@login_required
def confirm_vehicle_purchase(request, *args,  ** kwargs):
    """Confirm the vehicle purchase. Inform the purchaser of taxes and licensing cost per vehicle
    and total cost for the entire purchase. Make sure consumer has enough money.
    """
    #form = AddToFleetForm()
    context = request.user.base_context()

    if settings.TESTING == True:
        context['testing']=True
    if kwargs.has_key('id'):
        car = Vehicle.objects.get(pk=kwargs['id'])
    else:
        car = Vehicle.objects.get(name=kwargs['name'],turn=Turn.last_turn())
    car.price = int(car.price)

    car.quantity = kwargs['quantity']

    car.subtotal = int(car.get_vehicle_costs()   )

    car.fees = int(car.get_vehicle_fees())
    car.guz_fee = int(car.gas_guzzler) * int(car.quantity)
    car.fees = car.fees + car.guz_fee
    car.total = car.subtotal + car.fees

    car.max =  int(request.user.balance*10**6/car.price)


    if request.method == "POST":
        # Here, we need to do a vehicle transaction and
        # a fleet add.

        # check to make sure that
        desc_str = "Vehicle transaction."
        car.quantity = int(car.quantity)
        if car.quantity > car.num_available:
            car.quantity = car.num_available


        car.fees = float(car.fees)/10**6
        car.subtotal = float(car.subtotal)/10**6
        car.total = car.fees + car.subtotal

        if car.quantity > 0 and car.quantity*car.price/10**6 <= request.user.balance:  # don't create a 0 transaction



            vt = VehicleTransaction(buyer=request.user, seller=car.producer,
                                    amount=car.subtotal, desc=desc_str, vehicle=car,
                                    fees=car.fees, quantity=car.quantity,account="buy",

                                    turn=Turn.cur_turn())
            try:
                vt.save()
            except TypeError:
                raise TypeError("vt.save failed.")
            #try:
            vt.process(car.fees, car.subtotal)
    #        except AssertionError:
    #            raise AssertionError("Multiple values?")
    #        except Exception:
    #            raise Exception("VehicleTransaction process failed.")
        else:
            raise ValueError("Illegal car quantity or not enough funds to cover purchase.")
        return HttpResponseRedirect('/new_vehicle_market')

    else:
        if request.user.balance < 0:
            context['warning_message'] = "You will need to borrow to make this purchase. The interest rate is 5%."
        context['vehicle_purchase_confirm'] = True
        context['car'] = car
        return render_to_response('global/confirm_vehicle_purchase.html', context, request)

@SetUser
@login_required
def view_fleet(request):
    """Show a sortable table of the users vehicle fleet."""
    fleet_view = Fleet.objects.filter(owner=request.user).exclude(quantity=0)


    # ca;c
    for f in fleet_view:
        f.annual_fuel_consumption = f.vehicle.annual_fuel_usage(request.user)
        f.annual_sum_consumption = f.annual_fuel_consumption * f.quantity
        f.annual_vmt = f.vehicle.annual_vmt(request.user)
        f.annual_sum_vmt = f.annual_vmt * f.quantity / 1000
        f.age = f.vehicle.age()
    context = request.user.base_context()
    context['fleet_view'] = fleet_view
    return render_to_response('consumer/view_fleet.html', context, request)

@SetUser
@login_required
def advance_turn(request):
    request.user.advance_turn()
    #context = request.user.home_context()
    return HttpResponseRedirect('/home')


@SetUser
@login_required
def reset_game(request):
    request.user.reset_game()
    #context = request.user.home_context()
    return HttpResponseRedirect('/home')

@SetUser
@login_required
def reset_start(request):
    if not request.user.group == "Admin":
        raise Exception("Invalid user group for this call.")
    Turn.reset_turn_start()
    #context = request.user.home_context()
    return HttpResponseRedirect('/home')

@SetUser
@login_required
@user_passes_test(lambda u: u.group == "Vehicle Producer")
def rd_award(request):
    """Show info about RD awards: 1) the list of awards (static) and 2) the list
    of received awards."""
    context = request.user.base_context()
    context['rules']=RuleBase.objects.all().exclude(name='dummy')
    context['awards']=RandDPointRecord.objects.filter(producer=request.user)


    return render_to_response('vp/rd_award.html',context,request)


@SetUser
@login_required
@user_passes_test(lambda u: u.group == "Vehicle Producer")  
def vehicle_r_and_d(request):

    context = request.user.base_context()
    if request.method == "POST":
        form = RandDForm(request.POST)
        if form.is_valid():
            # make sure r&d points don't add up to more than user has available
            if request.user.rd_points < form.cleaned_data['points']:
                raise Exception("Too many rd_points used. Form tampering?")

            if request.user.rd_points >= form.cleaned_data['points']:
            # make sure r&d points add up to less than user.rd_points
                sum = 0
                for a in RandD.areas:
                    sum = sum + form.cleaned_data[a]
                if sum > request.user.rd_points:
                    raise Exception("More points accrued than user has. ")
                request.user.rd_points = request.user.rd_points - sum
                request.user.save()

                # subtract from point count
                form.cleaned_data['producer']=request.user
                del form.cleaned_data['points']
                r = RandD(**form.cleaned_data)
                r.producer = request.user
                r.save()


        else:
            print "fialed"
            print form.errors
            context['message'] = "form_is_valid failed for vehicle_r_and_d."
        return HttpResponseRedirect("/vp/vehicle_r_and_d/")



    else:
        kwargs={}
        kwargs['producer']=request.user
        areas={}
        history = []
        labels = []
        for a in RandD.areas:
            areas[a] = RandD.sum_area(a,**kwargs)
            history.append([areas[a]])
            labels.append(a)


        context['rules'] = RuleBase.objects.all()

        context['areas']=areas

        context['rd_history'] = history
        context['rd_labels']=labels
        context['points']=request.user.rd_points
        context['rd_expended']=request.user.rd_expended()
        context['rd_stats']=VehicleProducer.rd_stats()
        context['gauges']=request.user.all_gauges()
        context['pie']=request.user.pie_randd_areas()

        return render_to_response('vp/r_and_d.html', context, request)

@SetUser
@login_required
def fuel_transactions(request):
    """View transactions for the FP, fuel and other."""

    fts = FuelTransaction.objects.filter(seller=request.user)
    for ft in fts:
        ft.year = Turn.turn_to_year(ft.turn)
        fr =  FuelRecord.objects.get(turn=ft.turn,fuel=ft.fuel)
        ft.fuel_price =fr.actual_price

    ats = AssetTransaction.objects.filter(Q(seller=request.user)|Q(buyer=request.user))
    for at in ats:
        at.year = Turn.turn_to_year(at.turn)
        if at.buyer.username==request.user.username:
            at.amount = -at.amount

    context = request.user.home_context()
    context['fuel_sales']=fts
    context['assets']=ats

    return render_to_response('fp/transactions.html',context,request)

@SetUser
@login_required
def vehicle_sales_data(request):
    """Print a csv of vehicle sales data across all turns, all data viewable by all players."""
    # this should just get called during the advance_turn to spare cycles. it will not change between
    # turns.
    response=HttpResponse(mimetype="text/csv")
    response['Content-Disposition']='attachment; filename=veh_sales.csv'
    response['Cache-Control'] = 'no-cache'
    response_writer=csv.writer(response)
    header=['Producer','Name','Year','Drivetrain','Fuel','Style','Performance','MPG',
            'List Price','# Sold','Top Buyer']
    response_writer.writerow(header)


    for vss in VPSalesSummary.objects.all().exclude(vehicle__producer__username="v_init"):
        row = []
        row.append(vss.vehicle.producer.username)
        row.append(vss.vehicle.name)
        row.append(Turn.turn_to_year(vss.turn))
        row.append(vss.vehicle.drivetrain.name)
        row.append(vss.vehicle.drivetrain.fuel)
        row.append(vss.vehicle.style)
        row.append(vss.vehicle.performance)
        row.append(vss.vehicle.mpg)
        row.append(vss.vehicle.price)
        row.append(vss.sold)
        try:
            dict = eval(str(vss.buyer))
            top = sorted(dict,key=dict.get,reverse=True)[0]
        except IndexError:
            top="None"
        row.append(top)
        response_writer.writerow(row)

    return response



@SetUser
@login_required
def vehicle_sales(request):
    """View vehicle transaction records for this VP"""

    context = request.user.home_context()
    context['ledger']=session_mng((Turn.cur_turn(),'full_ledger'),request.user.full_ledger,request)
    summary= VPSalesSummary.objects.filter(vehicle__producer=request.user).order_by("-turn")
    context['vehicle_sales'] = session_mng((Turn.cur_turn(),'summary'),summary,request)
    if settings.GAME_TYPE=="autopia":
        v = VehicleTransaction.objects.filter(turn=Turn.cur_turn()).filter(Q(seller=request.user) | Q(buyer=request.user, seller=uget("admin")))
        for o in v:
            o.year = Turn.turn_to_year(o.turn)
            if o.buyer==request.user:
                o.amount = -o.amount

        context['vehicle_sales'] = v

        #penalties = Transaction.objects.filter(buyer=request.user, account="vehicle sales penalty")
        other = Transaction.objects.filter(Q(buyer=request.user)| Q(seller=request.user))
        for o in other:
            o.year = Turn.turn_to_year(o.turn)
            if o.buyer.username == request.user.username:
                o.amount = -o.amount

        context['vehicle_penalties']=other

    return  render_to_response('vp/transactions.html', context, request)


@SetUser
@login_required
@user_passes_test(lambda u: u.group == "Vehicle Producer")
def confirm_build(request):
    """This is the screen after show_vehicles where the VP makes a final
        confirmation of the build."""
    context = request.user.home_context()
    context['confirm'] = True

    distress = settings.VEHICLE_DISTRESS_SALE

    if request.method == "GET":

        form = VehicleProductionForm(request.GET)
        if form.is_valid():
            context.update(form.cleaned_data)
            context['veh_form'] = VehicleForm()
            context["min_cost"] = round(distress * (context['min'] * context['cost']) / 1000000, 2)
            context['unit_penalty'] = context['cost'] * distress
            context['max_cost'] = round(context['max'] * context['cost'] / 1000000, 2)
            return render_to_response("vp/show_vehicles.html", context, request)

    if request.method == "POST":
        form = VehicleForm(request.POST)
        # do conversions here.
        if form.is_valid():

            #make the new vehicle herec

            new_veh = form.save(commit=False)
            new_veh.producer = request.user
            new_veh.turn = (Turn.cur_turn() + 1)
            out = new_veh.legalName()
            if out['status'] == True:
                new_veh.save()
                context['message'] = "*** %s created succesfully ***" % new_veh.name


            else:
                print out['msg']
                context['message'] = out['msg']

            return render_to_response('vp/vp_home.html', context, request)
        else:
            context['message'] = "ERROR - views.confirm_build form.is_valid failed for POST."
            return render_to_response('vp/show_vehicles.html', context, request)


    else:

        context['message'] = "ERROR - views.confirm_build form.is_valid failed."
        return render_to_response('vp/show_vehicles.html', context, request)

@SetUser
@login_required
def vehicle_renew(request, *args, **kwargs):

    """ This is where the VP can choose to renew a vehicle. If he renews the vehicle
        he goes to the vehicle creation screen with the old vehicle data filled into the form.
        """
    context = request.user.home_context()
    if request.method == "POST":
        veh = Vehicle.objects.get(id=vid)
        # look up the vehicle_model for the vehicle for next turn

#        nvm = VehicleModel.objects.get(producer = request.user,turn=Turn.cur_turn(),\
#            drivetrain=veh.model.drivetrain)
#        renewed = Vehicle(production_cost=nvm.cost, mpg=nvm.mpg, name=veh.name,\
#            producer=veh.producer,price=veh.price, turn=Turn.cur_turn(),run=veh.run,\
#            parent=veh.id, drivetrain=veh.drivetrain,performance=veh.performance,\
#            style=veh.style, emissions=veh.emissions)
#        renewed.save()
        return HttpResponseRedirect("/")
    else:
        return render_to_response(context['home'],context, request)

@SetUser
@login_required()
def help_videos(request):
    """Creates the help videos index page by parsing the video directory in media.
        Each video has its own directory. Within each is a meta.txt file with a line
        for a 'class' value and a line for a 'link' value. The class is the heading
        the video should be listed under. The link is the link text. A line starting with "#" will
        be ignored as will an empty line. Example file:
        class = vehicle producer -line break- link = This is a sample text."""

    dict = {}
    links = {}
    for dir in listdir(settings.VIDEO_DIR):
        file = path.join(settings.VIDEO_DIR,dir,'meta.txt')
        if path.isfile(file):
            group=''
            text=''
            out = open(file)
            for line in out:
                if line.strip()=='':
                    continue
                if line.strip()[0] == '#':
                    continue
                key,val=line.strip().split("=")
                if key.strip() == 'class':
                    group = val.strip().title()
                if key.strip() =='link':
                    text = val.strip()
        else:
            #raise Exception("%s in VIDEO_DIR does not have a meta.txt file" % dir)
            continue
        tmp={'text':text,'dir':dir}
        try:
            dict[group].append(tmp)
        except KeyError:
            dict[group]=[tmp]
    context=request.user.home_context()
    context['vids']=dict
    return render_to_response('global/video_guide.html',context,request)


@SetUser
@login_required()
def delete_vehicle(request):
    """Delete a vehicle and reverse the transaction."""

    if request.method=="POST" and request.is_ajax():
        vid = int(request.POST['vid'])
        vts = VehicleTransaction.objects.filter(vehicle__id=vid)
        if not vts.count() == 1:
            # this is an illegal transaction
            logging.debug("Illegal delete_vehicle transaction attempted.")
            return HttpResponse(-1)

        vts[0].reverse()
        return HttpResponse(1)

@SetUser
@login_required()
def edit_vehicle(request):
    """Edit an existing vehicle for next turn."""
    if request.method=="GET" and request.is_ajax():
        vid = int(request.GET['vid'])
        data = {}
        #
        veh = Vehicle.objects.get(id=vid)
        if not veh.turn == Turn.cur_turn():
            raise ValueError("This is not an editable vehicle.")
        vt = VehicleTransaction.objects.get(vehicle=vid,account="initial vehicle build") # look up the vehicle transaction number
        data['url']="/vehicle/new_vehicle/%s/%s/" % (vid,vt.id)
        return HttpResponse(json.dumps(data))
    else:
        return HttpResponse(-1)

@SetUser
@login_required()
def new_vehicle(request, vid=None,vt=None): # def create_vehicle (alt_name)

    """View where VP creates new vehicles."""
    if request.method == "POST" and request.is_ajax():
        if request.POST['fxn']=="submit" and not Turn.is_processing():
            try:

                if request.POST.has_key('vt'):
                    # this case occurs if a copy slate vehicle is edited
                    vt = request.POST['vt']
                    vt = VehicleTransaction.objects.get(id=vt)
                    vt.reverse()
                dict={'status':'pass'}
                if request.user.balance <= 0:
                    dict['status']="fail"
                    dict['msg']="You do not have enough money."
                    data = json.dumps(dict)
                    return HttpResponse(data)

                # set up a new vehicle
                # check for legalna_name
                name=request.POST['name']
                out =Vehicle.legal_name(request.user,name)
            except Exception,e:
                # catch any error here to let the browser know
                # otherwise this is returned as a 500.
                out = {'status':"False",'msg':("Error occured: %s - %s" % (Exception,e))}

            if out['status']=="False":
                dict = {}
                dict['status']="fail"
                dict['msg']= out['msg']
                data = json.dumps(dict)
                return HttpResponse(data)

            data = {}
            for k in request.POST.keys():
                data[str(k)]=str(request.POST[k])
            data = request.user.builder(**data)
            data = Vehicle.prep(**data)
            veh = Vehicle(**data)
            try:
                veh.save()
            except ValueError,e:
                print e
                dict={'status':'fail','msg':"Vehicle must have a positive MPG."}
                return HttpResponse(json.dumps(dict))

            return HttpResponse(json.dumps(dict))

        else:
            dict={'status':'fail'}
            return HttpResponse(json.dumps(dict))

    elif request.method == "GET" and request.is_ajax():
        if request.GET['fxn']=="update_attrs":
            data = {}
            try:
                # a renewed vehicle - reconstruct a data dict
                # from the prior vehicle.
                veh = Vehicle.objects.get(id=int(request.GET['vid']))
                for key in veh.__dict__.keys():
                    if key in ['style','performance','name','run','margin','drivetrain_id']:
                        data[key]=veh.__getattribute__(key)

                        # convert drivetrain_id key to drivetrain
                        if key=="drivetrain_id":
                            data['drivetrain']=data[key]
                            del data[key]

            except (ValueError,KeyError): # vid does not exist or is undefined
                # this is a brand new vehicle,
                # or it is a renewed vehicle that has been modified.

                for k in request.GET.keys():
                    data[str(k)]=str(request.GET[k])


            veh = request.user.builder(**data)
            #veh['drivetrain']=veh['drivetrain'].name
            veh['drivetrain']=str(veh['drivetrain'].id)
            del veh['producer']

            try:
                if settings.FEEBATES:
                    veh['feebate_cost']= veh['feebate']
            except AttributeError:
                veh['feebate_cost']=0
            veh['copied']=True
            data = json.dumps(veh)
            return HttpResponse(data)
        elif request.GET['fxn']=="check_name":
            ### validate that the name is legal
            # must begin with a letter
            # must be under 20 chars
            # MOVE THIS INTO models as check_name
            name=request.GET['arg']
            out =Vehicle.legal_name(request.user,name)

            data = json.dumps(out)
            return HttpResponse(data)

        else:
            return -1

    else:
       # show the screen

        # get a list of the drivetrains and cost for the user, also mpg.
        context = request.user.home_context()
        context['renewed']=False
        if vid!=None:
            context['vid']=vid
            context['vehicle'] = Vehicle.objects.get(id=vid)
            context['renewed']=True

        #context['scaling_function'] = settings.VEHICLE_SCALING_FXN
        context['gas_guzzler_mpg'] = settings.GAS_GUZZLER
        context['gas_guzzler_tax'] = settings.GAS_GUZZLER_TAX
        u = request.user
        #context['style_level_cost'] = u.base_style_cost - 2*u.active_rd("style")
        #context['performance_level_cost'] = u.base_performance_cost - 2*u.active_rd("performance")
        #context['emissions_cost'] = settings.EMISSIONS_LEVEL_COST
        context['performance']=settings.VEH_ATTR['performance']
        context['style']=settings.VEH_ATTR['style']
        runs = []
        context['step'] = settings.VEHICLE_SCALING_STEP

        vp_max = max(settings.VEHICLE_MAX_RUN, (request.user.capacity / 2.0))
        context['max'] = min(vp_max,request.user.remaining_capacity)
        if not vt==None:
            context['vt']=vt


        #context['runs'] = settings.VEHICLE_RUNS
        context['drivetrains'] = Drivetrain.objects.all()
        context['feebates'] = settings.FEEBATES
        return render_to_response('vp/new_vehicle.html',context, request)


@SetUser
def complete(request):
    """Register the user as having completed his turn. This does not actually stop him
    from playing further, just notifies that he is done."""

    try:
        # only create an entry if it does not exist.
        out = TurnComplete.objects.get(turn=Turn.cur_turn(),user=request.user)
    except TurnComplete.DoesNotExist:
        obj = TurnComplete(turn=Turn.cur_turn(),user=request.user)
        obj.save()

    return HttpResponseRedirect("/home")

@SetUser
def fuel_station(request):
    """Provides information about fuel prices and history."""



    context=request.user.base_context()


    fuel_data = session_mng((Turn.cur_turn(),'fuel_market_data'),Fuel.fuel_market_data,request)
    if len(fuel_data['data']) > 7:
        var = len(fuel_data['data'])
        fuel_data['data']=fuel_data['data'][var-7:]
        fuel_data['price']=fuel_data['price'][var-7:]
        fuel_data['labels']=fuel_data['labels'][var-7:]


    charts = session_mng((Turn.cur_turn(),'charts'),FuelRecord.fuel_volume_charts,request)

    context['bar_width']=min(30,int(230.0/(Turn.cur_turn()+0.0)))
    context['fuel_history'] = fuel_data['data']
    if fuel_data['labels'][0]=="04":
        context['fuel_history'][0]= [x * 1.03 for x in context['fuel_history'][1]]
    context['history_labels'] = fuel_data['labels']
    context['long_labels'] = fuel_data['long_labels']
    context['history_legend']=fuel_data['legend']
    context['fuel_cost']=fuel_data['cost']
    context['price_history']=fuel_data['price']
    cafes = dict((k, v) for k, v in settings.CAFE_LEVELS.iteritems() if k <= 12 + Turn.cur_year())

    context['cafes']=cafes

    #context['global_ledger']=session_mng((Turn.cur_turn(),'global_ledger'),VehicleProducer.global_ledger,request)
    context['global_ledger']=VehicleProducer.global_ledger(turn=Turn.cur_turn())

    for val in ['gas','diesel','elec','h2']:
        context["%s_price" % val]=FuelRecord.last(val)

    e_data = Fuel.elec_market_data()
    context['e_data']=e_data['data']
    context['e_labels']=e_data['labels']
    context['e_legend']=e_data['legend']
    context['charts']=charts
    return render_to_response("global/fuel_station.html",context, request)




@SetUser
def fleet_info(request):
    """Provides information about the make up of the fleet."""

    context=request.user.base_context()

    data = session_mng((Turn.cur_turn(),'fleet_data'),Fleet.fleet_data,request)

    #context['drivetrain_quantity']=data['quantity']
    context['drivetrain_quantity']=session_mng((Turn.cur_turn(),'plot_drivetrain_data'),VehicleProducer.plot_drivetrain_data,request)
    context['drivetrain_name']=data['drivetrain']

    context['vp_profits']=VehicleProducer.vp_profits()
    context['years'] = data['years']
#    context['drivetrain_by_fuel'] =  data['drivetrain_by_fuel']
    context['fuel_labels'] = Fuel.fuel_names()

    #context['vps']=data['vps']
    context['vps']=session_mng((Turn.cur_turn(),'plot_market_data'),VehicleProducer.plot_market_data,request)
    context['vps_counts']=data['vps_counts']

    return render_to_response("global/fleet_info.html",context, request)




#def adjust_vmt(request,type):
#    """Part of consumer prefs. Reduce current_vmt_goal dependent on type of request."""

@SetUser
@login_required
def consumer_transactions(request):
    """View vehicle transaction records for this VP"""

    context = request.user.home_context()
    v = VehicleTransaction.objects.filter(buyer=request.user)
    for o in v:
        o.year = Turn.turn_to_year(o.turn)
    context = request.user.home_context()
    context['vehicle_buys'] = v

    trans = Transaction.objects.filter((Q(seller=request.user)|Q(buyer=request.user))).\
        exclude((Q(account="none")|Q(account="fuel")|Q(account="buy")))# & (Q(account="consumer allowance") |
        #Q(account = "disposed income")|(Q(account="player transaction"))) u)
    #trans = Transaction.objects.filter(seller=request.user,account="consumer allowance")
    for o in trans:
        o.year = Turn.turn_to_year(o.turn)

    context['transactions'] = trans

    fuels = FuelTransaction.objects.filter(buyer=request.user,quantity__gt=0)
    for f in fuels:
        f.year = Turn.turn_to_year(f.turn)
        f.quantity = int(f.quantity/1000)*1000

    context['fuels'] = fuels
    return render_to_response('consumer/transactions.html',context, request)



@SetUser
@login_required
def glossary(request):
    """Prints a gloassary of terms used in the game."""
    context=request.user.base_context()


    return render_to_response("global/glossary.html",context, request)

@SetUser
@login_required

def consumer_info(request):
    """Prints public info about the consumer players."""

    context=request.user.home_context()

    context['consumers']=Consumer.objects.all()
    context['fps']=FuelProducer.objects.all()
    context['vps']=VehicleProducer.objects.all()


    return render_to_response("global/consumer_info.html",context, request)



@SetUser
@login_required
def comment(request):
    """A screen to write comments about the game on."""
    context = request.user.home_context()

    if request.method == "POST":
        form = CommentForm(request.POST)
        # do conversions here.
        if form.is_valid():
            com = Comment(comment=form.cleaned_data['comment'], user=request.user, turn=Turn.cur_turn())
            com.save()

            return HttpResponseRedirect("/home")

    else:
        return render_to_response("global/comment.html",context, request)




@SetUser
@login_required
def email(request):
    """A screen to submit email address on."""
    context = request.user.home_context()

    if request.method == "POST":
        form = EmailForm(request.POST)
        f = forms.EmailField()
        # do conversions here.
        if form.is_valid():
            try:
                f.clean(form.cleaned_data['email'])
            except forms.ValidationError:
                context['message']  = "** Invalid email address format. Please re-enter it. **"
                return render_to_response("global/email.html",context, request)

            try: #check for existing address
                out = Email.objects.get(email=form.cleaned_data['email'])
            except Email.DoesNotExist: # email does not exist
                com = Email(email=form.cleaned_data['email'], user=request.user)

                com.save()

            return HttpResponseRedirect("/home")
        else:
            context['message']  = "* Invalid form submission. *"
            return render_to_response("global/email.html",context, request)




    else:
        return render_to_response("global/email.html",context, request)

@SetUser
@login_required
def score(request):
    """Show the scores for the players."""
    context = request.user.home_context()

    try:
        scores=ConsumerScore.objects.filter(turn=Turn.last_turn())
        for sc in scores:
            sc.year = Turn.turn_to_year(sc.turn)

        context['con_cur_scores']=scores

    except ConsumerScore.DoesNotExist:
        pass

    context['consumers']=Consumer.objects.all()

    return render_to_response("global/score.html",context, request)

@SetUser
@login_required
def game_guide(request):
    """Game guide screen."""
    context = request.user.home_context()

    return render_to_response("global/game_guide.html",context, request)

@SetUser
@login_required
@dtrans.commit_on_success
def build_refinery(request):
    """Refinery building screen for FP."""

    if request.method=="POST":
        id = request.POST['ref_id']
        rm = RefineryModel.objects.get(id=id)
        a = Asset(refinery=rm,status_code=1,
                  activation_turn=(rm.build_time+Turn.cur_turn()),
                  owner=request.user,
                  builder=request.user)
        # create the Asset!
        a.save()
        amount = round((rm.get_cost(request.user)+0.0)/10.0**3,3)
        tr = AssetTransaction(asset=a,buyer=request.user,seller=uget("admin"),
                              amount=amount,turn=Turn.cur_turn(),
                              comment="Build Refinery",
                              account="Build Refinery")
        tr.save()
        tr.process()
        return HttpResponseRedirect("/home")

    else:
        context = request.user.home_context()
        rs = RefineryModel.objects.all()

        context['refinery_life']=settings.REFINERY_LIFE
        context['refinery_life_years']=settings.REFINERY_LIFE * settings.YEAR_TURN_LEN
        turns = context['refinery_life']
        years = context['refinery_life_years']

        # fix the build costs up
        for r in rs:
            r.avail = Turn.turn_to_year(Turn.cur_turn()+r.build_time)
            r.build_time=r.build_time*settings.YEAR_TURN_LEN

            r.cost = r.get_cost(request.user)
            r.payback = r.total_payback_turns(request.user)
        context['refineries']=rs

        return render_to_response('fp/build_refinery.html',context,request)

@SetUser
@login_required
@dtrans.commit_on_success
def buy_refinery(request):
    """List refineries for sale. Allows fuel producers to buy them."""
    if request.method=="POST" and request.is_ajax() and not Turn.is_processing():
        if request.POST['fxn']=="buy_refinery":
            try:
            # do asset transaction
                a = request.POST['arg']
                asset = Asset.objects.get(id=a)
                amt = asset.sale_price/10.0**3
                desc = "Refinery purchase: %s %s from %s" % (asset.refinery.name,
                                                             asset.refinery.fuel,
                                                             asset.owner)

                at = AssetTransaction(buyer=request.user,seller=asset.owner,turn=Turn.cur_turn(),
                                      amount=amt,asset=asset,desc=desc,comment="Refinery Transaction",
                                      account="Refinery Purchase")

                at.save()
                at.process()


            except ValueError:
                return HttpResponse(-2)

            return HttpResponse(1)
        else:
            return HttpResponse(-1)

    else:
        context = request.user.home_context()
        context['assets']=Asset.objects.filter(for_sale=True,sale_price__gt=0)

        return render_to_response('fp/buy_refinery.html',context,request)

@SetUser
@login_required
def manage_refinery(request):
    """Flips the status from 1 to 2 or vice versa for refineries via a ajax GET."""
    if request.is_ajax():
        fuel = 0;
        try:
            message="none"
            if request.POST['fxn']=="schedule":
                id = request.POST['asset_id']
                asset = Asset.objects.get(id=id)
                lookup = {'active':2,'inactive':1,'eliminated':0}
                code = lookup[request.POST['arg']]
                asset.status_code = code
                asset.save()

                if code==0:
                    # deleting the asset, so redraw the whole screen
                    message="reload"
                fuel=asset.refinery.fuel
            elif request.POST['fxn']=="update":
                fuel=request.POST['arg']
            # send back dict of fuel name, active_capacity and margin

            dict = {'fuel':fuel,
                    'active_capacity':round(request.user.get_active_cap(fuel)/10.0**6,2),
                    'capacity':round(request.user.get_cap(fuel)/10.0**6,2),
                    'op_cost':request.user.get_op_cost(fuel),
                    'message':message,
                    'margin':round(request.user.get_margin(fuel),3)}
            #obj = request.user.get_active_cap(asset.refinery.fuel)
            data = json.dumps(dict)
            return HttpResponse(data)
        except Exception,e:
            logging.debug("Unexpected error:", e)
            return HttpResponse(-1)
#        except Exception:
#            return HttpResponse(-1)


@SetUser
@login_required
def convert_gas_diesel(request):
    """Converts oil plant from gas to diesel or vice versa."""
    if request.is_ajax() and not Turn.is_processing():

        id = request.POST['asset_id']
        asset = Asset.objects.get(id=id)
        fuel = request.POST['fuel'].strip()
        if asset.is_oil_plant:
            # find the equivalent RefineryModel of type fuel
            # and make that the new refinery
            new = RefineryModel.objects.get(fuel=fuel,capacity=asset.refinery.capacity)
            asset.refinery=new
            asset.save()
        else:
            raise Exception("Cannot convert a non-oil plant to gas/diesel.")

        return HttpResponse(1)

@SetUser
@login_required
def list_refinery(request):
    """List or delist a refinery. Args are asset_id,fxn=(list|delist),\
        and price, if a list."""

    if request.is_ajax() and not Turn.is_processing():
        id = request.POST['asset_id']
        asset = Asset.objects.get(id=id)
        if request.POST['fxn']=="list":
            asset.for_sale=True
            asset.sale_price=request.POST['price'].strip()
        elif request.POST['fxn']=="delist":
            asset.for_sale=False
            asset.sale_price=-1
        else:
            return HttpResponse(-1)

        asset.save()

        return HttpResponse(1)






