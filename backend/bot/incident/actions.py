import config
import logging
import slack_sdk.errors
import variables
import asyncio

from bot.audit import log
from bot.exc import IndexNotFoundError
from bot.incident.action_parameters import (
    ActionParametersSlack,
    ActionParametersWeb,
)
from bot.models.incident import (
    db_read_incident,
    db_update_incident_rca_col,
    db_update_incident_role,
    db_update_incident_status_col,
    db_update_incident_severity_col,
    db_update_incident_updated_at_col,
    db_update_jira_issues_col,
    db_update_rca_channel_id,
)
from bot.scheduler import scheduler
from bot.shared import tools
from bot.slack.client import (
    slack_web_client,
    get_formatted_channel_history,
    get_message_content,
    invite_user_to_channel,
    slack_workspace_id,
)
from bot.chatgpt.api import ChatGPTApi
from bot.jira.issue import JiraIssue

from bot.slack.incident_logging import read as read_incident_pinned_items
from bot.templates.incident.digest_notification import (
    IncidentChannelDigestNotification,
)
from bot.templates.incident.resolution_message import IncidentResolutionMessage
from bot.templates.incident.updates import IncidentUpdate
from bot.templates.incident.user_dm import IncidentUserNotification
from bot.templates.incident.private_message import PrivateMessage

from typing import Any, Dict, List
import re
import random

logger = logging.getLogger("incident.actions")


"""
Functions for handling inbound actions
"""


async def archive_incident_channel(
    action_parameters: type[ActionParametersSlack],
):
    """When an incoming action is incident.archive_incident_channel, this method
    archives the target channel.

    Keyword arguments:
    action_parameters -- type[ActionParametersSlack] containing Slack actions data
    """
    incident_data = db_read_incident(
        channel_id=action_parameters.channel_details.get("id")
    )
    try:
        logger.info(f"Archiving {incident_data.channel_name}.")
        result = slack_web_client.conversations_archive(
            channel=incident_data.channel_id
        )
        logger.debug(f"\n{result}\n")
    except slack_sdk.errors.SlackApiError as error:
        logger.error(f"Error archiving {incident_data.channel_name}: {error}")
    finally:
        # Write audit log
        log.write(
            incident_id=incident_data.channel_name,
            event="Channel archived.",
        )


async def assign_role(
    action_parameters: type[ActionParametersSlack] = ActionParametersSlack,
    web_data: type[ActionParametersWeb] = ActionParametersWeb,
    request_origin: str = "slack",
):
    """When an incoming action is incident.assign_role, this method
    assigns the role to the user provided in the input

    Keyword arguments:
    action_parameters(type[ActionParametersSlack]) containing Slack actions data
    web_data(Dict) - if executing from "web", this data must be passed
    request_origin(str) - can either be "slack" or "web"
    """
    match request_origin:
        case "slack":
            try:
                incident_data = db_read_incident(
                    channel_id=action_parameters.channel_details.get("id")
                )
                # Target incident channel
                target_channel = incident_data.channel_id
                channel_name = incident_data.channel_name
                user_id = action_parameters.actions.get("selected_user")
                action_value = "_".join(
                    action_parameters.actions.get("block_id").split("_")[3:]
                )
                last_underscore_index = action_value.rfind('_')
                if last_underscore_index != -1 and last_underscore_index < len(action_value) - 1 and action_value[last_underscore_index + 1:].isdigit():
                    action_value = action_value[:last_underscore_index]
                else:
                    action_value = action_value
                # Find the index of the block that contains info on
                # the role we want to update and format it with the new user later
                blocks = action_parameters.message_details.get("blocks")
                index = tools.find_index_in_list(
                    blocks, "block_id", f"role_{action_value}"
                )
                if index == -1:
                    raise IndexNotFoundError(
                        f"Could not find index for block_id role_{action_value}"
                    )
                temp_new_role_name = action_value.replace("_", " ")
                target_role = action_value
                ts = action_parameters.message_details.get("ts")
            except Exception as error:
                logger.error(
                    f"Error processing incident user update from Slack: {error}"
                )
        case "web":
            try:
                incident_data = db_read_incident(channel_id=web_data.channel_id)
                # Target incident channel
                target_channel = incident_data.channel_id
                channel_name = incident_data.channel_name
                user_id = web_data.user
                # Find the index of the block that contains info on
                # the role we want to update and format it with the new user later
                blocks = get_message_content(
                    conversation_id=web_data.channel_id,
                    ts=web_data.bp_message_ts,
                ).get("blocks")
                index = tools.find_index_in_list(
                    blocks, "block_id", f"role_{web_data.role}"
                )
                if index == -1:
                    raise IndexNotFoundError(
                        f"Could not find index for block_id role_{web_data.role}"
                    )
                temp_new_role_name = web_data.role.replace("_", " ")
                target_role = web_data.role
                ts = web_data.bp_message_ts
            except Exception as error:
                logger.error(f"Error processing incident user update from web: {error}")

    new_role_name = temp_new_role_name.title()
    blocks[index]["text"]["text"] = f"*{new_role_name}*: <@{user_id}>"
    # Convert user ID to user name to use later.
    user_name = next(
        (
            u["name"]
            for u in slack_web_client.users_list()["members"]
            if u["id"] == user_id
        ),
        None,
    )

    try:
        # Update the message
        slack_web_client.chat_update(
            channel=target_channel,
            ts=ts,
            blocks=blocks,
            text=f"<@{user_id}> is now {new_role_name}",
        )
    except Exception as error:
        logger.error(f"Error updating channel message during user update: {error}")

    # Send update notification message to incident channel
    try:
        result = slack_web_client.chat_postMessage(
            **IncidentUpdate.role(
                channel=target_channel, role=new_role_name, user=user_id
            ),
            text=f"<@{user_id}> is now {new_role_name}",
        )

        logger.debug(f"\n{result}\n")
    except slack_sdk.errors.SlackApiError as error:
        logger.error(f"Error sending role update to the incident channel: {error}")
    # Let the user know they've been assigned the role and what to do
    try:
        result = slack_web_client.chat_postMessage(
            **IncidentUserNotification.create(
                user=user_id, role=target_role, channel=target_channel
            ),
            text=f" <@{user_id}> have been assigned {new_role_name} for incident <#{target_channel}>",
        )
        logger.debug(f"\n{result}\n")
    except slack_sdk.errors.SlackApiError as error:
        logger.error(f"Error sending role description to user: {error}")
    logger.info(f"{user_name} was assigned {target_role} in {channel_name}")

    # Since the user was assigned the role, they should be auto invited.
    invite_user_to_channel(target_channel, user_id)

    # Send private message int the dedicated incident channel to the Incident commander to guide what next steps to follow
    try:
        result = slack_web_client.chat_postEphemeral(
            **PrivateMessage.message(
                channel=target_channel, role=target_role, user=user_id
            ),
            text=f"Please asses the impact and communicate status. This helps everyone stay up to date with the incident",
        )
        logger.debug(f"\n{result}\n")
    except slack_sdk.errors.SlackApiError as error:
        logger.error(f"Error sending private message to incident channel: {error}")

    # Update the row to indicate who owns the role.
    db_update_incident_role(channel_id=target_channel, role=target_role, user=user_name)

    # Write audit log
    log.write(
        incident_id=channel_name,
        event=f"User {user_name} was assigned role {target_role}.",
    )
    # Finally, updated the updated_at column
    db_update_incident_updated_at_col(
        channel_id=target_channel,
        updated_at=tools.fetch_timestamp(),
    )


