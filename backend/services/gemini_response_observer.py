"""
파일명: gemini_response_observer.py
작성자: Codex
설명: Gemini 응답 파싱, 요약 생성, 진단 메시지 생성을 담당한다.
상위 모듈: backend.services.gemini_image_service
하위 모듈: 없음
"""


from __future__ import annotations
import re
from typing import Protocol, TypedDict


SUMMARY_SCHEMA_VERSION = "gemini-response-summary.v1"
NO_INLINE_REASON_BLOCKED = "BLOCKED"
NO_INLINE_REASON_NO_CANDIDATE = "NO_CANDIDATE"
NO_INLINE_REASON_NO_IMAGE_PART = "NO_IMAGE_PART"
NO_INLINE_REASON_UNKNOWN = "UNKNOWN"
MAX_TEXT_LENGTH = 500
MAX_CANDIDATES_IN_SUMMARY = 10
MAX_CANDIDATES_IN_ERROR = 10

# NOTE: 관측성 로그에 민감 문자열이 남지 않도록 최소 마스킹 규칙을 적용한다.
EMAIL_PATTERN = re.compile(r"([A-Za-z0-9._%+-])([A-Za-z0-9._%+-]*)(@[A-Za-z0-9.-]+\\.[A-Za-z]{2,})")
GOOGLE_API_KEY_PATTERN = re.compile(r"AIza[0-9A-Za-z_-]{35}")


class GeminiResponseLike(Protocol):
    """Gemini 응답 객체의 최소 접근 계약."""

    candidates: object
    prompt_feedback: object


class SerializedSafetyRating(TypedDict, total=False):
    """safety_ratings 직렬화 항목."""

    category: str
    probability: str
    blocked: str


class PromptFeedbackSummary(TypedDict):
    """prompt_feedback 요약 스키마."""

    block_reason: str
    block_reason_message: str
    safety_ratings: list[SerializedSafetyRating]


class CandidateSummary(TypedDict):
    """candidate 요약 스키마."""

    finish_reason: str
    safety_ratings: list[SerializedSafetyRating]
    has_inline_image: bool
    text: str


class ResponseSummary(TypedDict):
    """응답 요약 스키마."""

    schema_version: str
    candidate_count: int
    candidates_truncated: bool
    prompt_feedback: PromptFeedbackSummary
    candidates: list[CandidateSummary]


