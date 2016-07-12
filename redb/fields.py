from zope.interface import Interface, Attribute, implements
import datetime as dt
import dateutil.parser

from . import tzadd

class IField( Interface ):

    field_type = Attribute("the type of the field, str, int, list, etc")

    def dumps(value):
        "method to serialize the value"

    def loads(value):
        "method to load the value"

class Field(object):
    """
    base class for all field types. it tries to hold all the functionality
    so derived classes only need to override methods in special circumstances.
    """
    implements(IField)

    def __init__(self, field_type, *args, **kw):
        assert field_type is not None
        self._field_type = field_type

        self._primary_key = kw.pop('primary_key', False)

    def __str__(self):
        return "<{}>".format(self.__class__.__name__)

    @property
    def field_type(self):
        return self._field_type

    @property
    def primary_key(self):
        return self._primary_key

    def cast(self, value):
        """
        cast non field_type to correct type
        """
        if value is None:
            return None

        if type(value) is not self._field_type:
            return self.field_type(value)
        return value

    @classmethod
    def dumps(cls, value):
        return value

    @classmethod
    def loads(cls, value):
        return value

class IntField(Field):

    def __init__(self, *args, **kw):
        super(IntField, self).__init__(int, *args, **kw)


class FloatField(Field):

    def __init__(self, *args, **kw):
        super(IntField, self).__init__(float, *args, **kw)


class StringField(Field):

    def __init__(self, *args, **kw):
        super(StringField, self).__init__(str, *args, **kw)


class DateField(Field):

    def __init__(self, *args, **kw):
        super(DateField, self).__init__(dt.datetime, *args, **kw)

    def cast(self, value):
        """
        make sure date always has a time zone
        """
        if value is None:
            return None

        if type(value) in [unicode,str]:
            return DateField.loads(value)

        if type(value) is not self.field_type:
            value = self.field_type(value)

        if value.tzinfo is None:
            value = tzadd( value )

        return value

    @classmethod
    def dumps(cls, value):
        if value is None:
            return 'null'
        return value.isoformat()

    @classmethod
    def loads(cls, date):
        if date is None or date == 'null':
            return None

        # assume date is in isoformat, this preserves timezone info
        if type(date) in [unicode,str]:
            date = dateutil.parser.parse(date)

        if date.tzinfo is None:
            date = tzadd( date )

        return date
