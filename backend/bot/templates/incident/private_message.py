import config


class PrivateMessage:
    @staticmethod
    def message(channel: str, role: str, user: str):
        return {
            "channel": channel,
            "user": user,
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": ":wave: You have been elected as the {} role.".format(
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
            ],
        }

