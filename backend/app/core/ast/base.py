from dataclasses import dataclass
from typing import Any

@dataclass
class ASTNode:
    def to_dict(self) -> dict:
        result = {"node_type": self.__class__.__name__}
        for key, value in self.__dict__.items():
            if isinstance(value, ASTNode):
                result[key] = value.to_dict()
            elif isinstance(value, list):
                result[key] = [v.to_dict() if isinstance(v, ASTNode) else v for v in value]
            else:
                result[key] = value
        return result