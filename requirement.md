# Feature: Authentication System (Login, Register, Logout)

* **Stack:** PySide6 (Frontend GUI) + Supabase Python SDK (Backend/Auth)
* **Target:** Provide a secure and seamless user account management system for the Desktop environment.

## 1. Functional Overview

The authentication system manages user access control and includes three core features:

1. **Registration (Register):** Allows new users to create an account using an Email and Password.
2. **Login:** Authenticates existing users, issues, and maintains user sessions.
3. **Logout:** Safely terminates the current session and redirects the user back to the login screen.


## 2. Detailed Functional Requirements

### 2.1. Registration Feature (Register)

* **Description:** Users input their details to create a new account. Upon successful registration, Supabase sends a confirmation email (if the "Confirm Email" setting is enabled in your Supabase dashboard).
* **Inputs:**
* `Email` (String, must be a valid email format).
* `Password` (String, minimum of 6 characters by default under Supabase policy).
* `Confirm Password` (String, must match the Password field exactly).


* **Workflow:**
1. The user clicks "Register" -> The Frontend performs input validation.
2. The Frontend invokes the Supabase SDK API: `supabase.auth.sign_up({"email": email, "password": password})`.
3. If successful: Display a message instructing the user to verify their email (or automatically log them in and redirect to the dashboard, depending on your Supabase configurations).
4. If failed: Display the corresponding error message returned by Supabase (e.g., Email already exists, Connection timeout...).



### 2.2. Login Feature

* **Description:** Authenticates the user's identity and redirects them to the application's main dashboard.
* **Inputs:** `Email`, `Password`.
* **Workflow:**
1. The user clicks "Login" -> The Frontend invokes the API: `supabase.auth.sign_in_with_password({"email": email, "password": password})`.
2. If successful:
* Supabase returns the `Session` data (containing `access_token` and `refresh_token`).
* The application stores the tokens to persist the login state.
* Closes the Login window and opens the main Dashboard window.


3. If failed (Incorrect credentials, unverified email): Display a specific, user-friendly error message.



### 2.3. Logout Feature

* **Description:** Terminates the active user session securely.
* **Workflow:**
1. The user clicks the "Logout" button on the main dashboard screen.
2. The application invokes the API: `supabase.auth.sign_out()`.
3. The local system clears the stored authentication tokens.
4. Closes all main application windows, re-initializes, and displays the Login screen.



### 2.4. Session Management (Auto-Login)

* **Description:** When the application launches, if a previous session is still valid, the app bypasses the login screen and routes the user directly to the main dashboard.
* **Workflow:**
1. Upon app startup (ideally inside the Main Window's `__init__` method), check for an existing locally stored token.
2. Call `supabase.auth.get_session()` or set the token into the client to verify its validity.
3. If the Session is valid -> Navigate straight to the main app dashboard. If invalid -> Present the Login screen.

## 3. UI/UX Requirements (PySide6 UI Requirements)

### 3.1. Mandatory UI Components

* **Login/Register View:**
* `QLineEdit` for Email (with clear placeholder text).
* `QLineEdit` for Password (configured with `EchoMode = QLineEdit.Password` to mask characters).
* `QPushButton` for the primary action (Login / Register).
* `QPushButton` or link-styled `QLabel` to toggle between the Login and Register forms.


* **Loading States (UX):**
* During API calls to Supabase, all action buttons must be disabled via `setEnabled(False)` to prevent duplicate submissions (Double Requests).
* Display a loading indicator, spinner, or an indeterminate `QProgressBar`.

### 3.2. Validation & Error Handling

* Use a `QMessageBox` or a dynamic red text `QLabel` beneath the input fields to display clear error prompts for the following scenarios:
* Empty Email or Password fields.
* Malformed Email formats (missing `@`, missing domain).
* Password mismatch (on the Register view).
* Server-side errors (e.g., `Invalid login credentials`).

## 4. Technical & Security Requirements

### 4.1. SDK Integration

* Use the official Python `supabase` client (`pip install supabase`).
* Initialize a standalone `supabase_client.py` file utilizing the Singleton pattern so that all PySide6 classes share a single connection instance:
```python
from supabase import create_client, Client
url: str = "YOUR_SUPABASE_URL"
key: str = "YOUR_SUPABASE_ANON_KEY"
supabase: Client = create_client(url, key)

```

### 4.2. Secure Token Storage

* **Basic Level:** Store `access_token` and `refresh_token` in a local `config.json` file or leverage PySide6's `QSettings`.
* **Advanced Level (Recommended):** Use the Python `keyring` library to securely save tokens directly into the Operating System's credential manager (Windows Credential Manager / macOS Keychain) to mitigate token theft.

### 4.3. Asynchronous Processing (Multi-threading)

* **Mandatory:** Executing network requests via the Supabase API is a blocking I/O task. **Do not execute these requests directly on the PySide6 Main UI Thread**, as doing so will freeze the graphical interface ("Not Responding").
* **Solution:** Employ `QThread` combined with the `QObject` (Worker pattern) or integrate the `qasync` library for asynchronous event loops. Use `PySide6.QtCore.Signal` to securely pass operation results from the background worker thread back to the main UI thread.