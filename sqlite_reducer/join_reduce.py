from sqlglot import exp
from .utils import run_oracle, split_stmts, unsplit_stmts, parse_sql


def _remove_join(tree, select_pos, join_idx):
    count = [-1]
    def fn(node):
        count[0] += 1
        if count[0] == select_pos:
            joins = list(node.args.get('joins') or [])
            node = node.copy()
            node.set('joins', joins[:join_idx] + joins[join_idx + 1:])
        return node
    return tree.copy().transform(fn, copy=False).sql(dialect='sqlite')


def join_reduce(sql: str, oracle_script: str) -> str:
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
                if isinstance(node, exp.Select) and node.args.get('joins')
            ]

            for select_pos, select_node in candidates:
                joins = list(select_node.args.get('joins'))
                for j in range(len(joins)):
                    candidate_stmt = _remove_join(tree, select_pos, j)
                    candidate_parts = stmts[:i] + [candidate_stmt] + stmts[i + 1:]
                    if run_oracle(unsplit_stmts(candidate_parts), oracle_script):
                        stmts[i] = candidate_stmt
                        break
                if stmts[i] != prev:
                    break

    return unsplit_stmts(stmts)
