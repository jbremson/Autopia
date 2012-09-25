"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""
from django.contrib.auth.models import Group
from auto.app.models import *
from auto.app.game_setup import *
from django.test import TestCase
from auto.plotkin.models import get_vehicle_fxn,f2D, D2f, get_level_fxn

import pdb

#
#class TestFleetBuild(TestCase):
#
#    def setUp(self):
#        selCreateAll(full=True)
#
#    def test_fleet_build(self):
#        """Test to see if I can add a fleet entry without a vehicleTransaction id so I can
#        use that ability to build game initialization fleet."""
#
#        v1 = uget("mega")
#        c1 = uget("family")
#        ad = uget("admin")
#
#        veh = v1.dummy()
#        veh.price=1
#        veh.save()
#
#        fl = Fleet(vehicle=veh,owner=c1,turn=9,fuel=veh.drivetrain.fuel,
#                   quantity=100,points=0)
#
#        fl.save()
#        self.assertEqual(c1.fleet_size,100,"Error: wanted: 100 got: %s" % c1.fleet_size)

class Mock(object):
    # by Joel Bremson - 2011
    """Will instantiate an object with properties sent as a **kwargs."""
    __recall__ = {}

    def __init__(self,**kwargs):
        for key in kwargs.keys():
            setattr(self, key, kwargs[key])


    def add_method(self,name,fxn):
        """Add <fxn> with <name> to instance. First arg of <fxn> must be 'self'."""
        setattr(self,name,fxn)

    @classmethod
    def replace(cls, obj, target, replacement):
        """Replace the method <target> on <obj> with <replacement> fxn. This allows you to change the behavior
        of an existing unrelated class. """
        Mock.__recall__[(obj,target)]=getattr(obj,target)
        obj.__dict__[target]=replacement

    @classmethod
    def replace_property(cls, obj, target, replacement):
        """Replace the property <target> on <obj> with <replacement> fxn. This allows you to change the behavior
        of an existing unrelated class. """
        Mock.__recall__[(obj,target)]=getattr(obj,target)
        obj.__dict__[target]=property(replacement)

    @classmethod
    def and_return(cls, obj, target, val):
        """Return <val> when obj.target (and target is a method) is called."""

        Mock.__recall__[(obj,target)]=getattr(obj,target)
        def foo(*args,**kwargs):
            return val

        cls.replace(obj, target, foo)

    @classmethod
    def reset_obj(cls,obj,target):
        """Reset object to its original state."""
        cls.replace(obj,target,Mock.__recall__[(obj,target)])
        del(Mock.__recall__[(obj,target)])

    @classmethod
    def reset_all(cls):
        """Reset all back to original methods."""
        for key in Mock.__recall__.keys():
            cls.replace(key[0],key[1],Mock.__recall__[key])

        Mock.__recall__ = {}



def get_award_rec(vp,base_name,turn=None):
    """Wrapper to get_r"ec that just adds to base name to turn it into the rule_name."""

    return get_rec(vp,"%s R&D Award" % base_name,turn)

def get_rec(vp,rule_name,turn=None):

    """Get the record rule_name for vp on 'turn'. Default turn is last_turn."""
    if turn==None:
        turn=Turn.last_turn()
    try:
        rec = RandDPointRecord.objects.get(turn=turn,rule__name=rule_name,producer=vp)
    except Exception,e:
        print e
        rec = None
    return rec


def test_area_rec(self,rec,area,points):
    """Test record to see that points are applied to the right area. This only works for non-free point tests."""

    print "Testing %s" % rec.rule.name
    self.assertEqual(points,rec.points,"Error: Wrong number of points for %s. Should have been %s, was %s" % (rec.rule.name,points,rec.points))

