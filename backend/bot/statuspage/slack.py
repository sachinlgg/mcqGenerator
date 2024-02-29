import config
import logging

from typing import Dict

logger = logging.getLogger("statuspage.slack")


def return_new_statuspage_incident_message(channel_id: str) -> Dict[str, str]:
    """Posts a message in the incident channel prompting for the creation of a Statuspage incident
    Args:
        channel_id: the channel to post the message to
        info: Dict[str, str] as returned by the StatuspageIncident class info method
    """
    return {
        "channel": channel_id,
        "blocks": [
            {
                "type": "actions",
                "block_id": "statuspage_starter_button",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Start Statuspage Incident",
                            "emoji": True,
                        },
                        "value": channel_id,
                        "action_id": "open_statuspage_incident_modal",
                        "style": "primary",
                    },
                    {
                        "type": "button",
                        "style": "primary",
                        "action_id": "statuspage.open_statuspage",
                        "text": {
                            "type": "plain_text",
                            "text": "Open Statuspage",
                        },
                        "url": config.active.integrations.get(
                            "statuspage"
                        ).get("url"),
                    },
                ],
            },
            {"type": "divider"},
        ],
    }


def return_new_statuspage_incident_message_with_zoom(channel_id: str, zoom_info: dict = None, status_page_info: dict = None) -> Dict[str, str]:
    """
    Posts a message in the incident channel prompting for the creation of a Statuspage incident

    Args:
        channel_id: the channel to post the message to
        zoom_info: Dict containing 'enabled' (boolean) and 'url' (string) for Zoom meeting, if available
        status_page_info: Dict containing 'enabled' (boolean) and 'url' (string) for Status Page, if available
    """
    blocks = [
        {
            "type": "actions",
            "block_id": "statuspage_starter_button",
            "elements": [],
        },
        {"type": "divider"},
    ]

    if zoom_info and zoom_info.get('enabled', True):
        blocks[0]['elements'].append({
            "type": "button",
            "text": {
                "type": "plain_text",
                "text": "Zoom War Room",
            },
            "url": zoom_info['url'],
            "action_id": "zoom.join_meeting",
            "style": "primary",
        })

    if status_page_info and status_page_info.get('enabled', True):
        blocks[0]['elements'].extend([
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "Start Statuspage Incident",
                    "emoji": True,
                },
                "value": channel_id,
                "action_id": "open_statuspage_incident_modal",
                "style": "primary",
            },
            {
                "type": "button",
                "style": "primary",
                "action_id": "statuspage.open_statuspage",
                "text": {
                    "type": "plain_text",
                    "text": "Open Statuspage",
                },
                "url": config.active.integrations.get("statuspage").get("url"),
            },
        ])

    return {"channel": channel_id, "blocks": blocks}


