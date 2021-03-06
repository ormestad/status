"""Set of handlers related with Picea.
"""

import tornado.web
import json
import time

from dateutil import parser

from status.util import SafeHandler

class PiceaHandler(SafeHandler):
    """ Serves a page with time series of storage usage on Picea.
    """
    def get(self):
        t = self.application.loader.load("picea.html")
        self.write(t.generate(user=self.get_current_user_name(), deprecated=True))


class PiceaHomeDataHandler(SafeHandler):
    """ Serves a time series for the total storage usage in HOME on Picea.

    Loaded through /api/v1/picea_home
    """
    def get(self):
        self.set_header("Content-type", "application/json")
        self.write(json.dumps(self.home_usage()))

    def home_usage(self):
        sizes = []
        for row in self.application.picea_db.view("sizes/home_total"):
            obs_time = parser.parse(row.key)
            sizes.append({"x": int(time.mktime(obs_time.timetuple()) * 1000),
                          "y": row.value * 1024})

        return sizes


class PiceaHomeUserDataHandler(SafeHandler):
    """ Serves a time series for the storage used by as user in HOME on Picea.

    Loaded through /api/v1/picea_home/([^/]*)$
    """
    def get(self, user):
        self.set_header("Content-type", "application/json")
        self.write(json.dumps(self.home_usage(user)))

    def home_usage(self, user):
        sizes = []
        view = self.application.picea_db.view("sizes/home_user", group=True)
        for row in view[[user, "0"], [user, "a"]]:
            obs_time = parser.parse(row.key[1])
            sizes.append({"x": int(time.mktime(obs_time.timetuple()) * 1000),
                          "y": row.value * 1024})

        return sizes


class PiceaUsersDataHandler(SafeHandler):
    """ Serves a list of users on Picea.

    Loaded through /api/v1/picea_home/users/
    """
    def get(self):
        self.set_header("Content-type", "application/json")
        self.write(json.dumps(self.home_users()))

    def home_users(self):
        users = []
        view = self.application.picea_db.view("sizes/home_user", group_level=1)
        for row in view:
            if "/" not in row.key[0]:
                users.append(row.key[0])

        return users
