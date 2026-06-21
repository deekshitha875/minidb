"""
btree.py — Core B-tree implementation for MiniDB

A B-tree is a self-balancing search tree where each node can hold
multiple keys. This keeps the tree short (few disk reads) and fast.

Order (t): minimum degree of the tree.
  - Each node holds at most 2t-1 keys
  - Each non-leaf node has at most 2t children
  - Each non-root node has at least t-1 keys
"""


class BTreeNode:
    def __init__(self, leaf=True):
        self.keys = []       # list of (key, value) pairs, sorted by key
        self.children = []   # list of child BTreeNode objects
        self.leaf = leaf     # True if this node has no children


class BTree:
    def __init__(self, t=2):
        """
        t = minimum degree. t=2 is the simplest B-tree (also called 2-3-4 tree).
        A real database uses t=100+ so each node maps to one disk page.
        """
        self.t = t
        self.root = BTreeNode(leaf=True)

    # ------------------------------------------------------------------
    # GET — find value by key
    # ------------------------------------------------------------------
    def get(self, key):
        result = self._search(self.root, key)
        return result  # returns value or None

    def _search(self, node, key):
        # Find the first index where key could be
        i = 0
        while i < len(node.keys) and key > node.keys[i][0]:
            i += 1

        # Exact match found
        if i < len(node.keys) and key == node.keys[i][0]:
            return node.keys[i][1]

        # Key not here and this is a leaf — key doesn't exist
        if node.leaf:
            return None

        # Go into the correct child
        return self._search(node.children[i], key)

    # ------------------------------------------------------------------
    # SET — insert or update a key-value pair
    # ------------------------------------------------------------------
    def set(self, key, value):
        # First check if key already exists — if so, update it
        if self._update(self.root, key, value):
            return

        # Key doesn't exist — insert it
        root = self.root

        # If root is full, split it first
        if len(root.keys) == 2 * self.t - 1:
            new_root = BTreeNode(leaf=False)
            new_root.children.append(self.root)
            self._split_child(new_root, 0)
            self.root = new_root

        self._insert_non_full(self.root, key, value)

    def _update(self, node, key, value):
        """Walk the tree; if key found, update value and return True."""
        i = 0
        while i < len(node.keys) and key > node.keys[i][0]:
            i += 1

        if i < len(node.keys) and key == node.keys[i][0]:
            node.keys[i] = (key, value)  # update in place
            return True

        if node.leaf:
            return False

        return self._update(node.children[i], key, value)

    def _insert_non_full(self, node, key, value):
        """Insert into a node that is guaranteed to not be full."""
        i = len(node.keys) - 1

        if node.leaf:
            # Insert key in sorted position
            node.keys.append(None)  # make space
            while i >= 0 and key < node.keys[i][0]:
                node.keys[i + 1] = node.keys[i]
                i -= 1
            node.keys[i + 1] = (key, value)
        else:
            # Find the correct child to descend into
            while i >= 0 and key < node.keys[i][0]:
                i -= 1
            i += 1

            # If that child is full, split it first
            if len(node.children[i].keys) == 2 * self.t - 1:
                self._split_child(node, i)
                if key > node.keys[i][0]:
                    i += 1

            self._insert_non_full(node.children[i], key, value)

    def _split_child(self, parent, i):
        """Split the i-th child of parent (it must be full)."""
        t = self.t
        full_child = parent.children[i]
        new_child = BTreeNode(leaf=full_child.leaf)

        # The middle key moves up to the parent
        mid = t - 1
        mid_key = full_child.keys[mid]

        # Right half goes to new_child
        new_child.keys = full_child.keys[mid + 1:]
        full_child.keys = full_child.keys[:mid]

        # If not a leaf, split children too
        if not full_child.leaf:
            new_child.children = full_child.children[t:]
            full_child.children = full_child.children[:t]

        # Insert mid_key into parent and new_child into parent's children
        parent.keys.insert(i, mid_key)
        parent.children.insert(i + 1, new_child)

    # ------------------------------------------------------------------
    # DELETE — remove a key
    # ------------------------------------------------------------------
    def delete(self, key):
        self._delete(self.root, key)

        # If root is now empty but has a child, shrink the tree
        if len(self.root.keys) == 0 and not self.root.leaf:
            self.root = self.root.children[0]

    def _delete(self, node, key):
        t = self.t
        i = 0
        while i < len(node.keys) and key > node.keys[i][0]:
            i += 1

        if i < len(node.keys) and key == node.keys[i][0]:
            # Key is in this node
            if node.leaf:
                # Simple case: just remove it
                node.keys.pop(i)
            else:
                # Replace with in-order predecessor, then delete predecessor
                pred = self._get_predecessor(node, i)
                node.keys[i] = pred
                self._delete(node.children[i], pred[0])
        else:
            # Key is not in this node
            if node.leaf:
                return  # Key doesn't exist, nothing to do

            # Make sure child has enough keys before descending
            if len(node.children[i].keys) < t:
                self._fill(node, i)
                # After fill, re-search since tree may have changed
                self._delete(self.root if node == self.root else node, key)
                return

            self._delete(node.children[i], key)

    def _get_predecessor(self, node, i):
        """Get the largest key in the left subtree of node.keys[i]."""
        current = node.children[i]
        while not current.leaf:
            current = current.children[-1]
        return current.keys[-1]

    def _fill(self, parent, i):
        """Ensure parent.children[i] has at least t keys."""
        t = self.t

        if i > 0 and len(parent.children[i - 1].keys) >= t:
            self._borrow_from_prev(parent, i)
        elif i < len(parent.children) - 1 and len(parent.children[i + 1].keys) >= t:
            self._borrow_from_next(parent, i)
        else:
            if i < len(parent.children) - 1:
                self._merge(parent, i)
            else:
                self._merge(parent, i - 1)

    def _borrow_from_prev(self, parent, i):
        child = parent.children[i]
        sibling = parent.children[i - 1]
        child.keys.insert(0, parent.keys[i - 1])
        parent.keys[i - 1] = sibling.keys.pop()
        if not sibling.leaf:
            child.children.insert(0, sibling.children.pop())

    def _borrow_from_next(self, parent, i):
        child = parent.children[i]
        sibling = parent.children[i + 1]
        child.keys.append(parent.keys[i])
        parent.keys[i] = sibling.keys.pop(0)
        if not sibling.leaf:
            child.children.append(sibling.children.pop(0))

    def _merge(self, parent, i):
        child = parent.children[i]
        sibling = parent.children[i + 1]
        child.keys.append(parent.keys.pop(i))
        child.keys.extend(sibling.keys)
        if not child.leaf:
            child.children.extend(sibling.children)
        parent.children.pop(i + 1)

    # ------------------------------------------------------------------
    # Utility — print the tree (for debugging)
    # ------------------------------------------------------------------
    def display(self):
        self._display(self.root, 0)

    def _display(self, node, level):
        indent = "  " * level
        keys_only = [k for k, v in node.keys]
        print(f"{indent}[{', '.join(map(str, keys_only))}]")
        for child in node.children:
            self._display(child, level + 1)
