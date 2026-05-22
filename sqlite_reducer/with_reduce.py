from sqlglot import exp
from .utils import run_oracle, split_stmts, unsplit_stmts, parse_sql


def apply_ctes(tree, ctes):
    tree_copy = tree.copy()
    with_clause = tree_copy.find(exp.With)
    if ctes:
        with_clause.set('expressions', [c.copy() for c in ctes])
    else:
        with_clause.pop()
    return tree_copy.sql(dialect='sqlite')


def with_reduce(sql: str, oracle_script: str) -> str:
    stmts = split_stmts(sql)

    for i in range(len(stmts)):
        prev = None
        while prev != stmts[i]:
            prev = stmts[i]
            parsed = parse_sql(stmts[i])
            if not parsed:
                break
            tree = parsed[0]
            with_clause = tree.find(exp.With)
            if with_clause is None:
                break

            ctes = list(with_clause.expressions)

            for j in range(len(ctes)):
                candidate_ctes = ctes[:j] + ctes[j + 1:]
                candidate_stmt = apply_ctes(tree, candidate_ctes)
                candidate_parts = stmts[:i] + [candidate_stmt] + stmts[i + 1:]
                if run_oracle(unsplit_stmts(candidate_parts), oracle_script):
                    stmts[i] = candidate_stmt
                    break

    return unsplit_stmts(stmts)
