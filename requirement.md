## 📜 UI REQUIREMENT SPECIFICATION: EXAM ATTEMPT ANALYTICS DASHBOARD (PYSIDE6)

### 1. OBJECTIVE

Implement a comprehensive, production-grade Exam Results & Analytics view using PySide6. The UI must digest data from the `exam_attempts` and `user_answers` models to display overall metric KPIs, a category-based performance breakdown table, and a detailed answer-sheet matrix.

### 2. DATA SOURCE DECODING (BACKEND ALIGNMENT)

To populate this UI, the Python controller must compute values dynamically from the database:

* `total_correct`: `COUNT(user_answers.is_correct == True)`
* `total_unanswered`: `COUNT(user_answers.user_choice IS NULL)`
* `total_wrong`: `COUNT(user_answers.is_correct == False AND user_answers.user_choice IS NOT NULL)`
* `accuracy_rate`: `(total_correct / total_questions) * 100`
* `category_breakdown`: Grouped metrics calculated by joining `exam_questions` sub-categories with their respective `user_answers.is_correct` states.

---

### 3. PYSIDE6 WIDGET ARCHITECTURE MAPPING

#### A. Top Summary Block (KPI Widgets)

Use a horizontal layout (`QHBoxLayout`) containing custom styled `QFrame` components acting as cards:

* **Card 1 (Metrics Sidebar):** A `QVBoxLayout` container holding `QLabel` items for global session logs:
* "Results" (e.g., `2 / 54`)
* "Accuracy" (e.g., `100.0%`)
* "Time" (Convert `duration_seconds` to `H:MM:SS`).


* **Card 2 (Correct Counter):** Light green background, displaying a large bold number of correct items.
* **Card 3 (Wrong Counter):** Light red background, displaying a large bold number of incorrect items.
* **Card 4 (Skipped Counter):** Light gray background, displaying a large bold number of unanswered items.

#### B. Detailed Category Analysis (QTabWidget)

Implement a `QTabWidget` to segment section-specific analysis:

* **Tab 1: Part-Specific Breakdown (e.g., "Part 7")**
* **Tab 2: "Overall" (Global Overview)**

Inside each tab, embed a **`QTableWidget`** configured with the following constraints:

* **Columns:** `[ Question Category, Correct, Wrong, Skipped, Accuracy %, Question List Badges ]`
* **Question List Badges Cell Manipulation:** - Column 6 must render a custom container widget using `QHBoxLayout` or a flow-wrapping layout.
* Populate this cell with small clickable `QPushButton` items representing the `question_number`.
* **Badge Coloring Rules:** - If `is_correct == True` ➔ Green background text (`#28a745`).
* If `user_choice IS NULL` ➔ Light gray border background (`#6c757d`).
* If `is_correct == False` ➔ Red background text (`#dc3545`).





#### C. Bottom Detailed Answer Sheet Layout

Render a dense wrap-around flow grid containing mini result tiles (`QFrame`) for all questions:

* Each item showcases: `[Question Number] [Correct Key Label] : [User Selection Indicator]`.
* If the user skipped the item, render italicized gray text saying *"not answered"*.
* Include a `QPushButton` named **"[Details]"** next to each item.

---

### 4. COMPONENT INTERACTION & EVENT SIGNALS

* **Badge / Details Trigger:** Connecting the `clicked` signal of any Question Badge or `[Details]` link button must spawn a modal overlay dialog (`QDialog`).
* The modal dynamically instantiates the specific targeted `ExamBlock` configuration (e.g., rendering the parent Part 7 reading passage layout side-by-side with the question details) to let the student analyze why they got that question correct, wrong, or skipped.
* **Retake Signal:** The **"Retake Wrong Answers"** button must extract all question IDs linked to this attempt where `is_correct == False`, and dynamically spin up a filtered target practice session utilizing the existing exam block rendering engine.