# Command Execution Rules
- **Reading Commands**: You are allowed to set SafeToAutoRun: true for pure reading/diagnostic commands such as ls, grep, cat, find, pwd, and git status.
- **Execution/Python Commands**: You must NEVER set SafeToAutoRun: true for commands that execute code or change system state, such as python, python3, npm, pip, rm, or git commit. These must always require manual approval.
