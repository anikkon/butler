#!/usr/bin/env python3
import pprint
from flask import Flask, request
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
from requests import post
from consts import *
from utils.printer import error, warning

# TODO handle 'close issue' events
# TODO Note Hook for issue comments

app = Flask(__name__)
user_collection = ''


def start_mongo():
    try:
        client = MongoClient(MONGO_ADDRESS, MONGO_PORT, serverSelectionTimeoutMS=10)
        global user_collection
        user_collection = client.iax058x.users
    except ServerSelectionTimeoutError:
        error('Mongo timeout. '
              'Make sure Mongo server is running and the port number is same as in the configuration file!')
        exit(1)


@app.route('/', methods=['GET'])
def ping():
    return '', 200


@app.route('/', methods=['POST'])
def gitlab_post_hook():
    payload = request.get_json()
    event_type = request.headers.get('X-Gitlab-Event')

    print('X-Gitlab-Event ', event_type)

    if event_type in SUPPORTED_GITLAB_EVENTS and payload is not None:
        return send_slack_message(payload)

    return '', 400


def send_slack_message(payload):
    print('Trying to post to slack')
    pprint.pprint(payload)

    oa = payload.get('object_attributes', {})
    author_uname = payload.get('user', {}).get('username', "")
    project_id = oa.get('project_id')

    if not project_id or not author_uname:
        error('Couldn\'t retrieve project id or author. Skipping.')
        return

    try:
        user_obj = user_collection.find_one({KEY_GITLAB_REPO_ID: project_id})
        author_obj = user_collection.find_one({KEY_GITLAB_UNAME: author_uname})
    except ServerSelectionTimeoutError:
        error('Mongo timeout. '
              'Make sure Mongo server is running and the port number is same as in the configuration file!')
        return

    if not user_obj:
        warning('Received an issue for project with id {0}, but can\'t find the owner.'.format(project_id))
        return
    if not author_obj:
        warning(
            'Received an issue assigned by {0}, but author is not in database.'.format(author_uname))

    user_slack_id = user_obj.get(KEY_SLACK_ID)
    user_slack_uname = user_obj.get(KEY_SLACK_UNAME)
    author_slack_id = author_obj.get(KEY_SLACK_ID)
    author_slack_uname = author_obj.get(KEY_SLACK_UNAME)

    issue_url = oa.get('url')
    issue_title = oa.get('title')
    issue_description = oa.get('description')
    issue_info = {}
    if issue_title:
        issue_info["title"] = issue_title
    if issue_url:
        issue_info['title_link'] = issue_url
    if issue_description:
        issue_info["text"] = issue_description

    attachment_for_user = {**{
        "color": ISSUE_COLOR, "pretext": ISSUE_MSG_TO_USER, "fields": [
            {
                "title": "Assigned by",
                "value": '@' + author_slack_uname,
                "short": "true"
            }
        ]}, **issue_info}

    attachment_for_author = {**{
        "color": ISSUE_COLOR, "pretext": ISSUE_MSG_TO_ASSIGNEE, "fields": [
            {
                "title": "Assigned to",
                "value": '@' + user_slack_uname,
                "short": "true"
            }
        ]}, **issue_info}

    headers = {
        **{'Content-type': 'application/json'},
        **SLACK_AUTH_HEADER
    }

    content_to_user = {
        "channel": user_slack_id,
        'as_user': 'true',
        "attachments": [attachment_for_user]
    }
    post(SLACK_POST_MESSAGE_URL, json=content_to_user, headers=headers)

    if author_slack_id:
        content_to_author = {
            "channel": author_slack_id,
            'as_user': 'true',
            "attachments": [attachment_for_author]
        }
        post(SLACK_POST_MESSAGE_URL, json=content_to_author, headers=headers)

    return '', 200


if __name__ == '__main__':
    start_mongo()
    app.run(port=SERVER_PORT)
