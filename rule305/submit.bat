for %%I in (.) do set CurrDirName=%%~nxI
echo %CurrDirName%
tar -czf s.%CurrDirName%.tar.gz *