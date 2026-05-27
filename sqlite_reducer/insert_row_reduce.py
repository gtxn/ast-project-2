from sqlglot import exp
from .utils import run_oracle, split_stmts, unsplit_stmts, parse_sql

def _remove_insert_row(tree, insert_pos, row_idx):
    count = [-1]
    def fn(node):
        count[0] += 1
        if count[0] == insert_pos:
            node = node.copy()
            values = node.args.get('expression')
            rows = list(values.expressions)
            values.set('expressions', rows[:row_idx] + rows[row_idx + 1:])
        return node
    return tree.copy().transform(fn, copy=False).sql(dialect='sqlite')

def insert_row_reduce(sql: str, oracle_script: str) -> str:
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
                if (
                    isinstance(node, exp.Insert)
                    and isinstance(node.args.get('expression'), exp.Values)
                    and len(node.args['expression'].expressions) > 1
                )
            ]

            for insert_pos, insert_node in candidates:
                rows = list(insert_node.args['expression'].expressions)
                for j in range(len(rows)):
                    candidate_stmt = _remove_insert_row(tree, insert_pos, j)
                    candidate_parts = stmts[:i] + [candidate_stmt] + stmts[i + 1:]
                    if run_oracle(unsplit_stmts(candidate_parts), oracle_script):
                        stmts[i] = candidate_stmt
                        break
                if stmts[i] != prev:
                    break

    return unsplit_stmts(stmts)
