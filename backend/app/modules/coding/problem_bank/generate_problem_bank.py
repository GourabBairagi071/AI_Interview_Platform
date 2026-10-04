"""
Script to generate exactly 995 high-quality, validated coding problems
spanning 25 DSA topics with exact difficulty distribution (297 Easy, 498 Medium, 200 Hard).
"""

import json
import os
import sys
from typing import Any

# Ensure backend root is on sys.path
backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
sys.path.insert(0, backend_root)

from app.modules.coding.problem_bank.schema import ProblemRecord, slugify
from app.modules.coding.problem_bank.validator import ProblemValidator
from app.modules.coding.problem_bank.build_dataset import TOPIC_TARGETS, compute_quotas, COMPANIES, ROLES

# Existing 5 database problems to avoid collision
EXISTING_SLUGS = {
    "two-sum",
    "valid-palindrome",
    "maximum-subarray",
    "binary-search",
    "longest-substring-without-repeating-characters"
}
EXISTING_TITLES = {
    "Two Sum",
    "Valid Palindrome",
    "Maximum Subarray",
    "Binary Search",
    "Longest Substring Without Repeating Characters"
}

def generate_starter_templates(title: str, topic: str, is_sql: bool = False, is_ml: bool = False) -> dict[str, str]:
    func_name = slugify(title).replace("-", "_")

    if is_sql:
        return {
            "python": f'''import sys

def {func_name}(records):
    """
    Simulates SQL query for: {title}
    TODO: Filter, aggregate, or sort the table records.
    """
    # Parse records and return query result
    return records

if __name__ == "__main__":
    lines = sys.stdin.read().strip().splitlines()
    if not lines:
        sys.exit(0)
    res = {func_name}(lines)
    if isinstance(res, list):
        for row in res:
            print(row if not isinstance(row, list) else " ".join(map(str, row)))
    elif res is not None:
        print(res)
''',
            "javascript": f'''const fs = require('fs');

/**
 * SQL Simulation for: {title}
 * @param {{string[]}} records
 * @return {{any}}
 */
function {func_name}(records) {{
    // Implement SQL processing logic
    return records.length > 0 ? records[0] : "";
}}

const input = fs.readFileSync(0, 'utf-8').trim();
if (input) {{
    const lines = input.split('\\n').map(l => l.trim()).filter(Boolean);
    const result = {func_name}(lines);
    if (Array.isArray(result)) {{
        result.forEach(r => console.log(Array.isArray(r) ? r.join(' ') : r));
    }} else if (result !== undefined && result !== null) {{
        console.log(result);
    }}
}}
''',
            "cpp": f'''#include <iostream>
#include <vector>
#include <string>

using namespace std;

// SQL Simulation: {title}
void solve() {{
    string line;
    while (getline(cin, line)) {{
        if (!line.empty()) {{
            cout << line << "\\n";
            break;
        }}
    }}
}}

int main() {{
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    solve();
    return 0;
}}
''',
            "java": f'''import java.util.*;
import java.io.*;

// SQL Simulation: {title}
public class Solution {{
    public static void main(String[] args) throws IOException {{
        BufferedReader br = new BufferedReader(new InputStreamReader(System.in));
        String line = br.readLine();
        if (line != null && !line.trim().isEmpty()) {{
            System.out.println(line.trim());
        }}
    }}
}}
'''
        }

    return {
        "python": f'''import sys

def {func_name}(data):
    """
    Solves {title} ({topic}).
    TODO: Implement your algorithmic solution below.
    """
    # Write your solution logic here
    return data

if __name__ == "__main__":
    lines = sys.stdin.read().strip().splitlines()
    if not lines:
        sys.exit(0)
    result = {func_name}(lines)
    if isinstance(result, list):
        print(" ".join(map(str, result)))
    elif result is not None:
        print(result)
''',
        "javascript": f'''const fs = require('fs');

/**
 * Solves {title} ({topic}).
 * @param {{string[]}} lines
 * @return {{any}}
 */
function {func_name}(lines) {{
    // Implement your algorithmic solution here
    return lines.length > 0 ? lines[0] : "";
}}

function main() {{
    const input = fs.readFileSync(0, 'utf-8').trim();
    if (!input) return;
    const lines = input.split('\\n').map(l => l.trim()).filter(Boolean);
    const result = {func_name}(lines);
    if (Array.isArray(result)) {{
        console.log(result.join(' '));
    }} else if (result !== undefined && result !== null) {{
        console.log(result);
    }}
}}

main();
''',
        "cpp": f'''#include <iostream>
#include <vector>
#include <string>
#include <sstream>
#include <algorithm>

using namespace std;

// Solution for: {title} ({topic})
void solve() {{
    string line;
    if (getline(cin, line)) {{
        // Implement your solution logic here
        cout << line << "\\n";
    }}
}}

int main() {{
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    solve();
    return 0;
}}
''',
        "java": f'''import java.util.*;
import java.io.*;

// Solution for: {title} ({topic})
public class Solution {{
    public static void main(String[] args) throws IOException {{
        BufferedReader br = new BufferedReader(new InputStreamReader(System.in));
        String line = br.readLine();
        if (line != null && !line.trim().isEmpty()) {{
            // Implement your solution logic here
            System.out.println(line.trim());
        }}
    }}
}}
'''
    }
