# Copyright (C) 2009 Robert Collins <robertc@robertcollins.net>
# Licenced under the txaws licence available at /LICENSE in the txaws source.
"""A GTK client for working with aws."""

from __future__ import absolute_import

import gnomekeyring
import gobject
import gtk

# DO NOT IMPORT twisted.internet, or things that import
# twisted.internet.
# Doing so loads the default Reactor, which is bad. thanks.

from txaws.credentials import AWSCredentials


__all__ = ["main"]


class AWSStatusIcon(gtk.StatusIcon):
    """A status icon shown when instances are running."""

    def __init__(self, reactor):
        gtk.StatusIcon.__init__(self)
        self.set_from_stock(gtk.STOCK_NETWORK)
        self.set_visible(True)
        self.reactor = reactor
        self.connect("activate", self.on_activate)
        self.probing = False
        # Nested import because otherwise we get "reactor already installed".
        self.password_dialog = None
        self.region = None
        try:
            creds = AWSCredentials()
        except ValueError:
            creds = self.from_gnomekeyring()
        if self.region is None:
            self.set_region(creds)
        self.create_client(creds)
        menu = """
            <ui>
             <menubar name="Menubar">
              <menu action="Menu">
               <menuitem action="Stop instances"/>
              </menu>
             </menubar>
            </ui>
        """
        actions = [
            ("Menu",  None, "Menu"),
            ("Stop instances", gtk.STOCK_STOP, "_Stop instances...", None,
                "Stop instances", self.on_stop_instances),
            ]
        ag = gtk.ActionGroup("Actions")
        ag.add_actions(actions)
        self.manager = gtk.UIManager()
        self.manager.insert_action_group(ag, 0)
        self.manager.add_ui_from_string(menu)
        self.menu = self.manager.get_widget(
            "/Menubar/Menu/Stop instances").props.parent
        self.connect("popup-menu", self.on_popup_menu)

    def set_region(self, creds):
        from txaws.service import AWSServiceRegion
	self.region = AWSServiceRegion(creds)

    def create_client(self, creds):
        if creds is not None:
            if self.region is None:
                self.set_region(creds)
            self.client = self.region.get_ec2_client()
            self.on_activate(None)
        else:
            # waiting on user entered credentials.
            self.client = None

    def from_gnomekeyring(self):
        # Try for gtk gui specific credentials.
        try:
            items = gnomekeyring.find_items_sync(
                gnomekeyring.ITEM_GENERIC_SECRET,
                {
                    "aws-host": "aws.amazon.com",
                })
        except (gnomekeyring.NoMatchError,
            gnomekeyring.DeniedError):
            self.show_a_password_dialog()
            return None
        else:
            key_id, secret_key = items[0].secret.split(":")
            return AWSCredentials(access_key=key_id, secret_key=secret_key)

    def show_a_password_dialog(self):
        self.password_dialog = gtk.Dialog(
            "Enter your AWS credentals", None, gtk.DIALOG_MODAL,
            (gtk.STOCK_OK, gtk.RESPONSE_ACCEPT,
            gtk.STOCK_CANCEL,
            gtk.RESPONSE_REJECT))
        content = self.password_dialog.get_content_area()
        def add_entry(name):
            box = gtk.HBox()
            box.show()
            content.add(box)
            label = gtk.Label(name)
            label.show()
            box.add(label)
            entry = gtk.Entry()
            entry.show()
            box.add(entry)
            label.set_use_underline(True)
            label.set_mnemonic_widget(entry)
        add_entry("AWS _Access Key ID")
        add_entry("AWS _Secret Key")

        self.password_dialog.show()
        self.password_dialog.connect("response", self.save_key)
        self.password_dialog.run()

    def on_activate(self, data):
        if self.probing or not self.client:
            # don't ask multiple times, and don't ask until we have
            # credentials.
            return
        self.probing = True
        deferred = self.client.describe_instances()
        deferred.addCallbacks(self.showhide, self.describe_error)

    def on_popup_menu(self, status, button, time):
        self.menu.popup(None, None, None, button, time)

    def on_stop_instances(self, data):
        # It would be nice to popup a window to select instances.. TODO.
        deferred = self.client.describe_instances()
        deferred.addCallbacks(self.shutdown_instances, self.show_error)

    def save_key(self, response_id, data):
        try:
            if data != gtk.RESPONSE_ACCEPT:
                # User cancelled. They can ask for the password again somehow.
                return
            content = self.password_dialog.get_content_area()
            key_id = content.get_children()[0].get_children()[1].get_text()
            secret_key = content.get_children()[1].get_children()[1].get_text()
            creds = AWSCredentials(access_key=key_id, secret_key=secret_key)
            self.create_client(creds)
            gnomekeyring.item_create_sync(
                None,
                gnomekeyring.ITEM_GENERIC_SECRET,
                "AWS access credentials",
                    {"aws-host": "aws.amazon.com"},
                    "%s:%s" % (key_id, secret_key), True)
        finally:
            self.password_dialog.hide()
            # XXX? Does this leak?
            self.password_dialog = None

    def showhide(self, reservation):
        active = 0
        for instance in reservation:
            if instance.instance_state == "running":
                active += 1
        self.set_tooltip("AWS Status - %d instances" % active)
        self.set_visible(active != 0)
        self.queue_check()

    def shutdown_instances(self, reservation):
        d = self.client.terminate_instances(
            *[instance.instance_id for instance in reservation])
        d.addCallbacks(self.on_activate, self.show_error)

    def queue_check(self):
        self.probing = False
        self.reactor.callLater(60, self.on_activate, None)

    def show_error(self, error):
        # debugging output for now.
        print error.value
        try:
            print error.value.response
        except:
            pass

    def describe_error(self, error):
        from twisted.internet.defer import TimeoutError
        if isinstance(error.value, TimeoutError):
            # timeout errors can be ignored - transient network issue or some
            # such.
            pass
        else:
            # debugging output for now.
            self.show_error(error)
        self.queue_check()


def main(argv, reactor=None):
    """Run the client GUI.

    Typical use:
    >>> sys.exit(main(sys.argv))

    @param argv: The arguments to run it with, e.g. sys.argv.
    @param reactor: The reactor to use. Must be compatible with gtk as this
        module uses gtk API"s.
    @return exitcode: The exit code it returned, as per sys.exit.
    """
    if reactor is None:
        from twisted.internet import gtk2reactor
        gtk2reactor.install()
        from twisted.internet import reactor
    try:
        AWSStatusIcon(reactor)
        gobject.set_application_name("aws-status")
        reactor.run()
    except ValueError:
        # In this case, the user cancelled, and the exception bubbled to here.
        pass
