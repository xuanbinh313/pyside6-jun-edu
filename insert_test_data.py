import json
from models.database import engine, Base, get_session
from models.exam import Exam, ExamQuestion, ExamContext, ExamSrtChunk

# 1. Drop existing tables that are being modified/created
print("Dropping old tables...")
Base.metadata.drop_all(bind=engine, tables=[
    ExamQuestion.__table__,
    ExamContext.__table__
])

# 2. Recreate tables with new schema
print("Creating tables with new schema...")
Base.metadata.create_all(bind=engine)

session = get_session()

# Find the test exam ID
exam = session.query(Exam).filter(Exam.title == "Test 06-04.mp3").first()
if not exam:
    print("Test exam 'Test 06-04.mp3' not found in database. Creating it...")
    exam = Exam(
        id="fe5c1e00-e70a-452f-9c05-42e24928763f",
        title="Test 06-04.mp3",
        description="A sample test exam containing listening and reading parts",
        duration_minutes=45,
        is_published=True
    )
    session.add(exam)
    session.commit()

exam_id = exam.id

# 3. Create a Reading Passage context
print("Inserting exam contexts...")
reading_context = ExamContext(
    exam_id=exam_id,
    context_type="READING_PASSAGE",
    content="The rapid expansion of the internet has transformed modern communication. [[131]] many businesses now rely on online platforms, others still prefer traditional marketing. In conclusion, the shift is [[132]] and inevitable.",
    index=1
)
session.add(reading_context)
session.commit()

# 4. Insert exam questions
print("Inserting exam questions...")
questions = [
    # Listening question 1 (audio start/end)
    ExamQuestion(
        id="q1",
        exam_id=exam_id,
        part=1,
        question_number=1,
        question_type="MULTIPLE_CHOICE",
        content="What is the topic of the talk?",
        options=json.dumps(["Directions", "Questions", "Answers", "Audio"]),
        correct_answer="A",
        additional_meta={"audio_start": 0.2, "audio_end": 4.16}
    ),
    # Listening question 2 (audio start/end)
    ExamQuestion(
        id="q2",
        exam_id=exam_id,
        part=2,
        question_number=2,
        question_type="MULTIPLE_CHOICE",
        content="How many questions will you be asked?",
        options=json.dumps(["One", "Two", "Three", "Four"]),
        correct_answer="C",
        additional_meta={"audio_start": 4.161, "audio_end": 20.24}
    ),
    # Question without audio range (Part 5)
    ExamQuestion(
        id="q3",
        exam_id=exam_id,
        part=5,
        question_number=3,
        question_type="MULTIPLE_CHOICE",
        content="This is a question with NO audio range",
        options=json.dumps(["Opt A", "Opt B", "Opt C", "Opt D"]),
        correct_answer="B",
        additional_meta={}
    ),
    # Reading question 131 linked to the passage context
    ExamQuestion(
        id="q131",
        exam_id=exam_id,
        context_id=reading_context.id,
        part=6,
        question_number=131,
        question_type="MULTIPLE_CHOICE",
        content="Choose the correct transition word:",
        options=json.dumps(["Although", "However", "Because", "Therefore"]),
        correct_answer="A",
        additional_meta={}
    ),
    # Reading question 132 linked to the passage context
    ExamQuestion(
        id="q132",
        exam_id=exam_id,
        context_id=reading_context.id,
        part=6,
        question_number=132,
        question_type="MULTIPLE_CHOICE",
        content="Choose the correct adjective:",
        options=json.dumps(["insignificant", "permanent", "gradual", "temporary"]),
        correct_answer="C",
        additional_meta={}
    )
]

for q in questions:
    session.add(q)

session.commit()
session.close()
print("Successfully reset database tables and inserted test data.")
