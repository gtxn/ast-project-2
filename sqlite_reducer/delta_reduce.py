from .utils import *

def delta_statement_reducer(sql_stmt: str, oracle_script: str) -> str:
  parts = delta_debug(split_stmts(sql_stmt), oracle_script, delimitter=';\n')
  
  return unsplit_stmts(parts)

def delta_token_reducer(sql_stmt: str, oracle_script: str) -> str:
  parts = delta_debug(tokenize_sql(sql_stmt), oracle_script, delimitter=' ')
  
  return untokenize_sql(parts)
