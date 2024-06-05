import config
import logging
import variables
import random
import time
import asyncio


from bot.audit.log import read as read_logs, write as write_log
from bot.exc import ConfigurationError
from bot.incident import incident
from bot.jira.issue import JiraIssue
from bot.models.incident import (
    db_read_all_incidents,
    db_read_incident_channel_id,
    db_read_open_incidents,
    db_read_incident,
    db_update_incident_last_update_sent_col,
    db_update_jira_issues_col,
    db_read_open_incidents_sorted,
)
from bot.models.pager import read_pager_auto_page_targets
from bot.shared import tools
from bot.slack.client import (check_user_in_group,slack_web_client,)
from bot.slack.handler import app, help_menu
from bot.slack.messages import (
    incident_list_message,
    pd_on_call_message,
)
from bot.statuspage.handler import (
    StatuspageComponents,
    StatuspageIncident,
    StatuspageIncidentUpdate,
)
from bot.templates.incident.updates import (
    IncidentUpdate,
)
from bot.templates.tools import parse_modal_values
from datetime import datetime
from bot.incident import actions as inc_actions

logger = logging.getLogger("slack.modals")

placeholder_severity = [sev for sev, _ in config.active.severities.items()][-1]


@app.event("app_home_opened")
def update_home_tab(client, event, logger):
    """
    Provide information via the app's home screen
    """
    base_blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": ":octopus: Octo",
            },
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Create New Incident",
                        "emoji": True,
                    },
                    "value": "show_incident_modal",
                    "action_id": "open_incident_modal",
                    "style": "danger",
                }
            ],
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Hi there, <@"
                + event["user"]
                + "> :wave:*!\n\nI'm your friendly Incident Companion,"
                + "here for faster incident resolution..\n",
            },
        },
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": ":firefighter: Creating Incidents",
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "To create a new incident, you can do the following:\n"
                + "- Use the button here\n "
                + "- Search for 'create a new incident' in the Slack search bar\n"
                + "- type _/octo create_ in any Slack channel to find my command and run it.",
            },
        },
        {
            "type": "image",
            "title": {
                "type": "plain_text",
                "text": "How to create a new incident",
                "emoji": True,
            },
            "image_url": "https://i.imgur.com/bGGtLr4.png",
            "alt_text": "how to create a new incident",
        },
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": ":point_right: Documentation and Learning Materials",
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "I offer a plethora of features. Explore them all by visiting my <https://bugster.ai/>.",
            },
        },
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": ":point_right: My Commands",
            },
        },
        {"type": "divider"},
    ]
    help_block = help_menu(include_header=False)
    base_blocks.extend(help_block)
    # Also add in open incident info
    database_data = db_read_all_incidents()
    open_incidents = incident_list_message(database_data, all=False)
    base_blocks.extend(open_incidents)
    # On call info
    if "pagerduty" in config.active.integrations:
        from bot.pagerduty import api as pd_api

        pd_oncall_data = pd_api.find_who_is_on_call()
        on_call_info = pd_on_call_message(data=pd_oncall_data)
        base_blocks.extend(on_call_info)
    # Version info
    base_blocks.extend(
        [
            {"type": "divider"},
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Version {config.__version__}",
                    }
                ],
            },
        ]
    )
    try:
        client.views_publish(
            user_id=event["user"],
            view={
                "type": "home",
                "blocks": base_blocks,
            },
        )
    except Exception as e:
        logger.error(f"Error publishing home tab: {e}")


@app.action("open_incident_modal")
@app.shortcut("open_incident_modal")
def open_modal(ack, body, client):
    """
    Provides the modal that will display when the shortcut is used to start an incident
    """
    base_blocks = [
        {
            "type": "input",
            "block_id": "open_incident_modal_desc",
            "optional": True,
            "element": {
                "type": "plain_text_input",
                "action_id": "open_incident_modal_set_description",
                "placeholder": {
                    "type": "plain_text",
                    "text": "A brief description of the Incident.",
                },
                "multiline": True,
            },
            "label": {"type": "plain_text", "text": "What's going on? "},
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "Compose a brief,punchy description of the current situation. Feel free to keep it blank and modify it at a later time.."
                }
            ]
        },
        {
            "type": "section",
            "block_id": "is_security_incident",
            "text": {
                "type": "mrkdwn",
                "text": "*Is this a security incident?*",
            },
            "accessory": {
                "action_id": "open_incident_modal_set_security_type",
                "type": "static_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select...",
                },
                "initial_option": {
                    "text": {
                        "type": "plain_text",
                        "text": "No",
                    },
                    "value": "false",
                },
                "options": [
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Yes",
                        },
                        "value": "true",
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "No",
                        },
                        "value": "false",
                    },
                ],
            },
        },
        {
            "block_id": "severity",
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*Severity*"},
            "accessory": {
                "type": "static_select",
                "action_id": "open_incident_modal_set_severity",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select a severity...",
                    "emoji": True,
                },
                "initial_option": {
                    "text": {
                        "type": "plain_text",
                        "text": placeholder_severity.upper(),
                    },
                    "value": placeholder_severity,
                },
                "options": [
                    {
                        "text": {
                            "type": "plain_text",
                            "text": sev.upper(),
                            "emoji": True,
                        },
                        "value": sev,
                    }
                    for sev, _ in config.active.severities.items()
                ],
            },
        },
        {
            "type": "context",
            "block_id": "severity_context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": get_severity_context()
                }
            ]
        },
        {
            "type": "section",
            "block_id": "private_channel",
            "text": {
                "type": "mrkdwn",
                "text": "*Who should be able to see this incident ?*",
            },
            "accessory": {
                "action_id": "open_incident_modal_set_private",
                "type": "static_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select...",
                },
                "initial_option": {
                    "text": {
                        "type": "plain_text",
                        "text": "Everyone",
                    },
                    "value": "false",
                },
                "options": [
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Private",
                        },
                        "value": "true",
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Everyone",
                        },
                        "value": "false",
                    },
                ],
            },
        },
        {
            "type": "context",
            "block_id": "private_channel_context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "*Everyone:* All members in the Slack workspace will have access to this incident.\n *Private:* Only invited members in the channel will have access."
                }
            ]
        }
    ]

    """
    If there are teams that will be auto paged, mention that
    """
    if "pagerduty" in config.active.integrations:
        auto_page_targets = read_pager_auto_page_targets()
        if len(auto_page_targets) != 0:
            base_blocks.extend(
                [
                    {"type": "divider"},
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": ":point_right: *The following teams will "
                            + "be automatically paged when this incident is created:*",
                        },
                    },
                ]
            )
            for i in auto_page_targets:
                for k, v in i.items():
                    base_blocks.extend(
                        [
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": f"_{k}_",
                                },
                            },
                        ]
                    )
    ack()
    client.views_open(
        trigger_id=body["trigger_id"],
        view={
            "type": "modal",
            # View identifier
            "callback_id": "open_incident_modal",
            "title": {"type": "plain_text", "text": "Start a new incident"},
            "submit": {"type": "plain_text", "text": "Start"},
            "blocks": base_blocks,
        },
    )


