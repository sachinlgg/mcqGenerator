import logging
import openai
import config
import asyncio
import json

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

    def test_tickets(self) -> bool:
        try:
            actions_items = [
                "Disable Ad Campaign Feature Flag: The feature flag allowing bulk notifications was promptly disabled, and the campaign was rolled back to a more conservative batch size of 10,000 messages. This measure aimed to mitigate strain on messaging service providers and alleviate rate-limiting issues.",
                "Retrieve Events from Dead Letter Queue: Immediately initiate the process to retrieve events from the dead letter queue, focusing on failed order notifications and other critical updates that were not successfully processed during the outage period."
            ]

            expected_output = [
                {
                    "description": "The feature flag allowing bulk notifications was promptly disabled, and the campaign was rolled back to a more conservative batch size of 10,000 messages. This measure aimed to mitigate strain on messaging service providers and alleviate rate-limiting issues.",
                    "summary": "Disable Ad Campaign Feature Flag"
                },
                {
                    "description": "Immediately initiate the process to retrieve events from the dead letter queue, focusing on failed order notifications and other critical updates that were not successfully processed during the outage period.",
                    "summary": "Retrieve Events from Dead Letter Queue"
                }
            ]

            # Instantiate the class and call the function
            result = asyncio.run(self.generate_actions_item_jira_tickets(actions_items))

            # Compare the result with the expected output
            logger.info(f"Test Auto Generation of Action Items for GPT Jira is working")
            return result == expected_output
        except Exception as error:
            logger.error(f"Test failed for Auto Generation of Action Items: {error}")
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

    async def generate_catch_me_on_incident(self, slack_message):
        """
        Generate a catch me up on incident based on a Slack message using ChatGPT.

        Parameters:
        - slack_message (str): The Slack message containing details about the incident.

        Returns:
        - catch_me_on_incident (str): The generated catch me on incident.
        """

        # Define the ChatGPT prompt
        prompt = f"Could you please give me an update on the incident ? Include the current context and a brief summary of what's happened so far based on the following incidents channel slack messages :\n{slack_message}\n"
        logger.info(f"Generate catch me up on incident from the following slack message : \n {slack_message} \n")

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

            catch_me_on_incident = response.choices[0].text.strip()
            return catch_me_on_incident

        except Exception as error:
            logger.error(f"Error generating catch me up on incident: {error}")
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

    async def generate_incident_rca(self, slack_message):
        """
        Generate an Incident Root Cause Analysis (RCA) based on a series of Slack messages using ChatGPT.

        Parameters:
        - slack_messages (list): A list of Slack messages containing details about the incident, its causes, and related information.

        Returns:
        - incident_rca (str): The generated Incident RCA.
        """

        # Combine all Slack messages into one string
        

        # Define the ChatGPT prompt
        prompt = f"Generate an Incident RCA based on the following Incident Channel Slack messages:\n{slack_message}\n\n"
        logger.info(f"Generating Incident RCA from the following Incident Channel Slack messages:\n{slack_message}\n\n")

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

    async def generate_immediate_actions(self, slack_message):
        """
        Use ChatGPT to find immediate action items taken during an incident based on an incident channel Slack message.

        Parameters:
        - slack_message (str): The Slack message containing details about the incident, including immediate actions.

        Returns:
        - immediate_actions (list): A list of immediate action items taken during the incident.
        """

        # Combine all Slack messages into one string
        

        prompt = f"Find immediate action items taken during the following incident based on incident channel Slack message:\n{slack_message}\n\nImmediate Actions:"

        try:
            response = self.api.Completion.create(
                engine="gpt-3.5-turbo-instruct",
                prompt=prompt,
                max_tokens=500,  # Adjust the max_tokens as needed for the desired RCA length
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


    async def generate_actions_item_jira_tickets(self, action_items):
        """
        Use ChatGPT to create Jira tickets from immediate action items list .

        Parameters:
        - action_items (str): A list of action items taken during the incident.

        Returns:
        - jira_ticket_contract (list): A list of immediate action items taken during the incident in contract of Jira.
        """


        jira_ticket_contract = []
        
        example_shot = """
            Immediate Actions:

 ['Reduce the cpu memory from the instance: Given the instance's unused memory, optimizing its CPU allocation can yield cost savings. By aligning resources with actual usage, we ensure efficient spending. This approach maintains performance while reducing unnecessary expenses.', 'Enable autoscaling of Database: We need to use increase the number of secondary node from 5 to 7.'] 

Create the above Immediate Action Items in list of JSON where below is the JSON format:
[
  {
    "description": "",
    "summary": ""
  }
]

OUTPUT:
[
  {
    "description": "Reduce the cpu memory from the instance",
    "summary": "Given the instance's unused memory, optimizing its CPU allocation can yield cost savings. By aligning resources with actual usage, we ensure efficient spending. This approach maintains performance while reducing unnecessary expenses."
  },
  {
    "description": "Enable autoscaling of Database",
    "summary": "We need to use increase the number of secondary node from 5 to 7."
  }
]
        """
        action_items_str = f'Immediate Actions:\n\n {action_items} \n\n'
        prompt = action_items_str + 'Create the above Immediate Action Items in list of JSON where below is the JSON format: :\n[\n  {\n    "description": "",\n    "summary": ""\n  }\n]] \n\nOUTPUT: \n'
        

        prompt = example_shot + '\n\n' + prompt
        

        try:
            response = self.api.Completion.create(
                engine="gpt-3.5-turbo-instruct",
                prompt=prompt,
                max_tokens=1000,  # Adjust the max_tokens as needed for the desired RCA length
                temperature=0.7,
                stop=None,
                n=1,
                timeout=60,  # Increase the timeout for longer responses
            )

            incident_actions_items_jira_tickets = response.choices[0].text.strip()
            logger.info(f"Formatting of Action Item ticket response : {incident_actions_items_jira_tickets}")
            try:
                incident_actions_items_jira_tickets_json = json.loads(incident_actions_items_jira_tickets)
            except json.JSONDecodeError:
                logger.error("Response is not in valid JSON format")
                return jira_ticket_contract

            for action_item_ticket in incident_actions_items_jira_tickets_json:
                # Interchanging the contract as summary is longer in depth details and decription is smaller one.
                # Continue to the next item if either description or summary is blank
                description = action_item_ticket.get("summary", "")
                summary = action_item_ticket.get("description", "")
                if not description or not summary:
                    continue
                jira_ticket_contract.append({
                    "description": description,
                    "summary": summary
                })

            return jira_ticket_contract

        except Exception as error:
            logger.error(f"Error generating Action Item Jira Tickets : {error}")
            return jira_ticket_contract

    async def generate_preventive_actions(self, slack_message):
        """
        Use ChatGPT to find preventive actions based on an incident channel Slack message.

        Parameters:
        - slack_message (str): The Slack message containing details about the incident, including preventive actions.

        Returns:
        - preventive_actions (list): A list of preventive actions to avoid similar incidents in the future.
        """

        # Combine all Slack messages into one string

        prompt = f"Find preventive actions based on the following incident from the Slack channel message:\n{slack_message}\n\nPreventive Actions:"

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

            preventive_actions = response.choices[0].text.strip()
            return preventive_actions

        except Exception as error:
            logger.error(f"Error generating Incident RCA: {error}")
            return None

