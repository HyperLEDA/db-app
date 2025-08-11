import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / ".."))

import pandas
from matplotlib import pyplot as plt

plt.style.use("petroff10")

parameter = "prior"

df = pandas.read_csv("experiments/data/results.csv")

plt.plot(df[parameter], df["collision_objects_ratio"], label="collision")
# plt.plot(df[parameter], df["existing_objects_ratio"], label="existing")
# plt.plot(df[parameter], df["new_objects_ratio"], label="new")
plt.legend()
plt.xlabel(parameter)
plt.ylabel("Object ratio")
plt.grid(True)
plt.xscale("log")
plt.show()
