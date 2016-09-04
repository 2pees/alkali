from zope.interface import Interface, Attribute, implements
import inspect

from .query import Query
from .storage import IStorage

import logging
logger = logging.getLogger(__name__)

class IManager( Interface ):
    pass

class Manager(object):
    """
    the ``Manager`` class is the parent/owner of all the
    :class:`alkali.model.Model` instances. Each ``Model`` has it's own
    manager. ``Manager`` could rightly be called ``Table``.
    """
    implements(IManager)

    def __init__( self, model_class ):
        """
        :param model_class: the model that we should store
        :type model_class: :class:`alkali.model.Model` class
        """
        assert inspect.isclass(model_class)
        self._model_class = model_class
        self._instances = {}
        self._dirty = False

        self.clear()

    def __repr__(self):
        return "<{}: {}>".format(self.name, len(self))

    def __len__(self):
        return len(self._instances)

    @property
    def count(self):
        """
        **property**: number of model instances we're holding
        """
        return len(self)

    @property
    def name(self):
        """
        **property**: pretty version of our class name, based on our model
            eg. *EntryManager*
        """
        return "{}Manager".format(self._model_class.__name__)

    @property
    def pks(self):
        """
        **property**: return all primary keys

        :rtype: ``list``
        """
        return self._instances.keys()

    @property
    def instances(self):
        """
        **property**: return all model instances

        :rtype: ``list``
        """
        return [elem for elem in Manager.sorter(self._instances)]

    @property
    def dirty(self):
        """
        **property**: return True if any model instances are dirty

        :rtype: ``bool``
        """
        if self._dirty:
            return True

        return any( map( lambda e: e.dirty, self.instances ) )


    @staticmethod
    def sorter(elements, **kw ):
        """
        yield model instances in key order

        :param elements: our instances
        :type elements: :class:`Manager.instances`
        :param kw:
            * reverse: return in reverse order
        :rtype: ``generator``
        """
        keys = sorted( elements.keys(), **kw )
        for key in keys:
            yield elements[key]


    def save(self, instance, dirty=True):
        """
        take ownership (add to our ``dict``) of given model instance

        :param instance:
        :type instance: :class:`alkali.model.Model` instance
        :param dirty: don't mark us as dirty if False, used during loading
        """
        #logger.debug( "saving model instance: %s", str(instance.pk) )

        assert instance.pk is not None
        self._instances[ instance.pk ] = instance

        # self._dirty is required because think what would happen
        # if we add a clean model instance
        if dirty:
            self._dirty = True


    def clear(self):
        """
        remove all instances of our models. we'll be marked as
        dirty if we previously had model instances.

        **Note**: this does not affect on-disk files until
        :func:`Manager.save` is called.
        """
        logger.debug( "%s: clearing all models", self.name )

        self._dirty = len(self) > 0
        self._instances = {}


    def delete(self, instance):
        """
        remove an instance from our models by calling ``del`` on it

        :param instance:
        :type instance: :class:`alkali.model.Model`
        """
        # TODO should probably take an pk instead of an instance
        logger.debug( "deleting model instance: %s", str(instance.pk) )

        try:
            del self._instances[ instance.pk ]
            self._dirty = True
        except KeyError:
            pass


    def store(self, storage, force=False):
        """
        save all our instances to storage

        :param storage:
        :type storage: :class:`alkali.storage.Storage` instance
        :param force: force save even if we're not dirty
        """
        assert not inspect.isclass(storage)

        if force:
            self._dirty = True

        if self.dirty:
            logger.debug( "%s: has dirty records, saving", self.name )
            logger.debug( "%s: storing models via storage class: %s", self.name, storage.name )

            storage.write( Manager.sorter(self._instances) )
        else:
            logger.debug( "%s: has no dirty records, not saving", self.name )

        self._dirty = False


    def load(self, storage):
        """
        load all our instances from storage

        raises ``KeyError`` if there are duplicate primary keys

        :param storage:
        :type storage: :class:`alkali.storage.Storage` instance
        """
        assert not inspect.isclass(storage)
        storage = IStorage(storage)
        logger.debug( "%s: loading models via storage class: %s", self.name, storage.name )

        self.clear()

        for elem in storage.read( self._model_class ):
            if isinstance(elem, dict):
                elem = self._model_class( **elem )

            if elem.pk in self._instances:
                raise KeyError( 'pk collision detected during load: %s' % str(elem.pk) )

            # this adds elem to our internal list
            self.save(elem, dirty=False)

        self._dirty = False
        logger.debug( "%s: finished loading", self.name )


    def get(self, *pk, **kw):
        """
        perform a query that returns an instance of a model

        raises ``KeyError`` if 0 or more than 1 instance returned

        :param pk: optional primary key
        :type pk: value or ``tuple`` if multi-pk
        :param kw: optional field_name=value
        :rtype: single :class:`alkali.model.Model` instance

        ::

            m = MyModel.objects.get(1)      # equiv to
            m = MyModel.objects.get(pk=1)

            m = MyModel.objects.get(some_field='a unique value')
        """
        if len(pk):
            kw['pk'] = pk[0]

        results = Query(self).filter(**kw).instances

        if len(results) == 0:
            raise KeyError("got no results")

        if len(results) > 1:
            raise KeyError("got more than 1 result")

        return results[0]

    def filter(self, **kw):
        """
        return a :class:`alkali.query.Query`, aka a subset of model instances

        see :class:`alkali.query.Query` for documentation
        """
        return Query(self).filter(**kw)

    def order_by(self, **kw):
        """
        return a :class:`alkali.query.Query` that has been sorted by given fields

        see :class:`alkali.query.Query` for documentation
        """
        return Query(self).order_by(**kw)

    def all(self):
        """
        return a full :class:`alkali.query.Query`, aka list of all model instances

        see :class:`alkali.query.Query` for documentation
        """
        return Query(self)
