"# luxai-2021" 

# Lux AI 2021 Competition Solution

This project showcases the code that achieved [9th place (out of 1178 participants) in the Lux-UI Kaggle competition.](https://www.kaggle.com/competitions/lux-ai-2021/leaderboard?) 

You can see the engine in action in this replay against a pure ML engine:

https://www.kaggle.com/competitions/lux-ai-2021/leaderboard?dialog=episodes-episode-35210052

## Overview

The solution uses a hybrid approach, combining a rule-based engine with a machine learning (ML) engine. The rule-based engine is responsible for making decisions based on game state and predefined rules, while the ML engine is used to predict actions based on game state features.

### Rule-Based Engine

The approach taken is primarily stateless. The algorithm iterates across all units in multiple passes, scoring the actions each unit may take while considering the context of other units and cities. If a clash occurs, the units are rerun with the knowledge of what caused the clash. Standard A* pathfinding is used, with weights to bias the units toward or away from certain targets. Additionally, tables of path length approximations avoiding cities were built using Dijkstra's algorithm for fast lookup, minimizing the need for frequent full pathfinding runs.

There are a few instances of statefulness, mainly to address unstable scoring. For example, there is specific code to ensure units reach new clusters. The scoring for exact movement proved to be unstable, so a bias was introduced toward following the plan from the previous tick. Despite this, there are still some issues with "dancing," where a unit's action causes weight changes that make it want to move in the opposite direction in the next tick. Increasing statefulness might help stabilize this behavior.

The rule-based engine is designed to make decisions based on the following factors:

1. **Turn number**: The engine takes into account the current turn number to adjust its strategy.
2. **Distance from enemy**: The engine considers the distance between the player's units and the enemy's units to determine the best course of action.
3. **Density of resources around the unit**: The engine evaluates the availability of resources around each unit to decide whether to collect, build, or move.

The engine uses a set of predefined rules to make decisions, such as:

* **Builder selection**: The engine selects the best city tile to build a worker based on factors like resource availability and unit density.
* **Unit movement**: The engine determines the best movement for each unit based on factors like resource collection, enemy proximity, and unit density.
* **Resource collection**: The engine decides which resources to collect based on factors like resource availability and unit capacity.

### Machine Learning Engine

The ML engine is used to predict actions based on game state features. The engine is trained on a dataset of game episodes and uses a convolutional neural network (CNN) architecture to predict actions. 

#### Neural network architecture
The neural network body consisted of a convolutional ResNet architecture with squeeze-excitation layers. 
The network blocks used 128-channel 5x5 convolutions, and include two types of normalization. 
The network had four outputs consisting of three actor outputs - a 32x32xN-actions tensor for workers, and city tiles 
The final network consisted of 16 residual blocks, plus the input encoder and output layers, for a grand total of 3 million parameters.

#### Imitation Learning 
The AI model in this project uses a form of imitation learning, where the model is trained to mimic the behavior of an expert or a set of expert demonstrations. In the context of the Lux AI competition, imitation learning involves training the model on a dataset of game episodes where actions taken by the agents are recorded.

#### Advantages of Imitation Learning 
 
- **Efficiency** : Imitation learning can leverage a large amount of pre-recorded data, making it efficient to train compared to reinforcement learning, which requires extensive interaction with the environment.
 
- **Simplicity** : The approach simplifies the training process as it directly learns from the expert's decisions without the need for complex reward signals.

This type of imitation learning helps in quickly developing a competitive agent by learning from the strategies and actions of expert players, enabling the model to perform well in the Lux AI competition environment.

A lot of details of the ML part of the code is in this separate repository: https://github.com/vitoque-git/Kaggle-luxai-Season1-Machine-Learning-Framework/blob/main/README.md

## Hybrid Approach

The hybrid approach combines the outputs of the rule-based engine and the ML engine to make final decisions. The engine uses a weighted average of the outputs from both engines to determine the best course of action.

The hybrid approach offers several advantages, including:

* **Improved decision-making**: The combination of rule-based and ML engines allows for more informed decision-making.
* **Flexibility**: The engine can adapt to different game scenarios and opponents.
* **Efficiency**: The engine can make decisions quickly and efficiently.
  
## The decision Engine
The key of a strong performance was to have an engine that was switching between the two tpe of approach (ML and Rule Based) using a very specific multi dimensional KPI:
- Turn number
- Distance from enemy
- Density of resources around the unit.


# Backtesting
The presence of two rule engines plus a super engine on top creates a three-dimensional testing space. This means there is a combination of versions across different engines that work together, making the search for an optimal configuration significantly more complex. Each combination was backtested, and every day, the top 5 most promising engines were released. The results were meticulously recorded in a traditional Excel spreadsheet, which you can find here, along with some interesting graphs: https://github.com/vitoque-git/luxui-2021/raw/main/results.xlsm

## Correlation between Backtesting Results and Agent Scores
The graph below shows the correlation between the win rate in backtesting and the score achieved by the agent in the competition. Achieving a high position in the competition was largely possible due to accurately predicting which agent would perform best in the competition based on backtesting results:

![Correlation between Backtesting Results and Agent Scores](https://github.com/vitoque-git/Kaggle-luxai-Season1-Python-Framework/blob/main/img/2.jpg)

### Daily Model Releases 

Each day, a new model was released. In the graph below, you can observe the changes over time:
 
- **Vertical Axis** : 
  - **Gray** : Change in win rate during backtesting
 
  - **Blue** : Change in agent score
 
- **Horizontal Axis** : The day of the competition on which the model was released.

![Trend of released models by the day of competition](https://github.com/vitoque-git/Kaggle-luxai-Season1-Python-Framework/blob/main/img/1.jpg)
  
# Code Structure

The code is organized into several modules, including:

* **Game state**: This module handles game state management, including updating game state and providing game state features.
* **Rule-based engine**: This module implements the rule-based engine, including builder selection, unit movement, and resource collection.
* **Machine learning engine**: This module implements the ML engine, including data preprocessing, model training, and prediction.
* **Hybrid approach**: This module combines the outputs of the rule-based engine and the ML engine to make final decisions.

# Results

The solution achieved 9th place (out of 1178 participants) in the Lux-UI Kaggle competition. The engine demonstrated strong performance in various game scenarios, including resource collection, unit movement, and builder selection.
  

