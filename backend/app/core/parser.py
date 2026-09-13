import ply.yacc as yacc
from app.core.lexer import tokens, build_lexer
from app.core.ast import (
    ProgramNode, BlockNode, IntLiteralNode, FloatLiteralNode,
    BoolLiteralNode, StringLiteralNode, ArrayLiteralNode, IdentifierNode,
    BinOpNode, UnaryOpNode, VarDeclNode, AssignNode, PrintNode,
    IfNode, WhileNode, ForNode, ForEachNode, BreakNode, ContinueNode,
    FunctionDeclNode, FunctionCallNode, MethodCallNode, ReturnNode, ArrayAccessNode
)

precedence = (
    ('left', 'OR'),
    ('left', 'AND'),
    ('nonassoc', 'EQ', 'NEQ'),
    ('nonassoc', 'LT', 'GT', 'LE', 'GE'),
    ('left', 'PLUS', 'MINUS'),
    ('left', 'TIMES', 'DIVIDE', 'MOD'),
    ('right', 'NOT', 'UMINUS'),
)

def p_program(p):
    '''program : statement_list'''
    p[0] = ProgramNode(statements=p[1])

def p_statement_list(p):
    '''statement_list : statement_list statement
                      | statement
                      | empty'''
    if len(p) == 3:
        p[0] = p[1] + [p[2]] if p[2] else p[1]
    elif len(p) == 2 and p[1] is not None:
        p[0] = [p[1]]
    else:
        p[0] = []

def p_block(p):
    '''block : LBRACE statement_list RBRACE'''
    p[0] = BlockNode(statements=p[2])

def p_type(p):
    '''type : TYPE_INT
            | TYPE_FLOAT
            | TYPE_BOOL
            | TYPE_STRING
            | TYPE_VOID
            | TYPE_INT LBRACKET RBRACKET
            | TYPE_FLOAT LBRACKET RBRACKET
            | TYPE_BOOL LBRACKET RBRACKET
            | TYPE_STRING LBRACKET RBRACKET'''
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = f"{p[1]}[]"

def p_statement_var_decl(p):
    '''statement : LET IDENTIFIER COLON type ASSIGN expression SEMICOLON
                 | LET IDENTIFIER COLON type SEMICOLON'''
    if len(p) == 8:
        p[0] = VarDeclNode(name=p[2], var_type=p[4], value=p[6], line=p.lineno(1))
    else:
        p[0] = VarDeclNode(name=p[2], var_type=p[4], value=None, line=p.lineno(1))

def p_statement_assign(p):
    '''statement : assignable ASSIGN expression SEMICOLON'''
    p[0] = AssignNode(target=p[1], value=p[3], line=p.lineno(2))

def p_assignable(p):
    '''assignable : IDENTIFIER
                  | postfix_expr LBRACKET expression RBRACKET'''
    if len(p) == 2:
        p[0] = IdentifierNode(name=p[1], line=p.lineno(1))
    else:
        p[0] = ArrayAccessNode(array=p[1], index=p[3], line=p.lineno(2))

def p_statement_print(p):
    '''statement : PRINT LPAREN expression RPAREN SEMICOLON'''
    p[0] = PrintNode(expression=p[3], line=p.lineno(1))

def p_statement_fn_decl(p):
    '''statement : FN IDENTIFIER LPAREN param_list RPAREN ARROW type block'''
    p[0] = FunctionDeclNode(name=p[2], params=p[4], return_type=p[7], body=p[8], line=p.lineno(1))

def p_param_list(p):
    '''param_list : param_list COMMA param
                  | param
                  | empty'''
    if len(p) == 4:
        p[0] = p[1] + [p[3]]
    elif len(p) == 2 and p[1] is not None:
        p[0] = [p[1]]
    else:
        p[0] = []

def p_param(p):
    '''param : IDENTIFIER COLON type'''
    p[0] = (p[1], p[3])

def p_statement_return(p):
    '''statement : RETURN expression SEMICOLON
                 | RETURN SEMICOLON'''
    val = p[2] if len(p) == 4 else None
    p[0] = ReturnNode(expression=val, line=p.lineno(1))

def p_statement_if(p):
    '''statement : IF LPAREN expression RPAREN block elif_blocks else_block'''
    p[0] = IfNode(condition=p[3], then_branch=p[5], elif_branches=p[6], else_branch=p[7], line=p.lineno(1))

def p_elif_blocks(p):
    '''elif_blocks : elif_blocks ELSE IF LPAREN expression RPAREN block
                   | empty'''
    if len(p) == 8:
        p[0] = p[1] + [(p[5], p[7])]
    else:
        p[0] = []

def p_else_block(p):
    '''else_block : ELSE block
                  | empty'''
    p[0] = p[2] if len(p) == 3 else None

def p_statement_while(p):
    '''statement : WHILE LPAREN expression RPAREN block'''
    p[0] = WhileNode(condition=p[3], body=p[5], line=p.lineno(1))

def p_statement_for(p):
    '''statement : FOR LPAREN for_init expression_opt SEMICOLON for_update_opt RPAREN block'''
    p[0] = ForNode(init=p[3], condition=p[4], update=p[6], body=p[8], line=p.lineno(1))

