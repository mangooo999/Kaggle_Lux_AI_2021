@echo off
set agent1=C:/git/luxai/imit4/main.py
set agent2=rulem11_8347/main.py
set start_loop=1
set num_loops=100
set storeReplay=true
set storeLogs=false


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

mkdir replays\%myfolder1%_%myfolder2%
set log_file=replays\%myfolder1%_%myfolder2%\results.log

echo.log file is:%log_file%

echo start %DATE% %TIME% > %log_file%
FOR /L %%G IN (%start_loop%,1,%num_loops%) DO (
	rem echo|set /p="!TIME! %%G a" >> %log_file%
	echo|set /p=" %%G a" >> %log_file%
	echo|set /p=" %%G a" 
	lux-ai-2021 --seed %%G --maxtime 15000 --loglevel 1 --width 32 --height 32 --storeReplay=%storeReplay% --storeLogs=%storeLogs% %agent1% %agent2% --out=replays/%myfolder1%_%myfolder2%/%%Ga.luxr | grep "rank: 1" >> %log_file%  
	rem echo|set /p="!TIME! %%G b" >> %log_file%
	echo|set /p=" %%G b" >> %log_file%
	echo|set /p=" b" 
	rem lux-ai-2021 --seed %%G --maxtime 12000 --loglevel 1 --width 12 --height 12 --storeReplay=%storeReplay% --storeLogs=%storeLogs% %agent2% %agent1% --out=replays/%myfolder1%_%myfolder2%/%%Gb.luxr | grep "rank: 1" >> %log_file%  	
	echo "."
	grep --count %agent1% %log_file%
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