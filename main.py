import os
import requests
from datetime import datetime, timedelta

def get_activity_users(repo_owner, repo_name, activity_type):
    if activity_type == "stargazers":
        url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/stargazers"
        timestamp_key = 'starred_at'
        action = 'star'
    elif activity_type == "pull_requests":
        url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/pulls"
        timestamp_key = 'created_at'
        action = 'opened a pull request'
    elif activity_type == "forks":
        url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/forks"
        timestamp_key = 'created_at'
        action = 'forked'
    else:
        print(f"Invalid activity type: {activity_type}")
        return []

    headers = {
        "Accept": "application/vnd.github.v3+json"
    }

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        activities = response.json()

        # Get the current time
        current_time = datetime.now()

        # Define the time threshold (24 hours ago)
        threshold_time = current_time - timedelta(hours=24)

        # Filter users based on the activity timestamp
        activity_users = [
            activity['user']
            for activity in activities
            if datetime.strptime(activity[timestamp_key], "%Y-%m-%dT%H:%M:%SZ") > threshold_time
        ]

        return activity_users, action
    else:
        print(f"Failed to fetch {activity_type} for {repo_owner}/{repo_name}. Status code: {response.status_code}")
        return [], ""

def format_user_profiles(users, action):
    formatted_profiles = []
    for user in users:
        profile = f"Username: {user['login']}\n" \
                  f"Profile URL: {user['html_url']}\n" \
                  f"Avatar URL: {user['avatar_url']}\n" \
                  f"Type: {user['type']}\n" \
                  f"Action: {action}\n"
        formatted_profiles.append(profile)

    return formatted_profiles

def send_slack_message(webhook_url, message):
    payload = {
        "text": message
    }

    response = requests.post(webhook_url, json=payload)
    if response.status_code == 200:
        print("Message sent successfully to Slack!")
    else:
        print(f"Failed to send message to Slack. Status code: {response.status_code}")

# Read the repository list and activity types from environment variables
repository_activity_list = os.getenv("REPOSITORY_ACTIVITY_LIST", "").split(",")

# Provide your Slack webhook URL
slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL", "")

for repository_activity in repository_activity_list:
    repo_owner, repo_name, activity_type = repository_activity.strip().split("/")
    activity_users, action = get_activity_users(repo_owner, repo_name, activity_type)
    if activity_users:
        formatted_profiles = format_user_profiles(activity_users, action)
        slack_message = f"Users who {action} {repo_owner}/{repo_name} in the Last 24 Hours:\n\n"
        slack_message += "\n\n".join(formatted_profiles)

        send_slack_message(slack_webhook_url, slack_message)