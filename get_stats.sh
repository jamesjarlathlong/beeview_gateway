#!/bin/bash
job=$1
hosts=$(python3 nodes_from_job.py $job)
{ parallel-ssh -i -v -H "$hosts" "tail -n 20 /etc/init.d/beeview_liss/px_stats; tail -n 20 /etc/init.d/beeview_liss/tx_stats" ; tail -n 20 px_stats; } \
		|python3 get_tx_stats.py "$job" \
		|python3 get_all_stats.py "$job"
