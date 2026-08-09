#!/usr/bin/env python3
# degrees.py 
# Python 3.12
# Find shortest "degrees of separation" between two actors using BFS.
# Usage: python degrees.py [data_directory]

import csv
import sys
from collections import deque
from typing import Dict, Set, Optional, List, Tuple

# --- Global data structures populated from CSV files ---
# names: maps lowercase actor name -> set of person_ids (strings)
names: Dict[str, Set[str]] = {}

# people: maps person_id -> {"name": name, "birth": year, "movies": set(movie_ids)}
people: Dict[str, Dict] = {}

# movies: maps movie_id -> {"title": title, "year": year, "stars": set(person_ids)}
movies: Dict[str, Dict] = {}

# --- Node class for search tree ---
class Node:
    """
    Search node.
    - state: person_id (string)
    - parent: Node that led to this node (None for root)
    - action: movie_id (string) used to reach this state from parent
    """
    def __init__(self, state: str, parent: Optional["Node"], action: Optional[str]):
        self.state = state
        self.parent = parent
        self.action = action

# --- FIFO frontier for BFS ---
class QueueFrontier:
    """
    Simple FIFO frontier for BFS using a deque.
    """
    def __init__(self):
        self.frontier = deque()

    def add(self, node: Node) -> None:
        self.frontier.append(node)

    def remove(self) -> Node:
        if not self.frontier:
            raise Exception("Frontier is empty")
        return self.frontier.popleft()

    def contains_state(self, state: str) -> bool:
        return any(node.state == state for node in self.frontier)

    def empty(self) -> bool:
        return len(self.frontier) == 0

# --- Data loading ---
def load_data(directory: str) -> None:
    """
    Load data from CSV files into the global names, people, and movies structures.
    Expects CSVs: people.csv, movies.csv, stars.csv in the given directory.
    """
    # Load people
    with open(f"{directory}/people.csv", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid = row["id"]
            name = row["name"]
            birth = row.get("birth", "")
            people[pid] = {"name": name, "birth": birth, "movies": set()}
            name_l = name.lower()
            names.setdefault(name_l, set()).add(pid)

    # Load movies
    with open(f"{directory}/movies.csv", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            mid = row["id"]
            title = row["title"]
            year = row.get("year", "")
            movies[mid] = {"title": title, "year": year, "stars": set()}

    # Load stars (movie-person relationships)
    with open(f"{directory}/stars.csv", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if "person_id" in row and "movie_id" in row:
                pid = row["person_id"]
                mid = row["movie_id"]
            else:
                keys = list(row.keys())
                pid = row[keys[0]]
                mid = row[keys[1]]
            if pid in people and mid in movies:
                people[pid]["movies"].add(mid)
                movies[mid]["stars"].add(pid)

# --- Helper functions used by shortest_path and UI ---
def person_id_for_name(name: str) -> Optional[str]:
    """
    Resolve a name to a person_id. If multiple people have that name,
    prompt the user to choose one. Returns None if name not found.
    """
    name_l = name.strip().lower()
    if name_l not in names:
        return None
    ids = list(names[name_l])
    if len(ids) == 1:
        return ids[0]
    # Multiple people with same name — ask user to disambiguate
    print(f"Which '{name}'?")
    for pid in ids:
        person = people[pid]
        print(f"  ID: {pid}, Name: {person['name']}, Birth: {person.get('birth','unknown')}")
    try:
        chosen = input("Enter the ID of the intended person: ").strip()
    except EOFError:
        return None
    return chosen if chosen in ids else None


def neighbors_for_person(person_id: str) -> Set[Tuple[str, str]]:
    """
    For a given person_id, return a set of (movie_id, person_id) pairs
    for all people who shared a movie with the person.
    """
    neighbors = set()
    for mid in people[person_id]["movies"]:
        for pid in movies[mid]["stars"]:
            if pid != person_id:
                neighbors.add((mid, pid))
    return neighbors

# --- BFS shortest path implementation ---
def shortest_path(source: str, target: str) -> Optional[List[Tuple[str, str]]]:
    """
    Return the shortest list of (movie_id, person_id) pairs that connect the source to the target.
    If source == target, return an empty list ([]).
    If no connection exists, return None.
    """
    if source == target:
        return []

    start = Node(state=source, parent=None, action=None)
    frontier = QueueFrontier()
    frontier.add(start)

    explored: Set[str] = set()

    while not frontier.empty():
        node = frontier.remove()
        explored.add(node.state)

        for movie_id, person_id in neighbors_for_person(node.state):
            if person_id in explored or frontier.contains_state(person_id):
                continue
            child = Node(state=person_id, parent=node, action=movie_id)
            if person_id == target:
                return _reconstruct_path(child)
            frontier.add(child)

    return None


def _reconstruct_path(goal_node: Node) -> List[Tuple[str, str]]:
    """
    Follow parent pointers from goal back to start and build list of
    (movie_id, person_id) pairs in source->...->target order.
    """
    path: List[Tuple[str, str]] = []
    node = goal_node
    while node.parent is not None:
        path.append((node.action, node.state))
        node = node.parent
    path.reverse()
    return path

# --- Main interactive CLI ---
def main() -> None:
    if len(sys.argv) > 2:
        sys.exit("Usage: python degrees.py [data_directory]")
    directory = sys.argv[1] if len(sys.argv) == 2 else "large"

    print("Loading data...")
    load_data(directory)
    print("Data loaded.")

    try:
        name1 = input("Name: ").strip()
    except EOFError:
        return
    source = person_id_for_name(name1)
    if source is None:
        print(f"Person '{name1}' not found.")
        return

    try:
        name2 = input("Name: ").strip()
    except EOFError:
        return
    target = person_id_for_name(name2)
    if target is None:
        print(f"Person '{name2}' not found.")
        return

    path = shortest_path(source, target)

    if path is None:
        print("Not connected.")
        return

    if path == []:
        print("0 degrees of separation.")
        print(f"{people[source]['name']} is the same person as {people[target]['name']}.")
        return

    degrees = len(path)
    print(f"{degrees} degrees of separation.")
    current = source
    for i, (movie_id, person_id) in enumerate(path, start=1):
        movie_title = movies[movie_id]["title"]
        print(f"{i}: {people[current]['name']} and {people[person_id]['name']} starred in {movie_title}")
        current = person_id

if __name__ == "__main__":
    main()
