from django.forms.models import model_to_dict
from functools import wraps


class ModelDiffMixin(object):

    """
    A model mixin that tracks model fields' values and provide some useful api
    to know what fields have been changed.

    See: http://stackoverflow.com/questions/533631/what-is-a-mixin-and-why-are-they-useful
    """

    def __init__(self, *args, **kwargs):
        super(ModelDiffMixin, self).__init__(*args, **kwargs)
        self.__initial = self._dict

    @property
    def diff(self):
        all_original = self.__initial
        all_new = self._dict
        return {
            field: (original, all_new[field])
            for field, original in all_original.items() if original != all_new[field]
        }

    @property
    def has_changed(self):
        return bool(self.diff)

    @property
    def changed_fields(self):
        return self.diff.keys()

    def get_field_diff(self, field_name):
        """
        Returns a diff for field if it's changed and None otherwise.
        """
        return self.diff.get(field_name, None)

    def save(self, *args, **kwargs):
        """
        Saves model and set initial state.
        """
        super(ModelDiffMixin, self).save(*args, **kwargs)
        self.__initial = self._dict

    @property
    def _dict(self):
        return model_to_dict(
            self,
            fields=[field.name for field in self._meta.fields]
        )


def disable_for_loaddata(signal_handler):
    @wraps(signal_handler)
    def wrapper(*args, **kwargs):
        if kwargs.get('raw'):
            return
        signal_handler(*args, **kwargs)

    return wrapper
