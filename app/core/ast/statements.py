from dataclasses import dataclass
from typing import Any, List, Optional
from app.core.ast.base import ASTNode
from app.core.ast.declarations import BlockNode

@dataclass
class VarDeclNode(ASTNode):
    name: str
    var_type: str
    value: Optional[ASTNode]
    line: int

@dataclass
class AssignNode(ASTNode):
    target: ASTNode
    value: ASTNode
    line: int

@dataclass
class PrintNode(ASTNode):
    expression: ASTNode
    line: int

@dataclass
class IfNode(ASTNode):
    condition: ASTNode
    then_branch: BlockNode
    elif_branches: List[Any]
    else_branch: Optional[BlockNode]
    line: int

@dataclass
class WhileNode(ASTNode):
    condition: ASTNode
    body: BlockNode
    line: int

@dataclass
class ForNode(ASTNode):
    init: Optional[ASTNode]
    condition: Optional[ASTNode]
    update: Optional[ASTNode]
    body: BlockNode
    line: int

@dataclass
class ForEachNode(ASTNode):
    item_name: str
    iterable: ASTNode
    body: BlockNode
    line: int

@dataclass
class BreakNode(ASTNode):
    line: int

@dataclass
class ContinueNode(ASTNode):
    line: int

@dataclass
class ReturnNode(ASTNode):
    expression: Optional[ASTNode]
    line: int