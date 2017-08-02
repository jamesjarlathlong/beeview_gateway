def reducer(k,vs):
	ws = [complex(*i[1]) for i in vs]
	one_row = lambda i,lst:[i*conj(e) for e in lst]
	all_rows = lambda lst:[one_row(i,lst) for i in lst]
	eig = np.pagerank(all_rows(ws))
	modeshape = [(vs[idx][0], el) for idx,el in enumerate(eig)]
	yield k,modeshape