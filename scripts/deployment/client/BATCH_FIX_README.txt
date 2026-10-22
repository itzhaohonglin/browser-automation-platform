Batch File Fix Notes
============================================================

Problem: 'if not exist' syntax causes errors in some Windows environments
Error message: 'This time should not have not' (Chinese Windows)

Solution: Replace 'if not exist' with 'if exist + goto' style

Before:
  if not exist file.txt (
      echo error
      exit /b 1
  )

After:
  if exist file.txt goto :check_ok
  echo error
  exit /b 1
  :check_ok

Fix time: 2026-10-21 21:00:51.250701
Files fixed: 4
