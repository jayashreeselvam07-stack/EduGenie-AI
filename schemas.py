from pydantic import BaseModel, Field, field_validator
from typing import List, Optional

# --- Tool 1: Ask EduGenie ---
class AskRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=12000, description="The question to ask EduGenie")
    language: str = Field("en", description="Response language ('en' for English, 'ta' for Tamil)")

class AskResponse(BaseModel):
    question: str
    answer: str
    explanation: str
    language: str

# --- Tool 2: Explain a Concept ---
class ExplainRequest(BaseModel):
    concept: str = Field(..., min_length=2, max_length=12000, description="The concept or topic to explain")
    level: str = Field("Beginner", description="Target audience level: 'Beginner', 'Intermediate', or 'Advanced'")
    language: str = Field("en", description="Response language ('en' or 'ta')")

class ExplainResponse(BaseModel):
    concept: str
    level: str
    explanation: str
    key_takeaways: List[str]
    analogy: Optional[str] = None
    language: str

# --- Tool 3: Generate a Quiz ---
class QuizRequest(BaseModel):
    topic: str = Field(..., min_length=2, max_length=12000, description="Topic or pasted study text for the quiz")
    language: str = Field("en", description="Response language ('en' or 'ta')")

class QuizQuestion(BaseModel):
    question: str
    options: List[str]
    correct_index: int
    explanation: str

    @field_validator("options")
    @classmethod
    def validate_options_length(cls, v):
        if len(v) != 4:
            raise ValueError("Quiz question must have exactly 4 options.")
        return v

    @field_validator("correct_index")
    @classmethod
    def validate_correct_index(cls, v):
        if not (0 <= v <= 3):
            raise ValueError("correct_index must be between 0 and 3.")
        return v

class QuizResponse(BaseModel):
    topic: str
    questions: List[QuizQuestion]
    language: str

    @field_validator("questions")
    @classmethod
    def validate_questions_count(cls, v):
        if len(v) != 3:
            raise ValueError("Quiz response must contain exactly 3 questions.")
        return v

# --- Tool 4: Summarize Notes ---
class SummarizeRequest(BaseModel):
    text: str = Field(..., min_length=10, max_length=12000, description="Pasted study text or notes to summarize")
    language: str = Field("en", description="Response language ('en' or 'ta')")

class ImportantTerm(BaseModel):
    term: str
    definition: str

class SummarizeResponse(BaseModel):
    summary: str
    key_points: List[str]
    important_terms: List[ImportantTerm]
    language: str

# --- Tool 5: Create a Learning Path ---
class LearningPathRequest(BaseModel):
    topic: str = Field(..., min_length=2, max_length=12000, description="Subject or goal for the learning path")
    language: str = Field("en", description="Response language ('en' or 'ta')")

class LearningModule(BaseModel):
    title: str
    level: str
    topics: List[str]
    estimated_hours: str

class ResourceSuggestion(BaseModel):
    name: str
    description: str
    type: str  # e.g., "Book", "Documentation", "Interactive Course", "Practice Site"

class LearningPathResponse(BaseModel):
    topic: str
    overview: str
    modules: List[LearningModule]
    milestones: List[str]
    resource_suggestions: List[ResourceSuggestion]
    language: str

# --- Generic API Error Schema ---
class APIErrorResponse(BaseModel):
    detail: str
    error_code: str
    configurable_help: Optional[str] = None
