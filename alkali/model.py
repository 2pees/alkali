from zope.interface import Interface, Attribute, implements
import json

from .memoized_property import memoized_property
from .metamodel import MetaModel
from . import fields
from . import signals

class IModel( Interface ):

    dict   = Attribute("represent our data as a dict")


class Model(object):
    """
    main class for the database.

    the definition of this class defines a table schema but instances of
    this class hold a row.

    model fields are available as attributes. eg. ``m.my_field = 'foo'``

    the Django docs at https://docs.djangoproject.com/en/1.10/topics/db/models/
    will be fairly relevant to alkali

    see :mod:`alkali.database` for some example code
    """
    __metaclass__ = MetaModel
    implements(IModel)

    def __init__(self, *args, **kw):
        # MetaModel.__call__ has put fields in self,
        # put any other keywords into self
        for name, value in kw.iteritems():
            setattr(self, name, value)

        signals.creation.send(self.__class__, instance=self)

    # called via copy.copy() module, when getting from manager
    def __copy__(self):
        new = type(self)()
        new.__dict__.update(self.__dict__)
        return new

    def __repr__(self):
        return "<{}: {}>".format(self.__class__.__name__, self.pk)

    def __eq__(self, other):
        # this is obviously a very shallow comparison
        return type(self) == type(other) and self.pk == other.pk

    def __ne__(self, other):
        return not self.__eq__(other)

    def __getattribute__(self, attr):
        # lookup and return foreign object if attr is a ForeignKey
        meta = super(Model,self).__getattribute__('Meta')
        if attr in meta.fields:
            field_type = meta.fields[attr]
            if isinstance(field_type, fields.ForeignKey):
                foreign_pk = self.__dict__[attr]
                return field_type.lookup(foreign_pk)

        return super(Model, self).__getattribute__(attr)

    def __setattr__(self, attr, val):
        if attr in self.Meta.fields:
            self.__assign_field( attr, val)
        else:
            self.__dict__[attr] = val

    def __assign_field(self, attr, val):
        # if we're setting a field value and that value is different
        # than current value, mark self as modified

        field_type = self.Meta.fields[attr]  # eg. IntField
        val = field_type.cast(val)           # make sure val is correct type

        if hasattr(self, attr):
            curr_val = getattr(self, attr)

            # do not let user change pk after it has been set
            if attr in self.Meta.pk_fields:
                if curr_val is not None and curr_val != val:
                    raise RuntimeError("trying to change set pk value: {} to {}".format(self.pk, val))

            self.__dict__['_dirty'] = curr_val != val
        else:
            # we don't have this attr during object creation
            curr_val = None

        self.__dict__[attr] = val # actually set the value

        signals.field_update.send(self.__class__, field=attr, old_val=curr_val, new_val=val)

    @property
    def dirty(self):
        """
        **property**: return True if our fields have changed since creation
        """
        return self._dirty

    @property
    def schema(self):
        """
        **property**: a string that quickly shows the fields and types
        """
        def fmt(name, field):
            return "{}:{}".format(name, field.field_type.__name__)

        name_type = [ fmt(n,f) for n,f in self.Meta.fields.iteritems() ]
        fields = ", ".join( name_type )
        return "<{}: {}>".format(self.__class__.__name__, fields)

    @memoized_property
    def pk(self):
        """
        **property**: returns this models primary key value. If the model is
        comprised of serveral primary keys then return a tuple of them.

        :rtype: :class:`alkali.fields.Field` or tuple-of-Field
        """
        pks = map( lambda name: getattr(self, name), self.Meta.pk_fields )

        if len(pks) == 1:
            return pks[0]

        return tuple(pks)

    @property
    def dict(self):
        """
        **property**: returns a dict of all the fields, the fields are
        json consumable

        :rtype: ``dict``
        """
        return { name: field.dumps( getattr(self, name) )
                for name, field in self.Meta.fields.iteritems() }

    @property
    def json(self):
        """
        **property**: returns json that holds all the fields

        :rtype: ``str``
        """
        return json.dumps(self.dict)

    def save(self):
        """
        add ourselves to our :class:`alkali.manager.Manager` and mark
        ourselves as no longer dirty.

        it's up to our ``Manager`` to persistently save us
        """
        self.__class__.objects.save(self)
        self._dirty = False
        return self
