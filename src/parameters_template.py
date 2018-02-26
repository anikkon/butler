"""
Template of the application configuration file. Change the values to fit your app.
"""

'''
Server config
'''
DEFAULT_PORT_APP = ''
DEFAULT_PORT_DB = ''
APP_URL = ''

'''
Google Sheets
'''
GOOGLE_SHEETS_URL = ''
GOOGLE_SHEETS_SHEET_NAME = ''
GOOGLE_SHEETS_COL_SLACK_UNAMES = ''  # name of the column with slack 'real names', i.e. 'Andree Prees'
GOOGLE_SHEETS_COL_GITLAB_UNAMES = ''  # name of the column with gitlab usernames
GOOGLE_SHEETS_COL_GITLAB_REPOS = ''  # name of the column with gitlab repositories
GOOGLE_SHEETS_CLIENT_SECRET_PATH = ''

'''
Gitlab
'''
GITLAB_AUTH_TOKEN = ''
GITLAB_ROOT_URL = ''

'''
Slack
'''
SLACK_AUTH_TOKEN = ''

'''
Strings
'''
ISSUE_MSG_TO_USER = 'You\'ve got an issue, sir!   :face_with_rolling_eyes:'
ISSUE_MSG_TO_AUTHOR = 'You\'ve opened an issue, sir!   :thinking_face:'