#class TestAwards(TestCase):
#
#    def setUp(self):
#          selCreateAll(full=True)
#
#    def test_awards_and_cafe_penalty(self):
#        v1 = uget("euro")
#        v2 = uget("mega")
#        c1 = uget("family")
#        ad = uget("admin")
#
#
#        pig = v2.dummy(**{'run':100,'name':'pig'})
#        pig.mpg=10
#        pig.save()
#
#        vehs = []
#        for dt in ['gas hev','h2','diesel','bev','h2 phev10']:
#            o = v1.dummy(**{'style':12,'performance':12,'drivetrain':dt})
#            o.run=400
#            o.save()
#            vehs.append(o)
#
#        ad.test_advance_turn()
#
#        vt = VehicleTransaction(vehicle=pig,quantity=50,buyer=c1,seller=v2,
#                                amount=float((50.0*pig.price)/10**6),turn=Turn.cur_turn(),
#                                fees=0,desc="testing")
#
#        vt.save()
#        vt.process()
#
#        for veh in vehs:
#            vt = VehicleTransaction(vehicle=veh,quantity=400,buyer=c1,seller=v1,
#                                amount=float((100.0*veh.price)/10**6),turn=Turn.cur_turn(),
#                                fees=0,desc="testing")
#
#            vt.save()
#            vt.process()
#
#        ad.test_advance_turn()
#
#        print "==========Testing cafe penalty==============="
#
#        cafe = Fuel.objects.get(turn=Turn.cur_turn()).cafe
#        test_val = (cafe - pig.mpg)*pig.run*10*settings.CAFE_PENALTY /10**6
#
#        tr=Transaction.objects.get(account="CAFE penalty") # should be the only one
#        self.assertEqual(test_val,tr.amount,"Error: should be: %s : was: %s" % (test_val,tr.amount) )
#
#
#        print "==========Test awards========================"
#
#
#        rec = get_award_rec(v1,'HEV')
#        test_area_rec(self,rec,'hev',2)
#
#        rec = get_award_rec(v1,'Gas')
#        test_area_rec(self,rec,'gas',1)
#
#        #check to see that there is a RandD record for 1 point on gas
#        # as a sanity check on record
#
#        gas=RandD.objects.filter(producer=v1,turn=Turn.last_turn(),gas=1)
#
#        self.assertEqual(gas.count(),1,"Error: should be: 1 was: %s" % gas.count())
#
#
#
#        rec = get_award_rec(v1,'Diesel')
#        test_area_rec(self,rec,'diesel',1)
#
#
#        rec = get_award_rec(v1,'BEV')
#        test_area_rec(self,rec,'bev',4)
#
#        rec=get_award_rec(v1,'H2')
#        test_area_rec(self,rec,'h2',8)
#
#        #check out the PHEV - should have two records, one for hev and one for bev
#        phev = RandDPointRecord.objects.filter(rule__name="PHEV R&D Award",rule__area="bev/hev")
#
#        self.assertEqual(phev.count(),2,"Error: count of phevs should be: 2 was: %s" % phev.count())


class TransactionTest(TestCase):
    """Test the various transactions."""

    def setUp(self):
        dt = Drivetrain(name='gas',phev=False)
        dt.save()
        a =  Admin(username="admin")
        a.save()
        return 1

    def test_basic_transaction(self):
        print "Running basic_transaction..."
        buyer=AutopiaUser(username='buyer',balance=10)
        buyer.save()
        seller=AutopiaUser(username='seller',balance=10)
        seller.save()

        tr = Transaction(buyer=buyer,seller=seller,amount=1,desc='foo',fees=0.0)
        tr.save()
        #tr.process()

        self.assertEqual(seller.balance,11)
        self.assertEqual(buyer.balance,9)

    def test_vehicle_transaction(self):
        print "Running a vehicle transaction."
        buyer=Consumer(username='buyer',balance=10)
        buyer.save()
        seller=VehicleProducer(username='seller',balance=10)
        seller.save()
        veh = Vehicle(producer=seller,style=10,performance=10, mpg=20, \
                      drivetrain=Drivetrain.objects.get(name='gas'), \
                      price=10000,production_cost=0,run=100,turn=Turn.last_turn())

        veh.save()

        vt = VehicleTransaction(vehicle=veh,buyer=buyer,seller=seller,
                    quantity=100,amount=1,account='buy')
        vt.save()
        self.assertEqual(seller.balance,11)
        self.assertEqual(buyer.balance,9)

        veh2 = Vehicle(producer=seller,style=10,performance=10, mpg=20, \
                drivetrain=Drivetrain.objects.get(name='gas'), \
                price=10000,production_cost=9000,run=100,turn=Turn.last_turn())

        veh2.save()
        self.assertEqual(seller.balance,10.1)

        vt = VehicleTransaction(vehicle=veh2,buyer=buyer,seller=seller,
                    quantity=100,amount=1,account='buy')
        vt.save(force=True)
        self.assertEqual(seller.balance,11.1)
        self.assertEqual(buyer.balance,8)


        FleetSnapshot.process()
        o = seller.customers(turn_gte=0)
        self.assertEqual(len(o),1)
        self.assertEqual(o[0][1],200) # bought 100 2x

        year = Turn.calc_next_turn_year()
        new_turn = Turn.cur_turn() + 1
        T = Turn(turn=new_turn, year=year, status="processing")
        T.save()
        self.assertEqual(buyer.last_turn_price_average(turn=0),10000)
        VPSalesSummary.summarize()




    def test_fuel_transaction(self):
        print  "Testing fuel transactions..."

        admin=AutopiaUser.objects.get(username='admin')
        fp = FuelProducer(username='f1',balance=10)
        fp.save()


        ft = FuelTransaction(buyer=admin,seller=fp,amount=1,quantity=10,turn=Turn.cur_turn(),\
                fuel="gas",account="fuel")
        ft.save()
        self.assertEqual(fp.balance,11)

    def test_asset_transaction(self):
        print "Test asset transactions..."
        fp1 = FuelProducer(username='f1',balance=10)
        fp1.save()
        fp2 = FuelProducer(username='f2',balance=10)
        fp2.save()
        rm = RefineryModel(size=1,fuel="gas",capacity=1,base_cost=1,
                           build_time=1,margin=1,active_cost=1,inactive_cost=1,
                           elim_cost=1)
        rm.save()

        asset = Asset(refinery=rm, status_code=2, activation_turn=1,
                        owner=fp1,builder=fp1)
        asset.save()

        at = AssetTransaction(buyer=fp2,seller=fp1,amount=1,asset=asset)
        at.save()

        self.assertEqual(fp1.balance,11)
        self.assertEqual(fp2.balance,9)
        self.assertEqual(asset.owner,fp2)
        self.assertNotEqual(asset.owner,fp1)


