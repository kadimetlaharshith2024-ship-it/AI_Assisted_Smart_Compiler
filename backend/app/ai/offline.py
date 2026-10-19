"""Rule-based explanations used when no AI key is configured (or the AI call
fails). They cover the messages produced by the lexer, parser and type checker,
at both explanation levels, so the "More simplified" button still works offline."""
import re

_T = r"[\w\[\]]+"   # a Lumen type such as int, string or int[]

# (pattern, beginner template, simple template); named groups feed the templates.
_RULES = [
    (rf"Undeclared identifier '(?P<name>\w+)'",
     "**What went wrong:** the name `{name}` is used, but it was never declared.\n\n"
     "**Why it happened:** Lumen only knows names you introduce with `let` first (or a typo made a new, unknown name).\n\n"
     "**How to fix it:** declare it before using it, or fix the spelling:\n\n```\nlet {name}: int = 0;\n```",
     "**In plain words:** you used a name, `{name}`, that the computer has never heard of. "
     "It is like asking for a locker that nobody has labelled yet.\n\n"
     "**The fix:** make the box first, like `let {name}: int = 0;`, or check if you spelled it differently somewhere."),

    (r"Undeclared function '(?P<name>.+?)'",
     "**What went wrong:** the function `{name}` is called but doesn't exist.\n\n"
     "**Why it happened:** functions must be declared with `fn` (watch for typos).\n\n"
     "**How to fix it:** declare it, e.g. `fn {name}() -> void {{ }}`, or correct the name.",
     "**In plain words:** you asked the computer to do a trick called `{name}`, but it was never taught that trick.\n\n"
     "**The fix:** teach it first with `fn`, or check the spelling of the name."),

    (rf"Cannot initialize '(?P<name>\w+)' of type '(?P<expected>{_T})' with a value of type '(?P<actual>{_T})'",
     "**What went wrong:** `{name}` is declared as `{expected}`, but you gave it a value of type `{actual}`.\n\n"
     "**Why it happened:** each variable holds one kind of value, and Lumen checks that they match.\n\n"
     "**How to fix it:** give it a value of type `{expected}`, or change the declared type to `{actual}`.",
     "**In plain words:** `{name}` is a box made only for `{expected}` things, and you tried to put a value of type `{actual}` in it. "
     "It is like pushing a basketball into an egg carton.\n\n"
     "**The fix:** put a value of type `{expected}` in the box, or make a box for `{actual}` instead."),

    (rf"Cannot assign a value of type '(?P<actual>{_T})' to (?P<what>variable '\w+'|an array element) of type '(?P<expected>{_T})'",
     "**What went wrong:** you tried to store a value of type `{actual}` in {what}, which holds `{expected}`.\n\n"
     "**Why it happened:** the type of a variable is fixed when it is declared.\n\n"
     "**How to fix it:** assign a value of type `{expected}` instead.",
     "**In plain words:** {what} only takes `{expected}` things, but you handed it a value of type `{actual}`. "
     "Like trying to put a DVD into a cassette player.\n\n"
     "**The fix:** use a value of type `{expected}` there."),

    (rf"Function '(?P<name>\w+)' must return '(?P<expected>{_T})', but this returns '(?P<actual>{_T})'",
     "**What went wrong:** `{name}` promises to return `{expected}`, but this `return` gives back `{actual}`.\n\n"
     "**Why it happened:** the type after `->` is a promise about what the function returns.\n\n"
     "**How to fix it:** return a value of type `{expected}`, or change the type after `->`.",
     "**In plain words:** `{name}` said it would hand back a value of type `{expected}`, but it handed back a value of type `{actual}`. "
     "Like ordering a pizza and getting a salad.\n\n"
     "**The fix:** return a value of type `{expected}`, or change what the function promises."),

    (r"Function '(?P<name>\w+)' is declared 'void' and cannot return a value",
     "**What went wrong:** `{name}` is `void`, so it must not return a value.\n\n"
     "**How to fix it:** remove the value after `return`, or change `void` to the type you want to return.",
     "**In plain words:** `{name}` promised to give nothing back, but it tried to give something.\n\n"
     "**The fix:** just write `return;`, or change `void` to the type of thing it should give back."),

    (r"Function '(?P<name>\w+)' must return a value of type '(?P<expected>.+?)' on every path|Function '(?P<name2>\w+)' must return a value of type '(?P<expected2>.+?)'",
     "**What went wrong:** `{name}` should return `{expected}`, but some route through it ends without a `return`.\n\n"
     "**Why it happened:** if an `if` has no `else`, the function can reach the end with nothing to return.\n\n"
     "**How to fix it:** add a `return` at the end, or an `else` that returns.",
     "**In plain words:** `{name}` promised to give back a value of type `{expected}`, but in some cases it just stops without giving anything. "
     "Like a vending machine that takes your money and gives nothing.\n\n"
     "**The fix:** make sure every path ends with `return`, for example one last `return` at the bottom."),

    (r"Argument (?P<pos>\d+) of '(?P<name>\w+)' expects '(?P<expected>.+?)', got '(?P<actual>.+?)'",
     "**What went wrong:** argument {pos} of `{name}` should be `{expected}`, but you passed `{actual}`.\n\n"
     "**How to fix it:** pass a value of type `{expected}` in that position.",
     "**In plain words:** `{name}` wants a value of type `{expected}` in spot {pos}, but you gave it a value of type `{actual}`. "
     "Like giving a key to a lock that needs a card.\n\n"
     "**The fix:** hand it a value of type `{expected}` there."),

    (r"Function '(?P<name>\w+)' expects (?P<expected>\d+) arguments, but (?P<actual>\d+) were provided",
     "**What went wrong:** `{name}` needs {expected} argument(s), but you gave {actual}.\n\n"
     "**How to fix it:** match the number of values in the call to the function's parameters.",
     "**In plain words:** `{name}` needs {expected} thing(s) to work with, but you gave it {actual}. "
     "Like a recipe that needs {expected} ingredient(s).\n\n"
     "**The fix:** give it exactly {expected}."),

    (r"(?P<where>'.+?') condition must be of type 'bool', got '(?P<actual>.+?)'",
     "**What went wrong:** the {where} condition is a value of type `{actual}`, but it must be `true` or `false` (`bool`).\n\n"
     "**How to fix it:** use a comparison, e.g. `if (x > 0)` instead of `if (x)`.",
     "**In plain words:** a condition is a yes/no question, but you gave a value of type `{actual}`, which isn't a yes or no.\n\n"
     "**The fix:** ask a real question, like `x > 0` or `x == 5`."),

    (r"Cannot concatenate '(?P<left>.+?)' and '(?P<right>.+?)'",
     "**What went wrong:** `+` can only join two strings, but here it got `{left}` and `{right}`.\n\n"
     "**How to fix it:** make both sides strings.",
     "**In plain words:** `+` can glue words to words, but you tried to glue `{left}` to `{right}`.\n\n"
     "**The fix:** keep both parts as text (strings)."),

    (r"Operator '(?P<op>.+?)' cannot (?:be applied to|compare) .+",
     "**What went wrong:** the operator `{op}` doesn't work with those types.\n\n"
     "**How to fix it:** make sure both sides are numbers (or both bool for `&&` / `||`).",
     "**In plain words:** the `{op}` sign doesn't make sense for that mix of things, like adding a word to a number.\n\n"
     "**The fix:** use matching kinds of values on both sides."),

    (r"(?:Variable|Function) '(?P<name>\w+)' is already declared",
     "**What went wrong:** `{name}` is declared twice in the same place.\n\n"
     "**How to fix it:** rename one, or drop the second `let` and just assign: `{name} = ...;`",
     "**In plain words:** you labelled two boxes with the same name, `{name}`, so the computer can't tell them apart.\n\n"
     "**The fix:** rename one, or skip the second `let` and just put a new value in the first box."),

    (r"'(?P<word>break|continue)' can only be used inside a loop",
     "**What went wrong:** `{word}` only works inside `while`, `for` or `foreach`.\n\n**How to fix it:** move it into a loop or remove it.",
     "**In plain words:** `{word}` is a loop button, and you pressed it with no loop running.\n\n**The fix:** put it inside a loop, or delete it."),

    (r"Syntax error at '(?P<token>.*)'",
     "**What went wrong:** the compiler didn't expect `{token}` at this point.\n\n"
     "**Why it happened:** usually a missing `;`, `)` or `}}` on this line or the one before.\n\n"
     "**How to fix it:** check the line above for a missing semicolon or bracket.",
     "**In plain words:** the computer got confused at `{token}`, like a sentence with a missing full stop.\n\n"
     "**The fix:** look at this line and the one just above for a forgotten `;`, `)` or `}}`."),

    (r"Unexpected end of input",
     "**What went wrong:** the code ended before it was complete.\n\n**How to fix it:** look for a missing `}}` or `)` or a last `;`.",
     "**In plain words:** your program stopped mid-sentence.\n\n**The fix:** check that every `{{` has a `}}` and every `(` has a `)`."),

    (r"Illegal character '(?P<char>.)'",
     "**What went wrong:** `{char}` isn't allowed in Lumen code.\n\n**How to fix it:** delete it (or put it inside a string).",
     "**In plain words:** the computer doesn't know the symbol `{char}`.\n\n**The fix:** remove it, or put it inside quote marks if it is part of text."),
]
_COMPILED = [(re.compile(p), b, s) for p, b, s in _RULES]

_GENERIC = {
    "beginner": ("**What went wrong:** the compiler reported: `{message}`.\n\n"
                 "**How to fix it:** look at the highlighted line and check variable types, spelling and punctuation."),
    "simple": ("**In plain words:** the computer found a problem and says: `{message}`.\n\n"
               "**The fix:** read that line slowly and check spelling, types and punctuation."),
}


def explain_offline(error_message, level="beginner"):
    index = 1 if level == "beginner" else 2
    for rule in _COMPILED:
        match = rule[0].search(error_message)
        if match:
            groups = {k: v for k, v in match.groupdict().items() if v is not None}
            # the two-branch "must return a value" rule uses name/name2 aliases
            groups.setdefault("name", groups.get("name2", ""))
            groups.setdefault("expected", groups.get("expected2", ""))
            return rule[index].format(**groups)
    return _GENERIC[level].format(message=error_message)
