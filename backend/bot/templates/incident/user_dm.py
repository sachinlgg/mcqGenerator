import config


class IncidentUserNotification:
    def create(user: str, role: str, channel: str):
        return {
            "channel": user,
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": ":wave: You have been elected as the {} for an incident.".format(
                            role.replace("_", " ").title()
                        ),
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": config.active.roles.get(role),
                    },
                },
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"Please join the channel here: <#{channel}>",
                    },
                },
            ],
        }
