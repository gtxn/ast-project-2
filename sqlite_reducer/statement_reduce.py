from collections import defaultdict
from .utils import *

def immutable_delete(arr, to_delete):
  to_delete = set(to_delete)
  return [item for i, item in enumerate(arr) if i not in to_delete]

def statement_reducer(sql_stmt: str, oracle_script: str) -> str:
  parts = split_stmts(sql_stmt)
  table_statement_map = defaultdict(set)
  table_statement_map['uncategorised_table'] = set()
  
  for i, stmt in enumerate(parts):
    try:
      tables = get_tables(stmt)
      if len(tables) > 1:
        table_statement_map['uncategorised_table'].add(i)
      else:
        table = tables[0]
        table_statement_map[table].add(i)
    
    except:
      table_statement_map['uncategorised_table'].add(i)
      
  all_tables = set(table_statement_map.keys()) - set(['uncategorised_table'])
  
  all_to_delete = set([])
  
  for table in all_tables:
    all_to_delete |= table_statement_map[table]
    parts_test = immutable_delete(parts, all_to_delete)
    
    sql_to_test = unsplit_stmts(parts_test)
    
    if run_oracle(sql_to_test, oracle_script):
      all_to_delete |= table_statement_map[table]
    else:
      all_to_delete -= table_statement_map[table]
  
  parts = immutable_delete(parts, all_to_delete)
  
  return unsplit_stmts(parts)

