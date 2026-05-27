from sqlglot import exp
from .utils import run_oracle, split_stmts, unsplit_stmts, parse_sql

_SIMPLER_TYPES = [
    exp.DataType.build('INTEGER'),
    exp.DataType.build('TEXT'),
]


def _apply_col(tree, col_idx, new_kind, new_constraints):
    tree_copy = tree.copy()
    cols = list(tree_copy.find_all(exp.ColumnDef))
    target = cols[col_idx]
    target.set('kind', new_kind.copy() if new_kind is not None else None)
    target.set('constraints', [c.copy() for c in new_constraints])
    return tree_copy.sql(dialect='sqlite')


def column_def_reduce(sql: str, oracle_script: str) -> str:
    stmts = split_stmts(sql)

    for i in range(len(stmts)):
        prev = None
        while prev != stmts[i]:
            prev = stmts[i]
            parsed = parse_sql(stmts[i])
            if not parsed:
                break
            tree = parsed[0]

            cols = list(tree.find_all(exp.ColumnDef))
            made_progress = False

            for col_idx, col in enumerate(cols):
                kind = col.args.get('kind')
                constraints = list(col.args.get('constraints') or [])

                for j in range(len(constraints)):
                    candidate_stmt = _apply_col(tree, col_idx, kind, constraints[:j] + constraints[j + 1:])
                    candidate_parts = stmts[:i] + [candidate_stmt] + stmts[i + 1:]
                    if run_oracle(unsplit_stmts(candidate_parts), oracle_script):
                        stmts[i] = candidate_stmt
                        made_progress = True
                        break

                if made_progress:
                    break

                if kind is not None:
                    candidate_stmt = _apply_col(tree, col_idx, None, constraints)
                    candidate_parts = stmts[:i] + [candidate_stmt] + stmts[i + 1:]
                    if run_oracle(unsplit_stmts(candidate_parts), oracle_script):
                        stmts[i] = candidate_stmt
                        made_progress = True
                        break

                    if not made_progress:
                        current_sql = kind.sql(dialect='sqlite')
                        for simpler in _SIMPLER_TYPES:
                            if simpler.sql(dialect='sqlite') == current_sql:
                                continue
                            candidate_stmt = _apply_col(tree, col_idx, simpler, constraints)
                            candidate_parts = stmts[:i] + [candidate_stmt] + stmts[i + 1:]
                            if run_oracle(unsplit_stmts(candidate_parts), oracle_script):
                                stmts[i] = candidate_stmt
                                made_progress = True
                                break

                if made_progress:
                    break

    return unsplit_stmts(stmts)