@app.view("open_incident_modal")
def handle_submission(ack, body, client):
    """
    Handles open_incident_modal
    """
    ack()
    parsed = parse_modal_values(body)
    user = body.get("user").get("id")

    # Create request parameters object
    try:
        request_parameters = incident.RequestParameters(
            channel="modal",
            incident_description=parsed.get("open_incident_modal_set_description"),
            user=user,
            severity=parsed.get("open_incident_modal_set_severity"),
            created_from_web=False,
            is_security_incident=parsed.get("open_incident_modal_set_security_type")
            in (
                "True",
                "true",
                True,
            ),
            private_channel=parsed.get("open_incident_modal_set_private")
            in (
                "True",
                "true",
                True,
            ),
        )
        resp = incident.create_incident(request_parameters)
        client.chat_postMessage(channel=user, text=resp)
    except ConfigurationError as error:
        logger.error(error)


@app.action("open_incident_general_update_modal")
@app.shortcut("open_incident_general_update_modal")
def open_modal(ack, body, client):
    """
    Provides the modal that will display when the shortcut is used to update audience about an incident
    """
    ack()

    # Build blocks for open incidents
    database_data = db_read_open_incidents_sorted(return_json=False, order_aesc=False)

    response = open_incident_general_update_modal_auto_select_incident(ack,body,client,database_data)
    response_state = parse_modal_values(response)
    auto_select_current_channel_id = response_state['incident_update_modal_select_incident_auto_select_shortcut']
    index = tools.find_index_in_obj_list(database_data,"channel_id",auto_select_current_channel_id)
    view = {
        "type": "modal",
        # View identifier
        "callback_id": "open_incident_general_update_modal",
        "title": {"type": "plain_text", "text": "Provide incident update"},
        "submit": {"type": "plain_text", "text": "Submit"},
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "This will send a formatted, timestamped message "
                            + "to the public incidents channel to provide an update "
                            + "on the status of an incident. Use this to keep those "
                            + "outside the incident process informed.",
                },
            },
            {
                "block_id": "open_incident_general_update_modal_incident_channel",
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Associated Incident:",
                },
                "accessory": {
                    "type": "static_select",
                    "action_id": "incident_update_modal_select_incident",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Select an ongoing incident...",
                        "emoji": True,
                    },
                    "options": [
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "None",
                                "emoji": True,
                            },
                            "value": "none",
                        }
                        if len(database_data) == 0
                        else {
                            "text": {
                                "type": "plain_text",
                                "text": f"<#{inc.channel_id}>",
                                "emoji": True,
                            },
                            "value": f"<#{inc.channel_id}>",
                        }
                        for inc in database_data
                        if inc.status != "resolved"
                    ],
                    "initial_option": {
                        "text": {
                            "type": "plain_text",
                            "text": f"<#{auto_select_current_channel_id}>",
                            "emoji": True,
                        },
                        "value": f"<#{auto_select_current_channel_id}>",
                    } if index != -1
                    else {
                        "text": {
                            "type": "plain_text",
                            "text": f"<#{database_data[0].channel_id}>",
                            "emoji": True,
                        },
                        "value": f"<#{database_data[0].channel_id}>",
                    }
                },
            },
            {
                "type": "input",
                "block_id": "open_incident_general_update_modal_impacted_resources",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "impacted_resources",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "e.g. API, Authentication, Dashboards",
                    },
                    "multiline": True,
                },
                "label": {
                    "type": "plain_text",
                    "text": "Impacted Resources:",
                },
            },
            {
                "type": "input",
                "block_id": "open_incident_general_update_modal_update_msg",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "message",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "A brief message to include with this update.",
                    },
                    "multiline": True,
                },
                "label": {
                    "type": "plain_text",
                    "text": "Message to Include:",
                },
            },
        ]
        if len(database_data) != 0
        else [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "There are currently no open incidents.",
                },
            },
        ],
    }
    if len(database_data) == 0:
        del view["submit"]
    client.views_update(view_id=response["view"]["id"],hash=response["view"]["hash"],view= view)


def open_incident_general_update_modal_auto_select_incident (ack, body, client,database_data):
    ack()

    view = {
        "type": "modal",
        # View identifier
        "callback_id": "open_incident_general_update_modal",
        "title": {"type": "plain_text", "text": "Provide incident update"},
        "submit": {"type": "plain_text", "text": "Submit"},
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "This will send a formatted, timestamped message "
                            + "to the public incidents channel to provide an update "
                            + "on the status of an incident. Use this to keep those "
                            + "outside the incident process informed.",
                },
            },
            {
                "type": "section",
                "block_id": "open_incident_general_update_modal_incident_channel_auto_select",
                "text": {
                    "type": "mrkdwn",
                    "text": "Associated Incident:"
                },
                "accessory": {
                    "action_id": "incident_update_modal_select_incident_auto_select_shortcut",
                    "type": "conversations_select",
                    "default_to_current_conversation": True,
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Select an ongoing incident..."
                    }
                }
            },
            {
                "type": "input",
                "block_id": "open_incident_general_update_modal_impacted_resources",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "impacted_resources",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "e.g. API, Authentication, Dashboards",
                    },
                    "multiline": True,
                },
                "label": {
                    "type": "plain_text",
                    "text": "Impacted Resources:",
                },
            },
            {
                "type": "input",
                "block_id": "open_incident_general_update_modal_update_msg",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "message",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "A brief message to include with this update.",
                    },
                    "multiline": True,
                },
                "label": {
                    "type": "plain_text",
                    "text": "Message to Include:",
                },
            },
        ]
        if len(database_data) != 0
        else [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "There are currently no open incidents.",
                },
            },
        ],
    }
    response = client.views_open(
        trigger_id=body["trigger_id"],
        view=view,
    )
    return response


@app.view("open_incident_general_update_modal")
def handle_submission(ack, body, client):
    import sys

    """
    Handles open_incident_general_update_modal
    """
    ack()
    parsed = parse_modal_values(body)
    channel_id = parsed.get("incident_update_modal_select_incident")
    # Extract the channel ID without extra characters
    for character in "#<>":
        channel_id = channel_id.replace(character, "")
    try:
        incident_data = db_read_incident(channel_id=channel_id)
        status = incident_data.status
        client.chat_postMessage(
            thread_ts=incident_data.dig_message_ts,
            channel=variables.digest_channel_id,
            blocks=IncidentUpdate.public_update(
                incident_id=channel_id,
                impacted_resources=parsed.get("impacted_resources"),
                message=parsed.get("message"),
                timestamp=tools.fetch_timestamp(),
                status = status.capitalize()
            ),
            text="Incident update for incident <#{}>: Message: {} Impacted Resources: {}".format(
                channel_id, parsed.get("message"),parsed.get("impacted_resources")
            ),
        )
    except Exception as error:
        logger.error(f"Error sending update out for {channel_id}: {error}")
    finally:
        db_update_incident_last_update_sent_col(
            channel_id=channel_id,
            last_update_sent=tools.fetch_timestamp(),
        )




