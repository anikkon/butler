#!/usr/bin/env python3
import argparse
import pprint
import pymongo
import requests
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
from consts import *
from utils import *


try:
    client = MongoClient(MONGO_ADDRESS, MONGO_PORT, serverSelectionTimeoutMS=10)
    user_collection = client.iax058x.users
except ServerSelectionTimeoutError:
    error('Mongo timeout. '
          'Make sure Mongo server is running and the port number is same as in the configuration file!')
    exit(1)


def config():
    if DATA_FROM == INPUT_DATA_SOURCE_GS:
        users = load_gsheets_data()
    else:
        # load from somewhere else..
        # currently not supported
        # TODO
        return
    old_users = mongo_get_users()
    info('Found {0} username pairs in Google Sheets.'.format(len(users)))
    info('Verifying Slack usernames.')
    users = verify_slack_users(users)
    info('Verified {0} users.'.format(len(users)))
    info('Verifying Gitlab usernames and projects.')
    users = verify_gitlab_users(users)
    info('Verified {0} users.'.format(len(users)))
    users = verify_old_users(users)
    info('Verified {0} users: {1}. This is final:'
         .format(len(users), [(u.get(KEY_SLACK_UNAME) + " : " + u.get(KEY_GITLAB_UNAME)) for u in users]))
    pprint.pprint(users)
    warning('Continuing will override all existing data. Want to continue? (yes/no)')
    if input().lower() != 'yes':
        return
    info('Deleting old Gitlab webhooks.')
    delete_gitlab_webhooks(old_users)
    info('Setting new Gitlab webhooks.')
    set_gitlab_webhooks(users)
    info('Inserting into db.')
    mongo_insert_users(users)
    info('Done!')


def load_gsheets_data():
    columns = GoogleSheetsClient(GOOGLE_SHEETS_URL, GOOGLE_SHEETS_CLIENT_SECRET_PATH).get_whole_sheet()
    slack_users = None
    gitlab_users = None
    gitlab_repos = None
    users = []

    # Find columns by name
    for column in columns:
        offset = GOOGLE_SHEETS_COLUMN_OFFSET
        if GOOGLE_SHEETS_COL_GITLAB_UNAMES in column:
            gitlab_users = column[offset:]
        elif GOOGLE_SHEETS_COL_SLACK_UNAMES in column:
            slack_users = column[offset:]
        elif GOOGLE_SHEETS_COL_GITLAB_REPOS in column:
            gitlab_repos = column[offset:]
        if gitlab_users and slack_users and gitlab_repos:
            break
    else:
        not_found = []
        if not gitlab_users: not_found.append(GOOGLE_SHEETS_COL_GITLAB_UNAMES)
        if not slack_users:  not_found.append(GOOGLE_SHEETS_COL_SLACK_UNAMES)
        if not gitlab_repos: not_found.append(GOOGLE_SHEETS_COL_GITLAB_REPOS)
        raise ValueError('Google Sheets column{s} \"{not_found}\" invalid or empty.'
                         .format(not_found="\", \"".join(not_found), s="s" if len(not_found) > 1 else ""))

    for i in range(0, min(len(slack_users), len(gitlab_users))):
        if slack_users[i] and gitlab_users[i]:
            users.append({
                KEY_SLACK_UNAME: slack_users[i],
                KEY_GITLAB_UNAME: gitlab_users[i]
            })
            try:
                repo_name = gitlab_repos[i]
                if repo_name:
                    users[i][KEY_GITLAB_REPO_NAME] = repo_name
            except IndexError:
                # We care only about slack_users and gitlab_users, gitlab_repos can be of any length throwing exception
                pass

    verify_users_not_empty(users)
    return users


