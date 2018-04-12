import json
from copy import deepcopy
import sys
def reformat_edge(level, edgedict, solution):  
        def get_target_node(solution,level,index):
            nextlevel = {'S':'M','M':'R','R':'K'}
            target_node_level = nextlevel.get(level)
            target_node_idx = int(index)
            return str(solution[target_node_level][target_node_idx])
        return [(get_target_node(solution, level,k),v) 
                for k,v in edgedict.items()] 
                #use list of tuples here instead of dict because while indexes
                #are unique, node assignment may not be, e.g. the solved dag
                #might have R = [0,0,0,0]
def reformat_entry(graph_key,graph_value, solution):
    """graph ley value  is like:'K_0', {'children': [], 'parents': ['R_0'], 'node_w': 0, 'edge_w': {'0':1381}}
    solution is like {'R': [31,21], 'S': [31,21], 'K': [0], 'M': [31]}
    result we want it like '31':{'name':'S_0','node_w':0.5,'edge_w':{'31':3.2}}"""
    level, index = graph_key.split('_')
    node = str(solution[level][int(index)])
    new_graph = {'name':graph_key}
    new_graph['node_w'] = graph_value.get('node_w')
    new_graph['edge_w'] = reformat_edge(level, graph_value.get('edge_w'), solution)
    return node, new_graph
def reformat(solution, graph):
    return [reformat_entry(k,v,solution) for k,v in graph.items()]
def is_senser(entry):
    return entry['name'].split('_')[0]=='S'
def nodew_translator(k, entry, px):
    """px is a dictionary of speeds e.g. {'31':0.3,'0':1}
    k is a node label e.g. '31', entry is a task description
    like {'edge_w': {'31':1024}, 'name': 'K_0', 'node_w': 0}
    """
    speed = 1 if is_senser(entry) else px.get(k)
    new_entry = deepcopy(entry)
    new_entry['node_w'] = new_entry['node_w']/speed
    return new_entry
def translate_nodeweights(px,graph_list):
    """graph_list is like [('0', {'edge_w': {}, 'name': 'K_0', 'node_w': 0}),
     ('31', {'edge_w': {'31': 100}, 'name': 'M_0', 'node_w': 0.6049999999999667})]
     """
    return [(k,nodew_translator(k,v,px)) for k,v in graph_list]
def get_bw(bw, source, target):
    try:
        return bw[source][target]
    except:
        couldbe = bw[target][source]
        return couldbe
def adjust(volume, source_node, target_node, bw):
    b= get_bw(bw, source_node, target_node)
    res = volume*b  
    return res  
def edgew_translator(source_node, entry, bw):
    edgeweight_dict = entry['edge_w']
    new_edgeweights = [(target_node,adjust(volume, source_node,target_node,bw) )
                       for target_node,volume
                       in edgeweight_dict]
    new_entry = deepcopy(entry)
    new_entry['edge_w'] = new_edgeweights
    return new_entry
def translate_edgeweights(bw, graph_list):
    return [(k, edgew_translator(k, v, bw)) for k,v in graph_list]
def get_job_record(job_name):
    with open('dag_stats', "r") as f1:
        jsons = (json.loads(line) for line in f1.readlines())
        d = next((line for line in jsons if line.get('job')==job_name))
        return d
def get_node_total(entry):
    return entry.get('node_w')+sum([i[1] for i in entry.get('edge_w')])
def get_total(results):
    #results is a tuple of node, and {"node_w": 0, "edge_w": [],'name'}
    return sum((get_node_total(v) for k,v in results))

if __name__ == '__main__':
    job_name = sys.argv[1]
    d = get_job_record(job_name)
    parsed = translate_edgeweights(d['bw'],translate_nodeweights(d['px'],reformat(d['sol'],d['graph'])))
    for k,v in parsed:
        print(k,':',v)
    print('total: ',d['totaltime'], get_total(parsed))