async def claim_role(action_parameters: type[ActionParametersSlack]):
    """When an incoming action is incident.claim_role, this method
    assigns the role to the user that hit the claim button

    Keyword arguments:
    action_parameters -- type[ActionParametersSlack] containing Slack actions data
    """
    incident_data = db_read_incident(channel_id=action_parameters.channel_details["id"])
    action_value = action_parameters.actions["value"]
    # Find the index of the block that contains info on
    # the role we want to update
    blocks = action_parameters.message_details["blocks"]
    index = tools.find_index_in_list(blocks, "block_id", f"role_{action_value}")
    if index == -1:
        raise IndexNotFoundError(
            f"Could not find index for block_id role_{action_value}"
        )
    # Replace the "_none_" value in the given block
    temp_new_role_name = action_value.replace("_", " ")
    new_role_name = temp_new_role_name.title()
    user = action_parameters.user_details["name"]
    blocks[index]["text"]["text"] = f"*{new_role_name}*: <@{user}>"
    # Update the message
    
    # Update the Auto Selected user in choose role

    # index = tools.find_index_in_list(blocks, "block_id", f"claim_assign_engineer_{action_value}")
    pattern = re.compile(f"^claim_assign_engineer_{re.escape(action_value)}")
    index = next((i for i, block in enumerate(blocks) if pattern.match(block.get("block_id", ""))), -1)
    if index == -1:
        raise IndexNotFoundError(
            f"Could not find index for block_id role_{action_value}"
        )
    user_id = action_parameters.user_details["id"]
    random_number = random.randint(1, 100)
    blocks[index]['block_id'] = f"claim_assign_engineer_{action_value}_{random_number}"

    blocks[index]['elements'][1] = {
        "type": "users_select",
        "action_id": "incident.assign_role",
        "placeholder": {
            "type": "plain_text",
            "text": f"Assign a role {action_value} ..."
        },
        "initial_user": f"{user_id}"
    }
    slack_web_client.chat_update(
        channel=incident_data.channel_id,
        ts=action_parameters.message_details["ts"],
        blocks=blocks,
    )
    # Send update notification message to incident channel
    try:
        result = slack_web_client.chat_postMessage(
            **IncidentUpdate.role(
                channel=incident_data.channel_id, role=new_role_name, user=user
            ),
            text=f"<@{user_id}> has been assigned {new_role_name} for incident <#{incident_data.channel_id}>",
        )
        logger.debug(f"\n{result}\n")
    except slack_sdk.errors.SlackApiError as error:
        logger.error(f"Error sending role update to incident channel: {error}")
    # Send private message int the dedicated incident channel to the Incident commander to guide what next steps to follow
    try:
        result = slack_web_client.chat_postEphemeral(
            **PrivateMessage.message(
                channel=incident_data.channel_id, role=action_value, user=user_id
            ),
            text=f"Please asses the impact and communicate status. This helps everyone stay up to date with the incident",
        )
        logger.debug(f"\n{result}\n")
    except slack_sdk.errors.SlackApiError as error:
        logger.error(f"Error sending private message to incident channel: {error}")
    # Let the user know they've been assigned the role and what to do
    try:
        result = slack_web_client.chat_postMessage(
            **IncidentUserNotification.create(
                user=action_parameters.user_details["id"],
                role=action_value,
                channel=incident_data.channel_id,
            ),
            text=f"You have been assigned the role {action_value} for incident {incident_data.channel_name}.",
        )
        logger.debug(f"\n{result}\n")
    except slack_sdk.errors.SlackApiError as error:
        logger.error(f"Error sending role description to user: {error}")
    logger.info(f"{user} has claimed {action_value} in {incident_data.channel_name}")
    # Update the row to indicate who owns the role.
    db_update_incident_role(
        channel_id=incident_data.channel_id, role=action_value, user=user
    )

    # Write audit log
    log.write(
        incident_id=incident_data.channel_id,
        event=f"User {user} claimed role {action_value}.",
    )
    # Finally, updated the updated_at column
    db_update_incident_updated_at_col(
        channel_id=incident_data.channel_id,
        updated_at=tools.fetch_timestamp(),
    )


