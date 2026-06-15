import json
import os

USERS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "active_users.json")


def track_user(chat_id: int):
    users = []
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            users = json.load(f)
    if chat_id not in users:
        users.append(chat_id)
        with open(USERS_FILE, "w") as f:
            json.dump(users, f)


def get_active_users() -> list:
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    return []
