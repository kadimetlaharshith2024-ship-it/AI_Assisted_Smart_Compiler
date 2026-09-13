// Content structured from language-handbook.md (v0.2).
// Each lesson can have prose, an optional data table, and one or more
// runnable code examples that feed straight into the Playground.

export const lessons = [
  {
    id: 'comments',
    number: 1,
    title: 'Comments',
    intro: 'Two comment styles: a line comment for quick notes, a block comment for longer explanations.',
    examples: [
      {
        label: 'Line and block comments',
        code: `// this is a line comment

/*
this is a
block comment
*/`
      }
    ]
  },
  {
    id: 'variables',
    number: 2,
    title: 'Variables & Types',
    intro: 'Every variable is declared with let, a name, a :type, and optionally an initial value. You can leave the value out and it gets a type-appropriate default.',
    typeTable: [
      { type: 'int', literal: '42', default: '0' },
      { type: 'float', literal: '3.14', default: '0.0' },
      { type: 'bool', literal: 'true / false', default: 'false' },
      { type: 'string', literal: '"hi"', default: '""' },
      { type: 'T[]', literal: '[1, 2, 3]', default: '[]' }
    ],
    examples: [
      {
        label: 'Declaring variables',
        code: `let age: int = 25;
let price: float = 9.99;
let isOpen: bool = true;
let city: string = "Chennai";
let scores: int[] = [90, 85, 77];

print(age);
print(price);
print(isOpen);
print(city);
print(scores.length());`
      },
      {
        label: 'Declaring without a value',
        code: `let total: int;
total = 100;
print(total);`
      }
    ]
  },
  {
    id: 'operators',
    number: 3,
    title: 'Operators',
    intro: 'Arithmetic, comparison, and logical operators. Integer division truncates like most C-family languages.',
    examples: [
      {
        label: 'Arithmetic',
        code: `let a: int = 10 + 3; // 13
let b: int = 10 - 3; // 7
let c: int = 10 * 3; // 30
let d: int = 10 / 3; // 3 (int division)
let e: int = 10 % 3; // 1
print(a);
print(b);
print(c);
print(d);
print(e);`
      },
      {
        label: 'Comparison',
        code: `let r1: bool = (5 == 5); // true
let r2: bool = (5 != 3); // true
let r3: bool = (5 < 10); // true
let r4: bool = (5 >= 5); // true
print(r1);
print(r2);
print(r3);
print(r4);`
      },
      {
        label: 'Logical',
        code: `let r5: bool = true && false; // false
let r6: bool = true || false; // true
let r7: bool = !true; // false
print(r5);
print(r6);
print(r7);`
      }
    ]
  },
  {
    id: 'print',
    number: 4,
    title: 'Print',
    intro: 'print(...) writes a single value to output. Strings concatenate with +.',
    examples: [
      {
        label: 'Printing values',
        code: `print("Hello, world!");

let name: string = "Ravi";
print("Hi " + name);`
      }
    ]
  },
  {
    id: 'if-else',
    number: 5,
    title: 'If / Else',
    intro: 'Standard if / else if / else branching.',
    examples: [
      {
        label: 'Branching on a value',
        code: `let x: int = 7;
if (x > 10) {
    print("big");
} else if (x > 5) {
    print("medium");
} else {
    print("small");
}`
      }
    ]
  },
  {
    id: 'loops',
    number: 6,
    title: 'Loops',
    intro: 'Three loop forms, plus break and continue for early exit and skipping.',
    subsections: [
      {
        heading: '6.1 while',
        examples: [
          {
            label: 'while loop',
            code: `let i: int = 0;
while (i < 5) {
    print(i);
    i = i + 1;
}`
          }
        ]
      },
      {
        heading: '6.2 for (C-style: init; condition; update)',
        examples: [
          {
            label: 'for loop',
            code: `for (let i: int = 0; i < 5; i = i + 1) {
    print(i);
}`
          }
        ]
      },
      {
        heading: '6.3 foreach (iterate over an array directly)',
        body: "This is sugar over indexing — useful when you don't need the index, and gives a clean array-specific error case (foreach used on a non-array type).",
        examples: [
          {
            label: 'foreach loop',
            code: `let nums: int[] = [10, 20, 30];
foreach (n in nums) {
    print(n);
}`
          }
        ]
      },
      {
        heading: '6.4 break and continue',
        examples: [
          {
            label: 'break and continue',
            code: `for (let i: int = 0; i < 10; i = i + 1) {
    if (i == 5) {
        break;
    }
    if (i % 2 == 0) {
        continue;
    }
    print(i);
}`
          }
        ]
      }
    ]
  },
  {
    id: 'functions',
    number: 7,
    title: 'Functions',
    intro: 'Functions declare a return type with ->. A non-void function is expected to return a value on every path.',
    examples: [
      {
        label: 'Declaring and calling functions',
        code: `fn add(a: int, b: int) -> int {
    return a + b;
}

fn greet(name: string) -> void {
    print("Hello, " + name);
}

fn isEven(n: int) -> bool {
    return n % 2 == 0;
}

let result: int = add(3, 4);
print(result); // 7
greet("Ravi"); // Hello, Ravi
print(isEven(10)); // true`
      }
    ]
  },
  {
    id: 'arrays',
    number: 8,
    title: 'Arrays',
    intro: 'Arrays support indexing, index assignment, and a built-in .length().',
    examples: [
      {
        label: 'Indexing and .length()',
        code: `let nums: int[] = [1, 2, 3, 4, 5];
print(nums[0]);        // 1
nums[1] = 99;
print(nums[1]);        // 99
print(nums.length());  // 5 (built-in)`
      }
    ]
  },
  {
    id: 'full-example',
    number: 9,
    title: 'Full Example Program',
    intro: 'Everything together: recursion, a loop building up a sequence, and print.',
    examples: [
      {
        label: 'Factorial sequence',
        code: `// Compute factorial and print first N results
fn factorial(n: int) -> int {
    if (n <= 1) {
        return 1;
    }
    return n * factorial(n - 1);
}

fn main() -> void {
    let limit: int = 6;
    let results: int[] = [];
    for (let i: int = 1; i <= limit; i = i + 1) {
        let f: int = factorial(i);
        print(f);
    }
}

main();`,
        expectedOutput: ['1', '2', '6', '24', '120', '720']
      }
    ]
  },
  {
    id: 'keywords',
    number: 10,
    title: 'Reserved Keywords',
    intro: 'Quick reference — these words can\u2019t be used as identifiers.',
    keywords: [
      'let', 'fn', 'return', 'if', 'else', 'while', 'for', 'foreach', 'in',
      'break', 'continue', 'true', 'false',
      'int', 'float', 'bool', 'string', 'void', 'print'
    ]
  }
]