async def export_chat_logs(action_parameters: type[ActionParametersSlack]):
    """When an incoming action is incident.export_chat_logs, this method
    fetches channel history, formats it, and returns it to the channel

    Keyword arguments:
    action_parameters -- type[ActionParametersSlack] containing Slack actions data
    """
    incident_data = db_read_incident(channel_id=action_parameters.channel_details["id"])
    # Retrieve channel history and post as text attachment
    history = get_formatted_channel_history(
        channel_id=incident_data.channel_id,
        channel_name=incident_data.channel_name,
    )

    try:
        logger.info(f"Sending chat transcript to {incident_data.channel_name}.")
        result = slack_web_client.files_upload_v2(
            channels=incident_data.channel_id,
            content=history,
            filename=f"{incident_data.channel_name} Chat Transcript",
            filetype="txt",
            initial_comment="As requested, here is the chat transcript. Remember"
            + " - while this is useful, it will likely need cultivation before "
            + "being added to a postmortem.",
            title=f"{incident_data.channel_name} Chat Transcript",
        )
        logger.debug(f"\n{result}\n")
    except slack_sdk.errors.SlackApiError as error:
        logger.error(
            f"Error sending message and attachment to {incident_data.channel_name}: {error}"
        )
    finally:
        # Write audit log
        log.write(
            incident_id=incident_data.channel_name,
            event=f"Incident chat log was exported by {action_parameters.user_details}.",
        )


