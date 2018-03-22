#!/usr/bin/env python3
from flask import Flask, request
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
from requests import post
from consts import *
from utils import error, warning


app = Flask(__name__)
user_collection = None

SLACK_REQUESTS_HEADER = {**{'Content-type': 'application/json'}, **SLACK_AUTH_HEADER}


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

    if payload is None or event_type not in SUPPORTED_GITLAB_EVENTS:
        return '', 400
    if event_type == GITLAB_EVENT_ISSUE:
        return issue_event(payload)
    if event_type == GITLAB_EVENT_NOTE:
        return note_event(payload)


def issue_event(payload):
    user = get_user(payload)
    author = get_author(payload)
    issue = get_issue(payload)

    if not user: return '', 400
    if not author: author = {}

    attachment_for_user = {
        **new_attachment(ISSUE_MSG_TO_USER, "Assigned by", '@' + author.get(KEY_SLACK_UNAME)),
        **issue}

    attachment_for_author = {
        **new_attachment(ISSUE_MSG_TO_AUTHOR, "Assigned to", '@' + user.get(KEY_SLACK_UNAME)),
        **issue}

    msg_to_user = new_slack_message(user.get(KEY_SLACK_ID), attachment=attachment_for_user)
    msg_to_author = new_slack_message(author.get(KEY_SLACK_ID), attachment=attachment_for_author)

    post(SLACK_POST_MESSAGE_URL, json=msg_to_user, headers=SLACK_REQUESTS_HEADER)
    if author.get(KEY_SLACK_ID):
        post(SLACK_POST_MESSAGE_URL, json=msg_to_author, headers=SLACK_REQUESTS_HEADER)

    return '', 200


def note_event(payload):
    issue_owner = mongo_find_one({KEY_GITLAB_USER_ID: payload.get('issue', {}).get('author_id', '')})
    comment_author = get_author(payload)
    repo_owner = get_user(payload)
    note = get_note(payload)

    notify_repo_owner = repo_owner != issue_owner and repo_owner != comment_author
    notify_issue_owner = issue_owner != comment_author

    attachment = {
        **new_attachment(NOTE_MSG_TO_ALL, "Commented by", '@' + comment_author.get(KEY_SLACK_UNAME)),
        **note}

    msg_to_issue_owner = new_slack_message(issue_owner.get(KEY_SLACK_ID), attachment=attachment)
    msg_to_repo_owner = new_slack_message(repo_owner.get(KEY_SLACK_ID), attachment=attachment)

    if notify_issue_owner:
        post(SLACK_POST_MESSAGE_URL, json=msg_to_issue_owner, headers=SLACK_REQUESTS_HEADER)
    if notify_repo_owner:
        post(SLACK_POST_MESSAGE_URL, json=msg_to_repo_owner, headers=SLACK_REQUESTS_HEADER)

    return '', 200


def mongo_find_one(param):
    try:
        return user_collection.find_one(param)
    except ServerSelectionTimeoutError:
        error('Mongo timeout. '
              'Make sure Mongo server is running and the port number is same as in the configuration file!')


def get_user(payload):
    oa = payload.get('object_attributes', {})
    project_id = oa.get('project_id')
    user = mongo_find_one({KEY_GITLAB_REPO_ID: project_id})
    if user: return user
    warning('Received an event for project with id {0}, but can\'t find the owner.'.format(project_id))


def get_author(payload):
    uname = payload.get('user', {}).get('username', "")
    author = mongo_find_one({KEY_GITLAB_UNAME: uname})
    if author: return author
    warning('Can\'t find user {0} in the database'.format(uname))


def get_issue(payload):
    oa = payload.get('object_attributes', {})
    url = oa.get('url')
    title = oa.get('title')
    description = oa.get('description')
    issue = {}
    if title: issue["title"] = title
    if url: issue['title_link'] = url
    if description: issue["text"] = description
    return issue


def get_note(payload):
    oa = payload.get('object_attributes', {})
    url = oa.get('url')
    content = oa.get('note')
    note = {}
    note['title'] = 'CLick here for details'
    if content: note['text'] = content
    if url: note['title_link'] = url
    return note


def new_attachment(pretext, title, value, color=ISSUE_COLOR):
    return {"color": color, "pretext": pretext, "fields": [{
        "title": title, "value": value, "short": "false"}]}


def new_slack_message(channel_id, attachment=None, as_user=True):
    return {"channel": channel_id, 'as_user': as_user, "attachments": [attachment]}


if __name__ == '__main__':
    start_mongo()
    app.run(host='0.0.0.0', port=SERVER_PORT)