"""
Catch Me On Incident
"""

@app.action("open_incident_catch_me_up_modal")
@app.shortcut("open_incident_catch_me_up_modal")
def open_modal(ack, body, client):
    """
    Provides the modal that will provide trigger catch me on incident
    """
    ack()

    # Build blocks for open incidents
    database_data = db_read_open_incidents_sorted(return_json=False, order_aesc=False)

    response = open_incident_catch_me_up_modal_auto_select_incident(ack,body,client,database_data)
    response_state = parse_modal_values(response)
    auto_select_current_channel_id = response_state['incident_catch_me_up_modal_select_incident_auto_select_shortcut']
    index = tools.find_index_in_obj_list(database_data,"channel_id",auto_select_current_channel_id)
    view = {
        "type": "modal",
        # View identifier
        "callback_id": "open_incident_catch_me_up_modal",
        "title": {"type": "plain_text", "text": "Catch Me On Incident"},
        "submit": {"type": "plain_text", "text": "Submit"},
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Catch me on Incident is a feature"
                            + "that reads context from the incident channel and transcripts"
                            + "providing a brief summary of what's going on with the incident.",
                },
            },
            {
                "block_id": "open_incident_catch_me_up_modal_incident_channel",
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Choose Incident Channel:",
                },
                "accessory": {
                    "type": "static_select",
                    "action_id": "incident_catch_me_up_modal_select_incident",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Select an ongoing incident...",
                        "emoji": True,
                    },
                    "options": [
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "None",
                                "emoji": True,
                            },
                            "value": "none",
                        }
                        if len(database_data) == 0
                        else {
                            "text": {
                                "type": "plain_text",
                                "text": f"<#{inc.channel_id}>",
                                "emoji": True,
                            },
                            "value": f"<#{inc.channel_id}>",
                        }
                        for inc in database_data
                        if inc.status != "resolved"
                    ],
                    "initial_option": {
                        "text": {
                            "type": "plain_text",
                            "text": f"<#{auto_select_current_channel_id}>",
                            "emoji": True,
                        },
                        "value": f"<#{auto_select_current_channel_id}>",
                    } if index != -1
                    else {
                        "text": {
                            "type": "plain_text",
                            "text": f"<#{database_data[0].channel_id}>",
                            "emoji": True,
                        },
                        "value": f"<#{database_data[0].channel_id}>",
                    }
                },
            },
        ]
        if len(database_data) != 0
        else [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "There are currently no open incidents.",
                },
            },
        ],
    }
    if len(database_data) == 0:
        del view["submit"]
    client.views_update(view_id=response["view"]["id"],hash=response["view"]["hash"],view= view)


def open_incident_catch_me_up_modal_auto_select_incident (ack, body, client,database_data):
    ack()

    view = {
        "type": "modal",
        # View identifier
        "callback_id": "open_incident_catch_me_up_modal",
        "title": {"type": "plain_text", "text": "Catch Me On Incident"},
        "submit": {"type": "plain_text", "text": "Submit"},
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Catch me on Incident is a feature"
                            + "that reads context from the incident channel and transcripts"
                            + "providing a brief summary of what's going on with the incident.",             
                },
            },
            {
                "type": "section",
                "block_id": "open_incident_catch_me_up_modal_incident_channel_auto_select",
                "text": {
                    "type": "mrkdwn",
                    "text": "Choose Incident Channel:"
                },
                "accessory": {
                    "action_id": "incident_catch_me_up_modal_select_incident_auto_select_shortcut",
                    "type": "conversations_select",
                    "default_to_current_conversation": True,
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Select an ongoing incident..."
                    }
                }
            },
        ]
        if len(database_data) != 0
        else [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "There are currently no open incidents.",
                },
            },
        ],
    }
    response = client.views_open(
        trigger_id=body["trigger_id"],
        view=view,
    )
    return response



@app.view("open_incident_catch_me_up_modal")
def handle_submission(ack, body, client):

    """
    Handles open_incident_catch_me_up_modal
    """
    ack()
    parsed = parse_modal_values(body)
    channel_id = parsed.get("incident_catch_me_up_modal_select_incident")
    # Extract the channel ID without extra characters
    for character in "#<>":
        channel_id = channel_id.replace(character, "")
    try:
        incident_data = db_read_incident(channel_id=channel_id)
        incident_slack_messages = inc_actions.get_incident_slack_thread(incident_data.channel_id)
        incident_catch_up_summary = asyncio.run(inc_actions.generate_catch_me_on_incident(incident_data.channel_id, incident_slack_messages))
        user = body["user"]["id"]

        client.chat_postEphemeral(
            channel=incident_data.channel_id,
            user= user,
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "plain_text",
                        "text": f"{incident_catch_up_summary}",
                        "emoji": True
                    }
                },
            ],
            text="Catch me on incident:",
        )

    except Exception as error:
        logger.error(f"Error getting summary out for {channel_id}: {error}")
        


"""
Paging
"""

    

