"""Identity Matcher for ANDRO-Vision Custom Objects & People."""

import json
import logging
from dataclasses import dataclass
from typing import Any
import numpy as np

from .extractor import cosine_similarity

logger = logging.getLogger(__name__)

@dataclass
class MatchResult:
    matched: bool
    identity_id: str | None
    identity_name: str
    object_class: str
    category: str
    confidence: float  # 0.0 to 1.0 (e.g. 0.91 = 91%)
    is_person: bool
    status_label: str  # e.g. "White Toyota Harrier", "Unknown Vehicle", "Unknown Person"
    best_reference_id: str | None = None

class IdentityMatcher:
    """
    Compares candidate feature embeddings against registered reference profiles.
    Strictly preserves class-identity separation and local privacy rules.
    """

    DEFAULT_OBJECT_THRESHOLD = 0.76
    DEFAULT_PERSON_THRESHOLD = 0.82

    def __init__(self, object_threshold: float = DEFAULT_OBJECT_THRESHOLD, person_threshold: float = DEFAULT_PERSON_THRESHOLD):
        self.object_threshold = object_threshold
        self.person_threshold = person_threshold

    def match(
        self,
        candidate_embedding: np.ndarray,
        object_class: str,
        enrolled_identities: list[dict[str, Any]],
    ) -> MatchResult:
        """
        Match a candidate embedding against all enrolled identities.

        Args:
            candidate_embedding: 192-D feature vector from crop.
            object_class: Detected class (e.g., 'car', 'person', 'dog', 'motorcycle').
            enrolled_identities: List of identity dicts containing metadata and parsed reference embeddings.
        """
        is_person = object_class.lower() == "person"
        threshold = self.person_threshold if is_person else self.object_threshold
        
        default_unknown_name = "Unknown Person" if is_person else f"Unknown {object_class.capitalize()}"

        if candidate_embedding is None or len(enrolled_identities) == 0:
            return MatchResult(
                matched=False,
                identity_id=None,
                identity_name=default_unknown_name,
                object_class=object_class,
                category="person" if is_person else "object",
                confidence=0.0,
                is_person=is_person,
                status_label=default_unknown_name,
            )

        best_score = 0.0
        best_identity = None
        best_ref_id = None

        candidate_norm = np.asarray(candidate_embedding, dtype=np.float32).flatten()

        for identity in enrolled_identities:
            # Match only compatible object classes
            id_class = identity.get("object_class", "").lower()
            if id_class and id_class != object_class.lower():
                # Allow vehicle cross-matching (e.g., car / truck / bus) if specified in category
                if identity.get("category", "").lower() == "vehicle" and object_class.lower() in ("car", "truck", "bus", "van", "suv"):
                    pass
                else:
                    continue

            # Privacy rule: Only check person identities for person detections
            if is_person and not identity.get("is_person", False):
                continue
            if not is_person and identity.get("is_person", False):
                continue

            # Check all reference embeddings for this identity (multi-reference support)
            ref_embeddings = identity.get("reference_embeddings", [])
            for ref in ref_embeddings:
                ref_vec = ref.get("embedding")
                if ref_vec is None:
                    continue
                score = cosine_similarity(candidate_norm, ref_vec)
                if score > best_score:
                    best_score = score
                    best_identity = identity
                    best_ref_id = ref.get("id")

        if best_identity and best_score >= threshold:
            confidence_pct = round(best_score * 100, 1)
            logger.debug(
                "Matched %s to identity '%s' with %.1f%% confidence (threshold: %.1f%%)",
                object_class,
                best_identity["name"],
                confidence_pct,
                threshold * 100,
            )
            return MatchResult(
                matched=True,
                identity_id=best_identity["id"],
                identity_name=best_identity["name"],
                object_class=object_class,
                category=best_identity.get("category", "object"),
                confidence=best_score,
                is_person=best_identity.get("is_person", False),
                status_label=f"{best_identity['name']} ({confidence_pct}%)",
                best_reference_id=best_ref_id,
            )

        # Below threshold -> designate as Unknown
        return MatchResult(
            matched=False,
            identity_id=None,
            identity_name=default_unknown_name,
            object_class=object_class,
            category="person" if is_person else "object",
            confidence=best_score,
            is_person=is_person,
            status_label=default_unknown_name,
        )
