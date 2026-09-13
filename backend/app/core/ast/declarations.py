from dataclasses import dataclass
from typing import List
from app.core.ast.base import ASTNode

@dataclass
class ProgramNode(ASTNode):
    statements: List[ASTNode]

@dataclass
class BlockNode(ASTNode):
    statements: List[ASTNode]

@dataclass
class FunctionDeclNode(ASTNode):
    name: str
    params: List[tuple]  # [('param_name', 'type_str')]
    return_type: str
    body: BlockNode
    line: int