# app/services/meeting_resolver.py
from datetime import datetime, timedelta, timezone, date as date_type
from typing import Optional

from app.schemas.meeting import MeetingOccurrence
from app.services.graph_client import GraphClient, GraphClientError


class GraphMeetingResolver:
    """
    Resolves the actual meeting occurrence for a given project/date.

    - Finds the event instance on Graph for the given date.
    - Handles cancelled occurrences.
    - Extracts start/end timestamps.
    """

    def __init__(self, graph_client: GraphClient, organizer_user_id: str):
        """
        Parameters
        ----------
        graph_client:
            Shared Graph client instance.
        organizer_user_id:
            The user ID/email of the meeting organizer to query events from.
            (Will be moved to DB when integrating fully.)
        """
        self.graph = graph_client
        self.organizer_user_id = organizer_user_id

    async def resolve_meeting_occurrence(
        self,
        meeting_id: str,
        standup_date: date_type,
    ) -> MeetingOccurrence:
        """
        Resolve the specific occurrence of a recurring meeting for the given date.
        """
        try:
            meeting = await self._fetch_occurrence(meeting_id, standup_date)
        except GraphClientError as exc:
            # Graph failure => no occurrence, but embed error info
            return MeetingOccurrence(
                meeting_id=meeting_id,
                start_time_utc=None,
                end_time_utc=None,
                is_cancelled=False,
                raw={"error": str(exc)},
            )

        if meeting is None:
            # No occurrence found => treat as NO_DATA
            return MeetingOccurrence(
                meeting_id=meeting_id,
                start_time_utc=None,
                end_time_utc=None,
                is_cancelled=False,
                raw=None,
            )

        is_cancelled = bool(meeting.get("isCancelled", False))
        start_raw = meeting.get("start", {})
        end_raw = meeting.get("end", {})

        start_utc = None
        end_utc = None

        if "dateTime" in start_raw:
            start_utc = self._parse_graph_datetime(start_raw)
        if "dateTime" in end_raw:
            end_utc = self._parse_graph_datetime(end_raw)

        return MeetingOccurrence(
            meeting_id=meeting_id,
            start_time_utc=start_utc,
            end_time_utc=end_utc,
            is_cancelled=is_cancelled,
            raw=meeting,
        )

    async def _fetch_occurrence(
        self, meeting_id: str, standup_date: date_type
    ) -> Optional[dict]:
        """
        Searches the organizer's events for any instance matching the meeting_id.
        """
        day_start = datetime.combine(standup_date, datetime.min.time()).astimezone(timezone.utc)
        day_end = day_start + timedelta(days=1)

        path = f"/v1.0/users/{self.organizer_user_id}/calendarView"
        params = {
            "startDateTime": day_start.isoformat(),
            "endDateTime": day_end.isoformat(),
        }

        payload = await self.graph.get_json(path, params=params)

        events = payload.get("value", [])

        for ev in events:
            if ev.get("id") == meeting_id or ev.get("onlineMeetingId") == meeting_id:
                return ev

        return None

    def _parse_graph_datetime(self, dt_obj: dict) -> datetime:
        """
        Converts Graph datetime JSON into aware UTC datetime.
        """
        dt_str = dt_obj["dateTime"]
        tz = dt_obj.get("timeZone", "UTC")
        dt = datetime.fromisoformat(dt_str)
        if dt.tzinfo is None:
            # Assume timezone provided
            dt = dt.replace(tzinfo=timezone.utc if tz == "UTC" else None)
        return dt.astimezone(timezone.utc)