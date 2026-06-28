# Implementation Plan - Refactor ImportQuestionsAgentDialog to Scrollable Step Panels

The goal is to update the [import_questions_agent_dialog.py](file:///d:/Works/jun-edu-workspace/pyside6-jun-edu/src/views/components/import_questions_agent_dialog.py) component:
1. Replace the `QTabWidget` with a scrollable container (`QScrollArea`) showing all 7 step blocks (group boxes) vertically on a single screen.
2. Move the Prompt text input of each step to a separate prompt input dialog, triggered by a button in its respective step block.
3. Add an "Overall PDF Source Files" selection panel below the "Answer sheets" panel to select the overall Question/Transcript PDFs.
4. Extract selected pages to `temp_questions_pdf.pdf` and `temp_transcripts_pdf.pdf` using `pypdf`.
5. Enable and auto-load these temp files in each step's PDF selectors once created.

## Proposed Changes

### UI & View Components

#### [NEW] [prompt_input_dialog.py](file:///d:/Works/jun-edu-workspace/pyside6-jun-edu/src/views/components/prompt_input_dialog.py)
- Create a clean dialog (`PromptInputDialog`) containing a `QTextEdit` for editing the prompt, with "Save" and "Cancel" buttons.

#### [MODIFY] [import_questions_agent_dialog.py](file:///d:/Works/jun-edu-workspace/pyside6-jun-edu/src/views/components/import_questions_agent_dialog.py)
- **Overall PDF Panel**:
  - Add `_build_overall_pdf_panel()` below the answer sheets panel.
  - Implement selection buttons and labels for overall Question PDF and Transcript PDF.
  - When selection is successful, use `pypdf` to extract selected pages to `temp_questions_pdf.pdf` / `temp_transcripts_pdf.pdf` in `get_local_media_dir()`.
- **Scrollable Steps Area**:
  - Replace `self.tabs = QTabWidget(self)` with a `QScrollArea`.
  - Inside the scroll area, place a container widget with a vertical layout containing 7 step blocks (group boxes: "Part 1" to "Part 7").
  - Each step block contains:
    - PDF page selections: "Select question pages" and "Select transcript pages" buttons (disabled by default until overall temp PDFs are created).
    - A button "Edit Prompt" to open the `PromptInputDialog`.
    - For Part 2, keep the "Question context" text edit directly inside the step box.
- **Enabling Step Buttons**:
  - When overall temp PDFs are successfully generated, enable the step-specific page selection buttons.
  - Clicking these buttons opens `PdfPageSelectorDialog` with the path pointing to the generated temp PDF file.

## Verification Plan

### Manual Verification
- Run the application.
- Open the Import Questions Agent dialog.
- Select overall PDFs and their pages in the new "Overall PDF Source Files" panel.
- Verify that `temp_questions_pdf.pdf` and `temp_transcripts_pdf.pdf` are generated correctly.
- Verify that individual step selection buttons become enabled and load the corresponding temp PDF.
- Verify that prompt text can be edited via the "Edit Prompt" button in each block.
- Validate python syntax and run Ruff.
