# app/services/attendance_resolver.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.schemas.attendance import AttendanceSummary
from app.services.graph_client import GraphClient, GraphClientError


class AttendanceResolver:
    """
    Resolves attendance information for a given meeting using Microsoft Graph.

    This implementation assumes the presence of online meeting attendance reports
    under the communications API, e.g.:

        GET /v1.0/communications/onlineMeetings/{meeting_id}/attendanceReports

    The exact endpoint and payload shape can be adjusted later without changing
    the evaluator logic, thanks to this abstraction.
    """

    def __init__(self, graph_client: GraphClient) -> None:
        self.graph = graph_client

    async def resolve_attendance(self, meeting_id: str) -> AttendanceSummary:
        """
        Resolve attendance metrics for the given meeting.

        Returns
        -------
        AttendanceSummary
            Normalized attendance information. If Graph is unreachable or no
            attendance data exists yet, has_data will be False and counts will
            default to zero.
        """
        try:
            payload = await self._fetch_attendance_reports(meeting_id)
        except GraphClientError as exc:
            # Graph failure => no data, but we keep the error message in `raw`
            return AttendanceSummary(
                meeting_id=meeting_id,
                non_organizer_count=0,
                duration_minutes=0.0,
                has_data=False,
                raw={"error": str(exc)},
            )

        reports = payload.get("value", [])
        if not reports:
            return AttendanceSummary(
                meeting_id=meeting_id,
                non_organizer_count=0,
                duration_minutes=0.0,
                has_data=False,
                raw=payload,
            )

        report = reports[0]
        records = report.get("attendanceRecords", [])

        non_org_count, duration_minutes = self._compute_metrics(records)

        return AttendanceSummary(
            meeting_id=meeting_id,
            non_organizer_count=non_org_count,
            duration_minutes=duration_minutes,
            has_data=True,
            raw=payload,
        )

    async def _fetch_attendance_reports(self, meeting_id: str) -> Dict[str, Any]:
        """
        Calls the Graph endpoint to retrieve attendance reports for the meeting.
        """
        path = f"/v1.0/communications/onlineMeetings/{meeting_id}/attendanceReports"
        return await self.graph.get_json(path)

    def _compute_metrics(self, records: List[Dict[str, Any]]) -> tuple[int, float]:
        """
        Compute non-organizer count and approximate total meeting duration.

        Rules
        -----
        - A participant is counted as non-organizer if:
          role != 'Organizer' AND totalAttendanceInSeconds > 0
        - Duration is computed as:
          (max(leaveDateTime) - min(joinDateTime)) across all records that have
          both join and leave timestamps.
        - If join/leave timestamps are missing, duration is 0.0.
        """
        non_org_count = 0

        join_times: List[datetime] = []
        leave_times: List[datetime] = []

        for rec in records:
            role = (rec.get("role") or "").lower()
            total_secs = rec.get("totalAttendanceInSeconds") or 0

            if role != "organizer" and total_secs > 0:
                non_org_count += 1

            j_raw = rec.get("joinDateTime")
            l_raw = rec.get("leaveDateTime")

            if j_raw:
                jt = self._parse_iso_utc(j_raw)
                if jt is not None:
                    join_times.append(jt)

            if l_raw:
                lt = self._parse_iso_utc(l_raw)
                if lt is not None:
                    leave_times.append(lt)

        duration_minutes = 0.0
        if join_times and leave_times:
            start = min(join_times)
            end = max(leave_times)
            delta = end - start
            duration_minutes = max(delta.total_seconds() / 60.0, 0.0)

        return non_org_count, duration_minutes

    def _parse_iso_utc(self, value: str) -> Optional[datetime]:
        """
        Parse an ISO-8601 datetime string and normalize to UTC.

        Returns None if parsing fails.
        """
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)