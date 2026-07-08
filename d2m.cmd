@echo  off
if not exist readme.docx.md (
	Call :Convert
	) else (
	Echo readme.docx.md already exists.
	choice /C YN /M Delete
	if errorlevel 2 goto :EOF
	Call :Convert
	)
Goto :EOF

:Convert
Echo cvDocX2md.cmd readme
Call cvDocX2md.cmd readme
StaRt readme.docx.md
Goto :EOF