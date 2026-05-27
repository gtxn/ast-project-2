from sqlglot import exp
from .utils import run_oracle, split_stmts, unsplit_stmts, parse_sql


def get_conjuncts(condition):
    if isinstance(condition, exp.And):
        return get_conjuncts(condition.left) + get_conjuncts(condition.right)
    return [condition]


def get_disjuncts(condition):
    if isinstance(condition, exp.Or):
        return get_disjuncts(condition.left) + get_disjuncts(condition.right)
    return [condition]


def build_and_chain(conjuncts):
    result = conjuncts[0].copy()
    for c in conjuncts[1:]:
        result = exp.And(this=result, expression=c.copy())
    return result


def build_or_chain(disjuncts):
    result = disjuncts[0].copy()
    for d in disjuncts[1:]:
        result = exp.Or(this=result, expression=d.copy())
    return result


def _apply_conjuncts(tree, where_idx, conjuncts):
    tree_copy = tree.copy()
    wheres = list(tree_copy.find_all(exp.Where))
    target = wheres[where_idx]
    if conjuncts:
        target.set('this', build_and_chain(conjuncts))
    else:
        target.pop()
    return tree_copy.sql(dialect='sqlite')


def where_condition_reduce(sql: str, oracle_script: str) -> str:
    stmts = split_stmts(sql)

    for i in range(len(stmts)):
        prev = None
        while prev != stmts[i]:
            prev = stmts[i]
            parsed = parse_sql(stmts[i])
            if not parsed:
                break
            tree = parsed[0]

            wheres = list(tree.find_all(exp.Where))
            made_progress = False

            for where_idx, where in enumerate(wheres):
                conjuncts = get_conjuncts(where.this)

                for j in range(len(conjuncts)):
                    candidate_conjuncts = conjuncts[:j] + conjuncts[j + 1:]
                    candidate_stmt = _apply_conjuncts(tree, where_idx, candidate_conjuncts)
                    candidate_parts = stmts[:i] + [candidate_stmt] + stmts[i + 1:]
                    if run_oracle(unsplit_stmts(candidate_parts), oracle_script):
                        stmts[i] = candidate_stmt
                        made_progress = True
                        break

                if made_progress:
                    break

                for j, conjunct in enumerate(conjuncts):
                    disjuncts = get_disjuncts(conjunct)
                    if len(disjuncts) <= 1:
                        continue
                    for k in range(len(disjuncts)):
                        candidate_disjuncts = disjuncts[:k] + disjuncts[k + 1:]
                        new_conjunct = build_or_chain(candidate_disjuncts)
                        candidate_stmt = _apply_conjuncts(
                            tree, where_idx, conjuncts[:j] + [new_conjunct] + conjuncts[j + 1:]
                        )
                        candidate_parts = stmts[:i] + [candidate_stmt] + stmts[i + 1:]
                        if run_oracle(unsplit_stmts(candidate_parts), oracle_script):
                            stmts[i] = candidate_stmt
                            made_progress = True
                            break
                    if made_progress:
                        break

                if made_progress:
                    break

    return unsplit_stmts(stmts)
