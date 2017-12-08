import sys
import json
def is_id(idtag, line):
	u = line.get('u',line.get('job', ''))
	justid = u.split('jjlong')[-1]
	return justid == idtag
def find_any_matching(feed, idtag):
	return [i for i in feed if is_id(idtag, i)]
def is_mapper(line):
	return line.get('type')=='mapper'
def is_reducer(line):
	return line.get('type')=='reducer'
def jsonify(feed):
	return [try_to_load(line) for line in feed]
def formatter(line):
	try:
		return {'rssi':line.get('rssi')
			,'dest':line.get('node')
			,'total':sum([i['t'] for i in line.get('stats')])
			,'num_msgs':line.get('msgize')
			,'assignment':line.get('assignment')
			}
	except TypeError:
		return line
def try_to_load(stdoutline):
	"""parallel ssh produces some nonsense lines
	like [2] 21:10:57 [SUCCESS] root@192.168.123.96
	and some null lines, just try to json it, if it doesn't
	work return nothing"""
	try:
		return json.loads(stdoutline)
	except ValueError:
		return None
if __name__ == "__main__":
	the_id = sys.argv[1].split('jjlong')[-1]
	feed = [i for i in sys.stdin]
	jsonified = jsonify(feed)
	existing = [i for i in jsonified if i]
	matching = find_any_matching(existing, the_id)
	fmatted = [formatter(line) for line in matching]
	#mapper = [i for i in matching if is_mapper(i)]
	#reducer = [i for i in matching if is_reducer(i)]
	for entry in fmatted:
		print(json.dumps(entry))