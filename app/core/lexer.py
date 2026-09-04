import ply.lex as lex

# Section 10: Reserved Keywords
reserved = {
    'let': 'LET',
    'fn': 'FN',
    'return': 'RETURN',
    'if': 'IF',
    'else': 'ELSE',
    'while': 'WHILE',
    'for': 'FOR',
    'foreach': 'FOREACH',
    'in': 'IN',
    'break': 'BREAK',
    'continue': 'CONTINUE',
    'true': 'TRUE',
    'false': 'FALSE',
    'int': 'TYPE_INT',
    'float': 'TYPE_FLOAT',
    'bool': 'TYPE_BOOL',
    'string': 'TYPE_STRING',
    'void': 'TYPE_VOID',
    'print': 'PRINT',
}

tokens = [
    'IDENTIFIER',
    'INT_LITERAL',
    'FLOAT_LITERAL',
    'STRING_LITERAL',

    # Section 3: Operators
    'PLUS', 'MINUS', 'TIMES', 'DIVIDE', 'MOD',
    'EQ', 'NEQ', 'LE', 'GE', 'LT', 'GT',
    'AND', 'OR', 'NOT',
    'ASSIGN', 'ARROW',

    # Delimiters
    'SEMICOLON', 'COMMA', 'COLON', 'DOT',
    'LPAREN', 'RPAREN',
    'LBRACE', 'RBRACE',
    'LBRACKET', 'RBRACKET',
] + list(set(reserved.values()))

t_PLUS      = r'\+'
t_MINUS     = r'-'
t_TIMES     = r'\*'
t_DIVIDE    = r'/'
t_MOD       = r'%'
t_EQ        = r'=='
t_NEQ       = r'!='
t_LE        = r'<='
t_GE        = r'>='
t_LT        = r'<'
t_GT        = r'>'
t_AND       = r'&&'
t_OR        = r'\|\|'
t_NOT       = r'!'
t_ASSIGN    = r'='
t_ARROW     = r'->'
t_SEMICOLON = r';'
t_COMMA     = r','
t_COLON     = r':'
t_DOT       = r'\.'
t_LPAREN    = r'\('
t_RPAREN    = r'\)'
t_LBRACE    = r'\{'
t_RBRACE    = r'\}'
t_LBRACKET  = r'\['
t_RBRACKET  = r'\]'

t_ignore = ' \t'

def t_COMMENT_BLOCK(t):
    r'/\*(.|\n)*?\*/'
    t.lexer.lineno += t.value.count('\n')

def t_COMMENT_LINE(t):
    r'//.*'
    pass

def t_STRING_LITERAL(t):
    r'\"([^\\\n]|(\\.))*?\"'
    t.value = t.value[1:-1]
    return t

def t_FLOAT_LITERAL(t):
    r'\d+\.\d+'
    t.value = float(t.value)
    return t

def t_INT_LITERAL(t):
    r'\d+'
    t.value = int(t.value)
    return t

def t_IDENTIFIER(t):
    r'[a-zA-Z_][a-zA-Z0-9_]*'
    t.type = reserved.get(t.value, 'IDENTIFIER')
    return t

def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

def t_error(t):
    t.lexer.errors.append({
        "line": t.lexer.lineno,
        "message": f"Illegal character '{t.value[0]}' at line {t.lexer.lineno}",
        "token": t.value[0]
    })
    t.lexer.skip(1)

def build_lexer():
    lexer = lex.lex()
    lexer.errors = []
    return lexer