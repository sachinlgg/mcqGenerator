import re

from bot.incident.action_parameters import (
    ActionParametersSlack,
    ActionParametersWeb,
)
from bot.incident.incident import Incident, RequestParameters
from bot.shared import tools
from bot.templates.incident.channel_boilerplate import (
    IncidentChannelBoilerplateMessage,
)
from bot.templates.incident.digest_notification import (
    IncidentChannelDigestNotification,
)
from bot.templates.incident.resolution_message import IncidentResolutionMessage
from bot.templates.incident.updates import IncidentUpdate
from bot.templates.incident.user_dm import IncidentUserNotification

placeholder_token = "verification-token"
placeholder_team_id = "T111"
placeholder_enterprise_id = "E111"
placeholder_app_id = "A111"


class TestIncidentManagement:
    def test_action_parameters_slack(self):
        ap = ActionParametersSlack(
            payload={
                "type": "block_actions",
                "team": {"id": "T9TK3CUKW", "domain": "example"},
                "user": {
                    "id": "UA8RXUSPL",
                    "name": "sample",
                    "team_id": "T9TK3CUKW",
                },
                "api_app_id": "AABA1ABCD",
                "token": "9s8d9as89d8as9d8as989",
                "container": {
                    "type": "message_attachment",
                    "message_ts": "1548261231.000200",
                    "attachment_id": 1,
                    "channel_id": "CBR2V3XEX",
                    "is_ephemeral": False,
                    "is_app_unfurl": False,
                },
                "trigger_id": "12321423423.333649436676.d8c1bb837935619ccad0f624c448ffb3",
                "channel": {"id": "CBR2V3XEX", "name": "mock"},
                "message": {
                    "bot_id": "BAH5CA16Z",
                    "type": "message",
                    "text": "This content can't be displayed.",
                    "user": "UAJ2RU415",
                    "ts": "1548261231.000200",
                },
                "response_url": "https://hooks.slack.com/actions/AABA1ABCD/1232321423432/D09sSasdasdAS9091209",
                "actions": [
                    {
                        "action_id": "sample-action",
                        "block_id": "=qXel",
                        "text": {
                            "type": "plain_text",
                            "text": "View",
                            "emoji": True,
                        },
                        "value": "click_me_123",
                        "type": "button",
                        "action_ts": "1548426417.840180",
                    }
                ],
            }
        )

        assert ap.actions == {
            "action_id": "sample-action",
            "block_id": "=qXel",
            "text": {"type": "plain_text", "text": "View", "emoji": True},
            "value": "click_me_123",
            "type": "button",
            "action_ts": "1548426417.840180",
        }

        assert ap.channel_details == {"id": "CBR2V3XEX", "name": "mock"}

        assert ap.message_details == {
            "bot_id": "BAH5CA16Z",
            "type": "message",
            "text": "This content can't be displayed.",
            "user": "UAJ2RU415",
            "ts": "1548261231.000200",
        }

        assert ap.user_details == {
            "id": "UA8RXUSPL",
            "name": "sample",
            "team_id": "T9TK3CUKW",
        }

        assert ap.parameters == {
            "action_id": "sample-action",
            "channel_id": "CBR2V3XEX",
            "channel_name": "mock",
            "timestamp": "1548261231.000200",
            "user": "sample",
            "user_id": "UA8RXUSPL",
        }

    def test_action_parameters_web(self):
        ap = ActionParametersWeb(
            incident_id="mock_incident_id",
            channel_id="mock_channel_id",
            role="mock_role",
            bp_message_ts="mock_ts",
            user="mock_user",
        )

        assert ap.incident_id == "mock_incident_id"

        assert ap.channel_id == "mock_channel_id"

        assert ap.role == "mock_role"

        assert ap.bp_message_ts == "mock_ts"

        assert ap.user == "mock_user"

    def test_incident_instantiate(self):
        inc = Incident(
            request_parameters=RequestParameters(
                channel="CBR2V3XEX",
                incident_description="something has broken",
                user="sample-incident-creator-user",
                severity="sev4",
                created_from_web=False,
                is_security_incident=False,
            )
        )
        assert isinstance(inc, Incident)

        assert re.search("^inc.*something-has-broken$", inc.channel_name)

        assert inc.conference_bridge == "mock"

    def test_incident_channel_name_create(self):
        inc = Incident(
            request_parameters=RequestParameters(
                channel="CBR2V3XEX",
                incident_description="unallowed ch@racter check!",
                user="sample-incident-creator-user",
                severity="sev4",
                created_from_web=False,
                is_security_incident=False,
            )
        )

        assert re.search("^inc.*unallowed-chracter-check$", inc.channel_name)

    def test_incident_build_digest_notification(self):
        assert IncidentChannelDigestNotification.create(
            incident_channel_details={
                "incident_description": "mock",
                "id": "CBR2V3XEX",
                "name": "mock",
                "is_security_incident": False,
                "user": "mock"
            },
            conference_bridge="mock",
            severity="sev4",
        ) == {
            "channel": "incidents",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": ":warning::fire_engine: mock",
                    },
                },
                {
                    "block_id": "digest_channel_severity",
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": ":fire: *Severity*: SEV4",
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
                        "text": ":speaking_head_in_silhouette: *Reporter*: <@mock>",
                    },
                },
                {
                    "block_id": "join_incident_channel",
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": ":slack: *Channel*: #mock",
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "A new incident has been declared. Please use the buttons here to participate.",
                    },
                },
                {
                    "type": "actions",
                    "block_id": "incchannelbuttons",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "War Room",
                            },
                            "url": "mock",
                            "action_id": "incident.click_conference_bridge_link",
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Incident Guide",
                            },
                            "url": "https://changeme.com",
                            "action_id": "incident.incident_guide_link",
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Incident Postmortems",
                            },
                            "url": "https://changeme.com",
                            "action_id": "incident.incident_postmortem_link",
                        },
                    ],
                },
            ],
        }

    def test_build_incident_channel_boilerplate(self):
        msg = IncidentChannelBoilerplateMessage.create(
            incident_channel_details={"id": "CBR2V3XEX", "name": "mock"},
            severity="sev4",
        )
        assert msg == {
            "channel": "CBR2V3XEX",
            "blocks": [
                {"type": "divider"},
                {
                    "block_id": "header",
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "We're facing an incident - what's the next step?",
                    },
                },
                {
                    "block_id": "header_info_1",
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "Start with assigning or claiming the Incident Commander role, followed by other role assignments.",
                    },
                },
                {
                    "block_id": "header_info_2",
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "The Incident Commander must promptly confirm the incident's severity and update it if it changes.",
                    },
                },
                {
                    "block_id": "header_info_3",
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "The incident initiates in *investigating* mode.and can transition through statuses until resolved.",
                    },
                },
                {"type": "divider"},
                {
                    "block_id": "status",
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "*Current Status:*"},
                    "accessory": {
                        "type": "static_select",
                        "action_id": "incident.set_status",
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
                {
                    "block_id": "severity",
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "*Severity:*"},
                    "accessory": {
                        "type": "static_select",
                        "action_id": "incident.set_severity",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "SEV4",
                            "emoji": True,
                        },
                        "options": [
                            {
                                "text": {
                                    "type": "plain_text",
                                    "text": "SEV1",
                                    "emoji": True,
                                },
                                "value": "sev1",
                            },
                            {
                                "text": {
                                    "type": "plain_text",
                                    "text": "SEV2",
                                    "emoji": True,
                                },
                                "value": "sev2",
                            },
                            {
                                "text": {
                                    "type": "plain_text",
                                    "text": "SEV3",
                                    "emoji": True,
                                },
                                "value": "sev3",
                            },
                            {
                                "text": {
                                    "type": "plain_text",
                                    "text": "SEV4",
                                    "emoji": True,
                                },
                                "value": "sev4",
                            },
                        ],
                    },
                },
                {"type": "divider"},
                {
                    "block_id": "role_incident_commander",
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Incident Commander*: _none_",
                    },
                },
                {
                    "type": "actions",
                    "block_id": "claim_assign_engineer_incident_commander",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Claim Role",
                                "emoji": True
                            },
                            "value": "incident_commander",
                            "action_id": "incident.claim_role"
                        },
                        {
                            "type": "users_select",
                            "action_id": "incident.assign_role",
                            "placeholder": {
                                "type": "plain_text",
                                "text": "Assign a role incident_commander ..."
                            }
                        }
                    ]
                },
                {"type": "divider"},
                {
                    "block_id": "role_technical_lead",
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Technical Lead*: _none_",
                    },
                },
                {
                    "type": "actions",
                    "block_id": "claim_assign_engineer_technical_lead",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Claim Role",
                                "emoji": True
                            },
                            "value": "technical_lead",
                            "action_id": "incident.claim_role"
                        },
                        {
                            "type": "users_select",
                            "action_id": "incident.assign_role",
                            "placeholder": {
                                "type": "plain_text",
                                "text": "Assign a role technical_lead ..."
                            }
                        }
                    ]
                },
                {"type": "divider"},
                {
                    "block_id": "role_communications_liaison",
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Communications Liaison*: _none_",
                    },
                },
                {
                    "type": "actions",
                    "block_id": "claim_assign_engineer_communications_liaison",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Claim Role",
                                "emoji": True
                            },
                            "value": "communications_liaison",
                            "action_id": "incident.claim_role"
                        },
                        {
                            "type": "users_select",
                            "action_id": "incident.assign_role",
                            "placeholder": {
                                "type": "plain_text",
                                "text": "Assign a role communications_liaison ..."
                            }
                        }
                    ]
                },
                {"type": "divider"},
                {
                    "block_id": "help_buttons",
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Manage Timeline",
                                "emoji": True,
                            },
                            "action_id": "open_incident_bot_timeline",
                            "style": "primary",
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Incident Guide",
                            },
                            "url": "https://changeme.com",
                            "action_id": "incident.incident_guide_link",
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Incident Postmortems",
                            },
                            "url": "https://changeme.com",
                            "action_id": "incident.incident_postmortem_link",
                        },
                    ],
                },
                {"type": "divider"},
            ],
        }

    def test_build_status_update(self):
        status = "monitoring"
        assert IncidentUpdate.status(channel="mock", status=status) == {
            "blocks": [
                {"type": "divider"},
                {
                    "text": {
                        "text": ":warning: Status Update",
                        "type": "plain_text",
                    },
                    "type": "header",
                },
                {
                    "text": {
                        "text": f"The incident status has changed to *{status.title()}*.",
                        "type": "mrkdwn",
                    },
                    "type": "section",
                },
                {"type": "divider"},
            ],
            "channel": "mock",
        }

    def test_build_updated_digest_message(self):
        status = "identified"
        severity = "sev4"
        is_security_incident = False
        msg = IncidentChannelDigestNotification.update(
            incident_id="mock",
            incident_description="mock",
            is_security_incident=is_security_incident,
            status=status,
            severity=severity,
            conference_bridge="mock",
        )
        assert msg == [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": ":warning::fire_engine: mock",
                },
            },
            {
                "block_id": "digest_channel_severity",
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": ":fire: *Severity*: SEV4",
                },
            },
            {
                "block_id": "digest_channel_status",
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f":bulb: *Status*: Identified",
                },
            },
            {
                "block_id": "digest_channel_reporter",
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": ":speaking_head_in_silhouette: *Reporter*: <@U05T9BLKJ07>",
                },
            },
            {
                "block_id": "join_incident_channel",
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": ":slack: *Channel*: #default_channel_name"
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "This incident is in progress. Current status is listed here. Join the channel for more information.",
                },
            },
            {
                "type": "actions",
                "block_id": "incchannelbuttons",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "War Room"},
                        "url": "mock",
                        "action_id": "incident.click_conference_bridge_link",
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Incident Guide",
                        },
                        "url": "https://changeme.com",
                        "action_id": "incident.incident_guide_link",
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Incident Postmortems",
                        },
                        "url": "https://changeme.com",
                        "action_id": "incident.incident_postmortem_link",
                    },
                ],
            },
        ]

    def test_build_public_status_update(self):
        timestamp = tools.fetch_timestamp()
        assert IncidentUpdate.public_update(
            incident_id="mock",
            impacted_resources="api",
            message="foobar",
            timestamp=timestamp,
        ) == [
            {
                "text": {
                    "text": ":warning: Incident Update",
                    "type": "plain_text",
                },
                "type": "header",
            },
            {
                "fields": [
                    {"text": "*Incident:*\n <#mock>", "type": "mrkdwn"},
                    {
                        "text": f"*Posted At:*\n {timestamp}",
                        "type": "mrkdwn",
                    },
                    {"text": "*Impacted Resources:*\n api", "type": "mrkdwn"},
                ],
                "type": "section",
            },
            {
                "text": {
                    "text": "*Current Status*\n foobar",
                    "type": "mrkdwn",
                },
                "type": "section",
            },
            {
                "elements": [
                    {
                        "text": "This update was provided by the incident management team in response to an ongoing incident.",
                        "type": "mrkdwn",
                    }
                ],
                "type": "context",
            },
        ]
