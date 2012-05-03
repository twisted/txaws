#!/usr/bin/env python2.7
import os
import sys

from launchpadlib.launchpad import Launchpad


class Error(Exception):
    """ 
    A base class for exceptions.
    """
    def __init__(self, msg=None):
        if msg == None:
            msg = self.__doc__.strip()
        super(Error, self).__init__(msg)


class CredentialsError(Error):
    """
    Can't proceed without Launchpad credential.
    """


class UnknownState(Error):
    pass


class Client(object):
    """
    A convenience wrapper for the Launchpad object.
    """
    def __init__(self, name=""):
        cachedir = os.path.expanduser("~/.launchpadlib/cache/")
        self.launchpad = Launchpad.login_with(
            name, 'production', cachedir,
            credential_save_failed=CredentialsError)
        self.project = self.get_project()
        self.set_state_map()

    def set_state_map(self):
        self.state_map = {
            "begin_state": {
                "fixcommitted": self.get_committed_bugs,
            },
            "end_state": {
                "fixreleased": self.set_released,
            },
        }

    def get_project(self, name="txaws"):
        return self.launchpad.projects["txaws"]

    def get_committed_bugs(self):
        return self.project.searchTasks(status="Fix Committed")

    def set_released(self, bugs=[]):
        count = int(bugs._wadl_resource.representation['total_size'])
        print "Found %s bugs." % count
        for bug_entry in bugs:
            status = "Fix Released"
            print "\tUpdating status of %s to '%s' ... " % (
                bug_entry.title, bug_entry.status),
            bug_entry.status = status
            bug_entry.lp_save()
            print "Done."
