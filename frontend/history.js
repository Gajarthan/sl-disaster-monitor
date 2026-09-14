import {dateRangeError,filterAlerts,LANGUAGE_NAMES} from './lib.js';
const literal=v=>"'"+String(v).replaceAll("'","''")+"'";
export function buildHistoryURL(dataset,f={},offset=0){
 const error=dateRangeError(f);if(error)throw new Error(error);
 const where=[];
 if(f.district){if(!/^[A-Za-z]+(?:[ -][A-Za-z]+)*$/.test(f.district))throw new Error('Invalid district');where.push('"district_'+f.district.toLowerCase().replace(/[ -]/g,'_')+'" = true');}
 for(const k of ['hazard','severity','document_type'])if(f[k])where.push('"'+k+'" = '+literal(f[k]));
 if(f.language)where.push(Object.hasOwn(LANGUAGE_NAMES,f.language)?'"language_'+f.language+'" = true':'"language" = '+literal(f.language));
 if(f.from)where.push('"issued_at" >= '+literal(f.from+'T00:00:00+05:30'));
 if(f.to)where.push('"issued_at" <= '+literal(f.to+'T23:59:59.999999+05:30'));
 const params=new URLSearchParams({dataset,config:'default',split:'train',where:where.join(' AND ')||'"source" = \'DMC\'',orderby:'"issued_at" DESC',offset:String(Math.max(0,Number(offset)||0)),length:'50'});
 return 'https://datasets-server.huggingface.co/filter?'+params;
}
export function normalizeRow(row){const copy={...row};for(const k of ['official','extraction']){if(!copy[k]||typeof copy[k]!=='object'){try{copy[k]=JSON.parse(copy[k+'_json']||'{}');}catch{copy[k]={};}}}return copy;}
export async function fetchJSON(url){const response=await fetch(url,{signal:AbortSignal.timeout(25000)});if(!response.ok)throw new Error('Request failed ('+response.status+')');return response.json();}
// Both adapters expose search(filters, offset). A database adapter can use the same contract.
export function recentProvider(url='./data/alerts_recent.json'){let cached;return {async search(filters,offset=0){if(!cached)cached=await fetchJSON(url);const rows=filterAlerts(cached,filters);return {rows:rows.slice(offset,offset+50),hasMore:offset+50<rows.length};}};}
export function historyProvider(dataset){return {async search(filters,offset=0){if(!dataset)throw new Error('Historical archive is not configured.');const data=await fetchJSON(buildHistoryURL(dataset,filters,offset));if(data.partial)throw new Error('Archive indexing is incomplete. Retry after the archive has finished indexing.');if(!Array.isArray(data.rows))throw new Error('Historical archive returned an unexpected response.');const rows=data.rows.map(x=>normalizeRow(x.row));return {rows,hasMore:typeof data.num_rows_total==='number'?offset+rows.length<data.num_rows_total:rows.length===50};}};}
