import logging
import json
import time

logger = logging.getLogger("api.demo")
from flask import Blueprint, jsonify, request, Response
from bot.models.incident import db_read_open_incidents_sorted

from bot.slack.client import ( send_custom_message, get_slack_users, get_channel_last_message)

# from flask_jwt_extended import jwt_required

demo = Blueprint("demo", __name__)

@demo.route("/demo-incident", methods=["GET"])
def demo_incident():
    try:
        hash_param = request.args.get('hash')
        # Check if the hash parameter is provided
        if not hash_param:
            return jsonify({"error": "Missing hash parameter"}), 400
        expected_hash = "aman_sachin_2024_octodemo"
        if hash_param != expected_hash:
            return jsonify({"error": "Invalid hash parameter"}), 403
        incidents = db_read_open_incidents_sorted(return_json=False, order_aesc=False)
        if not incidents or len(incidents) == 0:
            return jsonify({"error": "No Active incidents found"}), 404
        latest_incident_channel = incidents[0].channel_name;
        latest_incident_details = incidents[0];
        send_demo_messages(latest_incident_details);
        logger.info(f" Sending Demo Message on ${latest_incident_channel} ")
        return jsonify({"data": "Success" }), 200
    except Exception as error:
        return (
            jsonify({"error": str(error)}),
            500,
            {"ContentType": "application/json"},
        )



def send_demo_messages(latest_incident_details: dict = None):
    try:
        slack_users = get_slack_users(exclude_full_user_details = False);
        channel_message_cron(latest_incident_details, slack_users)

    except Exception as error:
        logger.error(f"Error while Sending Automated Demo Message ${error}")




def find_user_details(slack_users: list, user_name: str) -> dict:
    user_detail = {}
    for user in slack_users:
        if user["name"].lower() == user_name.lower():
            user_detail["user_id"] = user["id"]
            user_detail["profile_image"] = user["profile_image"]
            return  user_detail
    return None


def send_demo_messages_in_batch(latest_incident_details: dict = None, batch_message: any = None, slack_users: any = None):
    try:
        for message_data in batch_message:
            delay = int(message_data["delay"])
            time.sleep(delay)
            user_name = message_data["name"]
            message_content = message_data["message"]
            user_detail = find_user_details(slack_users, user_name)
            if user_detail:
                send_custom_message(channel_id=latest_incident_details.channel_id, user_id=user_detail["user_id"], message=message_content, username= user_name, icon_url = user_detail["profile_image"])
            else:
                logger.warning(f"User '{user_name}' not found in Slack users list.")
    except Exception as error:
        logger.error(f"Error while Sending Automated Demo Message ${error}")

def channel_message_cron(latest_incident_details: dict = None, slack_users: any = None):
    wait_message_demo = [
        {
            "wait_message": "has been assigned the *communications",
            "trigger_message": demo_message_phase1,
            "triggered": 0,
        },
        {
            "wait_message": "status has been changed to identified",
            "trigger_message": demo_message_phase2,
            "triggered": 0,
        },
        {
            "wait_message": "*authentication team escalation policy",
            "trigger_message": demo_message_phase3,
            "triggered": 0,
        },
        {
            "wait_message": "incident severity has been changed to sev3",
            "trigger_message": demo_message_phase4,
            "triggered": 0,
        },
        {
            "wait_message": "notification service api encountering a 422 status code",
            "trigger_message": demo_message_phase5,
            "triggered": 0,
        },
        {
            "wait_message": "*growth team escalation policy",
            "trigger_message": demo_message_phase6,
            "triggered": 0,
        },
        {
            "wait_message": "status has been changed to monitoring",
            "trigger_message": demo_message_phase7,
            "triggered": 0,
        },
        {
            "wait_message": "implement effective rate-limiting measures in our infrastructure",
            "trigger_message": demo_message_phase8,
            "triggered": 0,
        }
    ]
    start_time = time.time()
    max_duration = 15 * 60

    while time.time() - start_time < max_duration:
        last_channel_message = get_channel_last_message(latest_incident_details.channel_id)
        logger.info(f"last message in slack {last_channel_message.lower()} \n")
        for wait_message_data in wait_message_demo:
            wait_message = wait_message_data["wait_message"]
            trigger_messages=wait_message_data["trigger_message"]
            if last_channel_message.lower().find(wait_message) !=-1 and wait_message_data["triggered"] == 0:
                send_demo_messages_in_batch(latest_incident_details,trigger_messages,slack_users)
                wait_message_data["triggered"] = 1
                if trigger_messages == demo_message_phase8:
                    return
        time.sleep(10)  # Check every 30 seconds


