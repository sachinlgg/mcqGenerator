import config

from bot.slack.client import slack_workspace_id
from typing import Any, Dict


class IncidentChannelDigestNotification:
    @staticmethod
    def create(
        incident_channel_details: Dict[str, Any],
        conference_bridge: str,
        severity: str,
    ):
        if incident_channel_details.get("is_security_incident"):
            header = ":warning::lock::fire_engine: {}".format(
                incident_channel_details.get(
                    "incident_description"
                )
            )
        else:
            header = ":warning::fire_engine: {}".format(
                incident_channel_details.get(
                    "incident_description"
                )
            )

        inc_button_action_elements = [
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "Postmortem Library",
                },
                "url": config.active.links.get(
                    "incident_postmortems"
                ),
                "action_id": "incident.incident_postmortem_link",
            }
        ]
        if not incident_channel_details.get("private_channel"):
            inc_button_action_elements.insert(0,{
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "War Room",
                },
                "url": conference_bridge,
                "action_id": "incident.click_conference_bridge_link",
            })
        return {
            "channel": f"{config.active.digest_channel}",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": header,
                    },
                },
                {
                    "block_id": "digest_channel_severity",
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f":fire: *Severity*: {severity.upper()}",
                    },
                },
                {
                    "block_id": "digest_channel_status",
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": ":hourglass_flowing_sand: *Status*: Investigating",
                    },
                },
                {
                    "block_id": "digest_channel_reporter",
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": ":speaking_head_in_silhouette: *Reporter*: <@{}>".format(
                            incident_channel_details.get('user')
                        ),
                    },
                },
                {
                    "block_id": "join_incident_channel",
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": ":slack: *Channel*: #{}".format(incident_channel_details.get("name"))
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "A new incident has been declared. "
                        + "Please join the channel here to participate.",
                    },
                },
                {
                    "type": "actions",
                    "block_id": "incchannelbuttons",
                    "elements": inc_button_action_elements,
                },
            ],
        }

    @staticmethod
    def update(
        incident_id: str,
        incident_description: str,
        is_security_incident: bool,
        status: str,
        severity: str,
        conference_bridge: str,
        channel_name: str = 'default_channel_name',
        user: str = 'U05T9BLKJ07',
        private_channel: bool = False,
    ):
        incident_reacji_header = (
            ":warning::lock::fire_engine: {}".format(incident_description)
            if is_security_incident
            else ":warning::fire_engine: {}".format(incident_description)
        )
        incident_type = (
            "Critical Incident" if is_security_incident else "Incident"
        )
        emoji_mapping = {
            "Investigating": ":hourglass_flowing_sand:",
            "Identified": ":bulb:",
            "Monitoring": ":construction:",
            "Resolved": ":white_check_mark:",
        }
        emoji = emoji_mapping.get(status.title(), ":hourglass_flowing_sand:")

        if status == "resolved":
            header = f":white_check_mark: Resolved {incident_description} :white_check_mark:"
            message = "This incident has been resolved."
        else:
            header = f"{incident_reacji_header}"
            message = "This incident is in progress. Current status is listed here. Join the channel for more information."

        inc_button_action_elements = [
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "Postmortem Library",
                },
                "url": config.active.links.get(
                    "incident_postmortems"
                ),
                "action_id": "incident.incident_postmortem_link",
            }
        ]
        if not private_channel:
            inc_button_action_elements.insert(0,{
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "War Room",
                },
                "url": conference_bridge,
                "action_id": "incident.click_conference_bridge_link",
            })
        return [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": header,
                },
            },
            {
                "block_id": "digest_channel_severity",
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f":fire: *Severity*: {severity.upper()}",
                },
            },
            {
                "block_id": "digest_channel_status",
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{emoji} *Status*: {status.title()}",
                },
            },
            {
                "block_id": "digest_channel_reporter",
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": ":speaking_head_in_silhouette: *Reporter*: <@{}>".format(user),
                },
            },
            {
                "block_id": "join_incident_channel",
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": ":slack: *Channel*: #{}".format(channel_name)
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": message,
                },
            },
            {
                "type": "actions",
                "block_id": "incchannelbuttons",
                "elements": inc_button_action_elements,
            },
        ]