def get_gitlab_user_projects(user):
    uname = user.get(KEY_GITLAB_UNAME)
    response = requests.get(GITLAB_GET_PROJECTS_URL.format(username=uname),
                            headers=GITLAB_AUTH_HEADER, timeout=REQUEST_TIMEOUT, verify=SSL_VERIFY)
    projects = response.json()
    if response.status_code == requests.codes.ok:
        if projects:
            # All good, both user and project exists
            return response.json()
        else:
            # User exists with no repositories or insufficient permissions
            warning('Can\'t access Gitlab projects for user \'{username}\' or there\'re none. '
                    'Assure gitlab auth token has admin rights. Skipping.'.format(username=uname))
    elif response.status_code == requests.codes.not_found:
        # User doesn't exist
        warning('Github user \'{username}\' doesn\'t exist. Skipping'.format(username=uname))
    else:
        # Something else?
        warning('Woops, something went wrong! Gitlab returned {0}'.format(response.status_code))


def verify_slack_users(users):
    response = requests.get(SLACK_GET_USER_LIST_URL, headers=SLACK_AUTH_HEADER, timeout=REQUEST_TIMEOUT)
    slack_users = response.json().get("members", [])
    verified_users = []

    # A list of usernames for more efficient searches
    unames = [u.get(KEY_SLACK_UNAME, None) for u in users]

    def verify_user(slack_uname, slack_id, user_index):
        unames[user_index] = None
        user = users[user_index].copy()
        user[KEY_SLACK_UNAME] = slack_uname
        user[KEY_SLACK_ID] = slack_id
        verified_users.append(user)

    for slack_user in slack_users:
        name = slack_user.get('name', None)
        real_name = slack_user.get('real_name', None)
        display_name = slack_user.get('profile', {}).get('display_name', None)
        user_id = slack_user.get('id', None)
        try:
            verify_user(name, user_id, unames.index(display_name))
            continue
        except ValueError:
            pass
        try:
            # Couldn't find by display name, trying by real name
            verify_user(name, user_id, unames.index(real_name))
            continue
        except ValueError:
            pass
        try:
            # Couldn't find by real name, trying by name
            verify_user(name, user_id, unames.index(name))
            continue
        except ValueError:
            pass

    verify_users_not_empty(verified_users)
    return verified_users


def verify_gitlab_users(users):
    verified_users = []

    for user in users:
        repo_name = user.get(KEY_GITLAB_REPO_NAME, '').lower()
        uname = user.get(KEY_GITLAB_UNAME, '')
        user_data = verify_gitlab_user(user)

        if not repo_name:
            # User has no Gitlab repo. Verifying username only.
            warning('Gitlab user \'{username}\' doesn\'t have a repository field. Verifying username only.'
                    .format(username=uname))
            if user_data:
                verified_users.append(user)
        if not user_data:
            continue
        user[KEY_GITLAB_USER_ID] = user_data.get('id')

        # User does have a Gitlab repo. Verifying both username and repo name.
        projects = get_gitlab_user_projects(user)
        if not projects:
            continue
        for project in projects:
            r_name = project.get('name', '')
            if repo_name == r_name.lower():
                r_id = project.get('id', '')
                user[KEY_GITLAB_REPO_ID] = r_id
                verified_users.append(user)
                break
        else:
            warning('Couldn\'t find project {0} for user \'{1}\'. Skipping.'.format(repo_name, uname))

    if not verified_users:
        warning('Couldn\'t verify any gitlab users. Make sure Gitlab auth token is correct.')
        exit(1)
    return verified_users


def verify_gitlab_user(user):
    uname = user.get(KEY_GITLAB_UNAME)
    response = requests.get(GITLAB_GET_USER_URL.format(username=uname),
                            headers=GITLAB_AUTH_HEADER, timeout=REQUEST_TIMEOUT, verify=SSL_VERIFY)
    if response.status_code != requests.codes.ok:
        warning('Woops, something went wrong! Gitlab returned {0}'.format(response.status_code))
    elif response.json():
        # If user exists non-empty json object is returned
        return response.json()[0]
    else:
        warning('Gitlab user \'{username}\' doesn\'t exist. Skipping'.format(username=uname))


def verify_users_not_empty(users):
    if not users:
        error('No verified users. Exiting!')
        exit(1)


