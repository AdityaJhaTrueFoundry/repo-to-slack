import os
import requests
from datetime import datetime, timedelta

def get_activity_users(repo_owner, repo_name, activity_type, headers):
    if activity_type == "stargazers":
        stargazers_list = get_stargazers_with_pagination(repo_owner, repo_name, headers)
        timestamp_key = 'starred_at'
        action = 'star'
        user_key = 'user'
    elif activity_type == "pull_requests":
        url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/pulls"
        timestamp_key = 'created_at'
        action = 'opened a pull request'
        user_key = 'owner'
    elif activity_type == "forks":
        url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/forks"
        timestamp_key = 'created_at'
        user_key = 'owner'
        action = 'forked'
    else:
        print(f"Invalid activity type: {activity_type}")
        return []

    if activity_type != "stargazers":  # Only print the URL if it's not stargazers
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            activities = response.json()

            # Filter users based on the activity timestamp
            activity_users = filter_activity_users(user_key, timestamp_key, activities)
            
        else:
            print(f"Failed to fetch {activity_type} for {repo_owner}/{repo_name}. Status code: {response.status_code}")
            return [], ""
    else:
        # Use the stargazers_list that you fetched earlier
        activity_users = filter_activity_users(user_key, timestamp_key, stargazers_list)
    
    return activity_users, action
    
def filter_activity_users(user_key, timestamp_key, activity_data):
    # Get the current time
    current_time = datetime.now()

    # Define the time threshold (24 hours ago)
    threshold_time = current_time - timedelta(hours=24)

    return [
        activity[user_key]
        for activity in activity_data
        if datetime.strptime(activity[timestamp_key], "%Y-%m-%dT%H:%M:%SZ") > threshold_time
    ]

def get_stargazers_with_pagination(repo_owner, repo_name, headers):
    stargazers_list = []

    # Initialize the URL with the first page
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/stargazers"

    while True:
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            stargazers = response.json()
            if len(stargazers) == 0:
                break  # No more stargazers to fetch

            for stargazer in stargazers:
                stargazers_dict = {
                    "user": stargazer["user"],
                    "starred_at": stargazer["starred_at"],
                }
                stargazers_list.append(stargazers_dict)

            # Check for the "next" link in the response headers
            next_link = response.links.get('next')
            if next_link:
                url = next_link['url']  # Update the URL to the next page
            else:
                break  # No more pages to fetch

        else:
            print(f"Failed to fetch stargazers for {repo_owner}/{repo_name}. Status code: {response.status_code}")
            break  # Stop fetching on error

    return stargazers_list

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

# Slack webhook URL
slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL", "")

# Get Github Authorization Token
github_authorization_token = os.getenv("GITHUB_AUTH_TOKEN", "")

headers = {
    "Accept": "application/vnd.github.star+json",
    "Authorization": f"token {github_authorization_token}"
}

for repository_activity in repository_activity_list:
    repo_owner, repo_name, activity_type = repository_activity.strip().split("/")
    activity_users, action = get_activity_users(repo_owner, repo_name, activity_type, headers)
    if activity_users:
        formatted_profiles = format_user_profiles(activity_users, action)
        slack_message = f"Users who {action} {repo_owner}/{repo_name} in the Last 24 Hours:\n\n"
        slack_message += "\n\n".join(formatted_profiles)

        send_slack_message(slack_webhook_url, slack_message)