@app.shortcut("open_incident_bot_pager")
def open_modal(ack, body, client):
    # Acknowledge the command request
    ack()

    if "pagerduty" in config.active.integrations:
        from bot.pagerduty import api as pd_api

        database_data = db_read_open_incidents()

        
        blocks = [
            {
                "type": "section",
                "block_id": "incident_bot_pager_service_select",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Which Service is affected?*",
                },
                "accessory": {
                    "action_id": "update_incident_bot_pager_selected_service",
                    "type": "static_select",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Service...",
                    },
                    "options": [
                        {
                            "text": {
                                "type": "plain_text",
                                "text": ep,
                            },
                            "value": ep,
                        }
                        for ep in pd_api.find_services()
                    ],
                },
            },
            {
                "type": "context",
                "block_id": "incident_bot_pager_service_select_context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "The services you've defined in PagerDuty, which is affected during the incident"
                    }
                ]
            },
            {
                "type": "section",
                "block_id": "incident_bot_pager_team_select",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Which team do you need to page?*",
                },
                "accessory": {
                    "action_id": "update_incident_bot_pager_selected_team",
                    "type": "static_select",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Team...",
                    },
                    "options": [
                        {
                            "text": {
                                "type": "plain_text",
                                "text": ep,
                            },
                            "value": ep,
                        }
                        for ep in pd_api.find_who_is_on_call()
                    ],
                },
            },
            {
                "type": "context",
                "block_id": "incident_bot_pager_team_context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "Select the team you want to notify via PagerDuty to address the incident"
                    }
                ]
            },
            {
                "type": "section",
                "block_id": "incident_bot_pager_priority_select",
                "text": {
                    "type": "mrkdwn",
                    "text": "*What's Esclation urgency level?*",
                },
                "accessory": {
                    "action_id": "update_incident_bot_pager_selected_priority",
                    "type": "static_select",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Urgency...",
                    },
                    "options": [
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "low",
                            },
                            "value": "low",
                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "high",
                            },
                            "value": "high",
                        },
                    ],
                },
            },
            {
                "type": "context",
                "block_id": "incident_bot_pager_priority_select_context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "Choose the urgency level between *low* or *high* for the PagerDuty escalation"
                    }
                ]
            },
        ]
        incident_choose_block = {
            "type": "section",
            "block_id": "incident_bot_pager_incident_select",
            "text": {
                "type": "mrkdwn",
                "text": "*Specify the Incident to Escalate?*",
            },
            "accessory": {
                "action_id": "update_incident_bot_pager_selected_incident",
                "type": "static_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Incident...",
                },
                "options": [
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "None",
                            "emoji": True
                        },
                        "value": "none"
                    }
                ] if not database_data else [
                    {
                        "text": {
                            "type": "plain_text",
                            "text": f"#{inc.channel_name}",
                            "emoji": True
                        },
                        "value": f"{inc.channel_name}/{inc.channel_id}"
                    }
                    for inc in database_data if inc.status != "resolved"
                ],
            },
        }
        incident_context_block ={
            "type": "context",
            "block_id": "incident_bot_pager_incident_select_context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "Choose among ongoing open incidents to escalate using PagerDuty."
                }
            ]
        }
        incident_auto_choose_block = {
            "type": "section",
            "block_id": "incident_bot_pager_incident_auto_select",
            "text": {
                "type": "mrkdwn",
                "text": "*Specify the Incident to Escalate?*"
            },
            "accessory": {
                "action_id": "incident_bot_pager_incident_auto_select_shortcut",
                "type": "conversations_select",
                "default_to_current_conversation": True,
                "placeholder": {
                    "type": "plain_text",
                    "text": "Incident..."
                }
            }
        }
        blocks.append(incident_auto_choose_block)
        blocks.append(incident_context_block)
        response = client.views_open(
        # Pass a valid trigger_id within 3 seconds of receiving it
        trigger_id=body["trigger_id"],
        # View payload
        view={
            "type": "modal",
            "callback_id": "incident_bot_pager_modal",
            "title": {
                "type": "plain_text",
                "text": "Escalate",
            },
            "blocks": blocks
            if "pagerduty" in config.active.integrations
            else [
                {
                    "type": "section",
                    "block_id": "incident_bot_pager_disabled",
                    "text": {
                        "type": "mrkdwn",
                        "text": "The PagerDuty integration is not currently enabled.",
                    },
                },
            ],
        },
        )
        response_state = parse_modal_values(response)
        auto_select_current_channel_id = response_state['incident_bot_pager_incident_auto_select_shortcut']
        index = tools.find_index_in_obj_list(database_data,"channel_id",auto_select_current_channel_id)
        if index != -1:
            auto_select_current_channel= database_data[index].channel_name
            incident_choose_block["accessory"]["initial_option"] = {
                "text": {
                    "type": "plain_text",
                    "text": f"#{auto_select_current_channel}",
                },
                "value": f"{auto_select_current_channel}/{auto_select_current_channel_id}",
            }
        blocks.pop()
        blocks.pop()
        blocks.append(incident_choose_block)
        blocks.append(incident_context_block)
        client.views_update(view_id=response["view"]["id"],hash=response["view"]["hash"],view={
            "type": "modal",
            "callback_id": "incident_bot_pager_modal",
            "title": {
                "type": "plain_text",
                "text": "Escalate",
            },
            "blocks": blocks
            if "pagerduty" in config.active.integrations
            else [
                {
                    "type": "section",
                    "block_id": "incident_bot_pager_disabled",
                    "text": {
                        "type": "mrkdwn",
                        "text": "The PagerDuty integration is not currently enabled.",
                    },
                },
            ],
        })



@app.action("update_incident_bot_pager_selected_incident")
def update_modal_update_incident_bot_pager_selected_incident(ack, body, client):
    # Acknowledge the button request
    ack()

    parsed = parse_modal_values(body)
    incident = parsed.get("update_incident_bot_pager_selected_incident")
    incident_channel_name = incident.split("/")[0]
    incident_channel_id = incident.split("/")[1]
    priority = parsed.get("update_incident_bot_pager_selected_priority")
    team = parsed.get("update_incident_bot_pager_selected_team")
    service = parsed.get("update_incident_bot_pager_selected_service")

    # Call views_update with the built-in client
    client.views_update(
        # Pass the view_id
        view_id=body["view"]["id"],
        # String that represents view state to protect against race conditions
        hash=body["view"]["hash"],
        # View payload with updated blocks
        view={
            "type": "modal",
            "callback_id": "incident_bot_pager_modal",
            "title": {
                "type": "plain_text",
                "text": "Escalate",
            },
            "submit": {"type": "plain_text", "text": "Page"},
            "blocks": [
                {
                    "type": "section",
                    "block_id": "incident_bot_pager_info",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*You have selected the following options - please review them carefully.*\n\n"
                        + "After clicking Submit, an incident will be created in PagerDuty for the service and team listed here ,They will be paged. "
                        + "and also invited to the below incident's Slack channel.",
                    },
                },
                {"type": "divider"},
                {
                    "type": "section",
                    "block_id": f"service/{service}",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Service:* _{service}_",
                    },
                },
                {
                    "type": "section",
                    "block_id": f"team/{team}",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Team:* _{team}_",
                    },
                },
                {
                    "type": "section",
                    "block_id": f"priority/{priority}",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Urgency:* _{priority}_",
                    },
                },
                {
                    "type": "section",
                    "block_id": f"incident/{incident_channel_name}/{incident_channel_id}",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Incident:* _{incident_channel_name}_",
                    },
                },
            ],
        },
    )


@app.action("update_incident_bot_pager_selected_team")
def handle_static_action(ack, body, logger):
    ack()
    logger.debug(body)


@app.action("update_incident_bot_pager_selected_service")
def handle_static_action(ack, body, logger,client):
    ack()
    from bot.pagerduty import api as pd_api
    update_view = body["view"]["blocks"]
    selected_service_name = body["actions"][0]["selected_option"]["value"]
    service_esp = pd_api.find_services().get(selected_service_name, {}).get("escalation_policy_name", "No Escalation Policy")
    # default_escalation_policy = pd_api.find_who_is_on_call().get(service_esp,{})
    random_number = random.randint(1, 100)
    block_id = f"incident_bot_pager_team_select_{random_number}"
    # handling update in state issue https://github.com/slackapi/bolt-js/issues/1073#issuecomment-903599111
    update_block = {
            "type": "section",
            "block_id": block_id,
            "text": {
                "type": "mrkdwn",
                "text": "*Which team do you need to page?*",
            },
            "accessory": {
                "action_id": "update_incident_bot_pager_selected_team",
                "type": "static_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Team...",
                    "emoji": True
                },
                "options": [
                    {
                        "text": {
                            "type": "plain_text",
                            "text": ep,
                        },
                        "value": ep,
                    }
                    for ep in pd_api.find_who_is_on_call()
                ],
                "initial_option": {
                    "text": {
                        "type": "plain_text",
                        "text": service_esp,
                        "emoji": True,
                    },
                    "value": service_esp,
                },
            },
        }
    for i, block in enumerate(update_view):
        if block.get("block_id", "").startswith("incident_bot_pager_team_select") and block.get("type") == "section":
            update_view[i] = update_block
            break

    client.views_update(
        # Pass the view_id
        view_id=body["view"]["id"],
        trigger_id=body["trigger_id"],
        # String that represents view state to protect against race conditions
        hash=body["view"]["hash"],
        view = {
            "type" : body["view"]["type"],
            "title" : body["view"]["title"],
            "callback_id" : body["view"]["callback_id"],
            "blocks" : body["view"]["blocks"],
        }
    )
    logger.debug(body)