async def set_status(
    action_parameters: type[ActionParametersSlack] = ActionParametersSlack,
):
    """When an incoming action is incident.set_status, this method
    updates the status of the incident

    Keyword arguments:
    action_parameters(type[ActionParametersSlack]) containing Slack actions data
    """
    incident_data = db_read_incident(channel_id=action_parameters.channel_details["id"])
    incident_details_info = {"incident_data": incident_data}
    channel_name = incident_data.channel_name
    is_private_incident = action_parameters.channel_details.get("name",channel_name) != channel_name
    action_value = action_parameters.actions["selected_option"]["value"]
    user = action_parameters.user_details["id"]
    reporter = incident_data.roles['incident_reporter'] if incident_data.roles and 'incident_reporter' in incident_data.roles else user

    # Write audit log
    log.write(
        incident_id=incident_data.incident_id,
        event=f"Status was changed to {action_value}.",
    )

    # If set to resolved, send additional information.
    if action_value == "resolved":
        # Set up steps for RCA channel
        message_blocks = action_parameters.message_details["blocks"]
        # Extract names of required roles
        incident_commander = extract_role_owner(
            message_blocks, "role_incident_commander"
        )
        communications_liaison = extract_role_owner(
            message_blocks, "role_communications_liaison"
        )
        # Error out if incident commander hasn't been claimed
        for role, person in {
            "incident commander": incident_commander,
        }.items():
            if person == "_none_":
                try:
                    result = slack_web_client.chat_postMessage(
                        channel=incident_data.channel_id,
                        text=f":red_circle: <@{user}> Before this incident can"
                        + f" be marked as resolved, the *{role}* role must be "
                        + "assigned. Please assign it and try again.",
                    )
                except slack_sdk.errors.SlackApiError as error:
                    logger.error(
                        f"Error sending note to {incident_data.incident_id} regarding missing role claim: {error}"
                    )
                return
        # Create rca channel
        rca_channel_name = f"{incident_data.incident_id}-rca"
        rcaChannelDetails = {
            "id": "",
            "name": rca_channel_name,
        }
        try:
            rca_channel = slack_web_client.conversations_create(name=rca_channel_name)
            # Log the result which includes information like the ID of the conversation
            logger.debug(f"\n{rca_channel_name}\n")
            logger.info(f"Creating rca channel: {rca_channel_name}")
            # Write audit log
            log.write(
                incident_id=incident_data.incident_id,
                event=f"RCA channel was created.",
                content=rca_channel["channel"]["id"],
            )
            rcaChannelDetails = {
                "id": rca_channel["channel"]["id"],
                "name": rca_channel["channel"]["name"],
            }
            db_update_rca_channel_id(rca_channel["channel"]["id"],incident_data.incident_id)
        except slack_sdk.errors.SlackApiError as error:
            if error.response['error'] == 'name_taken':
                logger.warning(f"Channel name '{rca_channel_name}' is already taken. Fetching existing channel details.")
                if incident_data.rca_channel_id:
                    rca_channel_id = incident_data.rca_channel_id
                else:
                    rca_event_log = log.read_rca_created_event_content(incident_id=incident_data.incident_id)
                    rca_channel_id = rca_event_log["rca_channel_id"]
                db_update_rca_channel_id(rca_channel_id,incident_data.incident_id)
                rcaChannelDetails = {
                    "id": rca_channel_id,
                    "name": rca_channel_name,
                }
            else:
                logger.error(f"Error creating rca channel: {error}")
        # Invite incident commander and technical lead if they weren't empty

        incident_details_info["rcaChannelDetails"] = rcaChannelDetails
        # We want real user names to tag in the rca doc
        actual_user_names = []
        for person in [incident_commander,communications_liaison,reporter]:
            if person != "_none_":
                fmt = person.replace("<", "").replace(">", "").replace("@", "")
                invite_user_to_channel(rcaChannelDetails["id"], fmt)
                # Get real name of user to be used to generate RCA
                actual_user_names.append(
                    slack_web_client.users_info(user=fmt)["user"]["profile"][
                        "real_name"
                    ]
                )
            else:
                actual_user_names.append("Unassigned")
        # Format boilerplate message to rca channel
        rca_boilerplate_message_blocks = [
            {"type": "divider"},
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": ":white_check_mark: Incident RCA Planning",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "You have been invited to this channel to assist "
                    + f"with planning the RCA for <#{incident_data.channel_id}>. The Incident Commander "
                    + "should invite anyone who can help contribute to the RCA"
                    + " and then use this channel to plan the meeting to go over the incident.",
                },
            },
        ]
        # Generate rca template and create rca if enabled
        # Get normalized description as rca title
        if "atlassian" in config.active.integrations:
            if (
                config.active.integrations.get("atlassian")
                .get("confluence")
                .get("auto_create_rca")
            ):
                from bot.confluence.rca import IncidentRootCauseAnalysis

                rca_title = " ".join(incident_data.incident_id.split("-")[2:])
                incident_summary = ""
                incident_description = ""
                incident_rca = ""
                incident_immediate_actions = ""
                incident_preventive_actions = ""
                try:
                    incident_slack_messages = get_incident_slack_thread(incident_data.channel_id)
                    incident_summary_task = asyncio.create_task(generate_incident_summary(incident_data.channel_id, incident_slack_messages))
                    incident_description_task = asyncio.create_task(generate_incident_description(incident_data.channel_id, incident_slack_messages))
                    incident_rca_task = asyncio.create_task(generate_incident_rca(incident_data.channel_id, incident_slack_messages))
                    incident_immediate_actions_task = asyncio.create_task(generate_incident_immediate_actions(incident_data.channel_id, incident_slack_messages))
                    incident_preventive_actions_task = asyncio.create_task(generate_incident_preventive_actions(incident_data.channel_id, incident_slack_messages))
                    await asyncio.gather(incident_summary_task, incident_description_task, incident_rca_task, incident_immediate_actions_task, incident_preventive_actions_task)
                    incident_summary = incident_summary_task.result()
                    incident_description = incident_description_task.result()
                    incident_rca = incident_rca_task.result()
                    incident_immediate_actions = incident_immediate_actions_task.result()
                    incident_preventive_actions = incident_preventive_actions_task.result()
                except Exception as error:
                    logger.error(f"Error generating incident PostMoterm Content for {incident_data.channel_id}: {error}")
                rca = IncidentRootCauseAnalysis(
                    incident_id=incident_data.incident_id,
                    rca_title=rca_title,
                    incident_commander=actual_user_names[0],
                    severity=incident_data.severity,
                    severity_definition=config.active.severities[
                        incident_data.severity
                    ],
                    pinned_items=read_incident_pinned_items(
                        incident_id=incident_data.incident_id
                    ),
                    timeline=log.read(incident_id=incident_data.incident_id),
                    incident_summary = incident_summary,
                    incident_description = incident_description,
                    incident_rca = incident_rca,
                    incident_immediate_actions = incident_immediate_actions,
                    incident_preventive_actions = incident_preventive_actions,
                )
                rca_link = rca.create()
                db_update_incident_rca_col(
                    channel_id=incident_data.channel_id,
                    rca=rca_link,
                )
                # Write audit log
                log.write(
                    incident_id=incident_data.incident_id,
                    event=f"RCA was automatically created: {rca_link}",
                ),
                incident_details_info["rcaChannelDetails"]["rca_link"] = rca_link
                rca_boilerplate_message_blocks.extend(
                    [
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": "*I have created a base RCA document that"
                                " you can build on. You can open it using the button below.*",
                            },
                        },
                        {
                            "block_id": "buttons",
                            "type": "actions",
                            "elements": [
                                {
                                    "type": "button",
                                    "text": {
                                        "type": "plain_text",
                                        "text": "Incident Postmoterm",
                                    },
                                    "style": "primary",
                                    "url": rca_link,
                                    "action_id": "open_rca",
                                },
                                {
                                    "type": "button",
                                    "text": {
                                        "type": "plain_text",
                                        "text": "View Incident Channel",
                                    },
                                    "url": f"https://{slack_workspace_id}.slack.com/archives/{incident_data.channel_id}",
                                    "action_id": "incident.join_incident_channel",
                                },
                            ],
                        },
                        {"type": "divider"},
                    ]
                )
                try:
                    if (
                            config.active.integrations.get("atlassian")
                                    .get("jira")
                                    .get("auto_create_action_item")
                    ):
                        incident_actions_items_list= await generate_incident_action_items_jira_tickets(incident_preventive_actions)
                        await create_automated_jira_action_items(incident_actions_items_list,incident_details_info)
                    else:
                        logger.info(f" Auto Action Items in Jira Disabled for {channel_name}")
                except Exception as error:
                    logger.error(f"Error in generating Auto Action Items in Jira for: {error}")
        else:
            rca_boilerplate_message_blocks.extend(
                [
                    {
                        "block_id": "buttons",
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "View Incident Channel",
                                },
                                "url": f"https://{slack_workspace_id}.slack.com/archives/{incident_data.channel_id}",
                                "action_id": "incident.join_incident_channel",
                            },
                        ],
                    },
                    {"type": "divider"},
                ]
            )
        try:
            blocks = rca_boilerplate_message_blocks
            result = slack_web_client.chat_postMessage(
                channel=rcaChannelDetails["id"],
                blocks=blocks,
                text="",
            )
            logger.debug(f"\n{result}\n")

        except slack_sdk.errors.SlackApiError as error:
            logger.error(f"Error sending RCA update to RCA channel: {error}")

        # Send message to incident channel
        try:
            result = slack_web_client.chat_postMessage(
                **IncidentResolutionMessage.create(channel=incident_data.channel_id,incident_details_info=incident_details_info),
                text="The incident has been resolved.",
            )
            logger.debug(f"\n{result}\n")
        except slack_sdk.errors.SlackApiError as error:
            logger.error(
                f"Error sending resolution update to incident channel {incident_data.channel_name}: {error}"
            )

        # Log
        logger.info(f"Sent resolution info to {incident_data.channel_name}.")

        # If PagerDuty incident(s) exist, attempt to resolve them
        if "pagerduty" in config.active.integrations:
            from bot.pagerduty.api import resolve

            if incident_data.pagerduty_incidents is not None:
                for inc in incident_data.pagerduty_incidents:
                    resolve(pd_incident_id=inc)

    # Also updates digest message
    try:
        slack_web_client.chat_update(
            channel=variables.digest_channel_id,
            ts=incident_data.dig_message_ts,
            blocks=IncidentChannelDigestNotification.update(
                incident_id=incident_data.channel_name,
                incident_description=incident_data.channel_description,
                is_security_incident=incident_data.is_security_incident,
                status=action_value,
                severity=incident_data.severity,
                conference_bridge=incident_data.conference_bridge,
                channel_name = channel_name,
                user = reporter,
                private_channel = is_private_incident,
            ),
            text="",
        )
    except slack_sdk.errors.SlackApiError as error:
        logger.error(
            f"Error sending status update to incident channel {incident_data.channel_name}: {error}"
        )

    # Change placeholder for select to match current status in boilerplate message
    result = slack_web_client.conversations_history(
        channel=incident_data.channel_id,
        inclusive=True,
        oldest=incident_data.bp_message_ts,
        limit=1,
    )
    blocks = result["messages"][0]["blocks"]
    status_block_index = tools.find_index_in_list(blocks, "block_id", "status")
    if status_block_index == -1:
        raise IndexNotFoundError("Could not find index for block_id status")
    blocks[status_block_index]["accessory"]["initial_option"] = {
        "text": {
            "type": "plain_text",
            "text": action_value.title(),
            "emoji": True,
        },
        "value": action_value,
    }
    slack_web_client.chat_update(
        channel=incident_data.channel_id,
        ts=action_parameters.message_details["ts"],
        blocks=blocks,
    )

    # Update incident record with the status
    logger.info(
        f"Updating incident record in database with new status for {incident_data.channel_name}"
    )
    try:
        db_update_incident_status_col(
            channel_id=incident_data.channel_id,
            status=action_value,
        )
    except Exception as error:
        logger.fatal(f"Error updating entry in database: {error}")
    
    
        

    # See if there's a scheduled reminder job for the incident and delete it if so
    if action_value == "resolved":
        for job in scheduler.process.list_jobs():
            job_title = f"{incident_data.channel_name}_updates_reminder"
            if job.id == job_title:
                try:
                    scheduler.process.delete_job(job_title)
                    logger.info(f"Deleted job: {job_title}")
                    # Write audit log
                    log.write(
                        incident_id=incident_data.channel_name,
                        event="Deleted scheduled reminder for incident updates.",
                    )
                except Exception as error:
                    logger.error(f"Could not delete the job {job_title}: {error}")

    # If the incident is resolved, disable status select
    if action_value == "resolved":
        result = slack_web_client.conversations_history(
            channel=incident_data.channel_id,
            inclusive=True,
            oldest=incident_data.bp_message_ts,
            limit=1,
        )
        blocks = result["messages"][0]["blocks"]
        status_block_index = tools.find_index_in_list(blocks, "block_id", "status")
        if status_block_index == -1:
            raise IndexNotFoundError("Could not find index for block_id status")
        blocks[status_block_index]["accessory"]["confirm"] = {
            "title": {
                "type": "plain_text",
                "text": "This incident is already resolved.",
            },
            "text": {
                "type": "mrkdwn",
                "text": "Since this incident has already been resolved, it "
                + "shouldn't be reopened. A new incident should be started instead.",
            },
            "confirm": {"type": "plain_text", "text": "Reopen Anyway"},
            "deny": {"type": "plain_text", "text": "Go Back"},
            "style": "danger",
        }
        slack_web_client.chat_update(
            channel=incident_data.channel_id,
            ts=action_parameters.message_details["ts"],
            blocks=blocks,
        )
    # Log
    logger.info(
        f"Updated incident status for {incident_data.channel_name} to {action_value}."
    )
    try:
        result = slack_web_client.chat_postMessage(
            **IncidentUpdate.status(
                channel=incident_data.channel_id, status=action_value
            ),
            text=f"The incident status has been changed to {action_value}.",
        )
        logger.debug(f"\n{result}\n")
    except slack_sdk.errors.SlackApiError as error:
        logger.error(
            f"Error sending status update to incident channel {incident_data.channel_name}: {error}"
        )
    # Finally, updated the updated_at column
    db_update_incident_updated_at_col(
        channel_id=incident_data.channel_id,
        updated_at=tools.fetch_timestamp(),
    )


