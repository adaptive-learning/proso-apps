#  -*- coding: utf-8 -*-
import environment as environment


class InMemoryEnvironmentTest(environment.TestCommonEnvironment):

    _user = 0
    _item = 0

    def generate_item(self):
        self._item += 1
        return self._item

    def generate_user(self):
        self._user += 1
        return self._user

    def generate_environment(self):
        return environment.InMemoryEnvironment()