@app.action("update_incident_bot_pager_selected_priority")
def handle_static_action(ack, body, logger,client):

    try:
        selected_incident = body["view"]["state"]["values"]["incident_bot_pager_incident_select"]["update_incident_bot_pager_selected_incident"]["selected_option"]
        if selected_incident != None:
            ack()
            time.sleep(3)
            update_modal_update_incident_bot_pager_selected_incident(ack, body, client)
        else:
            ack()
            logger.debug(body)
    except:
        ack()
        logger.debug(body)

@app.view("incident_bot_pager_modal")
def handle_submission(ack, body, say, view):
    """
    Handles open_incident_bot_pager
    """
    ack()
    from bot.pagerduty import api as pd_api
    for block in view["blocks"]:
        if block.get("block_id", "").startswith("team") and block.get("type") == "section":
            team = block["block_id"].split("/")[1]
        elif block.get("block_id", "").startswith("service") and block.get("type") == "section":
            service = block["block_id"].split("/")[1]
        elif block.get("block_id", "").startswith("priority") and block.get("type") == "section":
            priority = block["block_id"].split("/")[1]
        elif block.get("block_id", "").startswith("incident/") and block.get("type") == "section":
            incident_channel_name = block["block_id"].split("/")[1]
            incident_channel_id = block["block_id"].split("/")[2]
    paging_user = body["user"]["name"]

    try:
        pd_api.page(
            ep_name=team,
            priority=priority,
            channel_name=incident_channel_name,
            channel_id=incident_channel_id,
            paging_user=paging_user,
        )
        msg = f"*NOTICE:* I have paged the team/escalation policy *{team}* for the service *{service}* to respond to this incident via PagerDuty at the request of *{paging_user}*."
    except Exception as error:
        msg = f"Looks like I encountered an error issuing that page: {error}"
    finally:
        say(
            channel=incident_channel_id,
            text=f"*NOTICE:* I have paged the team/escalation policy *{team}* for the service *{service}* "
            + f"to respond to this incident via PagerDuty at the request of *{paging_user}*.",
            blocks=[
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f":robot_face: PagerDuty Page Notification",
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": msg,
                    },
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "image",
                            "image_url": "https://i.imgur.com/IVvdFCV.png",
                            "alt_text": "pagerduty",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"This PagerDuty action was attempted at: {tools.fetch_timestamp()}",
                        },
                    ],
                },
            ],
        )


"""
Timeline
"""


@app.action("open_incident_bot_timeline")
@app.shortcut("open_incident_bot_timeline")
def open_modal(ack, body, client):
    # Acknowledge the command request
    ack()

    # Handle Message Shortcut Directly 
    if body.get("channel") != None and body.get("message") != None:
        incident_channel_id = body.get("channel").get("id")
        incident_channel_name = body.get("channel").get("name") 
        incident_channel_name_id = f"{incident_channel_name}/{incident_channel_id}"
        handle_open_incident_bot_timeline_message_shortcut(ack,body,client,incident_channel_name_id)
        return
        
    
    # Format incident list
    database_data = db_read_open_incidents_sorted(return_json=False, order_aesc=False)

    response = open_incident_bot_timeline_auto_select_incident(ack,body,client,database_data)
    response_state = parse_modal_values(response)
    auto_select_current_channel_id = response_state['update_incident_bot_timeline_auto_selected_incident']
    index = tools.find_index_in_obj_list(database_data,"channel_id",auto_select_current_channel_id)
    response_update = client.views_update(view_id=response["view"]["id"],hash=response["view"]["hash"],view={
        "type": "modal",
        "callback_id": "incident_bot_timeline_modal",
        "title": {"type": "plain_text", "text": "Incident timeline"},
        "submit": {"type": "plain_text", "text": "Update"},
        "blocks": [
            {
                "type": "section",
                "block_id": "incident_bot_timeline_incident_select",
                "text": {
                    "type": "mrkdwn",
                    "text": "Choose an incident to add an event to:",
                },
                "accessory": {
                    "action_id": "update_incident_bot_timeline_selected_incident",
                    "type": "static_select",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Incident...",
                    },
                    "options": [
                        {
                            "text": {
                                "type": "plain_text",
                                "text": inc.channel_name,
                                "emoji": True,
                            },
                            "value": f"{inc.channel_name}/{inc.channel_id}",
                        }
                        for inc in database_data
                        if inc.status != "resolved"
                    ],
                    "initial_option": {
                        "text": {
                            "type": "plain_text",
                            "text": f"{database_data[index].channel_name}",
                            "emoji": True,
                        },
                        "value": f"{database_data[index].channel_name}/{database_data[index].channel_id}",
                    } if index != -1
                    else {
                        "text": {
                            "type": "plain_text",
                            "text": f"{database_data[0].channel_name}",
                            "emoji": True,
                        },
                        "value": f"{database_data[0].channel_name}/{database_data[0].channel_id}",
                    }
                },
            }
            if len(database_data) != 0
            else {
                "type": "section",
                "block_id": "no_incidents",
                "text": {
                    "type": "mrkdwn",
                    "text": "There are currently no open incidents.\n\nYou can only add timeline events to open incidents.",
                },
            }
        ],
    },)

def open_incident_bot_timeline_auto_select_incident(ack,body,client,database_data):
    ack()
    response = client.views_open(
        # Pass a valid trigger_id within 3 seconds of receiving it
        trigger_id=body["trigger_id"],
        # View payload
        view={
            "type": "modal",
            "callback_id": "incident_bot_timeline_modal",
            "title": {"type": "plain_text", "text": "Incident timeline"},
            "blocks": [
                {
                    "type": "section",
                    "block_id": "incident_bot_timeline_incident_auto_select",
                    "text": {
                        "type": "mrkdwn",
                        "text": "Choose an incident to add an event to:"
                    },
                    "accessory": {
                        "action_id": "update_incident_bot_timeline_auto_selected_incident",
                        "type": "conversations_select",
                        "default_to_current_conversation": True,
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Incident..."
                        }
                    }
                }
                if len(database_data) != 0
                else {
                    "type": "section",
                    "block_id": "no_incidents",
                    "text": {
                        "type": "mrkdwn",
                        "text": "There are currently no open incidents.\n\nYou can only add timeline events to open incidents.",
                    },
                }
            ],
        },
    )
    return response


