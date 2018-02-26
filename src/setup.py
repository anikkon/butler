import argparse
import pprint
import pymongo
import requests
from pymongo.errors import ServerSelectionTimeoutError
from printer import info, warning, error
from pymongo import MongoClient
from constants import *
from google_sheets_client import GoogleSheetsClient


client = MongoClient('localhost', DEFAULT_PORT_DB)
user_collection = client.iax058x.users

# TODO start mongo manually
# FIXME Gitlab.pld ssl verification fails.. Using no-verify by default


def get_args():
    """"""
    parser = argparse.ArgumentParser(
        description="A simple argument parser",
        epilog="This is where you might put example usage"
    )

    # required argument
    parser.add_argument('-x', action="store", required=True,
                        help='Help text for option X')
    # optional arguments
    parser.add_argument('-y', help='Help text for option Y', default=False)
    parser.add_argument('-z', help='Help text for option Z', type=int)
    return parser.parse_args()


if __name__ == '__main__':
    get_args()



def config():
    users = get_google_sheets_data()
    old_users = mongo_get_users()
    info('Found {0} username pairs in Google Sheets.'.format(len(users)))
    info('Verifying Slack usernames.')
    verify_slack_users(users)
    info('Verified {0} users.'.format(len(users)))
    info('Verifying Gitlab usernames and projects.')
    verify_gitlab_users(users)
    info('Verified {0} users.'.format(len(users)))
    verify_old_users(users)
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


def get_google_sheets_data():
    columns = GoogleSheetsClient(GOOGLE_SHEETS_URL, GOOGLE_SHEETS_CLIENT_SECRET_PATH).get_whole_sheet()
    slack_users = None
    gitlab_users = None
    gitlab_repos = None
    users = []

    # Find columns by name
    for column in columns:
        if GOOGLE_SHEETS_COL_GITLAB_UNAMES in column:
            gitlab_users = column[1:]
        elif GOOGLE_SHEETS_COL_SLACK_UNAMES in column:
            slack_users = column[1:]
        elif GOOGLE_SHEETS_COL_GITLAB_REPOS in column:
            gitlab_repos = column[1:]
        if gitlab_users and slack_users and gitlab_repos:
            break
    else:
        # TODO fix issue with ValueError if the column is empty
        raise ValueError('Invalid column or row name')

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
                            headers=GITLAB_AUTH_HEADER, timeout=10,
                            verify=False)  # Gitlab.pld ssl verification fails.. FIXME
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
    response = requests.get(SLACK_GET_USER_LIST_URL, headers=SLACK_AUTH_HEADER, timeout=10)
    slack_users = response.json().get("members", [])
    verified_users = []

    # A list of usernames for more efficient searches
    unames = [u.get(KEY_SLACK_UNAME, None) for u in users]

    def verify_user(slack_uname, slack_id, user_index):
        unames[user_index] = None
        users[user_index][KEY_SLACK_UNAME] = slack_uname
        users[user_index][KEY_SLACK_ID] = slack_id
        verified_users.append(users[user_index])

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
    users = verified_users[:]


def verify_gitlab_users(users):
    verified_users = []

    for user in users:
        repo_name = user.get(KEY_GITLAB_REPO_NAME, '').lower()
        uname = user.get(KEY_GITLAB_UNAME, '')
        if not repo_name:
            # User has no Gitlab repo. Verifying username only.
            warning('Gitlab user \'{username}\' doesn\'t have a repository field. Verifying username only.'
                    .format(username=uname))
            if verify_gitlab_user(user):
                verified_users.append(user)
            continue

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
    users = verified_users[:]


def verify_gitlab_user(user):
    uname = user.get(KEY_GITLAB_UNAME)
    response = requests.get(GITLAB_GET_USER_URL.format(username=uname),
                            headers=GITLAB_AUTH_HEADER, timeout=10,
                            verify=False)  # Gitlab.pld ssl verification fails.. FIXME
    if response.status_code != requests.codes.ok:
        warning('Woops, something went wrong! Gitlab returned {0}'.format(response.status_code))
    elif response.json():
        # If user exists non-empty json object is returned
        return True
    else:
        warning('Gitlab user \'{username}\' doesn\'t exist. Skipping'.format(username=uname))
    return False


def verify_users_not_empty(users):
    if not users:
        error('No verified users. Exiting!')
        exit(1)


def verify_old_users(new_users):
    old_users = mongo_get_users()
    if not old_users:
        return
    new_unames = set([u.get(KEY_GITLAB_UNAME) for u in new_users])
    old_unames = set([u.get(KEY_GITLAB_UNAME) for u in old_users])
    diff_unames = list(old_unames - new_unames)

    if not diff_unames:
        return

    diff_users = [[item for item in old_users if item[KEY_GITLAB_UNAME] == uname][0] for uname in diff_unames]
    warning('The following users are in db, but not in the new dataset: {users}'.format(users=diff_unames))
    print('Choose an option..\nK - keep all\nD - delete all\nC - choose for each user manually')

    while True:
        choice = input().lower()
        if choice == 'k':
            new_users.extend(diff_users)
            return new_users
        elif choice == 'd':
            # TODO delete all webhooks
            return new_users
        elif choice == 'c':
            break
        print('Choose \'K\' \'D\' or \'C\'')

    print('\nOk, choosing for each user manually. Let\'s go:')

    for user in diff_users:
        uname = user.get(KEY_GITLAB_UNAME)
        print('\nUser: \'{username}\'\nK - Keep\nD - Delete'.format(username=uname))
        while True:
            choice = input().lower()
            if choice == 'k':
                new_users.append(user)
                break
            elif choice == 'd':
                # TODO delete webhook
                break
            print('Choose \'K\' or \'D\'')


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
    except ServerSelectionTimeoutError:
        error('Mongo timeout. '
              'Make sure Mongo server is running and the port number is same as in the configuration file!')
        raise


def set_gitlab_webhooks(users):
    # TODO append port to url
    for index, user in enumerate(users):
        project_id = user.get(KEY_GITLAB_REPO_ID)
        uname = user.get(KEY_GITLAB_UNAME)

        if not project_id:
            # User has no gitlab repo - doesn't need a webhook.
            continue
        response = post_gitlab_webhook(project_id, APP_URL)
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
        timeout=10, verify=verify)


def get_gitlab_webhook_id(project_id, verify=False):
    webhooks = requests.get(GITLAB_GET_PROJECT_HOOKS.format(
        project_id=project_id), headers=GITLAB_AUTH_HEADER,
        timeout=10, verify=verify).json()

    # webhook = next(wh for wh in webhooks if wh.get('url') == APP_URL)
    # return webhook.get('id')

    for wh in webhooks:
        if wh.get('url') == APP_URL:
            return wh.get('id')


def post_gitlab_webhook(project_id, url, issue_events=True, note_events=True, verify=False):
    content = {'url': url, 'id': project_id, 'issues_events': issue_events, 'note_events': note_events}
    return requests.post(GITLAB_POST_WEBHOOK_URL.format(
        project_id=project_id), headers=GITLAB_AUTH_HEADER,
        timeout=10, json=content, verify=verify)
#
#
# if __name__ == '__main__':
#     config()
