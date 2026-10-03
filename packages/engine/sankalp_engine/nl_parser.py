"""Natural Language Query Parser for SANKALP Transit Recovery.

Extracts structured journey parameters from conversational user input:
- Origin and Destination transit nodes (resolved dynamically via TransportDataSource)
- Arrival deadline (relative or clock time)
- Maximum budget constraint
- Delay context / train status (e.g. delayed by X hours, cancelled)

Design Principle:
- 100% generic syntactic entity parsing.
- ZERO hardcoded place names (conforms strictly to AST guard).
- All transit node resolution is delegated to TransportDataSource.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional
from .datasource import TransportDataSource
from .models import IST, Place


@dataclass(frozen=True)
class ParsedJourneyQuery:
    """Structured representation of a natural language recovery query."""

    raw_query: str
    origin: Optional[Place]
    destination: Optional[Place]
    deadline: Optional[datetime]
    budget_paise: Optional[int]
    budget_inr: Optional[int]
    injected_delay_minutes: Optional[float]
    is_cancellation: bool
    confidence_score: float
    explanation: str

    def to_dict(self) -> dict:
        return {
            "raw_query": self.raw_query,
            "origin": self.origin.to_dict() if self.origin else None,
            "destination": self.destination.to_dict() if self.destination else None,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "budget_paise": self.budget_paise,
            "budget_inr": self.budget_inr,
            "injected_delay_minutes": self.injected_delay_minutes,
            "is_cancellation": self.is_cancellation,
            "confidence_score": self.confidence_score,
            "explanation": self.explanation,
        }


class NaturalLanguageQueryParser:
    """Parses free-form journey disruption queries into structured parameters."""

    def __init__(self, data_source: TransportDataSource) -> None:
        self.ds = data_source

    def parse(self, text: str, reference_time: Optional[datetime] = None) -> ParsedJourneyQuery:
        """Parse natural language query text into structured query model."""
        now = reference_time or datetime.now(IST)
        cleaned = text.strip()

        # 1. Detect cancellation keywords
        is_cancellation = bool(re.search(r"\b(cancelled|canceled|diverted|broken)\b", cleaned, re.IGNORECASE))

        # 2. Extract delay if mentioned (e.g. "delayed by 3 hours", "late by 45 mins")
        injected_delay_minutes: Optional[float] = None
        delay_match = re.search(
            r"\b(?:delayed|late|delay of)\s+(?:by\s+)?(\d+(?:\.\d+)?)\s*(hours?|hrs?|h|minutes?|mins?|m)\b",
            cleaned,
            re.IGNORECASE,
        )
        if delay_match:
            qty = float(delay_match.group(1))
            unit = delay_match.group(2).lower()
            if "h" in unit:
                injected_delay_minutes = qty * 60.0
            else:
                injected_delay_minutes = qty

        # 3. Extract Budget (e.g. "under 2000 rupees", "budget 5000", "₹1,500", "under 3000")
        budget_paise: Optional[int] = None
        budget_inr: Optional[int] = None
        budget_match = re.search(
            r"(?:under|budget|max|within|limit of|₹|rs\.?|inr)\s*(\d+(?:,\d+)?)\s*(?:rupees|rs|inr)?\b",
            cleaned,
            re.IGNORECASE,
        )
        if not budget_match:
            # Fallback for ₹5000 or 5000 inr without prefix
            budget_match = re.search(r"[₹]\s*(\d+(?:,\d+)?)\b", cleaned)

        if budget_match:
            num_str = budget_match.group(1).replace(",", "")
            budget_inr = int(num_str)
            budget_paise = budget_inr * 100

        # 4. Extract Deadline (e.g. "by 8 PM", "before 6:30 pm", "reach by 20:00", "today 9 pm")
        deadline: Optional[datetime] = None
        # Priority A: Explicit clock time with AM/PM (e.g. "8 PM", "by 8:30 pm", "reach by 9 am")
        time_match = re.search(
            r"\b(?:by|before|reach by|arrive by)?\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b",
            cleaned,
            re.IGNORECASE,
        )
        if not time_match:
            # Priority B: 24h or relative clock time, strictly excluding duration units (hours, mins)
            time_match = re.search(
                r"\b(?:reach by|arrive by|before)\s+(\d{1,2})(?::(\d{2}))?(?!\s*(?:hours?|hrs?|h|mins?|minutes?))\b",
                cleaned,
                re.IGNORECASE,
            )

        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2)) if time_match.group(2) else 0
            meridiem = time_match.group(3).lower() if time_match.group(3) else None

            if meridiem == "pm" and hour < 12:
                hour += 12
            elif meridiem == "am" and hour == 12:
                hour = 0

            # Target today at that hour/min
            cand_deadline = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if cand_deadline <= now:
                # If target clock time is already in the past, interpret as tomorrow
                cand_deadline += timedelta(days=1)
            deadline = cand_deadline
        else:
            # Default fallback: 18 hours from reference time
            deadline = now + timedelta(hours=18)

        # 5. Extract Origin and Destination
        # Generic patterns for transit corridors:
        # Pattern A: "from <ORIGIN> to <DESTINATION>"
        # Pattern B: "<ORIGIN> to <DESTINATION>"
        origin_place: Optional[Place] = None
        dest_place: Optional[Place] = None

        route_match = re.search(
            r"\b(?:from|leaving|departing|at)\s+([A-Za-z\s]+?)\s+(?:to|heading to|towards|for)\s+([A-Za-z\s]+?)(?:,|\.|\s+(?:is|was|must|before|by|under|budget|delayed|due)|$)",
            cleaned,
            re.IGNORECASE,
        )

        if not route_match:
            # Try simpler "X to Y"
            route_match = re.search(
                r"\b([A-Za-z\s]{3,25})\s+(?:to|->)\s+([A-Za-z\s]{3,25})(?:,|\.|\s+(?:is|was|must|before|by|under|budget|delayed)|$)",
                cleaned,
                re.IGNORECASE,
            )

        if route_match:
            raw_orig = route_match.group(1).strip()
            raw_dest = route_match.group(2).strip()

            # Clean punctuation and common noise words
            noise_words = {"my", "the", "train", "flight", "trip", "stuck", "in", "currently"}
            orig_tokens = [t for t in raw_orig.split() if t.lower() not in noise_words]
            dest_tokens = [t for t in raw_dest.split() if t.lower() not in noise_words]

            cleaned_orig = " ".join(orig_tokens)
            cleaned_dest = " ".join(dest_tokens)

            # Query data source for candidate transit hubs
            if cleaned_orig:
                orig_candidates = self.ds.search_places(cleaned_orig, limit=1)
                if orig_candidates:
                    origin_place = orig_candidates[0]

            if cleaned_dest:
                dest_candidates = self.ds.search_places(cleaned_dest, limit=1)
                if dest_candidates:
                    dest_place = dest_candidates[0]

        # Calculate confidence score based on resolved slots
        confidence = 0.0
        explanations = []

        if origin_place:
            confidence += 0.35
            explanations.append(f"Origin resolved to {origin_place.name} ({origin_place.code})")
        else:
            explanations.append("Could not resolve departure origin")

        if dest_place:
            confidence += 0.35
            explanations.append(f"Destination resolved to {dest_place.name} ({dest_place.code})")
        else:
            explanations.append("Could not resolve arrival destination")

        if deadline:
            confidence += 0.15
            explanations.append(f"Deadline set to {deadline.strftime('%I:%M %p')}")

        if budget_inr:
            confidence += 0.15
            explanations.append(f"Budget capped at ₹{budget_inr}")

        return ParsedJourneyQuery(
            raw_query=text,
            origin=origin_place,
            destination=dest_place,
            deadline=deadline,
            budget_paise=budget_paise,
            budget_inr=budget_inr,
            injected_delay_minutes=injected_delay_minutes,
            is_cancellation=is_cancellation,
            confidence_score=round(confidence, 2),
            explanation="; ".join(explanations),
        )
