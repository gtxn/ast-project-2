from sqlglot import exp
from .utils import *

UNKNOWN = object()

# Evaluation of expressions
def eval_constant(node):
  if isinstance(node, exp.Literal):
    if node.is_string:
      return node.this

    if node.is_number:
      if "." in node.this:
        return float(node.this)
      return int(node.this)

    return UNKNOWN

  if isinstance(node, exp.Null):
    return None

  if isinstance(node, exp.Boolean):
    return bool(node.this)

  if isinstance(node, exp.Neg):
    value = eval_constant(node.this)
    if value is UNKNOWN:
      return UNKNOWN
    return -value
  
  if isinstance(node, exp.Not):
    value = eval_constant(node.this)
    if value is UNKNOWN:
      return UNKNOWN
    if value is None:
      return None
    return not value
  
  if isinstance(node, exp.Paren):
    value = eval_constant(node.this)
    if value is UNKNOWN:
      return UNKNOWN
    return (value)
  
  if isinstance(node, exp.Tuple):
    values = []
    for n in node.expressions:
      vi = eval_constant(n)
      if vi is UNKNOWN:
        return UNKNOWN
      
      values.append(vi)
    
    return values

  if isinstance(node, exp.EQ):
    left = eval_constant(node.this)
    right = eval_constant(node.expression)
    if UNKNOWN in (left, right):
      return UNKNOWN
    return left == right

  if isinstance(node, exp.NEQ):
    left = eval_constant(node.this)
    right = eval_constant(node.expression)
    if UNKNOWN in (left, right):
      return UNKNOWN
    return left != right

  if isinstance(node, exp.Add):
    left = eval_constant(node.this)
    right = eval_constant(node.expression)
    if UNKNOWN in (left, right):
      return UNKNOWN
    return left + right

  if isinstance(node, exp.Sub):
    left = eval_constant(node.this)
    right = eval_constant(node.expression)
    if UNKNOWN in (left, right):
      return UNKNOWN
    return left - right

  if isinstance(node, exp.Mul):
    left = eval_constant(node.this)
    right = eval_constant(node.expression)
    if UNKNOWN in (left, right):
      return UNKNOWN
    return left * right
  
  if isinstance(node, exp.Div):
    left = eval_constant(node.this)
    right = eval_constant(node.expression)
    if UNKNOWN in (left, right):
      return UNKNOWN
    return left / right

  return UNKNOWN

# Converts calculated value to an sql expression
def value_to_sql_expr(value):
  if value is UNKNOWN:
    return None

  if value is None:
    return exp.Null()

  if isinstance(value, bool):
    return exp.Boolean(this=value)

  if isinstance(value, (int, float)):
    return exp.Literal.number(value)

  if isinstance(value, str):
    return exp.Literal.string(value)
  
  if isinstance(value, tuple):
    return exp.Tuple(expressions=[value_to_sql_expr(x) for x in value])

  return None

# Transforms node to its evaluated value
def transformer(node):
  value = eval_constant(node)
  replacement = value_to_sql_expr(value)

  if replacement is not None:
    return replacement

  return node

# Replace a single node in an expression
def replace_node(stmt, target_index: int, replacement):
  curr_index = -1

  def replace(node):
    nonlocal curr_index
    curr_index += 1

    if curr_index == target_index:
      return replacement.copy()

    return node

  return stmt.copy().transform(replace, copy=False)

# Returns the unique substring
def unique_substring_span(big_str: str, substr: str):
  substr = substr.strip()

  if not substr:
    return None

  big_str = big_str.lower()
  substr = substr.lower()
  start = big_str.find(substr)

  if start == -1:
    return None

  if big_str.find(substr, start + 1) != -1:
    return None

  return start, start + len(substr)

# Replace node in stmt_sql with the replacement 
def splice_replacement(stmt_sql: str, node, replacement):
  span = unique_substring_span(stmt_sql, node.sql(dialect="sqlite"))

  if span is None:
    return None

  start, end = span
  replacement_sql = replacement.sql(dialect="sqlite")
  return stmt_sql[:start] + replacement_sql + stmt_sql[end:]

def expression_reduce(sql: str, oracle_script: str) -> str:
  parsed = parse_sql(sql)
  stmts = split_stmts(sql)
  serialized_stmts = [p.sql(dialect='sqlite') for p in parsed]
  can_serialize = run_oracle(unsplit_stmts(serialized_stmts), oracle_script)
  
  for i, p_stmt in enumerate(parsed):
    changed = True
    
    while changed:
      changed = False
      nodes = list(enumerate(p_stmt.walk(bfs=False)))

      for target_index, node in reversed(nodes):
        replacement = transformer(node)

        if replacement is node or replacement.sql(dialect="sqlite") == node.sql(dialect="sqlite"):
          continue

        new_stmt = replace_node(p_stmt, target_index, replacement)
        candidate_stmt = splice_replacement(stmts[i], node, replacement)

        if candidate_stmt is None:
          if not can_serialize:
            continue
          candidate_stmt = new_stmt.sql(dialect="sqlite")

        candidate_stmts = stmts[:i] + [candidate_stmt] + stmts[i+1:]
        candidate_sql = unsplit_stmts(candidate_stmts)
        
        if run_oracle(candidate_sql, oracle_script):
          parsed[i] = parse_sql(candidate_stmt)[0]
          stmts[i] = candidate_stmt
          p_stmt = parsed[i]
          changed = True
          break

  return unsplit_stmts(stmts)
