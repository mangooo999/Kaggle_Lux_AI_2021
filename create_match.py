from kaggle_environments import make

from rule13.agent import agent

env = make("lux_ai_2021", configuration={"seed": 562124210, "loglevel": 2, "annotations": True}, debug=True)
steps = env.run([agent, "simple_agent"])