def incident_bot_timeline_selected_incident_blocks(incident: str):
    incident_channel_name = incident.split("/")[0]
    timestamp_datetime = datetime.strptime(tools.fetch_timestamp(short=True), "%d/%m/%Y %H:%M:%S %Z")
    initial_time = timestamp_datetime.strftime("%H:%M")
    current_date = timestamp_datetime.strftime("%Y-%m-%d")
    application_timezone = "Europe/London" if config.active.options.get("timezone") == "UTC" else config.active.options.get("timezone")
    current_audit_logs = read_logs(incident_channel_name)
    current_logs = sorted(current_audit_logs, key=lambda x: x['ts'])
    base_blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": incident_channel_name,
            },
        },
        {
            "type": "section",
            "block_id": "incident_bot_timeline_info",
            "text": {
                "type": "mrkdwn",
                "text": "Add a new event to the incident's timeline. This will "
                        + "be automatically added to the RCA when the incident is resolved.\n",
            },
        },
        {"type": "divider"},
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": ":page_with_curl: Existing Entries \n",
            },
        },
    ]
    for log in current_logs:
        base_blocks.extend(
            [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": log["log"],
                    },
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "plain_text",
                            "text": log["ts"],
                            "emoji": True,
                        }
                    ],
                },
                {"type": "divider"},
            ],
        )
    base_blocks.extend(
        [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": ":writing_hand: Add New",
                },
            },
            {
                "type": "input",
                "block_id": "date",
                "element": {
                    "type": "datepicker",
                    "initial_date": current_date,
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Select a date",
                        "emoji": True,
                    },
                    "action_id": "update_incident_bot_timeline_date",
                },
                "label": {"type": "plain_text", "text": "Choose Date", "emoji": True},
            },
            {
                "type": "input",
                "block_id": "time",
                "element": {
                    "type": "timepicker",
                    "timezone": application_timezone,
                    "initial_time": initial_time,
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Select time",
                        "emoji": True,
                    },
                    "action_id": "update_incident_bot_timeline_time",
                },
                "label": {"type": "plain_text", "text": "Adjust Time", "emoji": True},
            },
            {
                "type": "input",
                "block_id": "text",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "update_incident_bot_timeline_text",
                    "multiline": True,
                },
                "label": {"type": "plain_text", "text": "Text", "emoji": True},
            },
        ]
    )
    return base_blocks

@app.action("update_incident_bot_timeline_selected_incident")
def update_modal_incident_bot_timeline_selected_incident(ack, body, client):
    # Acknowledge the button request
    ack()

    parsed = parse_modal_values(body)
    incident = parsed.get("update_incident_bot_timeline_selected_incident")

    base_blocks= incident_bot_timeline_selected_incident_blocks(incident)
    # Call views_update with the built-in client
    client.views_update(
        # Pass the view_id
        view_id=body["view"]["id"],
        # String that represents view state to protect against race conditions
        hash=body["view"]["hash"],
        # View payload with updated blocks
        view={
            "type": "modal",
            "callback_id": "incident_bot_timeline_modal_add",
            "title": {"type": "plain_text", "text": "Incident timeline"},
            "submit": {"type": "plain_text", "text": "Add"},
            "blocks": base_blocks,
        },
    )


@app.action("update_incident_bot_timeline_date")
def handle_static_action(ack, body, logger):
    ack()
    logger.debug(body)


@app.action("update_incident_bot_timeline_time")
def handle_static_action(ack, body, logger):
    ack()
    logger.debug(body)


@app.action("update_incident_bot_timeline_text")
def handle_static_action(ack, body, logger):
    ack()
    logger.debug(body)


@app.view("incident_bot_timeline_modal")
def handle_submission(ack, body, client, view):
    ack()
    parsed = parse_modal_values(body)
    incident = parsed.get("update_incident_bot_timeline_selected_incident")
    base_blocks= incident_bot_timeline_selected_incident_blocks(incident)
    # Call views_update with the built-in client
    client.views_open(
        # # Pass the view_id
        trigger_id=body["trigger_id"],
        view={
            "type": "modal",
            "callback_id": "incident_bot_timeline_modal_add",
            "title": {"type": "plain_text", "text": "Incident timeline"},
            "submit": {"type": "plain_text", "text": "Add"},
            "blocks": base_blocks,
        },
    )


def handle_open_incident_bot_timeline_message_shortcut(ack,body,client,incident_channel_name_id: str):
    ack()
    base_blocks= incident_bot_timeline_selected_incident_blocks(incident_channel_name_id)
    client.views_open(
        # # Pass the view_id
        trigger_id=body["trigger_id"],
        view={
            "type": "modal",
            "callback_id": "incident_bot_timeline_modal_add",
            "title": {"type": "plain_text", "text": "Incident timeline"},
            "submit": {"type": "plain_text", "text": "Add"},
            "blocks": base_blocks,
        },
    )
    return
    

@app.view("incident_bot_timeline_modal_add")
def handle_submission(ack, body, say, view):
    """
    Handles
    """
    ack()

    parsed = parse_modal_values(body)
    incident_id = view["blocks"][0]["text"]["text"]
    event_date = parsed.get("update_incident_bot_timeline_date")
    event_time = parsed.get("update_incident_bot_timeline_time")
    event_text = parsed.get("update_incident_bot_timeline_text")
    ts = tools.fetch_timestamp_from_time_obj(
        datetime.strptime(f"{event_date} {event_time}", "%Y-%m-%d %H:%M")
    )
    try:
        write_log(
            incident_id=incident_id,
            event=event_text,
            user=body["user"]["id"],
            ts=ts,
        )
    except Exception as error:
        logger.error(error)
    finally:
        say(
            channel=db_read_incident_channel_id(incident_id=incident_id),
            text=f":wave: *I have added the following event to this incident's timeline:* {ts} - {event_text}",
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f":wave: *I have added the following event to this incident's timeline:*",
                    },
                },
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{ts} - {event_text}",
                    },
                },
            ],
        )


"""
Statuspage
"""


