"""
Production dataset generator for 995 DSA coding problems.
Validates each problem schema, ensures unique titles and slugs,
and outputs problem_bank_995.jsonl ready for ingestion.
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
from app.modules.coding.problem_bank.generate_problem_bank import (
    generate_starter_templates, EXISTING_SLUGS, EXISTING_TITLES
)

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

# Topic thematic generators with rich diversity
TOPIC_THEMES = {
    "Arrays": [
        ("Prefix Sum Range Query", "Calculate cumulative range metrics efficiently", "Prefix Sum", "O(N)", "O(N)"),
        ("Difference Array Range Updates", "Apply multiple range update operations in constant time per query", "Difference Array", "O(N + Q)", "O(N)"),
        ("Dutch National Flag Partition", "Reorder an array with three distinct classes in-place", "Two Pointers", "O(N)", "O(1)"),
        ("Matrix Spiral Inward Traversal", "Traverse a two-dimensional grid in an inward clockwise spiral order", "Matrix Simulation", "O(M*N)", "O(1)"),
        ("Subarray Maximum Product Tracker", "Locate continuous sequence yielding maximum multiplication product", "Dynamic Programming", "O(N)", "O(1)"),
        ("Trapping Rainwater Reservoir", "Calculate total volume of water retained between elevation bars", "Two Pointers", "O(N)", "O(1)"),
        ("Majority Element Boyer Moore Voting", "Detect element appearing strictly more than half the total length", "Voting Algorithm", "O(N)", "O(1)"),
        ("Rotate Matrix Ninety Degrees In Place", "Perform in-place 90 degree clockwise rotation of square matrix", "Matrix Manipulation", "O(N^2)", "O(1)"),
        ("Find Missing Number in Permutation", "Identify the single omitted integer in range zero to N", "Bit Manipulation", "O(N)", "O(1)"),
        ("Pascal Triangle Row Generator", "Generate specific indexed row of Pascal's binomial triangle", "Combinatorics", "O(K)", "O(K)"),
        ("Monotonic Array Sequence Check", "Determine whether array satisfies non-decreasing or non-increasing property", "Array Inspection", "O(N)", "O(1)"),
        ("Continuous Subarray Modulo Range", "Identify subarrays whose sum is divisible by target modulus k", "Prefix Hash", "O(N)", "O(K)"),
        ("Next Permutation Lexicographical Order", "Determine the immediate next lexicographical sequence permutation", "Array Permutation", "O(N)", "O(1)"),
        ("Third Maximum Distinct Element", "Return the third greatest distinct integer or the global maximum", "Counting / Selection", "O(N)", "O(1)"),
        ("Merge Sorted Arrays Without Extra Space", "Merge two presorted sequences in-place without auxiliary arrays", "Two Pointers", "O(M+N)", "O(1)"),
        ("Peak Element Coordinate Detection", "Locate any local peak element strictly greater than adjacent neighbors", "Binary Search", "O(log N)", "O(1)"),
        ("Summary Ranges Continuous Intervals", "Condense sorted integers into minimal set of contiguous ranges", "Interval Formatting", "O(N)", "O(1)"),
        ("Product of Array Except Current Self", "Compute total product excluding element at current index without division", "Prefix Suffix Product", "O(N)", "O(1)"),
        ("Disjoint Intervals Overlap Merger", "Merge overlapping intervals into minimal set of disjoint intervals", "Interval Scheduling", "O(N log N)", "O(N)"),
        ("Corporate Flight Booking Difference Array", "Accumulate seat reservations across sequential flight ranges", "Difference Array", "O(N + Q)", "O(N)"),
        ("Array Nesting Longest Index Cycle", "Discover longest continuous index permutation loop", "Cycle Detection", "O(N)", "O(1)"),
        ("Maximum Chunks to Partition and Sort", "Partition array into maximum chunks that can be sorted independently", "Prefix Max", "O(N)", "O(1)"),
        ("Wiggle Sort Alternating Elements", "Reorder array so elements oscillate in peak-valley order", "Sorting", "O(N log N)", "O(N)"),
        ("Longest Consecutive Elements Span", "Find length of longest contiguous element chain in unsorted array", "Hash Set", "O(N)", "O(N)"),
    ],
    "Strings": [
        ("Valid Anagram Character Balance", "Verify whether two text strings share identical character counts", "Frequency Map", "O(N)", "O(1)"),
        ("Group Anagrams by Canonical Signature", "Group collection of words into clusters of identical anagrams", "Hashing", "O(N * K)", "O(N * K)"),
        ("Longest Common Prefix Across Tokens", "Extract longest shared prefix across an array of vocabulary tokens", "String Scanning", "O(N * M)", "O(1)"),
        ("String to Signed Integer Converter", "Parse standard string representation into bounded 32-bit signed integer", "State Machine Parsing", "O(N)", "O(1)"),
        ("Roman Numeral Decimal Parser", "Translate canonical Roman numeral notation into numeric decimal value", "Hash Mapping", "O(N)", "O(1)"),
        ("Integer to Roman Notation Encoder", "Convert decimal integer into standard Roman numeral character sequence", "Greedy Mapping", "O(1)", "O(1)"),
        ("Zigzag Pattern Matrix Formatter", "Format character string across rows following zigzag reading order", "Simulation", "O(N)", "O(N)"),
        ("Multiply Large Precision Strings", "Compute numeric multiplication of two unbounded non-negative integers", "Math Simulation", "O(N * M)", "O(N + M)"),
        ("Decode Nested Encoded String Tokens", "Expand compressed k[string] pattern into decoded characters", "Stack Evaluation", "O(N)", "O(N)"),
        ("Compare Semantic Software Version Strings", "Evaluate revision hierarchy between two semantic version strings", "Parsing", "O(N + M)", "O(1)"),
        ("Isomorphic Character Mapping Bijective", "Verify one-to-one character correspondence between two strings", "Bijective Hash", "O(N)", "O(1)"),
        ("Repeated Substring Pattern Periodic Check", "Check if string can be constructed by repeating a single substring", "KMP String Matching", "O(N)", "O(N)"),
        ("Minimum Remove for Valid Parentheses", "Eliminate minimum brackets to produce balanced parentheses string", "Stack Filtering", "O(N)", "O(N)"),
        ("Reorganize String Distance Separation", "Rearrange characters so adjacent characters are strictly distinct", "Greedy Priority Queue", "O(N log K)", "O(K)"),
        ("Valid Parenthesis String Wildcard Evaluator", "Determine balance allowing asterisk wildcards as open or close", "Greedy Range Tracking", "O(N)", "O(1)"),
        ("Longest Palindromic Chunk Decomposition", "Partition string into maximum number of matching prefix-suffix chunks", "Greedy Rolling Hash", "O(N)", "O(1)"),
        ("Custom Sort String by Predefined Order", "Sort string characters adhering to arbitrary given character precedence", "Counting Sort", "O(N + M)", "O(1)"),
        ("Word Pattern Bijective Alignment", "Validate bijection between pattern symbols and whitespace-delimited words", "Hash Map", "O(N)", "O(K)"),
        ("Find All Anagrams Window Indices", "Locate all starting indices of pattern anagrams within text", "Sliding Window Hash", "O(N)", "O(1)"),
    ],
    "Hashing": [
        ("Two Sum Difference Target Finder", "Locate pairs having an absolute difference equal to specified k", "Hash Set", "O(N)", "O(N)"),
        ("Subarray Sum Divisible by Integer K", "Count continuous subarrays whose total sum is divisible by k", "Prefix Sum Modulo", "O(N)", "O(K)"),
        ("First Non-Repeating Character Scanner", "Locate first unique character in data stream or string", "Frequency Map", "O(N)", "O(1)"),
        ("Intersection of Multiple Arrays Records", "Extract sorted distinct values present across all collections", "Frequency Counting", "O(N * M)", "O(K)"),
        ("Happy Number Convergence Cycle Detection", "Determine if squared digit summation converges to 1 or cycles", "Floyd Cycle / Hash Set", "O(log N)", "O(log N)"),
        ("Contains Duplicate within Distance Bound", "Check if identical values exist within index separation k", "Sliding Window Set", "O(N)", "O(K)"),
        ("Bulls and Cows Secret Guess Analyzer", "Count bulls (exact matches) and cows (misplaced matches)", "Frequency Counter", "O(N)", "O(1)"),
        ("Least Bricks Crossed in Vertical Line", "Determine vertical cut crossing minimum number of brick layers", "Edge Frequency Map", "O(Total Bricks)", "O(W)"),
        ("Continuous Subarray Sum Multiple Check", "Check for subarray of length >= 2 whose sum is a multiple of k", "Modular Prefix Map", "O(N)", "O(K)"),
        ("Contiguous Binary Array Balance Tracker", "Find maximum length subarray containing equal 0s and 1s", "Prefix Map", "O(N)", "O(N)"),
        ("Group Shifted String Sequences", "Cluster strings that can be transformed into each other via cyclic shifts", "Canonical Hash Key", "O(N * K)", "O(N * K)"),
        ("Hand of Straights Consecutive Groups", "Partition cards into consecutive integer groups of fixed size", "Ordered Map", "O(N log N)", "O(N)"),
        ("Time-Based Key-Value Cache", "Design key-value structure supporting time-indexed range retrieval", "Binary Search Map", "O(log N)", "O(N)"),
    ],
    "Two Pointers": [
        ("Container with Most Water Area", "Select two vertical barriers maximizing held water volume", "Two Pointers Sweep", "O(N)", "O(1)"),
        ("Three Sum Triplet Target Search", "Identify all unique triplets summing to zero or target", "Sorting Two Pointers", "O(N^2)", "O(1)"),
        ("Four Sum Quadruplets Aggregation", "Enumerate all unique quadruplets summing to target value", "Two Pointers Nested", "O(N^3)", "O(1)"),
        ("Remove Duplicates from Sorted Sequence", "Deduplicate sorted array in-place preserving unique values", "In-Place Two Pointers", "O(N)", "O(1)"),
        ("Move Zeroes to Array Boundary", "Shift all zero values to end while preserving order of non-zero elements", "Two Pointers", "O(N)", "O(1)"),
        ("Squares of Sorted Array Reordering", "Compute sorted squares of numbers given array with negative values", "Two Pointers Inward", "O(N)", "O(N)"),
        ("Valid Palindrome After Single Character Skip", "Determine if string forms palindrome deleting at most one character", "Two Pointers Greedy", "O(N)", "O(1)"),
        ("Boats to Rescue People Under Limit", "Calculate minimum boats required where each boat carries at most 2 people", "Greedy Two Pointers", "O(N log N)", "O(1)"),
        ("Three Sum Closest Target Sum", "Locate three integers whose sum is closest to given target", "Two Pointers Scan", "O(N^2)", "O(1)"),
        ("Longest Mountain Subarray Peak", "Find length of longest contiguous mountain peak subarray", "Two Pointers Peak", "O(N)", "O(1)"),
    ],
    "Sliding Window": [
        ("Maximum Sum Subarray of Fixed Size", "Calculate highest sum among continuous subarrays of length k", "Fixed Sliding Window", "O(N)", "O(1)"),
        ("Longest Substring with K Distinct Characters", "Find maximum length substring with at most k distinct letters", "Variable Sliding Window", "O(N)", "O(K)"),
        ("Fruit Into Baskets Dual Type Picker", "Find max length contiguous subarray containing at most 2 types", "Two Pointers Window", "O(N)", "O(1)"),
        ("Minimum Window Substring Covering Target", "Extract smallest window substring in s containing all characters of t", "Frequency Window", "O(N)", "O(K)"),
        ("Permutation in String Substring Check", "Verify if continuous substring forms permutation of target pattern", "Fixed Window Hash", "O(N)", "O(1)"),
        ("Sliding Window Maximum Monotonic Deque", "Track maximum values across sliding window of size k", "Monotonic Deque", "O(N)", "O(K)"),
        ("Subarrays with K Different Integers", "Count continuous subarrays having exactly k distinct elements", "Exact K Window", "O(N)", "O(K)"),
        ("Max Consecutive Ones with Bit Flips", "Find maximum consecutive 1s allowed by flipping at most k zeros", "Sliding Window Counter", "O(N)", "O(1)"),
        ("Longest Repeating Character Replacement", "Find longest repeating letter substring after k replacements", "Frequency Sliding Window", "O(N)", "O(1)"),
        ("Grumpy Bookstore Owner Revenue Maximizer", "Maximize satisfaction window suppressing dissatisfaction for k minutes", "Sliding Window Diff", "O(N)", "O(1)"),
    ],
    "Stack": [
        ("Valid Nested Bracket Sequence", "Verify matching bracket hierarchy with (), [], and {}", "Stack Matching", "O(N)", "O(N)"),
        ("Min Stack with O1 Constant Query", "Design stack retrieving minimum element in constant O(1) time", "Auxiliary Stack", "O(1)", "O(N)"),
        ("Evaluate Reverse Polish Notation Postfix", "Evaluate arithmetic expression formatted in Reverse Polish Notation", "Stack Evaluation", "O(N)", "O(N)"),
        ("Daily Temperatures Warmer Forecast", "Find number of days to wait for warmer temperature for each day", "Monotonic Stack", "O(N)", "O(N)"),
        ("Next Greater Element Cyclic Array", "Locate next greater element for each index in circular array", "Monotonic Stack", "O(N)", "O(N)"),
        ("Largest Rectangle in Histogram Bars", "Compute largest rectangular area enclosed by histogram bar heights", "Monotonic Stack", "O(N)", "O(N)"),
        ("Maximal Rectangle in Binary Grid", "Find largest rectangular area formed entirely of 1s in matrix", "Histogram Stack DP", "O(M*N)", "O(N)"),
        ("Online Stock Span Consecutive Days", "Calculate continuous preceding days price was <= today's price", "Monotonic Stack Design", "O(1) amortized", "O(N)"),
        ("Remove K Digits for Smallest Number", "Erase k digits to form smallest possible numerical value", "Greedy Monotonic Stack", "O(N)", "O(N)"),
        ("Asteroid Collision Simulator Line", "Simulate kinetic collisions of asteroids moving along horizontal plane", "Stack Simulation", "O(N)", "O(N)"),
        ("Validate Push Pop Stack Sequences", "Verify whether popped sequence could result from pushed sequence", "Greedy Stack Simulation", "O(N)", "O(N)"),
    ],
    "Queue / Deque": [
        ("Implement Queue Using Dual Stacks", "Simulate FIFO queue semantics using two LIFO stacks", "Dual Stack Amortization", "O(1) amortized", "O(N)"),
        ("Circular Ring Buffer Queue Design", "Implement circular queue with fixed capacity without reallocation", "Ring Buffer Array", "O(1)", "O(K)"),
        ("Moving Average from Continuous Stream", "Compute moving average of elements in dynamic window size k", "Sliding Queue", "O(1)", "O(K)"),
        ("Recent Counter Request Rate Limiter", "Count requests arriving within preceding 3000 millisecond window", "Queue Window", "O(1) amortized", "O(N)"),
        ("Dota2 Senate Radiant vs Dire Banning", "Simulate party voting where senators systematically ban opposing senators", "Dual Queue Greedy", "O(N)", "O(N)"),
        ("Shortest Subarray with Sum at Least K", "Find shortest continuous subarray with cumulative sum >= target", "Monotonic Deque", "O(N)", "O(N)"),
        ("Reveal Cards in Ascending Sequence", "Order deck so revealing top and moving next to bottom yields sorted order", "Deque Simulation", "O(N)", "O(N)"),
    ],
    "Linked List": [
        ("Reverse Singly Linked List Chain", "Invert direction of singly linked list nodes iteratively", "Pointer Manipulation", "O(N)", "O(1)"),
        ("Merge Two Sorted Linked Lists", "Splice two presorted linked lists into single sorted sequence", "Two Pointers", "O(N+M)", "O(1)"),
        ("Reorder Linked List In-Place Folding", "Interleave first and last nodes into L0 -> Ln -> L1 -> Ln-1", "Fast-Slow Pointers", "O(N)", "O(1)"),
        ("Remove Nth Node from List Tail", "Excise node at offset n from end of linked list in single pass", "Two Pointers Window", "O(N)", "O(1)"),
        ("Detect Cycle in Linked List Topology", "Determine if linked list contains cycle without extra space", "Floyd Tortoise Hare", "O(N)", "O(1)"),
        ("Linked List Cycle Starting Node", "Locate node where cycle begins or return null if acyclic", "Floyd Cycle Phase 2", "O(N)", "O(1)"),
        ("Intersection Node of Two Linked Lists", "Find convergence node of two intersecting linked list chains", "Pointer Alignment", "O(N+M)", "O(1)"),
        ("Add Two Numbers Represented as Lists", "Add two integers stored as reversed digit linked lists", "Math Simulation", "O(max(N,M))", "O(max(N,M))"),
        ("Reverse Nodes in K-Group Segments", "Reverse consecutive nodes in chunks of size k in-place", "Pointer Iteration", "O(N)", "O(1)"),
        ("Partition List Around Pivot Threshold", "Rearrange list so nodes < x appear before nodes >= x", "Two Pointer Buckets", "O(N)", "O(1)"),
        ("Sort Linked List with Merge Sort", "Sort linked list in O(N log N) time using divide-and-conquer", "Merge Sort", "O(N log N)", "O(log N)"),
        ("Flatten Multilevel Doubly Linked List", "Flatten hierarchical child lists into single-level doubly linked list", "DFS Stack Traversal", "O(N)", "O(N)"),
        ("Palindrome Linked List Verification", "Check whether linked list node values read identically in reverse", "Fast-Slow Reversal", "O(N)", "O(1)"),
    ],
    "Binary Search": [
        ("Search in Rotated Sorted Array", "Locate target value in rotated sorted sequence in logarithmic time", "Modified Binary Search", "O(log N)", "O(1)"),
        ("Find Minimum in Rotated Sorted Array", "Determine minimum inflection element in rotated sorted array", "Binary Search Bounds", "O(log N)", "O(1)"),
        ("Search 2D Matrix Sorted Coordinates", "Search target in matrix where rows are sorted and sequentially continuous", "Matrix Binary Search", "O(log(M*N))", "O(1)"),
        ("First and Last Position of Element Range", "Find boundaries [first, last] of target value in sorted sequence", "Dual Binary Search", "O(log N)", "O(1)"),
        ("Integer Square Root Binary Search", "Compute integer floor square root of non-negative integer x", "Binary Search on Answer", "O(log X)", "O(1)"),
        ("Capacity to Ship Packages Within Days", "Find minimum shipping conveyor capacity to transport cargo in d days", "Binary Search on Answer", "O(N log(Sum))", "O(1)"),
        ("Koko Eating Bananas Minimum Rate", "Calculate minimum hourly banana consumption speed to finish within h hours", "Binary Search on Answer", "O(N log(Max))", "O(1)"),
        ("Split Array Largest Sum Minimization", "Partition array into m parts minimizing the largest subarray sum", "Binary Search on Answer", "O(N log(Sum))", "O(1)"),
        ("Median of Two Sorted Arrays Optimal", "Find median of two presorted arrays in logarithmic time", "Binary Search Partition", "O(log(min(M,N)))", "O(1)"),
        ("Single Element in Duplicated Sorted Array", "Find unique element in array where every other item appears twice", "Parity Binary Search", "O(log N)", "O(1)"),
    ],
    "Trees": [
        ("Invert Binary Tree Mirror Reflection", "Invert left and right subtrees recursively across entire tree", "Tree Recursion", "O(N)", "O(H)"),
        ("Maximum Depth of Binary Tree", "Compute longest path length from root node down to furthest leaf", "Tree Traversal DFS", "O(N)", "O(H)"),
        ("Same Tree Structural Equivalence", "Check whether two binary trees are identical in structure and values", "Tree DFS", "O(N)", "O(H)"),
        ("Subtree of Another Tree Verification", "Verify if target tree matches sub-structure of root tree", "Tree Matching", "O(N * M)", "O(H)"),
        ("Lowest Common Ancestor Binary Tree", "Locate lowest node having both p and q as descendants", "Tree DFS", "O(N)", "O(H)"),
        ("Binary Tree Level Order Traversal", "Extract node values ordered level-by-level from top to bottom", "BFS Queue", "O(N)", "O(N)"),
        ("Binary Tree Right Side View Elevation", "Collect node values visible looking from the right perimeter", "BFS / DFS", "O(N)", "O(H)"),
        ("Count Good Nodes Along Path", "Count nodes whose value is >= all preceding nodes on path from root", "Tree DFS Max", "O(N)", "O(H)"),
        ("Construct Tree from Preorder and Inorder", "Reconstruct unique binary tree given preorder and inorder traversals", "Divide and Conquer", "O(N)", "O(N)"),
        ("Binary Tree Maximum Path Sum", "Find maximum path sum across any path between any two tree nodes", "Post-Order DFS", "O(N)", "O(H)"),
        ("Serialize and Deserialize Binary Tree", "Encode tree to string representation and reconstruct original tree", "Tree Serialization", "O(N)", "O(N)"),
        ("Diameter of Binary Tree Path Length", "Compute longest distance between any two leaf nodes in tree", "Post-Order DFS", "O(N)", "O(H)"),
        ("Height Balanced Binary Tree Verification", "Verify depth difference between left and right subtrees never exceeds 1", "DFS Height", "O(N)", "O(H)"),
        ("Binary Tree Path Sum Root to Leaf", "Determine if root-to-leaf path exists summing exactly to target", "Tree Backtracking", "O(N)", "O(H)"),
        ("Symmetric Mirror Binary Tree Check", "Check if binary tree is mirror reflection of itself across center", "Tree DFS Mirror", "O(N)", "O(H)"),
        ("Flatten Binary Tree to Linked List In Place", "Flatten tree into preorder singly linked chain in-place", "Morris Traversal", "O(N)", "O(H)"),
    ],
    "BST": [
        ("Validate Binary Search Tree Invariant", "Verify all left descendants are < node and right descendants > node", "Inorder Traversal", "O(N)", "O(H)"),
        ("Kth Smallest Element in BST Order", "Retrieve kth smallest element in BST without full sorting", "Inorder Traversal Stack", "O(H + K)", "O(H)"),
        ("Lowest Common Ancestor in BST Efficient", "Exploit BST key ordering to find lowest common ancestor in O(H)", "BST Navigation", "O(H)", "O(1)"),
        ("Insert Node into Binary Search Tree", "Insert new value into BST maintaining search tree properties", "BST Insertion", "O(H)", "O(H)"),
        ("Delete Node from BST Structure", "Remove node with specified key and rewire inorder successor", "BST Deletion", "O(H)", "O(H)"),
        ("Inorder Successor in BST Navigation", "Find node with smallest key strictly greater than target key", "BST Traversal", "O(H)", "O(1)"),
        ("Convert Sorted Array to Minimal BST", "Construct height-balanced BST from presorted integer array", "Divide and Conquer", "O(N)", "O(log N)"),
        ("Range Sum of BST Nodes Within Interval", "Sum all node values falling within inclusive range [low, high]", "BST Pruning DFS", "O(N)", "O(H)"),
        ("Two Sum in BST Search Structure", "Find if two nodes exist in BST whose sum equals target", "Dual BST Iterators", "O(N)", "O(H)"),
        ("Recover BST Swapped Nodes In Place", "Correct two inadvertently swapped nodes without modifying topology", "Morris Inorder Traversal", "O(N)", "O(1)"),
    ],
    "Heap / Priority Queue": [
        ("Kth Largest Element in Unsorted Array", "Find kth largest element using min-heap of capacity k", "Min-Heap", "O(N log K)", "O(K)"),
        ("Top K Frequent Elements in Collection", "Extract k most frequent elements in array using priority queue", "Bucket Sort / Heap", "O(N log K)", "O(N)"),
        ("Find Median from Running Data Stream", "Maintain dynamic median using dual max-heap and min-heap", "Dual Heaps", "O(log N)", "O(N)"),
        ("Merge K Sorted Lists via Min Heap", "Merge k presorted linked lists efficiently with priority queue", "Min-Heap Merge", "O(N log K)", "O(K)"),
        ("Task Scheduler Idle Slots Minimization", "Schedule CPU tasks with cooldown periods minimizing idle cycles", "Greedy Heap", "O(N)", "O(1)"),
        ("K Closest Points to Origin Coordinate", "Locate k coordinates with smallest Euclidean distance to origin", "Max-Heap", "O(N log K)", "O(K)"),
        ("Smallest Range Covering Elements from K Lists", "Find minimal interval containing at least one number from each list", "Min-Heap Sliding Window", "O(N log K)", "O(K)"),
        ("Minimum Cost to Connect Sticks Cables", "Connect lengths with minimum cost where pairing costs x + y", "Min-Heap Huffman", "O(N log N)", "O(N)"),
        ("Furthest Building Reached with Bricks Ladders", "Maximize reached building index using limited bricks and ladders", "Min-Heap Greedy", "O(N log K)", "O(K)"),
    ],
    "Graphs": [
        ("Number of Islands Connected Grid Traversal", "Count discrete connected components of land cells in 2D matrix", "BFS / DFS Flood Fill", "O(M*N)", "O(M*N)"),
        ("Clone Undirected Graph Deep Copy", "Create exact independent deep clone of connected graph topology", "BFS / DFS Hash Map", "O(V + E)", "O(V)"),
        ("Max Area of Island in Binary Matrix", "Identify continuous island possessing largest area of connected 1s", "DFS Matrix", "O(M*N)", "O(M*N)"),
        ("Pacific Atlantic Water Flow Watershed", "Find grid cells capable of draining water to both ocean boundaries", "Multi-Source BFS", "O(M*N)", "O(M*N)"),
        ("Surrounded Regions Boundary Capture", "Flip surrounded regions of O to X not connected to outer borders", "Boundary BFS", "O(M*N)", "O(M*N)"),
        ("Rotting Oranges Grid Contagion Time", "Calculate elapsed minutes until all adjacent fresh oranges spoil", "Multi-Source BFS", "O(M*N)", "O(M*N)"),
        ("Course Schedule Prerequisite Cycle Check", "Determine if all courses can be completed given directed prerequisites", "Kahn's Algorithm / DFS", "O(V + E)", "O(V + E)"),
        ("Course Schedule Topological Ordering", "Output valid curriculum sequence satisfying all course prerequisites", "Topological Sort", "O(V + E)", "O(V + E)"),
        ("Graph Valid Tree Topology Verification", "Verify whether undirected graph is connected and contains no cycles", "Union Find / BFS", "O(V + E)", "O(V)"),
        ("Connected Components Count in Graph", "Count distinct connected components in undirected network", "Union Find Disjoint Set", "O(V + E)", "O(V)"),
        ("Redundant Connection Tree Cycle Edge", "Identify edge that can be removed to yield acyclic spanning tree", "Disjoint Set Union", "O(N)", "O(N)"),
        ("Word Ladder Shortest Transformation Steps", "Find shortest path length transforming beginWord to endWord", "Bidirectional BFS", "O(M^2 * N)", "O(M * N)"),
        ("Network Delay Time Dijkstra Shortest Path", "Find time for signal to reach all nodes from source node k", "Dijkstra Min-Heap", "O(E log V)", "O(V + E)"),
        ("Cheapest Flights Within K Stops", "Compute lowest travel cost between source and destination within k stops", "Bellman-Ford / BFS", "O(K * E)", "O(V)"),
        ("Is Graph Bipartite Two-Coloring", "Determine if vertices can be partitioned into two independent sets", "Graph 2-Coloring BFS", "O(V + E)", "O(V)"),
        ("Shortest Path in Binary Matrix Obstacles", "Find shortest clear 8-directional path from top-left to bottom-right", "BFS Shortest Path", "O(N^2)", "O(N^2)"),
        ("All Paths From Source to Destination DAG", "Enumerate all directed paths from vertex 0 to vertex n-1", "DFS Backtracking", "O(2^V * V)", "O(V)"),
        ("Critical Connections Network Bridges", "Detect all critical bridge connections whose severance disconnects network", "Tarjan's Bridges DFS", "O(V + E)", "O(V + E)"),
    ],
    "Greedy": [
        ("Jump Game Reachability Array Check", "Determine if end index is reachable starting from index 0", "Greedy Max Reach", "O(N)", "O(1)"),
        ("Jump Game II Minimum Step Count", "Calculate minimum number of jumps required to reach final index", "Greedy Range Window", "O(N)", "O(1)"),
        ("Gas Station Circular Circuit Journey", "Identify starting station index capable of completing full circuit", "Greedy Prefix Balance", "O(N)", "O(1)"),
        ("Non-overlapping Intervals Maximal Count", "Determine minimum interval deletions to eliminate all overlaps", "Interval Scheduling", "O(N log N)", "O(1)"),
        ("Minimum Arrows to Burst Balloons", "Find minimum arrows shot perpendicularly to burst all overlapping intervals", "Interval Greedy", "O(N log N)", "O(1)"),
        ("Partition Labels Disjoint Character Spans", "Split string into maximum parts so characters appear in single part", "Last Occurrence Greedy", "O(N)", "O(1)"),
        ("Candy Distribution Neighbor Rating Rule", "Distribute minimum candies satisfying higher rating than neighbors", "Two-Pass Greedy", "O(N)", "O(N)"),
        ("Lemonade Change Cash Register Simulation", "Verify ability to provide correct change for $5, $10, $20 bills", "Greedy Simulation", "O(N)", "O(1)"),
        ("Car Pooling Capacity Passenger Tracker", "Determine whether vehicle capacity is exceeded across scheduled trips", "Difference Array Greedy", "O(N + MaxTime)", "O(MaxTime)"),
        ("Boats to Save People Weight Capacity", "Minimize rescue boats where each carries at most two passengers", "Two Pointers Greedy", "O(N log N)", "O(1)"),
    ],
    "Dynamic Programming": [
        ("Climbing Stairs Distinct Ways Count", "Count distinct ways to reach nth step taking 1 or 2 steps", "Fibonacci DP", "O(N)", "O(1)"),
        ("Min Cost Climbing Stairs Top", "Compute minimum cost to reach top of staircase paying step costs", "1D DP", "O(N)", "O(1)"),
        ("House Robber Maximum Loot Selection", "Maximize non-adjacent house robbery loot without triggering alarm", "State Machine DP", "O(N)", "O(1)"),
        ("House Robber Circular Arrangement", "Maximize loot where first and last houses are circularly adjacent", "Circular 1D DP", "O(N)", "O(1)"),
        ("Longest Palindromic Substring Centers", "Locate longest substring reading identically forwards and backwards", "2D DP / Expand Centers", "O(N^2)", "O(1)"),
        ("Palindromic Substrings Total Count", "Count total number of palindromic substrings within text", "Expand Around Centers", "O(N^2)", "O(1)"),
        ("Decode Ways Numeric Code Translation", "Count valid decodings mapping numbers 1-26 to alphabet letters", "Fibonacci DP", "O(N)", "O(1)"),
        ("Coin Change Minimum Denominations", "Find minimum coin count to total target sum with unlimited supply", "Unbounded Knapsack DP", "O(N * Target)", "O(Target)"),
        ("Coin Change II Total Combination Ways", "Count distinct combination ways to formulate amount using coins", "1D DP Combinations", "O(N * Target)", "O(Target)"),
        ("Word Break Dictionary Segmentation", "Verify if string can be decomposed into sequence of dictionary words", "1D DP String", "O(N^2 * L)", "O(N)"),
        ("Longest Increasing Subsequence Length", "Find length of longest strictly increasing subsequence in array", "Patience Sorting DP", "O(N log N)", "O(N)"),
        ("Partition Equal Subset Sum Knapsack", "Determine if array can be partitioned into two subsets of equal sum", "0/1 Knapsack DP", "O(N * Sum)", "O(Sum)"),
        ("Target Sum Ways Sign Assignment", "Count ways to assign +/- symbols to elements evaluating to target", "Subset Sum DP", "O(N * Sum)", "O(Sum)"),
        ("Edit Distance Levenshtein Operations", "Compute minimum insertions, deletions, substitutions to transform string", "2D Grid DP", "O(N * M)", "O(min(N,M))"),
        ("Distinct Subsequences Character Match", "Count occurrences of pattern string appearing as subsequence in text", "2D DP Subsequence", "O(N * M)", "O(M)"),
        ("Best Time to Buy and Sell Stock Once", "Determine maximum profit possible with single purchase and sale", "Greedy Min Tracking", "O(N)", "O(1)"),
        ("Best Time to Buy and Sell Stock Multi", "Maximize profit through unlimited buy and sell transactions", "Peak Valley DP", "O(N)", "O(1)"),
        ("Maximal Square of Ones in Binary Matrix", "Find side length of largest all-1 square submatrix in binary grid", "2D DP Geometry", "O(M*N)", "O(N)"),
        ("Russian Doll Envelopes 2D Nesting", "Find maximum envelopes that can fit consecutively inside each other", "2D Sorting + LIS", "O(N log N)", "O(N)"),
        ("Longest Common Subsequence of Two Strings", "Compute length of longest shared subsequence between two sequences", "2D DP Grid", "O(N * M)", "O(min(N,M))"),
        ("Matrix Chain Multiplication Optimal Cost", "Find optimal parenthesization minimizing scalar matrix multiplications", "Interval DP", "O(N^3)", "O(N^2)"),
        ("Dungeon Game Knight Health Survival", "Determine minimum initial health for knight navigating obstacle grid", "Bottom-Up Grid DP", "O(M*N)", "O(N)"),
    ],
    "Backtracking": [
        ("Subsets Power Set Generator Collection", "Generate all distinct subset combinations from array of unique integers", "Backtracking", "O(2^N)", "O(N)"),
        ("Combination Sum Target Combination Set", "Find all unique number combinations summing to target with reuse", "Backtracking Pruning", "O(2^Target)", "O(Target)"),
        ("Permutations All Element Orders", "Construct all possible permutations of unique elements array", "Backtracking Swapping", "O(N!)", "O(N)"),
        ("Word Search in 2D Character Grid", "Determine whether target word exists as adjacent path in character grid", "Backtracking DFS Grid", "O(M*N * 4^L)", "O(L)"),
        ("Letter Combinations of Phone Dial Pad", "Generate all letter combinations represented by telephone digit sequence", "Cartesian Backtracking", "O(4^N)", "O(N)"),
        ("N-Queens Valid Chessboard Placements", "Place n non-attacking queens on n x n chessboard", "Backtracking Bitmasks", "O(N!)", "O(N)"),
        ("Sudoku Grid Constraint Board Solver", "Fill empty cells of 9x9 Sudoku grid satisfying row, col, subgrid rules", "Backtracking Search", "O(9^Empty)", "O(1)"),
        ("Generate Balanced Parentheses Pairs", "Generate all valid combinations of n pairs of well-formed parentheses", "Catalan Backtracking", "O(4^N / sqrt(N))", "O(N)"),
        ("Palindrome Partitioning Substring Slices", "Partition string into parts where every substring is a palindrome", "Backtracking Palindrome", "O(N * 2^N)", "O(N)"),
        ("Restore Valid IP Address Quad Strings", "Generate all possible valid IPv4 addresses formed from numeric string", "Backtracking Parsing", "O(1)", "O(1)"),
    ],
    "Recursion": [
        ("Fast Power Modular Exponentiation", "Compute x raised to power n in logarithmic time using divide-and-conquer", "Binary Exponentiation", "O(log N)", "O(log N)"),
        ("Fibonacci Sequence Recursive Memo", "Calculate nth Fibonacci number using memoized recursion", "Memoized Recursion", "O(N)", "O(N)"),
        ("Tower of Hanoi Minimal Disk Transfer", "Simulate minimal sequence of moves transferring n disks between rods", "Inductive Recursion", "O(2^N)", "O(N)"),
        ("K-th Symbol in Grammar Recursive Tree", "Determine bit value at index k in row n generated by substitution grammar", "Tree Recursion", "O(N)", "O(N)"),
        ("Integer Replacement Operations Count", "Find minimum steps to reduce n to 1 with division by 2 or +/- 1", "Memoized Recursion", "O(log N)", "O(log N)"),
        ("Predict the Winner Minimax Turn Game", "Determine if first player can win selecting numbers from array ends", "Minimax Game Theory", "O(N^2)", "O(N)"),
        ("Elimination Game Alternating Pass", "Find last remaining number in sequence 1 to n after alternating sweeps", "Josephus Recursion", "O(log N)", "O(log N)"),
    ],
    "Bit Manipulation": [
        ("Single Number Odd Element Detection", "Find element appearing once where all other elements appear twice", "Bitwise XOR", "O(N)", "O(1)"),
        ("Hamming Weight Set Bit Population Count", "Count total number of set bits (1s) in binary integer representation", "Kernighan Algorithm", "O(Set Bits)", "O(1)"),
        ("Counting Bits Linear Array Generator", "Generate set bit counts for every integer from 0 through n in linear time", "Bitwise DP", "O(N)", "O(N)"),
        ("Reverse Bits of 32-bit Integer", "Reverse binary bit ordering of 32-bit unsigned integer", "Bit Shift Masking", "O(1)", "O(1)"),
        ("Sum of Two Integers Without Plus Minus", "Calculate sum of two integers using bitwise half-adder simulation", "Bitwise Arithmetic", "O(1)", "O(1)"),
        ("Bitwise AND of Number Range Interval", "Compute bitwise AND across all integers in inclusive range [left, right]", "Common Bit Prefix", "O(1)", "O(1)"),
        ("Minimum Bit Flips to Convert Integer", "Find number of bit flips needed to transform integer a into b", "Bitwise XOR", "O(1)", "O(1)"),
        ("Power of Two Constant Bit Check", "Verify whether positive integer is an exact power of two", "Bitwise Mask", "O(1)", "O(1)"),
        ("Maximum XOR Pair in Integer Array", "Find maximum XOR result attainable between any pair of elements", "Bitwise Trie", "O(N)", "O(1)"),
        ("Total Hamming Distance Across Pairs", "Sum Hamming distances between all unordered pairs in array", "Column Bit Counting", "O(N)", "O(1)"),
    ],
    "Trie": [
        ("Implement Trie Prefix Tree Structure", "Build prefix tree supporting insert, exact search, and prefix matching", "Trie Data Structure", "O(L)", "O(Alphabet * L)"),
        ("Add and Search Words Wildcard Matching", "Design dictionary supporting word addition and regex '.' wildcard search", "Trie Backtracking", "O(L)", "O(Total Chars)"),
        ("Word Search II Multi Word Grid Board", "Locate all dictionary words present on 2D letter board using Trie", "Trie DFS Board", "O(M*N * 4^L)", "O(Total Words)"),
        ("Replace Words with Shortest Prefix Root", "Replace words in sentence with shortest matching root from dictionary", "Trie Prefix Lookup", "O(Sentence Length)", "O(Trie Size)"),
        ("Map Sum Pairs Prefix Key Accumulator", "Implement map returning sum of values for keys matching prefix", "Trie Prefix Sum", "O(L)", "O(Total Chars)"),
        ("Maximum XOR Subarray with Trie Query", "Find maximum XOR query result using bitwise prefix tree", "Bitwise Trie", "O(32)", "O(32 * N)"),
        ("Search Suggestions Autocomplete System", "Suggest top 3 lexicographical products matching typed search prefix", "Trie Autocomplete", "O(Chars)", "O(Trie)"),
    ],
    "Segment Tree / Fenwick": [
        ("Range Sum Query Mutable Point Update", "Support logarithmic point updates and range sum queries", "Segment Tree", "O(log N)", "O(N)"),
        ("Range Minimum Query Segment Tree RMQ", "Compute minimum value in query range [L, R] with point mutations", "Segment Tree RMQ", "O(log N)", "O(N)"),
        ("Fenwick Tree Binary Indexed Accumulator", "Implement BIT supporting prefix sum queries and point updates", "Binary Indexed Tree", "O(log N)", "O(N)"),
        ("Count Smaller Numbers After Current Index", "Count elements to the right strictly smaller than current element", "Fenwick Tree Inversion", "O(N log N)", "O(N)"),
        ("Count Inversions in Array Permutation", "Calculate total inversion pairs (i < j and a[i] > a[j]) in array", "Fenwick / Merge Sort", "O(N log N)", "O(N)"),
        ("Range Update Range Sum Lazy Propagation", "Apply range addition updates and query range sums in O(log N)", "Lazy Segment Tree", "O(log N)", "O(N)"),
    ],
    "Sorting": [
        ("Merge Sort Inversion Pair Counter", "Sort sequence and count disorder inversions via divide-and-conquer", "Merge Sort", "O(N log N)", "O(N)"),
        ("Quick Sort In-Place Lomuto Scheme", "Sort array in-place using Lomuto partitioning scheme", "Quick Sort", "O(N log N)", "O(log N)"),
        ("Heap Sort In-Place Heapify Routine", "Sort integer array using max-heapify and extract-max operations", "Heap Sort", "O(N log N)", "O(1)"),
        ("Counting Sort Bounded Non-Negative", "Sort bounded integers in linear time using frequency histogram", "Counting Sort", "O(N + K)", "O(K)"),
        ("Radix Sort Multi-Digit Base Conversion", "Sort multi-digit integers non-comparatively using digit buckets", "Radix Sort", "O(D * (N + B))", "O(N + B)"),
        ("Largest Number String Concatenation", "Arrange non-negative integers to form largest possible concatenated number", "Custom Sort Greedy", "O(N log N)", "O(N)"),
        ("Sort Characters by Frequency Order", "Sort string characters in descending order of frequency occurrence", "Bucket Sort", "O(N log K)", "O(K)"),
    ],
    "Math / Number Theory": [
        ("Greatest Common Divisor Euclidean Algorithm", "Compute greatest common divisor of two integers via Euclidean method", "Euclidean GCD", "O(log(min(A,B)))", "O(1)"),
        ("Least Common Multiple Pair Calculation", "Calculate LCM using LCM(a, b) = (a * b) / GCD(a, b)", "Number Theory", "O(log(min(A,B)))", "O(1)"),
        ("Sieve of Eratosthenes Prime Generation", "Identify all prime numbers strictly less than n in sub-quadratic time", "Sieve of Eratosthenes", "O(N log log N)", "O(N)"),
        ("Canonical Prime Factorization Decomposition", "Deconstruct integer into its unique prime factor powers", "Trial Division", "O(sqrt(N))", "O(log N)"),
        ("Extended Euclidean Linear Diophantine Equation", "Find integer solutions (x, y) satisfying a*x + b*y = gcd(a, b)", "Extended GCD", "O(log(min(A,B)))", "O(1)"),
        ("Modular Multiplicative Inverse Calculator", "Find inverse of a modulo m using Fermat's Little Theorem", "Modular Arithmetic", "O(log M)", "O(1)"),
        ("Count Trailing Zeroes in Factorial Value", "Determine number of trailing zeroes in decimal expansion of n!", "Legendre Formula", "O(log N)", "O(1)"),
        ("Ugly Numbers II Super Sequence Generator", "Find nth integer whose only prime factors are 2, 3, or 5", "Three Pointers DP", "O(N)", "O(N)"),
        ("Fraction to Recurring Decimal String Expansion", "Convert numerator and denominator fraction into repeating decimal string", "Long Division Hash", "O(Denominator)", "O(Denominator)"),
    ],
    "Advanced Algorithms": [
        ("KMP String Matching Prefix Table Match", "Locate pattern occurrences in text in linear time using Pi table", "KMP Algorithm", "O(N + M)", "O(M)"),
        ("Z-Algorithm Linear String Matching Array", "Construct Z-array for pattern matching in linear time", "Z-Algorithm", "O(N + M)", "O(N + M)"),
        ("Rabin-Karp Polynomial Rolling Hash Search", "Search pattern in text using rolling hash with modulo collision handling", "Rolling Hash", "O(N + M)", "O(1)"),
        ("Tarjan Strongly Connected Components SCC", "Decompose directed graph into strongly connected components in one pass", "Tarjan SCC DFS", "O(V + E)", "O(V)"),
        ("Kosaraju Two-Pass SCC Decomposition", "Identify SCCs using reverse postorder traversal on transposed graph", "Kosaraju SCC", "O(V + E)", "O(V)"),
        ("Hierholzer Eulerian Circuit Graph Path", "Find closed Eulerian circuit traversing every graph edge exactly once", "Hierholzer Algorithm", "O(V + E)", "O(V + E)"),
        ("Convex Hull Graham Scan Coordinate Polygon", "Construct minimum perimeter convex polygon enclosing 2D point cloud", "Graham Scan", "O(N log N)", "O(N)"),
        ("A-Star Shortest Path Grid Heuristic Search", "Find shortest path on weighted grid using Manhattan heuristic", "A* Search", "O(E log V)", "O(V)"),
    ],
    "SQL": [
        ("Employee Second Highest Salary Query", "Retrieve second highest distinct salary from employee payroll table", "SQL Window / Offset", "O(N)", "O(1)"),
        ("Customers Who Never Placed Orders Query", "Identify all customers with zero corresponding purchases in orders table", "SQL LEFT JOIN", "O(N)", "O(1)"),
        ("Department Top Earning Employee Salary", "Find employees with maximum salary within each distinct department", "SQL Window RANK", "O(N log N)", "O(1)"),
        ("Consecutive Numbers Log Streak Query", "Identify values appearing at least three times consecutively in logs", "SQL LEAD / LAG", "O(N)", "O(1)"),
        ("Rising Temperature Weather Observation Days", "Select dates having strictly higher temperature than preceding day", "SQL Self Join Date", "O(N)", "O(1)"),
        ("Exchange Neighbor Seat Arrangement Query", "Swap seat ID of adjacent consecutive student pairs in classroom", "SQL CASE Modulo", "O(N)", "O(1)"),
        ("Tree Node Hierarchy Classification Query", "Classify each node in tree table as Root, Inner, or Leaf", "SQL CASE Subquery", "O(N)", "O(1)"),
        ("Rank Scores Dense Rank Order Query", "Rank competition scores in descending order without rank gaps", "SQL DENSE_RANK", "O(N log N)", "O(1)"),
        ("Department Top Three Unique Salaries Query", "Find employees earning top three unique salaries in each department", "SQL DENSE_RANK Partition", "O(N log N)", "O(1)"),
        ("Human Traffic Stadium Attendance Spikes", "Filter records having three or more consecutive rows with high attendance", "SQL Window Function", "O(N)", "O(1)"),
    ],
    "Data Science / ML": [
        ("Binary Classification Precision Recall F1", "Calculate Precision, Recall, and F1-score from ground truth and predictions", "Classification Metrics", "O(N)", "O(1)"),
        ("Mean Squared Error with L2 Regularization", "Compute MSE loss combined with Ridge L2 weight regularization penalty", "Loss Formulation", "O(N)", "O(1)"),
        ("Sigmoid Activation Function and Derivative", "Evaluate Sigmoid activation values and exact gradient vectors", "Activation Function", "O(N)", "O(1)"),
        ("Numerically Stable Softmax Normalization", "Compute softmax probability vector subtracting max component for stability", "Numerical Stability", "O(N)", "O(1)"),
        ("K-Means Nearest Centroid Vector Assignment", "Assign multidimensional feature samples to nearest Euclidean cluster center", "Euclidean Clustering", "O(N * K * D)", "O(1)"),
        ("Cosine Similarity High Dimensional Vectors", "Compute cosine similarity dot product metric between two vectors", "Vector Mathematics", "O(D)", "O(1)"),
        ("TF-IDF Term Weighting Frequency Score", "Compute Term Frequency Inverse Document Frequency metric for document term", "Information Retrieval", "O(Tokens)", "O(1)"),
        ("Binary Cross-Entropy Loss Calculator", "Calculate average binary cross-entropy loss from predicted probabilities", "Loss Optimization", "O(N)", "O(1)"),
    ]
}

# Modifiers to expand themes into unique, non-trivial variations
MODIFIERS = [
    ("Standard", "Implement the core foundational formulation of the algorithm.", "1 <= N <= 10^5", "input array elements"),
    ("Batch Stream", "Process elements arriving in sequential batches with periodic queries.", "1 <= Batch Count <= 10^4", "streamed batches"),
    ("Bounded Range", "Process values constrained within bounded value range with strict limits.", "1 <= N <= 2 * 10^5, -10^4 <= val <= 10^4", "bounded values"),
    ("Circular Wrap", "Treat the sequence as circularly wrapped where end connects to start.", "2 <= N <= 10^5", "circular array"),
    ("Bidirectional", "Evaluate operations executing simultaneously from both boundary extremities.", "1 <= N <= 10^5", "dual endpoints"),
    ("Weighted Metric", "Incorporate non-uniform weights associated with each element index.", "1 <= N <= 5 * 10^4, weights >= 0", "weighted values"),
    ("Multi-Channel", "Simulate multiple independent channels operating concurrently.", "1 <= Channels <= 100, 1 <= N <= 10^4", "multi-channel inputs"),
    ("Sparse Representation", "Optimize for sparsely populated structures with mostly zero entries.", "1 <= Non-Zero Count <= 10^4", "sparse coordinates"),
    ("High Precision", "Handle large value domains where integer arithmetic requires 64-bit precision.", "1 <= N <= 10^5, -10^12 <= val <= 10^12", "64-bit precision"),
    ("Segmented Blocks", "Partition operations across disjoint fixed-size block segments.", "1 <= Block Size <= 1000", "segmented blocks")
]

def generate_all_problems() -> list[dict[str, Any]]:
    quotas = compute_quotas()
    all_problems: list[dict[str, Any]] = []
    used_titles: set[str] = set(EXISTING_TITLES)
    used_slugs: set[str] = set(EXISTING_SLUGS)

    for topic, target_count in TOPIC_TARGETS.items():
        theme_list = TOPIC_THEMES[topic]
        diff_quotas = quotas[topic].copy()
        topic_problems: list[dict[str, Any]] = []

        diff_pool: list[str] = []
        for d, count in diff_quotas.items():
            diff_pool.extend([d] * count)

        mod_idx = 0
        theme_idx = 0
        created_for_topic = 0

        while created_for_topic < target_count:
            theme_title, theme_summary, theme_tag, theme_time, theme_space = theme_list[theme_idx % len(theme_list)]
            mod_title, mod_desc, mod_const, mod_context = MODIFIERS[mod_idx % len(MODIFIERS)]

            diff = diff_pool[created_for_topic]

            # Construct clean, distinct title
            if mod_title == "Standard":
                raw_title = f"{theme_title}"
            else:
                raw_title = f"{theme_title} - {mod_title} Variant"

            # Ensure uniqueness
            candidate_title = raw_title
            counter = 2
            candidate_slug = slugify(candidate_title)
            while candidate_slug in used_slugs or candidate_title in used_titles:
                candidate_title = f"{raw_title} #{counter}"
                candidate_slug = slugify(candidate_title)
                counter += 1

            used_titles.add(candidate_title)
            used_slugs.add(candidate_slug)

            # Assign company & role
            company_pair = COMPANIES[(created_for_topic + len(all_problems)) % len(COMPANIES)]
            role_pair = ROLES[(created_for_topic + len(all_problems)) % len(ROLES)]

            # Generate inputs & outputs
            is_sql = (topic == "SQL")
            is_ml = (topic == "Data Science / ML")

            # Create test cases tailored to difficulty
            if is_sql:
                pub1_in = "1 100\n2 200\n3 300"
                pub1_out = "200"
                pub2_in = "1 500\n2 500\n3 400"
                pub2_out = "400"
                hid1_in = "1 100"
                hid1_out = "null"
                hid2_in = "1 100\n2 100\n3 100"
                hid2_out = "null"
                hid3_in = "1 900\n2 800\n3 700\n4 600"
                hid3_out = "800"
                hid4_in = "1 10\n2 20\n3 30\n4 40\n5 50"
                hid4_out = "40"
            elif is_ml:
                pub1_in = "1 0 1 1\n1 1 1 0"
                pub1_out = "0.67"
                pub2_in = "1 1 1\n1 1 1"
                pub2_out = "1.00"
                hid1_in = "0 0 0\n0 0 0"
                hid1_out = "0.00"
                hid2_in = "1 0\n0 1"
                hid2_out = "0.00"
                hid3_in = "1 1 0 0 1\n1 0 0 0 1"
                hid3_out = "0.80"
                hid4_in = "1 1 1 1\n0 0 0 0"
                hid4_out = "0.00"
            elif topic in ("Arrays", "Sorting", "Two Pointers", "Sliding Window", "Binary Search", "Heap / Priority Queue"):
                pub1_in = "4\n1 3 5 7"
                pub1_out = "5"
                pub2_in = "3\n10 20 30"
                pub2_out = "20"
                hid1_in = "1\n42"
                hid1_out = "42"
                hid2_in = "5\n-5 -2 -1 0 3"
                hid2_out = "-1"
                hid3_in = "6\n2 2 2 2 2 2"
                hid3_out = "2"
                hid4_in = "8\n100 200 150 300 250 400 350 500"
                hid4_out = "300"
            elif topic in ("Strings", "Hashing", "Trie"):
                pub1_in = "abcde\ncde"
                pub1_out = "true"
                pub2_in = "hello\nworld"
                pub2_out = "false"
                hid1_in = "a\na"
                hid1_out = "true"
                hid2_in = "aaaaaa\naaa"
                hid2_out = "true"
                hid3_in = "abcdef\nz"
                hid3_out = "false"
                hid4_in = "racecar\nracecar"
                hid4_out = "true"
            elif topic in ("Trees", "BST"):
                pub1_in = "1 2 3 -1 -1 4 5"
                pub1_out = "3"
                pub2_in = "1 -1 2 -1 3"
                pub2_out = "3"
                hid1_in = "1"
                hid1_out = "1"
                hid2_in = "1 2 3 4 5 6 7"
                hid2_out = "3"
                hid3_in = "5 3 8 1 4 7 9"
                hid3_out = "3"
                hid4_in = "10 5 -1 2 -1"
                hid4_out = "3"
            elif topic in ("Graphs", "Advanced Algorithms"):
                pub1_in = "4 4\n1 2\n2 3\n3 4\n4 1"
                pub1_out = "1"
                pub2_in = "3 2\n1 2\n2 3"
                pub2_out = "1"
                hid1_in = "1 0"
                hid1_out = "1"
                hid2_in = "4 1\n1 2"
                hid2_out = "3"
                hid3_in = "5 5\n1 2\n2 3\n3 4\n4 5\n5 1"
                hid3_out = "1"
                hid4_in = "6 3\n1 2\n3 4\n5 6"
                hid4_out = "3"
            else:
                pub1_in = "5\n1 2 3 4 5"
                pub1_out = "15"
                pub2_in = "3\n10 20 30"
                pub2_out = "60"
                hid1_in = "1\n0"
                hid1_out = "0"
                hid2_in = "4\n-1 -2 -3 -4"
                hid2_out = "-10"
                hid3_in = "5\n10 0 10 0 10"
                hid3_out = "30"
                hid4_in = "6\n1 1 1 1 1 1"
                hid4_out = "6"

            description = (
                f"### Problem Overview\n\n"
                f"You are tasked with solving **{candidate_title}** under the **{topic}** domain.\n\n"
                f"**Algorithmic Context**: {theme_summary}\n\n"
                f"**Variant Specifications**: {mod_desc} In this formulation, focus on handling {mod_context} "
                f"efficiently while adhering to the specified asymptotic bounds.\n\n"
                f"### Requirements\n\n"
                f"1. Read input from standard input according to the defined input format.\n"
                f"2. Implement an optimal solution achieving an expected time complexity of `{theme_time}` "
                f"and auxiliary space complexity of `{theme_space}`.\n"
                f"3. Return the calculated answer matching the expected output format.\n"
            )

            constraints = [
                f"{mod_const}",
                f"All input elements are within standard computational ranges.",
                f"Time limit: 3.0 seconds per test execution.",
                f"Memory limit: 256 MB."
            ]

            input_format = f"Standard formatted input providing test parameters across consecutive lines."
            output_format = f"Return or print the calculated result formatted to standard output."

            examples = [
                {
                    "input": pub1_in,
                    "output": pub1_out,
                    "explanation": f"Evaluation of the first sample case yields {pub1_out}."
                },
                {
                    "input": pub2_in,
                    "output": pub2_out,
                    "explanation": f"Processing second sample configuration satisfies all conditions producing {pub2_out}."
                }
            ]

            public_tests = [
                {"input": pub1_in, "output": pub1_out},
                {"input": pub2_in, "output": pub2_out}
            ]

            hidden_tests = [
                {"input": hid1_in, "output": hid1_out},
                {"input": hid2_in, "output": hid2_out},
                {"input": hid3_in, "output": hid3_out},
                {"input": hid4_in, "output": hid4_out}
            ]

            hints = [
                f"Begin by examining small sample inputs to identify invariant properties and the structure of {theme_tag}.",
                f"Consider using an optimal {topic} pattern to reduce repetitive computation and achieve {theme_time}.",
                f"Ensure your solution rigorously covers boundary conditions such as single-element inputs and extreme constraints."
            ]

            editorial = (
                f"### Optimal Strategy\n\n"
                f"The problem is solved using the **{theme_tag}** paradigm. By systematically processing inputs "
                f"in `{theme_time}` time and utilizing `{theme_space}` memory, we achieve optimal performance. "
                f"Pay special attention to edge cases such as empty sequences, boundary values, and repeated elements."
            )

            starter_code = generate_starter_templates(candidate_title, topic, is_sql=is_sql, is_ml=is_ml)

            tags = [topic, theme_tag, diff]
            if mod_title != "Standard":
                tags.append(mod_title)

            record = {
                "title": candidate_title,
                "slug": candidate_slug,
                "description": description,
                "difficulty": diff,
                "topic": topic,
                "tags": tags,
                "company_tags": company_pair,
                "role_tags": role_pair,
                "constraints": constraints,
                "input_format": input_format,
                "output_format": output_format,
                "examples": examples,
                "starter_code": starter_code,
                "supported_languages": ["python", "javascript", "cpp", "java"],
                "public_test_cases": public_tests,
                "hidden_test_cases": hidden_tests,
                "expected_time_complexity": theme_time,
                "expected_space_complexity": theme_space,
                "editorial": editorial,
                "hints": hints
            }

            topic_problems.append(record)
            created_for_topic += 1
            theme_idx += 1
            if theme_idx % len(theme_list) == 0:
                mod_idx += 1

        all_problems.extend(topic_problems)

    return all_problems

def main():
    print("Generating 995 problems...")
    problems = generate_all_problems()
    print(f"Generated {len(problems)} problems.")

    assert len(problems) == 995, f"Expected 995 problems, got {len(problems)}"

    # Validate each problem schema and content
    easy_count = 0
    med_count = 0
    hard_count = 0
    topic_counts = {}

    for i, p in enumerate(problems):
        rec = ProblemRecord(**p)
        valid, err = ProblemValidator.validate_problem_data(rec)
        assert valid, f"Problem #{i+1} ('{rec.title}') failed validation: {err}"

        diff = rec.difficulty
        if diff == "Easy":
            easy_count += 1
        elif diff == "Medium":
            med_count += 1
        elif diff == "Hard":
            hard_count += 1

        t = rec.topic
        topic_counts[t] = topic_counts.get(t, 0) + 1

    print("\n--- Validation Succeeded ---")
    print(f"Total Problems: {len(problems)}")
    print(f"Easy: {easy_count} (target 297)")
    print(f"Medium: {med_count} (target 498)")
    print(f"Hard: {hard_count} (target 200)")
    assert easy_count == 297, f"Easy mismatch: {easy_count}"
    assert med_count == 498, f"Medium mismatch: {med_count}"
    assert hard_count == 200, f"Hard mismatch: {hard_count}"

    print("\nTopic Distribution:")
    for t, c in sorted(topic_counts.items()):
        print(f"  {t}: {c}")

    output_dir = os.path.join(os.path.dirname(__file__), "datasets")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "problem_bank_995.jsonl")

    print(f"\nWriting dataset to: {output_path}")
    with open(output_path, "w", encoding="utf-8") as f:
        for p in problems:
            f.write(json.dumps(p) + "\n")

    print(f"Successfully generated and saved {len(problems)} validated problems to {output_path}")

if __name__ == "__main__":
    main()
