from sqlglot import exp
from .utils import run_oracle, split_stmts, unsplit_stmts, parse_sql

def _remove_when(tree, case_pos, when_idx):
    count = [-1]
    def fn(node):
        count[0] += 1
        if count[0] == case_pos:
            ifs = list(node.args.get('ifs') or [])
            node = node.copy()
            node.set('ifs', ifs[:when_idx] + ifs[when_idx + 1:])
        return node
    return tree.copy().transform(fn, copy=False).sql(dialect='sqlite')

# Simply removes one of the cases
def _replace_case(tree, case_pos, replacement):
    count = [-1]
    def fn(node):
        count[0] += 1
        if count[0] == case_pos:
            return replacement.copy()
        return node
    return tree.copy().transform(fn, copy=False).sql(dialect='sqlite')

# Replaces whole case with he possible vaules directly
def _whole_case_replacements(case_node):
    replacements = []

    default = case_node.args.get('default')
    if default is not None:
        replacements.append(default)

    for if_expr in case_node.args.get('ifs') or []:
        true_expr = if_expr.args.get('true') or if_expr.args.get('expression')
        if true_expr is not None:
            replacements.append(true_expr)

    replacements.append(exp.Null())

    unique = []
    seen = set()
    for replacement in replacements:
        key = replacement.sql(dialect='sqlite')
        if key not in seen:
            seen.add(key)
            unique.append(replacement)

    return unique


def case_reduce(sql: str, oracle_script: str) -> str:
    stmts = split_stmts(sql)

    for i in range(len(stmts)):
        prev = None
        while prev != stmts[i]:
            prev = stmts[i]
            parsed = parse_sql(stmts[i])
            if not parsed:
                break
            tree = parsed[0]

            candidates = [
                (pos, node)
                for pos, node in enumerate(tree.walk(bfs=False))
                if isinstance(node, exp.Case) and node.args.get('ifs')
            ]

            for case_pos, case_node in candidates:
                for replacement in _whole_case_replacements(case_node):
                    candidate_stmt = _replace_case(tree, case_pos, replacement)
                    candidate_parts = stmts[:i] + [candidate_stmt] + stmts[i + 1:]
                    if run_oracle(unsplit_stmts(candidate_parts), oracle_script):
                        stmts[i] = candidate_stmt
                        break
                if stmts[i] != prev:
                    break

                ifs = list(case_node.args.get('ifs'))
                for j in range(len(ifs)):
                    candidate_stmt = _remove_when(tree, case_pos, j)
                    candidate_parts = stmts[:i] + [candidate_stmt] + stmts[i + 1:]
                    if run_oracle(unsplit_stmts(candidate_parts), oracle_script):
                        stmts[i] = candidate_stmt
                        break
                if stmts[i] != prev:
                    break

    return unsplit_stmts(stmts)
