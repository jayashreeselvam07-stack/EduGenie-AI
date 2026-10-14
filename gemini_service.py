import json
import logging
from typing import Dict, Any, List
from google import genai
from google.genai import types
from google.genai.errors import APIError

from app.config import config
from app.schemas import (
    AskResponse,
    ExplainResponse,
    QuizResponse,
    QuizQuestion,
    SummarizeResponse,
    ImportantTerm,
    LearningPathResponse,
    LearningModule,
    ResourceSuggestion
)

logger = logging.getLogger("edugenie.gemini")

# --- Custom Exception Classes for Granular Error Reporting ---
class GeminiNotConfiguredError(Exception):
    """Raised when GEMINI_API_KEY is missing or invalid placeholder."""
    pass

class GeminiAuthError(Exception):
    """Raised on 401/403 Authentication or Permission errors."""
    pass

class GeminiQuotaError(Exception):
    """Raised on 429 Quota or Rate limit exceeded errors."""
    pass

class GeminiModelNotFoundError(Exception):
    """Raised on 404 Model Not Found or retired model errors."""
    pass

class GeminiCapacityError(Exception):
    """Raised on 503 Server Capacity / High Demand errors."""
    pass

class GeminiNetworkError(Exception):
    """Raised on network connection / socket / DNS / timeout errors."""
    pass

class GeminiServiceError(Exception):
    """Raised on generic Gemini API failures."""
    pass


