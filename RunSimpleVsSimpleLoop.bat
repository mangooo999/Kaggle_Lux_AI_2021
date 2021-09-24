rem for run in {1..500}; do lux-ai-2021 --seed $run --loglevel 1 rule15/main.py rule16/main.py | tee logs.txt; done
rem echo off
echo start %DATE% %TIME% > results.log

FOR /L %%G IN (1,1,3) DO (
	echo|set /p="%TIME% %%G a" >> results.log
	lux-ai-2021 --seed %%G --loglevel 1 rule15/main.py rule16/main.py | grep "rank: 1" >> results.log  
	echo|set /p="%TIME% %%G b" >> results.log
	lux-ai-2021 --seed %%G --loglevel 1 rule16/main.py rule15/main.py | grep "rank: 1" >> results.log  	
)

echo end %DATE% %TIME% >> results.log