@app.action("open_statuspage_incident_modal")
def open_modal(ack, body, client):
    """
    Provides the modal that will display when the shortcut is used to start a Statuspage incident
    """
    user = body.get("user").get("id")
    incident_id = body.get("actions")[0].get("value").split("_")[-1:][0]
    incident_data = db_read_incident(channel_id=incident_id)
    blocks = [
        {
            "type": "image",
            "image_url": config.sp_logo_url,
            "alt_text": "statuspage",
        },
        {"type": "divider"},
        {
            "type": "section",
            "block_id": incident_id,
            "text": {
                "type": "mrkdwn",
                "text": "Incident ID: {}".format(incident_data.incident_id),
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "This Statuspage incident will start in "
                + "*investigating* mode. You may change its status as the "
                + "incident proceeds.",
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Please enter a brief description that will appear "
                + "as the incident description in the Statuspage incident. "
                + "Then select impacted components and confirm. Once "
                + "confirmed, the incident will be opened.",
            },
        },
        {"type": "divider"},
        {
            "type": "input",
            "block_id": "statuspage_name_input",
            "element": {
                "type": "plain_text_input",
                "action_id": "statuspage.name_input",
                "min_length": 1,
            },
            "label": {
                "type": "plain_text",
                "text": "Name for the incident",
                "emoji": True,
            },
        },
        {
            "type": "input",
            "block_id": "statuspage_body_input",
            "element": {
                "type": "plain_text_input",
                "action_id": "statuspage.body_input",
                "min_length": 1,
            },
            "label": {
                "type": "plain_text",
                "text": "Message describing the incident",
                "emoji": True,
            },
        },
        {
            "block_id": "statuspage_impact_select",
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*Impact:*"},
            "accessory": {
                "type": "static_select",
                "action_id": "statuspage.impact_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select an impact...",
                    "emoji": True,
                },
                "options": [
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Minor",
                            "emoji": True,
                        },
                        "value": "minor",
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Major",
                            "emoji": True,
                        },
                        "value": "major",
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Critical",
                            "emoji": True,
                        },
                        "value": "critical",
                    },
                ],
            },
        },
        {
            "block_id": "statuspage_components_status",
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*Components Impact:*"},
            "accessory": {
                "type": "static_select",
                "action_id": "statuspage.components_status_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select status of components...",
                    "emoji": True,
                },
                "options": [
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Degraded Performance",
                            "emoji": True,
                        },
                        "value": "degraded_performance",
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Partial Outage",
                            "emoji": True,
                        },
                        "value": "partial_outage",
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Major Outage",
                            "emoji": True,
                        },
                        "value": "major_outage",
                    },
                ],
            },
        },
        {
            "type": "section",
            "block_id": "statuspage_components_select",
            "text": {
                "type": "mrkdwn",
                "text": "Select impacted components",
            },
            "accessory": {
                "action_id": "statuspage.components_select",
                "type": "multi_static_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select components",
                },
                "options": [
                    {
                        "text": {
                            "type": "plain_text",
                            "text": c,
                        },
                        "value": c,
                    }
                    for c in StatuspageComponents().list_of_names
                ],
            },
        },
    ]

    ack()

    # Return modal only if user has permissions
    sp_config = config.active.integrations.get("statuspage")
    if sp_config.get("permissions") and sp_config.get("permissions").get("groups"):
        for gr in sp_config.get("permissions").get("groups"):
            if check_user_in_group(user_id=user, group_name=gr):
                client.views_open(
                    trigger_id=body["trigger_id"],
                    view={
                        "type": "modal",
                        # View identifier
                        "callback_id": "open_statuspage_incident_modal",
                        "title": {
                            "type": "plain_text",
                            "text": "Statuspage Incident",
                        },
                        "submit": {"type": "plain_text", "text": "Start"},
                        "blocks": blocks,
                    },
                )
            else:
                client.chat_postEphemeral(
                    channel=incident_id,
                    user=user,
                    text="You don't have permissions to manage Statuspage incidents.",
                )
    else:
        client.views_open(
            trigger_id=body["trigger_id"],
            view={
                "type": "modal",
                # View identifier
                "callback_id": "open_statuspage_incident_modal",
                "title": {
                    "type": "plain_text",
                    "text": "Statuspage Incident",
                },
                "submit": {"type": "plain_text", "text": "Start"},
                "blocks": blocks,
            },
        )


@app.view("open_statuspage_incident_modal")
def handle_submission(ack, body, client, view):
    """
    Handles open_statuspage_incident_modal
    """
    ack()
    incident_data = db_read_incident(channel_id=view["blocks"][2].get("block_id"))

    # Fetch parameters from modal
    parsed = parse_modal_values(body)
    body = parsed.get("statuspage.body_input")
    impact = parsed.get("statuspage.impact_select")
    name = parsed.get("statuspage.name_input")
    status = parsed.get("statuspage.components_status_select")
    selected_components = parsed.get("statuspage.components_select")

    # Create Statuspage incident
    try:
        StatuspageIncident(
            channel_id=incident_data.channel_id,
            request_data={
                "name": name,
                "status": "investigating",
                "body": body,
                "impact": impact,
                "components": StatuspageComponents().formatted_components_update(
                    selected_components, status
                ),
            },
        )
    except Exception as error:
        logger.error(f"Error creating Statuspage incident: {error}")

    client.chat_update(
        channel=incident_data.channel_id,
        ts=incident_data.sp_message_ts,
        text="Statuspage incident has been created.",
        blocks=StatuspageIncidentUpdate.update_management_message(
            incident_data.channel_id
        ),
    )


@app.action("open_statuspage_incident_update_modal")
def open_modal(ack, body, client):
    """
    Provides the modal that will display when the shortcut is used to update a Statuspage incident
    """
    user = body.get("user").get("id")
    incident_id = body.get("channel").get("id")
    incident_data = db_read_incident(channel_id=incident_id)
    sp_incident_data = incident_data.sp_incident_data
    blocks = [
        {"type": "divider"},
        {
            "type": "image",
            "image_url": config.sp_logo_url,
            "alt_text": "statuspage",
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Name*: {}\n*Status*: {}\nLast Updated: {}\n".format(
                    sp_incident_data.get("name"),
                    sp_incident_data.get("status"),
                    sp_incident_data.get("updated_at"),
                ),
            },
        },
        {"type": "divider"},
        {
            "type": "input",
            "block_id": f"statuspage_update_message_input_{incident_id}",
            "element": {
                "type": "plain_text_input",
                "action_id": "statuspage.update_message_input",
                "min_length": 1,
            },
            "label": {
                "type": "plain_text",
                "text": "Message to include with this update",
                "emoji": True,
            },
        },
        {
            "block_id": "statuspage_incident_status_management",
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*Update Status:*"},
            "accessory": {
                "type": "static_select",
                "action_id": "statuspage.update_status",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Investigating",
                    "emoji": True,
                },
                "options": [
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Investigating",
                            "emoji": True,
                        },
                        "value": "investigating",
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Identified",
                            "emoji": True,
                        },
                        "value": "identified",
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Monitoring",
                            "emoji": True,
                        },
                        "value": "monitoring",
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Resolved",
                            "emoji": True,
                        },
                        "value": "resolved",
                    },
                ],
            },
        },
    ]

    ack()

    # Return modal only if user has permissions
    sp_config = config.active.integrations.get("statuspage")
    if sp_config.get("permissions") and sp_config.get("permissions").get("groups"):
        for gr in sp_config.get("permissions").get("groups"):
            if check_user_in_group(user_id=user, group_name=gr):
                client.views_open(
                    trigger_id=body["trigger_id"],
                    view={
                        "type": "modal",
                        # View identifier
                        "callback_id": "open_statuspage_incident_update_modal",
                        "title": {
                            "type": "plain_text",
                            "text": "Update Incident",
                        },
                        "submit": {"type": "plain_text", "text": "Update"},
                        "blocks": blocks,
                    },
                )
            else:
                client.chat_postEphemeral(
                    channel=incident_id,
                    user=user,
                    text="You don't have permissions to manage Statuspage incidents.",
                )
    else:
        client.views_open(
            trigger_id=body["trigger_id"],
            view={
                "type": "modal",
                # View identifier
                "callback_id": "open_statuspage_incident_update_modal",
                "title": {
                    "type": "plain_text",
                    "text": "Update Incident",
                },
                "submit": {"type": "plain_text", "text": "Update"},
                "blocks": blocks,
            },
        )