class GeminiService:
    @property
    def model_name(self) -> str:
        return config.GEMINI_MODEL

    def _get_client(self) -> genai.Client:
        if not config.is_gemini_configured():
            raise GeminiNotConfiguredError(
                "GEMINI_API_KEY is missing or not configured. Please add your key to the .env file."
            )
        return genai.Client(api_key=config.GEMINI_API_KEY)

    def _clean_json_text(self, text: str) -> str:
        """Strip markdown code blocks if model included them."""
        text = text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        return text

    def _get_language_instruction(self, language: str) -> str:
        if language == "ta":
            return (
                "\nIMPORTANT LANGUAGE RULE: You MUST output all text, responses, headings, option values, "
                "definitions, and explanations ENTIRELY in standard, clear Tamil language (தமிழ்). "
                "Keep JSON keys in English as specified."
            )
        return "\nLANGUAGE RULE: Output all text in clear, correct English."

    def _handle_exception(self, e: Exception, context_action: str):
        """Classify and raise safe, descriptive exceptions without exposing API keys."""
        err_msg = str(e)
        code = getattr(e, "code", None)

        # Log sanitized error (never log raw key)
        logger.error(f"Error during {context_action}: type={type(e).__name__}, code={code}, msg={err_msg}")

        if isinstance(e, APIError):
            code_val = str(code) if code else ""
            msg_lower = err_msg.lower()

            if code == 503 or "503" in code_val or "capacity" in msg_lower or "high demand" in msg_lower or "unavailable" in msg_lower:
                raise GeminiCapacityError(
                    f"Gemini Server High Demand (503): Model '{self.model_name}' is temporarily experiencing peak server load. Please try again in a few seconds."
                )
            elif code == 404 or "404" in code_val or "not_found" in msg_lower or "no longer available" in msg_lower:
                raise GeminiModelNotFoundError(
                    f"Model '{self.model_name}' was not found or is retired. Please update GEMINI_MODEL=gemini-3.8-flash in your .env file."
                )
            elif code in [401, 403] or "api_key_invalid" in msg_lower or "permission_denied" in msg_lower or "unauthenticated" in msg_lower:
                raise GeminiAuthError(
                    "Authentication failed: Your GEMINI_API_KEY appears to be invalid or unauthorized. Please check your key at https://aistudio.google.com/"
                )
            elif code == 429 or "resource_exhausted" in msg_lower or "quota" in msg_lower:
                raise GeminiQuotaError(
                    "Gemini API rate limit or quota exceeded. Please wait a moment or check your API quota at Google AI Studio."
                )
            else:
                raise GeminiServiceError(f"Gemini API Error ({code or 'API'}): {getattr(e, 'message', err_msg)}")

        # Connection / Network / DNS errors
        if "connect" in err_msg.lower() or "timeout" in err_msg.lower() or "socket" in err_msg.lower() or "getaddrinfo" in err_msg.lower():
            raise GeminiNetworkError("Network error: Unable to connect to Gemini API servers. Please check your internet connection.")

        raise GeminiServiceError(f"Failed to complete {context_action}. Please try again.")

    # --- Tool 1: Ask EduGenie ---
    def ask_edugenie(self, question: str, language: str = "en") -> AskResponse:
        client = self._get_client()
        lang_instruction = self._get_language_instruction(language)
        
        prompt = f"""You are EduGenie, an expert educational AI assistant.
Answer the following student question accurately and clearly.

Question: {question}

Return your response strictly in valid JSON format with this exact structure:
{{
  "answer": "Concise direct answer to the question (2-4 sentences)",
  "explanation": "Detailed, easy-to-understand academic explanation of the concepts involved"
}}

{lang_instruction}"""

        try:
            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.3
                )
            )
            raw_text = self._clean_json_text(response.text or "{}")
            data = json.loads(raw_text)
            
            return AskResponse(
                question=question,
                answer=data.get("answer", "Answer not available."),
                explanation=data.get("explanation", "Explanation not available."),
                language=language
            )
        except Exception as e:
            self._handle_exception(e, "Ask EduGenie")

    # --- Tool 2: Explain a Concept ---
    def explain_concept(self, concept: str, level: str = "Beginner", language: str = "en") -> ExplainResponse:
        client = self._get_client()
        lang_instruction = self._get_language_instruction(language)

        prompt = f"""You are EduGenie, a passionate educator.
Explain the following concept tailored for a user at the '{level}' level.

Concept: {concept}
Target Level: {level}

Guidelines:
- Beginner: Use simple analogies, avoid jargon or explain every technical term intuitively.
- Intermediate: Provide standard technical context, core mechanisms, and practical examples.
- Advanced: Deep dive into theoretical principles, edge cases, underlying mechanics, and complex real-world applications.

Return your response strictly in valid JSON format with this structure:
{{
  "explanation": "Clear main explanation tailored to {level} level",
  "key_takeaways": ["Takeaway point 1", "Takeaway point 2", "Takeaway point 3"],
  "analogy": "A relatable real-world analogy to help visualize the concept"
}}

{lang_instruction}"""

        try:
            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.3
                )
            )
            raw_text = self._clean_json_text(response.text or "{}")
            data = json.loads(raw_text)

            takeaways = data.get("key_takeaways", [])
            if not isinstance(takeaways, list) or not takeaways:
                takeaways = ["Key takeaway details available in explanation."]

            return ExplainResponse(
                concept=concept,
                level=level,
                explanation=data.get("explanation", "Explanation could not be generated."),
                key_takeaways=[str(t) for t in takeaways],
                analogy=data.get("analogy"),
                language=language
            )
        except Exception as e:
            self._handle_exception(e, "Explain Concept")

    # --- Tool 3: Generate a Quiz ---
    def generate_quiz(self, topic: str, language: str = "en") -> QuizResponse:
        client = self._get_client()
        lang_instruction = self._get_language_instruction(language)

        prompt = f"""You are EduGenie. Generate a quiz based on the following topic or text.

Topic / Text:
{topic}

REQUIREMENTS:
1. Create EXACTLY 3 multiple-choice questions.
2. Each question MUST have EXACTLY 4 distinct option strings.
3. Include 'correct_index' as an integer (0 for option 1, 1 for option 2, 2 for option 3, 3 for option 4).
4. Provide a brief explanation for why the correct option is right.

Return response strictly as a JSON object with this structure:
{{
  "questions": [
    {{
      "question": "Question text here?",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_index": 0,
      "explanation": "Brief explanation of the correct answer."
    }},
    {{
      "question": "Second question text?",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_index": 1,
      "explanation": "Brief explanation of the correct answer."
    }},
    {{
      "question": "Third question text?",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_index": 2,
      "explanation": "Brief explanation of the correct answer."
    }}
  ]
}}

{lang_instruction}"""

        try:
            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.2
                )
            )
            raw_text = self._clean_json_text(response.text or "{}")
            data = json.loads(raw_text)

            raw_questions = data.get("questions", [])
            if not isinstance(raw_questions, list):
                raw_questions = []

            validated_questions: List[QuizQuestion] = []
            for item in raw_questions[:3]:
                q_text = str(item.get("question", "Question placeholder")).strip()
                opts = item.get("options", [])
                if not isinstance(opts, list):
                    opts = []
                
                opts = [str(o).strip() for o in opts if str(o).strip()]
                while len(opts) < 4:
                    opts.append(f"Option {len(opts) + 1}")
                opts = opts[:4]

                idx = item.get("correct_index", 0)
                try:
                    idx = int(idx)
                except (ValueError, TypeError):
                    idx = 0
                if idx < 0 or idx > 3:
                    idx = 0

                expl = str(item.get("explanation", "The selected option is correct.")).strip()

                validated_questions.append(
                    QuizQuestion(
                        question=q_text,
                        options=opts,
                        correct_index=idx,
                        explanation=expl
                    )
                )

            while len(validated_questions) < 3:
                q_num = len(validated_questions) + 1
                validated_questions.append(
                    QuizQuestion(
                        question=f"Question {q_num} on {topic[:30]}",
                        options=["Option A", "Option B", "Option C", "Option D"],
                        correct_index=0,
                        explanation="Default explanation."
                    )
                )
            
            validated_questions = validated_questions[:3]

            return QuizResponse(
                topic=topic,
                questions=validated_questions,
                language=language
            )

        except Exception as e:
            self._handle_exception(e, "Generate Quiz")

    # --- Tool 4: Summarize Notes ---
    def summarize_notes(self, text: str, language: str = "en") -> SummarizeResponse:
        client = self._get_client()
        lang_instruction = self._get_language_instruction(language)

        prompt = f"""You are EduGenie. Summarize the following study notes or text concisely.

Study Text:
{text}

Requirements:
- Provide a clear, well-written executive summary.
- List 3-6 essential key bullet points.
- Extract 2-5 important terms/concepts along with concise definitions.

Return strictly as JSON with this structure:
{{
  "summary": "Concise paragraph overview of the text.",
  "key_points": ["Key point 1", "Key point 2", "Key point 3"],
  "important_terms": [
    {{"term": "Term 1", "definition": "Short definition"}},
    {{"term": "Term 2", "definition": "Short definition"}}
  ]
}}

{lang_instruction}"""

        try:
            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.3
                )
            )
            raw_text = self._clean_json_text(response.text or "{}")
            data = json.loads(raw_text)

            key_pts = [str(k) for k in data.get("key_points", []) if k]
            if not key_pts:
                key_pts = ["Summary details outlined above."]

            terms_raw = data.get("important_terms", [])
            terms: List[ImportantTerm] = []
            if isinstance(terms_raw, list):
                for t in terms_raw:
                    if isinstance(t, dict) and t.get("term") and t.get("definition"):
                        terms.append(ImportantTerm(term=str(t["term"]), definition=str(t["definition"])))

            return SummarizeResponse(
                summary=data.get("summary", "Summary could not be generated."),
                key_points=key_pts,
                important_terms=terms,
                language=language
            )
        except Exception as e:
            self._handle_exception(e, "Summarize Notes")

    # --- Tool 5: Create a Learning Path ---
    def create_learning_path(self, topic: str, language: str = "en") -> LearningPathResponse:
        client = self._get_client()
        lang_instruction = self._get_language_instruction(language)

        prompt = f"""You are EduGenie. Create a structured step-by-step learning path for a student wanting to master the topic below.

Topic: {topic}

Requirements:
- Provide an overview of the roadmap.
- Create 3-4 structured modules ordered from Beginner to Advanced.
- Provide 3-5 measurable milestones to track progress.
- Provide 3-4 learning resource suggestions (e.g. books, official documentation, interactive course topics). Do NOT invent fake URLs; describe the resource name, description, and type clearly.

Return strictly as JSON with this structure:
{{
  "overview": "Overview of the learning journey",
  "modules": [
    {{
      "title": "Module 1: Foundations",
      "level": "Beginner",
      "topics": ["Topic 1", "Topic 2", "Topic 3"],
      "estimated_hours": "5-8 hours"
    }},
    {{
      "title": "Module 2: Core Mastery",
      "level": "Intermediate",
      "topics": ["Topic 1", "Topic 2"],
      "estimated_hours": "10-12 hours"
    }}
  ],
  "milestones": [
    "Milestone 1: Complete foundational exercises",
    "Milestone 2: Build a basic project"
  ],
  "resource_suggestions": [
    {{
      "name": "Resource Name / Subject",
      "description": "Why this resource is helpful",
      "type": "Book / Documentation / Course / Practice"
    }}
  ]
}}

{lang_instruction}"""

        try:
            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.3
                )
            )
            raw_text = self._clean_json_text(response.text or "{}")
            data = json.loads(raw_text)

            modules_raw = data.get("modules", [])
            modules: List[LearningModule] = []
            if isinstance(modules_raw, list):
                for m in modules_raw:
                    if isinstance(m, dict):
                        modules.append(
                            LearningModule(
                                title=str(m.get("title", "Module")),
                                level=str(m.get("level", "Beginner")),
                                topics=[str(tp) for tp in m.get("topics", [])],
                                estimated_hours=str(m.get("estimated_hours", "N/A"))
                            )
                        )

            milestones = [str(m) for m in data.get("milestones", []) if m]
            
            resources_raw = data.get("resource_suggestions", [])
            resources: List[ResourceSuggestion] = []
            if isinstance(resources_raw, list):
                for r in resources_raw:
                    if isinstance(r, dict):
                        resources.append(
                            ResourceSuggestion(
                                name=str(r.get("name", "Resource")),
                                description=str(r.get("description", "")),
                                type=str(r.get("type", "Guide"))
                            )
                        )

            return LearningPathResponse(
                topic=topic,
                overview=data.get("overview", "Roadmap overview."),
                modules=modules,
                milestones=milestones,
                resource_suggestions=resources,
                language=language
            )
        except Exception as e:
            self._handle_exception(e, "Create Learning Path")

gemini_service = GeminiService()
