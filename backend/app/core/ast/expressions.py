from dataclasses import dataclass
from typing import List
from app.core.ast.base import ASTNode

@dataclass
class IntLiteralNode(ASTNode):
    value: int
    line: int

@dataclass
class FloatLiteralNode(ASTNode):
    value: float
    line: int

@dataclass
class BoolLiteralNode(ASTNode):
    value: bool
    line: int

@dataclass
class StringLiteralNode(ASTNode):
    value: str
    line: int

@dataclass
class ArrayLiteralNode(ASTNode):
    elements: List[ASTNode]
    line: int

@dataclass
class IdentifierNode(ASTNode):
    name: str
    line: int

@dataclass
class BinOpNode(ASTNode):
    left: ASTNode
    op: str
    right: ASTNode
    line: int

@dataclass
class UnaryOpNode(ASTNode):
    op: str
    operand: ASTNode
    line: int

@dataclass
class FunctionCallNode(ASTNode):
    name: str
    args: List[ASTNode]
    line: int

@dataclass
class MethodCallNode(ASTNode):
    target: ASTNode
    method_name: str
    args: List[ASTNode]
    line: int

@dataclass
class ArrayAccessNode(ASTNode):
    array: ASTNode
    index: ASTNode
    line: int