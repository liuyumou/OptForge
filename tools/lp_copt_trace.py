"""Read-only CUDA activity attribution, including overlapping streams and graphs."""
from collections import Counter,defaultdict
import sqlite3
import statistics
from lp_cost import interval_union

def analyze(path):
    connection=sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True)
    connection.row_factory=sqlite3.Row
    try:
        tables={r[0] for r in connection.execute("select name from sqlite_master where type='table'")}
        names={r[0]:r[1] for r in connection.execute('select id,value from StringIds')} if 'StringIds' in tables else {}
        kernels=[];copies=[];apis=[];fills=[];graphs=[]
        for table in ['CUPTI_ACTIVITY_KIND_KERNEL','CUPTI_ACTIVITY_KIND_CONCURRENT_KERNEL']:
            if table not in tables:continue
            for row in connection.execute('select * from '+table):
                v=dict(row);name=names.get(v.get('demangledName',v.get('shortName')),str(v.get('shortName','unknown')))
                kernels.append(dict(start=v['start'],end=v['end'],name=name,stream=v.get('streamId'),correlation=v.get('correlationId'),
                    graph_id=v.get('graphId'),graph_node_id=v.get('graphNodeId'),geometry={k:v[k] for k in ['gridX','gridY','gridZ','blockX','blockY','blockZ','registersPerThread'] if k in v}))
        for table in ['CUPTI_ACTIVITY_KIND_MEMCPY','CUPTI_ACTIVITY_KIND_MEMCPY2']:
            if table not in tables:continue
            for row in connection.execute('select * from '+table):
                v=dict(row);copies.append(dict(start=v['start'],end=v['end'],bytes=v.get('bytes'),kind=v.get('copyKind'),stream=v.get('streamId'),correlation=v.get('correlationId')))
        if 'CUPTI_ACTIVITY_KIND_MEMSET' in tables:
            for row in connection.execute('select * from CUPTI_ACTIVITY_KIND_MEMSET'):
                v=dict(row);fills.append(dict(start=v['start'],end=v['end'],bytes=v.get('bytes'),stream=v.get('streamId'),correlation=v.get('correlationId')))
        if 'CUPTI_ACTIVITY_KIND_GRAPH_TRACE' in tables:
            for row in connection.execute('select * from CUPTI_ACTIVITY_KIND_GRAPH_TRACE'):
                v=dict(row);graphs.append(dict(start=v['start'],end=v['end'],stream=v.get('streamId'),correlation=v.get('correlationId'),graph_id=v.get('graphId'),graph_exec_id=v.get('graphExecId')))
        for table in ['CUPTI_ACTIVITY_KIND_RUNTIME','CUPTI_ACTIVITY_KIND_DRIVER']:
            if table not in tables:continue
            for row in connection.execute('select * from '+table):
                v=dict(row);name=names.get(v.get('nameId'),'unknown')
                # This Nsight exporter also puts cu* driver calls in RUNTIME.
                # Retain the source table while naming the documented API family.
                family='RUNTIME' if name.startswith('cuda') else 'DRIVER' if len(name)>2 and name.startswith('cu') and name[2].isupper() else 'UNKNOWN'
                apis.append(dict(start=v['start'],end=v['end'],name=name,correlation=v.get('correlationId'),layer=family,recorded_table=table,thread=v.get('globalTid')))
        if not kernels and not copies and not fills and not graphs:raise ValueError('no recorded CUDA device activity; unavailable, not zero')
        ki=[(k['start'],k['end']) for k in kernels];ci=[(k['start'],k['end']) for k in copies];fi=[(k['start'],k['end']) for k in fills];all_i=ki+ci+fi
        gi=[(g['start'],g['end']) for g in graphs];envelopes=all_i+gi
        start=min(a for a,b in envelopes);end=max(b for a,b in envelopes)
        grouped=defaultdict(list)
        for k in kernels:grouped[k['name']].append(k)
        summaries=[]
        for name,rows in sorted(grouped.items()):
            ns=sorted(r['end']-r['start'] for r in rows)
            geometries=[]
            for row in rows:
                if row['geometry'] not in geometries:geometries.append(row['geometry'])
            summaries.append(dict(name=name,count=len(rows),summed_ns=sum(ns),union_ns=interval_union((r['start'],r['end']) for r in rows),min_ns=min(ns),median_ns=statistics.median(ns),p95_ns=ns[int((len(ns)-1)*0.95)],max_ns=max(ns),geometries=geometries))
        ag=defaultdict(list)
        for a in apis:ag[(a['layer'],a['name'])].append(a)
        api_rows=[dict(layer=layer,name=name,recorded_tables=sorted({r['recorded_table'] for r in rows}),count=len(rows),summed_ns=sum(r['end']-r['start'] for r in rows),union_ns=interval_union((r['start'],r['end']) for r in rows)) for (layer,name),rows in sorted(ag.items())]
        cg=defaultdict(list)
        for c in copies:cg[c['kind']].append(c)
        copy_rows=[dict(kind=kind,direction={1:'host_to_device',2:'device_to_host',8:'device_to_device'}.get(kind,'other_or_unknown'),count=len(rows),bytes=sum(r['bytes'] for r in rows) if all(r['bytes'] is not None for r in rows) else None,
                        summed_ns=sum(r['end']-r['start'] for r in rows),union_ns=interval_union((r['start'],r['end']) for r in rows)) for kind,rows in sorted(cg.items(),key=lambda x:str(x[0]))]
        kernel_busy=interval_union(ki);copy_busy=interval_union(ci);fill_busy=interval_union(fi);kernel_copy_busy=interval_union(ki+ci);busy=interval_union(all_i)
        graph_union=interval_union(gi);envelope_union=interval_union(envelopes)
        correlations=defaultdict(list)
        for a in apis:
            if a['correlation'] is not None:correlations[a['correlation']].append(a['layer']+':'+a['name'])
        # One graph launch may execute many kernels. Correlation coverage is an
        # observation; an absent ID never licenses fabricated one-to-one mapping.
        correlated=sum(k['correlation'] in correlations for k in kernels)
        kc=Counter(k['correlation'] for k in kernels if k['correlation'] in correlations)
        cc=Counter(k['correlation'] for k in copies if k['correlation'] in correlations)
        fc=Counter(k['correlation'] for k in fills if k['correlation'] in correlations)
        gc=Counter(g['correlation'] for g in graphs if g['correlation'] in correlations)
        patterns=defaultdict(list)
        for key in set(kc)|set(cc)|set(fc)|set(gc):patterns[(tuple(sorted(correlations[key])),kc[key],cc[key],fc[key],gc[key])].append(key)
        correlation_groups=[dict(apis=list(names),kernels_per_correlation=k,copies_per_correlation=c,fills_per_correlation=f,graph_envelopes_per_correlation=g,correlation_count=len(ids),example_ids=sorted(ids)[:3])
            for (names,k,c,f,g),ids in sorted(patterns.items())]
        return dict(schema_version=1,kernel_count=len(kernels),kernel_count_is_complete=not graphs,total_executed_kernel_count=None if graphs else len(kernels),graph_count=len(graphs),graph_execution_union_ns=graph_union,graph_summed_ns=sum(b-a for a,b in gi),device_envelope_union_ns=envelope_union,unresolved_graph_span_ns=envelope_union-busy,kernel_summed_ns=sum(b-a for a,b in ki),kernel_union_ns=kernel_busy,
            copy_union_ns=copy_busy,device_union_ns=busy,kernel_copy_overlap_ns=kernel_busy+copy_busy-kernel_copy_busy,kernel_copy_union_ns=kernel_copy_busy,
            memset_count=len(fills) if 'CUPTI_ACTIVITY_KIND_MEMSET' in tables else None,memset_union_ns=fill_busy if 'CUPTI_ACTIVITY_KIND_MEMSET' in tables else None,
            memset_bytes=sum(f['bytes'] for f in fills) if 'CUPTI_ACTIVITY_KIND_MEMSET' in tables and all(f['bytes'] is not None for f in fills) else None,
            observed_device_span_ns=end-start,activity_free_ns=end-start-envelope_union,correlated_kernels=correlated,
            kernels=summaries,copies=copy_rows,apis=api_rows,correlation_groups=correlation_groups,
            uncorrelated_kernels=len(kernels)-correlated,graph_apis=[a for a in api_rows if 'GraphLaunch' in a['name']],
            timeline=[dict(kind='kernel',name=k['name'],start_ns=k['start']-start,end_ns=k['end']-start,stream=k['stream'],correlation=k['correlation'],graph_id=k['graph_id'],graph_node_id=k['graph_node_id']) for k in kernels]+
                     [dict(kind='copy',name=str(c['kind']),start_ns=c['start']-start,end_ns=c['end']-start,stream=c['stream'],correlation=c['correlation']) for c in copies]+
                     [dict(kind='fill',name='memset',start_ns=f['start']-start,end_ns=f['end']-start,stream=f['stream'],correlation=f['correlation']) for f in fills]+
                     [dict(kind='graph',name='opaque graph envelope',start_ns=g['start']-start,end_ns=g['end']-start,stream=g['stream'],correlation=g['correlation'],graph_id=g['graph_id'],graph_exec_id=g['graph_exec_id']) for g in graphs],
            limitations=['CUDA activity time is separate from host wall scopes; runtime/driver API costs may overlap.',
                         'Kernel names do not establish proprietary algorithm or arithmetic precision.',
                         'Device union covers visible kernels/copies/fills only. Graph envelopes can contain unobserved kernels and internal gaps; their union is not exact busy time.',
                         'Activity-free span excludes every recorded graph envelope as well as fine activity; it does not attribute a cause to the gap.',
                         'Opaque graph traces make total kernel counts, internal geometry and per-kernel costs unavailable; visible kernel summaries are incomplete in that case.',
                         'An absent memory-fill table is unavailable, not a measured zero.',
                         'Hardware counters and CPU sampling are unavailable under the existing host restrictions.'])
    finally:connection.close()
