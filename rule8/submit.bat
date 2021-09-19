for %%I in (.) do set CurrDirName=%%~nxI
echo %CurrDirName%
tar -czf submission.%CurrDirName%.tar.gz *