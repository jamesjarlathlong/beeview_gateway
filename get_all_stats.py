import sys
import json
import functools
def namer(sol):
    return {k+'_'+str(idx):el for k,v in sol.items() for idx, el in enumerate(v)}

def find_matching(entries, assignment):
    pxes = [add_assignment(entry) for entry in entries if entry.get('type')]
    txes = [entry for entry in entries if entry.get('assignment')]
    matching = [entry for entry in txes+pxes if entry.get('assignment')==assignment]
    return matching
def add_assignment(entry):
    translater = {'mapper':'M', 'reducer':'R'}
    idx = entry.get('onkey', entry.get('mapnum'))
    level = translater[entry.get('type')]
    assignment= level+'_'+str(idx)
    entry['assignment'] = assignment
    return entry
def find_all_matchers(solution, all_entries):
    return {k: find_matching(all_entries, k) for k in solution}
def format_txs(transmissions):
    print('transmissions: ', transmissions)
    return [(str(tx['dest']), 1000*tx['total']) for tx in transmissions]
def format_pxs(processed):
    times = [sum(i['ts']) for i in processed]
    self_node = next(iter([i.get('self') for i in processed]), None)
    return str(self_node), 1000*sum(times)
def format_assignment(assignment, matchers):
    """[{'mapnum': 1, 'assignment': 'M_1', 'ts': [0.009473085403442383, 2.288818359375e-05]
         ,'self': '96', 'type': 'mapper', 'job': 'jjlongkjegh'}
        ,{'rssi': 19, 'total': 2.6517860889434814, 'num_msgs': 3, 'assignment': 'M_1', 'dest': 31}
        ,{'mapnum': 1, 'assignment': 'M_1', 'ts': [0.009473085403442383, 2.288818359375e-05]
          ,'self': '96', 'type': 'mapper', 'job': 'jjlongkjegh'}
        ]
    """
    txes = [i for i in matchers if i.get('rssi')]
    pxes = [i for i in matchers if not i.get('rssi')]
    edge_weights = format_txs(txes)
    self_node, node_weight = format_pxs(pxes)
    return self_node, {'edge_w':edge_weights 
                       ,'node_w':node_weight
                       ,'name':assignment}
def format_all_assignments(assignment_data_pairs):
    return [format_assignment(assignment, data) 
            for assignment, data
            in assignment_data_pairs.items()]

def get_sol(job_name):
    with open('dag_stats') as f:
        jsons = (json.loads(line) for line in f.readlines())
        d = next((line for line in jsons if line.get('job')==job_name))
        sol = d['sol']
        return sol
def get_nodes(sol):
    node_lists = [v for k,v in sol.items()]
    uqified = set(functools.reduce( lambda x,y:x+y, node_lists))
    return list(uqified)
if __name__=='__main__':
    job_name = sys.argv[1]
    sol = get_sol(job_name)
    lines = [json.loads(line.strip('\n'))for line in sys.stdin]
    matched_to_assignment = find_all_matchers(namer(sol), lines)
    formatted = format_all_assignments(matched_to_assignment)
    for a,l in formatted:
        print(a,':',l)


"""
parallel-ssh -i -h hosts.txt "tail -n 2 /etc/init.d/beeview_liss/px_stats; tail -n 2 /etc/init.d/beeview_liss/tx_stats"|python3 get_tx_stats.py "kjegh"|python3 get_all_stats.py "jjlongkjegh"

make sure not scaling sense wrong in dag-plan

next step:
1) concatenate px types down to one node_w:0.456 for example - there are at least two pxes per assignment
2) concatenate tx types into a edge_w dictionary, for example
{'dest': 31, 'num_msgs': 3, 'total': 2.6517860889434814, 'rssi': 19, 'assignment': 'M_1'} 
and 
{'dest': 96, 'num_msgs': 3, 'total': 3.6517860889434814, 'rssi': 19, 'assignment': 'M_1'}
need to turn into [('31':2.65), ('96':3.65)]
what happens if there are multiple reducers on the same node?? -> ok it's fine, just use list of tuples instead of dict for edge_w
maybe sort them by index, or use e.g. 31_0, 96_1??
"""
