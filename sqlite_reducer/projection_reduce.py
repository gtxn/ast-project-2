from sqlglot import exp
from .utils import run_oracle, split_stmts, unsplit_stmts, parse_sql


def apply_projection(tree, sel_idx: int, candidate_projections: list) -> str:
    tree_copy = tree.copy()
    selects = list(tree_copy.find_all(exp.Select))
    target = selects[sel_idx]
    target.set('expressions', [p.copy() for p in candidate_projections])
    return tree_copy.sql(dialect='sqlite')


def projection_reduce(sql: str, oracle_script: str) -> str:
    stmts = split_stmts(sql)

    for i in range(len(stmts)):
        prev = None
        while prev != stmts[i]:
            prev = stmts[i]
            parsed = parse_sql(stmts[i])
            if not parsed:
                break
            tree = parsed[0]

            selects = list(tree.find_all(exp.Select))
            made_progress = False

            for sel_idx, select_node in enumerate(selects):
                projections = select_node.expressions

                if any(isinstance(p, exp.Star) for p in projections):
                    continue
                if len(projections) <= 1:
                    continue

                for j in range(len(projections)):
                    candidate_projections = projections[:j] + projections[j + 1:]
                    candidate_stmt = apply_projection(tree, sel_idx, candidate_projections)
                    candidate_parts = stmts[:i] + [candidate_stmt] + stmts[i + 1:]
                    if run_oracle(unsplit_stmts(candidate_parts), oracle_script):
                        stmts[i] = candidate_stmt
                        made_progress = True
                        break

                if made_progress:
                    break

    return unsplit_stmts(stmts)
