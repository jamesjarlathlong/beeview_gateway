from get_all_stats import get_sol, get_nodes
import sys
if __name__=='__main__':
	job = sys.argv[1]
	nodes = get_nodes(get_sol(job))
	addressify = lambda x: 'root@192.168.123.'+str(x)
	not_zero = [addressify(i) for i in nodes if i]
	print(" ".join(not_zero))
