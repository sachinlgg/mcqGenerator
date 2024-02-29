import config


class IncidentResolutionMessage:
    @staticmethod
    def create(channel: str, incident_details_info: dict = None):
        incident_channel_rca = incident_details_info.get("rcaChannelDetails", {})
        incident_rca_channel_name = incident_channel_rca.get("name", "")
        incident_rca_link = incident_channel_rca.get("rca_link")
        incident_postmortems_url = incident_rca_link or config.active.links.get("incident_postmortems")
        return {
            "channel": channel,
            "blocks": [
                {"type": "divider"},
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": ":white_check_mark: Incident Resolved",
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "This incident has been marked as resolved. The Incident Commander and relevant stakeholders "
                        + f"are invited to rca channel *#{incident_rca_channel_name}* to discuss the RCA."
                        + "\n You may optionally export "
                        + "the chat log for this incident below so it can be referenced in the RCA.",
                    },
                },
                {
                    "block_id": "resolution_buttons",
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Export Chat Logs",
                            },
                            "style": "primary",
                            "action_id": "incident.export_chat_logs",
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Archive Channel",
                            },
                            "style": "danger",
                            "action_id": "incident.archive_incident_channel",
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Incident Guide",
                            },
                            "url": config.active.links.get("incident_guide"),
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Incident Postmortem",
                            },
                            "url": incident_postmortems_url,
                        },
                    ],
                },
                {"type": "divider"},
            ],
        }
