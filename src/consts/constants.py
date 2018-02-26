"""
NB! Don't touch this unless you know what you're doing!
"""
import config as cf


SERVER_PORT = cf.SERVER_PORT
MONGO_PORT = cf.MONGO_PORT
MONGO_ADDRESS = cf.MONGO_ADDRESS
SERVER_ADDRESS = cf.SERVER_ADDRESS    # TODO change this line for the following in prod
# SERVER_ADDRESS = params.SERVER_ADDRESS + ":" + params.SERVER_PORT
SSL_VERIFY = cf.SSL_VERIFY
REQUEST_TIMEOUT = cf.REQUEST_TIMEOUT

'''
Google Sheets
'''
GOOGLE_SHEETS_URL = cf.GOOGLE_SHEETS_URL
GOOGLE_SHEETS_SHEET_NAME = cf.GOOGLE_SHEETS_SHEET_NAME
GOOGLE_SHEETS_COL_SLACK_UNAMES = cf.GOOGLE_SHEETS_COL_SLACK_UNAMES
GOOGLE_SHEETS_COL_GITLAB_UNAMES = cf.GOOGLE_SHEETS_COL_GITLAB_UNAMES
GOOGLE_SHEETS_COL_GITLAB_REPOS = cf.GOOGLE_SHEETS_COL_GITLAB_REPOS
GOOGLE_SHEETS_CLIENT_SECRET_PATH = cf.GOOGLE_SHEETS_CLIENT_SECRET_PATH

'''
Gitlab
'''
__GITLAB_BASE_URL = cf.GITLAB_ROOT_URL + 'api/v4/'
GITLAB_GET_PROJECTS_URL = __GITLAB_BASE_URL + 'users/{username}/projects?simple=true'
GITLAB_GET_USER_URL = __GITLAB_BASE_URL + 'users?username={username}'
GITLAB_GET_PROJECT_HOOKS = __GITLAB_BASE_URL + '/projects/{project_id}/hooks'
GITLAB_GET_PUT_DELETE_PROJECT_HOOK = __GITLAB_BASE_URL + '/projects/{project_id}/hooks/{hook_id}'
GITLAB_POST_WEBHOOK_URL = __GITLAB_BASE_URL + 'projects/{project_id}/hooks'
GOOGLE_SHEETS_COLUMN_OFFSET = cf.GOOGLE_SHEETS_COLUMN_OFFSET
GITLAB_EVENT_ISSUE = 'Issue Hook'
GITLAB_EVENT_NOTE = 'Note Hook'
GITLAB_AUTH_HEADER = {'PRIVATE-TOKEN': cf.GITLAB_AUTH_TOKEN}

'''
Slack
'''
__SLACK_BASE_URL = 'https://slack.com/api/'
SLACK_POST_MESSAGE_URL = __SLACK_BASE_URL + 'chat.postMessage'
SLACK_GET_USER_LIST_URL = __SLACK_BASE_URL + 'users.list'
SLACK_AUTH_HEADER = {'Authorization': 'Bearer ' + cf.SLACK_AUTH_TOKEN}

'''
Strings
'''
ISSUE_MSG_TO_USER = cf.ISSUE_MSG_TO_USER
ISSUE_MSG_TO_ASSIGNEE = cf.ISSUE_MSG_TO_AUTHOR
ISSUE_COLOR = '#d32f2f'

''''
Database keys
'''
KEY_SLACK_UNAME = 'slack_username'
KEY_SLACK_ID = 'slack_id'
KEY_GITLAB_UNAME = 'gitlab_username'
KEY_GITLAB_REPO_NAME = 'gitlab_repo_name'  # Optional
KEY_GITLAB_REPO_ID = 'gitlab_repo_id'  # Optional
KEY_GITLAB_REPO_HOOK_ID = 'gitlab_repo_hook_id'  # Optional