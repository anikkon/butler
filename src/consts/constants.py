"""
NB! Don't touch this unless you know what you're doing!
"""
import yaml
import os.path


path = os.path.abspath("app.config.yaml")
print(path)

with open(path, "r") as f:
    settings = yaml.load(f)

SERVER_PORT = settings['server']['port']
MONGO_PORT = settings['mongo']['port']
MONGO_ADDRESS = settings['mongo']['address']
SERVER_ADDRESS = settings['server']['address'] + ":" + str(settings['server']['port'])
SSL_VERIFY = settings['requests']['ssl_verify']
REQUEST_TIMEOUT = settings['requests']['timeout']
DATA_FROM = settings['data']['from']

'''
Google Sheets
'''
GOOGLE_SHEETS_URL = settings['gsheets']['url']
GOOGLE_SHEETS_SHEET_NAME = settings['gsheets']['sheet_name']
GOOGLE_SHEETS_COL_SLACK_UNAMES = settings['gsheets']['column_slack_unames']
GOOGLE_SHEETS_COL_GITLAB_UNAMES = settings['gsheets']['column_gitlab_unames']
GOOGLE_SHEETS_COL_GITLAB_REPOS = settings['gsheets']['column_gitlab_repos']
GOOGLE_SHEETS_CLIENT_SECRET_PATH = settings['gsheets']['client_secret_path']
GOOGLE_SHEETS_COLUMN_OFFSET = settings['gsheets']['column_offset']

'''
Gitlab
'''
__GITLAB_BASE_URL = settings['gitlab']['root_url'] + 'api/v4/'
GITLAB_GET_PROJECTS_URL = __GITLAB_BASE_URL + 'users/{username}/projects?simple=true'
GITLAB_GET_USER_URL = __GITLAB_BASE_URL + 'users?username={username}'
GITLAB_GET_PROJECT_HOOKS = __GITLAB_BASE_URL + '/projects/{project_id}/hooks'
GITLAB_GET_PUT_DELETE_PROJECT_HOOK = __GITLAB_BASE_URL + '/projects/{project_id}/hooks/{hook_id}'
GITLAB_POST_WEBHOOK_URL = __GITLAB_BASE_URL + 'projects/{project_id}/hooks'
GITLAB_EVENT_ISSUE = 'Issue Hook'
GITLAB_EVENT_NOTE = 'Note Hook'
GITLAB_AUTH_HEADER = {'PRIVATE-TOKEN': settings['gitlab']['auth_token']}

'''
Slack
'''
__SLACK_BASE_URL = 'https://slack.com/api/'
SLACK_POST_MESSAGE_URL = __SLACK_BASE_URL + 'chat.postMessage'
SLACK_GET_USER_LIST_URL = __SLACK_BASE_URL + 'users.list'
SLACK_AUTH_HEADER = {'Authorization': 'Bearer ' + settings['slack']['auth_token']}

'''
Stringsssl_verify
'''
ISSUE_MSG_TO_USER = settings['slack']['messages']['issue']['to_user']
ISSUE_MSG_TO_AUTHOR = settings['slack']['messages']['issue']['to_author']
NOTE_MSG_TO_ALL = settings['slack']['messages']['note']['to_all']
ISSUE_COLOR = '#d32f2f'

''''
Database keys
'''
KEY_SLACK_UNAME = 'slack_username'
KEY_SLACK_ID = 'slack_id'
KEY_GITLAB_UNAME = 'gitlab_username'
KEY_GITLAB_USER_ID = 'gitlab_id'
KEY_GITLAB_REPO_NAME = 'gitlab_repo_name'  # Optional
KEY_GITLAB_REPO_ID = 'gitlab_repo_id'  # Optional
KEY_GITLAB_REPO_HOOK_ID = 'gitlab_repo_hook_id'  # Optional

'''
Supported operations & options
'''
# Supported sources of user data. Add options here adding support for more
INPUT_DATA_SOURCE_GS = 'google-sheets'
INPUT_DATA_SOURCES = [INPUT_DATA_SOURCE_GS]
SUPPORTED_GITLAB_EVENTS = [GITLAB_EVENT_ISSUE, GITLAB_EVENT_NOTE]