def p_for_init(p):
    '''for_init : statement
                | expression_opt SEMICOLON'''
    p[0] = p[1]

def p_expression_opt(p):
    '''expression_opt : expression
                      | empty'''
    p[0] = p[1]

def p_for_update_opt(p):
    '''for_update_opt : IDENTIFIER ASSIGN expression
                      | empty'''
    if len(p) == 4:
        p[0] = AssignNode(target=IdentifierNode(name=p[1], line=p.lineno(1)), value=p[3], line=p.lineno(1))
    else:
        p[0] = None

def p_statement_foreach(p):
    '''statement : FOREACH LPAREN IDENTIFIER IN expression RPAREN block'''
    p[0] = ForEachNode(item_name=p[3], iterable=p[5], body=p[7], line=p.lineno(1))

def p_statement_break(p):
    '''statement : BREAK SEMICOLON'''
    p[0] = BreakNode(line=p.lineno(1))

def p_statement_continue(p):
    '''statement : CONTINUE SEMICOLON'''
    p[0] = ContinueNode(line=p.lineno(1))

def p_statement_expr(p):
    '''statement : expression SEMICOLON'''
    p[0] = p[1]

def p_expression_binop(p):
    '''expression : expression PLUS expression
                  | expression MINUS expression
                  | expression TIMES expression
                  | expression DIVIDE expression
                  | expression MOD expression
                  | expression EQ expression
                  | expression NEQ expression
                  | expression LT expression
                  | expression GT expression
                  | expression LE expression
                  | expression GE expression
                  | expression AND expression
                  | expression OR expression'''
    p[0] = BinOpNode(left=p[1], op=p[2], right=p[3], line=p.lineno(2))

def p_expression_unary(p):
    '''expression : MINUS expression %prec UMINUS
                  | NOT expression'''
    p[0] = UnaryOpNode(op=p[1], operand=p[2], line=p.lineno(1))

def p_expression_postfix(p):
    '''expression : postfix_expr'''
    p[0] = p[1]

def p_postfix_expr(p):
    '''postfix_expr : primary_expr
                    | postfix_expr LPAREN arg_list RPAREN
                    | postfix_expr LBRACKET expression RBRACKET
                    | postfix_expr DOT IDENTIFIER LPAREN arg_list RPAREN'''
    if len(p) == 2:
        p[0] = p[1]
    elif len(p) == 5 and p[2] == '(':
        name = p[1].name if isinstance(p[1], IdentifierNode) else str(p[1])
        p[0] = FunctionCallNode(name=name, args=p[3], line=p.lineno(2))
    elif len(p) == 5 and p[2] == '[':
        p[0] = ArrayAccessNode(array=p[1], index=p[3], line=p.lineno(2))
    elif len(p) == 7:
        p[0] = MethodCallNode(target=p[1], method_name=p[3], args=p[5], line=p.lineno(2))

def p_primary_expr(p):
    '''primary_expr : INT_LITERAL
                    | FLOAT_LITERAL
                    | STRING_LITERAL
                    | TRUE
                    | FALSE
                    | IDENTIFIER
                    | array_literal
                    | LPAREN expression RPAREN'''
    token_type = p.slice[1].type
    if token_type == 'INT_LITERAL':
        p[0] = IntLiteralNode(value=p[1], line=p.lineno(1))
    elif token_type == 'FLOAT_LITERAL':
        p[0] = FloatLiteralNode(value=p[1], line=p.lineno(1))
    elif token_type == 'STRING_LITERAL':
        p[0] = StringLiteralNode(value=p[1], line=p.lineno(1))
    elif token_type == 'TRUE':
        p[0] = BoolLiteralNode(value=True, line=p.lineno(1))
    elif token_type == 'FALSE':
        p[0] = BoolLiteralNode(value=False, line=p.lineno(1))
    elif token_type == 'IDENTIFIER':
        p[0] = IdentifierNode(name=p[1], line=p.lineno(1))
    elif token_type == 'array_literal':
        p[0] = p[1]
    else:
        p[0] = p[2]

def p_array_literal(p):
    '''array_literal : LBRACKET arg_list RBRACKET'''
    p[0] = ArrayLiteralNode(elements=p[2], line=p.lineno(1))

def p_arg_list(p):
    '''arg_list : arg_list COMMA expression
                | expression
                | empty'''
    if len(p) == 4:
        p[0] = p[1] + [p[3]]
    elif len(p) == 2 and p[1] is not None:
        p[0] = [p[1]]
    else:
        p[0] = []

def p_empty(p):
    '''empty :'''
    p[0] = None

def p_error(p):
    if p:
        parser.custom_errors.append({
            "line": p.lineno,
            "message": f"Syntax error at '{p.value}'",
            "token": str(p.value)
        })
    else:
        parser.custom_errors.append({
            "line": -1,
            "message": "Unexpected end of input",
            "token": "EOF"
        })

parser = yacc.yacc(debug=False, write_tables=False)

def parse_code(code: str):
    lexer = build_lexer()
    parser.custom_errors = []
    tree = parser.parse(code, lexer=lexer)
    return tree, lexer.errors, parser.custom_errors