async def set_severity(
    action_parameters: type[ActionParametersSlack] = None,
):
    """When an incoming action is incident.set_severity, this method
    updates the severity of the incident

    Keyword arguments:
    action_parameters(type[ActionParametersSlack]) - contains Slack actions data
    """
    incident_data = db_read_incident(channel_id=action_parameters.channel_details["id"])
    action_value = action_parameters.actions["selected_option"]["value"]
    channel_name = incident_data.channel_name
    is_private_incident = action_parameters.channel_details.get("name",channel_name) != channel_name
    user = action_parameters.user_details["id"]
    reporter = incident_data.roles['incident_reporter'] if incident_data.roles and 'incident_reporter' in incident_data.roles else user

    # Also updates digest message
    try:
        slack_web_client.chat_update(
            channel=variables.digest_channel_id,
            ts=incident_data.dig_message_ts,
            blocks=IncidentChannelDigestNotification.update(
                incident_id=incident_data.channel_name,
                incident_description=incident_data.channel_description,
                is_security_incident=incident_data.is_security_incident,
                status=incident_data.status,
                severity=action_value,
                conference_bridge=incident_data.conference_bridge,
                channel_name = channel_name,
                user = reporter,
                private_channel = is_private_incident,
            ),
        )
    except slack_sdk.errors.SlackApiError as error:
        logger.error(
            f"Error sending severity update to incident channel {incident_data.channel_name}: {error}"
        )

    # Change placeholder for select to match current status in boilerplate message
    result = slack_web_client.conversations_history(
        channel=incident_data.channel_id,
        inclusive=True,
        oldest=incident_data.bp_message_ts,
        limit=1,
    )
    blocks = result["messages"][0]["blocks"]
    sev_blocks_index = tools.find_index_in_list(blocks, "block_id", "severity")
    if sev_blocks_index == -1:
        raise IndexNotFoundError("Could not find index for block_id severity")
    blocks[sev_blocks_index]["accessory"]["initial_option"] = {
        "text": {
            "type": "plain_text",
            "text": action_value.upper(),
            "emoji": True,
        },
        "value": action_value,
    }
    slack_web_client.chat_update(
        channel=incident_data.channel_id,
        ts=action_parameters.message_details["ts"],
        blocks=blocks,
    )

    # Update incident record with the severity
    logger.info(
        f"Updating incident record in database with new severity for {incident_data.channel_name}"
    )
    try:
        db_update_incident_severity_col(
            channel_id=incident_data.channel_id,
            severity=action_value,
        )
    except Exception as error:
        logger.fatal(f"Error updating entry in database: {error}")

    # If SEV1/2, we need to start a timer to remind the channel about sending status updates
    if config.active.incident_reminders:
        if action_value in config.active.incident_reminders.get(
            "qualifying_severities"
        ):
            logger.info(f"Adding job because action was {action_value}")
            scheduler.add_incident_scheduled_reminder(
                channel_name=incident_data.channel_name,
                channel_id=incident_data.channel_id,
                severity=action_value,
                rate=config.active.incident_reminders.get("rate"),
            )
            # Write audit log
            log.write(
                incident_id=incident_data.channel_name,
                event=f"Scheduled reminder job created.",
            )

    # Final notification
    try:
        result = slack_web_client.chat_postMessage(
            **IncidentUpdate.severity(
                channel=incident_data.channel_id, severity=action_value
            ),
            text=f"The incident severity has been changed to {action_value}.",
        )
        logger.debug(f"\n{result}\n")
    except slack_sdk.errors.SlackApiError as error:
        logger.error(
            f"Error sending severity update to incident channel {incident_data.channel_name}: {error}"
        )
    # Log
    logger.info(
        f"Updated incident severity for {incident_data.channel_name} to {action_value}."
    )
    # Finally, updated the updated_at column
    db_update_incident_updated_at_col(
        channel_id=incident_data.channel_id,
        updated_at=tools.fetch_timestamp(),
    )
    # Write audit log
    log.write(
        incident_id=incident_data.channel_name,
        event=f"Severity set to {action_value.upper()}.",
    )