demo_message_phase1 = [
    {
        "name": "Sachin",
        "message": f"Hello Team,\n\nI've observed a significant surge in the error rate for our notification service, with a failure percentage exceeding 85% across various channels such as WhatsApp, Email, SMS, and push notifications.\n\n<@U05T9BLKJ07>, could you please outline the business impact stemming from this outage in the notification service?",
        "delay": "0",
    },
    {
        "name": "Aman",
        "message": "We're experiencing a notable influx of support tickets, predominantly falling into the following categories: users unable to receive SMS OTP and email OTP, issues with order confirmation emails, and disruption in SMS and WhatsApp notifications reaching customers.",
        "delay": "5",
    },
    {
        "name": "Sachin",
        "message": "I'm currently investigating the Datadog dashboard and metrics to pinpoint the root cause of the errors. I'll provide updates shortly.\n\nAs checked in the notification service APM page, 70% of the request IDs are associated with events like promotions, ads, campaigns, payday.\n\nUpon reviewing the error logs pattern, we observed rate limit error messages for events such as promotion, ad, campaign, payday, authentication OTP, order confirmed, and order shipment.",
        "delay": "5",
    },
    {
        "name": "Aman",
        "message": "Since we have identified that ads campaigns can be the potential cause of the issue, we would be shifting the status of the incident as identified.",
        "delay": "2",
    }
]


demo_message_phase2 = [
    {
        "name": "Sachin",
        "message": "The error messages explicitly state that we have exceeded the API limits of our third-party provider due to ad events, resulting in the blocking of authentication and order notification messages.\n\nAdditionally, the approximate age of the oldest message events across all channels, particularly WhatsApp and email, has experienced a significant spike in minutes. This spike indicates a delay in processing messages, further contributing to the service degradation and potential customer impact.\n\n<@U05T9BLKJ07>, can you reach out to the Authentication Service Team to ascertain whether the ongoing outage is affecting the authentication service?",
        "delay": "5",
    }
]

demo_message_phase3 = [
    {
        "name": "Sachin",
        "message": "In the meantime, till we have someone from the Authentication Team, <@U05T9BLKJ07>, could you please elevate the severity of the incident? Your swift action on this matter is crucial.",
        "delay": "3",
    }
]

demo_message_phase4 = [
    {
        "name": "Michael",
        "message": "We've initiated an ongoing incident investigation related to the authentication service, specifically concerning users not receiving OTPs. \n\nThis issue stems from the notification service API encountering a 422 status code. Consequently, the login success rates have significantly decreased, as indicated by our metrics. Additionally, I was aware of an ongoing campaign event coinciding with the payday sale, potentially contributing to this situation.",
        "delay": "10",
    }
]

demo_message_phase5 = [
    {
        "name": "Sachin",
        "message": "It's evident that we're encountering rate-limit events across our messaging service providers, such as Gupshup and Twilio. \n\nThe current load on the notification service is 20 times higher than our typical peak business times. Presently, we have approximately 1 million messages enqueued in the queue, and the processing speed is relatively slow, leading to a high failure rate of 85%, prompting entries to be put into the queue.\n\nIt's worth noting that our default configuration allows for 5 retries, after which these messages will be directed to the dead letter queue.",
        "delay": "10"
    },
    {
        "name": "Michael",
        "message": "Now, regarding recent changes, did we enable any feature flag, or is there an ongoing campaign initiated by the growth team that caused this surge in traffic? \n\n<@U05T9BLKJ07>, can you page the Growth Team for escalating this incident?",
        "delay": "10",
    }
]

demo_message_phase6 = [
    {
        "name": "Rahul",
        "message": "We activated the feature flag earlier this evening, just a few hours before the incident, allowing us to send bulk notifications in batches of 1 million messages.\n\nThis might be the primary reason for the rate-limiting issues with the APIs. To address this, I propose disabling the feature flag and rolling back the campaign with a more conservative batch size. \n\nThis should help mitigate the strain on the messaging service providers and alleviate the rate-limiting problems we're currently facing.",
        "delay": "15",
    },
    {
        "name": "Mat",
        "message": "During the Payday sale, our extensive campaign overwhelmed the notification service, resulting in the observed issues.\n\nTo address this, we've proactively reduced the batch size to 10,000 temporarily. This adjustment aims to alleviate the strain on the system and allow for potential automatic recovery. Would you mind changing the Incident status to Monitoring",
        "delay": "10",
    },
]

demo_message_phase7 = [
    {
        "name": "Sachin",
        "message": "I’ve observed that the load on the notification service has returned to normal, and the error rate has significantly reduced.\n\nHowever, considering that we use the same topic for both promotional and crucial notifications, such as order updates and authentications, I propose breaking them into subtopics.\n\nThis will serve as an action item to enhance our scalability and implement effective rate-limiting measures in our infrastructure. <@U05T9BLKJ07>, would you mind creating the action item for this purpose?",
        "delay": "10",
    },
]

demo_message_phase8 = [
    {
        "name": "Rahul",
        "message": "The order notifications are currently in the processing phase, and we anticipate that it will take an additional 5 minutes to complete the processing of all messages from the queues.",
        "delay": "45",
    },
    {
        "name": "Michael",
        "message": "The error rate in the Authentication Service has returned to normal levels, and I can confirm that the delivery of OTP across all channels has been restored to normal.",
        "delay": "10",
    },
    {
        "name": "Sachin",
        "message": "Now that the system has successfully recovered, our next step is to parse the messages from the dead letter queue.\n\nWe’ll be focusing on sending the missing notifications related to previous orders and other crucial updates.",
        "delay": "5",
    }
]

