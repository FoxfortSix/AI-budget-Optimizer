# budget_optimizer/models.py

from dataclasses import dataclass
from typing import Optional, Dict, List


@dataclass(frozen=True)
class State:
    kos: int
    makan: int
    transport: int
    internet: int
    jajan: int
    hiburan: int
    tabungan: int

    def to_dict(self) -> Dict[str, int]:
        return {
            "kos": self.kos,
            "makan": self.makan,
            "transport": self.transport,
            "internet": self.internet,
            "jajan": self.jajan,
            "hiburan": self.hiburan,
            "tabungan": self.tabungan,
        }

    @staticmethod
    def from_dict(d: Dict[str, int]) -> "State":
        return State(
            kos=d["kos"],
            makan=d["makan"],
            transport=d["transport"],
            internet=d["internet"],
            jajan=d["jajan"],
            hiburan=d["hiburan"],
            tabungan=d["tabungan"],
        )


@dataclass(frozen=True)
class Action:
    src: str
    dst: str
    amount: int
    cost: float


@dataclass(frozen=True)
class Node:
    state: State
    g: float
    h: float
    f: float
    parent: Optional["Node"]
    action: Optional[Action]

    def path(self) -> List[Action]:
        node = self
        actions = []
        while node and node.action:
            actions.append(node.action)
            node = node.parent
        return list(reversed(actions))
