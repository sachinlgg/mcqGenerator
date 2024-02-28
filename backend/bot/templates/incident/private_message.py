import config


class PrivateMessage:
    @staticmethod
    def message(channel: str, role: str, user: str, message: str):
        return {
            "channel": channel,
            "user": user,
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f":wave: Hello <@{user}> has been assigned the *{role}* role. {message}",
                    },
                },
                {"type": "divider"},
            ],
        }

