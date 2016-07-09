from zope.interface import Interface, Attribute, implements
import datetime as dt
from collections import OrderedDict
import os

from .storage import JSONStorage
from .table import Table
from .fields import Field

class IDatabase( Interface ):

    tables   = Attribute("the dict of tables")

class Database(object):
    implements(IDatabase)

    def __init__( self, tables=[], *args, **kw ):

        self._tables = OrderedDict()
        for table in tables:
            self._tables[table.name] = table

        self._storage_type = kw.pop('storage', JSONStorage)
        self._root_dir = kw.pop('root_dir', '.')

    @property
    def tables(self):
        return self._tables.values()

    def get_filename(self, table):
        ext = self._storage_type.extension
        return os.path.join( self._root_dir, "{}.{}".format(table.name,ext) )