from sqlglot import exp
from .utils import run_oracle, split_stmts, unsplit_stmts, parse_sql


def _apply_order(tree, order_idx, new_terms):
    tree_copy = tree.copy()
    orders = list(tree_copy.find_all(exp.Order))
    target = orders[order_idx]
    if not new_terms:
        target.pop()
    else:
        target.set('expressions', [t.copy() for t in new_terms])
    return tree_copy.sql(dialect='sqlite')


def order_by_reduce(sql: str, oracle_script: str) -> str:
    stmts = split_stmts(sql)

    for i in range(len(stmts)):
        prev = None
        while prev != stmts[i]:
            prev = stmts[i]
            parsed = parse_sql(stmts[i])
            if not parsed:
                break
            tree = parsed[0]

            orders = list(tree.find_all(exp.Order))
            made_progress = False

            for order_idx, order_node in enumerate(orders):
                terms = list(order_node.expressions)

                for j in range(len(terms)):
                    candidate_terms = terms[:j] + terms[j + 1:]
                    candidate_stmt = _apply_order(tree, order_idx, candidate_terms)
                    candidate_parts = stmts[:i] + [candidate_stmt] + stmts[i + 1:]
                    if run_oracle(unsplit_stmts(candidate_parts), oracle_script):
                        stmts[i] = candidate_stmt
                        made_progress = True
                        break

                if made_progress:
                    break

                for j, term in enumerate(terms):
                    if not isinstance(term.this, exp.Collate):
                        continue
                    new_term = term.copy()
                    new_term.set('this', term.this.this.copy())
                    candidate_terms = terms[:j] + [new_term] + terms[j + 1:]
                    candidate_stmt = _apply_order(tree, order_idx, candidate_terms)
                    candidate_parts = stmts[:i] + [candidate_stmt] + stmts[i + 1:]
                    if run_oracle(unsplit_stmts(candidate_parts), oracle_script):
                        stmts[i] = candidate_stmt
                        made_progress = True
                        break

                if made_progress:
                    break

                for j, term in enumerate(terms):
                    if not term.args.get('desc'):
                        continue
                    new_term = term.copy()
                    new_term.set('desc', False)
                    candidate_terms = terms[:j] + [new_term] + terms[j + 1:]
                    candidate_stmt = _apply_order(tree, order_idx, candidate_terms)
                    candidate_parts = stmts[:i] + [candidate_stmt] + stmts[i + 1:]
                    if run_oracle(unsplit_stmts(candidate_parts), oracle_script):
                        stmts[i] = candidate_stmt
                        made_progress = True
                        break

                if made_progress:
                    break

    return unsplit_stmts(stmts)
