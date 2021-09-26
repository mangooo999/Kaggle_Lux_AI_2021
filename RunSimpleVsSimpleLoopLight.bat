@echo off
set agent1=C:/git/luxai/light_bot/main.py
set agent2=rule19/main.py
set num_loops=50
SetLocal EnableDelayedExpansion


For %%A in ("%agent1%") do (
    Set Folder1=%%~dpA
    Set Name1=%%~nxA
)

For %%A in ("%agent2%") do (
    Set Folder2=%%~dpA
    Set Name2=%%~nxA
)
echo.Folder1 is: %Folder1%
echo.Folder2 is: %Folder2%

set MYDIR1=%Folder1:~0,-1%
for %%f in (%MYDIR1%) do set myfolder1=%%~nxf

set MYDIR2=%Folder2:~0,-1%
for %%f in (%MYDIR2%) do set myfolder2=%%~nxf

echo.Folder1 is: %myfolder1%
echo.Folder2 is: %myfolder2%

set log_file=results/%myfolder1%_%myfolder2%.log

echo.log file is:%log_file%

echo start %DATE% %TIME% > %log_file%
FOR /L %%G IN (1,1,%num_loops%) DO (
	rem echo|set /p="!TIME! %%G a" >> %log_file%
	echo|set /p=" %%G a" >> %log_file%
	lux-ai-2021 --seed %%G --loglevel 1 %agent1% %agent2% | grep "rank: 1" >> %log_file%  
	rem echo|set /p="!TIME! %%G b" >> %log_file%
	echo|set /p=" %%G b" >> %log_file%
	lux-ai-2021 --seed %%G --loglevel 1 %agent2% %agent1% | grep "rank: 1" >> %log_file%  	
	echo|set /p="."
)

echo end %DATE% %TIME% >> %log_file%


echo end
echo /p="%agent1% win "
echo|set /p="%agent1% win " >> %log_file%
grep --count %agent1% %log_file% | tee -a %log_file%

echo /p="%agent2% win "
echo|set /p="%agent2% win " >> %log_file%
grep --count %agent2% %log_file% | tee -a %log_file%

pause