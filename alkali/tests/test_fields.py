# encoding: utf-8

import os
import unittest
import mock
import tempfile
import datetime as dt

from alkali.fields import Field
from alkali.fields import IntField, StringField, BoolField
from alkali.fields import DateTimeField, FloatField, SetField
from alkali.fields import ForeignKey
from alkali.model import Model

from . import MyModel, MyMulti, MyDepModel

class TestField( unittest.TestCase ):

    def tearDown(self):
        MyModel.objects.clear()
        MyMulti.objects.clear()
        MyDepModel.objects.clear()

    def test_1(self):
        "verify class/instance implementation"

        for field in [IntField, BoolField, StringField, DateTimeField, FloatField, SetField ]:
            f = field()
            self.assertTrue( str(f) )
            self.assertTrue( f.properties )

        f = ForeignKey(MyModel)
        self.assertTrue( str(f) )

        m1 = MyModel(int_type=1)
        m2 = MyModel(int_type=2)
        self.assertEqual( id(m1.Meta.fields['int_type']), id(m2.Meta.fields['int_type']) )

    def test_2(self):
        "Field is a meta-like class, it has no value. make sure of that"
        f = IntField()
        with self.assertRaises(AttributeError):
            f.value
        with self.assertRaises(AttributeError):
            f._value

    def test_4(self):
        "test some field properties, verify primary key setting"
        f = IntField()

        for prop in f.properties:
            self.assertFalse( getattr(f, prop) )

        f = IntField( primary_key=True, indexed=True )
        self.assertEqual( True, f.primary_key )
        self.assertEqual( True, f.indexed )

    def test_5(self):
        "test date setting"
        now = dt.datetime.now()
        f = DateTimeField()
        v = f.cast(now)

        self.assertIsNotNone( v.tzinfo )

        v = f.cast(v) # keeps tzinfo
        self.assertIsNotNone( v.tzinfo )

        v = f.cast('now')
        self.assertEqual( dt.datetime, type(v) )

        v = f.loads('2016-07-20 17:53')
        self.assertEqual( dt.datetime, type(v) )

        self.assertRaises( TypeError, f.cast, 1 )

    def test_6(self):
        "test SetField"
        s=set([1,2,3])
        f = SetField()

        v = f.cast(s)
        self.assertEqual( s, v )

        self.assertEqual( s, f.loads( f.dumps(s) ) )

    def test_7(self):
        "test StringField"
        s = "ȧƈƈḗƞŧḗḓ ŧḗẋŧ ƒǿř ŧḗşŧīƞɠ"

        f = StringField()

        v = f.cast(s)
        self.assertEqual( s.decode('utf-8'), v )
        self.assertEqual( v, f.loads( f.dumps(v) ) )

    def test_8(self):
        "test none/null"
        f = DateTimeField()

        v = f.loads(None)
        self.assertIsNone(v)

        v = f.loads('null')
        self.assertIsNone(v)

    def test_10(self):
        "test foreign keys, link to multi pk model not supported"
        with self.assertRaises(AssertionError):
            class MyDepModelMulti(Model):
                pk1     = IntField(primary_key=True)
                foreign = ForeignKey(MyMulti)

        # can't name field pk
        with self.assertRaises(AssertionError):
            class MyDepModel(Model):
                pk      = IntField(primary_key=True)
                foreign = ForeignKey(MyModel)

    def test_11(self):
        """
        test foreign keys
        note: just being able to define MyDepModel runs lots of code
        """
        m = MyModel(int_type=1).save()
        self.assertFalse( m.mydepmodel_set.all() )

        d = MyDepModel(pk1=1, foreign=m)
        self.assertTrue( isinstance(d.foreign, MyModel) )
        self.assertNotEqual( id(m), id(d.foreign) ) # d.foreign gets a copy of the object

        d = MyDepModel(pk1=1, foreign=1) # foreign key value
        self.assertTrue( isinstance(d.foreign, MyModel) )
        self.assertNotEqual( id(m), id(d.foreign) )

        d.foreign.str_type = "hello world"
        self.assertNotEqual( "hello world", m.str_type )

        # after locally storing a version of m, modify and save and get it back
        m2 = d.foreign
        m2.str_type = "hello world"
        m2.save()
        self.assertEqual( "hello world", d.foreign.str_type )

        self.assertNotEqual( m.str_type, m2.str_type )

    def test_12(self):
        "test save"
        m = MyModel(int_type=1).save()
        d = MyDepModel(pk1=1, foreign=m).save()

    def test_12a(self):
        "test that trying to save unset foreign key fails"

        m = MyDepModel(pk1=1)
        with self.assertRaises(RuntimeError):
            m.dict

        # FIXME this should probably happen
        # with self.assertRaises(RuntimeError):
        #     m.save()

        f = MyModel(int_type=1).save()
        m.foreign = f

        self.assertTrue(m.dict)


    def test_13(self):
        """
        test queries
        """
        m = MyModel(int_type=1).save()
        d = MyDepModel(pk1=10, foreign=m).save()

        self.assertEqual( m, d.foreign )

        # filters on MyDepModel "obviously" return MyDepModel even if
        # we're comparing with foreign keys
        self.assertEqual( d, MyDepModel.objects.get(foreign=m) )
        self.assertEqual( d, MyDepModel.objects.filter(foreign=m)[0] )

    def test_14(self):
        "test extra kw params to field raise assertion"
        with self.assertRaises(AssertionError):
            f = IntField(some_keyword=True)


    def test_15(self):
        """
        test *_set on foreign model
        """
        m = MyModel(int_type=1).save()
        d = MyDepModel(pk1=10, foreign=m).save()

        self.assertTrue( hasattr( m, 'mydepmodel_set') )
        self.assertTrue( d in m.mydepmodel_set.all() )

    def test_16(self):
        "test some foreignkey casting"
        m = MyModel(int_type=1).save()
        MyDepModel(pk1=10, foreign=m).save()
        MyDepModel(pk1=11, foreign=1).save()
        MyDepModel(pk1=12, foreign="1").save()

        self.assertEqual( 3, m.mydepmodel_set.all().count )

    def test_20(self):
        "test auto increment integer field"

        class AutoModel1( Model ):
            auto = IntField(primary_key=True, auto_increment=True)

        class AutoModel2( Model ):
            auto = IntField(primary_key=True, auto_increment=True)

        self.assertEqual( 1, AutoModel1().auto )
        self.assertEqual( 2, AutoModel1().auto )

        self.assertEqual( 1, AutoModel2().auto )
        self.assertEqual( 2, AutoModel2().auto )

        m = AutoModel2().save()
        self.assertEqual( 3, m.auto )

    def test_25(self):
        "test that Field.__set__ gets called"

        with mock.patch.object(Field, '__set__') as mock_method:
            m = MyModel()
            m.int_type = 1
            mock_method.assert_called_once_with(m, 1)

        m = MyModel()
        self.assertIsNone( m.int_type )

        m.int_type = 1
        self.assertIsInstance( m.int_type, int )
        self.assertIsInstance( m.__dict__['int_type'], int )
        self.assertIs( m.int_type, m.__dict__['int_type'] )
        self.assertIsInstance( m.Meta.fields['int_type'], IntField ) # hasn't magically changed

    def test_26(self):
        "test that Field.__get__ gets called"

        with mock.patch.object(Field, '__get__') as mock_method:
            m = MyModel()
            m.int_type
            mock_method.assert_called_once_with(m.Meta.fields['int_type'], m, MyModel)

    def test_27(self):
        "test that magic model.fieldname_field returns Field object"
        m = MyModel()
        self.assertIs( MyModel.Meta.fields['int_type'], m.int_type__field )

    def test_28(self):
        # this is just to get code coverage, not sure how this
        # would ever happen in real life
        MyModel.int_type
        MyDepModel.foreign

    def test_30(self):
        "test BoolField"

        class MyModel( Model ):
            int_type   = IntField(primary_key=True)
            bool_type  = BoolField()

        m = MyModel()

        for v in [None, '']:
            m.bool_type = v
            self.assertEqual(None, m.bool_type)

        for v in ['false','False','0','NO','n',0,[]]:
            m.bool_type = v
            self.assertEqual(False, m.bool_type)

        for v in [' ','true','anything else',1,[1]]:
            m.bool_type = v
            self.assertEqual(True, m.bool_type)

    def test_valid_pk(self):
        import pytz
        from . import Entry
        now = dt.datetime.now(pytz.utc)
        e = Entry(pk=now)

        self.assertEqual(now, e.pk)
        self.assertTrue(e.valid_pk)
