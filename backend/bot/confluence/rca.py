import config

from bot.confluence.api import ConfluenceApi, logger
from bot.models.pg import IncidentLogging
from bot.shared import tools
from bot.templates.confluence.rca import RCATemplate
from typing import Any, Dict, List, Tuple


class IncidentRootCauseAnalysis:
    def __init__(
        self,
        incident_id: str,
        rca_title: str,
        incident_commander: str,
        severity: str,
        severity_definition: str,
        pinned_items: List[IncidentLogging],
        timeline: List[Dict],
        incident_summary: str,
        incident_description: str,
        incident_rca: str,
        incident_immediate_actions: str,
        incident_preventive_actions: str,

    ):
        self.incident_id = incident_id
        self.title = rca_title
        self.incident_commander = incident_commander
        self.severity = severity
        self.severity_definition = severity_definition
        self.pinned_items = pinned_items
        self.timeline = timeline
        self.incident_summary = incident_summary
        self.incident_description = incident_description
        self.incident_rca = incident_rca
        self.incident_immediate_actions = incident_immediate_actions
        self.incident_preventive_actions = incident_preventive_actions

        self.parent_page = (
            config.active.integrations.get("atlassian")
            .get("confluence")
            .get("parent")
        )
        self.space = (
            config.active.integrations.get("atlassian")
            .get("confluence")
            .get("space")
        )

        self.confluence = ConfluenceApi()
        self.exec = self.confluence.api
        self.today = self.confluence.today

    def create(self) -> str:
        """
        Creates a starting RCA page and returns the create page's URL
        """
        title = f"{self.today} - {self.incident_id} - {self.title.title()}"
        parent_page_id = self.exec.get_page_id(self.space, self.parent_page)
        logger.info(
            f"Creating RCA {title} in Confluence space {self.space} under parent {self.parent_page}..."
        )
        # Generate html for rca doc
        body = self.__render_rca_html(
            incident_commander=self.incident_commander,
            severity=self.severity,
            severity_definition=self.severity_definition,
            timeline=self.__generate_timeline(),
            pinned_messages=self.__generate_pinned_messages(),
            incident_summary = self.incident_summary,
            incident_description = self.incident_description,
            incident_rca = self.incident_rca,
            incident_immediate_actions = self.incident_immediate_actions,
            incident_preventive_actions = self.incident_preventive_actions,
        )
        # Create rca doc
        if self.exec.page_exists(space=self.space, title=self.parent_page):
            try:
                page_id = self.exec.get_page_id(self.space, title)
                if page_id:
                    logger.info(f"Updating existing RCA page {title}...")
                    self.exec.update_page(
                        page_id,
                        title,
                        body,
                        parent_id=parent_page_id,
                        type="page",
                        representation="storage",
                    )
                else:
                    logger.info(f"Creating new RCA page {title}...")
                    self.exec.create_page(
                        self.space,
                        title,
                        body,
                        parent_id=parent_page_id,
                        type="page",
                        representation="storage",
                    )
                created_page_id = self.exec.get_page_id(self.space, title)
                created_page_info = self.exec.get_page_by_id(
                    page_id=created_page_id
                )
                url = (
                    created_page_info["_links"]["base"]
                    + created_page_info["_links"]["webui"]
                )
                # If there are images in pinned items
                # Add them as attachments
                if self.pinned_items:
                    for item in self.pinned_items:
                        if item.img:
                            try:
                                logger.info(
                                    f"Attaching pinned item to {title}..."
                                )
                                # Attach content to rca
                                self.exec.attach_content(
                                    item.img,
                                    name=item.title,
                                    content_type=item.mimetype,
                                    page_id=created_page_id,
                                    space=config.active.integrations.get(
                                        "atlassian"
                                    )
                                    .get("confluence")
                                    .get("space"),
                                    comment=f"This item was pinned to the incident by {item.user} at {item.ts}.",
                                )
                            except Exception as error:
                                logger.error(
                                    f"Error attaching file to {title}: {error}"
                                )
                return url
            except Exception as error:
                logger.error(error)
        else:
            logger.error(
                "Couldn't create RCA page, does the parent page exist?"
            )

    def __find_user_id(self, user: str) -> Tuple[bool, Any]:
        """
        Accepts the publicName of a user in Atlassian Cloud and returns the ID if it exists
        """
        groups = self.exec.get_all_groups(start=0, limit=50)
        for g in groups:
            users = self.exec.get_group_members(
                group_name=g["name"], start=0, limit=1000
            )
            for u in users:
                if user in u["publicName"]:
                    return True, u["accountId"]
                else:
                    pass
        return False, None

    def __generate_pinned_messages(self) -> str:
        if not self.pinned_items:
            return "<p>No items were pinned for this incident.</p>"
        all_items_formatted = ""
        for item in self.pinned_items:
            if item.content:
                all_items_formatted += f"<blockquote><p><strong>{item.user} @ {item.ts} - </strong> {item.content}</p></blockquote><p />"
        return all_items_formatted

    def __generate_timeline(self) -> str:
        if len(self.timeline) == 0:
            return """
    <tr>
        <td>
            <p>None.</p>
        </td>
        <td>
            <p>No items were added to this incident's timeline.</p>
        </td>
    </tr>
    """
        all_items_formatted = ""
        for item in self.timeline:
            all_items_formatted += f"""
    <tr>
        <td>
            <p>{item["ts"]}</p>
        </td>
        <td>
            <p>{item["log"]}</p>
        </td>
    </tr>
    """
        # Boilerplate
        all_items_formatted += f"""
    <tr>
        <td>
            <p>&hellip;</p>
        </td>
        <td>
            <p>&hellip;</p>
        </td>
    </tr>
    """
        return all_items_formatted

    def __render_rca_html(
        self,
        incident_commander: str,
        severity: str,
        severity_definition: str,
        timeline: str,
        pinned_messages: str,
        incident_summary: str,
        incident_description: str,
        incident_rca: str,
        incident_immediate_actions: str,
        incident_preventive_actions: str,
    ) -> str:
        """Renders HTML for use in Confluence documents"""
        variables = {
            "incident_commander": self.__user_mention_format(
                incident_commander
            ),
            "severity": severity.upper(),
            "severity_definition": severity_definition,
            "timeline": timeline,
            "pinned_messages": pinned_messages,
            "incident_summary": incident_summary,
            "incident_description": incident_description,
            "incident_rca": incident_rca,
            "incident_immediate_actions": incident_immediate_actions,
            "incident_preventive_actions": incident_preventive_actions,
        }
        return RCATemplate.template(
            incident_commander=incident_commander,
            severity=severity,
            severity_definition=severity_definition,
            timeline=timeline,
            pinned_messages=pinned_messages,
            incident_summary=incident_summary,
            incident_description=incident_description,
            incident_rca=incident_rca,
            incident_immediate_actions=incident_immediate_actions,
            incident_preventive_actions=incident_preventive_actions,

        )

    def __user_mention_format(self, role: str) -> str:
        """
        Determines whether a user mention is a link or a string based on whether or
        not we could find the user ID
        """
        result = self.__find_user_id(role)
        if result[0]:
            return f"""
                <ac:link>
                    <ri:user ri:userkey="{result[1]}" />
                </ac:link>
            """
        else:
            return f"@{role}"