"""
Utility Functions
"""


def extract_role_owner(message_blocks: Dict[Any, Any], block_id: str) -> str:
    """
    Takes message blocks and a block_id and returns information specific
    to one of the role blocks
    """
    index = tools.find_index_in_list(message_blocks, "block_id", block_id)
    if index == -1:
        raise IndexNotFoundError(f"Could not find index for block_id {block_id}")
    return message_blocks[index]["text"]["text"].split(":")[1].replace(" ", "")



def get_incident_slack_thread(channel_id: str):
    """
    Fetches and formats the Slack channel history related to an incident.

    Parameters:
    - channel_id (str): The unique identifier of the Slack channel.

    Returns:
    - formatted_history (str): The formatted incident-related Slack channel history.
    """
    formatted_history = ""
    try:
        # Retrieve incident data from the database
        incident_data = db_read_incident(channel_id=channel_id)
        logger.info(f"Fetches and formats the Slack channel history for {incident_data.channel_name}.")

        # Retrieve and format the channel history
        channel_id = incident_data.channel_id
        channel_name = incident_data.channel_name
        formatted_history = get_formatted_channel_history(channel_id, channel_name)

        # Remove bot-related lines from the history
        formatted_history = remove_bot_lines(formatted_history)
    except Exception as error:
        logger.error(
            f"Error Generating Incident Slack Thread for {channel_id}: {error}"
        )
    return formatted_history