class GeminiResponseObserver:
    """Gemini 응답 관측성 유틸리티."""

    def extract_first_image_bytes(self, response: GeminiResponseLike) -> bytes | None:
        """
        응답 후보 목록에서 첫 번째 inline image 바이트를 추출한다.
        Args:
            response: GeminiResponseLike: generate_content 응답 객체.
        Returns:
            bytes | None: 발견된 이미지 바이트. 없으면 None.
        """
        for candidate in self._iter_candidates(response):
            for part in self._iter_parts(candidate):
                inline_data = getattr(part, "inline_data", None)
                if inline_data and getattr(inline_data, "data", None):
                    data = getattr(inline_data, "data", None)
                    if isinstance(data, bytes):
                        return data
        return None

    def classify_no_inline_reason(self, response: GeminiResponseLike) -> str:
        """
        inline 이미지 부재 원인을 코드로 분류한다.
        Args:
            response: GeminiResponseLike: generate_content 응답 객체.
        Returns:
            str: BLOCKED/NO_CANDIDATE/NO_IMAGE_PART/UNKNOWN 중 하나.
        """
        candidates = self._iter_candidates(response)
        if not candidates:
            return NO_INLINE_REASON_NO_CANDIDATE

        prompt_feedback = getattr(response, "prompt_feedback", None)
        block_reason = getattr(prompt_feedback, "block_reason", None) if prompt_feedback is not None else None
        if block_reason:
            return NO_INLINE_REASON_BLOCKED

        has_any_part = any(self._iter_parts(candidate) for candidate in candidates)
        if has_any_part:
            return NO_INLINE_REASON_NO_IMAGE_PART

        return NO_INLINE_REASON_UNKNOWN

    def build_no_inline_image_error(self, response: GeminiResponseLike) -> str:
        """
        inline 이미지가 없는 응답을 분석해 진단 메시지를 생성한다.
        Args:
            response: GeminiResponseLike: generate_content 응답 객체.
        Returns:
            str: 분류 코드/후보 개수/finish_reason/safety 등을 포함한 오류 문자열.
        """
        reason_code = self.classify_no_inline_reason(response)
        summary = self.build_response_summary(response)

        details: list[str] = [
            f"reason_code={reason_code}",
            f"schema_version={summary['schema_version']}",
            f"candidate_count={summary['candidate_count']}",
        ]

        prompt_feedback = summary["prompt_feedback"]
        if prompt_feedback["block_reason"]:
            details.append(f"prompt_block_reason={prompt_feedback['block_reason']}")
        if prompt_feedback["block_reason_message"]:
            details.append(f"prompt_block_message={prompt_feedback['block_reason_message']}")
        if prompt_feedback["safety_ratings"]:
            details.append(f"prompt_safety_ratings={prompt_feedback['safety_ratings']}")

        candidates = summary["candidates"]
        for idx, candidate in enumerate(candidates[:MAX_CANDIDATES_IN_ERROR], start=1):
            candidate_parts: list[str] = [f"candidate{idx}"]
            finish_reason = candidate["finish_reason"]
            if finish_reason:
                candidate_parts.append(f"finish_reason={finish_reason}")
            safety_ratings = candidate["safety_ratings"]
            if safety_ratings:
                candidate_parts.append(f"safety_ratings={safety_ratings}")
            text = candidate["text"]
            if text:
                candidate_parts.append(f"text={text}")
            details.append(", ".join(candidate_parts))

        base = "Gemini image response returned no inline image data"
        return f"{base}. " + " | ".join(details)

    def build_response_summary(self, response: GeminiResponseLike) -> ResponseSummary:
        """
        메타데이터 저장/디버깅 용도의 응답 요약 딕셔너리를 생성한다.
        Args:
            response: GeminiResponseLike: generate_content 응답 객체.
        Returns:
            ResponseSummary: 스키마 버전이 고정된 응답 요약 객체.
        """
        candidates = self._iter_candidates(response)
        prompt_feedback = self._build_prompt_feedback_summary(response)

        summary: ResponseSummary = {
            "schema_version": SUMMARY_SCHEMA_VERSION,
            "candidate_count": len(candidates),
            "candidates_truncated": len(candidates) > MAX_CANDIDATES_IN_SUMMARY,
            "prompt_feedback": prompt_feedback,
            "candidates": [],
        }

        for candidate in candidates[:MAX_CANDIDATES_IN_SUMMARY]:
            candidate_summary: CandidateSummary = {
                "finish_reason": "",
                "safety_ratings": [],
                "has_inline_image": False,
                "text": "",
            }

            finish_reason = getattr(candidate, "finish_reason", None)
            if finish_reason:
                candidate_summary["finish_reason"] = str(finish_reason)

            candidate_safety_ratings = self._serialize_safety_ratings(getattr(candidate, "safety_ratings", None))
            candidate_summary["safety_ratings"] = candidate_safety_ratings

            parts = self._iter_parts(candidate)
            candidate_summary["has_inline_image"] = any(
                getattr(getattr(part, "inline_data", None), "data", None) for part in parts
            )

            text_chunks = [str(getattr(part, "text")) for part in parts if getattr(part, "text", None)]
            if text_chunks:
                candidate_summary["text"] = self._sanitize_text(" ".join(text_chunks))

            summary["candidates"].append(candidate_summary)

        return summary

    def _build_prompt_feedback_summary(self, response: GeminiResponseLike) -> PromptFeedbackSummary:
        """
        prompt_feedback 요약 객체를 고정 스키마로 생성한다.
        Args:
            response: GeminiResponseLike: generate_content 응답 객체.
        Returns:
            PromptFeedbackSummary: block_reason/block_reason_message/safety_ratings 키를 가진 요약.
        """
        prompt_feedback_summary: PromptFeedbackSummary = {
            "block_reason": "",
            "block_reason_message": "",
            "safety_ratings": [],
        }

        prompt_feedback = getattr(response, "prompt_feedback", None)
        if prompt_feedback is None:
            return prompt_feedback_summary

        block_reason = getattr(prompt_feedback, "block_reason", None)
        if block_reason:
            prompt_feedback_summary["block_reason"] = str(block_reason)

        block_reason_message = getattr(prompt_feedback, "block_reason_message", None)
        if block_reason_message:
            prompt_feedback_summary["block_reason_message"] = self._sanitize_text(str(block_reason_message))

        prompt_feedback_summary["safety_ratings"] = self._serialize_safety_ratings(
            getattr(prompt_feedback, "safety_ratings", None)
        )

        return prompt_feedback_summary

    def _iter_candidates(self, response: GeminiResponseLike) -> list[object]:
        """
        응답 후보 목록을 방어적으로 추출한다.
        Args:
            response: GeminiResponseLike: generate_content 응답 객체.
        Returns:
            list[object]: 후보 목록. 누락/비정상 타입이면 빈 리스트.
        """
        raw = getattr(response, "candidates", None)
        return raw if isinstance(raw, list) else []

    def _iter_parts(self, candidate: object) -> list[object]:
        """
        단일 후보에서 content.parts 목록을 방어적으로 추출한다.
        Args:
            candidate: object: 후보 객체.
        Returns:
            list[object]: part 목록. 누락/비정상 타입이면 빈 리스트.
        """
        content = getattr(candidate, "content", None)
        raw = getattr(content, "parts", None)
        return raw if isinstance(raw, list) else []

    def _serialize_safety_ratings(self, ratings: object) -> list[SerializedSafetyRating]:
        """
        safety_ratings 객체를 JSON 저장 가능한 list[dict] 구조로 변환한다.
        Args:
            ratings: object: 응답의 safety_ratings 값(리스트 또는 None).
        Returns:
            list[SerializedSafetyRating]: category/probability/blocked 키를 가진 직렬화 목록.
        """
        items = ratings if isinstance(ratings, list) else []
        serialized: list[SerializedSafetyRating] = []
        for rating in items:
            row: SerializedSafetyRating = {
                "category": str(getattr(rating, "category", "")),
                "probability": str(getattr(rating, "probability", "")),
            }
            blocked = getattr(rating, "blocked", None)
            if blocked is not None:
                row["blocked"] = str(blocked)
            serialized.append(row)
        return serialized

    def _sanitize_text(self, text: str) -> str:
        """
        관측성 텍스트를 마스킹/길이 제한 규칙으로 정규화한다.
        Args:
            text: str: 원본 텍스트.
        Returns:
            str: 민감정보 마스킹과 길이 제한이 적용된 텍스트.
        """
        masked = self._mask_sensitive_text(text)
        return self._truncate_text(masked, limit=MAX_TEXT_LENGTH)

    def _mask_sensitive_text(self, text: str) -> str:
        """
        이메일/Google API 키 형태 문자열을 마스킹한다.
        Args:
            text: str: 원본 텍스트.
        Returns:
            str: 마스킹된 텍스트.
        """
        compact = " ".join(str(text).split())

        # NOTE: 이메일은 계정 로컬파트를 마스킹해 로그 노출을 줄인다.
        def _mask_email(match: re.Match[str]) -> str:
            head, body, domain = match.group(1), match.group(2), match.group(3)
            return f"{head}{'*' * len(body)}{domain}"

        compact = EMAIL_PATTERN.sub(_mask_email, compact)
        compact = GOOGLE_API_KEY_PATTERN.sub("AIza***************", compact)
        return compact

    def _truncate_text(self, text: str, limit: int) -> str:
        """
        긴 텍스트를 단일 라인으로 정규화하고 길이를 제한한다.
        Args:
            text: str: 원본 텍스트.
            limit: int: 최대 길이.
        Returns:
            str: 정규화/축약이 적용된 텍스트.
        """
        compact = " ".join(str(text).split())
        if len(compact) <= limit:
            return compact
        return compact[: limit - 3] + "..."
