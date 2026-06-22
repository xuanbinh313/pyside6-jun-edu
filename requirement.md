TARGET_LANG = "Vietnamese (vn)"

LISTENING_PROMPT_TEXT = r"""
Analyze the attached listening transcript text and extract all content into a raw JSON object. 
OUTPUT CONSTRAINT: Output ONLY the raw JSON. No markdown, no ```json code fences, no explanations.
TRANSLATION TARGET LANGUAGE: {TARGET_LANG}

{
    "contexts": [
        {
            "id": "Unique string ID (e.g., 'ctx_l1_1', 'ctx_l3_32')",
            "part": 2, // Integer (TOEIC part 1, 2, 3, or 4). Store ONLY in context, NEVER in questions.
            "context_type": "AUDIO_SRT | STANDALONE",
            "content": {
                // AUDIO_SRT: For Part 3 & 4. Put the full conversation/talk transcript text here.
                // STANDALONE: For Part 1 & 2. Must be exactly {"text": ""}
                "text": "string"
            },
            "index": 0, // 0-based order of appearance in the transcript
            "additional_meta": { 
                "audio_start": 0.0, 
                "audio_end": 0.0, 
                "note": "REQUIRED. Provide the exact full translation of 'content.text' into {TARGET_LANG}. If STANDALONE, leave as empty string." 
            }
        }
    ],
    "questions": [
        {
            "context_id": "Must match a valid context id. NEVER null.",
            "question_number": 11, // Printed or spoken question number as integer
            "question_type": "MULTIPLE_CHOICE",
            "content": "Question stem text. Follow the LISTENING PART RULES below.",
            "options": ["Flat string array. Stripped of prefixes like (A), B., C), etc. Keep original order."],
            "correct_answer": "Required choice label ('A', 'B', 'C', or 'D').",
            "additional_meta": {
                "note": "REQUIRED. Strictly format this field exactly as follows:\n[Translation of the question content stem into {TARGET_LANG}]\n[Translation of option 1 into {TARGET_LANG}]\n[Translation of option 2 into {TARGET_LANG}]\n[Translation of option 3 into {TARGET_LANG}]\n[Translation of option 4 into {TARGET_LANG} (if applicable)]\n\n[Detailed grammatical/contextual explanation in {TARGET_LANG} explaining why the correct_answer is right based on keywords from the transcript.]"
            }
        }
    ]
}

LISTENING PART RULES:
1. PART 1 (Photographs):
   - context_type: "STANDALONE" (content.text = "")
   - questions.content: Set to exactly "Look at the picture and choose the statement that best describes it."
   - questions.options: Put the 4 transcript descriptions (A, B, C, D) here.

2. PART 2 (Question-Response):
   - context_type: "STANDALONE" (content.text = "")
   - questions.content: Put the spoken Question/Statement here (e.g., "Where is the meeting room?").
   - questions.options: Put the 3 spoken response choices (A, B, C) here.

3. PART 3 & 4 (Conversations & Talks):
   - context_type: "AUDIO_SRT"
   - contexts.content.text: Put the entire spoken dialogue or monologue transcript block here.
   - questions.content: Put the printed question stem here.
   - questions.options: Put the 4 printed multiple-choice options here.

STRICT ARCHITECTURE RULES:
1. Every question must link to a context. Never use null context_id.
2. For Part 1 and Part 2, every single question MUST have its own unique, dedicated "STANDALONE" context. Do NOT group multiple Part 1 or Part 2 questions into one context.
3. For Part 3 and Part 4, all questions belonging to the same conversation/talk (usually sets of 3) must reference the exact same shared "AUDIO_SRT" context ID.
4. Extract every question provided in the transcript. Never leave correct_answer or additional_meta.note empty.
5. In 'questions.additional_meta.note', ensure there is a clear new line separating the translations (question + options) and the final explanation.
""".replace("{TARGET_LANG}", TARGET_LANG)