#        def aggregate(*args,**kwargs):
#            return 0

        m = Mock()
        m.aggregate = lambda x: dict(turn__min=0);

        Mock.and_return(Turn.objects,'all',m)
        Mock.and_return(Asset.objects,'all',Mock(aggregate=lambda x:dict(activation_turn__max=5)))
#
        self.assertEqual(Turn.objects.all().aggregate({})['turn__min'],0)
        self.assertEqual(Asset.objects.all().aggregate({})['activation_turn__max'],5)
        o = Asset.capacity_data()
        # I don't understand how this works in this situation - but
        # it appears to work correctly in practice.
        Mock.reset_all()

    def test_balance_history(self):
        vp = VehicleProducer()
        Mock.and_return(VPSumData.objects,'filter',[Mock(profit=5),Mock(profit=5)])
        self.assertEqual(sum(vp.balance_history()),45)

    def test_density_hash(self):
        hash = {'a':1,'b':2,'c':3}
        Mock.and_return(random,'randint',1)
        self.assertEqual(density_hash(hash),'a')
        Mock.and_return(random,'randint',6)
        self.assertEqual(density_hash(hash),'b')
        Mock.and_return(random,'randint',3)
        self.assertEqual(density_hash(hash),'c')









class FleetReportTest(TestCase):
    """Test Consumer.fleet_report."""



    def setUp(self):
        return 1

    def test_1(self):



        def vt_filter(*args,**kwargs):

            def excluder(*args,**kwargs):
                # this is where the vts come from to analyze
                out = []
                out.append(Mock(quantity=100,amount=2.0, vehicle=Mock(drivetrain=Mock(name='gas'),style=5,performance=5,mpg=30)))
                out.append(Mock(quantity=100,amount=4.0, vehicle=Mock(drivetrain=Mock(name='gas'),style=15,performance=10,mpg=15)))
                return out

            #return FakeVTSet()
            out = Mock()
            out.add_method('exclude',excluder)
            return out

        Mock.replace(VehicleTransaction.objects,'filter',vt_filter)
        #vto = VehicleTransaction.objects
        #vto.filter = vt_filter

        young = Consumer(username="young",style_weight=5,performance_weight=5,mpg_weight=10)
        young.save()


        out = FleetReport.fleet_report(young)
        self.assertEqual(round(out.performance_sd,1),2.5,"Failed performance.sd is supposed to equal 2.5 but equals %s " % out.performance_sd)
        self.assertEqual(out.total,200,"Failed: Should have been 200 was %s " % out.total)

        # testing quick_score


        def get_vehicle(*args, **kwargs):
            return Mock(style=10,performance=10,mpg=30,price=25.4,name="Mooker")

        Mock.replace(Vehicle.objects,'get',get_vehicle)
        veh = Vehicle.objects.get(id=10)
        self.assertEqual(veh.style,10)
        self.assertEqual(int(young.percent_attr('style')*100.0), 25)

        Mock.and_return(FleetReport.objects,'filter',1)
        self.assertEqual(FleetReport.objects.filter(),1)


        Mock.and_return(FleetReport.objects,'filter',[])
        print "Testing a FleetReport that is empty."
        # This is my comment let it go.
        # Here is another cmment to delete. Testing the
        # things. Does it work. Seems to?

        self.assertEqual(young.quick_score_vehicle(vid=1),50)

        print "Testing a FleetReport with one value. "

        flts = Mock(style=5,performance=10,mpg=20)
        for val in vars(flts).keys():
            setattr(flts,val+'_sd',1)

        Mock.and_return(FleetReport.objects,'filter',[flts])
        # should equal
        # out = 2.5 * 5 + 2.5 * 5 + 2.5 * 10

        self.assertEqual(young.quick_score_vehicle(vid=1),37)


        blts = Mock(style=5,performance=10,mpg=20)
        for val in vars(blts).keys():
            setattr(blts,val+'_sd',1)
        Mock.and_return(FleetReport.objects,'filter',[flts,blts])
        veh = get_vehicle()
        veh.style=5
        Mock.and_return(Vehicle.objects,'get',veh)
        self.assertEqual(young.quick_score_vehicle(vid=1), 22)


        print "testing veil."
        # this one is dangerous because it is possible that veiling won't actually change the weights."
        young.veil()

        self.assertEqual(young.veiled,True)
        self.assertEqual(young.save(),None) # don't save a veiled Consumer


