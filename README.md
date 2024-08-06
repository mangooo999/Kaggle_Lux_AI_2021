"# luxai-2021" 

This project showcase the code that achieved the [9th place (out 1178 participants)](https://www.kaggle.com/competitions/lux-ai-2021/leaderboard?) in the Lux-UI Kaggle competition.

You can see the engine in action in this replay against a pure ML engine:

https://www.kaggle.com/competitions/lux-ai-2021/leaderboard?dialog=episodes-episode-35210052

It uses a mix of rule base engine, and an machine learning one that have been developed in parallel.

# Neural network architecture Engine
The neural network body consisted of a convolutional ResNet architecture with squeeze-excitation layers. 
The network blocks used 128-channel 5x5 convolutions, and include two types of normalization. 
The network had four outputs consisting of three actor outputs - a 32x32xN-actions tensor for workers, and city tiles 
The final network consisted of 16 residual blocks, plus the input encoder and output layers, for a grand total of 3 million parameters.

# Imitation Learning 
The AI model in this project uses a form of imitation learning, where the model is trained to mimic the behavior of an expert or a set of expert demonstrations. In the context of the Lux AI competition, imitation learning involves training the model on a dataset of game episodes where actions taken by the agents are recorded.

## Advantages of Imitation Learning 
 
- **Efficiency** : Imitation learning can leverage a large amount of pre-recorded data, making it efficient to train compared to reinforcement learning, which requires extensive interaction with the environment.
 
- **Simplicity** : The approach simplifies the training process as it directly learns from the expert's decisions without the need for complex reward signals.

This type of imitation learning helps in quickly developing a competitive agent by learning from the strategies and actions of expert players, enabling the model to perform well in the Lux AI competition environment.

A lot of details of the ML part of the code is in this separate repository: https://github.com/vitoque-git/Kaggle-luxai-Season1-Machine-Learning-Framework/blob/main/README.md

# Rule Based Engine
The approach taken was stateless approach. 
I iterate across all the units in multiple-passes scoring the actions that the units may take with the context of what other units/cities are doing. If there's a clash, units are rerun with knowledge of what caused the clash. Standard A* pathfinding with weights to bias toward/away from certain things. I also built tables of path length approximations avoiding cities using Dijkstra which were for fast lookup to avoid having to run the full pathfinding too frequently.
There's a few places with state, mostly to hack around unstable scoring. For example, there is specific code designed to reach new clusters. Scoring where exactly to move to came out fairly unstable, so there's a bias toward doing whatever it is you planned to do last tick. I still get a bit of "dancing" though where performing an action results in the weights changing and the unit wanting to go the opposite direction next tick. Maybe more statefulness would stabilize this.

# The decision Engine
The key of a strong performance was to have an engine that was switching between the two tpe of approach (ML and Rule Based) using a very specific multi dimensional KPI:
- Turn number
- Distance from enemy
- Density of resources around the unit.

# Backtesting
The fact that there are two rule engine plus a super engine on top, create a three dimensional testing space. 
In other words, you have a combination of version across different engine that work together, and for which finding a surface maximum has a way more complex structure.
I back tested each combination of those, and tried to release every day the best 5 promising engine, and then meticulously recorded the result in a old style excel spreadsheet that you can find here together with some interesting graphs:

https://github.com/vitoque-git/luxui-2021/raw/main/results.xlsm
