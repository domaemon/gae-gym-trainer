import os
import cgi
import urllib

from google.appengine.api import users
from google.appengine.ext import ndb
from google.appengine.api import channel

import jinja2
import webapp2

import json
import datetime


JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'])


def table_key(table_name):
    return ndb.Key('GymTrainer', table_name)


def show_group_ids(user_id):
    group_ids = []

    tmp_user_group_entities = UserGroupTable.query(
        UserGroupTable.user_id == user_id,
        ancestor=table_key('UserGroupTable')
        ).fetch(projection=[UserGroupTable.group_id])
    
    for tmp_user_group_entity in tmp_user_group_entities:
        group_ids.append(tmp_user_group_entity.group_id)

    return group_ids


def show_user_ids(group_id):
    user_ids = []

    tmp_user_group_entities = UserGroupTable.query(
        UserGroupTable.group_id == group_id,
        ancestor=table_key('UserGroupTable')
        ).fetch(projection=[UserGroupTable.user_id])

    for tmp_user_group_entity in tmp_user_group_entities:
        user_ids.append(tmp_user_group_entity.user_id)

    return user_ids


def create_group(group_name, user_id):
    # update GroupTable
    tmp_group_entity = GroupTable(
        parent=table_key('GroupTable'),
        group_name = group_name)
    tmp_group_entity.put()
    group_id = str(tmp_group_entity.key.id())

    # update UserGroupTable
    tmp_user_group_entity = UserGroupTable(
        parent=table_key('UserGroupTable'),
        user_id = user_id,
        group_id = group_id)
    tmp_user_group_entity.put()


# input: group_ids
# output: [{'name': name, 'user_ids': [user_ids]}]
def create_group_objs(group_ids):
    group_objs = []

    for group_id in group_ids:
        group_obj = {}
        # check the users with the group
        tmp_group_table = GroupTable.get_by_id(
            int(group_id),
            parent=table_key('GroupTable'))
                                               
        group_obj['group_name'] = tmp_group_table.group_name
        user_ids = show_user_ids(group_id)
        group_obj['group_id'] = group_id
        group_obj['user_ids'] = user_ids
        group_objs.append(group_obj)

    return group_objs


def del_group(group_id):
    pass

def add_member(group_id, user_id):
    # register user if NOT exist
    tmp_user_entity = UserTable.query(
        UserTable.user_id == user_id,
        ancestor=table_key('UserTable')
        ).fetch(1)
    
    if (not tmp_user_entity): # I exist in the NDB
        register_user(user_id)

    # update UserGroupTable with the member user_id
    tmp_user_group_entity = UserGroupTable(
        parent=table_key('UserGroupTable'),
        user_id = user_id,
        group_id = group_id)
    tmp_user_group_entity.put()


def del_member(group_id, user_id):
    pass



def register_user(user_id):
    tmp_user_entity = UserTable(
        parent=table_key('UserTable'),
        user_id = user_id)
    tmp_user_entity.put()


class UserTable(ndb.Model):
    """Models an individual Guestbook entry with author, content, and date."""
    user_id = ndb.StringProperty()
    date = ndb.DateTimeProperty(auto_now_add=True)


class UserGroupTable(ndb.Model):
    """Models an individual Guestbook entry with author, content, and date."""
    user_id = ndb.StringProperty()
    group_id = ndb.StringProperty()
    date = ndb.DateTimeProperty(auto_now_add=True)


class GroupTable(ndb.Model):
    """Models an individual Guestbook entry with author, content, and date."""
    group_name = ndb.StringProperty()
    date = ndb.DateTimeProperty(auto_now_add=True)


class MainPage(webapp2.RequestHandler):

    def get(self):
        user = users.get_current_user()

        if not user:
            url = users.create_login_url(self.request.uri)
            self.redirect(url)
            return

        # check if the user is stored in the NDB
        user_id = str(user.user_id())
        user_entity = UserTable.query(
            UserTable.user_id == user_id,
            ancestor=table_key('UserTable')
            ).fetch(1)

        if (user_entity): # I exist in the NDB
            # check if the user is associated with any groups
            group_ids = show_group_ids(user_id)

            if (group_ids): # group entity exists
                group_objs = create_group_objs(group_ids)
            else:
                group_objs = None

        else: # I do NOT even exist in the NDB
            # register the unique_id in the userlist
            register_user(user_id)
            group_objs = None

        url = users.create_logout_url(self.request.uri)
        template_values = {
            'user': user,
            'group_objs': group_objs,
            'url': url,
            }
        template = JINJA_ENVIRONMENT.get_template('homescreen.html')
        self.response.write(template.render(template_values))


class GymTrainer(webapp2.RequestHandler):        

    def get(self):
        user = users.get_current_user()

        if not user:
            url = users.create_login_url(self.request.uri)
            self.redirect(url)
            return

        show = self.request.get('show', 'unknown')
        group_id = self.request.get('group_id', 'unknown')

        if (show == 'create_group'):
            template_values = { }
            template = JINJA_ENVIRONMENT.get_template('create_group.html')
            self.response.write(template.render(template_values))

        if (show == 'add_member'):
            group_obj = {}
            group_obj['group_name'] = GroupTable.get_by_id(
                int(group_id),
                parent=table_key('GroupTable')).group_name
            group_obj['group_id'] = group_id
            
            template_values = {
                'user': user,
                'group_obj': group_obj,
                }
            template = JINJA_ENVIRONMENT.get_template('add_member.html')
            self.response.write(template.render(template_values))

    def post(self):
        user = users.get_current_user()

        if not user:
            return

        action = self.request.get('action', 'unknown')
        group_name = self.request.get('group_name', 'unknown')
        group_id = self.request.get('group_id', 'unknown')
        user_id = user.user_id()

        member_given_name = self.request.get('member_given_name', 'unknown')
        member_family_name = self.request.get('member_family_name', 'unknown')
        member_email_address = self.request.get('member_email_address', 'unknown')

        if (action == 'create_group'):
            create_group(group_name, user_id)
            self.redirect("/")
            return

        if (action == 'add_member'):
            member = users.User(member_email_address)
            add_member(group_id, str(member.user_id()))
            self.redirect("/")
            return


application = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/gym-trainer', GymTrainer),
], debug=True)
