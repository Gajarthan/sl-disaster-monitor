import test from 'node:test';
import assert from 'node:assert/strict';
import {filterAlerts, healthState, sourceUrl, dateRangeError, mapSeverity} from '../frontend/lib.js';
import {buildHistoryURL, normalizeRow} from '../frontend/history.js';
const alert={districts:['Nuwara Eliya'],hazard:'heavy_rain',hazards:['heavy_rain','flood'],severity:'warning',language:'ta',document_type:'weather',issued_at:'2026-09-13T05:00:00+05:30'};
test('filters combine district, secondary hazard, language, dates and severity',()=>{
 assert.equal(filterAlerts([alert],{district:'Nuwara Eliya',hazard:'flood',language:'ta',severity:'warning',from:'2026-09-13',to:'2026-09-13'}).length,1);
 assert.equal(filterAlerts([alert],{district:'Colombo'}).length,0);
 assert.equal(filterAlerts([{...alert,issued_at:null}],{from:'2026-09-13'}).length,0);
});
test('invalid dates never silently remove filtering',()=>{
 assert.ok(dateRangeError({from:'2026-02-31'})); assert.ok(dateRangeError({from:'2026-09-14',to:'2026-09-13'}));
 assert.equal(dateRangeError({from:'2026-09-13',to:'2026-09-13'}),'');
 assert.throws(()=>buildHistoryURL('owner/data',{from:'invalid'}),/date/i);
});
test('collection health distinguishes stale source and failure',()=>{
 const now=Date.parse('2026-09-13T12:00:00Z');
 const metadata={status:'success',last_successful_scrape:'2026-09-13T11:00:00Z',last_dmc_document_seen:'2026-09-10T12:00:00Z'};
 assert.equal(healthState(metadata,now).kind,'source_stale');
 assert.equal(healthState({...metadata,status:'error'},now).kind,'error');
 assert.equal(healthState({...metadata,last_successful_scrape:'2026-09-13T00:00:00Z'},now).kind,'stale');
 assert.equal(healthState({},now).kind,'never_run');
 assert.equal(mapSeverity([alert],true),'no_coverage'); assert.equal(mapSeverity([],false),'no_coverage');
});
test('only official HTTPS URLs can be linked',()=>{
 assert.ok(sourceUrl('https://www.dmc.gov.lk/a.pdf')); assert.equal(sourceUrl('https://dmc.gov.lk.evil.test/a.pdf'),null); assert.equal(sourceUrl('javascript:alert(1)'),null);
});
test('history uses scalar district filtering, safe SQL literals and pagination',()=>{
 const url=new URL(buildHistoryURL('gajarthan/sl-disaster-alerts',{district:'Nuwara Eliya',hazard:"rain' OR 1=1 --",from:'2026-09-13',document_type:'weather'},50));
 const where=url.searchParams.get('where');
 assert.match(where,/"district_nuwara_eliya" = true/); assert.match(where,/rain'' OR 1=1 --/);
 assert.match(where,/"issued_at" >= '2026-09-13T00:00:00\+05:30'/);
 assert.equal(url.searchParams.get('length'),'50'); assert.equal(url.searchParams.get('offset'),'50');
 assert.equal(url.searchParams.get('orderby'),'"issued_at" DESC');
 assert.throws(()=>buildHistoryURL('x/y',{district:'Colombo" OR true'}),/district/i);
});
test('archive flattened objects are restored without crashing on malformed JSON',()=>{
 assert.deepEqual(normalizeRow({official_json:'{"title":"Rain"}',extraction_json:'bad'}).official,{title:'Rain'});
 assert.deepEqual(normalizeRow({extraction_json:'bad'}).extraction,{});
});
test('recent provider loads once, filters before pagination, and retries a failed load',async()=>{
 const {recentProvider}=await import('../frontend/history.js'); const original=globalThis.fetch;let calls=0;
 globalThis.fetch=async()=>{calls++;if(calls===1)throw new Error('offline');return {ok:true,json:async()=>Array.from({length:51},(_,i)=>({...alert,id:i}))};};
 try{const provider=recentProvider();assert.equal(calls,0);await assert.rejects(provider.search({}),/offline/);const first=await provider.search({district:'Nuwara Eliya'});assert.equal(first.rows.length,50);assert.equal(first.hasMore,true);const next=await provider.search({},50);assert.equal(next.rows.length,1);assert.equal(next.hasMore,false);assert.equal(calls,2);}finally{globalThis.fetch=original;}
});
test('history sends all scalar filters and restores returned row objects',async()=>{
 const {historyProvider}=await import('../frontend/history.js');const original=globalThis.fetch;let request;
 globalThis.fetch=async url=>{request=new URL(url);return {ok:true,json:async()=>({rows:[{row:{...alert,official_json:'{"title":"Rain"}'}}],num_rows_total:1})};};
 try{const result=await historyProvider('x/y').search({severity:'warning',language:'ta',document_type:'weather'});assert.equal(result.rows[0].official.title,'Rain');assert.equal(result.hasMore,false);assert.match(request.searchParams.get('where'),/"severity" = 'warning'/);assert.match(request.searchParams.get('where'),/"language" = 'ta'/);}finally{globalThis.fetch=original;}
});
test('nonstandard source ports and future collection timestamps are rejected',()=>{
 assert.equal(sourceUrl('https://www.dmc.gov.lk:8443/a.pdf'),null);
 assert.ok(sourceUrl('https://www.dmc.gov.lk:443/a.pdf'));
 assert.equal(healthState({status:'success',last_successful_scrape:'2026-09-14T00:00:00Z'},Date.parse('2026-09-13T12:00:00Z')).muted,true);
});
test('partially indexed archive results never claim complete coverage',async()=>{
 const {historyProvider}=await import('../frontend/history.js');const original=globalThis.fetch;
 globalThis.fetch=async()=>({ok:true,json:async()=>({partial:true,rows:[],num_rows_total:0})});
 try{await assert.rejects(historyProvider('x/y').search({}),/incomplete/i);}finally{globalThis.fetch=original;}
});
