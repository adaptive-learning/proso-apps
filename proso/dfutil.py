# -*- coding: utf-8 -*-


class DictIterator:

    def __init__(self, dataframe):
        self._dataframe = dataframe

    def __iter__(self):
        self._iter = self._dataframe.values.__iter__()
        self._columns = self._dataframe.columns.values
        return self

    def __len__(self):
        return len(self._dataframe)

    def __next__(self):
        return dict(list(zip(self._columns, next(self._iter))))


def iterdicts(dataframe):
    """
    Allows you to efficiently iterate over the dataframe.

    Args:
        dataframe (pandas.DataFrame):
            dataframe to iterate

    Returns:
        iterator allowing you to iterate over the dataframe providing rows as
        dicts
    """
    return DictIterator(dataframe)
