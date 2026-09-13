export const SEVERITIES=['unknown','info','advisory','warning','severe'];
export const COLORS={no_coverage:'#b8c5cd',unknown:'#7d718e',info:'#448fa5',advisory:'#c59c2f',warning:'#c97730',severe:'#bb3543'};
export const label=value=>String(value||'Unknown').replaceAll('_',' ').replace(/^./,c=>c.toUpperCase());
export function sourceUrl(value){try{const u=new URL(value);return u.protocol==='https:'&&['dmc.gov.lk','www.dmc.gov.lk'].includes(u.hostname)&&!u.port&&!u.username&&!u.password?u.href:null;}catch{return null;}}
function validDate(value){return /^\d{4}-\d{2}-\d{2}$/.test(value)&&!Number.isNaN(Date.parse(value))&&new Date(value).toISOString().slice(0,10)===value;}
export function dateRangeError(f){if([f.from,f.to].some(v=>v&&!validDate(v)))return 'Enter valid dates.';if(f.from&&f.to&&f.from>f.to)return 'The start date must be on or before the end date.';return '';}
export function filterAlerts(rows,f={}){if(dateRangeError(f))return [];return rows.filter(a=>{
 if(f.district&&!a.districts?.includes(f.district))return false;
 if(f.hazard&&!(a.hazards||[a.hazard]).includes(f.hazard))return false;
 for(const k of ['severity','language','document_type'])if(f[k]&&a[k]!==f[k])return false;
 if(f.from||f.to){if(!a.issued_at||!Number.isFinite(Date.parse(a.issued_at)))return false;const day=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Colombo',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(a.issued_at));if(f.from&&day<f.from||f.to&&day>f.to)return false;}
 return true;
});}
export function healthState(m={},now=Date.now()){
 const last=Date.parse(m.last_successful_scrape),doc=Date.parse(m.last_dmc_document_seen);
 if(m.status==='error')return {kind:'error',muted:true,message:'Collection failed. Displayed reports may be out of date. Check the official DMC source.'};
 if(m.status==='partial')return {kind:'partial',muted:true,message:'Collection is incomplete. Some source documents could not be checked; coverage may be missing.'};
 if(!Number.isFinite(last))return {kind:'never_run',muted:true,message:'No successful collection is recorded yet. Current coverage is unavailable.'};
 if(last-now>15*60000||doc-now>15*60000)return {kind:'stale',muted:true,message:'Collection or source timestamps are in the future. Current coverage cannot be verified; consult DMC.'};
 if(now-last>6*3600000)return {kind:'stale',muted:true,message:'Collection is more than 6 hours old. Current coverage is unavailable; consult DMC.'};
 if(!Number.isFinite(doc)||now-doc>48*3600000)return {kind:'source_stale',muted:true,message:'Collection is running, but the newest dated source document is over 48 hours old or undated. This does not establish current conditions.'};
 return {kind:'success',muted:false,message:'Collection is up to date. Reports describe district mentions, not verified affected areas.'};
}
export function mapSeverity(rows,muted){if(muted||!rows.length)return 'no_coverage';return rows.reduce((best,a)=>SEVERITIES.indexOf(a.severity)>SEVERITIES.indexOf(best)?a.severity:best,'unknown');}
export function displayTime(value){const d=new Date(value);return value&&Number.isFinite(d.getTime())?new Intl.DateTimeFormat('en-GB',{dateStyle:'medium',timeStyle:'short',timeZone:'Asia/Colombo'}).format(d)+' SLST':'Not available';}
