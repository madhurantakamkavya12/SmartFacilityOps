from typing_extensions import TypedDict
from langgraph.graph import END, START, StateGraph


class EnergyState(TypedDict):
    usage_kwh: float
    result: str


def analyze_energy(state: EnergyState) -> dict[str, str]:
    if state["usage_kwh"] > 500:
        label = "High"
    else:
        label = "Normal"

    return {"result": f"{label} usage: {state['usage_kwh']} kWh"}


builder = StateGraph(EnergyState)
builder.add_node("analyze_energy", analyze_energy)
builder.add_edge(START, "analyze_energy")
builder.add_edge("analyze_energy", END)

energy_graph = builder.compile()

output = energy_graph.invoke({"usage_kwh": 620.0, "result": ""})
print(output["result"])