@app.view("open_statuspage_incident_update_modal")
def handle_submission(ack, body):
    """
    Handles open_statuspage_incident_update_modal
    """
    ack()

    channel_id = body.get("view").get("blocks")[4].get("block_id").split("_")[-1:][0]
    values = body.get("view").get("state").get("values")
    update_message = (
        values.get(f"statuspage_update_message_input_{channel_id}")
        .get("statuspage.update_message_input")
        .get("value")
    )
    update_status = (
        values.get("statuspage_incident_status_management")
        .get("statuspage.update_status")
        .get("selected_option")
        .get("value")
    )

    try:
        StatuspageIncidentUpdate().update(channel_id, update_status, update_message)
    except Exception as error:
        logger.error(f"Error updating Statuspage incident: {error}")


"""
Jira
"""


@app.action("open_incident_create_jira_issue_modal")
def open_modal(ack, body, client):
    """
    Provides the modal that will display when the shortcut is used to create a Jira issue
    """
    incident_id = body.get("channel").get("id")
    blocks = [
        {
            "type": "header",
            "block_id": incident_id,
            "text": {
                "type": "plain_text",
                "text": "Create a Jira Issue",
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "This issue will be created in the project: *{}*".format(
                    config.active.integrations.get("atlassian")
                    .get("jira")
                    .get("project")
                ),
            },
        },
        {"type": "divider"},
        {
            "type": "input",
            "block_id": "jira_issue_summary_input",
            "element": {
                "type": "plain_text_input",
                "action_id": "jira.summary_input",
                "min_length": 1,
            },
            "label": {
                "type": "plain_text",
                "text": "Issue Summary",
                "emoji": True,
            },
        },
        {
            "type": "input",
            "block_id": "jira_issue_description_input",
            "element": {
                "type": "plain_text_input",
                "action_id": "jira.description_input",
                "min_length": 1,
                "multiline": True,
            },
            "label": {
                "type": "plain_text",
                "text": "Issue Description",
                "emoji": True,
            },
        },
        {
            "block_id": "jira_issue_type_select",
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*Issue Type:*"},
            "accessory": {
                "type": "static_select",
                "action_id": "jira.type_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Task",
                    "emoji": True,
                },
                "initial_option": {
                    "text": {
                        "type": "plain_text",
                        "text": "Task",
                    },
                    "value": "Task",
                },
                "options": [
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Epic",
                            "emoji": True,
                        },
                        "value": "Epic",
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Story",
                            "emoji": True,
                        },
                        "value": "Story",
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Task",
                            "emoji": True,
                        },
                        "value": "Task",
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Bug",
                            "emoji": True,
                        },
                        "value": "Bug",
                    },
                ],
            },
        },
        {
            "block_id": "jira_issue_priority_select",
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*Priority:*"},
            "accessory": {
                "type": "static_select",
                "action_id": "jira.priority_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "low",
                    "emoji": True,
                },
                "initial_option": {
                    "text": {
                        "type": "plain_text",
                        "text": "low",
                    },
                    "value": "low",
                },
                "options": [
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "low",
                            "emoji": True,
                        },
                        "value": "low",
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "medium",
                            "emoji": True,
                        },
                        "value": "medium",
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "high",
                            "emoji": True,
                        },
                        "value": "high",
                    },
                ],
            },
        },
    ]

    ack()
    client.views_open(
        trigger_id=body["trigger_id"],
        view={
            "type": "modal",
            # View identifier
            "callback_id": "open_incident_create_jira_issue_modal",
            "title": {
                "type": "plain_text",
                "text": "Jira Issue",
            },
            "submit": {"type": "plain_text", "text": "Create"},
            "blocks": blocks,
        },
    )


@app.view("open_incident_create_jira_issue_modal")
def handle_submission(ack, body, client, view):
    """
    Handles open_incident_create_jira_issue_modal
    """
    ack()
    channel_id = body.get("view").get("blocks")[0].get("block_id")

    parsed = parse_modal_values(body)
    try:
        incident_data = db_read_incident(channel_id=channel_id)
        resp = JiraIssue(
            incident_id=incident_data.incident_id,
            description=parsed.get("jira.description_input"),
            issue_type=parsed.get("jira.type_select"),
            priority=parsed.get("jira.priority_select"),
            summary=parsed.get("jira.summary_input"),
        ).new()
        issue_link = "{}/browse/{}".format(config.atlassian_api_url, resp.get("key"))
        db_update_jira_issues_col(channel_id=channel_id, issue_link=issue_link)
        try:
            resp = client.chat_postMessage(
                channel=channel_id,
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "A Jira issue has been created for this incident.",
                        },
                    },
                    {"type": "divider"},
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": "*Key:* {}".format(resp.get("key")),
                            },
                            {
                                "type": "mrkdwn",
                                "text": "*Summary:* {}".format(
                                    parsed.get("jira.summary_input")
                                ),
                            },
                            {
                                "type": "mrkdwn",
                                "text": "*Priority:* {}".format(
                                    parsed.get("jira.priority_select")
                                ),
                            },
                            {
                                "type": "mrkdwn",
                                "text": "*Type:* {}".format(
                                    parsed.get("jira.type_select")
                                ),
                            },
                        ],
                    },
                    {
                        "type": "actions",
                        "block_id": "jira_view_issue",
                        "elements": [
                            {
                                "type": "button",
                                "action_id": "jira.view_issue",
                                "style": "primary",
                                "text": {
                                    "type": "plain_text",
                                    "text": "View Issue",
                                },
                                "url": issue_link,
                            },
                        ],
                    },
                ],
                text="A Jira issue has been created for this incident: {}".format(
                    resp.get("self")
                ),
            )
            client.pins_add(
                channel=resp.get("channel"),
                timestamp=resp.get("ts"),
            )
        except Exception as error:
            logger.error(f"Error sending Jira issue message for {incident_data.incident_id}: {error}")
    except Exception as error:
        logger.error(error)

def get_severity_context():
    text_lines = []
    for sev, _ in config.active.severities.items():
        if sev.upper() == "SEV1":
            text_lines.append(f"*SEV1:* This incident is critical and requires immediate attention.")
        elif sev.upper() == "SEV2":
            text_lines.append(f"*SEV2:* This incident is urgent and should be addressed promptly.")
        elif sev.upper() == "SEV3":
            text_lines.append(f"*SEV3:* This incident has a moderate impact and should be resolved soon.")
        elif sev.upper() == "SEV4":
            text_lines.append(f"*SEV4:* This incident has a low impact and can be resolved at a convenient time.")
    return "\n".join(text_lines)