demo_messages = [
    {
        "name": "Sachin",
        "message": f"Hello Team,\n\nI've observed a significant surge in the error rate for our notification service, with a failure percentage exceeding 85% across various channels such as WhatsApp, Email, SMS, and push notifications.\n\n<@U05T9BLKJ07>, could you please outline the business impact stemming from this outage in the notification service?"
    },
    {
        "name": "Aman",
        "message": "We're experiencing a notable influx of support tickets, predominantly falling into the following categories: users unable to receive SMS OTP and email OTP, issues with order confirmation emails, and disruption in SMS and WhatsApp notifications reaching customers."
    },
    {
        "name": "Sachin",
        "message": "I'm currently investigating the Datadog dashboard and metrics to pinpoint the root cause of the errors. I'll provide updates shortly.\n\nAs checked in the notification service APM page, 70% of the request IDs are associated with events like promotions, ads, campaigns, payday.\n\nUpon reviewing the error logs pattern, we observed rate limit error messages for events such as promotion, ad, campaign, payday, authentication OTP, order confirmed, and order shipment."
    },
    {
        "name": "Aman",
        "message": "Since we have identified that ads campaigns can be the potential cause of the issue, we would be shifting the status of the incident as identified."
    },
    {
        "name": "Sachin",
        "message": "The error messages explicitly state that we have exceeded the API limits of our third-party provider due to ad events, resulting in the blocking of authentication and order notification messages.\n\nAdditionally, the approximate age of the oldest message events across all channels, particularly WhatsApp and email, has experienced a significant spike in minutes. This spike indicates a delay in processing messages, further contributing to the service degradation and potential customer impact.\n\n<@U05T9BLKJ07>, can you reach out to the Authentication Service Team to ascertain whether the ongoing outage is affecting the authentication service?"
    },
    {
        "name": "Sachin",
        "message": "In the meantime, till we have someone from the Authentication Team, <@U05T9BLKJ07>, could you please elevate the severity of the incident? Your swift action on this matter is crucial."
    },
    {
        "name": "Michael",
        "message": "We've initiated an ongoing incident investigation related to the authentication service, specifically concerning users not receiving OTPs. \n\nThis issue stems from the notification service API encountering a 422 status code. Consequently, the login success rates have significantly decreased, as indicated by our metrics. Additionally, I was aware of an ongoing campaign event coinciding with the payday sale, potentially contributing to this situation."
    },
    {
        "name": "Sachin",
        "message": "It's evident that we're encountering rate-limit events across our messaging service providers, such as Gupshup and Twilio. \n\nThe current load on the notification service is 20 times higher than our typical peak business times. Presently, we have approximately 1 million messages enqueued in the queue, and the processing speed is relatively slow, leading to a high failure rate of 85%, prompting entries to be put into the queue.\n\nIt's worth noting that our default configuration allows for 5 retries, after which these messages will be directed to the dead letter queue."
    },
    {
        "name": "Michael",
        "message": "Now, regarding recent changes, did we enable any feature flag, or is there an ongoing campaign initiated by the growth team that caused this surge in traffic? \n\n<@U05T9BLKJ07>, can you page the Growth Team for escalating this incident?"
    },
    {
        "name": "Rahul",
        "message": "We activated the feature flag earlier this evening, just a few hours before the incident, allowing us to send bulk notifications in batches of 1 million messages.\n\nThis might be the primary reason for the rate-limiting issues with the APIs. To address this, I propose disabling the feature flag and rolling back the campaign with a more conservative batch size. \n\nThis should help mitigate the strain on the messaging service providers and alleviate the rate-limiting problems we're currently facing."
    },
    {
        "name": "Mat",
        "message": "During the Payday sale, our extensive campaign overwhelmed the notification service, resulting in the observed issues.\n\nTo address this, we've proactively reduced the batch size to 10,000 temporarily. This adjustment aims to alleviate the strain on the system and allow for potential automatic recovery."
    },
    {
        "name": "Sachin",
        "message": "I’ve observed that the load on the notification service has returned to normal, and the error rate has significantly reduced.\n\nHowever, considering that we use the same topic for both promotional and crucial notifications, such as order updates and authentications, I propose breaking them into subtopics.\n\nThis will serve as an action item to enhance our scalability and implement effective rate-limiting measures in our infrastructure. <@U05T9BLKJ07>, would you mind creating the action item for this purpose?"
    },
    {
        "name": "Rahul",
        "message": "The order notifications are currently in the processing phase, and we anticipate that it will take an additional 5 minutes to complete the processing of all messages from the queues."
    },
    {
        "name": "Michael",
        "message": "The error rate in the Authentication Service has returned to normal levels, and I can confirm that the delivery of OTP across all channels has been restored to normal."
    },
    {
        "name": "Sachin",
        "message": "Now that the system has successfully recovered, our next step is to parse the messages from the dead letter queue.\n\nWe’ll be focusing on sending the missing notifications related to previous orders and other crucial updates."
    }
]