import logging

from bot.models.pg import AuditLog, Session
from bot.shared import tools
from bot.slack.client import get_user_name
from sqlalchemy import update
from sqlalchemy.orm import scoped_session
from typing import Dict, List, Tuple

logger = logging.getLogger("audit")


def delete(
    incident_id: str,
    log: str,
    ts: str,
    database_session: scoped_session = Session,
) -> Tuple[bool, str]:
    """
    Delete from audit log
    """
    try:
        if (
            database_session.query(AuditLog)
            .filter_by(incident_id=incident_id)
            .all()
        ):
            try:
                existing_row = (
                    database_session.query(AuditLog)
                    .filter_by(incident_id=incident_id)
                    .one()
                )
                for log_obj in existing_row.data:
                    if log in log_obj.values() and ts in log_obj.values():
                        found = True
                        break
                    else:
                        found = False
                if found:
                    database_session.execute(
                        update(AuditLog)
                        .where(AuditLog.incident_id == incident_id)
                        .values(
                            data=[
                                i
                                for i in existing_row.data
                                if not (log in i.values() and ts in i.values())
                            ]
                        )
                    )
                    database_session.commit()
                    return True, "removed log entry"
                else:
                    return False, "log entry not found"
            except Exception as error:
                logger.error(
                    f"Audit log row lookup failed for incident {incident_id}: {error}"
                )
        else:
            logger.warning(f"No audit log record for {incident_id}")
            return False, "no incident found with that id"
    except Exception as error:
        logger.error(
            f"Audit log row lookup failed for incident {incident_id}: {error}"
        )
        return False, error
    finally:
        database_session.close()
        database_session.remove()


def read(
    incident_id: str, database_session: scoped_session = Session
) -> List[Dict]:
    """
    Read audit log
    """
    try:
        if (
            database_session.query(AuditLog)
            .filter_by(incident_id=incident_id)
            .all()
        ):
            try:
                existing_row = (
                    database_session.query(AuditLog)
                    .filter_by(incident_id=incident_id)
                    .one()
                )
                return existing_row.data
            except Exception as error:
                logger.error(
                    f"Audit log row lookup failed for incident {incident_id}: {error}"
                )
        else:
            logger.warning(f"No audit log record for {incident_id}")
    except Exception as error:
        logger.error(
            f"Audit log row lookup failed for incident {incident_id}: {error}"
        )
    finally:
        database_session.close()
        database_session.remove()


def write(
    incident_id: str,
    event: str,
    content: str = "",
    user: str = "",
    ts: str = "",
    database_session: scoped_session = Session,
):
    """
    Write an audit log for an incident

    Logs are appended to a JSON list
    """
    try:
        # Create the row if it doesn't exist
        if (
            not database_session.query(AuditLog)
            .filter_by(incident_id=incident_id)
            .all()
        ):
            try:
                row = AuditLog(incident_id=incident_id, data=[])
                database_session.add(row)
                database_session.commit()
            except Exception as error:
                logger.error(
                    f"Audit log row create failed for incident {incident_id}: {error}"
                )
        existing_row = (
            database_session.query(AuditLog)
            .filter_by(incident_id=incident_id)
            .one()
        )
        data = existing_row.data
        data.append(
            {
                "log": event,
                "user": get_user_name(user),
                "content": content,
                "ts": ts if ts != "" else tools.fetch_timestamp(),
            }
        )
        database_session.execute(
            update(AuditLog)
            .where(AuditLog.incident_id == incident_id)
            .values(data=data)
        )
        database_session.commit()
    except Exception as error:
        logger.error(
            f"Audit log row create failed for incident {incident_id}: {error}"
        )
        database_session.rollback()
    finally:
        database_session.close()
        database_session.remove()



def read_rca_created_event_content(
        incident_id: str, database_session: scoped_session = Session
) -> Dict:
    """
    Read audit log and filter for RCA CREATED event to extract content values.
    """
    try:
        audit_logs = (
            database_session.query(AuditLog)
            .filter_by(incident_id=incident_id)
            .all()
        )

        rca_event_log = {"rca_channel_id": ""}
        if not audit_logs:
            logger.debug(f"No audit log record for {incident_id}")
            return rca_event_log

        for log_entry in audit_logs:
            for event in log_entry.data:
                if event.get("log") == "RCA channel was created.":
                    rca_event_log = event
                    rca_event_log["rca_channel_id"] = event.get("content", "")
                    # rca_created_contents.append(event.get("content", ""))
        return rca_event_log

    except Exception as error:
        logger.error(f"Failed to read audit log of RCA channel was created for incident {incident_id}: {error}")
        return []
    finally:
        database_session.close()
        database_session.remove()