def verify_old_users(new_users):
    old_users = mongo_get_users()
    if not old_users:
        return new_users
    new_unames = set([u.get(KEY_GITLAB_UNAME) for u in new_users])
    old_unames = set([u.get(KEY_GITLAB_UNAME) for u in old_users])
    diff_unames = list(old_unames - new_unames)

    if not diff_unames:
        return new_users

    diff_users = [[item for item in old_users if item[KEY_GITLAB_UNAME] == uname][0] for uname in diff_unames]
    warning('The following users are in db, but not in the new dataset: {users}'.format(users=diff_unames))
    print('Choose an option..\nK - keep all\nD - delete all\nC - choose for each user manually')

    while True:
        choice = input().lower()
        if choice == 'k':
            return new_users + diff_users
        elif choice == 'd':
            return new_users
        elif choice == 'c':
            break
        print('Choose \'K\' \'D\' or \'C\'')

    print('\nOk, choosing for each user manually. Let\'s go:')

    tmp = []

    for user in diff_users:
        uname = user.get(KEY_GITLAB_UNAME)
        print('\nUser: \'{username}\'\nK - Keep\nD - Delete'.format(username=uname))
        while True:
            choice = input().lower()
            if choice == 'k':
                tmp.append(user)
                break
            elif choice == 'd':
                break
            print('Choose \'K\' or \'D\'')

    return new_users + diff_users


def mongo_get_users():
    try:
        return list(user_collection.find({}))
    except ServerSelectionTimeoutError:
        error('Mongo timeout. '
              'Make sure Mongo server is running and the port number is same as in the configuration file!')
        raise


def mongo_insert_users(users):
    if not users:
        return
    try:
        user_collection.drop()
        user_collection.insert_many(users)
        user_collection.create_index([(KEY_GITLAB_UNAME, pymongo.ASCENDING)])
        user_collection.create_index([(KEY_GITLAB_REPO_ID, pymongo.ASCENDING)])
        user_collection.create_index([(KEY_GITLAB_USER_ID, pymongo.ASCENDING)])
    except ServerSelectionTimeoutError:
        error('Mongo timeout. '
              'Make sure Mongo server is running and the port number is same as in the configuration file!')
        raise


def set_gitlab_webhooks(users):
    for index, user in enumerate(users):
        project_id = user.get(KEY_GITLAB_REPO_ID)
        uname = user.get(KEY_GITLAB_UNAME)

        if not project_id:
            # User has no gitlab repo - doesn't need a webhook.
            continue
        response = post_gitlab_webhook(project_id, SERVER_ADDRESS)
        webhook_id = get_gitlab_webhook_id(project_id)

        if response.status_code != requests.codes.created:
            error('Couldn\'t set webhook for Gitlab user \'{username}\'. '
                  'Error code: {err_code}.  Skipping'.format(username=uname, err_code=response.status_code))
            continue
        users[index][KEY_GITLAB_REPO_HOOK_ID] = webhook_id


def delete_gitlab_webhooks(users):
    for user in users:
        project_id = user.get(KEY_GITLAB_REPO_ID)
        webhook_id = user.get(KEY_GITLAB_REPO_HOOK_ID)
        if project_id and webhook_id:
            delete_gitlab_webhook(project_id=project_id, webhook_id=webhook_id)


def delete_gitlab_webhook(project_id, webhook_id, verify=False):
    requests.delete(GITLAB_GET_PUT_DELETE_PROJECT_HOOK.format(
        project_id=project_id, hook_id=webhook_id), headers=GITLAB_AUTH_HEADER,
        timeout=REQUEST_TIMEOUT, verify=verify)


def get_gitlab_webhook_id(project_id, verify=False):
    webhooks = requests.get(GITLAB_GET_PROJECT_HOOKS.format(
        project_id=project_id), headers=GITLAB_AUTH_HEADER,
        timeout=REQUEST_TIMEOUT, verify=verify).json()

    for wh in webhooks:
        if wh.get('url') == SERVER_ADDRESS:
            return wh.get('id')


def post_gitlab_webhook(project_id, url, issue_events=True, note_events=True, verify=False):
    content = {'url': url, 'id': project_id, 'issues_events': issue_events, 'note_events': note_events}
    return requests.post(GITLAB_POST_WEBHOOK_URL.format(
        project_id=project_id), headers=GITLAB_AUTH_HEADER,
        timeout=REQUEST_TIMEOUT, json=content, verify=verify)


if __name__ == '__main__':
    config()