#        def fleet_report_filter(*args,**kwargs):
#            # return some stuff from FleetReport.objects.filter(...)

class FakeFR(object):

    def last(self,fuel):
        if fuel=="elec":
            return 1
        else:
            return 2

class MpgCalcTest(TestCase):
    """Test MPG / VMT calculations for PHEVs."""

    def setUp(self):
        t =Turn(turn=1,year=2004)
        t.save()
        f = FuelRecord(fuel='gas',turn=1,demand=10,supply=10,base_price=1,actual_price=2)
        f.save()
        f = FuelRecord(fuel='elec',turn=1,demand=10,supply=10,base_price=1,actual_price=1)
        f.save()
        return True

    def make_phev(self,range,mpg=100):
        v = Vehicle(drivetrain=Drivetrain(fuel='gas',phev=range),mpg=mpg,producer=VehicleProducer(username="tester"))
        return v

    def test_phev(self):
        test_mpg = 100
        v = self.make_phev(10,test_mpg)
        Mock.and_return(v,"nonev_mpg",50)
        self.assertEqual(v.drivetrain.phev,10)
        self.assertEqual(v.mpg,100)
        nonev = v.nonev_mpg()
        ev = v.ev_mpg()
        print "nonev_mpg = %s " % nonev
        print "ev_mpg = %s " % ev
        uf = settings.PHEV['10']
        check = uf * ev + (1-uf)*nonev
        print "check 100 mpg = %s" % check
        self.assertEqual(check,100)
        self.assertAlmostEqual(v.ev_gge(15000),10)
        self.assertAlmostEqual(v.nonev_gge(15000),240)

        comp = 4*(v.ev_gge(15000) + v.nonev_gge(15000)*2)
        self.assertAlmostEqual(v.op_cost, comp)


class MockTest(TestCase):
    """For the Mock webpage I made."""
    def setUp(self):
        return True

    def test_mock(self):
        m=Mock(foo=5,bar="yes",random=lambda x,y: 1)
        self.assertEqual(m.bar,"yes")
        self.assertEqual(m.random(1,10),1)

    def test_mock2(self):
        m=Mock(foo=Mock(color="purple") )
        self.assertEqual(m.foo.color,"purple")

