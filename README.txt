CLINIC VISIT SORTER
===================

Files
-----
main.py           Main Python program (Supports Groq & OpenAI APIs with zero third-party dependencies)
visits.csv        Sample input containing 26 visit records
.env              File to paste your GROQ_API_KEY for VS Code
.env.example      Example template for .env
.gitignore        Prevents accidentally committing secrets (.env) to Git
.vscode/          VS Code launch configuration (Run & Debug menu)
nurse_queue.csv   Generated nurse queue sorted by priority and arrival time
summary.txt       Generated clinic summary report

How to run in VS Code with your Groq API Key
--------------------------------------------
1. Open the project folder in VS Code:
   File -> Open Folder -> C:\Users\DELL\Downloads\Clinic_Visit_Sorter

2. Add your Groq API Key:
   - Open the '.env' file in VS Code.
   - Replace 'your_groq_api_key_here' with your Groq key (starts with gsk_...).
   - (Optional) Choose your Groq model: llama-3.3-70b-versatile or llama-3.1-8b-instant.
   - Save the file (Ctrl + S).

3. Run the program:
   - In VS Code Terminal (Ctrl + `):
         python main.py
     (or: py main.py)
   - Or press F5 to run with the debugger.

Fallback behavior
-----------------
If no API key is provided, the program safely defaults to:
category=other, priority=today, summary="Could not classify, nurse to review".
Red-flag rules still protect urgent cases (e.g. chest pain, fainting) by assigning see_now.

Important Note
--------------
This is an academic demonstration project, not a medical triage tool.
A human nurse makes all medical decisions.
