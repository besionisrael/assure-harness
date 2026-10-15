"""First-order AST mutation operators (classic set: AOR, ROR, LCR, UOI/UOD,
constant replacement, BCR). Used twice:
  * on the canonical solution, to measure oracle strength (mutation score);
  * on the builder's program in Phase B, to guide the verifier toward
    surviving mutants.
"""
import ast
import copy
import difflib
import random

BINOP_SWAP = {
    ast.Add: [ast.Sub], ast.Sub: [ast.Add], ast.Mult: [ast.FloorDiv, ast.Add],
    ast.Div: [ast.Mult], ast.FloorDiv: [ast.Div, ast.Mult], ast.Mod: [ast.FloorDiv],
    ast.Pow: [ast.Mult], ast.BitAnd: [ast.BitOr], ast.BitOr: [ast.BitAnd],
    ast.LShift: [ast.RShift], ast.RShift: [ast.LShift],
}
CMP_SWAP = {
    ast.Lt: [ast.LtE, ast.Gt], ast.LtE: [ast.Lt, ast.GtE], ast.Gt: [ast.GtE, ast.Lt],
    ast.GtE: [ast.Gt, ast.LtE], ast.Eq: [ast.NotEq], ast.NotEq: [ast.Eq],
    ast.In: [ast.NotIn], ast.NotIn: [ast.In], ast.Is: [ast.IsNot], ast.IsNot: [ast.Is],
}


def _docstring_nodes(tree):
    ids = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                ids.add(id(body[0].value))
    return ids


def _sites(tree):
    """Enumerate (node_index, operator_label, replacement_factory)."""
    skip = _docstring_nodes(tree)
    nodes = list(ast.walk(tree))
    sites = []
    for i, node in enumerate(nodes):
        if isinstance(node, (ast.BinOp, ast.AugAssign)):
            for new in BINOP_SWAP.get(type(node.op), []):
                sites.append((i, "AOR", ("op", new)))
        elif isinstance(node, ast.Compare):
            for j, op in enumerate(node.ops):
                for new in CMP_SWAP.get(type(op), []):
                    sites.append((i, "ROR", ("cmp", j, new)))
        elif isinstance(node, ast.BoolOp):
            sites.append((i, "LCR", ("boolop", ast.Or if isinstance(node.op, ast.And) else ast.And)))
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.Not, ast.USub)):
            sites.append((i, "UOD", ("unwrap",)))
        elif isinstance(node, ast.If):
            sites.append((i, "UOI", ("negate_test",)))
        elif isinstance(node, ast.Constant) and id(node) not in skip:
            v = node.value
            if isinstance(v, bool):
                sites.append((i, "CRP", ("const", not v)))
            elif isinstance(v, int):
                sites.append((i, "CRP", ("const", v + 1)))
                sites.append((i, "CRP", ("const", v - 1 if v != 0 else 1)))
            elif isinstance(v, float):
                sites.append((i, "CRP", ("const", v + 1.0)))
            elif isinstance(v, str) and v:
                sites.append((i, "CRP", ("const", "")))
        elif isinstance(node, ast.Break):
            sites.append((i, "BCR", ("stmt", ast.Continue)))
        elif isinstance(node, ast.Continue):
            sites.append((i, "BCR", ("stmt", ast.Break)))
    return sites


class _Apply(ast.NodeTransformer):
    def __init__(self, target, action):
        self.target, self.action, self.count = target, action, -1

    def generic_visit(self, node):
        return super().generic_visit(node)

    def visit(self, node):
        self.count += 1
        if self.count == self.target:
            return self._mutate(node)
        return self.generic_visit(node)

    def _mutate(self, node):
        kind = self.action[0]
        if kind == "op":
            node.op = self.action[1]()
        elif kind == "cmp":
            node.ops[self.action[1]] = self.action[2]()
        elif kind == "boolop":
            node.op = self.action[1]()
        elif kind == "unwrap":
            return node.operand
        elif kind == "negate_test":
            node.test = ast.UnaryOp(op=ast.Not(), operand=node.test)
        elif kind == "const":
            node.value = self.action[1]
        elif kind == "stmt":
            return self.action[1]()
        return node


def _walk_order_index(tree, flat_index):
    """ast.walk is breadth-first; NodeTransformer.visit is depth-first. Map the
    breadth-first index to the depth-first visiting index."""
    target = list(ast.walk(tree))[flat_index]
    counter = [-1]
    found = [None]

    def dfs(node):
        counter[0] += 1
        if node is target:
            found[0] = counter[0]
            return True
        for child in ast.iter_child_nodes(node):
            if dfs(child):
                return True
        return False

    dfs(tree)
    return found[0]


def generate(code, max_mutants=40, seed=0):
    """Return a list of dicts {id, operator, code, diff}; deduplicated and
    syntactically valid. Sampled to at most max_mutants with a fixed seed."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    original = ast.unparse(tree)
    seen, mutants = {original}, []
    for flat, label, action in _sites(tree):
        t = copy.deepcopy(tree)
        dfs_index = _walk_order_index(t, flat)
        mutated = _Apply(dfs_index, action).visit(t)
        ast.fix_missing_locations(mutated)
        try:
            src = ast.unparse(mutated)
            compile(src, "<mutant>", "exec")
        except Exception:  # noqa: BLE001
            continue
        if src in seen:
            continue
        seen.add(src)
        diff = "\n".join(l for l in difflib.unified_diff(
            original.splitlines(), src.splitlines(), lineterm="", n=1)
            if not l.startswith(("---", "+++")))
        mutants.append({"operator": label, "code": src, "diff": diff})
    rng = random.Random(seed)
    if len(mutants) > max_mutants:
        mutants = rng.sample(mutants, max_mutants)
    for i, m in enumerate(mutants):
        m["id"] = f"M{i:03d}"
    return mutants
