import json
import os
import sys
from typing import Any

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from app.modules.coding.problem_bank.schema import ProblemRecord, slugify
from app.modules.coding.problem_bank.validator import ProblemValidator

# Target category distribution (Sum = 995)
TOPIC_TARGETS = {
    "Arrays": 92,
    "Strings": 67,
    "Hashing": 46,
    "Two Pointers": 35,
    "Sliding Window": 35,
    "Stack": 40,
    "Queue / Deque": 20,
    "Linked List": 45,
    "Binary Search": 35,
    "Trees": 72,
    "BST": 30,
    "Heap / Priority Queue": 30,
    "Graphs": 77,
    "Greedy": 35,
    "Dynamic Programming": 113,
    "Backtracking": 30,
    "Recursion": 20,
    "Bit Manipulation": 20,
    "Trie": 18,
    "Segment Tree / Fenwick": 18,
    "Sorting": 22,
    "Math / Number Theory": 28,
    "Advanced Algorithms": 24,
    "SQL": 25,
    "Data Science / ML": 18,
}

COMPANIES = [
    ["Google", "Meta"], ["Amazon", "Microsoft"], ["Apple", "Netflix"],
    ["Uber", "Airbnb"], ["LinkedIn", "Stripe"], ["Salesforce", "Oracle"],
    ["Adobe", "ByteDance"], ["Palantir", "Databricks"], ["Coinbase", "Snowflake"],
    ["Bloomberg", "Goldman Sachs"]
]

ROLES = [
    ["Software Engineer", "Backend Engineer"],
    ["Fullstack Engineer", "Frontend Engineer"],
    ["Systems Engineer", "Infrastructure Engineer"],
    ["Data Engineer", "Analytics Engineer"],
    ["Machine Learning Engineer", "AI Research Engineer"]
]


def generate_python_template(title: str, topic: str, is_sql_or_ml: bool = False) -> str:
    func_name = slugify(title).replace("-", "_")
    return f'''import sys

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
    # Parse input and invoke solution
    result = {func_name}(lines)
    if isinstance(result, list):
        print(" ".join(map(str, result)))
    elif result is not None:
        print(result)
'''


def generate_js_template(title: str, topic: str) -> str:
    func_name = slugify(title).replace("-", "_")
    return f'''const fs = require('fs');

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
'''


def generate_cpp_template(title: str, topic: str) -> str:
    return f'''#include <iostream>
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
'''


def generate_java_template(title: str, topic: str) -> str:
    return f'''import java.util.*;
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


def compute_quotas():
    topic_diff = {}
    for topic, total in TOPIC_TARGETS.items():
        hard = round(total * 0.20)
        easy = round(total * 0.30)
        med = total - easy - hard
        topic_diff[topic] = {"Easy": easy, "Medium": med, "Hard": hard}

    curr_easy = sum(d["Easy"] for d in topic_diff.values())
    curr_med = sum(d["Medium"] for d in topic_diff.values())
    curr_hard = sum(d["Hard"] for d in topic_diff.values())

    diff_easy = 297 - curr_easy
    diff_hard = 200 - curr_hard

    topics_list = list(TOPIC_TARGETS.keys())
    i = 0
    while diff_easy != 0:
        t = topics_list[i % len(topics_list)]
        if diff_easy > 0 and topic_diff[t]["Medium"] > topic_diff[t]["Easy"]:
            topic_diff[t]["Easy"] += 1
            topic_diff[t]["Medium"] -= 1
            diff_easy -= 1
        elif diff_easy < 0 and topic_diff[t]["Easy"] > 3:
            topic_diff[t]["Easy"] -= 1
            topic_diff[t]["Medium"] += 1
            diff_easy += 1
        i += 1

    i = 0
    while diff_hard != 0:
        t = topics_list[i % len(topics_list)]
        if diff_hard > 0 and topic_diff[t]["Medium"] > topic_diff[t]["Hard"]:
            topic_diff[t]["Hard"] += 1
            topic_diff[t]["Medium"] -= 1
            diff_hard -= 1
        elif diff_hard < 0 and topic_diff[t]["Hard"] > 2:
            topic_diff[t]["Hard"] -= 1
            topic_diff[t]["Medium"] += 1
            diff_hard += 1
        i += 1

    return topic_diff
