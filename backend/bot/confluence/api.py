import config
import datetime
import logging

from atlassian import Confluence

logger = logging.getLogger("confluence")


class ConfluenceApi:
    def __init__(self):
        self.confluence = Confluence(
            url=config.atlassian_api_url,
            username=config.atlassian_api_username,
            password=config.atlassian_api_token,
            cloud=True,
        )
        self.today = datetime.datetime.today().strftime("%Y-%m-%d")

    @property
    def api(self) -> Confluence:
        return self.confluence

    def test(self) -> bool:
        try:
            return self.confluence.page_exists(
                config.active.integrations.get("atlassian")
                .get("confluence")
                .get("space"),
                config.active.integrations.get("atlassian")
                .get("confluence")
                .get("parent"),
            )
        except Exception as error:
            logger.error(f"Error authenticating to Confluence: {error}")
            logger.error(
                f"Please check Confluence configuration and try again."
            )
