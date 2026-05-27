from sqlglot import exp
from .utils import run_oracle, split_stmts, unsplit_stmts, parse_sql

def _table_name(node):
    if isinstance(node, exp.Schema):
        return _table_name(node.this)
    if isinstance(node, exp.Table):
        return node.name
    return None

def _remove_create_column(stmt, col_idx):
    stmt = stmt.copy()
    schema = stmt.this
    columns = list(schema.expressions)
    schema.set('expressions', columns[:col_idx] + columns[col_idx + 1:])
    return stmt

def _remove_insert_column(stmt, table_name, column_name, fallback_idx):
    if not isinstance(stmt, exp.Insert):
        return stmt

    target = stmt.this
    if _table_name(target) != table_name:
        return stmt

    values = stmt.args.get('expression')
    if not isinstance(values, exp.Values):
        return stmt

    stmt = stmt.copy()
    target = stmt.this
    values = stmt.args.get('expression')

    col_idx = fallback_idx
    if isinstance(target, exp.Schema) and target.expressions:
        insert_columns = list(target.expressions)
        matching = [
            idx
            for idx, column in enumerate(insert_columns)
            if getattr(column, 'name', None) == column_name
        ]
        if not matching:
            return stmt
        col_idx = matching[0]
        target.set('expressions', insert_columns[:col_idx] + insert_columns[col_idx + 1:])

    rows = []
    for row in values.expressions:
        expressions = list(row.expressions)
        if col_idx >= len(expressions):
            return stmt
        row = row.copy()
        row.set('expressions', expressions[:col_idx] + expressions[col_idx + 1:])
        rows.append(row)

    values.set('expressions', rows)
    return stmt

def _remove_table_column(parsed, create_idx, col_idx):
    create_stmt = parsed[create_idx]
    schema = create_stmt.this
    table_name = _table_name(schema)
    column_name = schema.expressions[col_idx].name

    result = []
    for i, stmt in enumerate(parsed):
        if i == create_idx:
            result.append(_remove_create_column(stmt, col_idx))
        else:
            result.append(_remove_insert_column(stmt, table_name, column_name, col_idx))

    return result

def table_column_reduce(sql: str, oracle_script: str) -> str:
    stmts = split_stmts(sql)

    prev = None
    while prev != unsplit_stmts(stmts):
        prev = unsplit_stmts(stmts)
        parsed = parse_sql(unsplit_stmts(stmts))
        if not parsed:
            break

        made_progress = False
        for create_idx, stmt in enumerate(parsed):
            if not (
                isinstance(stmt, exp.Create)
                and stmt.args.get('kind') == 'TABLE'
                and isinstance(stmt.this, exp.Schema)
                and len(stmt.this.expressions) > 1
            ):
                continue

            columns = list(stmt.this.expressions)
            for col_idx in range(len(columns)):
                candidate_parsed = _remove_table_column(parsed, create_idx, col_idx)
                candidate_stmts = [stmt.sql(dialect='sqlite') for stmt in candidate_parsed]
                candidate_sql = unsplit_stmts(candidate_stmts)
                if run_oracle(candidate_sql, oracle_script):
                    stmts = candidate_stmts
                    made_progress = True
                    break

            if made_progress:
                break

        if not made_progress:
            break

    return unsplit_stmts(stmts)