async def generate_incident_summary(channel_id: str, channel_history: str):
    """
    Generate an incident summary based on Slack channel history using ChatGPT.

    Parameters:
    - channel_id (str): The unique identifier of the Slack channel.
    - channel_history (str): The history of the Slack channel related to the incident.

    Returns:
    - incident_summary (str): The generated incident summary.
    """
    incident_summary = ""

    try:
        logger.info(f"Generating incident summary for {channel_id}.")
        incident_summary = await ChatGPTApi().generate_incident_summary(channel_history)
        logger.info(f"Incident summary generated via GPT: {incident_summary}")

    except Exception as error:
        logger.error(f"Error generating incident summary for {channel_id}: {error}")

    return incident_summary

async def generate_incident_description(channel_id: str, channel_history: str):
    """
    Generate an incident description based on Slack channel history using ChatGPT.

    Parameters:
    - channel_id (str): The unique identifier of the Slack channel.
    - channel_history (str): The history of the Slack channel related to the incident.

    Returns:
    - incident_description (str): The generated incident description.
    """
    incident_description = ""

    try:
        logger.info(f"Generating incident description for {channel_id}.")
        incident_description = await ChatGPTApi().generate_incident_description(channel_history)
        logger.info(f"Incident description generated via GPT: {incident_description}")

    except Exception as error:
        logger.error(f"Error generating incident description for {channel_id}: {error}")

    return incident_description

async def generate_incident_rca(channel_id: str, channel_history: str):
    """
    Generate an incident rca based on Slack channel history using ChatGPT.

    Parameters:
    - channel_id (str): The unique identifier of the Slack channel.
    - channel_history (str): The history of the Slack channel related to the incident.

    Returns:
    - incident_rca (str): The generated incident rca.
    """
    incident_rca = ""

    try:
        logger.info(f"Generating incident rca for {channel_id}.")
        incident_rca = await ChatGPTApi().generate_incident_rca(channel_history)
        logger.info(f"Incident rca generated via GPT: {incident_rca}")

    except Exception as error:
        logger.error(f"Error generating incident rca for {channel_id}: {error}")

    return incident_rca