#class FirstSales(TestCase):
#    """More R&D awards testing."""
#
#    def setUp(self):
#        selCreateAll(full=True)
#
#
#    def test_first_sales(self):
#
#        """Test the first sales awards."""
#
#        v1 = uget("euro")
#        v2 = uget("asian")
# foo this is good.
#        c1 = uget("family")
#        ad = uget("admin")
#
#        vehs =[]
#        for dt in ['h2','bev']:
#            o = v1.dummy(**{'style':12,'performance':12,'run':100,'drivetrain':dt})
#            o.save()
#            vehs.append(o)
#
#        ad.test_advance_turn()
#
#        for veh in vehs:
#            vt = VehicleTransaction(vehicle=veh,quantity=100,buyer=c1,seller=v1,
#                                amount=float((100.0*veh.price)/10**6),turn=Turn.cur_turn(),
#                                fees=0,desc="testing")
#
#            vt.save()
#            vt.process()
#
#
##        val = VehicleTransaction.first_sale(**{'seller':v1,'vehicle__drivetrain__fuel':'h2'})
##
##        self.assertEqual(val,True,"Error: Should have been True, was False.")
#
#        ad.test_advance_turn()
#
#        rec = RandDPointRecord.objects.filter(turn=Turn.last_turn(),rule__name="My First H2 Sale",producer=v1)
#        self.assertEqual(1,rec.count(),"Error: Wrong number of First H2 Sale refs. Shold be 1, was %s" % rec.count())
#
#
#        rec = RandDPointRecord.objects.filter(turn=Turn.last_turn(),rule__name="My First BEV Sale",producer=v1)
#        self.assertEqual(1,rec.count(),"Error: Wrong number of First BEV Sale refs. Shold be 1, was %s" % rec.count())
#
#
#class TestRules(TestCase):
#
#
#
#    def setUp(self):
#        selCreateAll(full=True)
#
#
#    def test_rules(self):
#        v1 = uget("euro")
#        v2 = uget("asian")
#        c1 = uget("family")
#        ad = uget("admin")
#
#        veh_1 = v1.dummy(**{'style':12,'performance':12,'run':100})
#        veh_1.production_cost=10000
#        veh_1.price=11000
#        veh_1.save()
#        veh_2 = v2.dummy(**{'run':100})
#        veh_2.production_cost=10000
#        veh_2.price=10500
#        veh_2.save()
#
#
#        ad.test_advance_turn()
#        #at this point there should be no points awarded
#
#        o =  RandDPointRecord.objects.all()
#        self.assertEqual(o.count(),0,"Error: There should be no RandDPointRecords. There are %s" % o.count())
#
#        vt = VehicleTransaction(vehicle=veh_1,quantity=100,buyer=c1,seller=v1,
#                                amount=float((100.0*veh_1.price)/10**6),turn=Turn.cur_turn(),
#                                fees=0,desc="testing")
#        vt.save()
#        vt.process()
#
#        vt = VehicleTransaction(vehicle=veh_2,quantity=100,buyer=c1,seller=v2,
#                                amount=float((100.0*veh_1.price)/10**6),turn=Turn.cur_turn(),
#                                fees=0,desc="testing")
#        vt.save()
#        vt.process()
#
#
#        self.assertEqual(VehicleTransaction.points_since_last_turn(100,**{'seller':v1,
#                                    'vehicle__drivetrain__fuel':'gas'}),1,
#                                    "Error: mod_count failed.")
#
#        val = VehicleTransaction.first_sale(**{'seller':v1,'vehicle__drivetrain__fuel':'gas'})
#
#        self.assertEqual(val,True,"Error: Should have been True was False.")
#
#        val = VehicleTransaction.first_sale(**{'seller':v1,'vehicle__drivetrain__bev':True})
#
#        self.assertEqual(val,False,"Error: Should have been False, was True.")
#        ad.test_advance_turn()
#        # refresh
#
#
#        v1=uget("euro")
#        v2=uget("asian")
#
#        # both asian and euro start with 10 rd points in selenium_setup
#        self.assertEqual(v1.rd_points,11,"Error: v1 did not refresh.")
#
#        rec = RandDPointRecord.objects.get(turn=Turn.last_turn(),producer=v1,rule__name="Revenue Points")
#        self.assertEqual(1,rec.points,"Error: Wrong number of revenue points. Should have been \
#            1, was %s" % rec.points)
#
#        # test SytleLeaderRule
#        rec = RandDPointRecord.objects.filter(turn=Turn.last_turn(),rule__name="Style Leader",producer=v1)
#        self.assertEqual(1,rec.count(),"Error: Wrong number of style leader refs. Shold be 1, was %s" % rec.count())
#
#        rec = RandDPointRecord.objects.filter(turn=Turn.last_turn(),rule__name="Performance Leader",producer=v1)
#        self.assertEqual(1,rec.count(),"Error: Wrong number of performance leader refs. Shold be 1, was %s" % rec.count())
#
#        rec = RandDPointRecord.objects.filter(turn=Turn.last_turn(),rule__name="Style Laggard",producer=v2)
#        self.assertEqual(1,rec.count(),"Error: Wrong number of style laggard refs. Shold be 1, was %s" % rec.count())
#
#        rec = RandDPointRecord.objects.filter(turn=Turn.last_turn(),rule__name="Performance Laggard",producer=v2)
#        self.assertEqual(1,rec.count(),"Error: Wrong number of performance laggard refs. Shold be 1, was %s" % rec.count())
#
#        print "checking to see if the vp have the right number of rd points in their areas."
#
#        v1_style = RandD.sum_area('style',**{'producer':v1})
#        self.assertEqual(2,v1_style,"Error: v1_style is wrong. Should have been 2. Was %s." % v1_style)
#        v1_perf = RandD.sum_area('performance',**{'producer':v1})
#        self.assertEqual(2,v1_perf,"Error: v1_performance is wrong. Should have been 2. Was %s." % v1_perf)
#
#        val = VehicleTransaction.first_sale(**{'seller':v1,'vehicle__drivetrain__fuel':'h2'})
#
#        self.assertEqual(val,False,"Error: Should have been False was True.")
#
## I tried to get this to work but it took too long so I gave up and just
## web tested it and it worked. So there.
##class TestFreePoints(TestCase):
##
##    def setUp(self):
##        selCreateAll(full=True)
##
##
##    def testFreePoints(self):
##        """Test the free points award."""
##        c1=uget("family")
##        v1=uget("euro")
##
##        a=uget("admin")
##
##        print "pre-build balance: %s" % v1.balance
##        veh=v1.dummy(**{'name':'free','run':100})
##        veh.price=10000
##        veh.production_cost=9000
##        veh.save()
##
##        print "post-build balance: %s" % v1.balance
##
##        old_bal = v1.balance
##        a.test_advance_turn()
##        # WORKING RIGHT HERE ON TEST!!!!! 11/10/10
##        buy_vehicle(c1,veh,100,force=True)
##        new_bal = v1.balance
##        print ("old bal %s new bal %s" % (old_bal,new_bal))
##        a.test_advance_turn()
##
##        # now we should have 1 free point given to euro.
##
##        # look to see if euro has one free point.
##        print "hi"
#
#class FirstSaleTest(TestCase):
#
#    def setUp(self):
#        selCreateAll(full=True)
#
#    def first_sale(self):
#        print "Here we test if FirstBEV and FirstH2 work correctly"
#        pass
#
#class T1(TestCase):
#
#    def setUp(self):
#        selCreateAll(full=True)
#
#
#
#    def testVehicleBuilder(self):
#        """Test the VP method - builder."""
#        v1 = uget('mega')
#        dict = {"drivetrain":'gas','style':'10','performance':'10',
#                'run':settings.VEHICLE_MAX_PRODUCTION + 10
#                ,'margin':5, 'name':'car 1'}
#        try:
#            out = v1.builder(**dict)
#        except ValueError:
#            print "*********** caught ValueError in testVehicleBuilder"
#            pass
#
#        dict['run']=settings.VEHICLE_MAX_PRODUCTION
#        out = v1.builder(**dict)
#        data = Vehicle.prep(**out)
#        veh = Vehicle(**data)
#
#        veh.save()
#
#class FuelTests(TestCase):
#    def setUp(self):
#        selCreateAll(full=True)
#
#
#    def test_actual_price(self):
#        """Check if actual_price function works."""
#        print "running test_actual_price..."
#        o = Fuel.actual_price(fuel=None,supply=100,demand=100,P=1,e=0.50)
#        self.assertEqual(o,1,"actual_price #1 failed should have been 1 was %s" % o)
#
#        o = Fuel.actual_price(fuel=None,supply=100,demand=100,P=1)
#        self.assertEqual(o,1,"actual_price #2 failed should have been 1 was %s" % o)
#
#class VehicleTestCase(TestCase):
#    # How to add a group to a user: g = Group(); g.name="foo"; g.save(); u.groups.add(g)
#
#
#    def setUp(self):
#        selCreateAll(full=True)
#
#    def testBuyAttrit(self):
#        """This test runs a test buy. It checks to see that balances are adjusted correctly. It tests
#            fleet attrition runs properly for two turns."""
#
#        c1 = uget("young")
#        v1 = uget("mega")
#        a = uget("admin")
#
#        veh = v1.dummy(**{'name':"foo", 'run':200})
#        veh.production_cost=10000
#        veh.price=10000
#        veh.mpg=10
#        veh.save()
#
#        pdb.set_trace()
#        a = uget("admin")
#        a.test_advance_turn()
#        val = float(100*veh.price)/10**6     # consumer c1 buys 100 of 200 vehicles in stock
#
#        vt = VehicleTransaction(vehicle=veh,buyer=c1,seller=v1, amount=val, quantity=100,account="buy")
#        vt.save()
#
#        print "vt.amount = " + str(vt.amount)
#
#        # check to make sure that the balances are altered on both sides
#        c1.pre = c1.balance
#        v1.pre = v1.balance
#        vt.process()
#
#        self.assertEqual(c1.pre - val, c1.balance, " vt process failed. c1.  pre = " + str(c1.pre) + " post = " + str(c1.balance))
#        self.assertEqual(v1.pre + val, v1.balance, " vt process failed. v1.  pre = " + str(v1.pre) + " post = " + str(v1.balance))
#        vehs = 0
#        for f in Fleet.objects.all():
#            vehs = vehs + f.quantity
#
#        self.assertEqual(vehs,veh.run,"Wrong number of vehicles in the system. Should be 200 is : " + str(vehs))
#
#
#        a.test_advance_turn()
#
#
#        # checking fuel consumption.
#        vehs = 0
#        for f in Fleet.objects.all():
#            vehs = vehs + f.quantity
#
#        self.assertEqual(vehs,93,"Wrong number of vehicles in the system. Should be 100 is : " + str(vehs))
#
#        a.test_advance_turn()
#        print "***** Turn " + str(Turn.cur_turn())
#        vehs = 0
#        for f in Fleet.objects.all():
#            vehs = vehs + f.quantity
#
#        self.assertEqual(vehs,75,"Wrong number of vehicles in the system. Should be 100 is : " + str(vehs))
#
#
#
#
#
#
#
#
#    def testStyleAndPerformanceMeasures(self):
#        c1 = uget("young")
#        c2 = uget("family")
#        v1 = uget("mega")
#        a = uget("admin")
#
#        veh = v1.dummy(**{'name':"foo", 'style':3,'performance':4, 'run':100})
#        veh.production_cost=10000
#        veh.price=10000
#        veh.mpg=10000
#        veh.save()
#
#        veh2 = v1.dummy(**{'name':"bar",'run':100})
#        veh2.save()
#        #veh2 = v1.dummy(name="bar", style=10,performance=10, run=100, producer="mega",turn=Turn.cur_turn(),production_cost=10000,price=10000,mpg=10)
#        val = float(10*veh.price)/10**6  # c1 buys 10 vehicles
#
#
#        a.test_advance_turn()
#
#        vt = VehicleTransaction(vehicle=veh,buyer=c1,seller=v1, amount=val, quantity=10,account="buy")
#        vt.save()
#        vt.process()
#
#
#        vt = VehicleTransaction(vehicle=veh2,buyer=c2,seller=v1, amount=val, quantity=10,account="buy")
#        vt.save()
#        vt.process()
#        self.assertEqual(3,c1.style_average, "style_average failed")
#        self.assertEqual(4,c1.performance_average, "performance_average failed")
#
#        self.assertEqual(6.5,Fleet.style_average(),"Fleet.style_average failed. Should have been 6.5 was %s" % Fleet.style_average())
#        self.assertEqual(7,Fleet.performance_average(),"Fleet.performance_average failed. Should have been 7 was %s" % Fleet.performance_average())
#
#    def testHarmonicMean(self):
#        """Testing if the harmonic mean calculation for the cafe score is right."""
#        v1 = uget("mega")
#        c1 = uget("young")
#        a = uget("admin")
#
#        r = RefineryModel.objects.get(size=4,fuel="gas")
#        f1 = uget("f1")
#        for i in range(0,5):
#            ass = r.create_refinery_for(f1)
#            ass.save()
#            ass.activate()
#
#        v1.balance = 100
#        v1.save()
#        dt = Drivetrain.objects.get(name="gas")
#        veh = Vehicle(name="aa",drivetrain=dt,producer=v1,mpg=1,production_cost=8000\
#            ,price=10000,turn=Turn.cur_turn(),performance=15,style=15,run=100)
#
#        veh.save()
#        self.assertAlmostEqual(v1.balance,99.2,1,"Balance check failed. Should have been 99.2, was %s" %\
#            v1.balance )
#
#
#        veh2 = Vehicle(name="bb",drivetrain=dt,producer=v1,mpg=3,production_cost=8000\
#            ,price=10000,turn=Turn.cur_turn(),performance=15,style=15,run=100)
#
#        veh2.save()
#        self.assertAlmostEqual(v1.balance,98.4,1,"Balance check failed. Should have been 98.4, was %s" %\
#            v1.balance )
#
#        a.test_advance_turn()
#        # vehicles are for sale now
#        # now let's have c1 buy the vehicles.
#        amount = 60*(veh.price + 0.0)/(10**6 * 1.0)
#        vt = VehicleTransaction(buyer=c1,seller=v1,quantity=60,vehicle=veh,amount=amount,account="buy")
#        vt.save()
#        vt.process(0,amount)
#
#        self.assertEqual(99.0,v1.balance,"Wrong balance after vehicle purchased. Should have been 98.9 was %s" % v1.balance)
#
#        vt = VehicleTransaction(buyer=c1,account="buy",seller=v1,quantity=60,vehicle=veh2,amount=amount)
#        vt.save()
#        vt.process(0,amount)
#
#        self.assertEqual(99.6,v1.balance,"Wrong balance after vehicle purchased. Should have been 99.6 was %s" % v1.balance)
#        self.assertEqual(v1.calc_cafe(),1.5,"calc_cafe failed should have been 1.5, was %s" % v1.calc_cafe())
#
#        for sc in VPScore.objects.filter(user=v1):
#            print (vars(sc))
#
#        a.test_advance_turn()
#        # test the  vp scoring while we're here...
#        for sc in VPScore.objects.filter(user=v1):
#            print (vars(sc))
#
#
#    def testBuyFuel(self):
#        c1 = uget("young")
#        v1 = uget("mega")
#        a = uget("admin")
#
#        #veh = Vehicle.dummy(name="foo", style=3,performance=4, run=100, producer="mega",turn=Turn.cur_turn(),production_cost=10000,price=10000,mpg=10)
#
#        dt = Drivetrain.objects.get(name="gas phev40")
#
#        veh = v1.dummy(**{'name':"gas phev40",'drivetrain':'gas phev40',
#             'style':15   ,'performance':15})
#
#        veh.mpg=100
#        veh.production_cost=38000
#        veh.price=42000
#        veh.save()
#
#        r = RefineryModel.objects.get(size=4,fuel="gas")
#        f1 = uget("f1")
#        Asset.objects.all().delete()
#        for i in range(0,5):
#            ass = r.create_refinery_for(f1)
#            ass.save()
#            ass.activate()
#
#        self.assertEqual(2000000,FuelProducer.market_active_cap('gas'),"market_active_cap failed for gas should have been 1200000 was %s" % FuelProducer.market_active_cap('gas'))
#        print "Made new refineries..."
#        #car has been scheduled
#        a.test_advance_turn()
#        # now car has been produced and can be sold
#
##        veh2 = v1.dummy(name="gas phev40",drivetrain="gas phev40",producer="mega",  \
##            mpg=100,turn=Turn.cur_turn(), style=15   ,performance=15,                                    \
##            production_cost=38000,price=42000,run=400)
#        veh2 = v1.dummy(**{'name':"gas phever",'drivetrain':dt,
#             'style':15   ,'performance':15})
#
#        veh2.mpg=100
#        veh2.production_cost=38000
#        veh2.price=42000
#        veh2.save()
#        val = float(100*veh.price)/10**6  # c1 buys 1 vehicles
#
#
#        vt = VehicleTransaction(vehicle=veh,buyer=c1,seller=v1, amount=val, quantity=100,account="buy")
#        vt.save()
#        vt.process()
#
#
#
#
#        self.assertEqual(c1.num_vehs_acquired,100,"Wrong number of vehicles acquired. Should be 100, was %s." % c1.num_vehs_acquired)
#
#              # test quota_ratio
#        val = round(100.0 / (c1.turn_target+0.0),2)
#        self.assertEqual(val,c1.quota_ratio,"qouta_ratio failed. Should have been %s, was %s" % (val, c1.quota_ratio))
#        out = v1.calc_cafe()
#        self.assertEqual(v1.calc_cafe(),100,"Wrong amount - should be 100 for cafe score, was: %s" % v1.calc_cafe())
#        self.assertEqual(v1.global_mpg(),100,"Wrong amount - should be 100 for cafe score, was: %s" % v1.calc_cafe())
#
#
#        mpg_avg = Fleet.objects.average('mpg',**{'owner':c1,'turn':Turn.cur_turn()})
#
#        self.assertEqual(100,mpg_avg,"Wrong mpg average. Expected 100 got %s" % mpg_avg)
#        a.test_advance_turn()
#        # turn has advanced - now we can see the fuel transaction record.
#        print "Checking fuel transactions that occurred in prior turn"
#
#        f = FuelTransaction.objects.get(buyer=c1,amount__gt = 0,fuel="gas")
#
#        self.assertEqual(f.quantity,15000,"Wrong amount of gas bought. Should have been 15000 gal was: " + str(f.quantity))
#
#        f = FuelTransaction.objects.get(buyer=c1,amount__gt = 0,fuel="bev")
#
#        self.assertEqual(f.quantity,11250,"Wrong amount of gas bought. Should have been 11250 gal was: " + str(f.quantity))
#
#        val = float(100*veh.price)/10**6  # c1 buys 1 vehicles
#
#
#        vt = VehicleTransaction(vehicle=veh2,buyer=c1,seller=v1, amount=val, quantity=100,account="buy")
#        vt.save()
#        vt.process()
#
#        val = round(200.0 / (2*(c1.turn_target+0.0)),2)
#        self.assertEqual(val,c1.quota_ratio,"qouta_ratio failed. Should have been %s, was %s" % (val, c1.quota_ratio))
#

