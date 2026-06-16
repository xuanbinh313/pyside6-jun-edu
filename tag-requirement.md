1. OBJECTIVE
Implement an offline-first, user-specific tagging system enabling students to label individual exam questions (e.g., "Vocabulary", "Grammar Bug", "Hard Review") and filter them later for re-studying. The core exam contents must remain decoupled from student interaction metrics.

2. LOCAL DATA STORAGE ALIGNMENT (SQLAlchemy & SQLite)
Add a new entity to the Python/SQLAlchemy layer:

- `user_question_tags` Table:
  - `id`: String (UUID, PK)
  - `user_id`: String (Indexed) -> Represents the current active student.
  - `question_id`: String (FK referencing `exam_questions.id`)
  - `tag_name`: String -> The tag text value chosen or created by the user.
  - `created_at`: DateTime
  - `dirty`: int (0: False, 1: True) -> Handles cloud syncing status natively.

3. PYSIDE6 UI INTERACTION FLOW (TAGGING ACTIONS)
- Beside each question entry widget inside the exam preview panel, render a tiny interactive tag/bookmark icon button (`QPushButton`).
- Clicking this button triggers a contextual floating menu (`QMenu` or custom dialog).
  - The menu must list previously created tags (queried via `SELECT DISTINCT tag_name FROM user_question_tags WHERE user_id = ?`) with checkboxes.
  - Include an "Add New Tag" input line field.
- **Save State:** Checking a tag or submitting a new one must immediately write a local entry to `user_question_tags` in SQLite with `dirty = 1`. Unchecking a tag executes a local database deletion query for that specific row.

4. PYSIDE6 FILTERING & RE-STUDYING RUNTIME LOGIC
In the dashboard review center:
- Provide a tag filter management block using a checkable `QListWidget` or a multi-select dropdown layout.
- When tags are selected, trigger a dynamic SQLAlchemy reload query joining `ExamQuestion` with `UserQuestionTag`. Filter by the active `user_id` and the designated `tag_name` list.
- Reload the question viewport layout. When a user clicks a filtered question, look up its `context_id`:
  - If a parent context exists (e.g., Part 3, 4, 6, 7), load and display that `ExamContext` block alongside the isolated question to provide the necessary reading text context or listening boundaries.

5. BACKGROUND OFFLINE SYNCHRONIZATION
The synchronization pipeline must query all records from `user_question_tags` where `dirty == 1`. Upsert these objects to Supabase via API batch requests, and swap local flags to `0` upon a 200 HTTP code validation response.