async def generate_incident_immediate_actions(channel_id: str, channel_history: str):
    """
    Generate an incident immediate_actions based on Slack channel history using ChatGPT.

    Parameters:
    - channel_id (str): The unique identifier of the Slack channel.
    - channel_history (str): The history of the Slack channel related to the incident.

    Returns:
    - incident_immediate_actions (str): The generated incident immediate actions.
    """
    incident_immediate_actions = ""

    try:
        logger.info(f"Generating incident immediate actions for {channel_id}.")
        incident_immediate_actions = await ChatGPTApi().generate_immediate_actions(channel_history)
        logger.info(f"Incident immediate actions generated via GPT: {incident_immediate_actions}")

    except Exception as error:
        logger.error(f"Error generating incident immediate actions for {channel_id}: {error}")

    return incident_immediate_actions


async def generate_incident_preventive_actions(channel_id: str, channel_history: str):
    """
    Generate an incident preventive_actions based on Slack channel history using ChatGPT.

    Parameters:
    - channel_id (str): The unique identifier of the Slack channel.
    - channel_history (str): The history of the Slack channel related to the incident.

    Returns:
    - incident_preventive_actions (str): The generated incident preventive actions.
    """
    incident_preventive_actions = ""

    try:
        logger.info(f"Generating incident preventive actions for {channel_id}.")
        incident_preventive_actions = await ChatGPTApi().generate_preventive_actions(channel_history)
        logger.info(f"Incident preventive actions generated via GPT: {incident_preventive_actions}")

    except Exception as error:
        logger.error(f"Error generating incident preventive actions for {channel_id}: {error}")

    return incident_preventive_actions

async def generate_incident_action_items_jira_tickets(incident_action_items: str):
    """
    Use ChatGPT to create Jira tickets from immediate action items list

    Parameters:
    - incident_immediate_actions (str): The generated incident immediate actions.

    Returns:
    - jira_ticket_contract (list): A list of immediate action items taken during the incident in contract of Jira.
    """
    jira_ticket_contract = []

    try:
        logger.info(f"Generating Jira Tickets of actions Items for {incident_action_items} ")
        jira_ticket_contract = await ChatGPTApi().generate_actions_item_jira_tickets(incident_action_items)
        logger.info(f"Incident action items generated via GPT in contract of Jira: {incident_action_items}")

    except Exception as error:
        logger.error(f"Error Generating Jira Tickets of immediate actions for {incident_action_items}: {error}")

    return jira_ticket_contract

async def generate_catch_me_on_incident(channel_id: str, channel_history: str):
    """
    Generate catch me on incident based on Slack channel history using ChatGPT.

    Parameters:
    - channel_id (str): The unique identifier of the Slack channel.
    - channel_history (str): The history of the Slack channel related to the incident.

    Returns:
    - catch_me_on_incident (str): The generated catch me on incident summary.
    """
    catch_me_on_incident = ""

    try:
        logger.info(f"Generating catch me on incident for {channel_id}.")
        catch_me_on_incident = await ChatGPTApi().generate_catch_me_on_incident(channel_history)
        logger.info(f"Catch me on Incident generated via GPT: {catch_me_on_incident}")

    except Exception as error:
        logger.error(f"Error generating Catch me on Incident for {channel_id}: {error}")

    return catch_me_on_incident

def remove_bot_lines(channel_history):
    """
    Remove lines containing 'Octo' from a channel history string.

    Parameters:
    - channel_history (str): The input string containing channel history.

    Returns:
    - modified_history (str): The modified channel history with 'Octo' lines removed.
    """
    # Split the input string into lines
    lines = channel_history.split('\n')

    # Include lines that contain either 'Octo' or 'Bot'
    filtered_lines = [line for line in lines if 'Octo' not in line and 'Bot' not in line]



    # Join the filtered lines to create the modified channel history
    modified_history = '\n'.join(filtered_lines)

    return modified_history

async def create_automated_jira_action_items(incident_immediate_actions_list: List[Dict[str, str]], incident_details_info: dict):

    try:
        channel_id = incident_details_info["incident_data"].channel_id
        incident_id = incident_details_info["incident_data"].incident_id
        logger.info(f"Generating Auto Action Items in Jira for Channel {channel_id}")
        for immediate_actions_ticket in incident_immediate_actions_list:
            resp = JiraIssue(
                incident_id=incident_id,
                description=immediate_actions_ticket.get("description"),
                issue_type="Task",
                priority="high",
                summary=immediate_actions_ticket.get("summary"),
            ).new()
            issue_link = "{}/browse/{}".format(config.atlassian_api_url, resp.get("key"))
            db_update_jira_issues_col(channel_id=channel_id, issue_link=issue_link)
            try:
                resp = slack_web_client.chat_postMessage(
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
                                        immediate_actions_ticket.get("summary")
                                    ),
                                },
                                {
                                    "type": "mrkdwn",
                                    "text": "*Priority:* High",
                                },
                                {
                                    "type": "mrkdwn",
                                    "text": "*Type:* Task",
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
            except Exception as error:
                logger.error(f"Error sending Jira issue message for {incident_id}: {error}")
    except Exception as error:
        logger.error(f"Error in generating Auto Action Items in Jira for Channel {channel_id}: {error}")        