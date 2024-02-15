import logging
import openai
import config

logger = logging.getLogger("chatgpt")

class ChatGPTApi:
    def __init__(self):
        openai.api_key = config.chatgpt_api_key

    @property
    def api(self) -> openai:
        return openai

    def test(self) -> bool:
        try:
            # You can perform a simple test here, like generating a response.
            response = self.api.Completion.create(
                engine="gpt-3.5-turbo-instruct",
                prompt="Hello, ChatGPT!",
                max_tokens=10,
            )
            if response.choices and response.choices[0].text.strip():
                logger.info(f"Connection to ChatGPT API successful.${response.choices[0].text.strip()}")
                return True
            else:
                logger.error("Connection to ChatGPT API successful, but the response was empty.")
                return False
        except Exception as error:
            logger.error(f"Error authenticating to ChatGPT: {error}")
            logger.error(f"Please check ChatGPT API configuration and try again.")
            return False

    async def generate_incident_summary(self, slack_message):
        """
        Generate a summary of an incident based on a Slack message using ChatGPT.

        Parameters:
        - slack_message (str): The Slack message containing details about the incident.

        Returns:
        - incident_summary (str): The generated incident summary.
        """

        # Define the ChatGPT prompt
        prompt = f"Generate a incident summary based on the following incidents channel slack :\n{slack_message}\n"
        logger.info(f"Generate Incident Summary from the following slack message : \n {slack_message} \n")

        try:
            response = self.api.Completion.create(
                engine="gpt-3.5-turbo-instruct",  # You can try other engines
                prompt=prompt,
                max_tokens=250,  # Adjust this based on the desired summary length
                temperature=0.7,  # Adjust temperature for creativity (0.2 for focused, 1.0 for diverse)
                stop=None,  # You can provide a list of stop words to limit the response
                n=1,  # Number of responses to generate
                timeout=30,  # Timeout in seconds
            )

            incident_summary = response.choices[0].text.strip()
            return incident_summary

        except Exception as error:
            logger.error(f"Error generating incident summary: {error}")
            return None

    async def generate_incident_description(self, slack_message, additional_details=""):
        """
        Generate a longer description of an incident including screenshots or links based on a Slack message using ChatGPT.

        Parameters:
        - slack_message (str): The Slack message containing initial details about the incident.
        - additional_details (str): Additional information, such as screenshots or links, to provide a comprehensive incident description.

        Returns:
        - incident_description (str): The generated incident description.
        """

        # Define the ChatGPT prompt
        prompt = f"Generate an incident description based on the following incident details from Slack:\n{slack_message}\n\nAdditional Details:\n{additional_details}\n"
        logger.info(f"Generating Incident Description from the following Slack message:\n{slack_message}\n")

        try:
            response = self.api.Completion.create(
                engine="gpt-3.5-turbo-instruct",
                prompt=prompt,
                max_tokens=500,  # Adjust the max_tokens as needed for the desired description length
                temperature=0.7,
                stop=None,
                n=1,
                timeout=60,  # Increase the timeout for longer descriptions
            )

            incident_description = response.choices[0].text.strip()
            return incident_description

        except Exception as error:
            logger.error(f"Error generating incident description: {error}")
            return None

    async def generate_incident_rca(self, slack_messages):
        """
        Generate an Incident Root Cause Analysis (RCA) based on a series of Slack messages using ChatGPT.

        Parameters:
        - slack_messages (list): A list of Slack messages containing details about the incident, its causes, and related information.

        Returns:
        - incident_rca (str): The generated Incident RCA.
        """

        # Combine all Slack messages into one string
        slack_message = "\n".join(slack_messages)

        # Define the ChatGPT prompt
        prompt = f"Generate an Incident RCA based on the following Incident Channel Slack messages:\n{slack_message}\n"
        logger.info(f"Generating Incident RCA from the following Incident Channel Slack messages:\n{slack_message}\n")

        try:
            response = self.api.Completion.create(
                engine="gpt-3.5-turbo-instruct",
                prompt=prompt,
                max_tokens=400,  # Adjust the max_tokens as needed for the desired RCA length
                temperature=0.7,
                stop=None,
                n=1,
                timeout=60,  # Increase the timeout for longer responses
            )

            incident_rca = response.choices[0].text.strip()
            return incident_rca

        except Exception as error:
            logger.error(f"Error generating Incident RCA: {error}")
            return None

    async def generate_immediate_actions(self, slack_messages):
        """
        Use ChatGPT to find immediate action items taken during an incident based on an incident channel Slack message.

        Parameters:
        - slack_message (str): The Slack message containing details about the incident, including immediate actions.

        Returns:
        - immediate_actions (list): A list of immediate action items taken during the incident.
        """

        # Combine all Slack messages into one string
        slack_message = "\n".join(slack_messages)

        prompt = f"Find immediate action items taken during the following incident based on incident channel Slack message:\n{slack_message}\n\nImmediate Actions:"

        try:
            response = self.api.Completion.create(
                engine="gpt-3.5-turbo-instruct",
                prompt=prompt,
                max_tokens=150,  # Adjust the max_tokens as needed for the desired RCA length
                temperature=0.7,
                stop=None,
                n=1,
                timeout=60,  # Increase the timeout for longer responses
            )

            incident_immediate_actions = response.choices[0].text.strip()
            return incident_immediate_actions

        except Exception as error:
            logger.error(f"Error generating Incident RCA: {error}")
            return None

    async def generate_preventive_actions(self, slack_messages):
        """
        Use ChatGPT to find preventive actions based on an incident channel Slack message.

        Parameters:
        - slack_message (str): The Slack message containing details about the incident, including preventive actions.

        Returns:
        - preventive_actions (list): A list of preventive actions to avoid similar incidents in the future.
        """

        # Combine all Slack messages into one string
        slack_message = "\n".join(slack_messages)

        prompt = f"Find preventive actions based on the following incident from the Slack channel message:\n{slack_message}\n\nPreventive Actions:"

        try:
            response = self.api.Completion.create(
                engine="gpt-3.5-turbo-instruct",
                prompt=prompt,
                max_tokens=200,  # Adjust the max_tokens as needed for the desired RCA length
                temperature=0.7,
                stop=None,
                n=1,
                timeout=60,  # Increase the timeout for longer responses
            )

            preventive_actions = response.choices[0].text.strip()
            return preventive_actions

        except Exception as error:
            logger.error(f"Error generating Incident RCA: {error}")
            return None

